# Weather Stations API - Hackathon

API backend para visualización de datos de estaciones meteorológicas en un mapa animado.

## Estructura del Proyecto

```
Hackaton/
├── app/
│   ├── models/          # Modelos de datos (Pydantic)
│   ├── services/        # Lógica de negocio
│   ├── controllers/     # Controladores/Routers de FastAPI
│   ├── routes/          # Definición centralizada de rutas
│   │   ├── api_routes.py    # Rutas de la API
│   │   └── routes.py        # Router principal
│   └── config/          # Configuración
├── main.py              # Archivo principal de FastAPI
├── requirements.txt     # Dependencias
└── datos_limpios_20251108_152228.csv  # Base de datos (CSV)
```

### Organización de Rutas

- **`routes/api_routes.py`**: Centraliza todas las rutas de la API bajo el prefijo `/api`
- **`routes/routes.py`**: Router principal que organiza todos los módulos de rutas
- **`controllers/`**: Contienen la lógica específica de cada endpoint
- **Escalabilidad**: Fácil agregar nuevos módulos (weather, analytics, etc.)

## Instalación

1. **Crear entorno virtual:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

La API estará disponible en: `http://localhost:8000`

## Documentación API

Una vez ejecutando, visita:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Endpoints Principales

### Estaciones
- `GET /api/stations/` - Lista todas las estaciones
- `GET /api/stations/{station_id}` - Datos de una estación específica
- `GET /api/stations/summary/data` - Resumen de datos disponibles

### Mapa
- `GET /api/stations/map/snapshot` - Snapshot del mapa para un timestamp
- `POST /api/stations/map/animation` - Datos para animación del mapa

### Series Temporales
- `POST /api/stations/timeseries` - Obtener series temporales

## Ejemplos de Uso

### Obtener todas las estaciones:
```bash
curl http://localhost:8000/api/stations/
```

### Snapshot del mapa:
```bash
curl "http://localhost:8000/api/stations/map/snapshot?timestamp=2025-09-01T12:00:00Z"
```

### Datos de animación:
```bash
curl -X POST "http://localhost:8000/api/stations/map/animation" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-09-01T00:00:00Z",
    "end_date": "2025-09-01T23:59:59Z",
    "time_interval": "1H",
    "variable": "temp"
  }'
```

## Variables Disponibles

- `temp` - Temperatura (°C)
- `humedad` - Humedad relativa (%)
- `presion` - Presión atmosférica
- `pm_2_5` - Partículas PM2.5
- `pm_10` - Partículas PM10
- `ica` - Índice de Calidad del Aire (AQI)
- `precipitacion` - Precipitación (mm)
- `viento_vel` - Velocidad del viento
- `viento_dir` - Dirección del viento

## Endpoints para Chatbot/LLM

### 🤖 Sistema Unificado de Chatbot - Nubi ☁️

El sistema incluye endpoints tanto para **chat conversacional** como para **datos estructurados**:

#### **🗣️ Chat Conversacional**

##### **POST /api/chatbot/message**
Endpoint principal para chat conversacional con Nubi ☁️:
```json
{
  "message": "Hola, ¿cómo está el aire en Halley UIS?",
  "user_id": "opcional"
}
```

**Respuesta:**
```json
{
  "response": "📍 *Halley UIS*\n🌡️ 24.5 °C\n💧 65 %\n🌫️ PM2.5: 15 µg/m³\n🌬️ ICA: 45\n🌿 Aire excelente y saludable.",
  "timestamp": "2025-01-08T15:30:00",
  "status": "success"
}
```

**Comandos soportados:**
- `hola` - Saludo inicial con opciones
- `a` - Ver estaciones disponibles  
- `b` - Modo educativo (explicar conceptos)
- `[nombre_estación]` - Estado actual de una estación
- `¿qué es PM2.5?` - Explicación de conceptos

#### **📊 Datos Estructurados**

##### **GET /api/chatbot/data**
Endpoint que retorna **TODA** la información del sistema estructurada:
- Resumen completo de todas las estaciones
- Información detallada de todas las variables
- Estadísticas globales y por estación
- Cobertura temporal y geográfica
- Información de calidad de datos

```bash
curl http://localhost:8000/api/chatbot/data
```

##### **POST /api/chatbot/query**
Consultas filtradas para análisis específicos:
```json
{
  "stations": [1, 2, 3],
  "variables": ["temp", "humedad", "ica"],
  "date_range": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-31T23:59:59Z"
  },
  "include_raw_data": true,
  "max_records": 1000
}
```

