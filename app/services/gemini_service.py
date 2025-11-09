"""
Servicio de Gemini integrado con las APIs meteorológicas
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import re
from google import genai
from app.services.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)


class GeminiChatService:
    """Servicio de chat con Gemini integrado con datos meteorológicos"""

    def __init__(self, gemini_api_key: str = None, csv_path: str = None):
        self.gemini_api_key = gemini_api_key
        self.has_gemini = bool(gemini_api_key)
        self.chatbot_service = ChatbotService(csv_path) if csv_path else None
        self.last_menu_shown = None  # Track del último menú mostrado

        if not self.has_gemini:
            logger.warning("Gemini API key no configurada")

    def get_health_status(self) -> Dict[str, Any]:
        """Retorna el estado del servicio"""
        return {
            "gemini_configured": self.has_gemini,
            "status": "ready" if self.has_gemini else "no_api_key",
        }

    async def interpretar_pregunta(self, pregunta: str) -> Dict[str, Any]:
        """Interpreta la intención del usuario usando Gemini o heurísticas básicas"""
        if not pregunta:
            return {"accion": "saludo"}

        q = pregunta.lower().strip()
        logger.info(f"Interpretando pregunta: '{pregunta}' (contexto actual: {self.last_menu_shown})")

        # Detectar saludos
        if any(saludo in q for saludo in ["hola", "hi", "hello", "buenas", "buenos"]):
            return {"accion": "saludo"}

        # Detectar opciones de menú principal (solo cuando NO hay contexto activo)
        if self.last_menu_shown is None:
            if q == "a":
                return {"accion": "listar"}
            elif q == "b":
                return {"accion": "concepto", "variable": None}

        # Detectar conceptos por pregunta directa (más específico)
        if q.startswith("qué es ") or q.startswith("que es "):
            variable = q.replace("qué es ", "").replace("que es ", "").strip()
            return {"accion": "concepto", "variable": variable}
            
        # Detectar preguntas que requieren análisis de datos (van directo a IA)
        preguntas_complejas = [
            "cuál", "cual", "mejor", "peor", "mayor", "menor", "más alto", "mas alto", 
            "más bajo", "mas bajo", "comparar", "compara", "diferencia", "ranking",
            "máximo", "maximo", "mínimo", "minimo", "promedio", "estadística"
        ]
        
        if any(palabra in q for palabra in preguntas_complejas):
            logger.info(f"Pregunta compleja detectada: '{pregunta}' - enviando a IA")
            return {"accion": "pregunta_abierta", "pregunta_original": pregunta}
        
        # Detectar preguntas generales simples
        if "cuántas estaciones" in q or "cuantas estaciones" in q:
            return {"accion": "general"}

        # Si no hay Gemini, usar heurísticas básicas
        if not self.has_gemini:
            return {"accion": "estado_actual", "estacion": pregunta}

        # PRIMERO detectar selección por letra (para conceptos) - MÁS ESPECÍFICO
        letra_match = re.match(r'^([a-fA-F])$', q)
        if letra_match:
            letra = letra_match.group(1).upper()
            logger.info(f"Letra detectada: {letra} - interpretando como concepto")
            return {"accion": "concepto_por_letra", "letra_concepto": letra}
        
        # DESPUÉS detectar selección por número (solo para estaciones)
        numero_match = re.match(r'^(\d+)$', q)
        if numero_match:
            numero = int(numero_match.group(1))
            logger.info(f"Número detectado: {numero} - interpretando como estación")
            return {"accion": "estado_actual_por_numero", "numero_estacion": numero}

        # Usar Gemini para interpretación avanzada
        prompt = f"""Eres Nubi ☁️, un asistente ambiental conectado a estaciones meteorológicas.
Debes clasificar la intención de la pregunta del usuario.

