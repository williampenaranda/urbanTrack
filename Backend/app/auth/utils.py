from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):       #Funcion encriptar contraseña en Hash
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):   #Compara la contraseña ingresada con la contraseña encriptada
    return pwd_context.verify(plain_password, hashed_password)
