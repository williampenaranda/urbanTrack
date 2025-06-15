# app/services/route_calculation.py
from sqlalchemy.orm import Session
from sqlalchemy import func
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

# --- Funciones Auxiliares ---

def _get_distance_between_points(db: Session, lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """
    Calcula la distancia esférica en metros entre dos puntos geográficos usando PostGIS.
    """
    distance = db.query(
        func.ST_Distance_Sphere(
            func.ST_MakePoint(lon1, lat1),
            func.ST_MakePoint(lon2, lat2)
        )
    ).scalar()
    return distance

def _build_transport_graph(db: Session) -> Dict[int, List[Dict]]:
    """
    Construye un grafo de transporte a partir de las rutas y paradas de la base de datos.
    El grafo: {parada_id: [{"neighbor": parada_id, "cost": segundos, "ruta_id": id, "is_transfer": False/True}]}
    """
    graph: Dict[int, List[Dict]] = {}
    paradas = db.query(Parada).all()
    rutas = db.query(Ruta).all()
    rutas_paradas = db.query(RutaParada).order_by(RutaParada.ruta_id, RutaParada.orden).all()

    # Mapear ID de parada a objeto parada para fácil acceso a ubicación
    paradas_map = {p.id: p for p in paradas}

    # 1. Añadir aristas intra-ruta (viajes en el mismo bus)
    rutas_paradas_map: Dict[int, List[RutaParada]] = {}
    for rp in rutas_paradas:
        if rp.ruta_id not in rutas_paradas_map:
            rutas_paradas_map[rp.ruta_id] = []
        rutas_paradas_map[rp.ruta_id].append(rp)

    for ruta_id, rps in rutas_paradas_map.items():
        # Asegurarse de que las paradas estén ordenadas
        sorted_rps = sorted(rps, key=lambda x: x.orden)
        
        for i in range(len(sorted_rps) - 1):
            parada_actual_rp = sorted_rps[i]
            parada_siguiente_rp = sorted_rps[i+1]

            parada_actual_obj = paradas_map.get(parada_actual_rp.parada_id)
            parada_siguiente_obj = paradas_map.get(parada_siguiente_rp.parada_id)

            if not parada_actual_obj or not parada_siguiente_obj:
                continue

            dist = _get_distance_between_points(
                db,
                func.ST_Y(parada_actual_obj.ubicacion), func.ST_X(parada_actual_obj.ubicacion),
                func.ST_Y(parada_siguiente_obj.ubicacion), func.ST_X(parada_siguiente_obj.ubicacion)
            )

            if dist is None or dist == 0:
                cost = 1 # Pequeño costo para evitar división por cero o rutas estáticas
            else:
                cost = dist / DEFAULT_BUS_SPEED_MPS # Tiempo en segundos

            if parada_actual_obj.id not in graph:
                graph[parada_actual_obj.id] = []
            if parada_siguiente_obj.id not in graph:
                graph[parada_siguiente_obj.id] = []
            
            # Añadir arista unidireccional
            graph[parada_actual_obj.id].append({
                "neighbor": parada_siguiente_obj.id,
                "cost": cost,
                "ruta_id": ruta_id,
                "is_transfer": False
            })

    # 2. Añadir aristas de transbordo
    # Agrupar rutas por parada para encontrar puntos de transbordo
    paradas_con_rutas: Dict[int, List[int]] = {} # {parada_id: [ruta_id, ...]}
    for rp in rutas_paradas:
        if rp.parada_id not in paradas_con_rutas:
            paradas_con_rutas[rp.parada_id] = set()
        paradas_con_rutas[rp.parada_id].add(rp.ruta_id)
    
    for parada_id, rutas_en_parada in paradas_con_rutas.items():
        if len(rutas_en_parada) > 1: # Si más de una ruta pasa por esta parada, es un punto de transbordo
            # Crear una "arista virtual" de transbordo que se conecta a sí misma con penalización
            # Es decir, si estoy en la parada X y quiero cambiar de ruta, el costo de "cambiar" en la parada X es la penalización
            # Esto se modela mejor en Dijkstra como un costo de llegar a la parada X con una ruta, y luego considerar la salida con otra.
            # Para simplificar la construcción del grafo, podemos pensar en un costo si el algoritmo de Dijkstra
            # decide cambiar de ruta en un nodo (parada). Dijkstra mismo lo maneja implícitamente si se pasa
            # información de la ruta actual en el estado.

            # Una forma más explícita para Dijkstra es tener estados (nodo, ruta_actual)
            # Pero para el grafo simple (nodo a nodo), la penalización se aplica *cuando se elige una nueva ruta*
            # desde una parada de transbordo.
            
            # Por ahora, nos aseguramos de que el grafo tenga el nodo para futuros cálculos de Dijkstra
            if parada_id not in graph:
                graph[parada_id] = []

    return graph


def _dijkstra(graph: Dict[int, List[Dict]], start_node: int, end_node: int) -> Optional[List[Dict]]:
    """
    Implementación del algoritmo de Dijkstra para encontrar el camino más corto.
    Retorna una lista de segmentos de ruta o None si no hay camino.
    Cada segmento: {"from_parada_id": X, "to_parada_id": Y, "ruta_id": Z, "is_transfer": False/True, "cost": segundos}
    """
    distances = {node: float('inf') for node in graph}
    # predecessors guarda (costo_total, nodo_previo, ruta_que_llevo_aqui, es_transfer)
    predecessors: Dict[int, Tuple[float, Optional[int], Optional[int], Optional[bool]]] = {node: (float('inf'), None, None, None) for node in graph}
    
    # Cola de prioridad: (costo_acumulado, nodo_actual, ruta_actual_id, es_transbordo_previo)
    priority_queue = [(0, start_node, None, False)] # costo, nodo_actual, ruta_id que trajo al nodo_actual, ¿fue transbordo para llegar aquí?
    distances[start_node] = 0

    path_details: Dict[int, Tuple[int, int, bool, float]] = {} # {nodo_actual: (prev_node, ruta_id, is_transfer, cost_to_get_here)}

    while priority_queue:
        current_cost, current_node, current_route_id, was_transfer_to_node = heapq.heappop(priority_queue)

        if current_cost > distances[current_node]:
            continue

        if current_node == end_node:
            break

        for edge in graph.get(current_node, []):
            neighbor = edge["neighbor"]
            edge_cost = edge["cost"]
            edge_ruta_id = edge["ruta_id"]
            edge_is_transfer = edge["is_transfer"]

            cost_to_neighbor = current_cost + edge_cost

            # Lógica de penalización de transbordo:
            # Si el borde que estamos evaluando pertenece a una ruta diferente a la ruta actual del pasajero,
            # aplicamos la penalización de transbordo.
            # No aplicamos penalización si es el primer segmento del viaje (current_route_id is None)
            # o si la ruta es la misma que la anterior.
            if current_route_id is not None and edge_ruta_id != current_route_id and not edge_is_transfer:
                cost_to_neighbor += TRANSFER_PENALTY_SECONDS # Aplicar penalización solo al cambiar de ruta real de bus

            if cost_to_neighbor < distances[neighbor]:
                distances[neighbor] = cost_to_neighbor
                predecessors[neighbor] = (cost_to_neighbor, current_node, edge_ruta_id, edge_is_transfer)
                heapq.heappush(priority_queue, (cost_to_neighbor, neighbor, edge_ruta_id, edge_is_transfer))
                # Guardar detalles para reconstruir el camino con información de ruta y transbordo
                path_details[neighbor] = (current_node, edge_ruta_id, edge_is_transfer, edge_cost)


    if distances[end_node] == float('inf'):
        return None # No se encontró un camino

    # Reconstruir el camino y sus detalles
    path = []
    current = end_node
    while current != start_node:
        if current not in path_details:
            # Esto puede ocurrir si el start_node no está en path_details, es el inicio.
            break
        prev_node, ruta_id, is_transfer_segment, segment_cost = path_details[current]
        
        # Determine if a transfer *just happened* before this segment started
        # This is tricky with simple node-to-node Dijkstra.
        # The penalty was applied when evaluating 'cost_to_neighbor'.
        # We need to explicitly mark a segment as a 'transfer' if the route_id changed.
        
        # Let's rebuild based on predecessors' ruta_id
        prev_ruta_id_in_predecessor_data = predecessors[prev_node][2] if predecessors[prev_node][1] is not None else None
        
        # If the route changed from the previous segment to the current segment
        # and it's not the very first segment, it's a transfer point.
        transfer_occurred_here = False
        if prev_ruta_id_in_predecessor_data is not None and ruta_id != prev_ruta_id_in_predecessor_data:
             transfer_occurred_here = True
        
        # Add the segment (reversed for path reconstruction)
        path.insert(0, {
            "from_parada_id": prev_node,
            "to_parada_id": current,
            "ruta_id": ruta_id,
            "is_transfer": transfer_occurred_here, # Mark as transfer if route changed
            "cost_seconds": segment_cost # Cost of traversing *this segment*
        })
        current = prev_node

    # Add estimated total time to the path (useful for frontend)
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
    
    # 1. Identificar la parada de origen más cercana
    paradas = db.query(Parada).all()
    parada_origen_cercana: Optional[Parada] = None
    min_dist_origen = float('inf')

    for parada in paradas:
        dist = _get_distance_between_points(
            db, origen_lat, origen_lon,
            func.ST_Y(parada.ubicacion), func.ST_X(parada.ubicacion)
        )
        if dist is not None and dist < min_dist_origen:
            min_dist_origen = dist
            parada_origen_cercana = parada

    if not parada_origen_cercana or min_dist_origen > MAX_DISTANCE_TO_STOP_METERS:
        return {"message": "No se encontró una parada de origen suficientemente cercana (Max 300m).", "ruta_sugerida": None}

    # 2. Identificar la parada de destino más cercana
    parada_destino_cercana: Optional[Parada] = None
    min_dist_destino = float('inf')

    for parada in paradas:
        dist = _get_distance_between_points(
            db, destino_lat, destino_lon,
            func.ST_Y(parada.ubicacion), func.ST_X(parada.ubicacion)
        )
        if dist is not None and dist < min_dist_destino:
            min_dist_destino = dist
            parada_destino_cercana = parada
    
    if not parada_destino_cercana or min_dist_destino > MAX_DISTANCE_TO_STOP_METERS:
        return {"message": "No se encontró una parada de destino suficientemente cercana (Max 300m).", "ruta_sugerida": None}

    print(f"Parada de origen más cercana: {parada_origen_cercana.nombre} (ID: {parada_origen_cercana.id}) a {min_dist_origen:.2f}m")
    print(f"Parada de destino más cercana: {parada_destino_cercana.nombre} (ID: {parada_destino_cercana.id}) a {min_dist_destino:.2f}m")

    # 3. Construir el grafo de transporte
    graph = _build_transport_graph(db)

    # Asegurarse de que las paradas de origen y destino existan en el grafo
    if parada_origen_cercana.id not in graph or parada_destino_cercana.id not in graph:
        return {"message": "Una o ambas paradas (origen/destino) no están conectadas en el grafo de rutas. Asegúrese que las rutas tienen al menos 2 paradas.", "ruta_sugerida": None}


    # 4. Ejecutar el algoritmo de Dijkstra
    dijkstra_result = _dijkstra(graph, parada_origen_cercana.id, parada_destino_cercana.id)

    if not dijkstra_result:
        return {
            "message": "No se encontró un camino entre las paradas de origen y destino sugeridas.",
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

    # 5. Formatear la salida del algoritmo de Dijkstra
    path_segments = dijkstra_result["path_segments"]
    total_time_seconds = dijkstra_result["total_time_seconds"]

    # Reconstruir la ruta sugerida en un formato legible
    ruta_reconstruida = []
    current_ruta_id = None
    segment_count = 0
    
    # Para obtener el nombre de la ruta y de las paradas
    rutas_map = {r.id: r.nombre for r in db.query(Ruta).all()}
    paradas_map = {p.id: p.nombre for p in db.query(Parada).all()}

    for i, segment in enumerate(path_segments):
        from_parada_id = segment["from_parada_id"]
        to_parada_id = segment["to_parada_id"]
        segment_ruta_id = segment["ruta_id"]
        cost_seconds = segment["cost_seconds"]

        # Determinar si hay transbordo en este punto
        is_transfer_segment = False
        if current_ruta_id is not None and segment_ruta_id != current_ruta_id:
            is_transfer_segment = True
            ruta_reconstruida.append({
                "tipo": "TRANSBORDO",
                "desde_parada": paradas_map.get(from_parada_id, "Desconocida"),
                "hacia_ruta": rutas_map.get(segment_ruta_id, "Desconocida"),
                "costo_segundos": TRANSFER_PENALTY_SECONDS,
                "descripcion": f"Cambia de ruta en {paradas_map.get(from_parada_id, 'Desconocida')} (Penalización de {TRANSFER_PENALTY_MINUTES} min)"
            })
        
        ruta_reconstruida.append({
            "tipo": "VIAJE_EN_BUS",
            "ruta_id": segment_ruta_id,
            "ruta_nombre": rutas_map.get(segment_ruta_id, "Desconocida"),
            "desde_parada_id": from_parada_id,
            "desde_parada_nombre": paradas_map.get(from_parada_id, "Desconocida"),
            "hasta_parada_id": to_parada_id,
            "hasta_parada_nombre": paradas_map.get(to_parada_id, "Desconocida"),
            "costo_segundos": cost_seconds,
            "descripcion": f"Toma Ruta '{rutas_map.get(segment_ruta_id, 'Desconocida')}' de '{paradas_map.get(from_parada_id, 'Desconocida')}' a '{paradas_map.get(to_parada_id, 'Desconocida')}'"
        })
        current_ruta_id = segment_ruta_id
        segment_count += 1

    return {
        "message": "Ruta más eficiente encontrada.",
        "ruta_sugerida": {
            "parada_origen_sugerida": {
                "id": parada_origen_cercana.id,
                "nombre": parada_origen_cercana.nombre,
                "distancia_origen_usuario_metros": min_dist_origen
            },
            "parada_destino_sugerida": {
                "id": parada_destino_cercana.id,
                "nombre": parada_destino_cercana.nombre,
                "distancia_destino_usuario_metros": min_dist_destino
            },
            "total_tiempo_estimado_segundos": total_time_seconds,
            "total_tiempo_estimado_formato": str(timedelta(seconds=int(total_time_seconds))),
            "segmentos_trayecto": ruta_reconstruida
        }
    }