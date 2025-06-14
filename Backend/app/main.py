from fastapi import FastAPI
from app.auth import routes as auth_routes
from app.rutas.bus_routes import router as bus_router  # Si tienes rutas adicionales
from app.database import Base, engine

app = FastAPI()

# Crear las tablas en la base de datos (solo se ejecuta si no existen)
Base.metadata.create_all(bind=engine)

# Registrar las rutas
app.include_router(auth_routes.router, prefix="/api/auth")
app.include_router(bus_router, prefix="/api/bus")
