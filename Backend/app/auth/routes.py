# app/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException, status # Importamos 'status' para códigos HTTP más claros
from sqlalchemy.orm import Session
# Asegúrate de que 'app.models.models' contenga tus modelos Pydantic (UserRegister, UserLogin, UserUpdate)
from app.models.models import UserRegister, UserLogin, UserUpdate
from app.models.entities import Usuario # Importamos el modelo Usuario de entities
from app.database import get_db
from app.auth.utils import hash_password, verify_password # Funciones para hashing de contraseñas
from app.services.route_calculation import calcular_trayecto_usuario
from app.models.models import (
    # ... tus otros esquemas
    CalculateRouteRequest,
    CalculateRouteResponse # <--- Asegúrate de importar esta nueva definición
)

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED) # Código de estado 201 para creación exitosa
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en la base de datos.
    Hashea la contraseña antes de guardarla.
    """
    # Verificamos si el nombre de usuario o el correo electrónico ya existen
    existing_user_by_username = db.query(Usuario).filter(Usuario.username == user_data.username).first()
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, # 409 Conflict es más apropiado para recursos duplicados
            detail="El nombre de usuario ya está registrado."
        )
    
    existing_user_by_email = db.query(Usuario).filter(Usuario.email == user_data.email).first()
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado."
        )

    try:
        # Creamos una nueva instancia de Usuario con los datos del Pydantic UserRegister
        new_user = Usuario(
            username=user_data.username,
            password=hash_password(user_data.password), # Hasheamos la contraseña
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email
            # created_at se genera automáticamente por el default=func.now() en el modelo
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user) # Refrescamos el objeto para obtener el ID y created_at

        return {"message": "Usuario registrado exitosamente", "user_id": new_user.id}
    except Exception as e:
        # En un entorno de producción, aquí podrías registrar el error 'e'
        # para depuración interna sin exponer detalles sensibles al cliente.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Error genérico del servidor
            detail=f"Error inesperado al registrar el usuario: {e}"
        )



@router.post("/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica a un usuario.
    Verifica las credenciales y devuelve información del usuario si son válidas.
    """
    # Buscamos al usuario por su nombre de usuario
    user = db.query(Usuario).filter(Usuario.username == credentials.username).first()
    print(f"Se recibió una solicitud de login para: {credentials.username}")

    # Verificamos si el usuario existe y si la contraseña es correcta
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, # 401 Unauthorized para credenciales inválidas
            detail="Nombre de usuario o contraseña incorrectos."
        )
    
    # Si las credenciales son válidas, devolvemos la información del usuario
    # No devolvemos la contraseña ni el hash por seguridad.
    return {
        "message": "Inicio de sesión exitoso.",
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            # created_at puede ser útil para el frontend si lo necesitas
            "created_at": user.created_at.isoformat() if user.created_at else None 
        }
    }



@router.put("/users/{user_id}")
def update_user(user_id: int, updated_user_data: UserUpdate, db: Session = Depends(get_db)):
    """
    Actualiza la información de un usuario existente.
    """
    user_to_update = db.query(Usuario).filter(Usuario.id == user_id).first()
    
    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # 404 Not Found si el usuario no existe
            detail="Usuario no encontrado."
        )
    
    try:
        # Verificamos si el nuevo username o email ya están en uso por otro usuario
        if updated_user_data.username and updated_user_data.username != user_to_update.username:
            existing_user_by_username = db.query(Usuario).filter(Usuario.username == updated_user_data.username).first()
            if existing_user_by_username and existing_user_by_username.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El nuevo nombre de usuario ya está en uso."
                )
        
        if updated_user_data.email and updated_user_data.email != user_to_update.email:
            existing_user_by_email = db.query(Usuario).filter(Usuario.email == updated_user_data.email).first()
            if existing_user_by_email and existing_user_by_email.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El nuevo correo electrónico ya está en uso."
                )

        # Actualizamos solo los campos que vienen en updated_user_data
        user_to_update.username = updated_user_data.username
        user_to_update.first_name = updated_user_data.first_name
        user_to_update.last_name = updated_user_data.last_name
        user_to_update.email = updated_user_data.email

        db.commit()
        db.refresh(user_to_update) # Refrescamos para obtener cualquier actualización automática (como 'onupdate' si se aplicara)
        
        return {"message": "Perfil actualizado exitosamente", "user": {
            "id": user_to_update.id,
            "username": user_to_update.username,
            "first_name": user_to_update.first_name,
            "last_name": user_to_update.last_name,
            "email": user_to_update.email,
            "created_at": user_to_update.created_at.isoformat() if user_to_update.created_at else None
        }}
    except HTTPException: # Re-lanza HTTPException sin modificarla
        raise
    except Exception as e:
        # Registra el error para depuración
        print(f"Error al actualizar el perfil del usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al actualizar el perfil: {e}"
        )

