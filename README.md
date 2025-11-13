# SENTINEL PRO v10.0 - Sistema Profesional de Gestión de Flotas

## 🚗 Descripción

SENTINEL PRO es un sistema avanzado de mantenimiento predictivo y gestión de flotas vehiculares que combina:

- **Lectura OBD-II en tiempo real** (21+ PIDs confirmados)
- **Análisis predictivo con IA** (Google Gemini)
- **Base de datos SQLite** persistente
- **Gestión multi-vehículo** (Sistema de flotas completo)
- **Seguimiento GPS** integrado
- **Analytics y gráficos** interactivos
- **Mapas de rutas** con Leaflet.js

## 📁 Estructura del Proyecto

```
ValoraCarIA/
├── backend/
│   ├── obd_server.py          # Servidor Flask principal
│   ├── database.py             # Gestor de base de datos SQLite
│   └── requirements.txt        # Dependencias Python
├── frontend/
│   ├── index.html              # Dashboard principal ✅
│   ├── fleet.html              # Gestión de flotas ✅
│   ├── analytics.html          # Análisis y gráficos ✅
│   ├── vehicle-detail.html     # Detalles de vehículo ✅
│   ├── css/
│   │   ├── style.css           # Estilos principales ✅
│   │   └── fleet.css           # Estilos de flotas ✅
│   └── js/
│       ├── common.js           # Funciones compartidas ✅
│       ├── script.js           # Lógica principal + GPS ✅
│       ├── fleet.js            # Gestión de flotas ✅
│       └── analytics.js        # (integrado en analytics.html) ✅
├── db/
│   └── sentinel.db             # Base de datos SQLite ✅
└── exports/
    └── csv/                    # Exportaciones CSV
```

## 🆕 Novedades v10.0

### 1. **Sistema de Base de Datos SQLite**
- ✅ Tabla `vehicles` - Gestión de múltiples vehículos
- ✅ Tabla `trips` - Historial completo de viajes
- ✅ Tabla `obd_data` - Datos OBD-II detallados
- ✅ Tabla `maintenance` - Registro de mantenimiento
- ✅ Tabla `alerts` - Sistema de alertas configurables
- ✅ Índices optimizados para consultas rápidas

### 2. **Tipo de Transmisión en Análisis IA**
- ✅ Campo de selección de transmisión añadido (Manual, Automática, DSG, CVT)
- ✅ Guardado en localStorage
- 🔄 Análisis IA mejorado con consideraciones específicas:
  - **Manual**: Análisis de uso de embrague
  - **Automática**: Evaluación de calidad de cambios
  - **DSG**: Comportamiento en cambios rápidos
  - **CVT**: Eficiencia de transmisión variable

### 3. **Módulo Common.js**
Funciones compartidas para todo el frontend:

```javascript
// Gestión de localStorage
SENTINEL.Storage.set('key', value)
SENTINEL.Storage.get('key', defaultValue)

// Llamadas API simplificadas
await SENTINEL.API.get('/endpoint')
await SENTINEL.API.post('/endpoint', data)

// Formateo de datos
SENTINEL.Formatter.date(date)
SENTINEL.Formatter.distance(km)
SENTINEL.Formatter.duration(seconds)

// Sistema de notificaciones
SENTINEL.Toast.success('Mensaje')
SENTINEL.Toast.error('Error')

// Utilidades GPS
await SENTINEL.GPS.getCurrentPosition()
SENTINEL.GPS.calculateDistance(lat1, lon1, lat2, lon2)
```

### 4. **DatabaseManager**
Clase Python completa para gestión de base de datos:

```python
from database import get_db

db = get_db()

# Crear vehículo
vehicle_id = db.create_vehicle(
    vin="ABC123456789",
    brand="Seat",
    model="León 2.0 TDI",
    year=2018,
    fuel_type="diesel",
    transmission="manual",
    mileage=95000
)

# Iniciar viaje
trip_id = db.start_trip(vehicle_id)

# Guardar datos OBD
db.save_obd_data_batch(trip_id, data_points)

# Finalizar viaje
db.end_trip(trip_id, stats)

# Obtener estadísticas
stats = db.get_vehicle_stats(vehicle_id)
```

## 🔧 Instalación