Responde SIEMPRE en formato JSON con:
{{
  "accion": "saludo" | "listar" | "estado_actual" | "serie" | "concepto" | "general",
  "estacion": "nombre o null",
  "variable": "nombre o null",
  "dias": number
}}

Ejemplos:
- "hola" → {{"accion":"saludo"}}
- "ver estaciones" → {{"accion":"listar"}}
- "Halley UIS" → {{"accion":"estado_actual","estacion":"Halley UIS"}}
- "PM2.5 de Halley" → {{"accion":"serie","estacion":"Halley","variable":"PM2.5","dias":7}}
- "qué es PM2.5" → {{"accion":"concepto","variable":"PM2.5"}}
- "cuántas estaciones hay" → {{"accion":"general"}}

Pregunta: "{pregunta}"
"""

        try:
            if self.has_gemini:
               
                client = genai.Client(api_key=self.gemini_api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                response_text = response.text.strip()
                
                # Intentar parsear JSON
                import json
                try:
                    result = json.loads(response_text)
                    logger.info(f"Gemini interpretó: {result}")
                    return result
                except json.JSONDecodeError:
                    logger.warning(f"Gemini no devolvió JSON válido: {response_text}")
                    # Fallback a heurísticas
                    return {"accion": "pregunta_abierta", "pregunta_original": pregunta}
            else:
                # Sin Gemini, usar heurísticas básicas
                return {"accion": "pregunta_abierta", "pregunta_original": pregunta}
                
        except Exception as e:
            logger.error(f"Error interpretando con Gemini: {e}")
            # Fallback a pregunta abierta para procesamiento manual
            return {"accion": "pregunta_abierta", "pregunta_original": pregunta}

    def explicar_concepto(self, variable: Optional[str]) -> str:
        """Explica conceptos meteorológicos"""
        if not variable:
            return """📘 ¡Modo educativo activado! Pregúntame cosas como:
