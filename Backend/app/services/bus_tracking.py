from sqlalchemy.orm import Session
from app.models.entities import RutaUsuario, UbicacionTemporal, Ubicacion
import uuid

def calcular_buses(db: Session):
    """
    Agrupa usuarios en la misma ruta y cercanos para calcular la ubicación de los buses.
    """
    usuarios_abordo = db.query(RutaUsuario).filter(RutaUsuario.abordo == True).all()
    buses_virtuales = {}

    for usuario in usuarios_abordo:
        ubicacion = db.query(Ubicacion).filter(Ubicacion.id == usuario.id_usuario).first()
        if not ubicacion:
            continue
        
        clave_bus = f"{usuario.id_ruta}_{int(ubicacion.latitud * 100)}_{int(ubicacion.longitud * 100)}"

        if clave_bus not in buses_virtuales:
            buses_virtuales[clave_bus] = {
                "bus_uuid": str(uuid.uuid4()),
                "ruta_id": usuario.id_ruta,
                "latitude": ubicacion.latitud,
                "longitude": ubicacion.longitud,
                "passengers": []
            }

        buses_virtuales[clave_bus]["passengers"].append(usuario.id_usuario)

    for bus_data in buses_virtuales.values():
        latitudes = [db.query(Ubicacion).filter(Ubicacion.id == user_id).first().latitud for user_id in bus_data["passengers"]]
        longitudes = [db.query(Ubicacion).filter(Ubicacion.id == user_id).first().longitud for user_id in bus_data["passengers"]]

        bus_data["latitude"] = sum(latitudes) / len(latitudes)
        bus_data["longitude"] = sum(longitudes) / len(longitudes)

        bus = UbicacionTemporal(idbus=bus_data["bus_uuid"], idruta=bus_data["ruta_id"], velocidad=0, distanciaonstop=0, estado="activo")
        db.add(bus)

    db.commit()
    return buses_virtuales
