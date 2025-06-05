from fastapi import APIRouter, HTTPException
from app.models.models import UserRegister, UserLogin, UserUpdate
from app.database import get_db_connection
from app.auth.utils import hash_password, verify_password

router = APIRouter()

@router.post("/register")
def register(user: UserRegister): #Se conecta con la base de datos e ingresa los datos de registro
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuario (username, password, first_name, last_name, email) VALUES (?, ?, ?, ?, ?)",
            (user.username, hash_password(user.password), user.first_name, user.last_name, user.email),
        )
        conn.commit()
    except Exception as e:
        print("Error al registrar el usuario:", str(e))  # Log del error
        raise HTTPException(status_code=400, detail="Error al registrar el usuario")
    finally:
        conn.close()
    return {"message": "Usuario registrado exitosamente"}

@router.post("/login")  #Se conecta con la base de datos para comparar predenciales
def login(data: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuario WHERE username = ?", (data.username,))
    user = cursor.fetchone()
    conn.close()
    print("Se recibió una solicitud de login:", data.username)
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "email": user["email"],
        }
    }

@router.put("/users/{user_id}")
def update_user(user_id: int, updated_user: UserUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE usuario SET username = ?, first_name = ?, last_name = ?, email = ? WHERE id = ?",
            (
                updated_user.username,
                updated_user.first_name,
                updated_user.last_name,
                updated_user.email,
                user_id,
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception as e:
        print("Error al actualizar usuario:", e)
        raise HTTPException(status_code=400, detail="Error al actualizar usuario")
    finally:
        conn.close()
    return {"message": "Perfil actualizado exitosamente"}