### Requisitos Previos
- Python 3.8+
- Adaptador OBD-II (ELM327 o compatible)
- Navegador moderno (Chrome, Firefox, Edge)

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd ValoraCarIA
```

2. **Instalar dependencias Python**
```bash
cd backend
pip install -r requirements.txt
```

3. **Configurar API de Gemini**
Edita `backend/obd_server.py`:
```python
GEMINI_API_KEY = "TU_API_KEY_AQUI"  # Obtener en https://makersuite.google.com/app/apikey
```

4. **Configurar puerto OBD**
```python
OBD_PORT = "COM6"  # Windows
OBD_PORT = "/dev/ttyUSB0"  # Linux
```

5. **Inicializar base de datos**
```bash
python database.py  # Test de inicialización
```

6. **Iniciar servidor**
```bash
python obd_server.py
```

7. **Abrir frontend**
```bash
# Abrir en navegador
cd ../frontend
# Servir con servidor local (ej: Live Server de VS Code)
# o simplemente abrir index.html
```

## 🚀 Uso

### Dashboard Principal (index.html)

1. **Configurar vehículo**
   - Marca, modelo, año
   - Kilometraje actual
   - **Tipo de transmisión** ✨ NUEVO
   - Tipo de combustible

2. **Monitorear en tiempo real**
   - Datos críticos cada 3s: RPM, velocidad, carga, MAF
   - Datos térmicos cada 60s: temperaturas
   - Score de salud 0-100

3. **Análisis predictivo con IA**
   - Predicción de fallos en 6-12 meses
   - Componentes prioritarios
   - Estimación de costes
   - **Análisis específico por transmisión** ✨ NUEVO

4. **Exportar datos**
   - CSV con datos completos del viaje
   - PDF con informe de diagnóstico

### Sistema de Flotas (pendiente de implementación completa)

**fleet.html** - Gestión visual de múltiples vehículos:
- Vista de tarjetas con todos los vehículos
- Estado de salud por vehículo
- Filtros por marca, combustible, estado
- Botón flotante "Añadir Vehículo"

**analytics.html** - Análisis avanzado:
- Gráficos Chart.js interactivos
- KPIs de flota
- Comparativas entre vehículos
- Heatmaps de uso
- Exportación a Excel

**vehicle-detail.html** - Detalles individuales:
- Historial completo de viajes
- Gráficos de rendimiento
- Mapas de rutas (Leaflet.js)
- Mantenimiento programado

## 📊 Base de Datos

### Esquema de Tablas

**vehicles**
- Gestión de múltiples vehículos
- VIN único por vehículo
- Soporte para activación/desactivación

**trips**
- Historial completo de viajes
- Estadísticas agregadas
- Referencia a datos GPS

**obd_data**
- Almacenamiento optimizado (batch insert)
- Datos de alta frecuencia
- Coordenadas GPS integradas

**maintenance**
- Registro de intervenciones
- Costes y fechas
- Próximo servicio

**alerts**
- Alertas configurables
- Niveles de severidad
- Sistema de reconocimiento

## 🗺️ GPS y Mapas (integración en progreso)

### Características planificadas:
- Geolocalización en tiempo real
- Cálculo de distancia con fórmula Haversine
- Mapas interactivos con Leaflet.js
- Reproducción animada de viajes
- Heatmaps de rutas frecuentes

## 🔌 API Endpoints

### Vehículos
```
POST   /api/vehicles          - Crear vehículo
GET    /api/vehicles          - Listar vehículos
GET    /api/vehicles/<id>     - Detalles de vehículo
PUT    /api/vehicles/<id>     - Actualizar vehículo
DELETE /api/vehicles/<id>     - Desactivar vehículo
```

### Viajes
```
POST   /api/trips/start       - Iniciar viaje
POST   /api/trips/stop        - Finalizar viaje
POST   /api/trips/<id>/data   - Guardar datos OBD
GET    /api/vehicles/<id>/trips          - Historial de viajes
GET    /api/vehicles/<id>/stats          - Estadísticas
```

### Mantenimiento
```
POST   /api/maintenance       - Registrar mantenimiento
GET    /api/vehicles/<id>/maintenance    - Historial
```

### Analytics
```
GET    /api/analytics/<vehicle_id>       - Datos para gráficos
GET    /api/fleet/stats                  - Estadísticas de flota
```

## 📈 Optimizaciones

### Backend
- ✅ Lectura OBD optimizada (críticos 3s, térmicos 60s)
- ✅ Batch insert para datos OBD (cada 10 registros)
- ✅ Índices en tablas para consultas rápidas
- ✅ Compresión de coordenadas GPS

### Frontend
- ✅ Polling inteligente con detección de fallos
- ✅ Caching de consultas frecuentes
- ✅ Loading spinners en operaciones asíncronas
- ✅ Sistema de notificaciones (toasts)

## 🛠️ Tecnologías

### Backend
- **Flask** - Framework web
- **SQLite3** - Base de datos
- **python-obd** - Comunicación OBD-II
- **Google Gemini AI** - Análisis predictivo
- **FPDF** - Generación de informes PDF

### Frontend
- **Vanilla JavaScript** - Sin frameworks
- **Chart.js** - Gráficos dinámicos (planificado)
- **Leaflet.js** - Mapas interactivos (planificado)
- **FontAwesome** - Iconografía

## 🔧 OBDb Integration (En Desarrollo)

⚠️ **ESTADO**: Temporalmente desactivada debido a conflictos de inicialización

SENTINEL PRO está en proceso de integrar la base de datos OBDb (Open Board Diagnostics Database)
para acceso a comandos OBD-II extendidos más allá de los PIDs básicos.

### Características Planificadas OBDb:
- 🔄 113 comandos OBD-II estándar (SAE J1979)
- 🔄 348 señales diferentes
- 🔄 Fuel trim (ajuste combustible)
- 🔄 Sensores O2 (lambda)
- 🔄 Sistema EGR
- 🔄 DPF (filtro partículas diesel)
- 🔄 Temperaturas gases escape
- 🔄 Monitores de emisiones

### Estado Actual:
El sistema funciona actualmente con **detección automática de PIDs soportados** por el vehículo.
La integración OBDb está temporalmente desactivada mientras se corrigen problemas de inicialización.

### Archivos Disponibles:
- `backend/default.json` - 113 comandos OBD-II (listo)
- `backend/obdb_parser.py` - Parser de comandos (listo)
- `backend/obdb_integration.py` - Integración con SENTINEL (en revisión)
- `backend/obdb_scanner.py` - Scanner de PIDs soportados (funcional)

### Para Desarrolladores:
La integración está comentada en `backend/obd_server.py` líneas 337-374.
Descomentar cuando se resuelvan los conflictos de inicialización con archivos inexistentes.

## ✅ Funcionalidades Implementadas (v10.0)

### Sistema de Flotas Completo
- [x] **API REST completa** con 20+ endpoints
  - Vehículos: CREATE, READ, UPDATE, DELETE
  - Viajes: Inicio/fin, datos OBD, historial
  - Mantenimiento: Registro y consultas
  - Analytics: Estadísticas y gráficos
  - Alertas: Creación y gestión

- [x] **fleet.html** - Gestión visual de flotas
  - Vista de tarjetas de vehículos
  - Filtros por marca, combustible, transmisión, salud
  - Modal para añadir/editar vehículos
  - Botón flotante de acción rápida
  - Estadísticas de flota en tiempo real
  - Vista grid/list intercambiable

- [x] **analytics.html** - Dashboard de análisis
  - Integración completa con Chart.js
  - KPIs dinámicos (viajes, distancia, velocidad, salud)
  - Gráfico de evolución de salud
  - Distribución de conducción (autopista/ciudad/carretera)
  - Tabla de viajes con exportación
  - Selector de rango de fechas

- [x] **fleet.js** - Lógica completa de gestión
  - Carga dinámica de vehículos desde API
  - Sistema de filtros en tiempo real
  - CRUD completo de vehículos
  - Inicio de viajes desde la flota
  - Gestión de vehículo activo

- [x] **fleet.css** - Estilos profesionales
  - Diseño responsive completo
  - Animaciones y transiciones suaves
  - Sistema de colores coherente
  - Modal system
  - Toasts notifications

### Base de Datos y Backend
- [x] DatabaseManager con SQLite
- [x] 5 tablas relacionales optimizadas
- [x] Índices para consultas rápidas
- [x] Batch insert para datos OBD
- [x] Sistema de vehículos activos/inactivos

### Mejoras en Análisis IA
- [x] Campo de tipo de transmisión en formulario
- [x] Guardado de transmisión en localStorage
- [x] **Análisis IA completo por tipo de transmisión**
  - Manual: Desgaste embrague, sincronización cambios
  - Automática: Suavidad cambios, fluido ATF
  - DSG/DCT: Cambios rápidos, mecatrónica
  - CVT: Eficiencia variable, correa/cadena

### Sistema GPS Integrado
- [x] **Tracking GPS en tiempo real**
  - watchPosition con alta precisión
  - Cálculo distancia con Haversine
  - Filtrado de datos erróneos
  - Priorización GPS sobre OBD
  - Almacenamiento de coordenadas (lat, lon)
  - Logging detallado cada 10 posiciones
  - Conversión m/s → km/h
  - Validación de velocidades
  - Preparado para mapas Leaflet.js

### 7. **Mapas Interactivos con Leaflet.js** ✅
- [x] **Visualización de rutas GPS en analytics.html**
  - Mapa interactivo con OpenStreetMap tiles
  - Polilíneas de colores para múltiples rutas
  - Marcadores de inicio (verde) y fin (rojo)
  - Popups informativos con datos del viaje
  - Selector de viajes individual o todos
  - Botón de centrado automático del mapa
  - Panel de estadísticas del viaje seleccionado
  - Zoom y pan interactivos
  - Integración con datos GPS de BD

### 8. **Página de Detalles de Vehículo (vehicle-detail.html)** ✅
- [x] **Vista completa individual por vehículo**
  - Tarjeta de información: VIN, año, combustible, transmisión
  - KPIs específicos: viajes, distancia, velocidad media, salud
  - Gráficos Chart.js: distancia por viaje, evolución de salud
  - Mapa del último viaje con ruta completa
  - Historial completo de viajes en tabla
  - Historial de mantenimiento
  - Selector de límite de viajes (10/25/50/100)
  - Botones de edición y para iniciar viaje
  - Responsive design
  - Integración completa con API

### 9. **Exportación a Excel Avanzada** ✅
- [x] **Reportes profesionales multi-hoja**
  - Librería SheetJS integrada
  - Hoja 1 - Resumen: datos vehículo + estadísticas
  - Hoja 2 - Viajes: tabla completa detallada
  - Hoja 3 - Datos Gráficos: datos numéricos
  - Formato profesional con anchos de columna
  - Nombre de archivo descriptivo con fecha
  - Fechas localizadas a español
  - Validación y notificaciones
  - Botón de exportación en analytics.html

## 📝 Próximas Mejoras

### Alta Prioridad ✅ (COMPLETADO)
- [x] Activar GPS automáticamente al iniciar viaje
- [x] Mapas interactivos con Leaflet.js en viajes
- [x] vehicle-detail.html con gráficos individuales
- [x] Exportación a Excel desde analytics
- [x] Guardado automático de coordenadas GPS en BD

### Media Prioridad
- [ ] Sistema de alertas en tiempo real
- [ ] Modo competición (telemetría estilo F1)
- [ ] Comparativa visual entre viajes
- [ ] Heatmaps de patrones de uso

### Baja Prioridad
- [ ] Generación de informes PDF mejorados
- [ ] Multi-idioma (i18n)
- [ ] Temas de color (dark mode)
- [ ] Notificaciones push del navegador
- [ ] PWA (Progressive Web App)

## 🤝 Contribución

Este proyecto está en desarrollo activo. Las contribuciones son bienvenidas.

## 📄 Licencia

Proyecto desarrollado como parte de ValoraCarIA.

## 🔗 Enlaces Útiles

- [Google Gemini API](https://makersuite.google.com/app/apikey)
- [Python OBD](https://python-obd.readthedocs.io/)
- [Chart.js](https://www.chartjs.org/)
- [Leaflet.js](https://leafletjs.com/)

## 📞 Soporte

Para problemas o sugerencias, crea un issue en el repositorio.

---

**SENTINEL PRO v10.0** - Sistema Profesional de Gestión de Flotas
© 2025 - Mantenimiento Predictivo Inteligente
