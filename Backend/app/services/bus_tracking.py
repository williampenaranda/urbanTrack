from sqlalchemy.orm import Session
from sqlalchemy import func # Necesario para funciones SQL como ST_Distance_Sphere
from app.models.entities import RutaUsuario, UbicacionTemporal, UbicacionUsuario, Parada, UsuarioRutaActual
from datetime import datetime
import uuid
import time # Para la tarea de fondo (sleep)
# Si necesitas acceder a las coordenadas de Parada.ubicacion en Python, usarías esto:
# from geoalchemy2.shape import to_shape
# from shapely.geometry import Point


# --- Constantes de Configuración ---
# Puedes mover estas constantes a un archivo de configuración (ej. config.py) en el futuro.
PROXIMIDAD_USUARIO_PARADA_METROS = 50   # Distancia en metros para considerar que un usuario está en una parada
PROXIMIDAD_USUARIO_BUS_METROS = 100    # Distancia en metros para considerar que un usuario está "a bordo" de un bus virtual
BUS_TRACKING_INTERVAL_SECONDS = 30 # Intervalo en segundos para el cálculo de buses virtuales en segundo plano

# --- Función Auxiliar para UbicacionUsuario ---
def _get_or_create_ubicacion_usuario(db: Session, user_id: int, latitude: float, longitude: float) -> UbicacionUsuario:
    """
    Obtiene el registro de UbicacionUsuario para un usuario o lo crea si no existe,
    actualizando su ubicación.
    """
    ubicacion_usuario = db.query(UbicacionUsuario).filter(UbicacionUsuario.user_id == user_id).first()
    if ubicacion_usuario:
        ubicacion_usuario.latitud = latitude
        ubicacion_usuario.longitud = longitude
        # 'ultima_actualizacion' se actualiza automáticamente gracias a `onupdate=func.now()` en el modelo
    else:
        ubicacion_usuario = UbicacionUsuario(
            user_id=user_id,
            latitud=latitude,
            longitud=longitude
        )
        db.add(ubicacion_usuario)
    db.commit()
    db.refresh(ubicacion_usuario) # Recargar el objeto para asegurar que tenga el ID y valores actualizados
    return ubicacion_usuario

# --- Lógica Principal de Rastreo de Buses ---
def calcular_buses(db: Session):
    """
    Calcula y actualiza la ubicación de los buses virtuales basándose en la ubicación de los usuarios "a bordo".
    Cada ruta tendrá un único bus virtual cuya posición es el promedio de las ubicaciones
    de todos los usuarios actualmente "a bordo" de esa ruta.
    """
    print("Iniciando cálculo de buses virtuales...")

    # Recuperar las ubicaciones de todos los usuarios que están marcados como "a bordo"
    # y agruparlos por la ruta a la que pertenecen.
    usuarios_abordo_por_ruta = (
        db.query(RutaUsuario.id_ruta, UbicacionUsuario.latitud, UbicacionUsuario.longitud)
        .join(UbicacionUsuario, UbicacionUsuario.user_id == RutaUsuario.id_usuario)
        .filter(RutaUsuario.abordo == True)
        .all()
    )

    # Diccionario para acumular las sumas de latitud/longitud y el conteo por cada ruta
    route_locations_sums = {}

    for ruta_id, lat, lon in usuarios_abordo_por_ruta:
        if ruta_id not in route_locations_sums:
            route_locations_sums[ruta_id] = {"sum_lat": 0.0, "sum_lon": 0.0, "count": 0}
        
        route_locations_sums[ruta_id]["sum_lat"] += lat
        route_locations_sums[ruta_id]["sum_lon"] += lon
        route_locations_sums[ruta_id]["count"] += 1
    
    # Procesar cada ruta para calcular la ubicación promedio de su bus virtual
    for ruta_id, data in route_locations_sums.items():
        avg_lat = data["sum_lat"] / data["count"]
        avg_lon = data["sum_lon"] / data["count"]

        # Buscar si ya existe un bus virtual para esta ruta en UbicacionTemporal
        # Asumimos que hay un solo bus virtual por ruta (identificado por idruta).
        bus_virtual = db.query(UbicacionTemporal).filter(UbicacionTemporal.idruta == ruta_id).first()

        if bus_virtual:
            # Si el bus ya existe, actualizamos su ubicación
            bus_virtual.latitud = avg_lat
            bus_virtual.longitud = avg_lon
            # 'ultima_actualizacion' se actualiza automáticamente al hacer commit
            print(f"Actualizado bus virtual para Ruta {ruta_id}: Lat {avg_lat:.6f}, Lon {avg_lon:.6f}")
        else:
            # Si no existe, creamos un nuevo bus virtual para esta ruta
            bus_virtual = UbicacionTemporal(
                idbus=str(uuid.uuid4()), # Se genera un UUID único para este bus virtual
                idruta=ruta_id,
                latitud=avg_lat,
                longitud=avg_lon,
                velocidad=0, # Valor por defecto, se puede calcular en el futuro
                distanciaonstop=0, # Valor por defecto
                estado="activo"
            )
            db.add(bus_virtual)
            print(f"Creado nuevo bus virtual para Ruta {ruta_id}: Lat {avg_lat:.6f}, Lon {avg_lon:.6f}")

    # Eliminar buses virtuales de rutas que ya no tienen usuarios "a bordo"
    # Opcional: podrías decidir mantenerlos con estado "inactivo"
    rutas_con_usuarios = set(route_locations_sums.keys())
    buses_activos_db = db.query(UbicacionTemporal).filter(UbicacionTemporal.idruta.notin_(rutas_con_usuarios)).all()
    for bus_a_eliminar in buses_activos_db:
        # Aquí podrías cambiar el estado a "inactivo" en lugar de eliminar
        # bus_a_eliminar.estado = "inactivo"
        db.delete(bus_a_eliminar)
        print(f"Eliminado bus virtual (sin usuarios) para Ruta {bus_a_eliminar.idruta}: {bus_a_eliminar.idbus}")

    db.commit() # Confirmar todos los cambios en la base de datos
    print("Cálculo de buses virtuales finalizado y base de datos actualizada.")
    
    # Devolver los buses virtuales actuales (útil para depuración/logueo)
    return db.query(UbicacionTemporal).all()


