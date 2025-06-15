# app/rutas/bus_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import RutaUsuario, UbicacionUsuario, UbicacionTemporal, Ruta, UsuarioRutaActual, Parada
from app.services.bus_tracking import _get_or_create_ubicacion_usuario, check_user_location_status, run_bus_tracking_periodically
from app.services.route_calculation import calcular_trayecto_usuario
from datetime import datetime

# --- ¡NUEVA IMPORTACIÓN DE ESQUEMAS! ---
from app.models.models import (
    UserLocationUpdate,
    CheckExitRequest,
    SelectRouteRequest,
    SetNextStopRequest,
    CalculateRouteRequest,
    BusLocationResponse, # Si decides usarla como response_model
    CalculateRouteResponse # Si decides usarla como response_model
)

router = APIRouter()
# --- Configuración para la tarea de fondo de cálculo de buses (Recordatorio) ---
# Este bloque no va en este archivo, sino en tu `main.py` de FastAPI.
# Es un recordatorio de cómo iniciar el hilo para `run_bus_tracking_periodically`.
"""
Ejemplo de cómo iniciar la tarea de fondo en tu main.py:

from threading import Thread
import time 

# ... tus imports de FastAPI, routers, get_db, etc.

@app.on_event("startup")
async def startup_event():
    print("Iniciando tarea de cálculo de buses en segundo plano...")
    background_thread = Thread(target=run_bus_tracking_periodically, args=(get_db,))
    background_thread.daemon = True 
    background_thread.start()
    print("Tarea de cálculo de buses iniciada.")

"""
# Fin del ejemplo de configuración de tarea de fondo.


@router.post("/update_location", status_code=status.HTTP_200_OK)
def update_location(data: UserLocationUpdate, db: Session = Depends(get_db)):    
    """
    Guarda la ubicación del usuario y actualiza su estado.
    """
    _get_or_create_ubicacion_usuario(db, data.user_id, data.latitude, data.longitude)

    user_tracking = db.query(RutaUsuario).filter(RutaUsuario.id_usuario == data.user_id, RutaUsuario.id_ruta == data.ruta_id).first()
    if user_tracking:
        user_tracking.ultima_actualizacion = datetime.utcnow()
    else:
        user_tracking = RutaUsuario(id_usuario=data.user_id, id_ruta=data.ruta_id, abordo=False, ultima_actualizacion=datetime.utcnow())
        db.add(user_tracking)
    
    user_current_route = db.query(UsuarioRutaActual).filter(UsuarioRutaActual.user_id == data.user_id).first()
    if user_current_route:
        user_current_route.ruta_seleccionada_id = data.ruta_id
    else:
        user_current_route = UsuarioRutaActual(user_id=data.user_id, ruta_seleccionada_id=data.ruta_id)
        db.add(user_current_route)
    
    db.commit() 
    
    status_info = check_user_location_status(db, data.user_id, data.latitude, data.longitude)

    return {"message": "Ubicación actualizada correctamente y estado verificado.", "status": status_info}



@router.get("/get_buses/{ruta_id}", status_code=status.HTTP_200_OK)
def obtener_buses(ruta_id: int, db: Session = Depends(get_db)):
    """
    Devuelve los buses virtuales actuales para la ruta especificada.
    """
    buses_temp = db.query(UbicacionTemporal).filter(UbicacionTemporal.idruta == ruta_id).all()
    
    buses_data = []
    for bus in buses_temp:
        buses_data.append({
            "bus_uuid": bus.idbus,
            "ruta_id": bus.idruta,
            "latitude": bus.latitud,
            "longitude": bus.longitud,
            "velocidad": bus.velocidad,
            "estado": bus.estado,
            "ultima_actualizacion": bus.ultima_actualizacion.isoformat() if bus.ultima_actualizacion else None
        })
    return buses_data



@router.post("/check_exit", status_code=status.HTTP_200_OK)
def verificar_bajada_endpoint(data: CheckExitRequest, db: Session = Depends(get_db)):
    """
    Este endpoint permite una verificación explícita de si un usuario se ha bajado.
    """
    status_info = check_user_location_status(db, data.user_id, data.latitude, data.longitude)
    return status_info



