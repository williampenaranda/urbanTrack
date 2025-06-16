from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, and_ # Importa 'cast' y 'and_'
from sqlalchemy.sql import alias
# Importaciones necesarias para trabajar con geometrías en SQLAlchemy y PostGIS
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID, ST_Distance
from geoalchemy2.types import Geography
from geoalchemy2.shape import to_shape # Para convertir de Geometry a Shapely Point

from app.models.entities import Ruta, Parada, RutaParada
# Importamos los modelos Pydantic necesarios para la nueva respuesta
from app.models.models import SimplifiedCalculatedRouteResponse, SimplifiedParadaResponse # ASUMO que estos modelos existen aquí o se importarán

from typing import List, Dict, Optional, Tuple
import heapq # Para la cola de prioridad de Dijkstra
from datetime import timedelta # Para manejar tiempos


# --- Constantes de Configuración del Algoritmo ---
DEFAULT_BUS_SPEED_KPH = 20 # Velocidad promedio del bus en km/h
DEFAULT_BUS_SPEED_MPS = DEFAULT_BUS_SPEED_KPH * 1000 / 3600 # Convertir a metros por segundo

WALKING_SPEED_KPH = 5 # Velocidad promedio al caminar en km/h
WALKING_SPEED_MPS = WALKING_SPEED_KPH * 1000 / 3600 # Convertir a metros por segundo

TRANSFER_PENALTY_MINUTES = 15 # Penalización por cada transbordo en minutos
TRANSFER_PENALTY_SECONDS = TRANSFER_PENALTY_MINUTES * 60 # Convertir a segundos

MAX_DISTANCE_TO_STOP_METERS = 300 # Distancia máxima para considerar que una ubicación está cerca de una parada

# --- La función _get_distance_between_points ya no es necesaria, se remueve ---


def _build_transport_graph(db: Session) -> Dict[int, List[Dict]]:
    """
    Construye un grafo de transporte a partir de las rutas y paradas de la base de datos,
    calculando los costos de los segmentos de manera eficiente en una sola consulta.
    """
    graph: Dict[int, List[Dict]] = {}
    
    # 1. Traer todas las paradas y rutas para mapearlas en Python (para nombres y ubicaciones)
    paradas = db.query(Parada).all()
    paradas_map = {p.id: p for p in paradas}
    
    # 2. Obtener todos los segmentos de ruta con sus costos de distancia en una sola consulta
    #    Usamos una subconsulta con LEAD para obtener la siguiente parada en la misma ruta
    
    subquery_rp = db.query(
        RutaParada.ruta_id,
        RutaParada.parada_id,
        RutaParada.orden,
        func.lead(RutaParada.parada_id).over(
            partition_by=RutaParada.ruta_id, order_by=RutaParada.orden
        ).label('next_parada_id')
    ).subquery()

    # Alias para la tabla Parada para poder unirla dos veces (para la parada actual y la siguiente)
    P1 = alias(Parada.__table__, name='p1')
    P2 = alias(Parada.__table__, name='p2')

    # Consulta para obtener los datos de los segmentos de viaje entre paradas
    segment_data = db.query(
        subquery_rp.c.ruta_id,
        subquery_rp.c.parada_id.label('from_parada_id'),
        subquery_rp.c.next_parada_id.label('to_parada_id'),
        ST_Distance(
            cast(P1.c.ubicacion, Geography),
            cast(P2.c.ubicacion, Geography)
        ).label('distance_meters')
    ).join(
        P1, subquery_rp.c.parada_id == P1.c.id
    ).join(
        P2, subquery_rp.c.next_parada_id == P2.c.id
    ).filter(
        subquery_rp.c.next_parada_id.isnot(None) # Excluye la última parada de cada ruta
    ).all()

    # 3. Poblar el grafo con los datos de los segmentos
    for seg in segment_data:
        from_parada_id = seg.from_parada_id
        to_parada_id = seg.to_parada_id
        ruta_id = seg.ruta_id
        distance_meters = seg.distance_meters

        if distance_meters is None or distance_meters == 0:
            cost = 1 # Pequeño costo para evitar división por cero
        else:
            cost = distance_meters / DEFAULT_BUS_SPEED_MPS # Tiempo en segundos

        if from_parada_id not in graph:
            graph[from_parada_id] = []
        if to_parada_id not in graph: # Asegurarse de que el nodo de destino también esté en el grafo
            graph[to_parada_id] = [] 

        graph[from_parada_id].append({
            "neighbor": to_parada_id,
            "cost": cost,
            "ruta_id": ruta_id,
            "is_transfer": False # Esto se manejará en Dijkstra si hay cambio de ruta
        })
    
    # Asegurarse de que todas las paradas existan como nodos en el grafo, incluso si no tienen salidas directas
    for p_id in paradas_map.keys():
        if p_id not in graph:
            graph[p_id] = []

    # 4. Añadir información para transbordos (no son "aristas" físicas, sino puntos de decisión)
    #    Solo necesitamos asegurarnos de que la parada exista en el grafo si múltiples rutas la atraviesan.
    rutas_paradas = db.query(RutaParada).all() 
    paradas_con_rutas: Dict[int, set[int]] = {} # Usar un set para rutas_en_parada
    for rp in rutas_paradas:
        if rp.parada_id not in paradas_con_rutas:
            paradas_con_rutas[rp.parada_id] = set()
        paradas_con_rutas[rp.parada_id].add(rp.ruta_id)
    
    for parada_id, rutas_en_parada in paradas_con_rutas.items():
        if len(rutas_en_parada) > 1:
            if parada_id not in graph:
                graph[parada_id] = []

    return graph


