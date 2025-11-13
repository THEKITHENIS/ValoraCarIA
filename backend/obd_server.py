# -----------------------------------------------------------------------------
# SENTINEL PRO - MANTENIMIENTO PREDICTIVO v9.0 - SERVIDOR COMPLETO
# Copia y pega TODO este archivo como obd_server.py
# -----------------------------------------------------------------------------
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import obd
import time
import json
import requests
import geocoder
import google.generativeai as genai
from fpdf import FPDF
import os
import traceback
import re
import csv
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import statistics
from csv_importer import CSVImporter

# === OBDb Integration ===
try:
    from obdb_parser import OBDbParser
    from obdb_integration import OBDbIntegration
    OBDB_AVAILABLE = True
    print("[OBDb] ✓ Módulos OBDb cargados correctamente")
except ImportError as e:
    OBDB_AVAILABLE = False
    print(f"[OBDb] ⚠️ Módulos OBDb no disponibles: {e}")
    print("[OBDb] El sistema funcionará solo con PIDs básicos (21)")

# ----- CONFIGURACIÓN OBLIGATORIA -----
OBD_PORT = "COM6"  # CAMBIA ESTO A TU PUERTO
GEMINI_API_KEY = "TU_GEMINI_API_KEY"  # TU API KEY
GEMINI_MODEL_NAME = "models/gemini-pro-latest"
# -------------------------------------

# Configuración de archivos
CSV_FOLDER = 'csv_data'
UPLOAD_FOLDER = 'uploaded_csv'
ALLOWED_EXTENSIONS = {'csv'}
CSV_FILENAME = os.path.join(CSV_FOLDER, 'obd_readings.csv')
HEALTH_HISTORY_FILE = 'health_history.json'
TRIP_HISTORY_FILE = 'historial_viajes.json'

os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Variables globales
connection = None
supported_commands_cache = set()
last_connection_attempt_time = 0
last_thermal_reading_time = 0
RECONNECTION_COOLDOWN = 10
THERMAL_READING_INTERVAL = 60

trip_data = {}
maintenanceHistory = []

# Variables globales OBDb
obdb_integration = None
obdb_parser = None

vehicle_health = {
    "overall_score": 100,
    "engine_health": 100,
    "thermal_health": 100,
    "efficiency_health": 100,
    "warnings": [],
    "predictions": [],
    "last_update": None
}

# === DETECCIÓN DINÁMICA DE PIDs ===
# Lista completa de PIDs a intentar leer (basada en especificación OBD-II completa)
ALL_POSSIBLE_PIDS = [
    'RPM', 'SPEED', 'THROTTLE_POS', 'ENGINE_LOAD', 'COOLANT_TEMP',
    'INTAKE_TEMP', 'MAF', 'INTAKE_PRESSURE', 'BAROMETRIC_PRESSURE',
    'TIMING_ADVANCE', 'FUEL_PRESSURE', 'FUEL_RAIL_PRESSURE_VAC',
    'FUEL_RAIL_PRESSURE_DIRECT', 'FUEL_RAIL_PRESSURE_ABS', 'COMMANDED_EGR',
    'EGR_ERROR', 'EVAPORATIVE_PURGE', 'FUEL_LEVEL', 'DISTANCE_W_MIL',
    'COMMANDED_EQUIV_RATIO', 'RELATIVE_THROTTLE_POS', 'AMBIANT_AIR_TEMP',
    'ABSOLUTE_THROTTLE_POS_B', 'ABSOLUTE_THROTTLE_POS_C', 'ACCELERATOR_POS_D',
    'ACCELERATOR_POS_E', 'ACCELERATOR_POS_F', 'COMMANDED_THROTTLE_ACTUATOR',
    'RUN_TIME', 'DISTANCE_SINCE_DTC_CLEAR', 'EVAP_VAPOR_PRESSURE',
    'CATALYST_TEMP_B1S1', 'CATALYST_TEMP_B2S1', 'CATALYST_TEMP_B1S2',
    'CATALYST_TEMP_B2S2', 'CONTROL_MODULE_VOLTAGE', 'ABSOLUTE_LOAD',
    'TIME_SINCE_DTC_CLEAR', 'FUEL_TYPE', 'ETHANOL_PERCENT',
    'EVAP_VAPOR_PRESSURE_ABS', 'EVAP_VAPOR_PRESSURE_ALT', 'SHORT_O2_TRIM_B1',
    'LONG_O2_TRIM_B1', 'SHORT_O2_TRIM_B2', 'LONG_O2_TRIM_B2',
    'RELATIVE_ACCEL_POS', 'HYBRID_BATTERY_REMAINING', 'OIL_TEMP',
    'FUEL_INJECTION_TIMING', 'FUEL_RATE', 'EXHAUST_GAS_TEMP_B1S1',
    'EXHAUST_GAS_TEMP_B1S2', 'EXHAUST_GAS_TEMP_B2S1', 'EXHAUST_GAS_TEMP_B2S2',
    'DPF_TEMPERATURE', 'DPF_PRESSURE', 'SHORT_FUEL_TRIM_1', 'LONG_FUEL_TRIM_1',
    'SHORT_FUEL_TRIM_2', 'LONG_FUEL_TRIM_2', 'O2_B1S1', 'O2_B1S2',
    'O2_B1S3', 'O2_B1S4', 'O2_B2S1', 'O2_B2S2', 'O2_B2S3', 'O2_B2S4',
    'WARMUPS_SINCE_DTC_CLEAR', 'RUN_TIME_MIL'
]

# Variables para PIDs disponibles del vehículo actual
available_pids = []
current_vehicle_pids_profile = {}

# Inicialización Gemini
model = None
try:
    if "TU_API_KEY" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 30:
        raise ValueError("API KEY no válida")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print(f"[GEMINI] ✓ Configurado: {GEMINI_MODEL_NAME}")
except Exception as e:
    print(f"[GEMINI] ✗ Error: {e}")

# === FUNCIONES CSV ===
def initialize_csv():
    if not os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'date', 'time',
                'rpm', 'speed_kmh', 'throttle_pos', 'engine_load', 'maf',
                'coolant_temp', 'intake_temp', 'distance_km'
            ])
        print(f"[CSV] ✓ Archivo creado con columnas optimizadas")

def save_reading_to_csv(data, thermal_data=None):
    try:
        now = datetime.now()
        with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                now.isoformat(),
                now.strftime('%Y-%m-%d'),
                now.strftime('%H:%M:%S'),
                data.get('RPM', ''),
                data.get('SPEED', ''),
                data.get('THROTTLE_POS', ''),
                data.get('ENGINE_LOAD', ''),
                data.get('MAF', ''),
                thermal_data.get('COOLANT_TEMP', '') if thermal_data else '',
                thermal_data.get('INTAKE_TEMP', '') if thermal_data else '',
                data.get('total_distance', '')
            ])
    except Exception as e:
        print(f"[CSV] Error guardando: {e}")

def read_csv_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"[CSV] Error leyendo: {e}")
        return []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === CÁLCULO MEJORADO DE DISTANCIA ===
def calculate_distance(speed_kmh, time_delta_s):
    if speed_kmh and speed_kmh > 0 and time_delta_s > 0:
        distance_km = (speed_kmh / 3600) * time_delta_s
        return distance_km
    return 0

# === ANÁLISIS DE SALUD DEL VEHÍCULO ===
def analyze_vehicle_health(trip_points):
    global vehicle_health
    
    if not trip_points or len(trip_points) < 10:
        return vehicle_health
    
    try:
        rpms = [p.get('RPM', 0) for p in trip_points if p.get('RPM') and p.get('RPM') > 0]
        throttles = [p.get('THROTTLE_POS', 0) for p in trip_points if p.get('THROTTLE_POS') is not None]
        loads = [p.get('ENGINE_LOAD', 0) for p in trip_points if p.get('ENGINE_LOAD') is not None]
        mafs = [p.get('MAF', 0) for p in trip_points if p.get('MAF') and p.get('MAF') > 0]
        temps_coolant = [p.get('COOLANT_TEMP', 0) for p in trip_points if p.get('COOLANT_TEMP') and p.get('COOLANT_TEMP') > 0]
        temps_intake = [p.get('INTAKE_TEMP', 0) for p in trip_points if p.get('INTAKE_TEMP') and p.get('INTAKE_TEMP') > 0]
        
        warnings = []
        predictions = []
        
        # 1. SALUD DEL MOTOR
        engine_health = 100
        if rpms:
            rpm_avg = statistics.mean(rpms)
            rpm_max = max(rpms)
            
            high_rpm_count = sum(1 for r in rpms if r > 4000)
            high_rpm_ratio = high_rpm_count / len(rpms)
            
            if high_rpm_ratio > 0.3:
                engine_health -= 20
                warnings.append("⚠️ Uso frecuente de RPM altas (>4000). Aumenta desgaste del motor.")
                predictions.append("Riesgo medio de desgaste prematuro de componentes en 12-18 meses")
            
            if rpm_max > 6000:
                engine_health -= 15
                warnings.append("🔴 RPM CRÍTICAS detectadas (>6000). Revisar limitador.")
        
        if loads:
            load_avg = statistics.mean(loads)
            if load_avg > 80:
                engine_health -= 10
                warnings.append("⚠️ Carga motor alta (>80%). Revisar admisión.")
        
        # 2. SALUD TÉRMICA
        thermal_health = 100
        if temps_coolant:
            temp_max = max(temps_coolant)
            temp_avg = statistics.mean(temps_coolant)
            
            if temp_max > 105:
                thermal_health -= 30
                warnings.append("🔴 CRÍTICO: Temperatura >105°C. Revisar sistema URGENTE.")
                predictions.append("Riesgo ALTO de fallo en junta culata o radiador en 1-3 meses")
            elif temp_avg > 95:
                thermal_health -= 15
                warnings.append("⚠️ Temperatura elevada. Revisar termostato y radiador.")
                predictions.append("Riesgo medio de sobrecalentamiento. Mantenimiento en 3-6 meses")
        
        if temps_intake:
            temp_intake_avg = statistics.mean(temps_intake)
            if temp_intake_avg > 50:
                thermal_health -= 10
                warnings.append("⚠️ Temperatura admisión alta. Revisar intercooler.")
        
        # 3. EFICIENCIA
        efficiency_health = 100
        if mafs:
            maf_avg = statistics.mean(mafs)
            if maf_avg < 10 or maf_avg > 80:
                efficiency_health -= 15
                warnings.append("⚠️ Flujo aire anómalo. Revisar MAF y filtro.")
                predictions.append("Posible obstrucción en admisión. Reducción eficiencia 5-10%")
        
        if throttles and len(throttles) > 1:
            harsh_accel = 0
            for i in range(1, len(throttles)):
                if throttles[i] - throttles[i-1] > 30:
                    harsh_accel += 1
            
            harsh_ratio = harsh_accel / len(throttles)
            if harsh_ratio > 0.05:
                efficiency_health -= 10
                warnings.append("⚠️ Conducción agresiva. Aumenta consumo y desgaste.")
        
        # PUNTUACIÓN GLOBAL
        overall_score = round((engine_health + thermal_health + efficiency_health) / 3)
        
        vehicle_health = {
            "overall_score": overall_score,
            "engine_health": round(engine_health),
            "thermal_health": round(thermal_health),
            "efficiency_health": round(efficiency_health),
            "warnings": warnings,
            "predictions": predictions,
            "last_update": datetime.now().isoformat()
        }
        
        save_health_history(vehicle_health)
        return vehicle_health
        
    except Exception as e:
        print(f"[HEALTH] Error en análisis: {e}")
        return vehicle_health

