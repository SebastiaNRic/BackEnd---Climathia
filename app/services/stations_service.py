"""
Servicio especializado para el manejo de estaciones meteorológicas
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import logging

from app.services.data_service import DataService
from app.config.settings import settings

logger = logging.getLogger(__name__)


class StationsService:
    """Servicio especializado para operaciones con estaciones meteorológicas"""
    
    def __init__(self, csv_path: str = None):
        """
        Inicializar el servicio de estaciones
        
        Args:
            csv_path: Ruta al archivo CSV. Si no se proporciona, usa settings.csv_file_path
        """
        self.csv_path = csv_path or settings.csv_file_path
        self.data_service = DataService(self.csv_path)
        self.df = None
        self._load_data()
    
    def _load_data(self):
        """Cargar datos una vez para optimizar consultas"""
        try:
            self.df = self.data_service._load_data()
            logger.info(f"Datos cargados para servicio de estaciones: {len(self.df)} registros")
        except Exception as e:
            logger.error(f"Error cargando datos para servicio de estaciones: {e}")
            raise
    
    def get_all_stations_averages(
        self, 
        date: str, 
        variables: List[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener promedios diarios de todas las estaciones para una fecha específica
        
        Args:
            date: Fecha en formato YYYY-MM-DD
            variables: Lista de variables a promediar
            
        Returns:
            Dict con promedios por estación
        """
        if variables is None:
            variables = ['ica', 'humedad', 'pm_1', 'pm_2_5', 'pm_10', 'temp', 'precipitacion']
        
        try:
            # Convertir fecha a rango del día completo con timezone UTC
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
            
            logger.info(f"Calculando promedios para todas las estaciones entre {start_date} y {end_date}")
            
            # Filtrar datos por fecha
            if self.df is None:
                self._load_data()
            
            # Convertir timestamp a datetime si es necesario
            if not pd.api.types.is_datetime64_any_dtype(self.df['timestamp']):
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], utc=True)
            
            # Filtrar por rango de fechas
            mask = (self.df['timestamp'] >= start_date) & (self.df['timestamp'] <= end_date)
            daily_data = self.df[mask].copy()
            
            if daily_data.empty:
                logger.warning(f"No se encontraron datos para la fecha {date}")
                return {
                    "date": date,
                    "total_stations": 0,
                    "stations_with_data": 0,
                    "stations": []
                }
            
            logger.info(f"Encontrados {len(daily_data)} registros para la fecha {date}")
            
            # Obtener estaciones únicas
            unique_stations = daily_data['station_id'].unique()
            logger.info(f"Procesando {len(unique_stations)} estaciones")
            
            stations_data = []
            
            for station_id in unique_stations:
                station_data = daily_data[daily_data['station_id'] == station_id]
                
                if station_data.empty:
                    continue
                
                # Obtener información básica de la estación
                station_info = station_data.iloc[0]
                
                # Calcular promedios para esta estación
                averages = {}
                for variable in variables:
                    if variable in station_data.columns:
                        # Filtrar valores válidos (no NaN, no None)
                        valid_values = station_data[variable].dropna()
                        
                        if not valid_values.empty:
                            avg_value = valid_values.mean()
                            averages[variable] = {
                                "average": round(avg_value, 2),
                                "count": len(valid_values),
                                "min": round(valid_values.min(), 2),
                                "max": round(valid_values.max(), 2)
                            }
                        else:
                            averages[variable] = None
                    else:
                        averages[variable] = None
                
                # Formato compatible con MapComponent
                formatted_averages = {
                    "temp": self._get_average_value(averages.get("temp")),
                    "hum": self._get_average_value(averages.get("humedad")),
                    "pm_1p0": self._get_average_value(averages.get("pm_1")),
                    "pm_2p5": self._get_average_value(averages.get("pm_2_5")),
                    "pm_10p0": self._get_average_value(averages.get("pm_10")),
                    "ica": self._get_average_value(averages.get("ica")),
                    "precipitacion": self._get_average_value(averages.get("precipitacion")),
                    "ts": None
                }
                
                station_result = {
                    "station_id": int(station_id),
                    "station_name": station_info.get('station_name', f'Estación {station_id}'),
                    "lat": float(station_info.get('lat', 0)),
                    "lon": float(station_info.get('lon', 0)),
                    "tipo_equipo": station_info.get('tipo_equipo', 'UNKNOWN'),
                    "record_count": len(station_data),
                    "raw_averages": averages,
                    "data": formatted_averages  # Para compatibilidad con MapComponent
                }
                
                stations_data.append(station_result)
            
            result = {
                "date": date,
                "total_stations": len(unique_stations),
                "stations_with_data": len(stations_data),
                "variables": variables,
                "stations": stations_data
            }
            
            logger.info(f"Procesamiento completado: {len(stations_data)} estaciones con datos")
            return result
            
        except Exception as e:
            logger.error(f"Error calculando promedios para todas las estaciones: {e}")
            raise
    
    def get_station_averages(
        self, 
        station_id: int, 
        date: str, 
        variables: List[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener promedios de una estación específica (método de conveniencia)
        
        Args:
            station_id: ID de la estación
            date: Fecha en formato YYYY-MM-DD
            variables: Lista de variables a promediar
            
        Returns:
            Dict con promedios de la estación
        """
        all_averages = self.get_all_stations_averages(date, variables)
        
        # Buscar la estación específica
        for station in all_averages.get("stations", []):
            if station["station_id"] == station_id:
                return {
                    "station_id": station_id,
                    "date": date,
                    "record_count": station["record_count"],
                    "raw_averages": station["raw_averages"],
                    "formatted_averages": station["data"],
                    "data": station["data"]
                }
        
        # Si no se encuentra la estación
        return {
            "station_id": station_id,
            "date": date,
            "message": "No hay datos disponibles para esta estación en la fecha especificada",
            "record_count": 0,
            "data": None
        }
    
    def _get_average_value(self, avg_dict: Dict) -> Optional[float]:
        """
        Extraer el valor promedio de un diccionario de estadísticas
        
        Args:
            avg_dict: Diccionario con estadísticas o None
            
        Returns:
            Valor promedio redondeado a 2 decimales o None
        """
        if avg_dict and avg_dict.get("average") is not None:
            return round(avg_dict["average"], 2)
        return None
    
    def get_stations_summary(self) -> Dict[str, Any]:
        """
        Obtener resumen de todas las estaciones disponibles
        
        Para estaciones duplicadas (mismo station_id), prioriza:
        1. VUE+AIR (si existe)
        2. PRO (si no hay VUE+AIR)
        3. AIR (solo si no hay otros tipos)
        
        Returns:
            Dict con información de estaciones sin duplicados
        """
        try:
            if self.df is None:
                self._load_data()
            
            # Definir orden de prioridad para tipos de equipo
            priority_order = {'VUE+AIR': 1, 'PRO': 2, 'AIR': 3}
            
            # Crear copia del DataFrame para no modificar el original
            df_temp = self.df.copy()
            
            # Agregar columna de prioridad
            df_temp['priority'] = df_temp['tipo_equipo'].map(priority_order).fillna(999)
            
            # Para cada station_id, tomar el registro con mayor prioridad (menor número)
            stations_info = (df_temp.sort_values(['station_id', 'priority'])
                           .groupby('station_id')
                           .first()
                           .reset_index())
            
            stations_list = []
            for _, station in stations_info.iterrows():
                stations_list.append({
                    "station_id": int(station['station_id']),
                    "station_name": station.get('station_name', f'Estación {station["station_id"]}'),
                    "lat": float(station.get('lat', 0)),
                    "lon": float(station.get('lon', 0)),
                    "tipo_equipo": station.get('tipo_equipo', 'UNKNOWN')
                })
            
            logger.info(f"Procesadas {len(stations_list)} estaciones únicas (sin duplicados)")
            
            return {
                "total_stations": len(stations_list),
                "stations": stations_list
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de estaciones: {e}")
            raise
    
    def get_airlink_stations_summary(self) -> Dict[str, Any]:
        """
        Obtener resumen de estaciones AirLink puras únicamente
        
        Excluye estaciones que tengan CUALQUIER registro con VUE+AIR,
        solo incluye estaciones que sean exclusivamente AIR.
        
        Returns:
            Dict con información de estaciones AirLink puras solamente
        """
        try:
            if self.df is None:
                self._load_data()
            
            # Encontrar station_ids que tienen registros VUE+AIR
            stations_with_vue = set(self.df[self.df['tipo_equipo'] == 'VUE+AIR']['station_id'].unique())
            
            # Filtrar estaciones que:
            # 1. Son tipo AIR
            # 2. NO tienen ningún registro VUE+AIR
            airlink_mask = (
                (self.df['tipo_equipo'] == 'AIR') & 
                (~self.df['station_id'].isin(stations_with_vue))
            )
            airlink_df = self.df[airlink_mask]
            
            if airlink_df.empty:
                logger.warning("No se encontraron estaciones AirLink puras (sin VUE+AIR)")
                return {
                    "total_stations": 0,
                    "stations": []
                }
            
            # Obtener estaciones únicas
            stations_info = airlink_df.groupby('station_id').first().reset_index()
            
            stations_list = []
            for _, station in stations_info.iterrows():
                stations_list.append({
                    "station_id": int(station['station_id']),
                    "station_name": station.get('station_name', f'Estación AirLink {station["station_id"]}'),
                    "lat": float(station.get('lat', 0)),
                    "lon": float(station.get('lon', 0)),
                    "tipo_equipo": station.get('tipo_equipo', 'AIR')
                })
            
            logger.info(f"Encontradas {len(stations_list)} estaciones AirLink puras (excluidas {len(stations_with_vue)} con VUE+AIR)")
            
            return {
                "total_stations": len(stations_list),
                "stations": stations_list
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estaciones AirLink: {e}")
            raise
    
    def get_station_detailed_data(self, station_id: int, date: str) -> Dict[str, Any]:
        """
        Obtener datos detallados de una estación para gráficos
        
        Args:
            station_id: ID de la estación
            date: Fecha en formato YYYY-MM-DD
            
        Returns:
            Dict con todas las mediciones del día con timestamps en milisegundos
        """
        try:
            # Convertir fecha a rango del día completo con timezone UTC
            target_date = datetime.strptime(date, "%Y-%m-%d")
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
            
            logger.info(f"Obteniendo datos detallados para estación {station_id} entre {start_date} y {end_date}")
            
            # Filtrar datos por fecha y estación
            if self.df is None:
                self._load_data()
            
            # Convertir timestamp a datetime si es necesario
            if not pd.api.types.is_datetime64_any_dtype(self.df['timestamp']):
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], utc=True)
            
            # Filtrar por estación y rango de fechas
            mask = (
                (self.df['station_id'] == station_id) & 
                (self.df['timestamp'] >= start_date) & 
                (self.df['timestamp'] <= end_date)
            )
            station_data = self.df[mask].copy()
            
            if station_data.empty:
                logger.warning(f"No se encontraron datos para estación {station_id} en fecha {date}")
                return {
                    "success": True,
                    "data": {
                        "station_id": station_id,
                        "date": date,
                        "measurements": []
                    }
                }
            
            logger.info(f"Encontrados {len(station_data)} registros para estación {station_id}")
            
            # Ordenar por timestamp
            station_data = station_data.sort_values('timestamp')
            
            # Convertir a lista de mediciones
            measurements = []
            for _, row in station_data.iterrows():
                # Convertir timestamp a milisegundos
                timestamp_ms = int(row['timestamp'].timestamp() * 1000)
                
                # Crear medición con todos los datos disponibles
                measurement = {
                    "timestamp": timestamp_ms,
                    "pm_1": self._format_value(row.get('pm_1')),
                    "pm_2_5": self._format_value(row.get('pm_2_5')),
                    "pm_10": self._format_value(row.get('pm_10')),
                    "humedad": self._format_value(row.get('humedad')),
                    "ica": self._format_value(row.get('ica')),
                    "temperatura": self._format_value(row.get('temp')),
                    "presion": self._format_value(row.get('presion')),
                    "vel_viento": self._format_value(row.get('viento_vel')),
                    "dir_viento": self._format_value(row.get('viento_dir')),
                    "precipitacion": self._format_value(row.get('precipitacion'))
                }
                
                measurements.append(measurement)
            
            # Obtener información básica de la estación
            station_info = station_data.iloc[0]
            
            result = {
                "success": True,
                "data": {
                    "station_id": station_id,
                    "station_name": station_info.get('station_name', f'Estación {station_id}'),
                    "date": date,
                    "total_measurements": len(measurements),
                    "measurements": measurements
                }
            }
            
            logger.info(f"Datos detallados procesados: {len(measurements)} mediciones para estación {station_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo datos detallados para estación {station_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {
                    "station_id": station_id,
                    "date": date,
                    "measurements": []
                }
            }
    
    def _format_value(self, value) -> Optional[float]:
        """
        Formatear un valor numérico para los gráficos
        
        Args:
            value: Valor a formatear
            
        Returns:
            Valor redondeado a 2 decimales o None si es inválido
        """
        if value is None or pd.isna(value):
            return None
        
        try:
            num_value = float(value)
            if np.isnan(num_value) or np.isinf(num_value):
                return None
            return round(num_value, 2)
        except (ValueError, TypeError):
            return None