def _dijkstra(graph: Dict[int, List[Dict]], start_node: int, end_node: int) -> Optional[Dict]:
    """
    Implementación del algoritmo de Dijkstra para encontrar el camino más corto.
    Retorna un diccionario con los segmentos del camino y el tiempo total,
    o None si no hay camino.
    Cada segmento: {"from_parada_id": X, "to_parada_id": Y, "ruta_id": Z, "is_transfer": False/True, "cost": segundos}
    """
    distances = {node: float('inf') for node in graph}
    
    # predecessors guarda (nodo_previo, ruta_id_del_segmento_que_llego_a_actual_node)
    predecessors: Dict[int, Tuple[Optional[int], Optional[int]]] = {node: (None, None) for node in graph}
    
    # Cola de prioridad: (costo_acumulado, nodo_actual, ruta_id_actual_del_pasajero)
    priority_queue = [(0, start_node, None)] # costo, nodo_actual, ruta_id que trajo al nodo_actual
    distances[start_node] = 0

    while priority_queue:
        current_cost, current_node, current_passenger_route_id = heapq.heappop(priority_queue)

        if current_cost > distances[current_node]:
            continue

        if current_node == end_node:
            break

        for edge in graph.get(current_node, []):
            neighbor = edge["neighbor"]
            edge_cost = edge["cost"]
            edge_ruta_id = edge["ruta_id"] # La ruta de este segmento

            cost_to_neighbor = current_cost + edge_cost

            # Lógica de penalización de transbordo:
            # Si el pasajero ya está en una ruta (current_passenger_route_id is not None)
            # y el segmento que va a tomar (edge_ruta_id) es diferente a su ruta actual,
            # aplicamos la penalización.
            if current_passenger_route_id is not None and edge_ruta_id != current_passenger_route_id:
                cost_to_neighbor += TRANSFER_PENALTY_SECONDS

            # La condición para actualizar la distancia debe considerar el current_passenger_route_id
            # para evitar ciclos o caminos subóptimos cuando la ruta de un nodo cambia
            # Por simplicidad, si el costo es menor, actualizamos. Esto asume que el dijkstra
            # encuentra el camino de menor costo en tiempo, incluyendo penalizaciones.
            if cost_to_neighbor < distances[neighbor]:
                distances[neighbor] = cost_to_neighbor
                predecessors[neighbor] = (current_node, edge_ruta_id)
                heapq.heappush(priority_queue, (cost_to_neighbor, neighbor, edge_ruta_id))

    if distances[end_node] == float('inf'):
        return None # No se encontró un camino

    # Reconstruir el camino y sus detalles
    path = []
    current = end_node
    # Mantener un registro de la ruta actual para el último segmento insertado
    # para detectar correctamente el transbordo al principio del siguiente.
    # Inicialmente es None, para que el primer segmento no aplique penalización de transbordo.
    last_segment_ruta_id = None 

    # Esto reconstruye el camino en orden inverso, luego se invierte al final
    temp_path_segments = []
    while current != start_node:
        prev_node, segment_ruta_id = predecessors[current]
        
        if prev_node is None: # Se llegó al nodo de inicio o hay un problema
            break

        # Calcular el costo real de este segmento (sin la penalización de transbordo que se aplicó al *llegar* a 'current')
        # Si 'current_node' fue alcanzado desde 'prev_node' con una penalización de transbordo,
        # esa penalización ya está incluida en distances[current].
        # El costo del *segmento de bus* en sí es el costo del borde.
        # Para obtener el costo de este segmento de bus, podemos buscarlo en el grafo.
        actual_segment_cost = 0
        for edge in graph.get(prev_node, []):
            if edge["neighbor"] == current and edge["ruta_id"] == segment_ruta_id:
                actual_segment_cost = edge["cost"]
                break

        # Determinar si este segmento es el *resultado* de un transbordo (es decir, el viaje en bus empieza en una nueva ruta)
        is_transfer_point = False
        if last_segment_ruta_id is not None and segment_ruta_id != last_segment_ruta_id:
             is_transfer_point = True # Si la ruta del segmento actual es diferente a la del anterior

        temp_path_segments.append({
            "from_parada_id": prev_node,
            "to_parada_id": current,
            "ruta_id": segment_ruta_id,
            "is_transfer_point": is_transfer_point, # Indica que aquí se realizó un cambio de ruta (antes de tomar este segmento)
            "cost_seconds": actual_segment_cost # El costo real del viaje en bus de este segmento
        })
        last_segment_ruta_id = segment_ruta_id # Actualizar para la siguiente iteración
        current = prev_node
    
    path = temp_path_segments[::-1] # Invertir para obtener el orden correcto

    total_time_seconds = distances[end_node]
    return {"path_segments": path, "total_time_seconds": total_time_seconds}