- ¿Qué es PM2.5?
- ¿Qué significa humedad?
- ¿Qué es la presión atmosférica?
- ¿Qué es el ICA?
- ¿Qué es la precipitación?"""

        v = variable.lower()
        explicaciones = {
            "pm2.5": "💨 *PM2.5* son partículas muy finas (menores de 2.5 micras). Pueden penetrar en los pulmones y afectar la salud. Menos de 12 µg/m³ se considera bueno, más de 55 es peligroso.",
            "pm1": "💨 *PM1* son partículas ultrafinas (menores de 1 micra). Son las más peligrosas porque pueden llegar al torrente sanguíneo.",
            "pm10": "💨 *PM10* son partículas inhalables (menores de 10 micras). Pueden irritar ojos, nariz y garganta.",
            "humedad": "💧 *Humedad relativa* mide cuánto vapor de agua hay en el aire (0-100%). Alta humedad hace que el ambiente se sienta más pesado.",
            "temperatura": "🌡️ *Temperatura* indica el calor del aire en °C. Los cambios rápidos pueden afectar la sensación térmica.",
            "presión": "📈 *Presión atmosférica* mide el peso del aire sobre nosotros, expresada en hPa. Cambios bruscos suelen anticipar lluvia o viento.",
            "ica": "🌬️ *ICA (Índice de Calidad del Aire)* es un número de 0-500 que indica qué tan contaminado está el aire. 0-50 es bueno, más de 300 es peligroso.",
            "precipitación": "🌧️ *Precipitación* es la cantidad de lluvia caída, medida en milímetros (mm). 1mm significa 1 litro por metro cuadrado.",
            "viento": "💨 *Viento* incluye velocidad (km/h) y dirección (grados). Ayuda a dispersar contaminantes y afecta la sensación térmica.",
        }

        return explicaciones.get(
            v,
            f'No tengo información específica sobre "{variable}". Puedo explicarte sobre PM2.5, humedad, temperatura, presión, ICA, precipitación o viento.',
        )

    def interpretar_calidad_aire(
        self, ica: Optional[float], pm25: Optional[float]
    ) -> str:
        """Interpreta la calidad del aire"""
        if ica is not None:
            if ica <= 50:
                return "🌿 Aire excelente y saludable."
            elif ica <= 100:
                return "😊 Aire bueno, sin riesgos importantes."
            elif ica <= 150:
                return "⚠️ Calidad moderada, grupos sensibles deben tener precaución."
            elif ica <= 200:
                return "🚨 Aire no saludable, evita actividades al aire libre."
            elif ica <= 300:
                return "☠️ Aire muy no saludable, permanece bajo techo."
            else:
                return "🆘 Aire peligroso, emergencia de salud."

        if pm25 is not None:
            if pm25 <= 12:
                return "🌿 Aire limpio y saludable."
            elif pm25 <= 35:
                return "😊 Aire moderado, sin riesgos importantes."
            elif pm25 <= 55:
                return "⚠️ Calidad regular, evita esfuerzos intensos al aire libre."
            elif pm25 <= 150:
                return "🚨 Aire contaminado, precaución al exponerse."
            else:
                return "☠️ Nivel muy peligroso. Permanece bajo techo."

        return "— Sin datos de calidad del aire disponibles."

    async def procesar_pregunta(self, pregunta: str) -> str:
        """Procesador principal de preguntas"""
        try:
            intent = await self.interpretar_pregunta(pregunta)
            accion = intent.get("accion", "general")
            estacion = intent.get("estacion")
            variable = intent.get("variable")
            dias = intent.get("dias", 7)
            
            logger.info(f"Procesando pregunta: '{pregunta}' -> accion: {accion}, intent: {intent}")
            logger.debug(f"Detalles de la pregunta: estacion={estacion}, variable={variable}, dias={dias}")

            saludos_aleatorios = [
                "☀️ ¡Hola! Soy Nubi, tu nube amiga.",
                "🌤️ ¡Bienvenido! Te ayudo a entender el clima y el aire.",
                "💨 Soy Nubi, lista para mostrarte los datos ambientales.",
            ]

            # 🌞 SALUDO INICIAL
            if accion == "saludo":
                import random
                
                # Limpiar contexto al volver al menú principal
                self.last_menu_shown = None

                saludo = random.choice(saludos_aleatorios)
                return f"""{saludo}
Soy tu asistente ambiental conectado a la red de estaciones meteorológicas.
Puedo decirte cómo está el aire, la temperatura o explicarte conceptos.

Opciones disponibles:
🅰️ Ver estaciones disponibles
🅱️ Aprender sobre variables (PM2.5, humedad, ICA, etc.)
¿Qué deseas hacer?"""

            # 🅰️ LISTAR ESTACIONES DISPONIBLES
            if accion == "listar" or (pregunta or "").lower() == "a":
                try:
                    # Limpiar contexto anterior y establecer nuevo
                    self.last_menu_shown = "estaciones"
                    
                    complete_data = self.chatbot_service.get_complete_data_for_chatbot()
                    estaciones = complete_data.stations

                    if not estaciones:
                        return "No hay estaciones disponibles en este momento."

                    lista = "\n".join(
                        [
                            f"{i+1}. {est.station_name}"
                            for i, est in enumerate(estaciones)
                        ]
                    )
                    
                    return f"""📍 *Estaciones disponibles:*
{lista}

💡 *Escribe el número de la estación* que quieres consultar (ejemplo: 1, 2, 3...)"""

                except Exception as e:
                    logger.error(f"Error listando estaciones: {e}")
                    return "No pude obtener la lista de estaciones ahora."


            # 🧠 EXPLICACIÓN DE CONCEPTO
            if accion == "concepto":
                if variable:
                    return self.explicar_concepto(variable)
                else:
                    # Es el modo educativo (escribieron "b")
                    logger.info("Activando modo educativo - estableciendo contexto 'conceptos'")
                    self.last_menu_shown = "conceptos"
                    
                    return """📘 *Modo educativo activado!*

