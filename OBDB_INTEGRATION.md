# OBDb Integration for SENTINEL PRO

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [¿Qué es OBDb?](#qué-es-obdb)
- [¿Qué añade a SENTINEL PRO?](#qué-añade-a-sentinel-pro)
- [Arquitectura](#arquitectura)
- [Instalación](#instalación)
- [Guía de Uso](#guía-de-uso)
- [Estructura de Datos](#estructura-de-datos)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## 🎯 Introducción

Esta integración expande SENTINEL PRO de **21 PIDs básicos** a **113+ comandos OBD-II extendidos** usando la base de datos **OBDb** (Open Board Diagnostics Database).

### ¿Por qué OBDb?

- ✅ **No Breaking**: Mantiene los 21 PIDs actuales funcionando
- ✅ **Opcional**: El sistema funciona sin OBDb (modo degradado)
- ✅ **Por Vehículo**: Perfiles específicos optimizan el monitoreo
- ✅ **AI-Enhanced**: Análisis Gemini más preciso con datos extendidos

---

## 🔍 ¿Qué es OBDb?

**OBDb** (Open Board Diagnostics Database) es una base de datos open-source que proporciona definiciones estructuradas de comandos OBD-II más allá de los estándares básicos.

### Características:

- 📊 **113+ comandos** OBD-II Mode 01
- 🏷️ **Categorización** por sistema (fuel, emissions, exhaust, etc.)
- 📝 **Metadatos** completos (unidades, rangos, frecuencias)
- 🔧 **Decodificación** de señales complejas
- 🚗 **Soporte** para gasolina, diesel, híbridos

---

## ⚡ ¿Qué añade a SENTINEL PRO?

### ANTES (21 PIDs básicos):
- RPM, velocidad, temperaturas
- Carga del motor, acelerador
- Presión de combustible
- MAF (Mass Air Flow)

### DESPUÉS (113+ señales):

#### 1. **Sistema de Combustible**
- Fuel trim (short/long) banco 1 y 2
- Estado del sistema de combustible
- Nivel de combustible preciso

#### 2. **Sensores de Oxígeno (Lambda)**
- O2 sensores banco 1 y 2
- Voltajes y corrientes
- Ratio lambda (aire-combustible)

#### 3. **Sistema de Emisiones**
- EGR (Exhaust Gas Recirculation)
- EVAP (sistema evaporativo)
- Estado de monitores de emisiones

#### 4. **Sistema de Escape**
- Temperaturas de gases de escape (4 sensores)
- Temperatura de catalizadores
- Monitoreo de eficiencia catalítica

#### 5. **DPF (Diesel)**
- Temperatura del filtro de partículas
- Presión diferencial
- Nivel de carga de hollín

#### 6. **Batería (Híbridos/Eléctricos)**
- Voltaje de batería HV
- Corriente de batería
- Estado de carga (SOC)

#### 7. **Diagnóstico**
- Estado de MIL (Check Engine)
- Conteo de DTCs pendientes
- Estado de monitores OBD

---

## 🏗️ Arquitectura

### Componentes Nuevos:

```
backend/
├── obdb_parser.py         # Parser de archivos JSON OBDb
├── obdb_integration.py    # Integración con SENTINEL PRO
├── obdb_scanner.py        # Scanner de vehículos
└── migrate_db.py          # Migración de base de datos

database/
└── sentinel.db
    ├── obd_data           # 21 PIDs básicos (SIN CAMBIOS)
    └── obd_extended       # Señales OBDb (NUEVA TABLA)

vehicle_profiles/
└── vehicle_{id}.json      # Perfiles por vehículo
```

### Flujo de Datos:

```
1. ESCANEO (una vez por vehículo):
   obdb_scanner.py → Detecta PIDs soportados → vehicle_profile.json

2. MONITOREO (durante viajes):
   OBD-II → obdb_integration.py → Señales extendidas →
   database.save_extended_signals() → obd_extended table

3. ANÁLISIS IA (bajo demanda):
   obd_data + obd_extended → obdb_integration.enhance_gemini_prompt() →
   Google Gemini → Análisis enriquecido
```

---

## 📦 Instalación

### 1. Requisitos Previos

```bash
# Asegurarse de que python-obd está instalado
pip install obd

# Verificar que existe la base de datos
ls -la db/sentinel.db
```

### 2. Migrar Base de Datos

**IMPORTANTE**: Esto crea un backup automático antes de migrar.

```bash
cd backend
python migrate_db.py
```

Salida esperada:
```
==================================================================
SENTINEL PRO - Database Migration
OBDb Extended Signals Support
==================================================================
[Migrate] Creating backup: ../db/sentinel.db.backup_20250112_143022
[Migrate] ✓ Backup created successfully (1048576 bytes)
[Migrate] Connecting to database: ../db/sentinel.db
[Migrate] Creating table 'obd_extended'...
[Migrate] ✓ Table created
[Migrate] Creating indices...
[Migrate] ✓ Indices created
[Migrate] ✓ Migration completed successfully
```

### 3. Crear Base de Datos OBDb Mínima

Si no tienes un archivo OBDb completo:

```bash
cd backend
python obdb_parser.py
```

Esto crea `obdb_minimal.json` con comandos comunes.

### 4. Escanear Vehículo (Opcional pero Recomendado)

Detecta qué comandos OBDb soporta tu vehículo específico:

```bash
# Windows
python obdb_scanner.py --vehicle-id 1 --port COM6

# Linux
python obdb_scanner.py --vehicle-id 1 --port /dev/ttyUSB0
```

Esto crea: `vehicle_profiles/vehicle_1.json`

---

## 📖 Guía de Uso

### Modo 1: Con Scanner (Recomendado)

1. **Escanear vehículo** una vez:
   ```bash
   python obdb_scanner.py --vehicle-id 1 --port COM6
   ```

2. **Iniciar servidor** con perfil:
   ```bash
   python obd_server.py
   ```

3. **Iniciar viaje** normalmente desde frontend

4. **Señales extendidas** se guardan automáticamente si están disponibles

### Modo 2: Sin Scanner (Degradado)

1. **Iniciar servidor** sin perfil:
   ```bash
   python obd_server.py
   ```

2. **Solo PIDs básicos** (21) funcionarán

3. **Sistema funcional** pero sin datos extendidos

---

## 📊 Estructura de Datos

### Tabla `obd_extended`

```sql
CREATE TABLE obd_extended (
    id INTEGER PRIMARY KEY,
    trip_id INTEGER,
    timestamp TIMESTAMP,

    -- Fuel System
    fuel_trim_short_1 REAL,    -- % (-100 a +100)
    fuel_trim_long_1 REAL,     -- % (-100 a +100)

    -- O2 Sensors
    o2_b1s1 REAL,              -- V (0 a 1.275)
    lambda_b1s1 REAL,          -- ratio (0.5 a 1.5)

    -- Emissions
    egr_commanded REAL,        -- % (0 a 100)
    egr_error REAL,            -- % (-100 a +100)

    -- Exhaust
    exhaust_temp_b1s1 REAL,    -- °C (-40 a 6513)
    catalyst_temp_b1s1 REAL,   -- °C (-40 a 6513)

    -- DPF (Diesel)
    dpf_temperature REAL,      -- °C
    dpf_pressure REAL,         -- kPa

    -- Diagnostics
    mil_status BOOLEAN,        -- Check Engine activo
    dtc_count INTEGER          -- Códigos pendientes
);
```

### Ejemplo de Datos:

```json
{
  "fuel_system": {
    "SHORT_FUEL_TRIM_1": {
      "value": 2.3,
      "unit": "%",
      "name": "Short Term Fuel Trim - Bank 1"
    },
    "LONG_FUEL_TRIM_1": {
      "value": -1.5,
      "unit": "%",
      "name": "Long Term Fuel Trim - Bank 1"
    }
  },
  "o2_sensors": {
    "O2_B1S1": {
      "value": 0.45,
      "unit": "V",
      "name": "O2 Sensor Voltage - Bank 1 Sensor 1"
    },
    "LAMBDA_B1S1": {
      "value": 0.98,
      "unit": "",
      "name": "Lambda - Bank 1 Sensor 1"
    }
  },
  "emissions": {
    "COMMANDED_EGR": {
      "value": 12.5,
      "unit": "%",
      "name": "Commanded EGR"
    }
  }
}
```

---

## 🔧 Troubleshooting

### Problema 1: "OBDb integration disabled"

**Síntomas**:
```
[OBDb Integration] ℹ️  Integration disabled (degraded mode)
```

**Causas posibles**:
- obdb_parser.py no encontrado
- obdb_minimal.json no existe
- python-obd no instalado

**Solución**:
```bash
# Crear base de datos mínima
python obdb_parser.py

# Verificar python-obd
pip install obd
```

### Problema 2: "Profile not found"

**Síntomas**:
```
[OBDb Integration] ⚠️  Profile not found: vehicle_profiles/vehicle_1.json
```

**Causas**:
- Vehículo no escaneado
- Directorio vehicle_profiles no existe

**Solución**:
```bash
# Crear directorio
mkdir vehicle_profiles

# Escanear vehículo
python obdb_scanner.py --vehicle-id 1 --port COM6
```

### Problema 3: "Migration failed"

**Síntomas**:
```
[Migrate] ✗ Migration failed: table obd_extended already exists
```

**Solución**:
- Tabla ya existe, migración no necesaria
- Si quieres recrear: restaura desde backup primero

### Problema 4: Scanner no detecta comandos

**Síntomas**:
```
[Scanner] ✓ Found 0 supported OBDb commands
```

**Causas**:
- Vehículo no conectado
- Puerto incorrecto
- Protocolo no compatible

**Solución**:
```bash
# Verificar conexión primero con python-obd básico
python
>>> import obd
>>> connection = obd.OBD("COM6")
>>> print(connection.status())
>>> connection.query(obd.commands.RPM)
```

---

## ❓ FAQ

### ¿Afecta a los datos existentes?

**NO**. La migración:
- ✅ Solo añade tabla nueva `obd_extended`
- ✅ NO modifica `obd_data` existente
- ✅ NO altera datos históricos
- ✅ Crea backup automático

### ¿Qué pasa si no escaneo mi vehículo?

El sistema funciona en **modo degradado**:
- ✅ 21 PIDs básicos funcionan
- ❌ Señales extendidas no disponibles
- ⚠️ Análisis IA menos preciso

### ¿Cuánto tarda el escaneo?

- **2-5 minutos** por vehículo
- Solo necesario **una vez** por vehículo
- Resultado se guarda en perfil JSON

### ¿Funciona con todos los vehículos?

Depende del vehículo:
- **Gasolina moderna** (2008+): ~70-90 comandos
- **Diesel Euro 5+**: ~80-100 comandos (con DPF)
- **Híbridos**: ~90-110 comandos (con batería HV)
- **Vehículos antiguos** (<2005): ~30-50 comandos

### ¿Cómo veo los datos extendidos?

1. **API Endpoint**:
   ```bash
   curl http://localhost:5000/api/obdb/extended-signals
   ```

2. **Base de Datos**:
   ```sql
   SELECT * FROM obd_extended WHERE trip_id = 123;
   ```

3. **Frontend** (próximamente):
   - Pestaña "Datos Extendidos OBDb"
   - Gráficos de fuel trim, O2, etc.

### ¿Afecta al rendimiento?

**Impacto mínimo**:
- Consultas OBDb: +100-200ms por ciclo
- Almacenamiento: +50 bytes por punto de datos
- Análisis IA: +5-10 segundos (por mayor contexto)

### ¿Puedo desactivar OBDb?

**SÍ**, simplemente:
1. No escanees el vehículo (no crees perfil)
2. El sistema detecta automáticamente la ausencia
3. Funciona en modo degradado (solo 21 PIDs)

---

## 📚 Referencias

- **OBDb GitHub**: https://github.com/openboarddata
- **python-obd Docs**: https://python-obd.readthedocs.io/
- **OBD-II PIDs**: https://en.wikipedia.org/wiki/OBD-II_PIDs
- **SENTINEL PRO**: README.md principal

---

## 🤝 Contribuciones

Si encuentras bugs o tienes sugerencias:

1. Abre un issue en GitHub
2. Describe el problema/mejora
3. Incluye logs relevantes
4. Especifica tu vehículo (marca, modelo, año)

---

## 📝 Changelog

### v1.0 (2025-01-12)
- ✅ Integración inicial de OBDb
- ✅ Parser JSON para comandos OBDb
- ✅ Scanner de vehículos
- ✅ Tabla `obd_extended` en base de datos
- ✅ Mejora de prompts Gemini AI
- ✅ Migración automática con backup
- ✅ Documentación completa

---

## 📄 Licencia

SENTINEL PRO © 2025 - Todos los derechos reservados