def save_health_history(health_data):
    try:
        history = []
        if os.path.exists(HEALTH_HISTORY_FILE):
            with open(HEALTH_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history.append(health_data)
        
        if len(history) > 100:
            history = history[-100:]
        
        with open(HEALTH_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[HEALTH] Error guardando: {e}")

def get_trip_history():
    if os.path.exists(TRIP_HISTORY_FILE):
        with open(TRIP_HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_trip_summary(summary):
    history = get_trip_history()
    history.append(summary)
    with open(TRIP_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

# === FUNCIONES OBD ===
def initialize_obd_connection(force_reconnect=False):
    global connection, supported_commands_cache, last_connection_attempt_time
    
    current_time = time.time()
    if not force_reconnect and current_time - last_connection_attempt_time < RECONNECTION_COOLDOWN:
        return False
    
    last_connection_attempt_time = current_time
    
    if connection and connection.is_connected() and not force_reconnect:
        return True
    
    try:
        print(f"[OBD] Conectando a {OBD_PORT}...")
        new_connection = obd.OBD(OBD_PORT, baudrate=None, fast=False, timeout=10)
        
        if new_connection.is_connected():
            connection = new_connection
            print("[OBD] ✓ Conectado exitosamente")
            time.sleep(1)
            
            if force_reconnect or not supported_commands_cache:
                supported_commands_cache = set(connection.supported_commands)
            
            if supported_commands_cache:
                print(f"[OBD] ✓ {len(supported_commands_cache)} comandos soportados")

            # === Inicializar integración OBDb ===
            global obdb_integration, obdb_parser
            if OBDB_AVAILABLE:
                try:
                    print("[OBDb] Inicializando parser...")
                    obdb_parser = OBDbParser("default.json")

                    if obdb_parser.commands:
                        print(f"[OBDb] ✓ Parser cargado: {len(obdb_parser.commands)} comandos disponibles")

                        # Intentar cargar perfil del vehículo activo
                        # (Por ahora sin perfil específico)
                        obdb_integration = OBDbIntegration(connection)
                        print("[OBDb] ✓ Integración OBDb activada")
                    else:
                        print("[OBDb] ⚠️ No se cargaron comandos")
                        obdb_integration = None

                except Exception as e:
                    print(f"[OBDb] ⚠️ Error en integración OBDb: {e}")
                    import traceback
                    traceback.print_exc()
                    obdb_integration = None
            else:
                if not OBDB_AVAILABLE:
                    print("[OBDb] Módulos no disponibles")
                elif not connection:
                    print("[OBDb] Sin conexión OBD")
                obdb_integration = None

            return True
        else:
            print(f"[OBD] ✗ No se pudo conectar")
            connection = None
            return False
            
    except Exception as e:
        print(f"[OBD] ✗ Error: {e}")
        connection = None
        return False

def reset_trip():
    global trip_data
    trip_data = {
        "active": False,
        "start_time": None,
        "last_read_time": None,
        "distance_km": 0.0,
        "points": []
    }

reset_trip()
initialize_csv()

# === ENDPOINTS ===

@app.route("/get_live_data", methods=["GET"])
def get_live_data():
    global connection, trip_data, last_thermal_reading_time
    
    if not connection or not connection.is_connected():
        if not initialize_obd_connection(force_reconnect=True):
            return jsonify({
                "offline": True,
                "RPM": None,
                "SPEED": None,
                "THROTTLE_POS": None,
                "ENGINE_LOAD": None,
                "MAF": None,
                "COOLANT_TEMP": None,
                "INTAKE_TEMP": None,
                "total_distance": 0
            })
    
    # DATOS CRÍTICOS (cada 3s)
    critical_commands = [
        obd.commands.RPM,
        obd.commands.SPEED,
        obd.commands.THROTTLE_POS,
        obd.commands.ENGINE_LOAD,
        obd.commands.MAF
    ]
    
    results = {}
    for cmd in critical_commands:
        try:
            response = connection.query(cmd)
            if response and response.value is not None:
                results[cmd.name] = response.value.magnitude if hasattr(response.value, 'magnitude') else response.value
            else:
                results[cmd.name] = None
        except Exception as e:
            results[cmd.name] = None
    
    # DATOS TÉRMICOS (cada 60s)
    thermal_data = {}
    current_time = time.time()
    
    if current_time - last_thermal_reading_time >= THERMAL_READING_INTERVAL:
        thermal_commands = [
            obd.commands.COOLANT_TEMP,
            obd.commands.INTAKE_TEMP
        ]
        
        for cmd in thermal_commands:
            try:
                response = connection.query(cmd)
                if response and response.value is not None:
                    thermal_data[cmd.name] = response.value.magnitude if hasattr(response.value, 'magnitude') else response.value
                else:
                    thermal_data[cmd.name] = None
            except Exception as e:
                thermal_data[cmd.name] = None
        
        last_thermal_reading_time = current_time
        results.update(thermal_data)
    else:
        if trip_data.get("points") and len(trip_data["points"]) > 0:
            last_point = trip_data["points"][-1]
            results['COOLANT_TEMP'] = last_point.get('COOLANT_TEMP')
            results['INTAKE_TEMP'] = last_point.get('INTAKE_TEMP')
        else:
            results['COOLANT_TEMP'] = None
            results['INTAKE_TEMP'] = None
    
    # GESTIÓN DE VIAJE
    if results.get("RPM") and results.get("RPM") > 400:
        if not trip_data["active"]:
            reset_trip()
            trip_data["active"] = True
            trip_data["start_time"] = time.time()
            trip_data["last_read_time"] = time.time()
            print("[TRIP] ✓ Nuevo viaje iniciado")
        
        current_time = time.time()
        time_delta_s = current_time - trip_data["last_read_time"]
        
        if results.get("SPEED") and time_delta_s > 0:
            distance_increment = calculate_distance(results.get("SPEED"), time_delta_s)
            trip_data["distance_km"] += distance_increment
        
        results['total_distance'] = round(trip_data['distance_km'], 3)
        trip_data["points"].append(results)
        trip_data["last_read_time"] = current_time
        
        save_reading_to_csv(results, thermal_data if thermal_data else None)
        
        if len(trip_data["points"]) % 30 == 0:
            analyze_vehicle_health(trip_data["points"])
    else:
        results['total_distance'] = trip_data['distance_km'] if trip_data["active"] else 0
    
    return jsonify(results)

@app.route("/get_vehicle_health", methods=["GET"])
def get_vehicle_health():
    global vehicle_health
    return jsonify(vehicle_health)

@app.route("/get_health_history", methods=["GET"])
def get_health_history():
    try:
        if os.path.exists(HEALTH_HISTORY_FILE):
            with open(HEALTH_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return jsonify({"history": history})
        return jsonify({"history": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def get_obd_health():
    """
    Endpoint para verificar el estado de conexión OBD
    Retorna información sobre si el adaptador está conectado y el VIN del vehículo
    """
    try:
        # Verificar si el adaptador OBD está conectado
        obd_connected = connection is not None and hasattr(connection, 'is_connected') and connection.is_connected()

        # Intentar obtener VIN si está conectado
        vehicle_vin = None
        if obd_connected:
            try:
                # Intentar obtener VIN del vehículo conectado
                # Nota: Esto es opcional y depende de si el adaptador soporta este comando
                if hasattr(connection, 'query'):
                    vin_cmd = obd.commands.VIN
                    if vin_cmd:
                        response = connection.query(vin_cmd)
                        if response and not response.is_null():
                            vehicle_vin = str(response.value)
            except Exception as vin_error:
                print(f"[HEALTH] No se pudo obtener VIN: {vin_error}")

        return jsonify({
            "obd_connected": obd_connected,
            "vehicle_vin": vehicle_vin,
            "server_running": True,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        print(f"[API] Error en endpoint health: {e}")
        return jsonify({
            "obd_connected": False,
            "vehicle_vin": None,
            "server_running": True,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 200  # Retornar 200 aunque haya error para que el frontend sepa que el servidor está vivo

@app.route('/api/obd/scan-available-pids', methods=['POST'])
def scan_available_pids():
    """
    Escanea QUÉ PIDs están disponibles en el vehículo conectado
    Usa el método de 3 reintentos para máxima fiabilidad
    """
    global available_pids, current_vehicle_pids_profile

    if not connection or not connection.is_connected():
        return jsonify({'error': 'OBD no conectado'}), 400

    data = request.json
    vehicle_id = data.get('vehicle_id')

    print(f"\n🔍 Escaneando PIDs disponibles para vehículo {vehicle_id}...")
    print(f"   Probando {len(ALL_POSSIBLE_PIDS)} PIDs posibles...")

    available_pids = []
    pids_data = []

    # Probar cada PID con el método de 3 reintentos
    for idx, pid_name in enumerate(ALL_POSSIBLE_PIDS):
        if not hasattr(obd.commands, pid_name):
            continue

        try:
            cmd = getattr(obd.commands, pid_name)
            valor_final = None
            unidad = ''

            # 3 INTENTOS (método robusto)
            for intento in range(3):
                try:
                    response = connection.query(cmd)

                    if response and response.value is not None and not response.is_null():
                        valor = response.value

                        if hasattr(valor, 'magnitude'):
                            valor_final = valor.magnitude
                            unidad = str(response.unit) if hasattr(response, 'unit') else ''
                        else:
                            valor_final = valor
                            unidad = ''

                        break

                except:
                    pass

                time.sleep(0.05)

            # Si obtuvo valor después de 3 intentos
            if valor_final is not None:
                pid_info = {
                    'name': pid_name,
                    'command': str(cmd.command) if hasattr(cmd, 'command') else 'N/A',
                    'description': cmd.desc if hasattr(cmd, 'desc') else '',
                    'unit': unidad,
                    'sample_value': float(valor_final) if isinstance(valor_final, (int, float)) else str(valor_final)
                }
                available_pids.append(pid_name)
                pids_data.append(pid_info)
                print(f"  ✅ {pid_name}: {valor_final} {unidad}")

        except Exception as e:
            # Error silencioso para no spam en consola
            pass

        # Pequeña pausa para no saturar el adaptador
        time.sleep(0.03)

        # Progreso cada 10 PIDs
        if (idx + 1) % 10 == 0:
            print(f"   Progreso: {idx + 1}/{len(ALL_POSSIBLE_PIDS)} PIDs probados...")

    # Obtener protocolo del vehículo
    protocol = "Unknown"
    try:
        if hasattr(connection, 'protocol_name'):
            protocol = connection.protocol_name()
        elif hasattr(connection, 'protocol'):
            protocol = str(connection.protocol)
    except:
        pass

    # Guardar perfil de PIDs para este vehículo
    current_vehicle_pids_profile = {
        'vehicle_id': vehicle_id,
        'scan_date': datetime.now().isoformat(),
        'total_pids': len(available_pids),
        'pids': pids_data,
        'protocol': protocol
    }

    # Guardar en base de datos
    try:
        db = get_db()
        if db:
            db.save_vehicle_pids_profile(vehicle_id, current_vehicle_pids_profile)
    except Exception as e:
        print(f"[SCAN] Advertencia: No se pudo guardar perfil en BD: {e}")

    print(f"\n✅ Escaneo completado: {len(available_pids)} PIDs disponibles")
    print(f"   Protocolo: {protocol}")

    return jsonify({
        'success': True,
        'total_pids': len(available_pids),
        'available_pids': available_pids,
        'pids_data': pids_data,
        'profile': current_vehicle_pids_profile
    })

@app.route('/api/obd/live-data-dynamic', methods=['GET'])
def get_live_data_dynamic():
    """
    Lee TODOS los PIDs disponibles dinámicamente
    Si no se escaneó antes, usa lista básica
    """
    if not connection or not connection.is_connected():
        return jsonify({'error': 'OBD no conectado'}), 400

    # Usar PIDs disponibles o lista básica
    pids_to_read = available_pids if available_pids else [
        'RPM', 'SPEED', 'ENGINE_LOAD', 'THROTTLE_POS', 'COOLANT_TEMP',
        'INTAKE_TEMP', 'MAF', 'INTAKE_PRESSURE'
    ]

    data = {}

    for pid_name in pids_to_read:
        if not hasattr(obd.commands, pid_name):
            continue

        try:
            cmd = getattr(obd.commands, pid_name)

            # 2 reintentos (más rápido para live data)
            for intento in range(2):
                try:
                    response = connection.query(cmd)

                    if response and response.value is not None and not response.is_null():
                        valor = response.value

                        if hasattr(valor, 'magnitude'):
                            data[pid_name.lower()] = valor.magnitude
                        else:
                            data[pid_name.lower()] = valor

                        break

                except:
                    pass

                time.sleep(0.02)

        except:
            pass

    # Añadir timestamp
    data['timestamp'] = datetime.now().isoformat()

    return jsonify(data)

@app.route('/api/vehicles/<int:vehicle_id>/pids-profile', methods=['GET'])
def get_vehicle_pids_profile_endpoint(vehicle_id):
    """
    Obtiene el perfil de PIDs más reciente de un vehículo
    """
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Base de datos no disponible'}), 500

        profile = db.get_vehicle_pids_profile(vehicle_id)

        if not profile:
            return jsonify(None), 200  # Retornar null si no hay perfil

        return jsonify(profile)

    except Exception as e:
        print(f"[API] Error obteniendo perfil de PIDs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/predictive_analysis", methods=["POST"])
def predictive_analysis():
    global model, trip_data
    
    if not model:
        return jsonify({"error": "IA no configurada"}), 500
    
    vehicle_info = request.json.get("vehicleInfo", {})
    
    if not trip_data["points"] or len(trip_data["points"]) < 20:
        return jsonify({"error": "Datos insuficientes. Conduce al menos 2 minutos."}), 400
    
    try:
        points = trip_data["points"]
        
        rpms = [p.get('RPM', 0) for p in points if p.get('RPM')]
        loads = [p.get('ENGINE_LOAD', 0) for p in points if p.get('ENGINE_LOAD')]
        mafs = [p.get('MAF', 0) for p in points if p.get('MAF')]
        temps = [p.get('COOLANT_TEMP', 0) for p in points if p.get('COOLANT_TEMP')]
        
        stats = {
            "rpm_avg": round(statistics.mean(rpms)) if rpms else 0,
            "rpm_max": round(max(rpms)) if rpms else 0,
            "load_avg": round(statistics.mean(loads)) if loads else 0,
            "maf_avg": round(statistics.mean(mafs), 2) if mafs else 0,
            "temp_max": round(max(temps)) if temps else 0,
            "distance": round(trip_data["distance_km"], 2),
            "duration_min": round((trip_data["last_read_time"] - trip_data["start_time"]) / 60, 1)
        }
        
        # Obtener tipo de transmisión
        transmission = vehicle_info.get('transmission', 'manual')
        transmission_text = {
            'manual': 'MANUAL',
            'automatica': 'AUTOMÁTICA',
            'dsg': 'DSG/DCT (Doble Embrague)',
            'cvt': 'CVT (Transmisión Variable Continua)'
        }.get(transmission, 'MANUAL')

        # Análisis específico por transmisión
        transmission_analysis = {
            'manual': """
ANÁLISIS TRANSMISIÓN MANUAL:
- Evalúa desgaste de embrague analizando cambios bruscos de RPM
- Revisa sincronización de cambios basándote en relación RPM/velocidad
- Detecta patrones de uso incorrecto (salidas en marchas altas, exceso de RPM en neutro)
- Predice vida útil del embrague según estilo de conducción""",
            'automatica': """
ANÁLISIS TRANSMISIÓN AUTOMÁTICA:
- Evalúa suavidad de cambios mediante variaciones de RPM
- Detecta patrones de cambios anormales (kickdown excesivo, hunting entre marchas)
- Analiza temperatura de transmisión indirectamente vía carga del motor
- Predice necesidad de cambio de fluido ATF según kilometraje y uso""",
            'dsg': """
ANÁLISIS TRANSMISIÓN DSG/DCT:
- Evalúa comportamiento en cambios rápidos y secuenciales
- Detecta sobrecalentamiento del doble embrague en uso urbano intenso
- Analiza patrones de cambio en modo manual vs automático
- Predice desgaste de mecatrónica y embragues según estilo de conducción""",
            'cvt': """
ANÁLISIS TRANSMISIÓN CVT:
- Evalúa eficiencia de la transmisión variable mediante relación RPM/velocidad
- Detecta comportamiento anormal de la correa/cadena CVT
- Analiza patrones de deslizamiento o vibraciones (RPM constantes a velocidades variables)
- Predice necesidad de mantenimiento de fluido CVT según kilometraje"""
        }.get(transmission, '')

        prompt = f"""Eres ingeniero de diagnóstico vehicular especializado en MANTENIMIENTO PREDICTIVO y TRANSMISIONES.

VEHÍCULO: {vehicle_info.get('brand', 'N/D')} {vehicle_info.get('model', 'N/D')} ({vehicle_info.get('year', 'N/D')})
KILOMETRAJE: {vehicle_info.get('mileage', 'N/D')} km
COMBUSTIBLE: {vehicle_info.get('type', 'N/D').upper()}
TRANSMISIÓN: {transmission_text}

DATOS VIAJE:
- Duración: {stats['duration_min']} min
- Distancia: {stats['distance']} km
- RPM promedio: {stats['rpm_avg']} / máx: {stats['rpm_max']}
- Carga promedio: {stats['load_avg']}%
- MAF promedio: {stats['maf_avg']} g/s
- Temp máx: {stats['temp_max']}°C

{transmission_analysis}

Proporciona:
1. Predicción de fallos en 6-12 meses (INCLUYENDO análisis específico de transmisión {transmission_text})
2. Componentes prioritarios (motor + transmisión)
3. Vida útil estimada de componentes críticos
4. Mantenimiento preventivo (incluyendo fluidos de transmisión si aplica)
5. Análisis del estilo de conducción y su impacto en la transmisión

JSON VÁLIDO:
{{
    "predictive_score": 85,
    "risk_level": "Bajo",
    "predictions": [
        {{
            "component": "Bomba agua",
            "failure_probability": "15%",
            "estimated_timeframe": "12-18 meses",
            "symptoms": "Temp elevada ocasional",
            "action": "Inspeccionar próxima revisión"
        }}
    ],
    "priority_maintenance": [
        {{
            "task": "Cambio aceite",
            "urgency": "Alta",
            "timeframe": "1000km",
            "reason": "Kilometraje alto"
        }}
    ],
    "component_health": {{
        "engine": "85%",
        "cooling_system": "90%",
        "air_intake": "88%"
    }},
    "cost_estimate": {{
        "preventive_now": "150-300€",
        "if_delayed": "800-1500€"
    }}
}}"""

        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            ai_analysis = json.loads(json_match.group())
        else:
            ai_analysis = json.loads(cleaned)
        
        ai_analysis["trip_stats"] = stats
        ai_analysis["vehicle_health"] = vehicle_health
        
        return jsonify(ai_analysis)
        
    except Exception as e:
        print(f"[PREDICTIVE] Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/get_common_failures", methods=["POST"])
def get_common_failures():
    if not model:
        return jsonify({"error": "IA no configurada"}), 500
    
    v = request.json.get("vehicleInfo", {})
    brand = v.get("brand")
    model_year = v.get("model")
    year = v.get("year")
    
    if not all([brand, model_year, year]):
        return jsonify({"error": "Marca, modelo y año requeridos."}), 400
    
    prompt = f"""Actúa como mecánico jefe de taller con 20 años en {brand}.

VEHÍCULO: {brand} {model_year} año {year}

Identifica las 3 averías más comunes para este modelo específico.

Responde SOLO con JSON válido:
{{
    "failures": [
        {{
            "title": "Nombre de la avería",
            "symptom": "Síntoma que presenta",
            "cause": "Causa principal",
            "solution": "Solución recomendada",
            "severity": "Alta"
        }},
        {{
            "title": "Segunda avería",
            "symptom": "Síntoma",
            "cause": "Causa",
            "solution": "Solución",
            "severity": "Media"
        }},
        {{
            "title": "Tercera avería",
            "symptom": "Síntoma",
            "cause": "Causa",
            "solution": "Solución",
            "severity": "Baja"
        }}
    ],
    "recommendation": "Consejo general de mantenimiento preventivo para este modelo"
}}"""
    
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
        if json_match:
            failures_data = json.loads(json_match.group())
        else:
            failures_data = json.loads(cleaned_response)
        
        return jsonify(failures_data)
    except Exception as e:
        print(f"[FAILURES] Error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error IA: {e}"}), 500

@app.route("/get_vehicle_valuation", methods=["POST"])
def get_vehicle_valuation():
    if not model:
        return jsonify({"error": "IA no configurada"}), 500
    
    v = request.json.get("vehicleInfo", {})
    brand = v.get("brand", "")
    model_year = v.get("model", "")
    year = v.get("year", "")
    mileage = v.get("mileage", "")
    
    if not all([brand, model_year, year, mileage]):
        return jsonify({"error": "Todos los datos requeridos."}), 400

    trip_history = get_trip_history()
    driving_style_summary = "Sin datos"
    driving_quality_score = 5
    
    if trip_history and len(trip_history) > 0:
        total_km = sum(t.get('distancia_km', 0) for t in trip_history)
        
        if total_km > 1:
            driving_quality_score = 8
            driving_style_summary = f"Conducción registrada: {len(trip_history)} viajes"

    maintenance_history = request.json.get("maintenanceHistory", [])
    maintenance_score = 5
    
    if maintenance_history:
        num = len(maintenance_history)
        if num >= 10:
            maintenance_score = 9
        elif num >= 5:
            maintenance_score = 8
        elif num >= 2:
            maintenance_score = 7
        else:
            maintenance_score = 6

    print(f"[VALUATION] Tasando {brand} {model_year} {year}")
    
    try:
        prompt = f"""Eres tasador profesional de vehículos segunda mano en España con 20 años experiencia.

VEHÍCULO: {brand} {model_year} - Año {year} - {mileage} km - {v.get('type', 'gasolina')}

CONDICIÓN:
- Conducción: {driving_style_summary} (Score: {driving_quality_score}/10)
- Mantenimiento: {len(maintenance_history)} intervenciones (Score: {maintenance_score}/10)

Proporciona tasación realista del mercado español actual, ajustada por condición del vehículo.

Responde SOLO con JSON válido:
{{
    "min_price": 8000,
    "max_price": 12000,
    "realistic_price": 10000,
    "justification": "Explicación detallada de 2-3 líneas sobre la valoración"
}}"""

        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
        if json_match:
            valuation_data = json.loads(json_match.group())
        else:
            valuation_data = json.loads(cleaned_response)
        
        valuation_data["min_price"] = int(valuation_data["min_price"])
        valuation_data["max_price"] = int(valuation_data["max_price"])
        valuation_data["realistic_price"] = int(valuation_data["realistic_price"])
        
        print(f"[VALUATION] ✓ {valuation_data['realistic_price']}€")
        return jsonify(valuation_data)
        
    except Exception as e:
        print(f"[VALUATION] Error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error: {e}"}), 500

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(filepath)
        
        return jsonify({
            "success": True,
            "filename": new_filename
        })
    
    return jsonify({"error": "Tipo no permitido"}), 400

@app.route("/list_uploaded_csvs", methods=["GET"])
def list_uploaded_csvs():
    try:
        files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith('.csv'):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                size = os.path.getsize(filepath)
                modified = os.path.getmtime(filepath)
                files.append({
                    'filename': filename,
                    'size_kb': round(size / 1024, 2),
                    'modified': datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')
                })
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download_current_csv", methods=["GET"])
def download_current_csv():
    if os.path.exists(CSV_FILENAME):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            CSV_FILENAME,
            as_attachment=True,
            download_name=f'sentinel_data_{timestamp}.csv'
        )
    return jsonify({"error": "No hay datos"}), 404

@app.route("/generate_report", methods=["POST"])
def generate_report():
    vehicle_info = request.json.get("vehicleInfo", {})
    health_data = vehicle_health
    maintenance = request.json.get("maintenanceHistory", [])
    
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, 'SENTINEL PRO - Informe Diagnostico', 0, 1, 'C')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 10, f"{vehicle_info.get('brand', 'N/D')} {vehicle_info.get('model', 'N/D')} - {vehicle_info.get('year', 'N/D')}", 0, 1, 'C')
    pdf.cell(0, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Puntuacion Salud: {health_data['overall_score']}/100", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Sistemas:', 0, 1, 'L')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"- Motor: {health_data['engine_health']}/100", 0, 1)
    pdf.cell(0, 6, f"- Termica: {health_data['thermal_health']}/100", 0, 1)
    pdf.cell(0, 6, f"- Eficiencia: {health_data['efficiency_health']}/100", 0, 1)
    pdf.ln(5)
    
    if health_data['warnings']:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Advertencias:', 0, 1, 'L')
        pdf.set_font("Arial", '', 9)
        for w in health_data['warnings']:
            pdf.multi_cell(0, 5, f"- {w}")
    
    if health_data['predictions']:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Predicciones:', 0, 1, 'L')
        pdf.set_font("Arial", '', 9)
        for p in health_data['predictions']:
            pdf.multi_cell(0, 5, f"- {p}")
    
    if maintenance:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Mantenimiento:', 0, 1, 'L')
        pdf.set_font("Arial", '', 9)
        for m in maintenance[:10]:
            pdf.cell(0, 5, f"- {m.get('date', 'N/D')}: {m.get('type', 'N/D')}", 0, 1)
    
    filename = f"sentinel_pro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)

# =============================================================================
# ENDPOINTS IA OPTIMIZADOS - SENTINEL PRO v10.0
# =============================================================================

@app.route("/api/ai/analyze-current-trip", methods=["POST"])
def analyze_current_trip():
    """
    Analiza el viaje actualmente en curso (Dashboard)
    ACTUALIZADO: Usa TODOS los PIDs disponibles del vehículo
    """
    global model, trip_data

    if not model:
        return jsonify({"error": "IA no configurada"}), 500

    data = request.json
    vehicle_info = data.get("vehicle_info", {})
    trip_data_received = data.get("trip_data", [])
    transmission = data.get("transmission", "manual")
    vehicle_id = data.get("vehicle_id")

    # Validar datos mínimos (5 minutos = ~100 registros a 3s cada uno)
    if len(trip_data_received) < 100:
        return jsonify({
            "error": "Datos insuficientes. Conduce al menos 5 minutos.",
            "data_points": len(trip_data_received),
            "required": 100
        }), 400

    try:
        # Obtener perfil de PIDs disponibles del vehículo
        pids_profile = None
        if vehicle_id and db:
            pids_profile = db.get_vehicle_pids_profile(vehicle_id)

        # Analizar QUÉ PIDs están presentes en los datos del viaje
        available_pids_in_trip = list(trip_data_received[0].keys()) if trip_data_received else []
        available_pids_in_trip = [p for p in available_pids_in_trip if p != 'timestamp']

        # Calcular estadísticas dinámicas para TODOS los PIDs disponibles
        all_stats = {}
        for pid_key in available_pids_in_trip:
            values = [p.get(pid_key) for p in trip_data_received if p.get(pid_key) is not None]
            if values and all(isinstance(v, (int, float)) for v in values):
                try:
                    all_stats[pid_key] = {
                        'avg': round(statistics.mean(values), 2),
                        'min': round(min(values), 2),
                        'max': round(max(values), 2),
                        'count': len(values)
                    }
                except:
                    pass

        duration_min = len(trip_data_received) * 3 / 60  # 3 segundos por punto

        # Resumen básico para compatibilidad
        basic_stats = {
            "rpm_avg": all_stats.get('rpm', {}).get('avg', 0),
            "rpm_max": all_stats.get('rpm', {}).get('max', 0),
            "speed_avg": all_stats.get('speed', {}).get('avg', 0),
            "speed_max": all_stats.get('speed', {}).get('max', 0),
            "load_avg": all_stats.get('load', {}).get('avg', 0),
            "temp_max": all_stats.get('temp', {}).get('max', 0),
            "duration_min": round(duration_min, 1),
            "data_points": len(trip_data_received),
            "total_pids_monitored": len(available_pids_in_trip)
        }

        # Análisis específico por transmisión
        transmission_context = {
            'manual': 'transmisión MANUAL - evalúa uso de embrague y cambios',
            'automatica': 'transmisión AUTOMÁTICA - evalúa suavidad de cambios',
            'dsg': 'transmisión DSG/DCT - evalúa cambios rápidos y sobrecalentamiento',
            'cvt': 'transmisión CVT - evalúa eficiencia de correa/cadena'
        }.get(transmission, 'transmisión MANUAL')

        # Preparar contexto de PIDs disponibles
        pids_context = f"""
PIDs MONITORIZADOS: {len(available_pids_in_trip)} parámetros
Parámetros disponibles: {', '.join(available_pids_in_trip)}
"""

        if pids_profile:
            pids_context += f"""
Perfil del vehículo: {pids_profile.get('total_pids', 0)} PIDs detectados en escaneo
Protocolo: {pids_profile.get('protocol', 'Unknown')}
"""

        # Estadísticas detalladas de TODOS los PIDs
        detailed_stats = "\n".join([
            f"- {pid.upper()}: promedio {stats['avg']}, rango [{stats['min']} - {stats['max']}]"
            for pid, stats in all_stats.items()
        ])

        # Últimos 10 registros completos para contexto
        recent_samples = trip_data_received[-10:]

        prompt = f"""Eres ingeniero de diagnóstico automotriz analizando un VIAJE EN CURSO con MONITOREO COMPLETO.

VEHÍCULO: {vehicle_info.get('brand', 'N/D')} {vehicle_info.get('model', 'N/D')} ({vehicle_info.get('year', 'N/D')})
TRANSMISIÓN: {transmission.upper()} - {transmission_context}

{pids_context}

ESTADÍSTICAS DEL VIAJE ACTUAL:
Duración: {basic_stats['duration_min']} minutos
Puntos de datos: {basic_stats['data_points']}

ANÁLISIS DETALLADO DE TODOS LOS PARÁMETROS:
{detailed_stats}

ÚLTIMOS 10 REGISTROS COMPLETOS:
{json.dumps(recent_samples, indent=2)}

INSTRUCCIONES:
1. Analiza TODOS los {len(available_pids_in_trip)} parámetros disponibles (no solo los básicos)
2. Identifica patrones anormales en CUALQUIER parámetro
3. Evalúa eficiencia basándote en datos completos
4. Para cada parámetro fuera de rango normal, explica implicaciones
5. Da recomendaciones basadas en TODOS los datos, no solo RPM/velocidad
6. Score de conducción 0-100 considerando ALL parámetros

Responde SOLO con JSON válido:
{{
    "driving_score": 85,
    "style": "Eficiente|Moderado|Agresivo",
    "positives": ["Lista de aspectos positivos"],
    "concerns": ["Lista de preocupaciones identificadas en CUALQUIER parámetro"],
    "recommendations": ["Recomendaciones específicas basadas en TODOS los datos"],
    "transmission_health": "Buena|Regular|Atención",
    "parameters_analyzed": ["Lista de parámetros que fueron clave en el análisis"],
    "unusual_readings": ["PIDs con lecturas fuera de lo normal"],
    "trip_summary": "Resumen considerando TODOS los parámetros monitorizados"
}}"""

        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()

        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            ai_analysis = json.loads(json_match.group())
        else:
            ai_analysis = json.loads(cleaned)

        # Añadir estadísticas completas al resultado
        ai_analysis["trip_stats"] = basic_stats
        ai_analysis["all_parameters_stats"] = all_stats
        ai_analysis["pids_monitored"] = available_pids_in_trip
        ai_analysis["analyzed_at"] = datetime.now().isoformat()

        print(f"[AI-CURRENT-TRIP] ✓ Análisis completado: Score {ai_analysis.get('driving_score', 0)}/100, {len(available_pids_in_trip)} PIDs analizados")

        return jsonify(ai_analysis)

    except Exception as e:
        print(f"[AI-CURRENT-TRIP] ✗ Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/analyze-vehicle-history", methods=["POST"])
def analyze_vehicle_history():
    """
    Analiza el histórico completo de un vehículo (Fleet/Analytics/Vehicle-Detail)
    ACTUALIZADO: Incluye TODOS los PIDs disponibles en el análisis
    """
    global model

    if not model:
        return jsonify({"error": "IA no configurada"}), 500

    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.json
    vehicle_id = data.get("vehicle_id")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    include_predictions = data.get("include_predictions", True)

    if not vehicle_id:
        return jsonify({"error": "vehicle_id requerido"}), 400

    try:
        # Obtener datos del vehículo
        vehicle = db.get_vehicle(vehicle_id)
        if not vehicle:
            return jsonify({"error": "Vehículo no encontrado"}), 404

        # Obtener perfil de PIDs disponibles del vehículo
        pids_profile = db.get_vehicle_pids_profile(vehicle_id)

        # Obtener estadísticas
        stats = db.get_vehicle_stats(vehicle_id, start_date, end_date)

        # Obtener viajes recientes
        trips = db.get_vehicle_trips(vehicle_id, start_date, end_date, limit=20)

        # Obtener mantenimiento
        maintenance = db.get_vehicle_maintenance(vehicle_id)

        # Analizar qué PIDs se han registrado en el histórico
        all_pids_used = set()
        if trips:
            for trip in trips[:5]:  # Analizar últimos 5 viajes
                try:
                    trip_data = db.get_trip_obd_data(trip['id'])
                    if trip_data:
                        for datapoint in trip_data[:10]:  # Muestra de datos
                            all_pids_used.update(datapoint.keys())
                except:
                    pass

        # Quitar timestamp de la lista
        all_pids_used.discard('timestamp')
        all_pids_used.discard('id')

        # Preparar contexto de PIDs
        pids_context = ""
        if pids_profile:
            pids_context = f"""
PERFIL DE PIDs DEL VEHÍCULO:
- Total de parámetros disponibles: {pids_profile.get('total_pids', 0)} PIDs
- Protocolo OBD: {pids_profile.get('protocol', 'Unknown')}
- Último escaneo: {pids_profile.get('scan_date', 'N/D')}
- Parámetros registrados en histórico: {len(all_pids_used)} diferentes
- PIDs monitorizados: {', '.join(sorted(all_pids_used))}
"""
        else:
            pids_context = f"""
PARÁMETROS MONITORIZADOS:
- {len(all_pids_used)} parámetros diferentes registrados en histórico
- PIDs: {', '.join(sorted(all_pids_used))}
"""

        # Preparar prompt extenso con contexto completo
        prompt = f"""Eres sistema de MANTENIMIENTO PREDICTIVO analizando histórico completo con MONITOREO MULTI-PARÁMETRO.

VEHÍCULO:
{vehicle['brand']} {vehicle['model']} ({vehicle['year']})
VIN: {vehicle.get('vin', 'N/D')}
Combustible: {vehicle.get('fuel_type', 'N/D')}
Transmisión: {vehicle.get('transmission', 'N/D')}
Kilometraje actual: {vehicle.get('mileage', 0)} km

{pids_context}

ESTADÍSTICAS DEL PERÍODO ANALIZADO:
- Total viajes: {stats.get('total_trips', 0)}
- Distancia total: {stats.get('total_distance', 0)} km
- Velocidad promedio: {stats.get('avg_speed', 0)} km/h
- Score salud promedio: {stats.get('avg_health', 85)}/100

HISTORIAL MANTENIMIENTO:
{len(maintenance) if maintenance else 0} intervenciones registradas
{json.dumps(maintenance[:5], indent=2) if maintenance else 'Sin registros'}

ÚLTIMOS VIAJES:
{json.dumps([{
    'distance': t.get('distance', 0),
    'duration': t.get('duration', 0),
    'avg_speed': t.get('avg_speed', 0),
    'health_score': t.get('health_score', 100)
} for t in trips[:5]], indent=2) if trips else 'Sin viajes registrados'}

INSTRUCCIONES:
Analiza TODOS los {len(all_pids_used)} parámetros registrados en el histórico.

1. EVALUACIÓN GENERAL (0-100)
   - Considera TODOS los parámetros disponibles
   - Identifica tendencias en cada categoría de PIDs

2. COMPONENTES EN RIESGO
   - Basado en TODOS los datos históricos
   - Motor, térmico, combustible, transmisión, emisiones, eléctrico

3. PREDICCIONES 6-12 MESES
   - Usa TODOS los parámetros para predecir averías
   - Analiza patrones en datos completos

4. RECOMENDACIONES ESPECÍFICAS
   - Basadas en los {len(all_pids_used)} parámetros únicos registrados

5. ESTIMACIÓN COSTES (preventivo vs correctivo)

Responde SOLO con JSON válido:
{{
    "overall_score": 85,
    "trend": "Estable|Mejorando|Deteriorando",
    "components_at_risk": [
        {{
            "component": "Bomba de agua",
            "risk_level": "Alta|Media|Baja",
            "probability": "25%",
            "timeframe": "6-9 meses",
            "symptoms": "Temperatura elevada ocasional",
            "action": "Inspección en próxima revisión"
        }}
    ],
    "predictions": [
        {{
            "issue": "Posible fallo bomba agua",
            "timeframe": "6-9 meses",
            "cost_estimate": "200-400€",
            "prevention": "Cambio preventivo ahora: 150€"
        }}
    ],
    "priority_maintenance": [
        {{
            "task": "Cambio aceite + filtros",
            "urgency": "Alta|Media|Baja",
            "timeframe": "1 mes",
            "reason": "Kilometraje alto desde último cambio"
        }}
    ],
    "cost_summary": {{
        "preventive_now": "300-500€",
        "if_delayed_6_months": "800-1500€"
    }},
    "parameters_analyzed": ["Lista de parámetros que fueron clave en el análisis"],
    "monitoring_quality": "Excelente|Bueno|Limitado (según cantidad de PIDs disponibles)",
    "recommendations": ["Consejo 1 basado en TODOS los datos", "Consejo 2"]
}}"""

        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()

        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            ai_analysis = json.loads(json_match.group())
        else:
            ai_analysis = json.loads(cleaned)

        # Añadir metadata completa
        ai_analysis["vehicle_info"] = {
            "id": vehicle_id,
            "brand": vehicle['brand'],
            "model": vehicle['model'],
            "year": vehicle['year'],
            "mileage": vehicle.get('mileage', 0)
        }
        ai_analysis["analyzed_at"] = datetime.now().isoformat()
        ai_analysis["period"] = {
            "start": start_date,
            "end": end_date,
            "stats": stats
        }

        # Añadir información de PIDs monitorizados
        ai_analysis["pids_info"] = {
            "total_available": pids_profile.get('total_pids', 0) if pids_profile else 0,
            "protocol": pids_profile.get('protocol', 'Unknown') if pids_profile else 'Unknown',
            "unique_pids_in_history": len(all_pids_used),
            "pids_list": list(all_pids_used)
        }

        # Guardar análisis en BD (opcional)
        # db.save_ai_analysis(vehicle_id, ai_analysis, datetime.now())

        print(f"[AI-HISTORY] ✓ Análisis vehículo {vehicle_id}: Score {ai_analysis.get('overall_score', 0)}/100, {len(all_pids_used)} PIDs históricos")

        return jsonify(ai_analysis)

    except Exception as e:
        print(f"[AI-HISTORY] ✗ Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# =============================================================================
# ENDPOINTS REST API - SISTEMA DE FLOTAS v10.0
# =============================================================================

# Importar DatabaseManager
import sys
sys.path.append(os.path.dirname(__file__))
try:
    from database import get_db
    db = get_db()
    print("[DB] ✓ DatabaseManager cargado")
except Exception as e:
    print(f"[DB] ⚠️  Error cargando DatabaseManager: {e}")
    db = None

# Inicializar CSV Importer
csv_importer = CSVImporter(db) if db else None
if csv_importer:
    print("[CSV-IMPORTER] ✓ CSVImporter inicializado")

# Inicializar Alert Monitor
alert_monitor = None
try:
    from alert_monitor import AlertMonitor
    alert_monitor = AlertMonitor(db) if db else None
    if alert_monitor:
        print("[ALERT-MONITOR] ✓ AlertMonitor inicializado")
except Exception as e:
    print(f"[ALERT-MONITOR] ⚠️  Error cargando AlertMonitor: {e}")

# --- ENDPOINTS DE VEHÍCULOS ---

@app.route("/api/vehicles", methods=["POST"])
def create_vehicle_endpoint():
    """Crear un nuevo vehículo"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json

        # Validar campos requeridos
        required_fields = ['brand', 'model', 'year', 'fuel_type', 'transmission']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo requerido: {field}"}), 400

        vehicle_id = db.create_vehicle(
            vin=data.get('vin', f"VIN{int(time.time())}"),  # VIN temporal si no se proporciona
            brand=data['brand'],
            model=data['model'],
            year=int(data['year']),
            fuel_type=data['fuel_type'],
            transmission=data['transmission'],
            mileage=int(data.get('mileage', 0)),
            notes=data.get('notes', '')
        )

        return jsonify({
            "success": True,
            "vehicle_id": vehicle_id,
            "message": "Vehículo creado correctamente"
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"[API] Error creando vehículo: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles", methods=["GET"])
def get_vehicles_endpoint():
    """Obtener lista de vehículos"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        active_only = request.args.get('active', 'true').lower() == 'true'
        vehicles = db.get_all_vehicles(active_only=active_only)

        return jsonify({
            "success": True,
            "count": len(vehicles),
            "vehicles": vehicles
        })

    except Exception as e:
        print(f"[API] Error obteniendo vehículos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles/<int:vehicle_id>", methods=["GET"])
def get_vehicle_endpoint(vehicle_id):
    """Obtener detalles de un vehículo"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        vehicle = db.get_vehicle(vehicle_id)

        if not vehicle:
            return jsonify({"error": "Vehículo no encontrado"}), 404

        return jsonify({
            "success": True,
            "vehicle": vehicle
        })

    except Exception as e:
        print(f"[API] Error obteniendo vehículo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles/<int:vehicle_id>", methods=["PUT"])
def update_vehicle_endpoint(vehicle_id):
    """Actualizar un vehículo"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json

        # Actualizar vehículo
        success = db.update_vehicle(vehicle_id, **data)

        if not success:
            return jsonify({"error": "No se pudo actualizar el vehículo"}), 400

        return jsonify({
            "success": True,
            "message": "Vehículo actualizado correctamente"
        })

    except Exception as e:
        print(f"[API] Error actualizando vehículo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles/<int:vehicle_id>", methods=["DELETE"])
def delete_vehicle_endpoint(vehicle_id):
    """Desactivar un vehículo"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        success = db.delete_vehicle(vehicle_id, hard_delete=False)

        if not success:
            return jsonify({"error": "No se pudo desactivar el vehículo"}), 400

        return jsonify({
            "success": True,
            "message": "Vehículo desactivado correctamente"
        })

    except Exception as e:
        print(f"[API] Error desactivando vehículo: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS DE VIAJES ---

@app.route("/api/trips/start", methods=["POST"])
def start_trip_endpoint():
    """Iniciar un nuevo viaje"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json
        vehicle_id = data.get('vehicle_id')

        if not vehicle_id:
            return jsonify({"error": "vehicle_id requerido"}), 400

        trip_id = db.start_trip(vehicle_id)

        return jsonify({
            "success": True,
            "trip_id": trip_id,
            "message": "Viaje iniciado"
        }), 201

    except Exception as e:
        print(f"[API] Error iniciando viaje: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/trips/<int:trip_id>/stop", methods=["POST"])
def stop_trip_endpoint(trip_id):
    """Finalizar un viaje"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json
        stats = data.get('stats', {})

        success = db.end_trip(trip_id, stats)

        if not success:
            return jsonify({"error": "No se pudo finalizar el viaje"}), 400

        return jsonify({
            "success": True,
            "message": "Viaje finalizado"
        })

    except Exception as e:
        print(f"[API] Error finalizando viaje: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/trips/<int:trip_id>/data", methods=["POST"])
def save_trip_data_endpoint(trip_id):
    """Guardar datos OBD del viaje"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json
        data_points = data.get('data_points', [])

        if not data_points:
            return jsonify({"error": "No hay datos para guardar"}), 400

        success = db.save_obd_data_batch(trip_id, data_points)

        return jsonify({
            "success": True,
            "points_saved": len(data_points)
        })

    except Exception as e:
        print(f"[API] Error guardando datos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles/<int:vehicle_id>/trips", methods=["GET"])
def get_vehicle_trips_endpoint(vehicle_id):
    """Obtener historial de viajes de un vehículo"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        limit = int(request.args.get('limit', 50))
        trips = db.get_vehicle_trips(vehicle_id, limit=limit)

        return jsonify({
            "success": True,
            "count": len(trips),
            "trips": trips
        })

    except Exception as e:
        print(f"[API] Error obteniendo viajes: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/trips/<int:trip_id>", methods=["GET"])
def get_trip_endpoint(trip_id):
    """Obtener detalles de un viaje"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        trip = db.get_trip(trip_id)

        if not trip:
            return jsonify({"error": "Viaje no encontrado"}), 404

        # Opcional: incluir datos OBD
        include_obd = request.args.get('include_obd', 'false').lower() == 'true'
        if include_obd:
            trip['obd_data'] = db.get_trip_obd_data(trip_id)

        return jsonify({
            "success": True,
            "trip": trip
        })

    except Exception as e:
        print(f"[API] Error obteniendo viaje: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles/<int:vehicle_id>/stats", methods=["GET"])
def get_vehicle_stats_endpoint(vehicle_id):
    """Obtener estadísticas de un vehículo"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        stats = db.get_vehicle_stats(vehicle_id, start_date, end_date)

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        print(f"[API] Error obteniendo estadísticas: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS DE MANTENIMIENTO ---

@app.route("/api/maintenance", methods=["POST"])
def add_maintenance_endpoint():
    """Registrar mantenimiento"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json

        # Validar campos requeridos
        if 'vehicle_id' not in data or 'date' not in data or 'type' not in data:
            return jsonify({"error": "Campos requeridos: vehicle_id, date, type"}), 400

        maintenance_id = db.add_maintenance(
            vehicle_id=int(data['vehicle_id']),
            date=data['date'],
            type=data['type'],
            description=data.get('description'),
            mileage=int(data.get('mileage', 0)) if data.get('mileage') else None,
            cost=float(data.get('cost', 0)),
            mechanic=data.get('mechanic'),
            next_service_km=int(data.get('next_service_km', 0)) if data.get('next_service_km') else None
        )

        return jsonify({
            "success": True,
            "maintenance_id": maintenance_id,
            "message": "Mantenimiento registrado"
        }), 201

    except Exception as e:
        print(f"[API] Error registrando mantenimiento: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles/<int:vehicle_id>/maintenance", methods=["GET"])
def get_vehicle_maintenance_endpoint(vehicle_id):
    """Obtener historial de mantenimiento"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        limit = int(request.args.get('limit', 50))
        maintenance = db.get_vehicle_maintenance(vehicle_id, limit=limit)

        return jsonify({
            "success": True,
            "count": len(maintenance),
            "maintenance": maintenance
        })

    except Exception as e:
        print(f"[API] Error obteniendo mantenimiento: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS DE ANALYTICS ---

@app.route("/api/analytics/<int:vehicle_id>", methods=["GET"])
def get_analytics_endpoint(vehicle_id):
    """Obtener datos para análisis y gráficos"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Obtener estadísticas
        stats = db.get_vehicle_stats(vehicle_id, start_date, end_date)

        # Preparar datos para Chart.js
        trips = stats.get('trips', [])

        # Datos para gráfico de línea temporal (health score)
        health_timeline = {
            'labels': [t.get('start_time', '')[:10] for t in trips],
            'data': [t.get('health_score', 100) for t in trips]
        }

        # Datos para gráfico de barras (viajes por semana)
        # ... se puede mejorar agrupando por semana

        # Datos para gráfico circular (distribución conducción)
        highway_km = sum(t.get('distance', 0) for t in trips if t.get('avg_speed', 0) > 80)
        city_km = sum(t.get('distance', 0) for t in trips if t.get('avg_speed', 0) < 50)
        road_km = sum(t.get('distance', 0) for t in trips if 50 <= t.get('avg_speed', 0) <= 80)

        driving_distribution = {
            'labels': ['Autopista', 'Ciudad', 'Carretera'],
            'data': [highway_km, city_km, road_km]
        }

        return jsonify({
            "success": True,
            "vehicle_id": vehicle_id,
            "stats": stats,
            "charts": {
                "health_timeline": health_timeline,
                "driving_distribution": driving_distribution
            }
        })

    except Exception as e:
        print(f"[API] Error obteniendo analytics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/fleet/stats", methods=["GET"])
def get_fleet_stats_endpoint():
    """Obtener estadísticas de toda la flota"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        stats = db.get_fleet_stats()

        return jsonify({
            "success": True,
            "fleet_stats": stats
        })

    except Exception as e:
        print(f"[API] Error obteniendo estadísticas de flota: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS DE ALERTAS ---

@app.route("/api/alerts", methods=["POST"])
def create_alert_endpoint():
    """Crear una alerta"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json

        alert_id = db.create_alert(
            vehicle_id=int(data['vehicle_id']),
            alert_type=data['alert_type'],
            severity=data['severity'],
            message=data['message'],
            value=float(data.get('value')) if data.get('value') else None,
            threshold=float(data.get('threshold')) if data.get('threshold') else None,
            trip_id=int(data.get('trip_id')) if data.get('trip_id') else None
        )

        return jsonify({
            "success": True,
            "alert_id": alert_id
        }), 201

    except Exception as e:
        print(f"[API] Error creando alerta: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/vehicles/<int:vehicle_id>/alerts", methods=["GET"])
def get_vehicle_alerts_endpoint(vehicle_id):
    """Obtener alertas de un vehículo"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        acknowledged = request.args.get('acknowledged')
        if acknowledged is not None:
            acknowledged = acknowledged.lower() == 'true'

        alerts = db.get_vehicle_alerts(vehicle_id, acknowledged)

        return jsonify({
            "success": True,
            "count": len(alerts),
            "alerts": alerts
        })

    except Exception as e:
        print(f"[API] Error obteniendo alertas: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts", methods=["GET"])
def get_all_alerts_endpoint():
    """Obtener todas las alertas de la flota"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        acknowledged = request.args.get('acknowledged')
        if acknowledged is not None:
            acknowledged = acknowledged.lower() == 'true'

        limit = int(request.args.get('limit', 100))

        alerts = db.get_all_alerts(acknowledged, limit)

        return jsonify({
            "success": True,
            "count": len(alerts),
            "alerts": alerts
        })

    except Exception as e:
        print(f"[API] Error obteniendo todas las alertas: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<int:alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert_endpoint(alert_id):
    """Marcar una alerta como reconocida"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        success = db.acknowledge_alert(alert_id)

        if success:
            return jsonify({
                "success": True,
                "message": "Alerta reconocida correctamente"
            })
        else:
            return jsonify({"error": "Alerta no encontrada"}), 404

    except Exception as e:
        print(f"[API] Error reconociendo alerta: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/acknowledge-all", methods=["POST"])
def acknowledge_all_alerts_endpoint():
    """Marcar todas las alertas como reconocidas"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json or {}
        vehicle_id = data.get('vehicle_id')

        count = db.acknowledge_all_alerts(vehicle_id)

        return jsonify({
            "success": True,
            "acknowledged_count": count,
            "message": f"{count} alertas reconocidas"
        })

    except Exception as e:
        print(f"[API] Error reconociendo todas las alertas: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS DE REGLAS DE ALERTAS ---

@app.route("/api/alert-rules", methods=["POST"])
def create_alert_rule_endpoint():
    """Crear una regla de alerta"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json

        rule_id = db.create_alert_rule(
            vehicle_id=int(data.get('vehicle_id')) if data.get('vehicle_id') else None,
            name=data['name'],
            parameter=data['parameter'],
            condition=data['condition'],
            threshold=float(data['threshold']),
            severity=data['severity'],
            message_template=data.get('message_template'),
            notify_email=data.get('notify_email', False),
            notify_sound=data.get('notify_sound', True)
        )

        return jsonify({
            "success": True,
            "rule_id": rule_id,
            "message": "Regla de alerta creada correctamente"
        }), 201

    except Exception as e:
        print(f"[API] Error creando regla de alerta: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alert-rules", methods=["GET"])
def get_alert_rules_endpoint():
    """Obtener reglas de alertas"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        vehicle_id = request.args.get('vehicle_id')
        if vehicle_id:
            vehicle_id = int(vehicle_id)

        enabled_only = request.args.get('enabled_only', 'true').lower() == 'true'

        rules = db.get_alert_rules(vehicle_id, enabled_only)

        return jsonify({
            "success": True,
            "count": len(rules),
            "rules": rules
        })

    except Exception as e:
        print(f"[API] Error obteniendo reglas de alertas: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alert-rules/<int:rule_id>", methods=["GET"])
def get_alert_rule_endpoint(rule_id):
    """Obtener una regla de alerta por ID"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        rule = db.get_alert_rule(rule_id)

        if rule:
            return jsonify({
                "success": True,
                "rule": rule
            })
        else:
            return jsonify({"error": "Regla no encontrada"}), 404

    except Exception as e:
        print(f"[API] Error obteniendo regla de alerta: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alert-rules/<int:rule_id>", methods=["PUT"])
def update_alert_rule_endpoint(rule_id):
    """Actualizar una regla de alerta"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json

        success = db.update_alert_rule(rule_id, **data)

        if success:
            return jsonify({
                "success": True,
                "message": "Regla actualizada correctamente"
            })
        else:
            return jsonify({"error": "No se actualizó ningún campo"}), 400

    except Exception as e:
        print(f"[API] Error actualizando regla de alerta: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alert-rules/<int:rule_id>", methods=["DELETE"])
def delete_alert_rule_endpoint(rule_id):
    """Eliminar una regla de alerta"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        success = db.delete_alert_rule(rule_id)

        if success:
            return jsonify({
                "success": True,
                "message": "Regla eliminada correctamente"
            })
        else:
            return jsonify({"error": "Regla no encontrada"}), 404

    except Exception as e:
        print(f"[API] Error eliminando regla de alerta: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alert-rules/<int:rule_id>/toggle", methods=["POST"])
def toggle_alert_rule_endpoint(rule_id):
    """Activar/desactivar una regla de alerta"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json
        enabled = data.get('enabled', True)

        success = db.toggle_alert_rule(rule_id, enabled)

        if success:
            return jsonify({
                "success": True,
                "message": f"Regla {'activada' if enabled else 'desactivada'} correctamente"
            })
        else:
            return jsonify({"error": "Regla no encontrada"}), 404

    except Exception as e:
        print(f"[API] Error alternando regla de alerta: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alert-rules/default/<int:vehicle_id>", methods=["POST"])
def install_default_rules_endpoint(vehicle_id):
    """Instalar reglas predefinidas para un vehículo"""
    if not alert_monitor:
        return jsonify({"error": "Alert Monitor no disponible"}), 500

    try:
        count = alert_monitor.install_default_rules(vehicle_id)

        return jsonify({
            "success": True,
            "rules_installed": count,
            "message": f"{count} reglas predefinidas instaladas correctamente"
        })

    except Exception as e:
        print(f"[API] Error instalando reglas predefinidas: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/stats", methods=["GET"])
def get_alert_stats_endpoint():
    """Obtener estadísticas de alertas"""
    if not alert_monitor:
        return jsonify({"error": "Alert Monitor no disponible"}), 500

    try:
        vehicle_id = request.args.get('vehicle_id')
        if vehicle_id:
            vehicle_id = int(vehicle_id)

        days = int(request.args.get('days', 7))

        stats = alert_monitor.get_alert_stats(vehicle_id, days)

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        print(f"[API] Error obteniendo estadísticas de alertas: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS DE IMPORTACIÓN CSV ---

@app.route("/api/import/analyze", methods=["POST"])
def analyze_csv_endpoint():
    """
    Analiza un archivo CSV y detecta su formato

    Form Data:
        file: Archivo CSV a analizar

    Returns:
        Información detallada del CSV (fuente, columnas, preview, etc.)
    """
    if not csv_importer:
        return jsonify({"error": "CSV Importer no disponible"}), 500

    try:
        # Verificar que se subió un archivo
        if 'file' not in request.files:
            return jsonify({"error": "No se proporcionó ningún archivo"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "Nombre de archivo vacío"}), 400

        # Verificar extensión
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "El archivo debe ser CSV"}), 400

        # Guardar archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{int(time.time())}_{filename}")
        file.save(temp_path)

        # Analizar CSV
        analysis = csv_importer.analyze_csv(temp_path)

        # Agregar información del archivo temporal
        analysis['temp_file'] = os.path.basename(temp_path)
        analysis['original_filename'] = filename

        return jsonify(analysis)

    except Exception as e:
        print(f"[API] Error analizando CSV: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/import/execute", methods=["POST"])
def execute_import_endpoint():
    """
    Ejecuta la importación de un CSV previamente analizado

    Body JSON:
        temp_file: Nombre del archivo temporal
        vehicle_id: ID del vehículo destino (null para crear nuevo)
        source_type: Tipo de fuente detectada
        column_mappings: Mapeo de columnas
        create_trips: Si dividir en viajes
        trip_gap_minutes: Minutos para separar viajes
        skip_invalid_rows: Si omitir filas inválidas
        vehicle_data: (Opcional) Datos para crear nuevo vehículo

    Returns:
        Resultado de la importación
    """
    if not csv_importer:
        return jsonify({"error": "CSV Importer no disponible"}), 500

    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        data = request.json

        # Obtener parámetros
        temp_file = data.get('temp_file')
        vehicle_id = data.get('vehicle_id')
        source_type = data.get('source_type')
        column_mappings = data.get('column_mappings', {})
        create_trips = data.get('create_trips', True)
        trip_gap_minutes = data.get('trip_gap_minutes', 30)
        skip_invalid_rows = data.get('skip_invalid_rows', True)
        vehicle_data = data.get('vehicle_data')

        if not temp_file:
            return jsonify({"error": "temp_file requerido"}), 400

        # Construir ruta completa
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_file)

        if not os.path.exists(temp_path):
            return jsonify({"error": "Archivo temporal no encontrado"}), 404

        # Crear vehículo nuevo si se proporcionó vehicle_data
        if not vehicle_id and vehicle_data:
            vehicle_id = db.create_vehicle(
                vin=vehicle_data.get('vin', 'IMPORTED'),
                brand=vehicle_data.get('brand', 'Unknown'),
                model=vehicle_data.get('model', 'Unknown'),
                year=vehicle_data.get('year', 2020),
                fuel_type=vehicle_data.get('fuel_type', 'gasolina'),
                transmission=vehicle_data.get('transmission', 'manual'),
                mileage=vehicle_data.get('mileage', 0),
                notes=vehicle_data.get('notes')
            )
            print(f"[CSV-IMPORT] ✓ Vehículo creado: ID {vehicle_id}")

        if not vehicle_id:
            return jsonify({"error": "vehicle_id o vehicle_data requerido"}), 400

        # Ejecutar importación
        result = csv_importer.import_csv(
            csv_path=temp_path,
            vehicle_id=vehicle_id,
            source_type=source_type,
            column_mappings=column_mappings,
            create_trips=create_trips,
            trip_gap_minutes=trip_gap_minutes,
            skip_invalid_rows=skip_invalid_rows
        )

        # Limpiar archivo temporal
        try:
            os.remove(temp_path)
        except:
            pass

        return jsonify(result)

    except Exception as e:
        print(f"[API] Error ejecutando importación: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/import/history", methods=["GET"])
def get_import_history_endpoint():
    """Obtener historial de importaciones"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        vehicle_id = request.args.get('vehicle_id', type=int)

        conn = db._get_connection()
        cursor = conn.cursor()

        if vehicle_id:
            cursor.execute('''
                SELECT
                    i.*,
                    v.brand,
                    v.model,
                    v.year
                FROM imports i
                LEFT JOIN vehicles v ON i.vehicle_id = v.id
                WHERE i.vehicle_id = ?
                ORDER BY i.import_date DESC
            ''', (vehicle_id,))
        else:
            cursor.execute('''
                SELECT
                    i.*,
                    v.brand,
                    v.model,
                    v.year
                FROM imports i
                LEFT JOIN vehicles v ON i.vehicle_id = v.id
                ORDER BY i.import_date DESC
            ''')

        columns = [desc[0] for desc in cursor.description]
        imports = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return jsonify({
            "success": True,
            "count": len(imports),
            "imports": imports
        })

    except Exception as e:
        print(f"[API] Error obteniendo historial: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/import/<int:import_id>", methods=["GET"])
def get_import_detail_endpoint(import_id):
    """Obtener detalles de una importación específica"""
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                i.*,
                v.brand,
                v.model,
                v.year
            FROM imports i
            LEFT JOIN vehicles v ON i.vehicle_id = v.id
            WHERE i.id = ?
        ''', (import_id,))

        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Importación no encontrada"}), 404

        columns = [desc[0] for desc in cursor.description]
        import_data = dict(zip(columns, row))

        return jsonify({
            "success": True,
            "import": import_data
        })

    except Exception as e:
        print(f"[API] Error obteniendo detalle: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/import/<int:import_id>/rollback", methods=["DELETE"])
def rollback_import_endpoint(import_id):
    """
    Revierte una importación (elimina viajes y datos creados)
    NOTA: Esta operación es irreversible
    """
    if not db:
        return jsonify({"error": "Base de datos no disponible"}), 500

    try:
        conn = db._get_connection()
        cursor = conn.cursor()

        # Obtener información de la importación
        cursor.execute('SELECT * FROM imports WHERE id = ?', (import_id,))
        import_row = cursor.fetchone()

        if not import_row:
            return jsonify({"error": "Importación no encontrada"}), 404

        # Verificar si se puede revertir
        columns = [desc[0] for desc in cursor.description]
        import_data = dict(zip(columns, import_row))

        if not import_data.get('can_rollback'):
            return jsonify({"error": "Esta importación no se puede revertir"}), 400

        # TODO: Implementar lógica de rollback
        # Por ahora solo marcar como no reversible
        cursor.execute('''
            UPDATE imports
            SET can_rollback = 0
            WHERE id = ?
        ''', (import_id,))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Importación marcada para rollback (funcionalidad en desarrollo)"
        })

    except Exception as e:
        print(f"[API] Error en rollback: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/obdb/extended-signals", methods=["GET"])
def get_obdb_extended_signals():
    """
    Obtiene señales extendidas de OBDb (más allá de los 21 PIDs básicos)
    """
    if not obdb_integration:
        return jsonify({
            "success": False,
            "error": "OBDb no disponible",
            "message": "Sistema funcionando con PIDs básicos solamente"
        }), 503

    try:
        # Obtener señales extendidas
        extended_signals = obdb_integration.get_extended_signals()

        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "signals": extended_signals,
            "total_categories": len(extended_signals),
            "total_signals": sum(len(signals) for signals in extended_signals.values())
        })

    except Exception as e:
        print(f"[API] Error obteniendo señales extendidas: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/obdb/status", methods=["GET"])
def get_obdb_status():
    """
    Obtiene el estado de la integración OBDb
    """
    status = {
        "obdb_available": OBDB_AVAILABLE,
        "obdb_integrated": obdb_integration is not None,
        "parser_loaded": obdb_parser is not None,
        "total_commands": len(obdb_parser.commands) if obdb_parser else 0,
        "mode": "extended" if obdb_integration else "basic",
        "basic_pids": 21,
        "extended_pids": len(obdb_parser.commands) if obdb_parser else 0
    }

    return jsonify(status)


if __name__ == "__main__":
    print("=" * 70)
    print("SENTINEL PRO - SISTEMA DE FLOTAS v10.0")
    print("=" * 70)
    print(f"\n[CONFIG] Puerto OBD: {OBD_PORT}")
    print(f"[CONFIG] Modelo IA: {GEMINI_MODEL_NAME}")
    print("\n[OPTIMIZACIONES]")
    print("  ✓ Datos críticos cada 3s: RPM, velocidad, acelerador, carga, MAF")
    print("  ✓ Datos térmicos cada 60s: temperaturas refrigerante/admisión")
    print("  ✓ Cálculo preciso de distancia por integración")
    print("  ✓ Análisis salud automático cada 90s")
    print("\n[FEATURES PROFESIONALES]")
    print("  ✓ Scoring salud 0-100")
    print("  ✓ Detección patrones desgaste")
    print("  ✓ Predicción fallos con IA")
    print("  ✓ Averías comunes por modelo")
    print("  ✓ Tasación inteligente")
    print("\n[SISTEMA DE FLOTAS v10.0]")
    print("  ✓ Base de datos SQLite con gestión multi-vehículo")
    print("  ✓ API REST completa (vehículos, viajes, mantenimiento)")
    print("  ✓ Análisis por tipo de transmisión")
    print("  ✓ Estadísticas y analytics avanzados")
    print("  ✓ Sistema de alertas configurables")

    # Verificar tabla obd_extended
    if db:
        try:
            cursor = db.conn.cursor()
            cursor.execute('''
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='obd_extended'
            ''')

            if not cursor.fetchone():
                print("\n[DB] ⚠️  Tabla 'obd_extended' no existe")
                print("[DB] Ejecutando migración automática...")

                # Importar y ejecutar migración
                try:
                    from migrate_db import migrate_database
                    success = migrate_database("../db/sentinel.db", skip_backup=True)

                    if success:
                        print("[DB] ✓ Migración completada")
                    else:
                        print("[DB] ✗ Error en migración")
                except Exception as e:
                    print(f"[DB] ✗ Error ejecutando migración: {e}")
            else:
                print("\n[DB] ✓ Tabla 'obd_extended' existe")

        except Exception as e:
            print(f"\n[DB] Error verificando tabla: {e}")

    initialize_obd_connection(force_reconnect=True)
    print("\n✓ Servidor activo en http://localhost:5000\n")

    app.run(host='0.0.0.0', port=5000, debug=False)