Selecciona qué quieres aprender:
A. ¿Qué es PM2.5?
B. ¿Qué significa humedad?
C. ¿Qué es la presión atmosférica?
D. ¿Qué es el ICA?
E. ¿Qué es la precipitación?
F. ¿Qué es el viento?

💡 *Escribe la letra* de la pregunta que te interesa (ejemplo: A, B, C...)
🤔 O haz una *pregunta abierta* sobre el clima y el aire."""

            # 🌍 INFORMACIÓN GENERAL
            if accion == "general":
                try:
                    complete_data = self.chatbot_service.get_complete_data_for_chatbot()
                    total = len(complete_data.stations)
                    total_records = complete_data.system_info.get("total_records", 0)

                    return f"""📊 Información del sistema:
                    • *{total} estaciones activas*
                    • *{total_records:,} registros de datos*
                    • Variables: temperatura, humedad, presión, PM, ICA, precipitación
                    • Cobertura: {complete_data.temporal_coverage.get('total_days', 0)} días

                    Puedes escribir "ver estaciones" para ver la lista completa."""

                except Exception as e:
                    logger.error(f"Error obteniendo información general: {e}")
                    return "No pude obtener la información general ahora."

            # 🌡️ ESTADO ACTUAL DE UNA ESTACIÓN
            if accion == "estado_actual" and estacion:
                try:
                    complete_data = self.chatbot_service.get_complete_data_for_chatbot()

                    # Buscar estación por nombre (búsqueda flexible)
                    estacion_encontrada = None
                    for est in complete_data.stations:
                        if estacion.lower() in est.station_name.lower():
                            estacion_encontrada = est
                            break

                    if not estacion_encontrada:
                        return f'No encontré la estación "{estacion}". Escribe "ver estaciones" para ver las disponibles.'

                    # Obtener últimas mediciones
                    latest = estacion_encontrada.latest_measurements
                    if not latest or not latest.get("measurements"):
                        return f'No hay datos recientes para "{estacion_encontrada.station_name}".'

                    measurements = latest["measurements"]
                    timestamp = datetime.fromisoformat(
                        latest["timestamp"].replace("Z", "+00:00")
                    )
                    ts_str = timestamp.strftime("%d/%m/%Y %H:%M")

                    # Interpretar calidad del aire
                    ica = measurements.get("ica")
                    pm25 = measurements.get("pm_2_5")
                    interpretacion = self.interpretar_calidad_aire(ica, pm25)

                    return f"""📍 *{estacion_encontrada.station_name}*
                    🌡️ {measurements.get('temp', '—')} °C
                    💧 {measurements.get('humedad', '—')} %
                    📈 {measurements.get('presion', '—')} hPa
                    🌫️ PM2.5: {pm25 or '—'} µg/m³
                    🌬️ ICA: {ica or '—'}
                    🌧️ Precipitación: {measurements.get('precipitacion', '—')} mm
                    🕒 {ts_str}

                        {interpretacion}"""

                except Exception as e:
                    logger.error(f"Error obteniendo estado de estación: {e}")
                    return f'No pude obtener los datos de "{estacion}" ahora.'

            # 🔢 ESTADO ACTUAL POR NÚMERO DE ESTACIÓN
            if accion == "estado_actual_por_numero":
                try:
                    numero = intent.get("numero_estacion", 0)
                    complete_data = self.chatbot_service.get_complete_data_for_chatbot()
                    
                    if numero < 1 or numero > len(complete_data.stations):
                        return f'Número fuera de rango. Escribe un número del 1 al {len(complete_data.stations)}.\n\nEscribe "a" para ver la lista de estaciones nuevamente.'
                    
                    # Limpiar contexto después de usar
                    self.last_menu_shown = None
                    
                    # Obtener estación por índice (número - 1)
                    estacion_encontrada = complete_data.stations[numero - 1]
                    
                    # Obtener últimas mediciones
                    latest = estacion_encontrada.latest_measurements
                    if not latest or not latest.get("measurements"):
                        return f'No hay datos recientes para "{estacion_encontrada.station_name}".'
                    
                    measurements = latest["measurements"]
                    timestamp = datetime.fromisoformat(latest["timestamp"].replace("Z", "+00:00"))
                    ts_str = timestamp.strftime("%d/%m/%Y %H:%M")
                    
                    # Interpretar calidad del aire
                    ica = measurements.get("ica")
                    pm25 = measurements.get("pm_2_5")
                    interpretacion = self.interpretar_calidad_aire(ica, pm25)
                    
                    return f"""📍 *{estacion_encontrada.station_name}*
