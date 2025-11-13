# SENTINEL PRO v10.0

## Sistema Inteligente de Mantenimiento Predictivo y Gestión de Flotas

SENTINEL PRO es una aplicación web profesional que combina lectura OBD-II en tiempo real, análisis predictivo con IA (Google Gemini), y gestión completa de flotas vehiculares con base de datos SQLite.

---

## 📁 Estructura del Proyecto

```
sentinel-pro/
├── index.html              # Dashboard principal
├── fleet.html              # Gestión de flotas
├── vehicle-detail.html     # Detalles de vehículo
├── analytics.html          # Analytics y gráficos
├── alerts.html             # Sistema de alertas
├── import.html             # Importación de CSV
├── css/
│   ├── style.css           # Estilos principales
│   ├── fleet.css           # Estilos de flotas
│   └── alerts.css          # Estilos de alertas
├── js/
│   ├── common.js           # Funciones compartidas
│   ├── script.js           # Lógica principal
│   ├── fleet.js            # Gestión de flotas
│   └── alerts.js           # Sistema de alertas
├── backend/
│   ├── obd_server.py       # Servidor Flask principal
│   ├── database.py         # Gestor SQLite
│   ├── csv_importer.py     # Importador de CSV
│   ├── alert_monitor.py    # Monitor de alertas
│   ├── obdb_*.py           # Integración OBDb
│   ├── migrate_db.py       # Migraciones de BD
│   ├── requirements.txt    # Dependencias Python
│   └── default.json        # Configuración por defecto
├── db/
│   └── sentinel.db         # Base de datos SQLite
├── csv_data/               # Datos CSV exportados
├── uploaded_csv/           # CSV importados
├── vehicle_profiles/       # Perfiles de vehículos
├── README.md
└── .gitignore
```

---

## 🚀 Instalación Rápida

### 1. Instalar dependencias

```bash
pip install -r backend/requirements.txt
```

### 2. Configurar Backend

Edita `backend/obd_server.py` y configura:

```python
OBD_PORT = "COM6"  # Tu puerto OBD (Windows: COM3, COM4... | Linux: /dev/ttyUSB0)
GEMINI_API_KEY = "tu_api_key_aqui"  # Opcional: para análisis IA
```

Para obtener una API key de Gemini gratis: https://makersuite.google.com/app/apikey

### 3. Iniciar el servidor

```bash
cd backend
python obd_server.py
```

### 4. Abrir en navegador

Abre `index.html` en tu navegador o usa un servidor local:

```bash
# Opción 1: Abrir directamente
open index.html

# Opción 2: Servidor Python
python -m http.server 8080
# Luego abre: http://localhost:8080
```

---

## 📖 Uso

### Crear un vehículo

1. Ve a **Flotas** (fleet.html)
2. Click en el botón **"+"** (esquina superior derecha)
3. Completa los datos: Marca, Modelo, Año, Combustible, Transmisión
4. Click en **"Guardar Vehículo"**

### Iniciar un viaje

1. Conecta tu adaptador OBD-II al puerto del vehículo
2. Enciende el motor
3. En el **Dashboard** (index.html), selecciona tu vehículo
4. Click en **"Iniciar Viaje"**
5. Los datos OBD se registrarán automáticamente cada 3 segundos

### Importar datos CSV

1. Ve a **Importar** (import.html)
2. Sube un archivo CSV de Torque, OBD11, Carista, VCDS, etc.
3. El sistema detectará automáticamente el formato
4. Asocia el CSV a un vehículo existente o crea uno nuevo
5. Click en **"Ejecutar Importación"**

### Ver análisis con IA

1. Asegúrate de tener configurada tu `GEMINI_API_KEY`
2. Ve a **Analytics** (analytics.html)
3. Selecciona un vehículo
4. Click en **"Generar Informe IA"**
5. Recibirás un análisis completo con:
   - Estado general del vehículo
   - Problemas detectados
   - Recomendaciones de mantenimiento
   - Estimación de costos

---

## 🔌 API REST

El backend expone una API REST completa:

### Vehículos
- `GET /api/vehicles` - Listar todos
- `GET /api/vehicles/<id>` - Obtener uno
- `POST /api/vehicles` - Crear
- `PUT /api/vehicles/<id>` - Actualizar
- `DELETE /api/vehicles/<id>` - Eliminar (soft delete)

### Flotas
- `GET /api/fleet/stats` - Estadísticas generales

### Viajes
- `GET /api/trips` - Listar todos los viajes
- `POST /api/trips/start` - Iniciar viaje
- `POST /api/trips/<id>/stop` - Finalizar viaje

### Alertas
- `GET /api/alerts` - Listar alertas
- `POST /api/alerts/<id>/acknowledge` - Reconocer alerta