# --- Verificación de Estado de Ubicación del Usuario ---
def check_user_location_status(db: Session, user_id: int, current_lat: float, current_lon: float) -> dict:
    """
    Verifica si un usuario está cerca de una parada o cerca de un bus virtual
    y actualiza su estado 'abordo' en RutaUsuario y 'en_parada' en UsuarioRutaActual.
    """
    user_status = {
        "user_id": user_id,
        "is_on_bus": False,
        "is_at_station": False,
        "current_bus_id": None,
        "current_station_id": None,
        "message": "Ubicación actualizada."
    }

    # Obtener la información de la ruta actual del usuario
    user_route_actual = db.query(UsuarioRutaActual).filter(UsuarioRutaActual.user_id == user_id).first()
    
    # 1. Verificar si el usuario está en una parada
    paradas = db.query(Parada).all()
    user_at_any_station_now = False # Nuevo estado para esta ejecución
    for parada in paradas:
        # Calcula la distancia entre la ubicación actual del usuario y la parada usando PostGIS
        # ST_Distance_Sphere devuelve la distancia en metros para coordenadas geográficas (SRID 4326)
        distance_to_parada = db.query(
            func.ST_Distance_Sphere(
                func.ST_MakePoint(current_lon, current_lat), # Longitud, Latitud del usuario
                func.ST_MakePoint(func.ST_X(parada.ubicacion), func.ST_Y(parada.ubicacion)) # Longitud, Latitud de la parada
            )
        ).scalar()

        if distance_to_parada is not None and distance_to_parada <= PROXIMIDAD_USUARIO_PARADA_METROS:
            user_at_any_station_now = True
            user_status["is_at_station"] = True
            user_status["current_station_id"] = parada.id
            user_status["message"] = f"Usuario cerca de la parada {parada.nombre} (ID: {parada.id})."
            break # El usuario está en una parada, no necesitamos revisar más paradas

    # Actualizar el estado 'en_parada' en UsuarioRutaActual
    if user_route_actual:
        if user_at_any_station_now and not user_route_actual.en_parada:
            user_route_actual.en_parada = True
            user_route_actual.hora_llegada_parada = datetime.utcnow()
            db.add(user_route_actual)
        elif not user_at_any_station_now and user_route_actual.en_parada:
            user_route_actual.en_parada = False
            user_route_actual.hora_llegada_parada = None
            db.add(user_route_actual)
        db.commit() # Confirma los cambios de 'en_parada'

    # 2. Verificar si el usuario está "a bordo" de un bus virtual
    # Solo se verifica si el usuario ha seleccionado una ruta
    if user_route_actual and user_route_actual.ruta_seleccionada_id:
        virtual_bus = db.query(UbicacionTemporal).filter(
            UbicacionTemporal.idruta == user_route_actual.ruta_seleccionada_id
        ).first()

        if virtual_bus:
            # Calcular la distancia entre el usuario y el bus virtual de su ruta seleccionada
            distance_to_bus = db.query(
                func.ST_Distance_Sphere(
                    func.ST_MakePoint(current_lon, current_lat), # Longitud, Latitud del usuario
                    func.ST_MakePoint(virtual_bus.longitud, virtual_bus.latitud) # Longitud, Latitud del bus virtual
                )
            ).scalar()

            # Obtener el registro RutaUsuario para el usuario y la ruta seleccionada (si existe)
            user_ruta_status = db.query(RutaUsuario).filter(
                RutaUsuario.id_usuario == user_id,
                RutaUsuario.id_ruta == user_route_actual.ruta_seleccionada_id
            ).first()

            if distance_to_bus is not None and distance_to_bus <= PROXIMIDAD_USUARIO_BUS_METROS:
                user_status["is_on_bus"] = True
                user_status["current_bus_id"] = virtual_bus.idbus
                user_status["message"] = "Usuario a bordo del bus virtual."

                # Marcar al usuario como 'abordo' en RutaUsuario si aún no lo está
                if user_ruta_status and not user_ruta_status.abordo:
                    user_ruta_status.abordo = True
                    user_ruta_status.ultima_actualizacion = datetime.utcnow()
                    db.add(user_ruta_status)
                    db.commit()
                elif not user_ruta_status:
                    # Si no existe un registro RutaUsuario, créalo y márcalo como abordo
                    new_ruta_usuario = RutaUsuario(
                        id_usuario=user_id,
                        id_ruta=user_route_actual.ruta_seleccionada_id,
                        abordo=True,
                        ultima_actualizacion=datetime.utcnow()
                    )
                    db.add(new_ruta_usuario)
                    db.commit()
            else:
                # Si el usuario está lejos del bus de su ruta, ya no está "a bordo"
                if user_ruta_status and user_ruta_status.abordo:
                    user_ruta_status.abordo = False
                    user_ruta_status.ultima_actualizacion = datetime.utcnow()
                    db.add(user_ruta_status)
                    db.commit()
                # No sobrescribir el mensaje si ya se ha detectado que el usuario está en una estación
                if user_status["message"] == "Ubicación actualizada.":
                     user_status["message"] = "Usuario no está cerca de ningún bus virtual en su ruta seleccionada."
        elif user_status["message"] == "Ubicación actualizada.":
            user_status["message"] = "No hay bus virtual activo para la ruta seleccionada."

    db.commit() # Confirma cualquier cambio pendiente

    return user_status