🌡️ {measurements.get('temp', '—')} °C
💧 {measurements.get('humedad', '—')} %
📈 {measurements.get('presion', '—')} hPa
🌫️ PM2.5: {pm25 or '—'} µg/m³
🌬️ ICA: {ica or '—'}
🌧️ Precipitación: {measurements.get('precipitacion', '—')} mm
🕒 {ts_str}

{interpretacion}

💡 Escribe "a" para ver otras estaciones o "hola" para el menú principal."""
                    
                except Exception as e:
                    logger.error(f"Error obteniendo estado por número: {e}")
                    return f'No pude obtener los datos de la estación número {intent.get("numero_estacion", "?")}.'

            # 📚 CONCEPTO POR LETRA
            if accion == "concepto_por_letra":
                conceptos = {
                    "A": "pm2.5",
                    "B": "humedad", 
                    "C": "presión",
                    "D": "ica",
                    "E": "precipitación",
                    "F": "viento"
                }
                
                letra = intent.get("letra_concepto", "")
                if letra in conceptos:
                    # Limpiar contexto después de usar
                    self.last_menu_shown = None
                    
                    explicacion = self.explicar_concepto(conceptos[letra])
                    return f"""{explicacion}

💡 Escribe "b" para ver otros conceptos o "hola" para el menú principal."""
                else:
                    return f'Letra fuera de rango. Escribe una letra de A a F.\n\nEscribe "b" para ver la lista de conceptos nuevamente.'

            # 📈 SERIE HISTÓRICA (simplificada por ahora)
            if accion == "serie":
                return f"""📈 Las series históricas están disponibles a través de la API.
                    Para datos detallados de {variable or 'variables'} en {estacion or 'estaciones'}, 
                    puedes usar los endpoints de la API o pregúntame por el estado actual."""

            # 🤖 PREGUNTA ABIERTA CON IA - Gemini interpreta y responde
            if accion == "pregunta_abierta":
                try:
                    pregunta_original = intent.get("pregunta_original", pregunta)
                    # Primero validar si la pregunta es relevante
                    es_relevante = await self.validar_pregunta_relevante(pregunta_original)
                    if es_relevante:
                        # Usar IA para generar respuesta inteligente
                        return await self.responder_con_ia(pregunta_original)
                    else:
                        return await self.respuesta_fuera_de_scope(pregunta_original)
                except Exception as e:
                    logger.error(f"Error respondiendo pregunta abierta: {e}")
                    return f'Interesante pregunta sobre "{pregunta}". Puedo ayudarte mejor si me preguntas sobre estaciones específicas o conceptos como PM2.5, humedad, etc. Escribe "hola" para ver las opciones.'

            # 🤔 FALLBACK PARA PREGUNTAS LARGAS (cuando no hay IA)
            if len(pregunta.split()) > 1:  # Si es más de una palabra, probablemente es pregunta abierta
                try:
                    # Primero validar si la pregunta es relevante
                    es_relevante = await self.validar_pregunta_relevante(pregunta)
                    if es_relevante:
                        return await self.responder_pregunta_abierta(pregunta)
                    else:
                        return await self.respuesta_fuera_de_scope(pregunta)
                except Exception as e:
                    logger.error(f"Error respondiendo pregunta abierta: {e}")
                    return f'Interesante pregunta sobre "{pregunta}". Puedo ayudarte mejor si me preguntas sobre estaciones específicas o conceptos como PM2.5, humedad, etc. Escribe "hola" para ver las opciones.'

            # 🌀 Default: si no entendió nada
            return 'No entendí muy bien. Puedes decir "hola" para ver las opciones o escribir el nombre de una estación.'

        except Exception as e:
            logger.error(f"Error procesando pregunta: {e}")
            return 'Ocurrió un error procesando tu pregunta. Intenta de nuevo o escribe "hola" para ver las opciones.'

    async def responder_pregunta_abierta(self, pregunta: str) -> str:
        """Responde preguntas abiertas basándose en los datos del backend"""
        try:
            # Obtener datos completos del sistema
            complete_data = self.chatbot_service.get_complete_data_for_chatbot()
            
            # Palabras clave para diferentes tipos de preguntas
            pregunta_lower = pregunta.lower()
            
            # Preguntas sobre cantidad/estadísticas
            if any(word in pregunta_lower for word in ['cuántas', 'cuantas', 'cantidad', 'total', 'número']):
                if 'estacion' in pregunta_lower:
                    total_estaciones = len(complete_data.stations)
                    return f"""📊 Actualmente tengo *{total_estaciones} estaciones* monitoreando el aire y el clima.
                    
