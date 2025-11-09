import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import os
import re
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from app.models.chatbot_data import (
    ChatbotDataResponse, StationSummary, VariableInfo, ChatbotQuery
)
from app.services.data_service import DataService
from app.config.settings import settings

logger = logging.getLogger(__name__)

class ChatbotService:
    """Servicio especializado para proporcionar datos completos al chatbot"""
    
    def __init__(self, csv_path: str):
        self.data_service = DataService(csv_path)
        self.df = None
        
        # ✅ Usar settings en lugar de os.getenv directamente
        self.gemini_api_key = settings.gemini_api_key
        self.has_gemini = bool(self.gemini_api_key)
        self._load_data()
        
        # Debug temporal para verificar la carga
        if self.has_gemini:
            logger.info(f"✅ Gemini API key configurada correctamente (termina en: ...{self.gemini_api_key[-4:]})")
        else:
            logger.warning("⚠️ Gemini API key no configurada - solo respuestas heurísticas disponibles")
            logger.debug(f"Valor desde settings.gemini_api_key: {repr(self.gemini_api_key)}")
            logger.debug(f"Valor desde os.getenv: {repr(os.getenv('GEMINI_API_KEY'))}")
    
    def _load_data(self):
        """Carga los datos una vez para optimizar consultas"""
        try:
            self.df = self.data_service._load_data()
            logger.info(f"Datos cargados para chatbot: {len(self.df)} registros")
        except Exception as e:
            logger.error(f"Error cargando datos para chatbot: {e}")
            raise
    
    def get_complete_data_for_chatbot(self) -> ChatbotDataResponse:
        """Obtiene todos los datos estructurados para el chatbot"""
        
        # Información del sistema
        system_info = {
            "name": "Weather Stations API",
            "description": "Sistema de monitoreo de estaciones meteorológicas",
            "version": "1.0.0",
            "total_records": len(self.df),
            "last_updated": datetime.now().isoformat(),
            "data_source": "CSV processed data"
        }
        
        # Resumen de estaciones
        stations = self._get_stations_summary()
        
        # Información de variables
        variables = self._get_variables_info()
        
        # Estadísticas globales
        global_stats = self._get_global_statistics()
        
        # Cobertura temporal
        temporal_coverage = self._get_temporal_coverage()
        
        # Cobertura geográfica
        geographic_coverage = self._get_geographic_coverage()
        
        # Contexto para el chatbot
        context_info = self._get_context_info()
        
        return ChatbotDataResponse(
            system_info=system_info,
            stations=stations,
            variables=variables,
            global_stats=global_stats,
            temporal_coverage=temporal_coverage,
            geographic_coverage=geographic_coverage,
            context_info=context_info
        )
    
    def _get_stations_summary(self) -> List[StationSummary]:
        """Genera resumen completo de cada estación"""
        stations = []
        
        for station_id in self.df['station_id'].unique():
            station_data = self.df[self.df['station_id'] == station_id]
            
            # Información básica
            station_info = station_data.iloc[0]
            
            # Estadísticas por variable
            station_summary = StationSummary(
                station_id=int(station_id),
                station_name=station_info['station_name'],
                tipo_equipo=station_info['tipo_equipo'],
                location={
                    "latitude": float(station_info['lat']),
                    "longitude": float(station_info['lon'])
                },
                total_records=len(station_data),
                date_range={
                    "start": station_data['timestamp'].min().isoformat(),
                    "end": station_data['timestamp'].max().isoformat()
                },
                temperature_stats=self._get_variable_stats(station_data, 'temp'),
                humidity_stats=self._get_variable_stats(station_data, 'humedad'),
                pressure_stats=self._get_variable_stats(station_data, 'presion'),
                wind_speed_stats=self._get_variable_stats(station_data, 'viento_vel'),
                wind_direction_stats=self._get_variable_stats(station_data, 'viento_dir'),
                pm_1_stats=self._get_variable_stats(station_data, 'pm_1'),
                pm_2_5_stats=self._get_variable_stats(station_data, 'pm_2_5'),
                pm_10_stats=self._get_variable_stats(station_data, 'pm_10'),
                ica_stats=self._get_variable_stats(station_data, 'ica'),
                precipitation_stats=self._get_variable_stats(station_data, 'precipitacion'),
                data_quality=self._get_data_quality_info(station_data),
                latest_measurements=self._get_latest_measurements(station_data)
            )
            
            stations.append(station_summary)
        
        return stations
    
    def _get_variable_stats(self, data: pd.DataFrame, variable: str) -> Optional[Dict[str, Any]]:
        """Calcula estadísticas para una variable específica"""
        if variable not in data.columns:
            return None
        
        series = data[variable].dropna()
        if len(series) == 0:
            return None
        
        return {
            "count": len(series),
            "mean": float(series.mean()),
            "median": float(series.median()),
            "std": float(series.std()),
            "min": float(series.min()),
            "max": float(series.max()),
            "percentile_25": float(series.quantile(0.25)),
            "percentile_75": float(series.quantile(0.75)),
            "missing_count": data[variable].isna().sum(),
            "missing_percentage": float((data[variable].isna().sum() / len(data)) * 100)
        }
    
    def _get_variables_info(self) -> List[VariableInfo]:
        """Información detallada de todas las variables"""
        variables_config = {
            "temp": {
                "description": "Temperatura exterior",
                "unit": "°C",
                "data_type": "float",
                "valid_range": {"min": -10, "max": 50}
            },
            "humedad": {
                "description": "Humedad relativa",
                "unit": "%",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 100}
            },
            "presion": {
                "description": "Presión atmosférica a nivel del mar",
                "unit": "hPa",
                "data_type": "float",
                "valid_range": {"min": 900, "max": 1100}
            },
            "viento_vel": {
                "description": "Velocidad media del viento",
                "unit": "km/h",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 60}
            },
            "viento_dir": {
                "description": "Dirección media del viento",
                "unit": "grados",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 360}
            },
            "pm_1": {
                "description": "Partículas PM1.0",
                "unit": "μg/m³",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 500}
            },
            "pm_2_5": {
                "description": "Partículas PM2.5",
                "unit": "μg/m³",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 500}
            },
            "pm_10": {
                "description": "Partículas PM10",
                "unit": "μg/m³",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 500}
            },
            "ica": {
                "description": "Índice de Calidad del Aire (AQI)",
                "unit": "índice",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 500}
            },
            "precipitacion": {
                "description": "Precipitación acumulada",
                "unit": "mm",
                "data_type": "float",
                "valid_range": {"min": 0, "max": 200}
            }
        }
        
        variables = []
        for var_name, config in variables_config.items():
            if var_name in self.df.columns:
                series = self.df[var_name]
                
                variables.append(VariableInfo(
                    name=var_name,
                    description=config["description"],
                    unit=config["unit"],
                    data_type=config["data_type"],
                    valid_range=config.get("valid_range"),
                    stations_with_data=self.df[self.df[var_name].notna()]['station_id'].nunique(),
                    total_measurements=series.notna().sum(),
                    quality_indicators={
                        "total_records": len(series),
                        "missing_records": series.isna().sum(),
                        "missing_percentage": float((series.isna().sum() / len(series)) * 100),
                        "has_imputed_flag": f"{var_name}_imputed" in self.df.columns
                    }
                ))
        
        return variables
    
    def _get_global_statistics(self) -> Dict[str, Any]:
        """Estadísticas globales del dataset"""
        return {
            "total_stations": self.df['station_id'].nunique(),
            "total_records": len(self.df),
            "equipment_types": self.df['tipo_equipo'].value_counts().to_dict(),
            "date_range": {
                "start": self.df['timestamp'].min().isoformat(),
                "end": self.df['timestamp'].max().isoformat(),
                "days_covered": (self.df['timestamp'].max() - self.df['timestamp'].min()).days
            },
            "data_completeness": {
                var: float(100 - (self.df[var].isna().sum() / len(self.df)) * 100)
                for var in ['temp', 'humedad', 'presion', 'pm_2_5', 'ica', 'precipitacion']
                if var in self.df.columns
            }
        }
    
    def _get_temporal_coverage(self) -> Dict[str, Any]:
        """Información sobre cobertura temporal"""
        df_temporal = self.df.copy()
        df_temporal['date'] = df_temporal['timestamp'].dt.date
        df_temporal['hour'] = df_temporal['timestamp'].dt.hour
        
        return {
            "total_days": df_temporal['date'].nunique(),
            "measurements_per_day": df_temporal.groupby('date').size().describe().to_dict(),
            "hourly_distribution": df_temporal['hour'].value_counts().sort_index().to_dict(),
            "gaps_analysis": self._analyze_temporal_gaps()
        }
    
    def _get_geographic_coverage(self) -> Dict[str, Any]:
        """Información sobre cobertura geográfica"""
        stations_geo = self.df.groupby('station_id').agg({
            'lat': 'first',
            'lon': 'first',
            'station_name': 'first'
        }).reset_index()
        
        return {
            "bounding_box": {
                "north": float(stations_geo['lat'].max()),
                "south": float(stations_geo['lat'].min()),
                "east": float(stations_geo['lon'].max()),
                "west": float(stations_geo['lon'].min())
            },
            "center_point": {
                "latitude": float(stations_geo['lat'].mean()),
                "longitude": float(stations_geo['lon'].mean())
            },
            "stations_by_region": self._group_stations_by_region(stations_geo)
        }
    
    def _get_context_info(self) -> Dict[str, str]:
        """Información contextual para el chatbot"""
        return {
            "purpose": "Este sistema monitorea estaciones meteorológicas con datos de calidad del aire y clima",
            "data_types": "Incluye temperatura, humedad, presión, viento, partículas PM, índice de calidad del aire y precipitación",
            "geographic_scope": "Red de estaciones distribuidas geográficamente",
            "temporal_scope": f"Datos desde {self.df['timestamp'].min().strftime('%Y-%m-%d')} hasta {self.df['timestamp'].max().strftime('%Y-%m-%d')}",
            "data_quality": "Datos procesados con imputación de valores faltantes y limpieza de outliers",
            "usage_notes": "Los datos pueden tener valores imputados marcados con flags específicos"
        }
    
    def _get_data_quality_info(self, station_data: pd.DataFrame) -> Dict[str, Any]:
        """Información de calidad de datos para una estación"""
        imputed_flags = [col for col in station_data.columns if col.endswith('_imputed')]
        
        quality_info = {
            "total_records": len(station_data),
            "imputed_data": {}
        }
        
        for flag in imputed_flags:
            var_name = flag.replace('_imputed', '')
            if var_name in station_data.columns:
                quality_info["imputed_data"][var_name] = {
                    "imputed_count": station_data[flag].sum(),
                    "imputed_percentage": float((station_data[flag].sum() / len(station_data)) * 100)
                }
        
        return quality_info
    
    def _get_latest_measurements(self, station_data: pd.DataFrame) -> Dict[str, Any]:
        """Últimas mediciones de una estación"""
        latest = station_data.loc[station_data['timestamp'].idxmax()]
        
        measurements = {
            "timestamp": latest['timestamp'].isoformat(),
            "measurements": {}
        }
        
        for var in ['temp', 'humedad', 'presion', 'viento_vel', 'pm_2_5', 'ica', 'precipitacion']:
            if var in latest and pd.notna(latest[var]):
                measurements["measurements"][var] = float(latest[var])
        
        return measurements
    
    def _analyze_temporal_gaps(self) -> Dict[str, Any]:
        """Analiza gaps temporales en los datos"""
        # Simplificado - podrías expandir esto
        return {
            "analysis": "Análisis de gaps temporales disponible",
            "method": "Detección de intervalos faltantes entre mediciones"
        }
    
    def _group_stations_by_region(self, stations_geo: pd.DataFrame) -> Dict[str, int]:
        """Agrupa estaciones por región geográfica"""
        # Simplificado - podrías usar clustering geográfico real
        return {
            "total_stations": len(stations_geo),
            "geographic_distribution": "Distribuidas en la región de estudio"
        }
    
    def get_filtered_data(self, query: ChatbotQuery) -> Dict[str, Any]:
        """Obtiene datos filtrados según query del chatbot"""
        df_filtered = self.df.copy()
        
        # Filtrar por estaciones
        if query.stations:
            df_filtered = df_filtered[df_filtered['station_id'].isin(query.stations)]
        
        # Filtrar por rango de fechas
        if query.date_range:
            if 'start' in query.date_range:
                start_date = pd.to_datetime(query.date_range['start'])
                df_filtered = df_filtered[df_filtered['timestamp'] >= start_date]
            if 'end' in query.date_range:
                end_date = pd.to_datetime(query.date_range['end'])
                df_filtered = df_filtered[df_filtered['timestamp'] <= end_date]
        
        # Seleccionar variables
        if query.variables:
            base_cols = ['timestamp', 'station_id', 'station_name', 'lat', 'lon']
            selected_cols = base_cols + [var for var in query.variables if var in df_filtered.columns]
            df_filtered = df_filtered[selected_cols]
        
        # Limitar registros
        if len(df_filtered) > query.max_records:
            df_filtered = df_filtered.sample(n=query.max_records)
        
        result = {
            "total_records": len(df_filtered),
            "stations_count": df_filtered['station_id'].nunique(),
            "date_range": {
                "start": df_filtered['timestamp'].min().isoformat(),
                "end": df_filtered['timestamp'].max().isoformat()
            }
        }
        
        if query.include_raw_data:
            result["data"] = df_filtered.to_dict('records')
        
        return result

    # ==========================================
    # SISTEMA HÍBRIDO DE RESPUESTAS
    # ==========================================
    
    async def responder_pregunta(self, pregunta: str) -> str:
        """
        Sistema híbrido: Primero intenta respuestas heurísticas, 
        luego usa Gemini para preguntas abiertas sobre clima
        """
        try:
            # 1. Intentar respuesta heurística primero
            respuesta_heuristica = self._responder_heuristico(pregunta)
            if respuesta_heuristica:
                logger.info(f"Respuesta heurística encontrada para: '{pregunta}'")
                return respuesta_heuristica
            
            # 2. Si no hay respuesta heurística, usar Gemini
            if self.has_gemini:
                logger.info(f"Usando Gemini para pregunta abierta: '{pregunta}'")
                return await self._responder_con_gemini(pregunta)
            else:
                # 3. Fallback si no hay Gemini
                return self._respuesta_fallback(pregunta)
                
        except Exception as e:
            logger.error(f"Error respondiendo pregunta '{pregunta}': {e}")
            return "Lo siento, ocurrió un error procesando tu pregunta. ¿Puedes intentar de nuevo?"

    def _responder_heuristico(self, pregunta: str) -> Optional[str]:
        """Respuestas heurísticas basadas en patrones predefinidos"""
        pregunta_lower = pregunta.lower().strip()
        
        # Base de conocimiento heurística
        respuestas_heuristicas = {
            # Saludos
            "hola": "¡Hola! 👋 Soy tu asistente de datos climáticos. ¿En qué puedo ayudarte?",
            "buenos días": "¡Buenos días! ☀️ ¿Qué información climática necesitas hoy?",
            "buenas tardes": "¡Buenas tardes! 🌤️ ¿Cómo puedo ayudarte con los datos meteorológicos?",
            
            # Preguntas básicas sobre el sistema
            "cuántas estaciones hay": f"Tenemos {self.df['station_id'].nunique()} estaciones meteorológicas monitoreando la región.",
            "cuantas estaciones hay": f"Tenemos {self.df['station_id'].nunique()} estaciones meteorológicas monitoreando la región.",
            "qué variables miden": "Las estaciones miden: temperatura 🌡️, humedad 💧, presión atmosférica 📊, viento 💨, partículas PM (1.0, 2.5, 10) 🌫️, índice de calidad del aire (ICA) 🌬️ y precipitación ☔",
            "que variables miden": "Las estaciones miden: temperatura 🌡️, humedad 💧, presión atmosférica 📊, viento 💨, partículas PM (1.0, 2.5, 10) 🌫️, índice de calidad del aire (ICA) 🌬️ y precipitación ☔",
            
            # Conceptos básicos
            "qué es pm2.5": "PM2.5 son partículas finas de 2.5 micrómetros o menos. Son peligrosas porque pueden penetrar profundamente en los pulmones y el torrente sanguíneo. 🫁",
            "que es pm2.5": "PM2.5 son partículas finas de 2.5 micrómetros o menos. Son peligrosas porque pueden penetrar profundamente en los pulmones y el torrente sanguíneo. 🫁",
            "qué es ica": "El ICA (Índice de Calidad del Aire) mide qué tan limpio o contaminado está el aire. Valores: 0-50 Bueno 🟢, 51-100 Moderado 🟡, 101-150 Dañino para grupos sensibles 🟠, 151+ Dañino 🔴",
            "que es ica": "El ICA (Índice de Calidad del Aire) mide qué tan limpio o contaminado está el aire. Valores: 0-50 Bueno 🟢, 51-100 Moderado 🟡, 101-150 Dañino para grupos sensibles 🟠, 151+ Dañino 🔴",
            "qué es humedad": "La humedad relativa es el porcentaje de vapor de agua en el aire comparado con el máximo que puede contener a esa temperatura. 💧",
            "que es humedad": "La humedad relativa es el porcentaje de vapor de agua en el aire comparado con el máximo que puede contener a esa temperatura. 💧",
            
            # Información del sistema
            "cuántos registros hay": f"Tenemos {len(self.df):,} registros de mediciones en total.",
            "cuantos registros hay": f"Tenemos {len(self.df):,} registros de mediciones en total.",
            "desde cuándo hay datos": f"Los datos van desde {self.df['timestamp'].min().strftime('%d/%m/%Y')} hasta {self.df['timestamp'].max().strftime('%d/%m/%Y')}.",
            "desde cuando hay datos": f"Los datos van desde {self.df['timestamp'].min().strftime('%d/%m/%Y')} hasta {self.df['timestamp'].max().strftime('%d/%m/%Y')}.",
        }
        
        # Buscar coincidencia exacta
        if pregunta_lower in respuestas_heuristicas:
            return respuestas_heuristicas[pregunta_lower]
        
        # Buscar patrones con regex
        patrones = [
            (r".*estación.*(\d+).*", self._responder_estacion_por_numero),
            (r".*temperatura.*promedio.*", self._responder_temperatura_promedio),
            (r".*humedad.*promedio.*", self._responder_humedad_promedio),
            (r".*calidad.*aire.*", self._responder_calidad_aire_general),
            (r".*pm.*alto.*", self._responder_pm_alto),
            (r".*mejor.*aire.*", self._responder_mejor_aire),
            (r".*peor.*aire.*", self._responder_peor_aire),
        ]
        
        for patron, funcion in patrones:
            match = re.search(patron, pregunta_lower)
            if match:
                return funcion(match, pregunta)
        
        return None  # No se encontró respuesta heurística

    def _responder_estacion_por_numero(self, match, pregunta_original: str) -> str:
        """Responde información sobre una estación específica por número"""
        try:
            numero = int(match.group(1))
            estaciones = self.df['station_id'].unique()
            
            if numero <= len(estaciones):
                station_id = sorted(estaciones)[numero - 1]
                station_data = self.df[self.df['station_id'] == station_id]
                station_name = station_data['station_name'].iloc[0]
                
                # Últimas mediciones
                latest = station_data.loc[station_data['timestamp'].idxmax()]
                
                respuesta = f"📍 **Estación {numero}: {station_name}**\n\n"
                respuesta += f"🌡️ Temperatura: {latest.get('temp', '—')}°C\n"
                respuesta += f"💧 Humedad: {latest.get('humedad', '—')}%\n"
                respuesta += f"🌫️ PM2.5: {latest.get('pm_2_5', '—')} µg/m³\n"
                respuesta += f"🌬️ ICA: {latest.get('ica', '—')}\n"
                respuesta += f"📊 Presión: {latest.get('presion', '—')} hPa\n"
                respuesta += f"⏰ Última medición: {latest['timestamp'].strftime('%d/%m/%Y %H:%M')}"
                
                return respuesta
            else:
                return f"Solo tenemos {len(estaciones)} estaciones. Intenta con un número del 1 al {len(estaciones)}."
                
        except Exception as e:
            logger.error(f"Error respondiendo estación por número: {e}")
            return "No pude obtener información de esa estación."

    def _responder_temperatura_promedio(self, match, pregunta_original: str) -> str:
        """Responde sobre temperatura promedio"""
        temp_promedio = self.df['temp'].mean()
        temp_min = self.df['temp'].min()
        temp_max = self.df['temp'].max()
        
        return f"🌡️ **Temperatura promedio**: {temp_promedio:.1f}°C\n📊 Rango: {temp_min:.1f}°C a {temp_max:.1f}°C"

    def _responder_humedad_promedio(self, match, pregunta_original: str) -> str:
        """Responde sobre humedad promedio"""
        humedad_promedio = self.df['humedad'].mean()
        return f"💧 **Humedad promedio**: {humedad_promedio:.1f}%"

    def _responder_calidad_aire_general(self, match, pregunta_original: str) -> str:
        """Responde sobre calidad del aire general"""
        ica_promedio = self.df['ica'].mean()
        
        if ica_promedio <= 50:
            estado = "Buena 🟢"
        elif ica_promedio <= 100:
            estado = "Moderada 🟡"
        elif ica_promedio <= 150:
            estado = "Dañina para grupos sensibles 🟠"
        else:
            estado = "Dañina 🔴"
            
        return f"🌬️ **Calidad del aire promedio**: ICA {ica_promedio:.0f} - {estado}"

    def _responder_pm_alto(self, match, pregunta_original: str) -> str:
        """Responde sobre PM más alto"""
        pm_max = self.df['pm_2_5'].max()
        estacion_pm_max = self.df.loc[self.df['pm_2_5'].idxmax(), 'station_name']
        
        return f"🌫️ **PM2.5 más alto**: {pm_max:.1f} µg/m³ en la estación {estacion_pm_max}"

    def _responder_mejor_aire(self, match, pregunta_original: str) -> str:
        """Responde sobre la estación con mejor aire"""
        mejor_ica = self.df.groupby('station_name')['ica'].mean().idxmin()
        ica_valor = self.df.groupby('station_name')['ica'].mean().min()
        
        return f"🌬️ **Mejor calidad del aire**: {mejor_ica} con ICA promedio de {ica_valor:.0f}"

    def _responder_peor_aire(self, match, pregunta_original: str) -> str:
        """Responde sobre la estación con peor aire"""
        peor_ica = self.df.groupby('station_name')['ica'].mean().idxmax()
        ica_valor = self.df.groupby('station_name')['ica'].mean().max()
        
        return f"🌬️ **Peor calidad del aire**: {peor_ica} con ICA promedio de {ica_valor:.0f}"

    async def responder_con_gemini(self, pregunta: str) -> str:
        """
        🤖 Método público para FORZAR el uso de Gemini IA
        
        Este método bypasea completamente el sistema heurístico y va directo a Gemini.
        Diseñado específicamente para el botón "Explícame" que requiere análisis IA.
        
        Args:
            pregunta: Pregunta contextual robusta generada automáticamente
            
        Returns:
            Respuesta detallada de Gemini IA
        """
        try:
            logger.info("🚀 FORZANDO uso de Gemini IA (sin heurísticas)")
            
            if not self.has_gemini:
                raise Exception("Gemini IA no está disponible")
            
            # Llamar directamente al método privado de Gemini
            return await self._responder_con_gemini(pregunta)
            
        except Exception as e:
            logger.error(f"❌ Error forzando Gemini: {e}")
            raise Exception(f"Error procesando con Gemini IA: {str(e)}")

    async def _responder_con_gemini(self, pregunta: str) -> str:
        """Usa Gemini para responder preguntas abiertas sobre clima con contexto mejorado"""
        try:
            # Para preguntas contextuales robustas, no validar scope (ya vienen pre-validadas)
            es_pregunta_contextual = "📍 **Estación:**" in pregunta or "📊 **Promedios del período:**" in pregunta
            
            if not es_pregunta_contextual and not self._es_pregunta_climatica(pregunta):
                return self._respuesta_fuera_de_scope(pregunta)
            
            from google import genai
            
            # Crear contexto mejorado para Gemini
            contexto = self._crear_contexto_mejorado_para_gemini()
            
            prompt = f"""Eres un experto meteorólogo y especialista en calidad del aire con amplio conocimiento científico.

CONTEXTO DE DATOS DISPONIBLES:
{contexto}

CONOCIMIENTO ESPECIALIZADO QUE DEBES APLICAR:

🌬️ **ESTÁNDARES DE CALIDAD DEL AIRE (µg/m³):**
- PM2.5: Bueno (0-12), Moderado (12.1-35.4), Insalubre para grupos sensibles (35.5-55.4), Insalubre (55.5-150.4)
- PM10: Bueno (0-54), Moderado (55-154), Insalubre para grupos sensibles (155-254), Insalubre (255-354)
- ICA: Bueno (0-50), Moderado (51-100), Insalubre para grupos sensibles (101-150), Insalubre (151-200)

🌡️ **CONDICIONES METEOROLÓGICAS:**
- Humedad: Baja (<30%), Normal (30-60%), Alta (60-80%), Muy alta (>80%)
- Temperatura: Considera efectos en dispersión de contaminantes
- Precipitación: Ayuda a limpiar el aire de partículas

📊 **ANÁLISIS QUE DEBES REALIZAR:**
1. Evalúa cada variable según estándares internacionales
2. Identifica patrones y correlaciones entre variables
3. Considera efectos en salud pública
4. Proporciona recomendaciones específicas y prácticas
5. Explica causas probables de los valores observados

INSTRUCCIONES DE RESPUESTA:
- RESPUESTAS CONCISAS: Máximo 3-4 párrafos cortos
- Usa emojis para organizar pero SIN texto excesivo
- Números exactos y comparaciones directas
- Recomendaciones específicas en 1-2 líneas
- Evita explicaciones largas - ve directo al punto
- Formato: Conclusión + Datos clave + Recomendación breve

PREGUNTA/ANÁLISIS SOLICITADO:
{pregunta}

IMPORTANTE: Responde de forma ULTRA-CONCISA. Máximo 150 palabras. Directo al grano.

RESPUESTA EXPERTA:"""

            client = genai.Client(api_key=self.gemini_api_key)
            response = client.models.generate_content(
                model="gemini-2.5-pro",  # Usar modelo más avanzado
                contents=prompt
            )
            
            respuesta = response.text.strip()
            logger.info(f"✅ Gemini (contexto mejorado) respondió: {respuesta[:100]}...")
            
            return respuesta
            
        except Exception as e:
            logger.error(f"❌ Error usando Gemini con contexto mejorado: {e}")
            return "Lo siento, no pude procesar tu consulta con IA en este momento. Por favor, intenta de nuevo o reformula tu pregunta."

    def _es_pregunta_climatica(self, pregunta: str) -> bool:
        """Valida si la pregunta es sobre clima/meteorología"""
        palabras_climaticas = [
            'clima', 'temperatura', 'temp', 'calor', 'frío', 'grados',
            'humedad', 'húmedo', 'seco', 'vapor',
            'lluvia', 'precipitación', 'lloviendo', 'agua',
            'viento', 'brisa', 'velocidad',
            'presión', 'atmosférica', 'hpa',
            'aire', 'calidad', 'contaminación', 'limpio',
            'pm2.5', 'pm10', 'pm', 'partículas', 'polvo',
            'ica', 'índice', 'aqi', 'smog',
            'estación', 'estaciones', 'sensor', 'monitoreo',
            'datos', 'medición', 'registro'
        ]
        
        pregunta_lower = pregunta.lower()
        return any(palabra in pregunta_lower for palabra in palabras_climaticas)

    def _crear_contexto_para_gemini(self) -> str:
        """Crea contexto con datos reales para Gemini"""
        # Estadísticas generales
        contexto = f"""RESUMEN DEL SISTEMA:
- Total estaciones: {self.df['station_id'].nunique()}
- Total registros: {len(self.df):,}
- Período: {self.df['timestamp'].min().strftime('%d/%m/%Y')} - {self.df['timestamp'].max().strftime('%d/%m/%Y')}

ESTADÍSTICAS ACTUALES:
- Temperatura promedio: {self.df['temp'].mean():.1f}°C (rango: {self.df['temp'].min():.1f}°C - {self.df['temp'].max():.1f}°C)
- Humedad promedio: {self.df['humedad'].mean():.1f}%
- ICA promedio: {self.df['ica'].mean():.0f}
- PM2.5 promedio: {self.df['pm_2_5'].mean():.1f} µg/m³

ESTACIONES CON DATOS RECIENTES:
"""
        
        # Agregar datos de estaciones
        for station_id in self.df['station_id'].unique()[:5]:  # Primeras 5 estaciones
            station_data = self.df[self.df['station_id'] == station_id]
            latest = station_data.loc[station_data['timestamp'].idxmax()]
            
            contexto += f"• {latest['station_name']}: "
            contexto += f"Temp: {latest.get('temp', '—')}°C, "
            contexto += f"Humedad: {latest.get('humedad', '—')}%, "
            contexto += f"PM2.5: {latest.get('pm_2_5', '—')} µg/m³, "
            contexto += f"ICA: {latest.get('ica', '—')}\n"
        
        return contexto

    def _crear_contexto_mejorado_para_gemini(self) -> str:
        """Crea contexto enriquecido y detallado para Gemini con análisis avanzado"""
        try:
            # Estadísticas generales del sistema
            total_estaciones = self.df['station_id'].nunique()
            total_registros = len(self.df)
            fecha_inicio = self.df['timestamp'].min().strftime('%d/%m/%Y')
            fecha_fin = self.df['timestamp'].max().strftime('%d/%m/%Y')
            
            # Estadísticas por variable con percentiles
            stats_temp = self.df['temp'].describe()
            stats_humedad = self.df['humedad'].describe()
            stats_pm25 = self.df['pm_2_5'].describe()
            stats_pm10 = self.df['pm_10'].describe()
            stats_ica = self.df['ica'].describe()
            
            contexto = f"""📊 **SISTEMA DE MONITOREO AMBIENTAL**

🏢 **INFORMACIÓN GENERAL:**
- Total de estaciones activas: {total_estaciones}
- Registros históricos: {total_registros:,}
- Cobertura temporal: {fecha_inicio} hasta {fecha_fin}
- Tipos de equipos: {', '.join(self.df['tipo_equipo'].unique())}

📈 **ESTADÍSTICAS HISTÓRICAS DETALLADAS:**

🌡️ **TEMPERATURA:**
- Promedio: {stats_temp['mean']:.1f}°C
- Rango: {stats_temp['min']:.1f}°C - {stats_temp['max']:.1f}°C
- Percentil 25: {stats_temp['25%']:.1f}°C | Mediana: {stats_temp['50%']:.1f}°C | Percentil 75: {stats_temp['75%']:.1f}°C

💧 **HUMEDAD:**
- Promedio: {stats_humedad['mean']:.1f}%
- Rango: {stats_humedad['min']:.1f}% - {stats_humedad['max']:.1f}%
- Percentil 25: {stats_humedad['25%']:.1f}% | Mediana: {stats_humedad['50%']:.1f}% | Percentil 75: {stats_humedad['75%']:.1f}%

🌫️ **PARTÍCULAS PM2.5:**
- Promedio: {stats_pm25['mean']:.1f} µg/m³
- Rango: {stats_pm25['min']:.1f} - {stats_pm25['max']:.1f} µg/m³
- Percentil 25: {stats_pm25['25%']:.1f} | Mediana: {stats_pm25['50%']:.1f} | Percentil 75: {stats_pm25['75%']:.1f} µg/m³

🌬️ **PARTÍCULAS PM10:**
- Promedio: {stats_pm10['mean']:.1f} µg/m³
- Rango: {stats_pm10['min']:.1f} - {stats_pm10['max']:.1f} µg/m³
- Percentil 25: {stats_pm10['25%']:.1f} | Mediana: {stats_pm10['50%']:.1f} | Percentil 75: {stats_pm10['75%']:.1f} µg/m³

🏭 **ÍNDICE DE CALIDAD DEL AIRE (ICA):**
- Promedio: {stats_ica['mean']:.0f}
- Rango: {stats_ica['min']:.0f} - {stats_ica['max']:.0f}
- Percentil 25: {stats_ica['25%']:.0f} | Mediana: {stats_ica['50%']:.0f} | Percentil 75: {stats_ica['75%']:.0f}

📍 **ESTACIONES REPRESENTATIVAS (Datos más recientes):**"""

            # Agregar datos detallados de estaciones con mejor información
            estaciones_unicas = self.df['station_id'].unique()[:8]  # Más estaciones para contexto
            
            for i, station_id in enumerate(estaciones_unicas, 1):
                station_data = self.df[self.df['station_id'] == station_id]
                latest = station_data.loc[station_data['timestamp'].idxmax()]
                
                # Calcular promedios recientes (últimos 10 registros)
                recent_data = station_data.tail(10)
                
                contexto += f"""
{i}. **{latest['station_name']}** (ID: {station_id})
   - Ubicación: Lat {latest.get('lat', 'N/A')}, Lon {latest.get('lon', 'N/A')}
   - Tipo: {latest.get('tipo_equipo', 'N/A')}
   - Última medición: {latest['timestamp'].strftime('%d/%m/%Y %H:%M')}
   - Temp: {latest.get('temp', 'N/A')}°C | Humedad: {latest.get('humedad', 'N/A')}%
   - PM2.5: {latest.get('pm_2_5', 'N/A')} µg/m³ | PM10: {latest.get('pm_10', 'N/A')} µg/m³
   - ICA: {latest.get('ica', 'N/A')} | Precipitación: {latest.get('precipitacion', 'N/A')} mm
   - Promedio reciente PM2.5: {recent_data['pm_2_5'].mean():.1f} µg/m³"""

            # Agregar análisis de tendencias
            contexto += f"""

🔍 **ANÁLISIS DE TENDENCIAS GENERALES:**
- Estaciones con mejor calidad de aire: {self.df.groupby('station_name')['ica'].mean().nsmallest(3).index.tolist()}
- Estaciones con mayor concentración PM2.5: {self.df.groupby('station_name')['pm_2_5'].mean().nlargest(3).index.tolist()}
- Rango de temperaturas más común: {stats_temp['25%']:.1f}°C - {stats_temp['75%']:.1f}°C
- Humedad típica: {stats_humedad['25%']:.1f}% - {stats_humedad['75%']:.1f}%

💡 **CONTEXTO PARA ANÁLISIS:**
Este sistema monitorea continuamente la calidad del aire y condiciones meteorológicas.
Los datos permiten evaluar patrones, identificar anomalías y generar recomendaciones de salud pública."""

            return contexto
            
        except Exception as e:
            logger.error(f"Error creando contexto mejorado: {e}")
            # Fallback al contexto básico
            return self._crear_contexto_para_gemini()

    def _respuesta_fuera_de_scope(self, pregunta: str) -> str:
        """Respuesta cuando la pregunta no es sobre clima"""
        return f"""🤔 Tu pregunta sobre "{pregunta}" no está relacionada con datos climáticos o meteorológicos.

Soy especialista en:
🌡️ **Clima**: temperatura, humedad, precipitación, viento, presión
🌬️ **Calidad del aire**: PM2.5, ICA, contaminación  
📍 **Estaciones**: ubicaciones, datos actuales, estadísticas

¿Te gustaría preguntar algo sobre estos temas?"""

    def _respuesta_fallback(self, pregunta: str) -> str:
        """Respuesta cuando no hay Gemini disponible"""
        return f"""No pude encontrar una respuesta específica para "{pregunta}".

💡 **Prueba preguntas como:**
• "¿Cuántas estaciones hay?"
• "¿Qué es PM2.5?"
• "¿Cuál es la temperatura promedio?"
• "¿Cómo está la calidad del aire?"
• "Información de la estación 1"

O consulta datos específicos usando nuestros endpoints de API."""