def run_bus_tracking_periodically(get_db_session_func): # Esta es la función get_db que pasas
    while True:
        db_session = None  # Inicializa la variable a None
        db_generator = None # Variable para el objeto generador
        try:
            # 1. Obtener el objeto generador de la función get_db
            db_generator = get_db_session_func()
            
            # 2. Avanzar el generador para obtener la sesión de base de datos real
            db_session = next(db_generator) # <-- ¡ESTE ES EL CAMBIO CRÍTICO!

            # 3. Ahora, db_session es una sesión de SQLAlchemy válida
            calcular_buses(db_session)

        except StopIteration:
            print("Error: La función get_db_session_func no produjo una sesión de base de datos.")
        except Exception as e:
            # Captura cualquier otro error durante el cálculo o la conexión
            print(f"Error en el hilo de cálculo de buses: {e}")
        finally:
            # 4. Asegurarse de cerrar la sesión y el generador
            if db_session:
                db_session.close() # Cierra la sesión explícitamente
            if db_generator:
                try:
                    # Intenta cerrar el generador. Esto ejecuta el bloque 'finally' dentro de get_db().
                    # Es buena práctica para liberar recursos asociados al generador.
                    db_generator.close()
                except RuntimeError as e:
                    # Puede ocurrir si el generador ya está cerrado/exhausto, lo cual es normal.
                    if "generator already executing" not in str(e):
                        print(f"Advertencia al cerrar el generador DB: {e}")
        
        time.sleep(BUS_TRACKING_INTERVAL_SECONDS)