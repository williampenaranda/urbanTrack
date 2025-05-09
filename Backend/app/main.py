from fastapi import FastAPI
from app.auth import routes as auth_routes  # ← este es el correcto
from app.database import init_db           # ← este también

app = FastAPI()

init_db()  # Ejecuta schema.sql si es necesario
app.include_router(auth_routes.router)
