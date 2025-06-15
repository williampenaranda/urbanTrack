# app/models/models.py (Este archivo contendrá tus esquemas Pydantic)

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List # Asegúrate de importar List para listas en Pydantic

# Nuevas importaciones necesarias para GeoAlchemy2/Shapely en Pydantic
from geoalchemy2.shape import to_shape
from geoalchemy2 import Geometry
from shapely.geometry import Point

# --- Esquemas de Autenticación y Gestión de Usuarios ---

# Esquema para el registro de nuevos usuarios
class UserRegister(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    email: EmailStr

# Esquema para el inicio de sesión de usuarios
class UserLogin(BaseModel):
    username: str
    password: str

# Esquema para la actualización de datos de usuario (sin password aquí)
class UserUpdate(BaseModel):
    username: str # Puedes hacerlo opcional si solo se actualizan otros campos
    first_name: str
    last_name: str
    email: EmailStr

# Esquema para la respuesta al cliente cuando se devuelve información de un usuario
class UserResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True # Equivalente a orm_mode = True en Pydantic v1


# --- Esquemas para Ubicación Geográfica Reutilizables ---
# (Este es clave para manejar las geometrías de PostGIS en tus respuestas)
class UbicacionLatLon(BaseModel):
    """Modelo para representar una ubicación con latitud y longitud."""
    latitude: float
    longitude: float

    @classmethod
    def from_geometry(cls, geom: Optional[Geometry]):
        """Convierte un objeto Geometry de GeoAlchemy2 a UbicacionLatLon."""
        if geom:
            # Convierte el objeto Geometry (PostGIS) a un objeto Point de Shapely
            point = to_shape(geom)
            return cls(latitude=point.y, longitude=point.x)
        return None


# --- Esquemas para Rutas de Buses y Rastreo ---

# Esquema para la actualización de ubicación del usuario
class UserLocationUpdate(BaseModel):
    user_id: int
    ruta_id: int # La ruta que el usuario quiere tomar/está tomando
    latitude: float
    longitude: float

# Esquema para verificar la bajada del usuario
class CheckExitRequest(BaseModel):
    user_id: int
    ruta_id: int # La ruta que el usuario estaba tomando
    latitude: float
    longitude: float

# Esquema para seleccionar una ruta
class SelectRouteRequest(BaseModel):
    user_id: int
    ruta_id: int

# Esquema para establecer la próxima parada
class SetNextStopRequest(BaseModel):
    user_id: int
    parada_id: int

# Esquema para la solicitud de cálculo de ruta (manteniendo tu nombre)
class CalculateRouteRequest(BaseModel):
    origen_lat: float = Field(..., description="Latitud de la ubicación de origen del usuario.")
    origen_lon: float = Field(..., description="Longitud de la ubicación de origen del usuario.")
    destino_lat: float = Field(..., description="Latitud de la ubicación de destino del usuario.")
    destino_lon: float = Field(..., description="Longitud de la ubicación de destino del usuario.")

# Esquema para la respuesta de /get_buses
class BusLocationResponse(BaseModel):
    bus_uuid: str
    ruta_id: int
    latitude: float
    longitude: float
    velocidad: float
    estado: str
    ultima_actualizacion: Optional[datetime] # Puede ser None si no hay fecha


# --- Esquemas para las Paradas (usando UbicacionLatLon para la ubicación) ---
class ParadaBaseResponse(BaseModel): # Nombre base para evitar conflicto con ParadaSugeridaResponse
    id: int
    nombre: str
    # Usamos UbicacionLatLon para que la ubicación se serialice correctamente
    ubicacion: UbicacionLatLon

    class Config:
        from_attributes = True
        json_encoders = {
            Geometry: lambda v: UbicacionLatLon.from_geometry(v).dict() if v else None
        }

# Tu ParadaSugeridaResponse existente (adaptado para usar UbicacionLatLon si quieres incluirla)
class ParadaSugeridaResponse(ParadaBaseResponse): # Hereda para incluir id, nombre, ubicacion
    distancia_origen_usuario_metros: Optional[float] = None
    distancia_destino_usuario_metros: Optional[float] = None


# --- Esquemas para las Rutas (para GET /rutas y GET /rutas/{id}) ---
class RutaParadaOrderResponse(BaseModel):
    """Representa la relación Ruta-Parada con los detalles de la parada."""
    parada_id: int
    orden: int
    parada: ParadaBaseResponse # Anida la parada completa aquí

    class Config:
        from_attributes = True

class RutaBasicResponse(BaseModel): # Para cuando solo se necesita ID y nombre de la ruta
    id: int
    nombre: str

    class Config:
        from_attributes = True

class RutaDetailResponse(RutaBasicResponse): # Herencia para detalles completos de una ruta
    paradas: List[RutaParadaOrderResponse] = [] # Incluye las paradas ordenadas

    class Config:
        from_attributes = True


# --- Esquemas para la Respuesta del Cálculo de Ruta (ajustados a tu estructura original) ---

# Esquemas anidados para la respuesta de /calculate_route
# Nombres de clase ajustados para mayor claridad y evitar duplicados con los de arriba

class SegmentoTrayectoResponse(BaseModel):
    tipo: str # "VIAJE_EN_BUS" o "TRANSBORDO"
    ruta_id: Optional[int] = None # Solo para VIAJE_EN_BUS
    ruta_nombre: Optional[str] = None # Solo para VIAJE_EN_BUS
    desde_parada_id: int
    desde_parada_nombre: str
    # 'ubicacion' de las paradas no estaba aquí, pero es útil para el frontend
    desde_parada_ubicacion: UbicacionLatLon # Añadido
    hasta_parada_id: Optional[int] = None
    hasta_parada_nombre: Optional[str] = None
    hasta_parada_ubicacion: Optional[UbicacionLatLon] = None # Añadido
    costo_segundos: float # Duración del segmento
    descripcion: str
    # Campos adicionales específicos para transbordo
    hacia_ruta: Optional[str] = None # Nombre de la ruta a la que se transborda

class RutaDetalleCalculadaResponse(BaseModel): # Renombrado de RutaSugeridaDetalleResponse para claridad
    parada_origen_sugerida: ParadaSugeridaResponse
    parada_destino_sugerida: ParadaSugeridaResponse
    total_tiempo_estimado_segundos: float
    total_tiempo_estimado_formato: str # Ej. "0:15:30"
    segmentos_trayecto: List[SegmentoTrayectoResponse]

class CalculateRouteResponse(BaseModel): # Tu esquema de respuesta final para /calculate_route
    message: str
    ruta_sugerida: Optional[RutaDetalleCalculadaResponse] = None
    # Mantengo tus campos originales para evitar romper tu frontend si ya los usabas
    rutas_alternativas_origen: Optional[List[RutaBasicResponse]] = None # Adaptado para usar RutaBasicResponse
    parada_origen_sugerida: Optional[ParadaSugeridaResponse] = None
    parada_destino_sugerida: Optional[ParadaSugeridaResponse] = None