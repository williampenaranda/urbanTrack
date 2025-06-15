from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Optional

from app.models.entities import Ruta, RutaParada, Parada
from geoalchemy2.shape import to_shape 


def get_all_routes(db: Session) -> List[Dict]:
    """
    Obtiene todas las rutas de Transcaribe con sus detalles, incluyendo las paradas asociadas,
    utilizando carga ansiosa para optimizar el rendimiento.
    """
    routes_data = []

    # Elimina el .join(Ruta.paradas) porque joinedload ya se encarga de la unión
    # y el ordenamiento de la tabla intermedia será en Python.
    rutas = db.query(Ruta).options(
        joinedload(Ruta.paradas).joinedload(RutaParada.parada)
    ).order_by(Ruta.id).all() # <-- CAMBIO AQUI: Solo ordena por Ruta.id

    for ruta in rutas:
        paradas_en_ruta = []
        # Aquí, las `ruta.paradas` ya están cargadas por `joinedload`.
        # Las ordenamos en Python usando el atributo 'orden' de cada objeto RutaParada.
        for rp in sorted(ruta.paradas, key=lambda x: x.orden):
            parada = rp.parada # La parada ya está precargada a través de la relación.
            if parada:
                ubicacion_coords = None
                if parada.ubicacion:
                    point = to_shape(parada.ubicacion)
                    ubicacion_coords = {"latitude": point.y, "longitude": point.x}

                paradas_en_ruta.append({
                    "id": parada.id,
                    "nombre": parada.nombre,
                    "codigo": str(parada.id),
                    "ubicacion": ubicacion_coords,
                    "orden_en_ruta": rp.orden
                })
        
        routes_data.append({
            "id": ruta.id,
            "nombre": ruta.nombre,
            "paradas": paradas_en_ruta
        })
            
    return routes_data


def get_route_by_id(db: Session, route_id: int) -> Optional[Dict]:
    """
    Busca una ruta específica de Transcaribe por su ID y retorna sus detalles, incluyendo las paradas,
    utilizando carga ansiosa para optimizar el rendimiento.
    """
    ruta = (
        db.query(Ruta)
        .filter(Ruta.id == route_id)
        .options(
            joinedload(Ruta.paradas).joinedload(RutaParada.parada)
        )
        .first()
    )

    if not ruta:
        return None

    paradas_en_ruta = []
    # Aquí también ordenamos en Python.
    for rp in sorted(ruta.paradas, key=lambda x: x.orden):
        parada = rp.parada 
        if parada:
            ubicacion_coords = None
            if parada.ubicacion:
                point = to_shape(parada.ubicacion)
                ubicacion_coords = {"latitude": point.y, "longitude": point.x}

            paradas_en_ruta.append({
                "id": parada.id,
                "nombre": parada.nombre,
                "codigo": str(parada.id),
                "ubicacion": ubicacion_coords,
                "orden_en_ruta": rp.orden
            })
    
    route_data = {
        "id": ruta.id,
        "nombre": ruta.nombre,
        "paradas": paradas_en_ruta
    }
        
    return route_data