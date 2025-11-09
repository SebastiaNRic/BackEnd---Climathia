from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from typing import List, Optional
import logging

from app.models.station_data import (
    StationInfo, StationData, MapDataPoint, 
    TimeSeriesQuery, MapAnimationQuery
)
from app.services.data_service import DataService
from app.services.stations_service import StationsService
from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stations", tags=["stations"])

# Dependency para obtener el servicio de datos
def get_data_service() -> DataService:
    # Usar la configuración para obtener la ruta del CSV
    return DataService(settings.csv_file_path)

# Dependency para obtener el servicio de estaciones
def get_stations_service() -> StationsService:
    # Usar la configuración para obtener la ruta del CSV
    return StationsService(settings.csv_file_path)


@router.get("/", response_model=List[StationInfo])
async def get_all_stations(
    data_service: DataService = Depends(get_data_service)
):
    """Obtiene la lista de todas las estaciones disponibles"""
    try:
        stations = data_service.get_stations()
        return stations
    except Exception as e:
        logger.error(f"Error obteniendo estaciones: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/airlink")
async def get_airlink_stations(
    stations_service: StationsService = Depends(get_stations_service)
):
    """
    📡 Obtiene la lista de estaciones AirLink únicamente
    
    Perfecto para selectores y gráficos que solo necesitan estaciones AirLink.
    El mapa seguirá usando el endpoint principal que incluye todas las estaciones.
    """
    try:
        logger.info("Obteniendo lista de estaciones AirLink")
        stations = stations_service.get_airlink_stations_summary()
        logger.info(f"Encontradas {stations['total_stations']} estaciones AirLink")
        return stations
    except Exception as e:
        logger.error(f"Error obteniendo estaciones AirLink: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{station_id}", response_model=List[StationData])
