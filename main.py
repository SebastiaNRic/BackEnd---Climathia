from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn

from app.config.settings import settings
from app.routes.api_routes import api_router

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Crear la aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API para datos de estaciones meteorológicas - Hackathon",
    debug=settings.debug
)

# Configurar CORS - Permitir conexión desde la interfaz de chat
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",  # Otros puertos comunes
        "*"  # En desarrollo - en producción especificar dominios exactos
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(api_router)

# Endpoint de salud
@app.get("/")
async def root():
    """Endpoint de salud de la API"""
    return {
        "message": "Weather Stations API - Hackathon",
        "version": settings.app_version,
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud"""
    return {"status": "healthy", "service": settings.app_name}


if __name__ == "__main__":
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,  # Auto-reload configurable
        reload_dirs=["app/"] if settings.reload else None,  # Monitorear cambios en la carpeta app
        reload_includes=["*.py"] if settings.reload else None,  # Solo archivos Python
        log_level=settings.log_level.lower()
    )
