# main.py

from fastapi import FastAPI
from threading import Thread
import time
from contextlib import asynccontextmanager

# Importaciones de tu configuración de base de datos
from app.database import Base, engine, get_db

# --- ¡¡¡ESTA LÍNEA ES CRÍTICA Y DEBE ESTAR AQUÍ, ARRIBA DE FastAPI INSTANCE!!! ---
# Asegura que todos los modelos definidos en entities.py sean conocidos por SQLAlchemy
# antes de que Base.metadata.create_all() sea llamado en el lifespan.
import app.models.entities 

# Importaciones de tus módulos de rutas
from app.auth import routes as auth_routes
from app.rutas.bus_routes import router as bus_router

# Importación de la función de tu tarea de fondo
from app.services.bus_tracking import run_bus_tracking_periodically


# --- Manejo del ciclo de vida de la aplicación (Startup/Shutdown) con lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona los eventos de inicio y cierre de la aplicación.
    Aquí se inicializan recursos y se inician tareas de fondo.
    """
    # --- Código que se ejecuta al INICIAR la aplicación ---
    print("Iniciando creación de tablas de la base de datos...")
    # Base.metadata.create_all() creará las tablas para TODOS los modelos
    # que hayan sido importados/conocidos por Base.metadata hasta este punto.
    Base.metadata.create_all(bind=engine)
    print("Tablas de la base de datos verificadas/creadas.")
  
    print("Esperando 2 segundos para asegurar que las tablas estén disponibles...")
    time.sleep(2) # Retraso de 2 segundos. Puedes ajustar si es necesario.
    print("Continuando con el inicio de la tarea de fondo.")
   
    print("Iniciando tarea de cálculo y seguimiento de buses en segundo plano...")
    background_thread = Thread(target=run_bus_tracking_periodically, args=(get_db,))
    background_thread.daemon = True  # Asegura que el hilo se cerrará cuando la aplicación principal se cierre
    background_thread.start()
    print("Tarea de cálculo de buses iniciada.")

    yield # La aplicación comienza a procesar solicitudes aquí

    # --- Código que se ejecuta al CERRAR la aplicación ---
    print("Aplicación cerrándose. Realizando limpieza de recursos...")
    
app = FastAPI(
    title="API de Transporte Público Inteligente",
    description="API para gestionar rutas, paradas, y cálculo de trayectos para buses y usuarios.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth_routes.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(bus_router, prefix="/api/bus", tags=["Buses y Rutas"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "API de Transporte Público está funcionando!"}