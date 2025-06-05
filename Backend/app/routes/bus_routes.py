from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db_connection
from app.models.entities import RutaUsuario, Ubicacion, UbicacionTemporal
from app.services.bus_tracking import calcular_buses
from datetime import datetime

router = APIRouter()

@router.post("/update_location")
def update_location(user_id: int, ruta_id: int, latitude: float, longitude: float, db: Session = Depends(get_db_connection)):
    """
    Guarda la ubicación del usuario en la base de datos y actualiza el estado de abordo.
    """
    ubicacion = Ubicacion(latitud=latitude, longitud=longitude)
    db.add(ubicacion)
    db.commit()
    
    user_tracking = db.query(RutaUsuario).filter(RutaUsuario.id_usuario == user_id, RutaUsuario.id_ruta == ruta_id).first()

    if user_tracking:
        user_tracking.abordo = True
        user_tracking.ultima_actualizacion = datetime.utcnow()
    else:
        user_tracking = RutaUsuario(id_usuario=user_id, id_ruta=ruta_id, abordo=True, ultima_actualizacion=datetime.utcnow())

    db.add(user_tracking)
    db.commit()

    return {"message": "Ubicación actualizada correctamente"}

@router.get("/get_buses/{ruta_id}")
def obtener_buses(ruta_id: int, db: Session = Depends(get_db_connection)):
    """
    Devuelve los buses virtuales en la ruta especificada.
    """
    buses = calcular_buses(db)
    return buses

@router.post("/check_exit")
def verificar_bajada(user_id: int, ruta_id: int, latitude: float, longitude: float, db: Session = Depends(get_db_connection)):
    """
    Verifica si el usuario se ha alejado del grupo y lo marca como 'fuera del bus'.
    """
    user = db.query(RutaUsuario).filter(RutaUsuario.id_usuario == user_id, RutaUsuario.id_ruta == ruta_id).first()
    
    if user:
        bus = db.query(UbicacionTemporal).filter(UbicacionTemporal.idruta == ruta_id).first()
        if bus:
            distancia = ((bus.bus.latitud - latitude) ** 2 + (bus.bus.longitud - longitude) ** 2) ** 0.5
            if distancia > 0.05:  # Si la distancia supera 50 metros
                user.abordo = False
                db.commit()
                return {"message": "Usuario se bajó del bus"}
    
    return {"message": "Usuario sigue en el bus"}
