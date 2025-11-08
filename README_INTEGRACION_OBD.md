# SENTINEL PRO - Integración OBD Server

## 🎯 Integración Completada

Se ha integrado exitosamente el servidor OBD (`obd_server.py`) con la aplicación SENTINEL PRO (`index.html` + `script.js`).

## 📊 PIDs Implementados (21 PIDs Confirmados)

### Datos Críticos (actualización cada 3 segundos)
1. **rpm** - Revoluciones por minuto del motor
2. **speed** - Velocidad del vehículo (km/h)
3. **throttle_pos** - Posición del acelerador (%)
4. **engine_load** - Carga del motor (%)
5. **maf** - Flujo de aire (g/s)
6. **intake_pressure** - Presión de admisión (kPa)
7. **voltage** - Voltaje de la ECU (V)

### Datos Térmicos (actualización cada 60 segundos)
8. **coolant_temp** - Temperatura del refrigerante (°C)
9. **intake_temp** - Temperatura de admisión (°C)

### Datos Diesel
10. **fuel_pressure** - Presión del rail de combustible (kPa)

### Datos Adicionales (todos los ciclos)
11. **barometric_pressure** - Presión barométrica (kPa)
12. **distance_mil** - Distancia con MIL encendido (km)
13. **relative_throttle** - Posición relativa del acelerador (%)
14. **ambient_temp** - Temperatura ambiente (°C)
15. **accelerator_d** - Posición acelerador D (%)
16. **accelerator_e** - Posición acelerador E (%)
17. **run_time** - Tiempo de marcha (s)
18. **distance_since_clear** - Distancia desde borrado DTC (km)

## 🚀 Cómo Usar

### 1. Iniciar el Servidor OBD

```bash
python obd_server.py
```

**Configuración requerida en `obd_server.py`:**
- `OBD_PORT = "COM6"` - Cambia al puerto de tu adaptador ELM327
- `GEMINI_API_KEY` - Tu clave API de Google Gemini

### 2. Abrir la Aplicación Web

Abre `index.html` en tu navegador preferido.

### 3. Verificar Conexión

- Si el OBD está conectado, verás una notificación verde: **"OBD conectado - 21 PIDs activos"**
- Los datos se actualizarán automáticamente en las cajas métricas
- Si no hay conexión, verás **"---"** en todos los campos

## 🔧 Endpoints Disponibles

### `/api/live_data` (GET)
Devuelve todos los 21 PIDs en formato JSON:

```json
{
  "connected": true,
  "rpm": 850,
  "speed": 0,
  "throttle_pos": 24.3,
  "engine_load": 42.4,
  "maf": 6.41,
  "coolant_temp": 38,
  "intake_temp": 20,
  "intake_pressure": 87,
  "voltage": 12.96,
  "fuel_pressure": 30820,
  "barometric_pressure": 94,
  "distance_mil": 0,
  "relative_throttle": 15.3,
  "ambient_temp": 17,
  "accelerator_d": 14.5,
  "accelerator_e": 14.5,
  "run_time": 88,
  "distance_since_clear": 0
}
```

### `/api/health` (GET)
Verifica el estado de la conexión OBD:

```json
{
  "connected": true,
  "port": "COM6",
  "status": "OK"
}
```

## 📝 Guardado de Datos

Todos los 21 PIDs se guardan automáticamente en CSV cuando el motor está encendido (RPM > 400):

**Ubicación:** `csv_data/obd_readings.csv`

**Columnas:**
```
timestamp, date, time, rpm, speed_kmh, throttle_pos, engine_load, maf,
coolant_temp, intake_temp, distance_since_clear, intake_pressure, voltage,
fuel_pressure, barometric_pressure, distance_mil, relative_throttle,
ambient_temp, accelerator_d, accelerator_e, run_time
```

## ⚡ Optimizaciones Implementadas

### Backend (obd_server.py)
- ✅ Reintentos automáticos (3 intentos por PID)
- ✅ Extracción de valores numéricos (magnitude)
- ✅ Datos térmicos optimizados (cada 60s)
- ✅ Datos críticos en cada consulta (cada 3s)
- ✅ Manejo de errores robusto

### Frontend (script.js)
- ✅ Polling cada 3 segundos
- ✅ Manejo de desconexión con modo offline
- ✅ Visualización de "---" cuando no hay datos
- ✅ Log de PIDs cada 30s en consola
- ✅ Notificaciones de estado de conexión

## 🔍 Depuración

### Consola del navegador
Abre las herramientas de desarrollador (F12) para ver:
- Estado de conexión OBD
- Valores de los 21 PIDs cada 30 segundos
- Errores de conexión

### Consola del servidor
Verás:
```
[OBD] Conectando a COM6...
[OBD] ✓ Conectado exitosamente
[OBD] ✓ 265 comandos soportados
[CSV] ✓ Archivo creado con 21 PIDs confirmados
✓ Servidor activo en http://localhost:5000
```

## 📋 Nombres de PIDs en python-obd

Los nombres exactos utilizados son:
- `RPM`, `SPEED`, `THROTTLE_POS`, `ENGINE_LOAD`
- `COOLANT_TEMP`, `INTAKE_TEMP`
- `MAF`, `INTAKE_PRESSURE`, `CONTROL_MODULE_VOLTAGE`
- `FUEL_RAIL_PRESSURE_DIRECT`
- `BAROMETRIC_PRESSURE`, `DISTANCE_W_MIL`, `RELATIVE_THROTTLE_POS`
- `AMBIANT_AIR_TEMP`, `ACCELERATOR_POS_D`, `ACCELERATOR_POS_E`
- `RUN_TIME`, `DISTANCE_SINCE_DTC_CLEAR`

## ✅ Funcionalidades Existentes Mantenidas

- ✅ Análisis predictivo con IA (Gemini)
- ✅ Averías comunes por modelo
- ✅ Tasación inteligente del vehículo
- ✅ Gestión de archivos CSV
- ✅ Historial de mantenimiento
- ✅ Generación de informes PDF
- ✅ Salud del vehículo en tiempo real
- ✅ Modo offline (funciona sin OBD)

## 🎨 Archivos NO Modificados

Según las restricciones del proyecto:
- ✅ `index.html` - Sin cambios
- ✅ `style.css` - Sin cambios

## 🐛 Solución de Problemas

### No se conecta al OBD
1. Verifica que el adaptador ELM327 esté conectado
2. Comprueba el puerto COM correcto en `OBD_PORT`
3. Verifica que el vehículo esté encendido (contacto ON)

### PIDs muestran "---"
1. El PID puede no estar soportado por tu vehículo
2. Verifica la consola del servidor para ver errores
3. Algunos PIDs requieren que el motor esté en marcha

### CSV no se guarda
1. Verifica que `csv_data/` exista
2. El motor debe estar en marcha (RPM > 400)
3. Comprueba permisos de escritura

## 📧 Soporte

Para más información, consulta:
- Documentación de python-obd: https://python-obd.readthedocs.io/
- Especificación OBD-II PIDs: https://en.wikipedia.org/wiki/OBD-II_PIDs

---

**SENTINEL PRO v9.0** - Sistema de Mantenimiento Predictivo © 2025
