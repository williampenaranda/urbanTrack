from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
import datetime
#SQLAlchemy para gestionar manejo de flujo constante de datos(ubicacion tiempo real)
Base = declarative_base()

class Ruta(Base):
    __tablename__ = 'ruta'
    id = Column(Integer, primary_key=True)
    nombre = Column(Text, nullable=False)

class Ubicacion(Base):
    __tablename__ = 'ubicacion'
    id = Column(Integer, primary_key=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)

class Estacion(Base):
    __tablename__ = 'estacion'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text, nullable=False)
    idubicacion = Column(Integer, ForeignKey('ubicacion.id'))
    descripcion = Column(Text)

    ubicacion = relationship("Ubicacion")

class Parada(Base):
    __tablename__ = 'parada'
    id = Column(Integer, primary_key=True)
    nombre = Column(Text)
    idubicacion = Column(Integer, ForeignKey('ubicacion.id'))
    id_estacion = Column(Integer, ForeignKey('estacion.id'), nullable=True)

    ubicacion = relationship("Ubicacion")
    estacion = relationship("Estacion")

class Usuario(Base):
    __tablename__ = 'usuario'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Bus(Base):
    __tablename__ = 'bus'
    id = Column(Integer, primary_key=True)
    idruta = Column(Integer, ForeignKey('ruta.id'))

    ruta = relationship("Ruta")

class Irregularidad(Base):
    __tablename__ = 'irregularidad'
    id = Column(Integer, primary_key=True)
    idusuario = Column(Integer, ForeignKey('usuario.id'))
    idruta = Column(Integer, ForeignKey('ruta.id'))
    titulo = Column(Text)
    descripcion = Column(Text)
    fecha = Column(DateTime)
    idubicacion = Column(Integer, ForeignKey('ubicacion.id'))

    usuario = relationship("Usuario")
    ruta = relationship("Ruta")
    ubicacion = relationship("Ubicacion")

class UbicacionTemporal(Base):
    __tablename__ = 'ubicaciontemporal'
    id = Column(Integer, primary_key=True)
    tiempo = Column(DateTime)
    idbus = Column(Integer, ForeignKey('bus.id'))
    idruta = Column(Integer, ForeignKey('ruta.id'))
    idparadadestino = Column(Integer, ForeignKey('parada.id'))
    velocidad = Column(Float)
    nextstopid = Column(Integer, ForeignKey('parada.id'))
    distanciaonstop = Column(Float)
    tiemporestado = Column(Float)
    estado = Column(Text)

    bus = relationship("Bus")
    ruta = relationship("Ruta")
    parada_destino = relationship("Parada", foreign_keys=[idparadadestino])
    next_stop = relationship("Parada", foreign_keys=[nextstopid])

class RutaParada(Base):
    __tablename__ = 'ruta_parada'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_ruta = Column(Integer, ForeignKey('ruta.id'), nullable=False)
    id_parada = Column(Integer, ForeignKey('parada.id'), nullable=False)
    orden = Column(Integer, nullable=False)

    ruta = relationship("Ruta")
    parada = relationship("Parada")

class RutaUsuario(Base):
    __tablename__ = 'rutas_usuario'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuario.id'), nullable=False)
    id_ruta = Column(Integer, ForeignKey('ruta.id'), nullable=False)
    abordo = Column(Boolean, default=False)
    ultima_actualizacion = Column(DateTime, default=datetime.datetime.utcnow)

    usuario = relationship("Usuario")
    ruta = relationship("Ruta")
