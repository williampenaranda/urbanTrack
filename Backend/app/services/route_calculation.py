from sqlalchemy.orm import Session
from sqlalchemy import func, cast, and_ # Importa 'cast' y 'and_'
from sqlalchemy.sql import alias
# Importaciones necesarias para trabajar con geometrías en SQLAlchemy y PostGIS
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID, ST_Distance
from geoalchemy2.types import Geography
from geoalchemy2.shape import to_shape # Para convertir de Geometry a Shapely Point

from app.models.entities import Ruta, Parada, RutaParada
from typing import List, Dict, Optional, Tuple
import heapq # Para la cola de prioridad de Dijkstra
from datetime import timedelta # Para manejar tiempos


# --- Constantes de Configuración del Algoritmo ---
DEFAULT_BUS_SPEED_KPH = 20 # Velocidad promedio del bus en km/h
DEFAULT_BUS_SPEED_MPS = DEFAULT_BUS_SPEED_KPH * 1000 / 3600 # Convertir a metros por segundo

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
        if to_parada_id not in graph:
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
    paradas_con_rutas: Dict[int, List[int]] = {}
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
    
    # predecessors guarda (costo_total, nodo_previo, ruta_id_del_segmento_que_llego_a_actual_node)
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
    last_segment_ruta_id = None 

    while current != start_node:
        prev_node, segment_ruta_id = predecessors[current]
        
        if prev_node is None: # Se llegó al nodo de inicio o hay un problema
            break

        # Determinar si este segmento representa un transbordo (cambio de ruta)
        # Esto ocurre si la ruta del segmento actual es diferente a la ruta del segmento anterior
        # (si existe) O si es el primer segmento del camino (no hay ruta anterior)
        transfer_occurred_here = False
        if last_segment_ruta_id is not None and segment_ruta_id != last_segment_ruta_id:
            transfer_occurred_here = True
        
        path.insert(0, {
            "from_parada_id": prev_node,
            "to_parada_id": current,
            "ruta_id": segment_ruta_id,
            "is_transfer": transfer_occurred_here,
            "cost_seconds": distances[current] - distances[prev_node] # El costo real de este segmento
        })
        last_segment_ruta_id = segment_ruta_id # Actualizar para la siguiente iteración
        current = prev_node

    total_time_seconds = distances[end_node]
    return {"path_segments": path, "total_time_seconds": total_time_seconds}


# --- Función Principal de Cálculo de Trayecto ---

