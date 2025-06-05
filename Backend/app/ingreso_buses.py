# seed_paradas.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.entities import Base, Ubicacion, Parada, Estacion, Ruta  # Ajusta la ruta si es necesario

# Ejemplo de conexión con SQLite (puedes usar otro motor: PostgreSQL, MySQL, etc.)
engine = create_engine("sqlite:///transcaribe.db", echo=True)  
Session = sessionmaker(bind=engine)
session = Session()

# Crear las tablas (si no existen)
Base.metadata.create_all(engine)

# Datos para la línea T100E (ejemplo con datos asumidos reales)
paradas = [
    {
        "nombre": "La Bodeguita",
        "latitud": 10.419757778151677,
        "longitud": -75.55169788249471,
        "es_estacion": True  # Definido como estación, si lo necesitas
    },
    {
        "nombre": "Centro",
        "latitud": 10.425035546556323, 
        "longitud": -75.54664275627614,
        "es_estacion": True
    },
    {
        "nombre": "María Auxiliadora",
        "latitud": 10.408947656398293,
        "longitud": -75.51563610516841,
        "es_estacion": True
    },
    {
        "nombre": "Cuatro Vientos",
        "latitud": 10.406474274047904,
        "longitud": -75.50248235090638,
        "es_estacion": True
    },
    {
        "nombre": "La Castellana",
        "latitud": 10.39441522810936,
        "longitud": -75.48591021123082,
        "es_estacion": True
    },
    {
        "nombre": "Madre Bernarda",
        "latitud": 10.395071512907611,
        "longitud": -75.47884512495773,
        "es_estacion": True
    },
    {
        "nombre": "Portal",
        "latitud": 10.395371173302719,
        "longitud": -75.47281180286103,
        "es_estacion": True
    },
    {
      "nombre": "Chambacú",
      "latitud": 10.425904473662273,
      "longitud": -75.54052868402731,
      "es_estacion": True
    },
    {
      "nombre": "Lo Amador",
      "latitud": 10.422371151373092,
      "longitud": -75.5345707353182,
      "es_estacion": True
    },
    {
      "nombre": "La Popa",
      "latitud": 10.420325862723193,
      "longitud": -75.5309572307058,
      "es_estacion": True
    },
    {
      "nombre": "Delicias",
      "latitud": 10.416715537998394,
      "longitud": -75.52799076698366,
      "es_estacion": True
    },
    {
      "nombre": "Bazurto",
      "latitud": 10.413969793429754,
      "longitud": -75.52439805727028,
      "es_estacion": True
    },
    {
      "nombre": "El Prado",
      "latitud": 10.411086818534075,
      "longitud": -75.51952587690401,
      "es_estacion": True
    },
    {
      "nombre": "España",
      "latitud": 10.408309116072557,
      "longitud": -75.51299972759116,
      "es_estacion": True
    },
    {
      "nombre": "República del Líbano",
      "latitud": 10.407339330522671,
      "longitud": -75.5076205915093,
      "es_estacion": True
    },
    {
      "nombre": "Villa Olímpica",
      "latitud": 10.403475777652273,
      "longitud": -75.49700480195132,
      "es_estacion": True
    },
    {
      "nombre": "Los Ejecutivos",
      "latitud": 10.399405214544485,
      "longitud": -75.49364458599639,
      "es_estacion": True
    },
    {
      "nombre": "Los Ángeles",
      "latitud": 10.395088852660738,
      "longitud": -75.49040456832743,
      "es_estacion": False
    },
    
]

# Insertar cada parada en la base de datos
for parada_data in paradas:
    # Primero crear la ubicación
    ubicacion = Ubicacion(
        latitud=parada_data["latitud"],
        longitud=parada_data["longitud"]
    )
    session.add(ubicacion)
    session.flush()  # Permite asignar el id a la instancia sin hacer commit completo aún

    # Si la parada es una estación, la insertamos en la tabla Estacion
    if parada_data.get("es_estacion", False):
        estacion = Estacion(
            nombre=parada_data["nombre"],
            idubicacion=ubicacion.id,
            descripcion=f"Estación {parada_data['nombre']}"
        )
        session.add(estacion)
    else:
        # Insertar en la tabla Parada si no es considerada estación
        parada = Parada(
            nombre=parada_data["nombre"],
            idubicacion=ubicacion.id
            # Si deseas relacionarla con una estación, puedes asignar id_estacion
        )
        session.add(parada)

# Confirmar los cambios en la base de datos.
session.commit()