### Análisis con IA (Gemini)
- `GET /api/gemini/status` - Verificar disponibilidad
- `POST /api/gemini/analyze` - Análisis general
- `POST /api/gemini/analyze-csv` - Análisis de CSV
- `POST /api/gemini/health-report` - Informe de salud completo

### Importación CSV
- `POST /api/import/analyze` - Analizar formato CSV
- `POST /api/import/execute` - Ejecutar importación

---

## ✨ Características

### Datos en Tiempo Real
- ✅ **Datos críticos cada 3s**: RPM, velocidad, acelerador, carga motor, MAF
- ✅ **Datos térmicos cada 60s**: Temperatura refrigerante/admisión
- ✅ **Cálculo preciso de distancia** por integración de velocidad

### Análisis Predictivo
- ✅ **Scoring de salud** (0-100) con 3 subsistemas (motor, térmica, eficiencia)
- ✅ **Detección automática de problemas** (sobrecalentamiento, RPM excesivas, etc.)
- ✅ **Predicción de fallos** basada en patrones de uso
- ✅ **Análisis con IA** usando Google Gemini

### Gestión de Flotas
- ✅ **Multi-vehículo** con base de datos SQLite
- ✅ **Historial completo** de viajes y mantenimiento
- ✅ **Estadísticas y analytics** avanzados
- ✅ **Mapas de rutas** con Leaflet.js
- ✅ **Sistema de alertas** configurable

### Importación de Datos
- ✅ **Detección automática** de formato CSV (Torque, OBD11, Carista, VCDS)
- ✅ **Mapeo inteligente** de columnas
- ✅ **División automática** en viajes
- ✅ **Validación de datos** con manejo de errores

---

## 🧪 Compatibilidad OBD-II

### PIDs Básicos Soportados (21+)
- RPM, Velocidad, Posición acelerador, Carga motor
- Temperatura refrigerante/admisión
- Flujo de aire (MAF), Presión de admisión
- Avance de encendido, Nivel de combustible
- Presión de combustible, y más...

### OBDb Integration (Opcional)
Si tienes los módulos OBDb, SENTINEL PRO puede acceder a cientos de señales adicionales específicas del fabricante.

---

## 🛠️ Tecnologías

**Backend:**
- Python 3.8+
- Flask (servidor web)
- python-obd (lectura OBD-II)
- google-generativeai (análisis IA)
- SQLite (base de datos)

**Frontend:**
- HTML5 + CSS3
- JavaScript ES6+ (Vanilla JS, sin frameworks)
- Chart.js (gráficos)
- Leaflet.js (mapas)

---

## 📊 Esquema de Base de Datos

```sql
vehicles           # Vehículos de la flota
trips              # Viajes realizados
obd_data           # Datos OBD-II detallados
maintenance        # Historial de mantenimiento
alerts             # Alertas activas
alert_rules        # Reglas de alertas
imports            # Historial de importaciones CSV
vehicle_pids_profiles  # Perfiles de PIDs por vehículo
obd_extended       # Datos OBD extendidos (OBDb)
```

---

## 🚨 Solución de Problemas

### El servidor no inicia
- Verifica que el puerto `5000` esté libre
- Ejecuta: `pip install -r backend/requirements.txt`

### No conecta con OBD
- Verifica el puerto correcto en `OBD_PORT`
- Asegúrate de que el adaptador esté conectado
- Enciende el motor del vehículo
- Prueba con diferentes baudrates (auto, 38400, 9600)

### Los botones de IA no funcionan
- Verifica que `GEMINI_API_KEY` esté configurada
- La API key debe tener más de 30 caracteres
- Visita `http://localhost:5000/api/gemini/status` para verificar

### Errores de importación CSV
- Verifica que el archivo sea CSV válido
- Asegúrate de que tenga columnas de timestamp y PIDs OBD
- Revisa la consola del navegador para más detalles

---

## 📝 Changelog

### v10.0 (Actual)
- ✅ Sistema completo de gestión de flotas
- ✅ Base de datos SQLite con 9 tablas
- ✅ API REST completa con 40+ endpoints
- ✅ Importación inteligente de CSV
- ✅ Integración con Google Gemini AI
- ✅ Sistema de alertas configurables
- ✅ Analytics avanzados con gráficos
- ✅ Mapas de rutas con Leaflet
- ✅ Optimización de lecturas OBD (3s críticos, 60s térmicos)

---

## 📄 Licencia

Este proyecto es de código abierto para uso educativo y personal.

---

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📧 Contacto

Para reportar bugs o sugerir mejoras, abre un issue en el repositorio.

---

**SENTINEL PRO v10.0** - Sistema Profesional de Mantenimiento Predictivo © 2025
