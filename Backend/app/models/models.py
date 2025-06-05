from pydantic import BaseModel, EmailStr
#Se utilizo libreria pydantic para la gestion de los usuarios en la base de datos
class UserRegister(BaseModel):      
    username: str
    password: str
    first_name: str
    last_name: str
    email: EmailStr

class UserLogin(BaseModel):
    username: str
    password: str
    
class UserUpdate(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr