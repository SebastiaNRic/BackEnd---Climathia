from pydantic_settings import BaseSettings
from typing import Optional, List, Union


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Configuración de la aplicación
    app_name: str = "Weather Stations API"
    app_version: str = "1.0.0"
    debug: bool = False
    reload: bool = True
    
    # Configuración del servidor
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Configuración de CORS
    cors_origins: Union[str, List[str]] = "*"
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    # Ruta al archivo CSV
    csv_file_path: str = "datos_limpios_20251108_152228.csv"
    
    # Configuración de logging
    log_level: str = "INFO"
    
    # API Keys
    gemini_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"


# Instancia global de configuración
settings = Settings()