@router.post("/select_route", status_code=status.HTTP_200_OK)
def select_route_for_user(request: SelectRouteRequest, db: Session = Depends(get_db)):
    """
    Permite a un usuario seleccionar la ruta que va a tomar.
    """
    user_route = db.query(UsuarioRutaActual).filter(UsuarioRutaActual.user_id == request.user_id).first()
    if user_route:
        user_route.ruta_seleccionada_id = request.ruta_id
    else:
        user_route = UsuarioRutaActual(user_id=request.user_id, ruta_seleccionada_id=request.ruta_id)
        db.add(user_route)
    db.commit()
    db.refresh(user_route) 
    return {"message": f"Ruta {request.ruta_id} seleccionada para el usuario {request.user_id}"}



@router.post("/set_next_stop", status_code=status.HTTP_200_OK)
def set_next_stop_for_user(request: SetNextStopRequest, db: Session = Depends(get_db)):
    """
    Permite a un usuario indicar la próxima parada donde planea bajarse.
    La verificación de si la parada pertenece a la ruta se implementará más adelante.
    """
    user_route_info = db.query(UsuarioRutaActual).filter(UsuarioRutaActual.user_id == request.user_id).first()
    
    if not user_route_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no ha seleccionado una ruta aún. Por favor, seleccione una ruta primero."
        )
    
    # --- Lógica de verificación de parada en ruta (deshabilitada por ahora) ---
    # Esto se puede habilitar una vez que la lógica de cálculo de ruta esté lista.
    # if not user_route_info.ruta_seleccionada_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="El usuario no tiene una ruta seleccionada. Seleccione una ruta antes de establecer una parada."
    #     )
    #
    # from app.models.entities import RutaParada # Necesitarías importar RutaParada aquí si no está arriba
    # parada_en_ruta = db.query(RutaParada).filter(
    #     RutaParada.ruta_id == user_route_info.ruta_seleccionada_id, 
    #     RutaParada.parada_id == request.parada_id
    # ).first()
    #
    # if not parada_en_ruta:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="La parada seleccionada no pertenece a la ruta activa del usuario."
    #     )
    # --- FIN Lógica de verificación ---

    user_route_info.proxima_parada_id = request.parada_id
    db.commit()
    db.refresh(user_route_info)
    return {"message": f"Próxima parada {request.parada_id} establecida para el usuario {request.user_id}"}

# --- NUEVO ENDPOINT para calcular la ruta ---
@router.post("/calculate_route", status_code=status.HTTP_200_OK)
def calculate_user_route(request: CalculateRouteRequest, db: Session = Depends(get_db)):
    """
    Calcula el trayecto más adecuado para el usuario entre dos puntos geográficos.
    """
    try:
        suggested_route = calcular_trayecto_usuario(
            db,
            request.origen_lat,
            request.origen_lon,
            request.destino_lat,
            request.destino_lon
        )
        if suggested_route and suggested_route.get("ruta_sugerida"):
            return suggested_route
        elif suggested_route: # Si hay mensaje pero no ruta sugerida directa (ej. rutas alternativas)
            return suggested_route
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se pudo calcular una ruta para las ubicaciones proporcionadas."
            )
    except Exception as e:
        print(f"Error al calcular la ruta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al calcular la ruta: {e}"
        )

@router.post("/calculate_route", status_code=status.HTTP_200_OK, response_model=CalculateRouteResponse) # <--- Asegúrate de que response_model esté actualizado
def calculate_user_route(request: CalculateRouteRequest, db: Session = Depends(get_db)):
    """
    Calcula el trayecto más adecuado para el usuario entre dos puntos geográficos.
    """
    try:
        # calcular_trayecto_usuario ya devuelve el formato que necesitamos para CalculateRouteResponse
        suggested_route_data = calcular_trayecto_usuario(
            db,
            request.origen_lat,
            request.origen_lon,
            request.destino_lat,
            request.destino_lon
        )
        # La función ya devuelve un diccionario que coincide con CalculateRouteResponse
        # No necesitamos Raise HTTPException aquí si el servicio ya maneja los mensajes de no encontrado.
        # Solo lo hacemos si el servicio devuelve None para un error inesperado
        if suggested_route_data is None:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El servicio de cálculo de ruta devolvió un resultado nulo."
            )
        return suggested_route_data
    except Exception as e:
        print(f"Error al calcular la ruta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al calcular la ruta: {e}"
        )