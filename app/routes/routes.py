"""
Archivo centralizado de rutas para toda la aplicación.
Aquí se definen y organizan todas las rutas de la API.
"""

from fastapi import APIRouter
from app.routes.api_routes import api_router

# Router principal de la aplicación
main_router = APIRouter()

# Incluir el router de la API
main_router.include_router(api_router)

# Aquí puedes agregar más routers principales si es necesario:
# main_router.include_router(admin_router, prefix="/admin")
# main_router.include_router(public_router, prefix="/public")

# Lista de todas las rutas disponibles para documentación
AVAILABLE_ROUTES = {
    "api": {
        "prefix": "/api",
        "description": "Endpoints principales de la API",
        "modules": [
            {
                "name": "stations",
                "prefix": "/api/stations",
                "description": "Gestión de estaciones meteorológicas"
            }
        ]
    }
}

def get_routes_info():
    """Retorna información sobre todas las rutas disponibles"""
    return AVAILABLE_ROUTES
