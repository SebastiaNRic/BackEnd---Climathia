import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from app.models.station_data import (
    StationData, StationInfo, MapDataPoint, 
    TimeSeriesQuery, MapAnimationQuery
)

logger = logging.getLogger(__name__)


class DataService:
    """Servicio para manejar los datos de las estaciones meteorológicas"""
    
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self._df: Optional[pd.DataFrame] = None
        self._stations_cache: Optional[List[StationInfo]] = None
        
    def _load_data(self) -> pd.DataFrame:
        """Carga los datos del CSV si no están ya cargados"""
        if self._df is None:
            logger.info(f"Cargando datos desde {self.csv_path}")
            self._df = pd.read_csv(self.csv_path)
            
            # Convertir timestamp a datetime
            self._df['timestamp'] = pd.to_datetime(self._df['timestamp'])
            
            # Convertir valores 'NA' a None/NaN
            self._df = self._df.replace('NA', np.nan)
            
            # Convertir columnas booleanas
            bool_columns = [col for col in self._df.columns if col.endswith('_imputed')]
            for col in bool_columns:
                self._df[col] = self._df[col].map({'TRUE': True, 'FALSE': False})
                
            logger.info(f"Datos cargados: {len(self._df)} registros")
            
        return self._df
    
    def get_stations(self) -> List[StationInfo]:
        """Obtiene la lista de todas las estaciones únicas"""
        if self._stations_cache is None:
            df = self._load_data()
            stations_df = df[['station_id', 'station_name', 'tipo_equipo', 'lat', 'lon']].drop_duplicates()
            
            self._stations_cache = [
                StationInfo(
                    station_id=row['station_id'],
                    station_name=row['station_name'],
                    tipo_equipo=row['tipo_equipo'],
                    lat=row['lat'],
                    lon=row['lon']
                )
                for _, row in stations_df.iterrows()
            ]
            
        return self._stations_cache
    
    def get_station_data(
        self, 
        station_id: int, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[StationData]:
        """Obtiene todos los datos de una estación específica"""
        df = self._load_data()
        
        # Filtrar por estación
        station_df = df[df['station_id'] == station_id].copy()
        
        # Filtrar por fechas si se proporcionan
        if start_date:
            station_df = station_df[station_df['timestamp'] >= start_date]
        if end_date:
            station_df = station_df[station_df['timestamp'] <= end_date]
            
        # Convertir a modelos Pydantic
        return [
            StationData(**row.to_dict())
            for _, row in station_df.iterrows()
        ]
    
    def get_map_data(
        self, 
        timestamp: datetime,
        tolerance_minutes: int = 30
    ) -> List[MapDataPoint]:
        """Obtiene datos de todas las estaciones para un timestamp específico"""
        df = self._load_data()
        
        # Buscar datos dentro del rango de tolerancia
        start_time = timestamp - timedelta(minutes=tolerance_minutes)
        end_time = timestamp + timedelta(minutes=tolerance_minutes)
        
        filtered_df = df[
            (df['timestamp'] >= start_time) & 
            (df['timestamp'] <= end_time)
        ].copy()
        
        # Obtener el registro más cercano para cada estación
        closest_data = []
        for station_id in filtered_df['station_id'].unique():
            station_data = filtered_df[filtered_df['station_id'] == station_id]
            # Encontrar el registro más cercano al timestamp solicitado
            station_data['time_diff'] = abs(station_data['timestamp'] - timestamp)
            closest_record = station_data.loc[station_data['time_diff'].idxmin()]
            
            closest_data.append(MapDataPoint(
                station_id=closest_record['station_id'],
                station_name=closest_record['station_name'],
                lat=closest_record['lat'],
                lon=closest_record['lon'],
                timestamp=closest_record['timestamp'],
                temp=closest_record['temp'] if pd.notna(closest_record['temp']) else None,
                humedad=closest_record['humedad'] if pd.notna(closest_record['humedad']) else None,
                presion=closest_record['presion'] if pd.notna(closest_record['presion']) else None,
                pm_2_5=closest_record['pm_2_5'] if pd.notna(closest_record['pm_2_5']) else None,
                ica=closest_record['ica'] if pd.notna(closest_record['ica']) else None,
                precipitacion=closest_record['precipitacion'] if pd.notna(closest_record['precipitacion']) else None
            ))
            
        return closest_data
    
    def get_animation_data(self, query: MapAnimationQuery) -> Dict[str, Any]:
        """Obtiene datos para animación del mapa"""
        df = self._load_data()
        
        # Filtrar por fechas
        if query.start_date:
            df = df[df['timestamp'] >= query.start_date]
        if query.end_date:
            df = df[df['timestamp'] <= query.end_date]
            
        # Resamplear datos según el intervalo
        df_resampled = df.set_index('timestamp').groupby('station_id').resample(
            query.time_interval
        ).agg({
            'station_name': 'first',
            'lat': 'first',
            'lon': 'first',
            query.variable: 'mean'
        }).reset_index()
        
        # Organizar datos por timestamp
        animation_frames = {}
        for timestamp in df_resampled['timestamp'].unique():
            frame_data = df_resampled[df_resampled['timestamp'] == timestamp]
            
            animation_frames[timestamp.isoformat()] = [
                {
                    'station_id': row['station_id'],
                    'station_name': row['station_name'],
                    'lat': row['lat'],
                    'lon': row['lon'],
                    'value': row[query.variable] if pd.notna(row[query.variable]) else None
                }
                for _, row in frame_data.iterrows()
            ]
            
        return {
            'variable': query.variable,
            'time_interval': query.time_interval,
            'frames': animation_frames,
            'timestamps': sorted(animation_frames.keys())
        }
    
    def get_time_series(self, query: TimeSeriesQuery) -> Dict[str, Any]:
        """Obtiene series temporales para análisis"""
        df = self._load_data()
        
        # Filtrar por estaciones si se especifican
        if query.station_ids:
            df = df[df['station_id'].isin(query.station_ids)]
            
        # Filtrar por fechas
        if query.start_date:
            df = df[df['timestamp'] >= query.start_date]
        if query.end_date:
            df = df[df['timestamp'] <= query.end_date]
            
        # Seleccionar solo las variables solicitadas
        columns = ['timestamp', 'station_id', 'station_name'] + query.variables
        available_columns = [col for col in columns if col in df.columns]
        
        result_df = df[available_columns].copy()
        
        return {
            'data': result_df.to_dict('records'),
            'variables': query.variables,
            'total_records': len(result_df)
        }
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de los datos disponibles"""
        df = self._load_data()
        
        return {
            'total_records': len(df),
            'stations_count': df['station_id'].nunique(),
            'date_range': {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat()
            },
            'variables': {
                'temperature': {
                    'available': df['temp'].notna().sum(),
                    'min': df['temp'].min(),
                    'max': df['temp'].max(),
                    'mean': df['temp'].mean()
                },
                'humidity': {
                    'available': df['humedad'].notna().sum(),
                    'min': df['humedad'].min(),
                    'max': df['humedad'].max(),
                    'mean': df['humedad'].mean()
                },
                'pressure': {
                    'available': df['presion'].notna().sum(),
                    'min': df['presion'].min(),
                    'max': df['presion'].max(),
                    'mean': df['presion'].mean()
                },
                'air_quality_index': {
                    'available': df['ica'].notna().sum(),
                    'min': df['ica'].min(),
                    'max': df['ica'].max(),
                    'mean': df['ica'].mean()
                },
                'precipitation': {
                    'available': df['precipitacion'].notna().sum(),
                    'min': df['precipitacion'].min(),
                    'max': df['precipitacion'].max(),
                    'mean': df['precipitacion'].mean()
                }
            }
        }
