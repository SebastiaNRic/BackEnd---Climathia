from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum
import math


class TipoEquipo(str, Enum):
    PRO = "PRO"
    VUE_AIR = "VUE+AIR"
    AIR = "AIR"


class StationData(BaseModel):
    """Modelo para los datos de una estación meteorológica"""
    timestamp: datetime
    station_id: int
    station_name: str
    tipo_equipo: TipoEquipo
    lat: float = Field(..., description="Latitud de la estación")
    lon: float = Field(..., description="Longitud de la estación")
    temp: Optional[float] = Field(None, description="Temperatura en °C")
    humedad: Optional[float] = Field(None, description="Humedad relativa %")
    presion: Optional[float] = Field(None, description="Presión atmosférica")
    viento_vel: Optional[float] = Field(None, description="Velocidad del viento")
    viento_dir: Optional[float] = Field(None, description="Dirección del viento")
    pm_1: Optional[float] = Field(None, description="Partículas PM1")
    pm_2_5: Optional[float] = Field(None, description="Partículas PM2.5")
    pm_10: Optional[float] = Field(None, description="Partículas PM10")
    ica: Optional[float] = Field(None, description="Índice de Calidad del Aire")
    precipitacion: Optional[float] = Field(None, description="Precipitación en mm")
    temp_imputed: Optional[bool] = False
    humedad_imputed: Optional[bool] = False
    presion_imputed: Optional[bool] = False
    viento_vel_imputed: Optional[bool] = False
    viento_dir_imputed: Optional[bool] = False
    ica_imputed: Optional[bool] = False
    precipitacion_imputed: Optional[bool] = False

    @field_validator('temp_imputed', 'humedad_imputed', 'presion_imputed', 
                    'viento_vel_imputed', 'viento_dir_imputed', 'ica_imputed', 
                    'precipitacion_imputed', mode='before')
    @classmethod
    def validate_imputed_fields(cls, v):
        """Validar campos *_imputed convirtiendo NaN a False"""
        if v is None:
            return False
        if isinstance(v, float) and math.isnan(v):
            return False
        if isinstance(v, str):
            if v.lower() in ('true', '1', 'yes', 'y'):
                return True
            elif v.lower() in ('false', '0', 'no', 'n', ''):
                return False
            else:
                return False
        return bool(v)

    @field_validator('temp', 'humedad', 'presion', 'viento_vel', 'viento_dir', 
                    'pm_1', 'pm_2_5', 'pm_10', 'ica', 'precipitacion', mode='before')
    @classmethod
    def validate_numeric_fields(cls, v):
        """Validar campos numéricos convirtiendo NaN a None"""
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        if isinstance(v, str) and v.strip() == '':
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StationInfo(BaseModel):
    """Información básica de una estación"""
    station_id: int
    station_name: str
    tipo_equipo: TipoEquipo
    lat: float
    lon: float


class MapDataPoint(BaseModel):
    """Punto de datos optimizado para el mapa animado"""
    station_id: int
    station_name: str
    lat: float
    lon: float
    timestamp: datetime
    temp: Optional[float] = None
    humedad: Optional[float] = None
    presion: Optional[float] = None
    pm_2_5: Optional[float] = None
    ica: Optional[float] = None
    precipitacion: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TimeSeriesQuery(BaseModel):
    """Parámetros para consultas de series temporales"""
    station_ids: Optional[List[int]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    variables: Optional[List[str]] = Field(
        default=["temp", "humedad", "presion", "pm_2_5", "ica", "precipitacion"],
        description="Variables a incluir en la respuesta"
    )


class MapAnimationQuery(BaseModel):
    """Parámetros para la animación del mapa"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    time_interval: Optional[str] = Field(
        default="1H",
        description="Intervalo de tiempo (15min, 30min, 1H, etc.)"
    )
    variable: str = Field(
        default="temp",
        description="Variable a mostrar en el mapa"
    )