async def get_station_data(
    station_id: int,
    start_date: Optional[datetime] = Query(None, description="Fecha de inicio (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Fecha de fin (ISO format)"),
    data_service: DataService = Depends(get_data_service)
):
    """Obtiene todos los datos de una estación específica"""
    try:
        data = data_service.get_station_data(station_id, start_date, end_date)
        if not data:
            raise HTTPException(status_code=404, detail="Estación no encontrada")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo datos de estación {station_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/map/snapshot", response_model=List[MapDataPoint])
async def get_map_snapshot(
    timestamp: datetime = Query(..., description="Timestamp para el snapshot (ISO format)"),
    tolerance_minutes: int = Query(30, description="Tolerancia en minutos para buscar datos"),
    data_service: DataService = Depends(get_data_service)
):
    """Obtiene un snapshot de todas las estaciones para un momento específico"""
    try:
        map_data = data_service.get_map_data(timestamp, tolerance_minutes)
        return map_data
    except Exception as e:
        logger.error(f"Error obteniendo snapshot del mapa: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/map/animation")
async def get_animation_data(
    query: MapAnimationQuery,
    data_service: DataService = Depends(get_data_service)
):
    """Obtiene datos para animación del mapa"""
    try:
        animation_data = data_service.get_animation_data(query)
        return animation_data
    except Exception as e:
        logger.error(f"Error obteniendo datos de animación: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/timeseries")
async def get_time_series(
    query: TimeSeriesQuery,
    data_service: DataService = Depends(get_data_service)
):
    """Obtiene series temporales para análisis"""
    try:
        timeseries_data = data_service.get_time_series(query)
        return timeseries_data
    except Exception as e:
        logger.error(f"Error obteniendo series temporales: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/summary/data")
async def get_data_summary(
    data_service: DataService = Depends(get_data_service)
):
    """Obtiene un resumen de los datos disponibles"""
    try:
        summary = data_service.get_data_summary()
        return summary
    except Exception as e:
        logger.error(f"Error obteniendo resumen de datos: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/averages")
async def get_all_stations_averages(
    date: str = Query(..., description="Fecha específica (YYYY-MM-DD)"),
    variables: Optional[str] = Query("ica,humedad,pm_1,pm_2_5,pm_10,temp,precipitacion", description="Variables a promediar"),
    stations_service: StationsService = Depends(get_stations_service)
):
    """
    🗺️ ENDPOINT PRINCIPAL PARA EL MAPA
    
    Obtiene promedios diarios de TODAS las estaciones para una fecha específica.
    Perfecto para mostrar información completa en el mapa.
    
    Args:
        date: Fecha en formato YYYY-MM-DD
        variables: Variables a promediar (separadas por comas)
        
    Returns:
        Dict con promedios de todas las estaciones
    """
    try:
        # Parsear variables
        variable_list = [v.strip() for v in variables.split(',')]
        
        logger.info(f"Obteniendo promedios de todas las estaciones para fecha: {date}")
        
        # Obtener promedios de todas las estaciones
        result = stations_service.get_all_stations_averages(date, variable_list)
        
        logger.info(f"Procesadas {result['stations_with_data']} estaciones con datos de {result['total_stations']} totales")
        
        return result
        
    except ValueError as e:
        logger.error(f"Formato de fecha inválido: {date}: {e}")
        raise HTTPException(status_code=400, detail=f"Formato de fecha inválido: {e}")
    except Exception as e:
        logger.error(f"Error obteniendo promedios de todas las estaciones: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {type(e).__name__}")


@router.get("/{station_id}/detailed-data")
async def get_station_detailed_data(
    station_id: int,
    date: str = Query(..., description="Fecha específica (YYYY-MM-DD)"),
    stations_service: StationsService = Depends(get_stations_service)
):
    """
    📊 ENDPOINT PARA DATOS DE GRÁFICOS
    
    Obtiene todas las mediciones detalladas de una estación para una fecha específica.
    Perfecto para gráficos de PM, Humedad, ICA, etc.
    
    Args:
        station_id: ID de la estación
        date: Fecha en formato YYYY-MM-DD
        
    Returns:
        Dict con todas las mediciones del día con timestamps
    """
    try:
        logger.info(f"Obteniendo datos detallados para estación {station_id} en fecha: {date}")
        
        # Usar el servicio de estaciones para obtener datos detallados
        result = stations_service.get_station_detailed_data(station_id, date)
        
        logger.info(f"Datos detallados para estación {station_id}: {len(result.get('data', {}).get('measurements', []))} mediciones")
        
        return result
        
    except ValueError as e:
        logger.error(f"Formato de fecha inválido para estación {station_id}, fecha {date}: {e}")
        raise HTTPException(status_code=400, detail=f"Formato de fecha inválido: {e}")
    except Exception as e:
        logger.error(f"Error obteniendo datos detallados para estación {station_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {type(e).__name__}")


@router.get("/{station_id}/averages")
async def get_station_daily_averages(
    station_id: int,
    date: str = Query(..., description="Fecha específica (YYYY-MM-DD)"),
    variables: Optional[str] = Query("ica,humedad,pm_1,pm_2_5,pm_10,temp,precipitacion", description="Variables a promediar"),
    stations_service: StationsService = Depends(get_stations_service)
):
    """
    Obtiene promedios diarios de una estación específica
    
    Usa el nuevo StationsService para obtener datos de una estación individual.
    Mantiene compatibilidad con el MapComponent del frontend.
    """
    try:
        # Parsear variables
        variable_list = [v.strip() for v in variables.split(',')]
        
        logger.info(f"Obteniendo promedios para estación {station_id} en fecha: {date}")
        
        # Usar el nuevo servicio de estaciones
        result = stations_service.get_station_averages(station_id, date, variable_list)
        
        logger.info(f"Resultado para estación {station_id}: {result.get('record_count', 0)} registros")
        
        return result
        
    except ValueError as e:
        logger.error(f"Formato de fecha inválido para estación {station_id}, fecha {date}: {e}")
        raise HTTPException(status_code=400, detail=f"Formato de fecha inválido: {e}")
    except AttributeError as e:
        logger.error(f"Error de atributo para estación {station_id}: {e}")
        raise HTTPException(status_code=500, detail="Error procesando datos de la estación")
    except TypeError as e:
        logger.error(f"Error de tipo de datos para estación {station_id}: {e}")
        raise HTTPException(status_code=500, detail="Error en el formato de datos")
    except Exception as e:
        logger.error(f"Error inesperado calculando promedios para estación {station_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {type(e).__name__}")
