from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
import logging
import os
from datetime import datetime

from app.models.chatbot_data import ChatbotDataResponse, ChatbotQuery, ChatMessage, ChatResponse
from app.services.chatbot_service import ChatbotService
from app.services.gemini_service import GeminiChatService
from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Dependency para obtener el servicio del chatbot
def get_chatbot_service() -> ChatbotService:
    """Dependency para inyectar el servicio del chatbot"""
    return ChatbotService(settings.csv_file_path)

# Cache global para mantener el contexto del chat
_gemini_service_cache = {}

def get_gemini_service() -> GeminiChatService:
    """Dependency para inyectar el servicio de Gemini con contexto persistente"""
    # Usar un ID de sesión simple (en producción usarías session ID real)
    session_id = "default_session"
    
    if session_id not in _gemini_service_cache:
        gemini_api_key = settings.gemini_api_key or os.getenv('GEMINI_API_KEY')
        csv_path = settings.csv_file_path
        _gemini_service_cache[session_id] = GeminiChatService(gemini_api_key, csv_path)
    
    return _gemini_service_cache[session_id]

@router.get("/data", response_model=ChatbotDataResponse)
async def get_complete_data_for_chatbot(
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Endpoint principal para el chatbot - Retorna TODA la información del sistema
    
    Este endpoint está diseñado para ser consumido por un chatbot/LLM y contiene:
    - Resumen completo de todas las estaciones
    - Información detallada de todas las variables
    - Estadísticas globales y por estación
    - Cobertura temporal y geográfica
    - Información de calidad de datos
    - Contexto para el chatbot
    
    Ideal para sistemas RAG (Retrieval-Augmented Generation)
    """
    try:
        logger.info("Generando datos completos para chatbot")
        complete_data = chatbot_service.get_complete_data_for_chatbot()
        logger.info(f"Datos generados: {len(complete_data.stations)} estaciones, {len(complete_data.variables)} variables")
        return complete_data
    except Exception as e:
        logger.error(f"Error generando datos para chatbot: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/query")
async def query_filtered_data(
    query: ChatbotQuery,
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Endpoint para consultas específicas del chatbot
    
    Permite al chatbot hacer consultas filtradas por:
    - Estaciones específicas
    - Variables específicas  
    - Rangos de fechas
    - Incluir o no datos crudos
    - Limitar número de registros
    """
    try:
        logger.info(f"Procesando query del chatbot: {query.dict()}")
        filtered_data = chatbot_service.get_filtered_data(query)
        return filtered_data
    except Exception as e:
        logger.error(f"Error procesando query del chatbot: {e}")
        raise HTTPException(status_code=500, detail="Error procesando consulta")

@router.get("/stations/summary")
async def get_stations_summary_for_chatbot(
    station_ids: Optional[List[int]] = Query(None, description="IDs específicos de estaciones"),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Resumen rápido de estaciones para el chatbot
    
    Útil cuando el chatbot necesita información específica de ciertas estaciones
    sin cargar todo el dataset completo.
    """
    try:
        complete_data = chatbot_service.get_complete_data_for_chatbot()
        
        if station_ids:
            filtered_stations = [
                station for station in complete_data.stations 
                if station.station_id in station_ids
            ]
            return {"stations": filtered_stations}
        
        return {"stations": complete_data.stations}
    except Exception as e:
        logger.error(f"Error obteniendo resumen de estaciones: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/variables/info")
async def get_variables_info_for_chatbot(
    variables: Optional[List[str]] = Query(None, description="Variables específicas"),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Información detallada de variables para el chatbot
    
    Proporciona al chatbot información técnica sobre las variables disponibles,
    incluyendo unidades, rangos válidos, y estadísticas de calidad.
    """
    try:
        complete_data = chatbot_service.get_complete_data_for_chatbot()
        
        if variables:
            filtered_variables = [
                var for var in complete_data.variables 
                if var.name in variables
            ]
            return {"variables": filtered_variables}
        
        return {"variables": complete_data.variables}
    except Exception as e:
        logger.error(f"Error obteniendo información de variables: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/context")
async def get_context_for_chatbot(
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Información contextual para el chatbot
    
    Proporciona contexto sobre el sistema, propósito, alcance temporal y geográfico.
    Útil para que el chatbot entienda de qué trata el sistema y pueda dar respuestas
    más informadas.
    """
    try:
        complete_data = chatbot_service.get_complete_data_for_chatbot()
        
        return {
            "system_info": complete_data.system_info,
            "context_info": complete_data.context_info,
            "global_stats": complete_data.global_stats,
            "temporal_coverage": complete_data.temporal_coverage,
            "geographic_coverage": complete_data.geographic_coverage
        }
    except Exception as e:
        logger.error(f"Error obteniendo contexto para chatbot: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/health")
async def chatbot_service_health(
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Health check del servicio del chatbot
    
    Verifica que el servicio esté funcionando correctamente y proporciona
    información básica sobre el estado de los datos.
    """
    try:
        # Verificar que los datos se pueden cargar
        complete_data = chatbot_service.get_complete_data_for_chatbot()
        
        return {
            "status": "healthy",
            "data_loaded": True,
            "total_stations": len(complete_data.stations),
            "total_variables": len(complete_data.variables),
            "last_check": complete_data.system_info["last_updated"],
            "service_ready": True
        }
    except Exception as e:
        logger.error(f"Health check falló: {e}")
        return {
            "status": "unhealthy",
            "data_loaded": False,
            "error": str(e),
            "service_ready": False
        }

# ==========================================
# ENDPOINTS DE CHAT CONVERSACIONAL CON GEMINI
# ==========================================

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    message: ChatMessage,
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Endpoint principal para el chat conversacional con Nubi ☁️
    
    Sistema híbrido que combina:
    1. Respuestas heurísticas rápidas para preguntas comunes
    2. IA (Gemini) para preguntas complejas sobre clima
    3. Validación de scope y fallbacks inteligentes
    
    Este endpoint maneja:
    - Preguntas básicas con respuestas instantáneas
    - Análisis inteligente de datos meteorológicos
    - Explicaciones de conceptos climáticos
    - Información de estaciones específicas
    """
    try:
        logger.info(f"Procesando mensaje con sistema híbrido: {message.message}")
        
        # Usar el nuevo sistema híbrido
        response_text = await chatbot_service.responder_pregunta(message.message)
        
        timestamp = datetime.now().isoformat()
        
        return ChatResponse(
            response=response_text,
            timestamp=timestamp,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error procesando el mensaje del chat"
        )

@router.get("/chat/health")
async def chat_health(
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Health check para el sistema híbrido de chat
    
    Verifica:
    - Estado del sistema heurístico (siempre disponible)
    - Disponibilidad de Gemini IA
    - Conectividad con los datos meteorológicos
    - Capacidades del sistema híbrido
    """
    try:
        # Verificar datos básicos
        data_available = chatbot_service.df is not None and len(chatbot_service.df) > 0
        
        # Verificar Gemini
        gemini_available = chatbot_service.has_gemini
        
        # Determinar estado general
        if data_available and gemini_available:
            status = "healthy"
            message = "Sistema híbrido completamente funcional"
        elif data_available:
            status = "degraded" 
            message = "Funcionando con respuestas heurísticas - Gemini no disponible"
        else:
            status = "unhealthy"
            message = "Datos meteorológicos no disponibles"
        
        return {
            "status": status,
            "service": "Hybrid Chat Service",
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "heuristic_responses": data_available,
                "gemini_ai": gemini_available,
                "data_records": len(chatbot_service.df) if data_available else 0,
                "stations_count": chatbot_service.df['station_id'].nunique() if data_available else 0
            }
        }
            
    except Exception as e:
        logger.error(f"Error en health check de chat híbrido: {e}")
        return {
            "status": "unhealthy",
            "service": "Hybrid Chat Service",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/info")
async def chat_info():
    """
    Información completa sobre el chatbot Nubi ☁️ - Sistema Híbrido
    """
    return {
        "name": "Nubi ☁️",
        "description": "Asistente ambiental híbrido con IA para datos meteorológicos",
        "version": "2.0.0",
        "system_type": "Hybrid (Heuristic + AI)",
        "capabilities": [
            "🚀 Respuestas heurísticas instantáneas",
            "🤖 Análisis inteligente con Gemini IA", 
            "📊 Consultar estado actual de estaciones",
            "📍 Listar estaciones disponibles",
            "📚 Explicar conceptos meteorológicos",
            "🌬️ Interpretar calidad del aire",
            "📈 Análisis comparativo de datos",
            "🔍 Preguntas abiertas sobre clima",
            "🛡️ Validación de scope automática"
        ],
        "commands": {
            "a": "Ver estaciones disponibles",
            "b": "Modo educativo - explicar conceptos",
            "hola": "Saludo inicial con opciones",
            "[nombre_estacion]": "Estado actual de una estación",
            "¿qué es [variable]?": "Explicación de conceptos"
        },
        "variables_supported": [
            "temperatura", "humedad", "presión", 
            "PM1", "PM2.5", "PM10", "ICA", 
            "precipitación", "viento_vel", "viento_dir"
        ],
        "endpoints": {
            "chat": "/chatbot/message - Chat conversacional",
            "data": "/chatbot/data - Datos estructurados completos",
            "query": "/chatbot/query - Consultas filtradas",
            "health": "/chatbot/health - Estado del servicio"
        }
    }

@router.post("/explain", response_model=ChatResponse)
async def explain_data_with_gemini(
    message: ChatMessage,
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """
    🤖 Endpoint específico para explicaciones con Gemini IA
    
    Este endpoint SIEMPRE usa Gemini IA, sin pasar por el sistema heurístico.
    Diseñado específicamente para el botón "Explícame" que genera preguntas
    contextuales robustas sobre datos meteorológicos.
    
    Características:
    - Fuerza el uso de Gemini IA (no heurístico)
    - Optimizado para análisis de datos complejos
    - Respuestas detalladas y técnicas
    - Contexto meteorológico especializado
    """
    try:
        logger.info(f"🤖 Procesando explicación FORZADA con Gemini: {message.message[:100]}...")
        
        # Verificar que Gemini esté disponible
        if not chatbot_service.has_gemini:
            logger.error("❌ Gemini no está disponible para explicaciones")
            raise HTTPException(
                status_code=503, 
                detail="El servicio de IA (Gemini) no está disponible actualmente"
            )
        
        # FORZAR el uso de Gemini directamente, sin heurísticas
        response_text = await chatbot_service.responder_con_gemini(message.message)
        
        if not response_text or response_text.strip() == "":
            logger.warning("⚠️ Gemini devolvió respuesta vacía")
            response_text = "Lo siento, no pude generar una explicación detallada en este momento. Por favor, intenta de nuevo."
        
        timestamp = datetime.now().isoformat()
        
        logger.info("✅ Explicación con Gemini completada exitosamente")
        
        return ChatResponse(
            response=response_text,
            timestamp=timestamp,
            status="success"
        )
        
    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise
    except Exception as e:
        logger.error(f"❌ Error procesando explicación con Gemini: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno procesando la explicación: {str(e)}"
        )