Estas estaciones están distribuidas por la región y miden variables como temperatura, humedad, PM2.5, ICA y precipitación.

¿Te gustaría ver la lista completa? Escribe "a" 📍"""
                
                elif any(word in pregunta_lower for word in ['datos', 'registros', 'mediciones']):
                    total_records = complete_data.system_info.get('total_records', 0)
                    return f"""📈 El sistema tiene *{total_records:,} registros* de mediciones ambientales.
                    
Estos datos incluyen temperatura, humedad, presión, calidad del aire (PM2.5, ICA) y precipitación de todas las estaciones.

¿Quieres consultar alguna estación específica? Escribe "a" para ver la lista 📍"""
            
            # Preguntas sobre calidad del aire
            elif any(word in pregunta_lower for word in ['aire', 'contaminación', 'pm2.5', 'ica', 'calidad']):
                # Obtener estadísticas de calidad del aire
                estaciones_con_datos = [est for est in complete_data.stations if est.latest_measurements]
                
                if estaciones_con_datos:
                    # Calcular promedio de ICA si está disponible
                    icas = []
                    pm25s = []
                    
                    for est in estaciones_con_datos:
                        measurements = est.latest_measurements.get('measurements', {})
                        if measurements.get('ica'):
                            icas.append(measurements['ica'])
                        if measurements.get('pm_2_5'):
                            pm25s.append(measurements['pm_2_5'])
                    
                    if icas:
                        ica_promedio = sum(icas) / len(icas)
                        interpretacion = self.interpretar_calidad_aire(ica_promedio, None)
                        
                        return f"""🌬️ *Estado actual de la calidad del aire:*
                        
• ICA promedio: *{ica_promedio:.1f}*
• {interpretacion}
• Estaciones monitoreando: *{len(estaciones_con_datos)}*

Para ver datos específicos de una estación, escribe "a" 📍
Para aprender sobre calidad del aire, escribe "b" 📘"""
                
                return """🌬️ La calidad del aire se mide principalmente con:
                
• *PM2.5*: Partículas finas que afectan la salud
• *ICA*: Índice que resume la calidad (0-500)
• *PM10*: Partículas más grandes pero también importantes

