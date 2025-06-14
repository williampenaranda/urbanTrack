# app/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.models import UserRegister, UserLogin, UserUpdate
from app.models.entities import Usuario
from app.database import get_db
from app.auth.utils import hash_password, verify_password

router = APIRouter()

@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(Usuario).filter(Usuario.username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="El usuario ya existe")

        new_user = Usuario(
            username=user.username,
            password=hash_password(user.password),
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "Usuario registrado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error al registrar el usuario")

@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.username == data.username).first()
    print("Se recibió una solicitud de login:", data.username)
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }
    }

@router.put("/users/{user_id}")
def update_user(user_id: int, updated_user: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    try:
        user.username = updated_user.username
        user.first_name = updated_user.first_name
        user.last_name = updated_user.last_name
        user.email = updated_user.email

        db.commit()
        return {"message": "Perfil actualizado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error al actualizar el perfil")

