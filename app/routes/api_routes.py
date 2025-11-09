from fastapi import APIRouter
from app.controllers import stations_controller, chatbot_controller

# Router principal de la API
api_router = APIRouter(prefix="/api")

# Incluir routers de controladores
api_router.include_router(stations_controller.router, tags=["stations"])
api_router.include_router(chatbot_controller.router, tags=["chatbot"])

# Si agregas más controladores en el futuro, los incluyes aquí:
# api_router.include_router(weather_router, tags=["weather"])
# api_router.include_router(analytics_router, tags=["analytics"])
