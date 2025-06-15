# app/models.py (Este archivo contendrá tus esquemas Pydantic)

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List # Asegúrate de importar List para listas en Pydantic

# --- Esquemas de Autenticación y Gestión de Usuarios ---

# Esquema para el registro de nuevos usuarios
class UserRegister(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    email: EmailStr # Usa EmailStr para validación de formato de email

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
    created_at: datetime # Asume que tu entidad Usuario tiene este campo

    class Config:
        from_attributes = True # Equivalente a orm_mode = True en Pydantic v1


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

# Esquema para la solicitud de cálculo de ruta
class CalculateRouteRequest(BaseModel):
    origen_lat: float = Field(..., description="Latitud de la ubicación de origen del usuario.")
    origen_lon: float = Field(..., description="Longitud de la ubicación de origen del usuario.")
    destino_lat: float = Field(..., description="Latitud de la ubicación de destino del usuario.")
    destino_lon: float = Field(..., description="Longitud de la ubicación de destino del usuario.")

# --- Esquemas de Respuesta (Opcionales, pero recomendados para la salida de la API) ---

# Esquema para la respuesta de /get_buses
class BusLocationResponse(BaseModel):
    bus_uuid: str
    ruta_id: int
    latitude: float
    longitude: float
    velocidad: float
    estado: str
    ultima_actualizacion: Optional[datetime] # Puede ser None si no hay fecha


# Esquemas anidados para la respuesta de /calculate_route
class ParadaSugeridaResponse(BaseModel):
    id: int
    nombre: str
    distancia_origen_usuario_metros: Optional[float] = None
    distancia_destino_usuario_metros: Optional[float] = None

class RutaSugeridaDetalleResponse(BaseModel): # Nombre distinto para evitar confusión si tuvieras una entidad Ruta
    ruta_id: int
    ruta_nombre: str
    parada_origen_sugerida: ParadaSugeridaResponse
    parada_destino_sugerida: ParadaSugeridaResponse
    message: str

class RutaAlternativaOrigenResponse(BaseModel):
    ruta_id: int
    ruta_nombre: str
    message: str # Como "Pasa por la parada de origen 'X'."

class CalculateRouteResponse(BaseModel):
    message: str
    ruta_sugerida: Optional[RutaSugeridaDetalleResponse] = None
    rutas_alternativas_origen: Optional[List[RutaAlternativaOrigenResponse]] = None
    parada_origen_sugerida: Optional[ParadaSugeridaResponse] = None # Para escenarios donde solo se encuentra la parada de origen
    parada_destino_sugerida: Optional[ParadaSugeridaResponse] = None # Para escenarios donde solo se encuentra la parada de destino

class ParadaSugeridaResponse(BaseModel):
    id: int
    nombre: str
    distancia_origen_usuario_metros: Optional[float] = None
    distancia_destino_usuario_metros: Optional[float] = None

class SegmentoTrayectoResponse(BaseModel):
    tipo: str # "VIAJE_EN_BUS" o "TRANSBORDO"
    ruta_id: Optional[int] = None # Solo para VIAJE_EN_BUS
    ruta_nombre: Optional[str] = None # Solo para VIAJE_EN_BUS
    desde_parada_id: int
    desde_parada_nombre: str
    hasta_parada_id: Optional[int] = None # No aplica directamente para TRANSBORDO como punto final del seg
    hasta_parada_nombre: Optional[str] = None # No aplica directamente para TRANSBORDO como punto final del seg
    costo_segundos: float
    descripcion: str
    # Campos adicionales específicos para transbordo
    hacia_ruta: Optional[str] = None # Nombre de la ruta a la que se transborda

class RutaDetalleSugeridaResponse(BaseModel):
    parada_origen_sugerida: ParadaSugeridaResponse
    parada_destino_sugerida: ParadaSugeridaResponse
    total_tiempo_estimado_segundos: float
    total_tiempo_estimado_formato: str # Ej. "0:15:30"
    segmentos_trayecto: List[SegmentoTrayectoResponse]

class CalculateRouteResponse(BaseModel):
    message: str
    ruta_sugerida: Optional[RutaDetalleSugeridaResponse] = None
    # Eliminamos 'rutas_alternativas_origen' y 'parada_origen_sugerida/destino_sugerida' de aquí
    # ya que la respuesta detallada de ruta sugerida ya los incluye o la lógica de Dijkstra los maneja.
