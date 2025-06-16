# app/models/entities.py

#Contiene los modelos especificos para uso de SLQAlchemy PostGIS
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

# --- Importaciones específicas para GeoAlchemy2 ---
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape # Para convertir de GeoAlchemy2 a shapely, útil para Python
from shapely.geometry import Point # Para crear objetos Point en Python, si es necesario

from app.database import Base 

# --- Tablas de Transcaribe (paradas y rutas existentes) ---

class Parada(Base):
    """
    Representa una parada de bus de Transcaribe.
    'ubicacion' ahora usa el tipo Geometry de GeoAlchemy2.
    """
    __tablename__ = 'parada'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    # Define la columna de ubicación como Geometry (Point, SRID 4326)
    ubicacion = Column(Geometry(geometry_type='POINT', srid=4326), unique=True, nullable=False)

class Ruta(Base):
    """
    Representa una ruta de bus de Transcaribe.
    """
    __tablename__ = 'ruta'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    paradas = relationship("RutaParada", back_populates="ruta")

class RutaParada(Base):
    """
    Tabla intermedia que define el orden de las paradas en una ruta.
    """
    __tablename__ = 'ruta_parada'
    ruta_id = Column(Integer, ForeignKey('ruta.id'), primary_key=True)
    parada_id = Column(Integer, ForeignKey('parada.id'), primary_key=True)
    orden = Column(Integer, nullable=False)
    
    ruta = relationship("Ruta", back_populates="paradas")
    parada = relationship("Parada")

# --- Tablas para el seguimiento de usuarios y buses virtuales ---

class Usuario(Base):
    """
    Representa un usuario registrado en el sistema, incluyendo sus credenciales.
    """
    __tablename__ = 'usuario'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # Aquí se almacenará el hash de la contraseña
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now()) # Fecha y hora de creación del usuario

    ubicacion_actual = relationship("UbicacionUsuario", back_populates="usuario", uselist=False)
    ruta_activa = relationship("UsuarioRutaActual", back_populates="usuario", uselist=False)
    rutas_tomadas = relationship("RutaUsuario", back_populates="usuario")
    # Ya no se necesita la relación con irregularidades_reportadas aquí
    votes = relationship("IrregularityVote", back_populates="user")


class UbicacionUsuario(Base):
    """
    Almacena la última ubicación conocida de cada usuario.
    """
    __tablename__ = 'ubicacion_usuario'
    user_id = Column(Integer, ForeignKey('usuario.id'), primary_key=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    # Cambiado a Geometry para ser consistente con otras ubicaciones espaciales si es necesario
    ubicacion_punto = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False) 
    ultima_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="ubicacion_actual")


class RutaUsuario(Base):
    """
    Registra el estado de un usuario respecto a una ruta específica.
    Indica si un usuario está 'a bordo' de un bus virtual en esa ruta.
    """
    __tablename__ = 'ruta_usuario'
    id_usuario = Column(Integer, ForeignKey('usuario.id'), primary_key=True)
    id_ruta = Column(Integer, ForeignKey('ruta.id'), primary_key=True)
    abordo = Column(Boolean, default=False)
    ultima_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="rutas_tomadas")
    ruta = relationship("Ruta")


class UbicacionTemporal(Base):
    """
    Representa la ubicación calculada de un 'bus virtual'.
    Estos registros se actualizan periódicamente por la lógica de 'calcular_buses'.
    """
    __tablename__ = 'ubicacion_temporal'
    idbus = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    idruta = Column(Integer, ForeignKey('ruta.id'), nullable=False)
    # Se mantiene como Float por ahora, pero se puede considerar Geometry si la lógica lo requiere.
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    velocidad = Column(Float, default=0.0)
    distanciaonstop = Column(Float, default=0.0)
    estado = Column(String, default="activo")
    ultima_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())

    ruta = relationship("Ruta")


class UsuarioRutaActual(Base):
    """
    Almacena la ruta que un usuario ha seleccionado activamente (o está planeando tomar),
    y la próxima parada donde el usuario tiene la intención de bajarse.
    """
    __tablename__ = 'usuario_ruta_actual'
    user_id = Column(Integer, ForeignKey('usuario.id'), primary_key=True)
    ruta_seleccionada_id = Column(Integer, ForeignKey('ruta.id'))
    proxima_parada_id = Column(Integer, ForeignKey('parada.id'))
    en_parada = Column(Boolean, default=False)
    hora_llegada_parada = Column(DateTime)

    usuario = relationship("Usuario", back_populates="ruta_activa")
    ruta_seleccionada = relationship("Ruta")
    proxima_parada = relationship("Parada")


##Tablas para Reporte de Irregularidades y Votos


class ReportedIrregularity(Base):
    __tablename__ = "reported_irregularities"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True, nullable=False)
    descripcion = Column(String, nullable=True)
    
    # Campo de ubicación para datos geográficos
    # 'POINT' indica que almacenará puntos, srid=4326 es el estándar GPS (WGS 84)
    ubicacion = Column(Geometry('POINT', srid=4326), nullable=False) 
    
    activa = Column(Boolean, default=True) # Por defecto, la irregularidad está activa
    
    # Fecha y hora de creación, establecida automáticamente por la base de datos
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    ultimo_like_at = Column(DateTime(timezone=True), nullable=True) # Última vez que se le dio 'like' (opcional)
    likes = Column(Integer, default=0) # Contador de likes, por defecto 0
    dislikes = Column(Integer, default=0) # Contador de dislikes, por defecto 0

    # Relación con IrregularityVote
    votes = relationship("IrregularityVote", back_populates="irregularity")

class IrregularityVote(Base):
    __tablename__ = "irregularity_votes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    irregularity_id = Column(Integer, ForeignKey("reported_irregularities.id"), nullable=False)
    
    # True para like, False para dislike
    is_like = Column(Boolean, nullable=False) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("Usuario", back_populates="votes")
    irregularity = relationship("ReportedIrregularity", back_populates="votes")