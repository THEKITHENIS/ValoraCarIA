# Changelog - SENTINEL PRO

Todos los cambios notables en este proyecto serán documentados aquí.

---

## [v10.0.1] - 2025-11-13

### 🔧 Reorganización de Estructura

**ANTES:**
```
ValoraCarIA/
├── frontend/
│   ├── index.html, fleet.html, etc.
│   ├── css/
│   └── js/
├── backend/
└── db/
```

**DESPUÉS:**
```
ValoraCarIA/
├── index.html, fleet.html, analytics.html, etc. (en raíz)
├── css/
├── js/
├── backend/
├── db/
├── csv_data/
├── uploaded_csv/
└── vehicle_profiles/
```

**Razón:** Simplificar rutas y facilitar el acceso directo a las páginas HTML.

---

### ✨ Nuevos Endpoints API

Se agregaron los siguientes endpoints al backend (`obd_server.py`):

#### Viajes
- **GET `/api/trips`** - Listar todos los viajes con paginación
  - Query params: `vehicle_id` (opcional), `limit`, `offset`
  - Retorna lista completa de viajes con estadísticas

#### IA con Gemini
- **GET `/api/gemini/status`** - Verificar disponibilidad de Gemini AI
  - Retorna: `available`, `model`, `configured`

- **POST `/api/gemini/analyze`** - Análisis general con IA
  - Body: `{ "prompt": "...", "context": {} }`
  - Retorna análisis personalizado

- **POST `/api/gemini/analyze-csv`** - Análisis de datos CSV de un vehículo
  - Body: `{ "vehicle_id": 1, "trip_id": optional }`
  - Retorna análisis detallado basado en estadísticas de uso

- **POST `/api/gemini/health-report`** - Informe completo de salud vehicular
  - Body: `{ "vehicle_id": 1, "include_maintenance": true }`
  - Retorna informe markdown con 6 secciones:
    1. Puntuación de salud general (0-100)
    2. Análisis de patrones de uso
    3. Diagnóstico por sistemas
    4. Recomendaciones de mantenimiento
    5. Problemas comunes del modelo
    6. Estimación de costos

---

### 🐛 Correcciones

#### Navegación entre páginas
- **Archivo:** `js/fleet.js:443-454`
- **Problema:** Al hacer clic en "Ver Detalle", redirigía a `index.html`
- **Solución:** Ahora redirige correctamente a `vehicle-detail.html?id=${vehicleId}`
- **Beneficio:** La página de detalle de vehículo es accesible desde la vista de flotas

#### Persistencia de vehículo activo
- **Archivo:** `js/common.js:758-766`
- **Estado:** ✅ Ya funcionaba correctamente
- **Funcionalidad:**
  - Usa `localStorage.getItem('activeVehicleId')` para mostrar el link de "Vehículo" en navbar
  - Link se muestra solo si hay un vehículo activo seleccionado

#### Rutas CSS/JS en HTML
- **Estado:** ✅ Ya estaban correctas
- Todos los archivos HTML ya usaban rutas relativas correctas:
  - `css/style.css`, `css/fleet.css`, `css/alerts.css`
  - `js/common.js`, `js/script.js`, `js/fleet.js`, `js/alerts.js`

---

### 📦 Sistema de Importación CSV

**Estado:** ✅ Completamente funcional

El sistema ya contaba con:
- ✅ Endpoint `/api/import/analyze` - Detecta formato CSV automáticamente
- ✅ Endpoint `/api/import/execute` - Ejecuta importación con mapeo de columnas
- ✅ Tabla `imports` en BD - Registra todas las importaciones
- ✅ CSVImporter - Maneja Torque, OBD11, Carista, VCDS, etc.
- ✅ División automática en viajes basada en gaps de tiempo

**No se requirieron cambios.**

---

### 📝 Documentación

#### README.md - Completamente reescrito
- ✅ Estructura del proyecto actualizada
- ✅ Instalación paso a paso
- ✅ Guía de uso completa
- ✅ Documentación de API REST (40+ endpoints)
- ✅ Solución de problemas comunes
- ✅ Changelog integrado

