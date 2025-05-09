from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    email: EmailStr

class UserLogin(BaseModel):
    username: str
    password: str
