from fastapi import FastAPI
from app.database import init_db         
from app.routes.bus_routes import router as bus_router
from app.auth.routes import router as auth_router  
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()  # Ejecuta schema.sql si es necesario
app.include_router(auth_router, prefix="/api/auth")
app.include_router(bus_router, prefix="/api/bus")