def calcular_trayecto_usuario(
    db: Session,
    origen_lat: float,
    origen_lon: float,
    destino_lat: float,
    destino_lon: float
) -> Optional[Dict]:
    """
    Calcula el trayecto más eficiente (en tiempo) para el usuario
    desde una ubicación de origen a una ubicación de destino,
    priorizando rutas directas con penalización por transbordo.
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
        return {"message": "No se encontró una parada de origen suficientemente cercana (Max 300m).", "ruta_sugerida": None}
    
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
        return {"message": "No se encontró una parada de destino suficientemente cercana (Max 300m).", "ruta_sugerida": None}
    
    parada_destino_cercana, min_dist_destino = parada_destino_cercana_result

    print(f"Parada de origen más cercana: {parada_origen_cercana.nombre} (ID: {parada_origen_cercana.id}) a {min_dist_origen:.2f}m")
    print(f"Parada de destino más cercana: {parada_destino_cercana.nombre} (ID: {parada_destino_cercana.id}) a {min_dist_destino:.2f}m")

    # 3. Construir el grafo de transporte (AHORA MUCHO MÁS EFICIENTE)
    graph = _build_transport_graph(db)

    # Asegurarse de que las paradas de origen y destino existan en el grafo
    # Esto es importante si una parada no tiene segmentos de ruta salientes/entrantes definidos,
    # pero sí puede ser un punto de transbordo (ej. una parada final/inicial de una ruta)
    if parada_origen_cercana.id not in graph or parada_destino_cercana.id not in graph:
        return {
            "message": "Una o ambas paradas (origen/destino) no están conectadas en el grafo de rutas. Asegúrese que las rutas tienen al menos 2 paradas o son puntos de transbordo.",
            "ruta_sugerida": None,
            "parada_origen_sugerida": {
                "id": parada_origen_cercana.id,
                "nombre": parada_origen_cercana.nombre,
                "distancia_origen_usuario_metros": min_dist_origen
            },
            "parada_destino_sugerida": {
                "id": parada_destino_cercana.id,
                "nombre": parada_destino_cercana.nombre,
                "distancia_destino_usuario_metros": min_dist_destino
            }
        }

    # 4. Ejecutar el algoritmo de Dijkstra
    dijkstra_result = _dijkstra(graph, parada_origen_cercana.id, parada_destino_cercana.id)

    if not dijkstra_result:
        # Prepara los datos de las paradas sugeridas para la respuesta
        parada_origen_sugerida_response = {
            "id": parada_origen_cercana.id,
            "nombre": parada_origen_cercana.nombre,
            "ubicacion": {
                "latitude": to_shape(parada_origen_cercana.ubicacion).y,
                "longitude": to_shape(parada_origen_cercana.ubicacion).x
            } if parada_origen_cercana.ubicacion else None,
            "distancia_origen_usuario_metros": min_dist_origen
        }

        parada_destino_sugerida_response = {
            "id": parada_destino_cercana.id,
            "nombre": parada_destino_cercana.nombre,
            "ubicacion": {
                "latitude": to_shape(parada_destino_cercana.ubicacion).y,
                "longitude": to_shape(parada_destino_cercana.ubicacion).x
            } if parada_destino_cercana.ubicacion else None,
            "distancia_destino_usuario_metros": min_dist_destino
        }

        return {
            "message": "No se encontró un camino entre las paradas de origen y destino sugeridas.",
            "ruta_sugerida": None,
            "parada_origen_sugerida": parada_origen_sugerida_response,
            "parada_destino_sugerida": parada_destino_sugerida_response
        }

    # 5. Formatear la salida del algoritmo de Dijkstra
    path_segments = dijkstra_result["path_segments"]
    total_time_seconds = dijkstra_result["total_time_seconds"]

    # Reconstruir la ruta sugerida en un formato legible
    ruta_reconstruida = []
    
    # Para obtener el nombre de la ruta y de las paradas
    rutas_map = {r.id: r.nombre for r in db.query(Ruta).all()}
    paradas_map = {p.id: p.nombre for p in db.query(Parada).all()}
    paradas_ubicacion_map = {p.id: to_shape(p.ubicacion) for p in db.query(Parada).all()}

    # Guardar la ruta_id del segmento anterior para detectar transbordos
    previous_segment_ruta_id = None

    for i, segment in enumerate(path_segments):
        from_parada_id = segment["from_parada_id"]
        to_parada_id = segment["to_parada_id"]
        segment_ruta_id = segment["ruta_id"]
        cost_seconds = segment["cost_seconds"] 

        # Determinar si hay transbordo en este punto
        is_transfer_segment = False
        if previous_segment_ruta_id is not None and segment_ruta_id != previous_segment_ruta_id:
            is_transfer_segment = True
            # Añadir el segmento de transbordo explícito
            ruta_reconstruida.append({
                "tipo": "TRANSBORDO",
                "ruta_id": None, # No hay ruta específica para el segmento de transbordo
                "ruta_nombre": None,
                "desde_parada_id": from_parada_id,
                "desde_parada_nombre": paradas_map.get(from_parada_id, "Desconocida"),
                "desde_parada_ubicacion": {
                    "latitude": paradas_ubicacion_map.get(from_parada_id).y,
                    "longitude": paradas_ubicacion_map.get(from_parada_id).x
                } if paradas_ubicacion_map.get(from_parada_id) else None,
                "hasta_parada_id": from_parada_id, # La parada donde ocurre el transbordo
                "hasta_parada_nombre": paradas_map.get(from_parada_id, "Desconocida"),
                "hasta_parada_ubicacion": {
                    "latitude": paradas_ubicacion_map.get(from_parada_id).y,
                    "longitude": paradas_ubicacion_map.get(from_parada_id).x
                } if paradas_ubicacion_map.get(from_parada_id) else None,
                "costo_segundos": TRANSFER_PENALTY_SECONDS,
                "descripcion": f"Cambia de ruta en {paradas_map.get(from_parada_id, 'Desconocida')} (Penalización de {TRANSFER_PENALTY_MINUTES} min)",
                "hacia_ruta": rutas_map.get(segment_ruta_id, "Desconocida") # La ruta a la que se transborda
            })
        
        # Añadir el segmento de viaje en bus
        ruta_reconstruida.append({
            "tipo": "VIAJE_EN_BUS",
            "ruta_id": segment_ruta_id,
            "ruta_nombre": rutas_map.get(segment_ruta_id, "Desconocida"),
            "desde_parada_id": from_parada_id,
            "desde_parada_nombre": paradas_map.get(from_parada_id, "Desconocida"),
            "desde_parada_ubicacion": {
                "latitude": paradas_ubicacion_map.get(from_parada_id).y,
                "longitude": paradas_ubicacion_map.get(from_parada_id).x
            } if paradas_ubicacion_map.get(from_parada_id) else None,
            "hasta_parada_id": to_parada_id,
            "hasta_parada_nombre": paradas_map.get(to_parada_id, "Desconocida"),
            "hasta_parada_ubicacion": {
                "latitude": paradas_ubicacion_map.get(to_parada_id).y,
                "longitude": paradas_ubicacion_map.get(to_parada_id).x
            } if paradas_ubicacion_map.get(to_parada_id) else None,
            "costo_segundos": cost_seconds,
            "descripcion": f"Toma Ruta '{rutas_map.get(segment_ruta_id, 'Desconocida')}' de '{paradas_map.get(from_parada_id, 'Desconocida')}' a '{paradas_map.get(to_parada_id, 'Desconocida')}'"
        })
        previous_segment_ruta_id = segment_ruta_id
    
    # Prepara los datos de las paradas sugeridas para la respuesta (ahora que las tenemos del query optimizado)
    parada_origen_sugerida_response = {
        "id": parada_origen_cercana.id,
        "nombre": parada_origen_cercana.nombre,
        "ubicacion": {
            "latitude": to_shape(parada_origen_cercana.ubicacion).y,
            "longitude": to_shape(parada_origen_cercana.ubicacion).x
        } if parada_origen_cercana.ubicacion else None,
        "distancia_origen_usuario_metros": min_dist_origen
    }

    parada_destino_sugerida_response = {
        "id": parada_destino_cercana.id,
        "nombre": parada_destino_cercana.nombre,
        "ubicacion": {
            "latitude": to_shape(parada_destino_cercana.ubicacion).y,
            "longitude": to_shape(parada_destino_cercana.ubicacion).x
        } if parada_destino_cercana.ubicacion else None,
        "distancia_destino_usuario_metros": min_dist_destino
    }

    return {
        "message": "Ruta más eficiente encontrada.",
        "ruta_sugerida": {
            "parada_origen_sugerida": parada_origen_sugerida_response,
            "parada_destino_sugerida": parada_destino_sugerida_response,
            "total_tiempo_estimado_segundos": total_time_seconds,
            "total_tiempo_estimado_formato": str(timedelta(seconds=int(total_time_seconds))),
            "segmentos_trayecto": ruta_reconstruida
        }
    }