# --- Función Principal de Cálculo de Trayecto ---

async def calcular_trayecto_usuario( # Hacemos la función asíncrona
    db: Session,
    origen_lat: float,
    origen_lon: float,
    destino_lat: float,
    destino_lon: float
) -> Optional[SimplifiedCalculatedRouteResponse]: # Modificamos el tipo de retorno
    """
    Calcula el trayecto más eficiente (en tiempo) para el usuario
    desde una ubicación de origen a una ubicación de destino,
    priorizando rutas directas con penalización por transbordo,
    y retorna la información en un formato simplificado.
    """
    
    # 1. Identificar la parada de origen más cercana de forma eficiente
    # Crear un punto GEOGRAPHY para el origen
    origen_point_geo = cast(ST_SetSRID(ST_MakePoint(origen_lon, origen_lat), 4326), Geography)
    
    # Consulta optimizada para encontrar la parada más cercana dentro del radio MAX_DISTANCE_TO_STOP_METERS
    parada_origen_cercana_result = db.query(
        Parada,
        ST_Distance(cast(Parada.ubicacion, Geography), origen_point_geo).label("distance_meters")
    ).filter(
        ST_Distance(cast(Parada.ubicacion, Geography), origen_point_geo) <= MAX_DISTANCE_TO_STOP_METERS
    ).order_by(
        "distance_meters"
    ).first()

    if not parada_origen_cercana_result:
        # Retorna None, el endpoint manejara la HTTPException
        return None 
    
    parada_origen_cercana, min_dist_origen = parada_origen_cercana_result

    # 2. Identificar la parada de destino más cercana de forma eficiente
    # Crear un punto GEOGRAPHY para el destino
    destino_point_geo = cast(ST_SetSRID(ST_MakePoint(destino_lon, destino_lat), 4326), Geography)

    # Consulta optimizada para encontrar la parada más cercana dentro del radio MAX_DISTANCE_TO_STOP_METERS
    parada_destino_cercana_result = db.query(
        Parada,
        ST_Distance(cast(Parada.ubicacion, Geography), destino_point_geo).label("distance_meters")
    ).filter(
        ST_Distance(cast(Parada.ubicacion, Geography), destino_point_geo) <= MAX_DISTANCE_TO_STOP_METERS
    ).order_by(
        "distance_meters"
    ).first()
    
    if not parada_destino_cercana_result:
        # Retorna None, el endpoint manejara la HTTPException
        return None 
    
    parada_destino_cercana, min_dist_destino = parada_destino_cercana_result

    # 3. Construir el grafo de transporte
    graph = _build_transport_graph(db)

    # Asegurarse de que las paradas de origen y destino existan en el grafo
    if parada_origen_cercana.id not in graph or parada_destino_cercana.id not in graph:
        # Esto indica un problema de datos o que las paradas no son parte de rutas conectadas
        return None 

    # 4. Ejecutar el algoritmo de Dijkstra
    dijkstra_result = _dijkstra(graph, parada_origen_cercana.id, parada_destino_cercana.id)

    if not dijkstra_result:
        return None # No se encontró un camino viable en bus

    # 5. Calcular los componentes de la respuesta simplificada
    
    # Tiempo estimado total
    total_bus_and_transfer_time_seconds = dijkstra_result["total_time_seconds"]

    # Tiempos de caminata
    time_walking_origin_seconds = min_dist_origen / WALKING_SPEED_MPS if WALKING_SPEED_MPS > 0 else 0
    time_walking_destination_seconds = min_dist_destino / WALKING_SPEED_MPS if WALKING_SPEED_MPS > 0 else 0

    total_estimated_time_seconds = total_bus_and_transfer_time_seconds + time_walking_origin_seconds + time_walking_destination_seconds
    tiempo_estimado_minutos = round(total_estimated_time_seconds / 60, 2)

    # Lista de paradas del trayecto
    path_segments = dijkstra_result["path_segments"]
    
    # Necesitamos cargar los nombres de las rutas y paradas
    rutas_map = {r.id: r.nombre for r in db.query(Ruta).all()}
    paradas_map = {p.id: p for p in db.query(Parada).all()} # Mapear por ID para acceso rápido
    
    paradas_trayecto_data: List[SimplifiedParadaResponse] = []
    
    # Añadir la parada de embarque (la primera parada del trayecto en bus)
    if path_segments:
        first_segment = path_segments[0]
        first_bus_stop_id = first_segment["from_parada_id"]
        first_bus_ruta_id = first_segment["ruta_id"] # La ruta del primer segmento
        first_parada_obj = paradas_map.get(first_bus_stop_id)
        if first_parada_obj:
            paradas_trayecto_data.append(
                SimplifiedParadaResponse(
                    nombre=first_parada_obj.nombre,
                    ruta_nombre=rutas_map.get(first_bus_ruta_id, "N/A"), # La ruta asociada a esta parada en el trayecto
                    longitude=to_shape(first_parada_obj.ubicacion).x,
                    latitude=to_shape(first_parada_obj.ubicacion).y
                )
            )

        # Iterar sobre los segmentos para añadir el resto de paradas
        for segment in path_segments:
            # Añadir la parada 'to_parada_id' de cada segmento
            # Esto automáticamente incluye la parada de transbordo y la parada final
            current_parada_id = segment["to_parada_id"]
            current_ruta_id = segment["ruta_id"]
            current_parada_obj = paradas_map.get(current_parada_id)

            if current_parada_obj:
                paradas_trayecto_data.append(
                    SimplifiedParadaResponse(
                        nombre=current_parada_obj.nombre,
                        ruta_nombre=rutas_map.get(current_ruta_id, "N/A"),
                        longitude=to_shape(current_parada_obj.ubicacion).x,
                        latitude=to_shape(current_parada_obj.ubicacion).y
                    )
                )

    # Eliminar duplicados si hay (ej. si la misma parada es el fin de un segmento y el inicio de otro)
    # Convertir a tuplas para que sean 'hashable' y luego de vuelta a lista de objetos
    unique_paradas_tuples = []
    seen_coords = set()
    for parada in paradas_trayecto_data:
        coords_tuple = (parada.latitude, parada.longitude)
        if coords_tuple not in seen_coords:
            unique_paradas_tuples.append(parada)
            seen_coords.add(coords_tuple)
    paradas_trayecto_data = unique_paradas_tuples


    # Retornar el resultado en el formato Pydantic simplificado
    return SimplifiedCalculatedRouteResponse(
        tiempo_estimado_minutos=tiempo_estimado_minutos,
        distancia_origen_primera_parada_metros=round(min_dist_origen, 2),
        distancia_ultima_parada_destino_metros=round(min_dist_destino, 2),
        paradas_trayecto=paradas_trayecto_data
    )