¿Quieres ver datos actuales? Escribe "a" para estaciones 📍
¿Quieres aprender más? Escribe "b" para conceptos 📘"""
            
            # Preguntas sobre clima/temperatura
            elif any(word in pregunta_lower for word in ['clima', 'temperatura', 'lluvia', 'humedad', 'viento']):
                return """🌡️ Monitoreo las siguientes variables climáticas:
                
• *Temperatura*: En grados Celsius
• *Humedad*: Porcentaje de vapor de agua
• *Precipitación*: Lluvia en milímetros
• *Presión*: Atmosférica en hPa
• *Viento*: Velocidad y dirección

¿Quieres ver datos actuales? Escribe "a" para estaciones 📍
¿Quieres aprender sobre estas variables? Escribe "b" 📘"""
            
            # Preguntas sobre ubicaciones
            elif any(word in pregunta_lower for word in ['dónde', 'donde', 'ubicación', 'lugar', 'zona']):
                cobertura = complete_data.geographic_coverage
                return f"""📍 *Cobertura geográfica del sistema:*
                
• Latitud: {cobertura.get('lat_range', {}).get('min', 'N/A')} a {cobertura.get('lat_range', {}).get('max', 'N/A')}
• Longitud: {cobertura.get('lon_range', {}).get('min', 'N/A')} a {cobertura.get('lon_range', {}).get('max', 'N/A')}
• Estaciones distribuidas por la región

¿Quieres ver la lista completa de estaciones? Escribe "a" 📍"""
            
            # Pregunta genérica sobre el sistema
            else:
                return f"""🤔 Interesante pregunta sobre "{pregunta}".
                
Soy Nubi ☁️ y puedo ayudarte con:
• 📍 Datos de *{len(complete_data.stations)} estaciones* (escribe "a")
• 📘 Conceptos sobre *aire y clima* (escribe "b")
• 🌡️ Mediciones de *temperatura, humedad, PM2.5, ICA*
• 📊 Estadísticas del sistema

¿Qué te gustaría explorar?"""
                
        except Exception as e:
            logger.error(f"Error en respuesta abierta: {e}")
            return 'No pude procesar tu pregunta completamente. Intenta ser más específico o escribe "hola" para ver las opciones.'

    async def validar_pregunta_relevante(self, pregunta: str) -> bool:
        """Valida si una pregunta está relacionada con los datos disponibles"""
        pregunta_lower = pregunta.lower()
        
        # Palabras clave relacionadas con nuestros datos
        palabras_relevantes = [
            # Clima y meteorología
            'clima', 'temperatura', 'temp', 'calor', 'frío', 'grados',
            'humedad', 'húmedo', 'seco', 'vapor',
            'lluvia', 'precipitación', 'lloviendo', 'agua',
            'viento', 'brisa', 'velocidad del viento',
            'presión', 'atmosférica', 'hpa', 'mbar',
            
            # Calidad del aire
            'aire', 'calidad', 'contaminación', 'contaminado', 'limpio',
            'pm2.5', 'pm10', 'pm', 'partículas', 'polvo',
            'ica', 'índice', 'aqi', 'smog',
            
            # Estaciones y ubicaciones
            'estación', 'estaciones', 'sensor', 'sensores', 'monitoreo',
            'ubicación', 'lugar', 'zona', 'región', 'dónde', 'donde',
            
            # Datos y estadísticas
            'datos', 'información', 'medición', 'mediciones', 'registro',
            'cuánto', 'cuanto', 'cuánta', 'cuanta', 'cuántas', 'cuantas',
            'promedio', 'máximo', 'mínimo', 'estadística',
            
            # Tiempo
            'hoy', 'ahora', 'actual', 'reciente', 'último', 'última',
            'ayer', 'mañana', 'semana', 'mes', 'día', 'hora'
        ]
        
        # Verificar si contiene palabras relevantes
        tiene_palabras_relevantes = any(palabra in pregunta_lower for palabra in palabras_relevantes)
        
        # Palabras que indican preguntas NO relevantes
        palabras_irrelevantes = [
            'fútbol', 'deportes', 'música', 'película', 'comida', 'receta',
            'política', 'economía', 'historia', 'matemáticas', 'programación',
            'amor', 'relación', 'trabajo', 'estudios', 'universidad',
            'coche', 'carro', 'transporte', 'viaje', 'turismo'
        ]
        
        tiene_palabras_irrelevantes = any(palabra in pregunta_lower for palabra in palabras_irrelevantes)
        
        # Es relevante si tiene palabras clave Y NO tiene palabras irrelevantes
        return tiene_palabras_relevantes and not tiene_palabras_irrelevantes

    async def respuesta_fuera_de_scope(self, pregunta: str) -> str:
        """Respuesta cuando la pregunta está fuera del alcance del sistema"""
        return f"""🤔 Tu pregunta sobre "{pregunta}" está fuera de mi área de especialidad.