#### .gitignore - Nuevo archivo
Protege archivos sensibles:
- Base de datos (*.db, *.sqlite)
- CSV importados (csv_data/, uploaded_csv/)
- Claves API y credenciales
- Archivos temporales y backups
- Entornos virtuales Python
- Archivos del sistema operativo

---

### 🧪 Verificaciones Realizadas

#### Backend
- ✅ Todos los endpoints existen y están correctamente definidos
- ✅ Base de datos SQLite con 9 tablas
- ✅ DatabaseManager se inicializa correctamente con `get_db()`
- ✅ CSVImporter integrado y funcional
- ✅ Gemini AI configurado (requiere API key del usuario)
- ✅ OBDb integration opcional disponible

#### Frontend
- ✅ Todos los HTML cargan sin errores 404
- ✅ Navegación entre páginas funciona correctamente
- ✅ Sistema de vehículo activo con localStorage
- ✅ Links de navegación se muestran/ocultan dinámicamente
- ✅ Página de detalle de vehículo carga datos correctamente

#### Estructura de archivos
- ✅ HTML en raíz del proyecto
- ✅ CSS en carpeta `css/`
- ✅ JavaScript en carpeta `js/`
- ✅ Backend en carpeta `backend/`
- ✅ Base de datos en carpeta `db/`
- ✅ Carpetas auxiliares creadas: `csv_data/`, `uploaded_csv/`

---

## Checklist de Funcionalidad

### Backend ✅
- [x] Backend inicia sin errores: `python backend/obd_server.py`
- [x] Base de datos se crea en `db/sentinel.db`
- [x] Todos los endpoints REST funcionan
- [x] DatabaseManager carga correctamente
- [x] CSVImporter disponible
- [x] Gemini AI disponible (con API key)

### Frontend ✅
- [x] Todos los HTML cargan sin errores 404
- [x] Navegación entre páginas funciona
- [x] Se pueden crear vehículos (fleet.html)
- [x] Se pueden iniciar viajes (index.html)
- [x] Se pueden importar CSVs (import.html)
- [x] Página de detalle carga correctamente (vehicle-detail.html)

### Integración ✅
- [x] Frontend conecta con backend (API REST)
- [x] localStorage persiste vehículo activo
- [x] Rutas CSS/JS correctas en todos los HTML
- [x] Sistema de navegación dinámico funciona

---

## Notas Técnicas

### Compatibilidad con OBDb
El sistema mantiene **retrocompatibilidad total** con la integración OBDb:
- PIDs básicos (21) siempre disponibles
- PIDs extendidos (cientos) con módulos OBDb opcionales
- Modo híbrido: Si OBDb falla, sistema cae a PIDs básicos

### Estructura de Base de Datos
```sql
vehicles              -- Vehículos de la flota
trips                 -- Viajes realizados
obd_data              -- Lecturas OBD-II
maintenance           -- Historial de mantenimiento
alerts                -- Alertas activas
alert_rules           -- Reglas de alertas
imports               -- Historial de importaciones CSV
vehicle_pids_profiles -- Perfiles de PIDs por vehículo
obd_extended          -- Datos extendidos (OBDb)
```

### Optimizaciones de Rendimiento
- Datos críticos cada 3s (RPM, velocidad, acelerador, carga, MAF)
- Datos térmicos cada 60s (temperaturas)
- Cálculo de distancia por integración de velocidad
- Análisis de salud automático cada 90s

---

## Próximos Pasos (Opcional)

### Mejoras Sugeridas
1. **Autenticación de usuarios** - Sistema de login/registro
2. **Notificaciones push** - Alertas en tiempo real
3. **Modo offline** - Service Workers para funcionar sin conexión
4. **Exportación de informes** - PDF con gráficos
5. **Dashboard personalizable** - Widgets arrastrables
6. **Integración con APIs externas** - Precio de combustible, tráfico, etc.

### Optimizaciones Futuras
1. **WebSockets** - Datos OBD en tiempo real sin polling
2. **Compresión de datos** - Reducir tamaño de base de datos
3. **Índices adicionales** - Mejorar velocidad de consultas
4. **Cache Redis** - Acelerar respuestas de API
5. **Tests unitarios** - Cobertura con pytest

---

**Fecha de actualización:** 2025-11-13
**Versión:** v10.0.1
**Estado:** ✅ Producción estable
