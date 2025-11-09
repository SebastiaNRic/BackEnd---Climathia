from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class StationSummary(BaseModel):
    """Resumen completo de una estación para el chatbot"""
    station_id: int
    station_name: str
    tipo_equipo: str
    location: Dict[str, float] = Field(description="Coordenadas geográficas")
    total_records: int
    date_range: Dict[str, str] = Field(description="Rango de fechas disponibles")
    
    # Estadísticas por variable
    temperature_stats: Optional[Dict[str, Any]] = None
    humidity_stats: Optional[Dict[str, Any]] = None
    pressure_stats: Optional[Dict[str, Any]] = None
    wind_speed_stats: Optional[Dict[str, Any]] = None
    wind_direction_stats: Optional[Dict[str, Any]] = None
    pm_1_stats: Optional[Dict[str, Any]] = None
    pm_2_5_stats: Optional[Dict[str, Any]] = None
    pm_10_stats: Optional[Dict[str, Any]] = None
    ica_stats: Optional[Dict[str, Any]] = None
    precipitation_stats: Optional[Dict[str, Any]] = None
    
    # Datos de calidad
    data_quality: Dict[str, Any] = Field(description="Información sobre datos faltantes e imputados")
    
    # Últimas mediciones
    latest_measurements: Optional[Dict[str, Any]] = None

class VariableInfo(BaseModel):
    """Información detallada de una variable"""
    name: str
    description: str
    unit: str
    data_type: str
    valid_range: Optional[Dict[str, float]] = None
    stations_with_data: int
    total_measurements: int
    quality_indicators: Dict[str, Any]

class ChatbotDataResponse(BaseModel):
    """Respuesta completa para el chatbot con toda la información del sistema"""
    
    # Metadatos generales
    system_info: Dict[str, Any] = Field(description="Información general del sistema")
    
    # Información de estaciones
    stations: List[StationSummary] = Field(description="Resumen completo de todas las estaciones")
    
    # Información de variables
    variables: List[VariableInfo] = Field(description="Descripción detallada de todas las variables")
    
    # Estadísticas globales
    global_stats: Dict[str, Any] = Field(description="Estadísticas generales del dataset")
    
    # Información temporal
    temporal_coverage: Dict[str, Any] = Field(description="Cobertura temporal de los datos")
    
    # Información geográfica
    geographic_coverage: Dict[str, Any] = Field(description="Cobertura geográfica de las estaciones")
    
    # Contexto para el chatbot
    context_info: Dict[str, str] = Field(description="Información contextual para el chatbot")

class ChatbotQuery(BaseModel):
    """Query específica del chatbot para obtener datos filtrados"""
    stations: Optional[List[int]] = Field(None, description="IDs de estaciones específicas")
    variables: Optional[List[str]] = Field(None, description="Variables específicas")
    date_range: Optional[Dict[str, str]] = Field(None, description="Rango de fechas")
    include_raw_data: bool = Field(False, description="Incluir datos crudos en la respuesta")
    max_records: int = Field(1000, description="Máximo número de registros a retornar")

# ==========================================
# MODELOS PARA CHAT CONVERSACIONAL
# ==========================================

class ChatMessage(BaseModel):
    """Mensaje del usuario para el chat conversacional"""
    message: str = Field(description="Mensaje del usuario")
    user_id: Optional[str] = Field(None, description="ID opcional del usuario")

class ChatResponse(BaseModel):
    """Respuesta del chatbot conversacional"""
    response: str = Field(description="Respuesta generada por el chatbot")
    timestamp: str = Field(description="Timestamp de la respuesta")
    status: str = Field(default="success", description="Estado de la respuesta")