Soy Nubi ☁️, especializada en datos ambientales y meteorológicos. Puedo ayudarte con:

🌡️ **Clima:** temperatura, humedad, precipitación, viento, presión
🌬️ **Calidad del aire:** PM2.5, ICA, contaminación
📍 **Estaciones:** ubicaciones, datos actuales, estadísticas
📊 **Información:** cuántas estaciones, rangos de datos, cobertura

¿Te gustaría explorar alguno de estos temas?
• Escribe "a" para ver estaciones 📍
• Escribe "b" para aprender conceptos 📘
• Haz una pregunta sobre clima o calidad del aire 🌤️"""

    async def responder_con_ia(self, pregunta: str) -> str:
        """Responde preguntas complejas usando IA con contexto directo (sin Function Calling)"""
        try:
            if not self.has_gemini:
                return await self.responder_pregunta_abierta(pregunta)
            
            from google import genai
            
            # Obtener datos directamente para contexto
            complete_data = self.chatbot_service.get_complete_data_for_chatbot()
            
            # Crear contexto con datos reales
            contexto_estaciones = ""
            for i, station in enumerate(complete_data.stations, 1):
                latest = station.latest_measurements
                if latest and latest.get("measurements"):
                    measurements = latest["measurements"]
                    contexto_estaciones += f"{i}. {station.station_name}:\n"
                    contexto_estaciones += f"   - Temperatura: {measurements.get('temp', '—')}°C\n"
                    contexto_estaciones += f"   - Humedad: {measurements.get('humedad', '—')}%\n"
                    contexto_estaciones += f"   - PM2.5: {measurements.get('pm_2_5', '—')} µg/m³\n"
                    contexto_estaciones += f"   - ICA: {measurements.get('ica', '—')}\n\n"
            
            # Prompt con contexto completo
            prompt_ia = f"""Eres Nubi ☁️, un asistente especializado en datos ambientales y meteorológicos.

DATOS ACTUALES DEL SISTEMA:
- Total de estaciones: {len(complete_data.stations)}
- Total de registros: {complete_data.system_info.get('total_records', 0):,}
- Variables disponibles: {', '.join([var.name for var in complete_data.variables])}

ESTACIONES CON DATOS RECIENTES:
{contexto_estaciones}

INSTRUCCIONES:
- Responde la pregunta usando SOLO los datos proporcionados arriba
- Para comparaciones, analiza todos los valores disponibles
- Mantén un tono amigable y usa emojis apropiados
- Sé específico con números y nombres de estaciones
- Si no hay datos suficientes, dilo claramente

PREGUNTA DEL USUARIO: "{pregunta}"

RESPUESTA:"""

            client = genai.Client(api_key=self.gemini_api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_ia
            )
            respuesta_ia = response.text.strip()
            
            logger.info(f"IA respondió a '{pregunta}': {respuesta_ia[:100]}...")
            
            return respuesta_ia
            
        except Exception as e:
            logger.error(f"Error en IA: {e}")
            return await self.responder_pregunta_abierta(pregunta)