#### **🔧 Utilidades**

##### **GET /api/chatbot/info**
Información completa sobre capacidades del chatbot

##### **GET /api/chatbot/health**
Health check del servicio completo

##### **GET /api/chatbot/chat/health**
Health check específico del chat conversacional

### 💡 Casos de Uso para Chatbot

**Perfecto para sistemas RAG (Retrieval-Augmented Generation):**
- ✅ **Preguntas sobre estaciones**: "¿Cuántas estaciones hay?"
- ✅ **Consultas de datos**: "¿Cuál es la temperatura promedio?"
- ✅ **Análisis de calidad del aire**: "¿Cómo está el ICA hoy?"
- ✅ **Información geográfica**: "¿Dónde están ubicadas las estaciones?"
- ✅ **Estadísticas temporales**: "¿Cuándo fue la última medición?"

## 🤖 Chat con Nubi - Asistente Ambiental

### **Integración Completa de Gemini**

El sistema incluye **Nubi ☁️**, un chatbot inteligente powered by Gemini que puede:

#### **POST /api/chat/message**
Endpoint principal para chatear con Nubi:
```json
{
  "message": "¿Cómo está la calidad del aire?",
  "user_id": "opcional"
}
```

**Respuesta:**
```json
{
  "response": "🌬️ La calidad del aire varía por estación...",
  "timestamp": "2025-11-08T15:30:00Z",
  "status": "success"
}
```

#### **Comandos Especiales de Nubi:**
- **`hola`** - Saludo inicial con opciones
- **`a`** - Ver todas las estaciones disponibles  
- **`b`** - Modo educativo (explicar conceptos)
- **`Nombre de estación`** - Estado actual de esa estación
- **`¿Qué es PM2.5?`** - Explicaciones de variables

#### **Capacidades de Nubi:**
- 🌡️ **Estado actual** de cualquier estación
- 📊 **Estadísticas generales** del sistema
- 🧠 **Explicaciones educativas** de conceptos meteorológicos
- 🌬️ **Interpretación de calidad del aire** (ICA, PM2.5)
- 📍 **Información geográfica** de estaciones

### **Migración desde Node.js**

**Antes (Node.js):**
```javascript
// Backend separado en Node.js
const response = await fetch('http://localhost:3001/chat', {
  method: 'POST',
  body: JSON.stringify({ message })
});
```

**Ahora (Python integrado):**
```javascript
// Directamente al backend de Python
const response = await fetch('http://localhost:8000/api/chat/message', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message })
});
```

### **Configuración de Gemini:**

1. **Obtener API Key**: https://makersuite.google.com/app/apikey
2. **Configurar en .env**:
```env
GEMINI_API_KEY=tu_api_key_aqui
```
3. **Instalar dependencia**:
```bash
pip install google-generativeai
```

## Deployment

### 🚀 Opciones de Deployment

#### **1. Railway (Recomendado para APIs)**
```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login y deploy
railway login
railway init
railway up
```

#### **2. Render**
```bash
# 1. Conectar repositorio en render.com
# 2. Configurar:
# - Build Command: pip install -r requirements.txt
# - Start Command: python start.py
```

#### **3. Heroku**
```bash
# 1. Instalar Heroku CLI
# 2. Deploy
heroku create weather-stations-api
git push heroku main
```

#### **4. Local con Docker**
```bash
# Crear Dockerfile si es necesario
docker build -t weather-api .
docker run -p 8000:8000 weather-api
```

### 🔧 Variables de Entorno para Producción

```env
# Requeridas
CSV_FILE_PATH=datos_limpios_20251108_152228.csv

# Opcionales
GEMINI_API_KEY=tu_api_key_aqui
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

## Configuración

Puedes crear un archivo `.env` para personalizar la configuración:

```env
APP_NAME=Weather Stations API
DEBUG=true
RELOAD=true
HOST=0.0.0.0
PORT=8000
CSV_FILE_PATH=datos_limpios_20251108_152228.csv
LOG_LEVEL=INFO
```

### Auto-Reload

El servidor está configurado con **auto-reload habilitado por defecto**, lo que significa:

- ✅ **Reinicio automático** cuando cambias archivos Python en `/app/`
- ✅ **Desarrollo ágil** sin necesidad de reiniciar manualmente
- ✅ **Configurable** mediante la variable `RELOAD=true/false`

**Archivos monitoreados:**
- Todos los archivos `.py` en la carpeta `app/`
- Modelos, servicios, controladores y configuración
