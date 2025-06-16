# app/auth/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt # Asegúrate de importar 'jwt' y 'JWTError' de 'jose'

# Importa tu modelo de Usuario y tu función de base de datos
from app.models.entities import Usuario 
from app.database import get_db

# Importa las constantes de seguridad (SECRET_KEY, ALGORITHM)
from app.core.security import SECRET_KEY, ALGORITHM 

# Esto define el esquema de seguridad OAuth2 con la URL donde el cliente puede obtener un token
# Asegúrate de que 'api/login' sea la URL de tu endpoint de login que devuelve el token.
# Anteriormente era 'api/auth/login', pero tu router de login lo definiste con prefix="/api",
# así que la URL completa sería "/api/login".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login") 

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario: # Añadir el tipo de retorno para claridad
    """
    Dependencia para obtener el usuario autenticado a partir de un token JWT.
    Decodifica y valida el token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # --- Lógica REAL de decodificación de JWT ---
        # Decodificamos el token usando la SECRET_KEY y el ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Obtenemos el 'sub' (subject) del payload, que es el username del usuario
        username: str = payload.get("sub") 
        
        if username is None:
            raise credentials_exception # Si el 'sub' no está presente, las credenciales son inválidas
        
        # Buscamos al usuario en la base de datos por el username del token
        user = db.query(Usuario).filter(Usuario.username == username).first()
        if user is None:
            raise credentials_exception # Si el usuario no existe en la DB, las credenciales son inválidas
            
    except JWTError: # Captura cualquier error relacionado con el JWT (token inválido, expirado, etc.)
        raise credentials_exception
        
    return user