// =============================================================================
// SENTINEL PRO v9.0 - FRONTEND JAVASCRIPT COMPLETO
// Copia y pega TODO este archivo como script.js
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // === CONFIGURACIÓN ===
    const API_URL = 'http://localhost:5000';
    const POLL_INTERVAL = 3000;
    
    // Referencias DOM - Configuración Vehículo
    const vehicleBrand = document.getElementById('vehicleBrand');
    const vehicleModel = document.getElementById('vehicleModel');
    const vehicleYear = document.getElementById('vehicleYear');
    const vehicleMileage = document.getElementById('vehicleMileage');
    const vehicleTransmission = document.getElementById('vehicleTransmission');
    const vehicleType = document.getElementById('vehicleType');
    const vehicleDataInputs = [vehicleBrand, vehicleModel, vehicleYear, vehicleMileage, vehicleTransmission, vehicleType];
    
    // Referencias DOM - Datos en vivo
    const liveRpm = document.getElementById('live_rpm');
    const liveSpeed = document.getElementById('live_speed');
    const liveDistance = document.getElementById('live_distance');
    const liveThrottle = document.getElementById('live_throttle');
    const liveLoad = document.getElementById('live_load');
    const liveMaf = document.getElementById('live_maf');
    const liveCoolantTemp = document.getElementById('live_coolant_temp');
    const liveIntakeTemp = document.getElementById('live_intake_temp');
    
    // Referencias DOM - Salud del vehículo
    const healthScore = document.getElementById('health_score');
    const engineHealth = document.getElementById('engine_health');
    const thermalHealth = document.getElementById('thermal_health');
    const efficiencyHealth = document.getElementById('efficiency_health');
    const warningsContainer = document.getElementById('warnings_container');
    const predictionsContainer = document.getElementById('predictions_container');
    
    // Referencias DOM - Botones
    const analyzeTripBtn = document.getElementById('analyzeTripBtn');
    const downloadReportBtn = document.getElementById('downloadReportBtn');
    const downloadCSVBtn = document.getElementById('downloadCSVBtn');
    const uploadCSVInput = document.getElementById('uploadCSVInput');
    const uploadCSVBtn = document.getElementById('uploadCSVBtn');
    const csvFilesList = document.getElementById('csvFilesList');
    const commonFailuresBtn = document.getElementById('commonFailuresBtn');
    const commonFailuresResult = document.getElementById('common-failures-result');
    const valuationBtn = document.getElementById('valuationBtn');
    const valuationResult = document.getElementById('valuation-result');
    
    // Referencias DOM - Mantenimiento
    const maintenanceForm = document.getElementById('maintenanceForm');
    const maintenanceLog = document.getElementById('maintenanceLog');
    
    // Referencias DOM - Análisis IA
    const aiResults = document.getElementById('ai-results');
    const aiPlaceholder = document.getElementById('ai-placeholder');
    
    // Variables globales
    let maintenanceHistory = [];
    let isOBDConnected = false;
    let consecutiveFailures = 0;
    const MAX_CONSECUTIVE_FAILURES = 3;
    let uploadedCSVFiles = [];

    // Variables GPS
    let gpsWatchId = null;
    let gpsEnabled = false;
    let lastGPSPosition = null;
    let gpsDataPoints = [];
    let totalGPSDistance = 0;

    // Control de viaje
    let tripActive = false;
    let lowRpmCount = 0;
    const LOW_RPM_THRESHOLD = 5; // Número de lecturas consecutivas con RPM < 400 para finalizar viaje
    let currentTripId = null;
    let tripDataBuffer = []; // Buffer para acumular datos antes de enviar a BD
    const TRIP_DATA_BATCH_SIZE = 10; // Enviar cada 10 puntos de datos

    // Estado global del modo de trabajo
    let workMode = 'fleet'; // fleet | new | import
    let selectedFleetVehicle = null;

    // === SELECTOR DE MODO DE TRABAJO ===

    function initModeSelector() {
        const modeButtons = document.querySelectorAll('.mode-btn');
        const fleetSelector = document.getElementById('fleetVehicleSelector');
        const newMessage = document.getElementById('newVehicleMessage');
        const importSection = document.getElementById('csvImportSection');
        const configCard = document.getElementById('vehicleConfigCard');
        const saveNewVehicleSection = document.getElementById('saveNewVehicleSection');
        const csvWarning = document.getElementById('csvWarningNoVehicle');

        if (!modeButtons || modeButtons.length === 0) return; // No hay selector de modo

        modeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Actualizar botones activos
                modeButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Cambiar modo
                workMode = btn.dataset.mode;

                // Mostrar/ocultar secciones
                if (fleetSelector) fleetSelector.style.display = workMode === 'fleet' ? 'block' : 'none';
                if (newMessage) newMessage.style.display = workMode === 'new' ? 'block' : 'none';
                if (importSection) importSection.style.display = workMode === 'import' ? 'block' : 'none';

                // Mostrar/ocultar botón de guardar nuevo vehículo
                if (saveNewVehicleSection) {
                    saveNewVehicleSection.style.display = (workMode === 'new' || workMode === 'import') ? 'block' : 'none';
                }

                // Mostrar/ocultar advertencia CSV según si hay vehículo activo
                if (csvWarning && workMode === 'import') {
                    const activeVehicleId = localStorage.getItem('activeVehicleId');
                    csvWarning.style.display = activeVehicleId ? 'none' : 'block';
                }

                // Configurar formulario según modo
                if (workMode === 'fleet') {
                    loadFleetVehicles();
                    disableVehicleForm();
                    loadMaintenanceLog(); // Cargar historial del vehículo activo
                } else if (workMode === 'new') {
                    clearVehicleForm();
                    enableVehicleForm();
                    clearMaintenanceLog(); // Limpiar historial
                } else if (workMode === 'import') {
                    const activeVehicleId = localStorage.getItem('activeVehicleId');
                    if (!activeVehicleId) {
                        clearVehicleForm();
                        enableVehicleForm();
                        clearMaintenanceLog(); // Limpiar historial
                    }
                }
            });
        });

        // Cargar vehículo de flota
        const loadFleetVehicleBtn = document.getElementById('loadFleetVehicle');
        if (loadFleetVehicleBtn) {
            loadFleetVehicleBtn.addEventListener('click', async () => {
                const vehicleId = document.getElementById('fleetVehicleSelect').value;
                if (vehicleId) {
                    await loadVehicleData(vehicleId);
                }
            });
        }

        // Drag & drop para CSV
        const dropZone = document.getElementById('csvDropZone');
        const fileInput = document.getElementById('csvImportInput');

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());

            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });

            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('dragover');
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                handleCSVFiles(e.dataTransfer.files);
            });

            fileInput.addEventListener('change', (e) => {
                handleCSVFiles(e.target.files);
            });
        }

        // Botón proceder a importación
        const proceedBtn = document.getElementById('proceedToImport');
        if (proceedBtn) {
            proceedBtn.addEventListener('click', () => {
                // Validar que haya vehículo configurado
                const activeVehicleId = localStorage.getItem('activeVehicleId');
                if (!activeVehicleId) {
                    if (window.SENTINEL && window.SENTINEL.Toast) {
                        window.SENTINEL.Toast.error('Debes configurar un vehículo antes de importar datos CSV');
                    } else {
                        alert('Debes configurar un vehículo antes de importar datos CSV');
                    }
                    return;
                }
                window.location.href = 'import.html';
            });
        }

        // Botón guardar nuevo vehículo
        const saveNewVehicleBtn = document.getElementById('saveNewVehicleBtn');
        if (saveNewVehicleBtn) {
            saveNewVehicleBtn.addEventListener('click', saveNewVehicle);
        }

        // Iniciar en modo fleet por defecto
        loadFleetVehicles();
    }

    // Cargar vehículos de la flota
    async function loadFleetVehicles() {
        try {
            const response = await fetch(`${API_URL}/api/vehicles`);
            const data = await response.json();

            const vehicles = data.vehicles || data;
            const select = document.getElementById('fleetVehicleSelect');

            if (!select) return;

            select.innerHTML = '<option value="">Selecciona un vehículo...</option>';

            if (vehicles && vehicles.length > 0) {
                vehicles.forEach(vehicle => {
                    const option = document.createElement('option');
                    option.value = vehicle.id;
                    option.textContent = `${vehicle.brand} ${vehicle.model} (${vehicle.year})${vehicle.vin ? ' - ' + vehicle.vin : ''}`;
                    select.appendChild(option);
                });
            } else {
                select.innerHTML = '<option value="">No hay vehículos en la flota</option>';
            }
        } catch (error) {
            console.error('Error cargando vehículos:', error);
            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.error('Error al cargar la flota');
            }
        }
    }

    // Cargar datos del vehículo seleccionado
    async function loadVehicleData(vehicleId) {
        try {
            const response = await fetch(`${API_URL}/api/vehicles/${vehicleId}`);
            const data = await response.json();
            const vehicle = data.vehicle || data;

            // Rellenar formulario
            if (vehicleBrand) vehicleBrand.value = vehicle.brand || '';
            if (vehicleModel) vehicleModel.value = vehicle.model || '';
            if (vehicleYear) vehicleYear.value = vehicle.year || '';
            if (vehicleMileage) vehicleMileage.value = vehicle.mileage || '';
            if (vehicleTransmission) vehicleTransmission.value = vehicle.transmission || 'manual';
            if (vehicleType) vehicleType.value = vehicle.fuel_type || 'gasolina';

            selectedFleetVehicle = vehicle;

            // Guardar en localStorage
            localStorage.setItem('activeVehicleId', vehicleId);
            saveVehicleInfo();

            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.success('Vehículo cargado correctamente');
            }
        } catch (error) {
            console.error('Error cargando vehículo:', error);
            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.error('Error al cargar el vehículo');
            }
        }
    }

    // Guardar nuevo vehículo en la base de datos
    async function saveNewVehicle() {
        // Validar campos requeridos
        if (!vehicleBrand || !vehicleBrand.value.trim()) {
            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.error('La marca del vehículo es obligatoria');
            } else {
                alert('La marca del vehículo es obligatoria');
            }
            vehicleBrand.focus();
            return;
        }

        if (!vehicleModel || !vehicleModel.value.trim()) {
            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.error('El modelo del vehículo es obligatorio');
            } else {
                alert('El modelo del vehículo es obligatorio');
            }
            vehicleModel.focus();
            return;
        }

        if (!vehicleYear || !vehicleYear.value) {
            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.error('El año del vehículo es obligatorio');
            } else {
                alert('El año del vehículo es obligatorio');
            }
            vehicleYear.focus();
            return;
        }

        // Preparar datos del vehículo
        const vehicleData = {
            brand: vehicleBrand.value.trim(),
            model: vehicleModel.value.trim(),
            year: parseInt(vehicleYear.value),
            mileage: vehicleMileage && vehicleMileage.value ? parseInt(vehicleMileage.value) : 0,
            transmission: vehicleTransmission ? vehicleTransmission.value : 'manual',
            fuel_type: vehicleType ? vehicleType.value : 'gasolina'
        };

        // Deshabilitar botón mientras se guarda
        const saveBtn = document.getElementById('saveNewVehicleBtn');
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

        try {
            const response = await fetch(`${API_URL}/api/vehicles`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(vehicleData)
            });

            if (!response.ok) {
                throw new Error('Error al guardar el vehículo');
            }

            const result = await response.json();
            const newVehicleId = result.vehicle_id || result.id;

            // Guardar como vehículo activo
            localStorage.setItem('activeVehicleId', newVehicleId);
            saveVehicleInfo();

            // Cargar historial (vacío para nuevo vehículo)
            loadMaintenanceLog();

            // Ocultar advertencia CSV si estamos en modo import
            const csvWarning = document.getElementById('csvWarningNoVehicle');
            if (csvWarning && workMode === 'import') {
                csvWarning.style.display = 'none';
            }

            // Mostrar feedback de éxito
            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.success('¡Vehículo guardado exitosamente!');
            } else {
                alert('¡Vehículo guardado exitosamente!');
            }

            // Cambiar botón a estado "guardado"
            saveBtn.innerHTML = '<i class="fas fa-check-circle"></i> Vehículo Guardado';
            saveBtn.classList.remove('btn-success');
            saveBtn.classList.add('btn-secondary');

            // Después de 3 segundos, permitir guardar de nuevo
            setTimeout(() => {
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalText;
                saveBtn.classList.remove('btn-secondary');
                saveBtn.classList.add('btn-success');
            }, 3000);

        } catch (error) {
            console.error('Error guardando vehículo:', error);
            if (window.SENTINEL && window.SENTINEL.Toast) {
                window.SENTINEL.Toast.error('Error al guardar el vehículo. Intenta de nuevo.');
            } else {
                alert('Error al guardar el vehículo. Intenta de nuevo.');
            }
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }

    // Deshabilitar formulario
    function disableVehicleForm() {
        const fields = [vehicleBrand, vehicleModel, vehicleYear, vehicleMileage, vehicleTransmission, vehicleType];
        fields.forEach(field => {
            if (field) field.disabled = true;
        });
    }

    // Habilitar formulario
    function enableVehicleForm() {
        const fields = [vehicleBrand, vehicleModel, vehicleYear, vehicleMileage, vehicleTransmission, vehicleType];
        fields.forEach(field => {
            if (field) field.disabled = false;
        });
    }

    // Limpiar formulario
    function clearVehicleForm() {
        const fields = [vehicleBrand, vehicleModel, vehicleYear, vehicleMileage, vehicleTransmission, vehicleType];
        fields.forEach(field => {
            if (field) field.value = '';
        });
        selectedFleetVehicle = null;
    }

    // Manejar archivos CSV
    function handleCSVFiles(files) {
        if (files.length > 0) {
            const fileList = Array.from(files).map(f => f.name).join(', ');
            const dropZone = document.getElementById('csvDropZone');
            if (dropZone) {
                dropZone.innerHTML = `
                    <i class="fas fa-file-csv" style="color: #10b981;"></i>
                    <p style="color: #10b981;">${files.length} archivo(s) seleccionado(s)</p>
                    <p class="small-text">${fileList}</p>
                `;
            }
            const proceedBtn = document.getElementById('proceedToImport');
            if (proceedBtn) proceedBtn.style.display = 'block';

            // Guardar archivos en sessionStorage para usar en import.html
            const fileNames = Array.from(files).map(f => f.name);
            sessionStorage.setItem('pendingCSVImport', JSON.stringify(fileNames));
        }
    }

    // === FUNCIONES DE ALMACENAMIENTO ===
    
    function saveVehicleInfo() {
        const vehicleInfo = {
            brand: vehicleBrand.value,
            model: vehicleModel.value,
            year: vehicleYear.value,
            mileage: vehicleMileage.value,
            transmission: vehicleTransmission.value,
            type: vehicleType.value
        };
        localStorage.setItem('vehicleInfo', JSON.stringify(vehicleInfo));
    }
    
    function loadVehicleInfo() {
        const savedInfo = localStorage.getItem('vehicleInfo');
        if (savedInfo) {
            const vehicleInfo = JSON.parse(savedInfo);
            vehicleBrand.value = vehicleInfo.brand || '';
            vehicleModel.value = vehicleInfo.model || '';
            vehicleYear.value = vehicleInfo.year || '';
            vehicleMileage.value = vehicleInfo.mileage || '';
            vehicleTransmission.value = vehicleInfo.transmission || 'manual';
            vehicleType.value = vehicleInfo.type || 'gasolina';
        }
    }
    
    function getVehicleInfo() {
        return {
            brand: vehicleBrand.value,
            model: vehicleModel.value,
            year: vehicleYear.value,
            type: vehicleType.value,
            transmission: vehicleTransmission.value,
            mileage: vehicleMileage.value
        };
    }
    
    vehicleDataInputs.forEach(input => input.addEventListener('change', saveVehicleInfo));

    // === FUNCIONES GPS ===

    /**
     * Iniciar seguimiento GPS
     */
    function startGPSTracking() {
        if (!navigator.geolocation) {
            console.warn('[GPS] Geolocalización no soportada en este navegador');
            return false;
        }

        if (gpsWatchId !== null) {
            console.log('[GPS] Ya está activo');
            return true;
        }

        console.log('[GPS] Iniciando seguimiento...');

        gpsWatchId = navigator.geolocation.watchPosition(
            handleGPSPosition,
            handleGPSError,
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );

        gpsEnabled = true;
        totalGPSDistance = 0;
        gpsDataPoints = [];
        console.log('[GPS] ✓ Seguimiento iniciado');
        return true;
    }

    /**
     * Detener seguimiento GPS
     */
    function stopGPSTracking() {
        if (gpsWatchId !== null) {
            navigator.geolocation.clearWatch(gpsWatchId);
            gpsWatchId = null;
            gpsEnabled = false;
            console.log('[GPS] ✓ Seguimiento detenido');
            console.log(`[GPS] Distancia total GPS: ${totalGPSDistance.toFixed(3)} km`);
        }
    }

    /**
     * Manejar nueva posición GPS
     */
    function handleGPSPosition(position) {
        const newPosition = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            speed: position.coords.speed, // m/s
            timestamp: position.timestamp
        };

        // Calcular distancia si hay posición anterior
        if (lastGPSPosition) {
            const distance = SENTINEL.GPS.calculateDistance(
                lastGPSPosition.latitude,
                lastGPSPosition.longitude,
                newPosition.latitude,
                newPosition.longitude
            );

            // Solo sumar si la distancia es razonable (menos de 100m entre lecturas)
            if (distance < 0.1) {
                totalGPSDistance += distance;
            }
        }

        lastGPSPosition = newPosition;
        gpsDataPoints.push(newPosition);

        // Log cada 10 posiciones
        if (gpsDataPoints.length % 10 === 0) {
            console.log(`[GPS] ${gpsDataPoints.length} puntos - ${totalGPSDistance.toFixed(3)} km - Precisión: ${newPosition.accuracy.toFixed(0)}m`);
        }
    }

    /**
     * Manejar error GPS
     */
    function handleGPSError(error) {
        let errorMsg = '';
        switch(error.code) {
            case error.PERMISSION_DENIED:
                errorMsg = 'Permiso GPS denegado';
                break;
            case error.POSITION_UNAVAILABLE:
                errorMsg = 'Posición no disponible';
                break;
            case error.TIMEOUT:
                errorMsg = 'Timeout GPS';
                break;
            default:
                errorMsg = 'Error desconocido';
        }
        console.error(`[GPS] ✗ ${errorMsg}`);
    }

    /**
     * Obtener velocidad preferida (GPS si disponible, sino OBD)
     */
    function getPreferredSpeed(obdSpeed) {
        if (lastGPSPosition && lastGPSPosition.speed !== null && lastGPSPosition.speed > 0) {
            // Convertir de m/s a km/h
            const gpsSpeedKmh = lastGPSPosition.speed * 3.6;

            // Usar GPS si es razonable (< 250 km/h)
            if (gpsSpeedKmh < 250) {
                return gpsSpeedKmh;
            }
        }

        // Fallback a OBD
        return obdSpeed;
    }

    /**
     * Obtener distancia preferida (GPS si disponible, sino OBD)
     */
    function getPreferredDistance(obdDistance) {
        if (gpsEnabled && totalGPSDistance > 0) {
            // Preferir GPS si tiene datos
            return totalGPSDistance;
        }
        return obdDistance;
    }

    // === FUNCIONES DE ACTUALIZACIÓN UI ===
    
    function updateLiveData(data) {
        if (data.RPM === 'Offline' || data.RPM === null) {
            liveRpm.textContent = '---';
            liveRpm.classList.add('offline');
        } else {
            liveRpm.textContent = Math.round(data.RPM);
            liveRpm.classList.remove('offline');
        }
        
        if (data.SPEED === 'Offline' || data.SPEED === null) {
            liveSpeed.textContent = '---';
            liveSpeed.classList.add('offline');
        } else {
            liveSpeed.textContent = Math.round(data.SPEED);
            liveSpeed.classList.remove('offline');
        }
        
        if (data.total_distance === 'Offline' || data.total_distance === null) {
            liveDistance.textContent = '---';
            liveDistance.classList.add('offline');
        } else {
            liveDistance.textContent = data.total_distance.toFixed(3);
            liveDistance.classList.remove('offline');
        }
        
        if (data.THROTTLE_POS !== null && data.THROTTLE_POS !== undefined) {
            liveThrottle.textContent = Math.round(data.THROTTLE_POS);
            liveThrottle.classList.remove('offline');
        } else {
            liveThrottle.textContent = '---';
            liveThrottle.classList.add('offline');
        }
        
        if (data.ENGINE_LOAD !== null && data.ENGINE_LOAD !== undefined) {
            liveLoad.textContent = Math.round(data.ENGINE_LOAD);
            liveLoad.classList.remove('offline');
        } else {
            liveLoad.textContent = '---';
            liveLoad.classList.add('offline');
        }
        
        if (data.MAF !== null && data.MAF !== undefined) {
            liveMaf.textContent = data.MAF.toFixed(1);
            liveMaf.classList.remove('offline');
        } else {
            liveMaf.textContent = '---';
            liveMaf.classList.add('offline');
        }
        
        if (data.COOLANT_TEMP !== null && data.COOLANT_TEMP !== undefined) {
            liveCoolantTemp.textContent = Math.round(data.COOLANT_TEMP);
            liveCoolantTemp.classList.remove('offline');
        } else if (data.COOLANT_TEMP !== 'Offline') {
            // Mantener último valor
        } else {
            liveCoolantTemp.textContent = '---';
            liveCoolantTemp.classList.add('offline');
        }
        
        if (data.INTAKE_TEMP !== null && data.INTAKE_TEMP !== undefined) {
            liveIntakeTemp.textContent = Math.round(data.INTAKE_TEMP);
            liveIntakeTemp.classList.remove('offline');
        } else if (data.INTAKE_TEMP !== 'Offline') {
            // Mantener último valor
        } else {
            liveIntakeTemp.textContent = '---';
            liveIntakeTemp.classList.add('offline');
        }
    }
    
    function updateHealthDisplay(health) {
        if (!health) return;
        
        healthScore.textContent = health.overall_score || 100;
        healthScore.className = 'health-score-value ' + getHealthClass(health.overall_score);
        
        engineHealth.textContent = health.engine_health || 100;
        thermalHealth.textContent = health.thermal_health || 100;
        efficiencyHealth.textContent = health.efficiency_health || 100;
        
        if (health.warnings && health.warnings.length > 0) {
            warningsContainer.innerHTML = '<h4><i class="fas fa-exclamation-triangle"></i> Advertencias Activas</h4>';
            const ul = document.createElement('ul');
            ul.className = 'warnings-list';
            health.warnings.forEach(warning => {
                const li = document.createElement('li');
                li.textContent = warning;
                ul.appendChild(li);
            });
            warningsContainer.appendChild(ul);
            warningsContainer.style.display = 'block';
        } else {
            warningsContainer.style.display = 'none';
        }
        
        if (health.predictions && health.predictions.length > 0) {
            predictionsContainer.innerHTML = '<h4><i class="fas fa-chart-line"></i> Predicciones de Mantenimiento</h4>';
            const ul = document.createElement('ul');
            ul.className = 'predictions-list';
            health.predictions.forEach(prediction => {
                const li = document.createElement('li');
                li.textContent = prediction;
                ul.appendChild(li);
            });
            predictionsContainer.appendChild(ul);
            predictionsContainer.style.display = 'block';
        } else {
            predictionsContainer.style.display = 'none';
        }
    }
    
    function getHealthClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 60) return 'good';
        if (score >= 40) return 'warning';
        return 'critical';
    }
    
    function updateAnalyzeButton() {
        if (isOBDConnected) {
            analyzeTripBtn.innerHTML = '<i class="fas fa-flag-checkered"></i> Finalizar y Analizar Viaje';
            analyzeTripBtn.title = 'Análisis con datos OBD reales';
            analyzeTripBtn.classList.remove('mode-fallback');
            analyzeTripBtn.classList.add('mode-obd');
        } else {
            analyzeTripBtn.innerHTML = '<i class="fas fa-brain"></i> Análisis Predictivo con IA';
            analyzeTripBtn.title = 'Análisis basado en datos simulados';
            analyzeTripBtn.classList.remove('mode-obd');
            analyzeTripBtn.classList.add('mode-fallback');
        }
    }
    
    function showConnectionNotification(message, type = 'info') {
        const existingNotification = document.querySelector('.connection-notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        const notification = document.createElement('div');
        notification.className = `connection-notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
    
    // === FUNCIONES DE GESTIÓN DE VIAJES CON BD ===

    /**
     * Iniciar viaje en la base de datos
     */
    async function startTripInDB() {
        const vehicleId = SENTINEL.ActiveVehicle.get();

        if (!vehicleId) {
            console.warn('[TRIP] No hay vehículo activo. Crear vehículo en fleet.html primero.');
            return null;
        }

        try {
            const response = await fetch(`${API_URL}/api/trips/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vehicle_id: vehicleId })
            });

            if (!response.ok) {
                throw new Error('Error iniciando viaje en BD');
            }

            const result = await response.json();
            currentTripId = result.trip_id;
            tripDataBuffer = [];

            console.log(`[TRIP-DB] ✓ Viaje iniciado en BD (trip_id: ${currentTripId})`);
            return currentTripId;

        } catch (error) {
            console.error('[TRIP-DB] Error iniciando viaje:', error);
            return null;
        }
    }

    /**
     * Guardar datos OBD + GPS en la BD
     */
    async function saveTripDataToDB(dataPoint) {
        if (!currentTripId) return;

        tripDataBuffer.push(dataPoint);

        // Enviar cuando el buffer alcanza el tamaño de batch
        if (tripDataBuffer.length >= TRIP_DATA_BATCH_SIZE) {
            await flushTripDataBuffer();
        }
    }

    /**
     * Enviar buffer de datos a la BD
     */
    async function flushTripDataBuffer() {
        if (!currentTripId || tripDataBuffer.length === 0) return;

        try {
            const response = await fetch(`${API_URL}/api/trips/${currentTripId}/data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data_points: tripDataBuffer })
            });

            if (response.ok) {
                const result = await response.json();
                console.log(`[TRIP-DB] ✓ ${result.points_saved} puntos guardados en BD`);
                tripDataBuffer = [];
            }

        } catch (error) {
            console.error('[TRIP-DB] Error guardando datos:', error);
        }
    }

    /**
     * Finalizar viaje en la BD
     */
    async function endTripInDB() {
        if (!currentTripId) return;

        // Enviar datos pendientes
        await flushTripDataBuffer();

        try {
            const stats = {
                distance_km: totalGPSDistance || trip_data?.distance_km || 0,
                avg_speed: 0, // Calcular si es necesario
                max_speed: 0  // Calcular si es necesario
            };

            const response = await fetch(`${API_URL}/api/trips/${currentTripId}/stop`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stats })
            });

            if (response.ok) {
                console.log(`[TRIP-DB] ✓ Viaje ${currentTripId} finalizado en BD`);
            }

        } catch (error) {
            console.error('[TRIP-DB] Error finalizando viaje:', error);
        } finally {
            currentTripId = null;
            tripDataBuffer = [];
        }
    }

    // === FUNCIONES DE RED ===

    async function fetchLiveData() {
        try {
            const response = await fetch(`${API_URL}/get_live_data`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.offline === true) {
                if (isOBDConnected) {
                    console.log('[OBD] Conexión perdida');
                    isOBDConnected = false;
                }
                consecutiveFailures++;
                updateLiveData({ 
                    RPM: 'Offline', 
                    SPEED: 'Offline', 
                    THROTTLE_POS: 'Offline',
                    ENGINE_LOAD: 'Offline',
                    MAF: 'Offline',
                    COOLANT_TEMP: 'Offline',
                    INTAKE_TEMP: 'Offline',
                    total_distance: 'Offline' 
                });
            } else {
                if (!isOBDConnected) {
                    console.log('[OBD] ✓ Conectado');
                    showConnectionNotification('OBD conectado - Optimizado: críticos 3s, térmicos 60s', 'success');
                }
                isOBDConnected = true;
                consecutiveFailures = 0;
                updateLiveData(data);

                // GESTIÓN AUTOMÁTICA DE GPS Y BD
                const rpm = data.RPM;

                if (rpm && rpm > 400) {
                    // Viaje activo - iniciar GPS y BD si no está activo
                    lowRpmCount = 0;

                    if (!tripActive) {
                        tripActive = true;
                        console.log('[AUTO-GPS] ✓ Viaje detectado (RPM > 400)');

                        // Iniciar viaje en BD
                        await startTripInDB();

                        // Iniciar GPS
                        if (!gpsEnabled) {
                            const gpsStarted = startGPSTracking();
                            if (gpsStarted) {
                                showConnectionNotification('GPS activado - Viaje iniciado en BD', 'success');
                            }
                        }
                    }

                    // Guardar datos del viaje actual
                    if (currentTripId) {
                        const dataPoint = {
                            timestamp: new Date().toISOString(),
                            rpm: data.RPM,
                            speed: data.SPEED,
                            coolant_temp: data.COOLANT_TEMP,
                            intake_temp: data.INTAKE_TEMP,
                            maf: data.MAF,
                            engine_load: data.ENGINE_LOAD,
                            throttle_pos: data.THROTTLE_POS,
                            fuel_pressure: data.FUEL_PRESSURE || null,
                            latitude: lastGPSPosition?.latitude || null,
                            longitude: lastGPSPosition?.longitude || null
                        };

                        await saveTripDataToDB(dataPoint);
                    }

                } else if (tripActive && (!rpm || rpm < 400)) {
                    // Contador para evitar paradas momentáneas
                    lowRpmCount++;

                    if (lowRpmCount >= LOW_RPM_THRESHOLD) {
                        // Viaje finalizado
                        tripActive = false;
                        lowRpmCount = 0;
                        console.log('[AUTO-GPS] ✓ Viaje finalizado (RPM < 400)');

                        // Finalizar viaje en BD
                        await endTripInDB();

                        // Detener GPS
                        if (gpsEnabled) {
                            stopGPSTracking();
                            showConnectionNotification('GPS desactivado - Viaje finalizado', 'info');
                        }
                    }
                }
            }

            updateAnalyzeButton();
            
        } catch (error) {
            consecutiveFailures++;
            
            if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES && isOBDConnected) {
                console.log('[OBD] Múltiples fallos detectados');
                showConnectionNotification('Conexión OBD perdida. Modo fallback activado.', 'warning');
            }
            
            isOBDConnected = false;
            updateLiveData({ 
                RPM: 'Offline', 
                SPEED: 'Offline',
                THROTTLE_POS: 'Offline',
                ENGINE_LOAD: 'Offline',
                MAF: 'Offline',
                COOLANT_TEMP: 'Offline',
                INTAKE_TEMP: 'Offline',
                total_distance: 'Offline' 
            });
            updateAnalyzeButton();
        }
    }
    
    async function fetchVehicleHealth() {
        try {
            const response = await fetch(`${API_URL}/get_vehicle_health`);
            if (response.ok) {
                const health = await response.json();
                updateHealthDisplay(health);
            }
        } catch (error) {
            console.error('[HEALTH] Error obteniendo salud:', error);
        }
    }
    
    async function analyzeTrip() {
        const loadingMessage = isOBDConnected 
            ? 'Analizando viaje con datos OBD reales...' 
            : 'Generando análisis predictivo con IA...';
        
        showLoadingState(loadingMessage);
        
        try {
            const response = await fetch(`${API_URL}/predictive_analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicleInfo: getVehicleInfo(),
                    maintenanceHistory
                })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Error desconocido');
            }
            
            displayPredictiveAnalysis(result);
            
        } catch (error) {
            displayAiError(`Error: ${error.message}`);
        }
    }
    
    function showLoadingState(message) {
        aiPlaceholder.style.display = 'block';
        aiPlaceholder.innerHTML = `<p><i class="fas fa-cogs fa-spin"></i> ${message}</p>`;
        aiResults.style.display = 'none';
    }
    
    function displayPredictiveAnalysis(analysis) {
        aiPlaceholder.style.display = 'none';
        
        let html = `
            <div class="card predictive-analysis">
                <h2>
                    <i class="fas fa-brain"></i>
                    Análisis Predictivo de Mantenimiento
                </h2>
                
                <div class="predictive-score-section">
                    <div class="score-circle ${getHealthClass(analysis.predictive_score)}">
                        <span class="score-number">${analysis.predictive_score}</span>
                        <span class="score-label">/100</span>
                    </div>
                    <div class="score-info">
                        <h3>Nivel de Riesgo: <span class="risk-badge risk-${analysis.risk_level.toLowerCase()}">${analysis.risk_level}</span></h3>
                        <p>Puntuación predictiva basada en datos del viaje actual y patrones de desgaste</p>
                    </div>
                </div>
        `;
        
        if (analysis.trip_stats) {
            const stats = analysis.trip_stats;
            html += `
                <div class="trip-stats-grid">
                    <div class="stat-card">
                        <i class="fas fa-clock"></i>
                        <span class="stat-value">${stats.duration_min}</span>
                        <span class="stat-label">minutos</span>
                    </div>
                    <div class="stat-card">
                        <i class="fas fa-route"></i>
                        <span class="stat-value">${stats.distance}</span>
                        <span class="stat-label">km</span>
                    </div>
                    <div class="stat-card">
                        <i class="fas fa-tachometer-alt"></i>
                        <span class="stat-value">${stats.rpm_avg}</span>
                        <span class="stat-label">RPM promedio</span>
                    </div>
                    <div class="stat-card">
                        <i class="fas fa-temperature-high"></i>
                        <span class="stat-value">${stats.temp_max}°C</span>
                        <span class="stat-label">Temp máx</span>
                    </div>
                </div>
            `;
        }
        
        if (analysis.predictions && analysis.predictions.length > 0) {
            html += `
                <div class="predictions-section">
                    <h3><i class="fas fa-exclamation-circle"></i> Predicciones de Fallos</h3>
                    <div class="predictions-grid">
            `;
            
            analysis.predictions.forEach(pred => {
                html += `
                    <div class="prediction-card">
                        <h4>${pred.component}</h4>
                        <div class="prediction-details">
                            <p><strong>Probabilidad:</strong> ${pred.failure_probability}</p>
                            <p><strong>Timeframe:</strong> ${pred.estimated_timeframe}</p>
                            <p><strong>Síntomas:</strong> ${pred.symptoms}</p>
                            <p class="prediction-action"><i class="fas fa-wrench"></i> ${pred.action}</p>
                        </div>
                    </div>
                `;
            });
            
            html += `</div></div>`;
        }
        
        if (analysis.priority_maintenance && analysis.priority_maintenance.length > 0) {
            html += `
                <div class="maintenance-section">
                    <h3><i class="fas fa-tools"></i> Mantenimiento Prioritario</h3>
                    <div class="maintenance-list">
            `;
            
            analysis.priority_maintenance.forEach(maint => {
                const urgencyClass = maint.urgency === 'Alta' ? 'urgent' : 'normal';
                html += `
                    <div class="maintenance-item ${urgencyClass}">
                        <div class="maint-header">
                            <h4>${maint.task}</h4>
                            <span class="urgency-badge urgency-${urgencyClass}">${maint.urgency}</span>
                        </div>
                        <p><strong>Timeframe:</strong> ${maint.timeframe}</p>
                        <p><strong>Razón:</strong> ${maint.reason}</p>
                    </div>
                `;
            });
            
            html += `</div></div>`;
        }
        
        if (analysis.component_health) {
            html += `
                <div class="component-health-section">
                    <h3><i class="fas fa-heartbeat"></i> Salud de Componentes</h3>
                    <div class="components-grid">
            `;
            
            for (const [component, health] of Object.entries(analysis.component_health)) {
                const healthValue = parseInt(health);
                const healthClass = getHealthClass(healthValue);
                html += `
                    <div class="component-item">
                        <span class="component-name">${component}</span>
                        <div class="health-bar">
                            <div class="health-fill ${healthClass}" style="width: ${health}"></div>
                        </div>
                        <span class="health-value">${health}</span>
                    </div>
                `;
            }
            
            html += `</div></div>`;
        }
        
        if (analysis.cost_estimate) {
            html += `
                <div class="cost-estimate-section">
                    <h3><i class="fas fa-euro-sign"></i> Estimación de Costes</h3>
                    <div class="cost-comparison">
                        <div class="cost-card preventive">
                            <i class="fas fa-shield-alt"></i>
                            <h4>Mantenimiento Preventivo Ahora</h4>
                            <p class="cost-value">${analysis.cost_estimate.preventive_now}</p>
                        </div>
                        <div class="cost-arrow">
                            <i class="fas fa-arrow-right"></i>
                        </div>
                        <div class="cost-card delayed">
                            <i class="fas fa-exclamation-triangle"></i>
                            <h4>Si se Retrasa</h4>
                            <p class="cost-value">${analysis.cost_estimate.if_delayed}</p>
                        </div>
                    </div>
                </div>
            `;
        }
        
        html += `</div>`;
        aiResults.innerHTML = html;
        aiResults.style.display = 'block';
    }
    
    function displayAiError(errorMessage) {
        aiPlaceholder.style.display = 'block';
        aiPlaceholder.innerHTML = `<p style="color: red;"><i class="fas fa-exclamation-triangle"></i> ${errorMessage}</p>`;
        aiResults.style.display = 'none';
    }
    
    // === FUNCIONES AVERÍAS COMUNES ===
    
    async function getCommonFailures() {
        const vehicleInfo = getVehicleInfo();
        if (!vehicleInfo.brand || !vehicleInfo.model || !vehicleInfo.year) {
            alert('Por favor, introduce la Marca, Modelo y Año del vehículo.');
            return;
        }
        
        commonFailuresResult.innerHTML = `<p><i class="fas fa-spinner fa-spin"></i> Buscando averías comunes...</p>`;
        
        try {
            const response = await fetch(`${API_URL}/get_common_failures`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vehicleInfo })
            });
            
            const result = await response.json();
            
            if (!response.ok) throw new Error(result.error || 'Error desconocido.');
            
            createAccordionFromJSON(commonFailuresResult, result);
        } catch(error) {
            commonFailuresResult.innerHTML = `<p style="color:red;">Error: ${error.message}</p>`;
        }
    }
    
    function createAccordionFromJSON(container, data) {
        container.innerHTML = '';
        
        if (data.failures && Array.isArray(data.failures)) {
            data.failures.forEach(failure => {
                const item = document.createElement('div');
                item.className = 'accordion-item';
                
                const button = document.createElement('button');
                button.className = 'accordion-button';
                if (failure.severity) {
                    button.classList.add(`severity-${failure.severity.toLowerCase()}`);
                }
                button.textContent = failure.title || "Avería sin título";
                
                const panel = document.createElement('div');
                panel.className = 'accordion-panel';
                panel.innerHTML = `
                    <p><strong>Síntoma:</strong> ${failure.symptom || "N/D"}</p>
                    <p><strong>Causa:</strong> ${failure.cause || "N/D"}</p>
                    <p><strong>Solución:</strong> ${failure.solution || "N/D"}</p>
                `;
                
                item.appendChild(button);
                item.appendChild(panel);
                container.appendChild(item);
                
                button.addEventListener('click', () => {
                    button.classList.toggle('active');
                    if (panel.style.maxHeight) {
                        panel.style.maxHeight = null;
                        panel.style.padding = "0 20px";
                    } else {
                        panel.style.maxHeight = panel.scrollHeight + "px";
                        panel.style.padding = "15px 20px";
                    }
                });
            });
        }
        
        if (data.recommendation) {
            const recommendationBox = document.createElement('div');
            recommendationBox.className = 'recommendation-box';
            recommendationBox.innerHTML = `
                <h4><i class="fas fa-user-md"></i> Recomendación del Jefe de Taller</h4>
                <p>${data.recommendation}</p>
            `;
            container.appendChild(recommendationBox);
        }
    }
    
    // === FUNCIONES DE TASACIÓN ===
    
    async function getValuation() {
        const vehicleInfo = getVehicleInfo();
        if (!vehicleInfo.brand || !vehicleInfo.model || !vehicleInfo.year || !vehicleInfo.mileage) {
            alert('Por favor, introduce Marca, Modelo, Año y Kilómetros.');
            return;
        }
        
        valuationResult.innerHTML = `<p><i class="fas fa-spinner fa-spin"></i> Realizando tasación...</p>`;
        
        try {
            const response = await fetch(`${API_URL}/get_vehicle_valuation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vehicleInfo, maintenanceHistory })
            });
            
            const result = await response.json();
            
            if (!response.ok || result.error) throw new Error(result.error || 'Respuesta no válida.');
            
            valuationResult.innerHTML = `
                <div class="valuation-prices">
                    <div><span>Precio Mín. Mercado</span><strong>${result.min_price || 'N/D'} €</strong></div>
                    <div><span>Precio Máx. Mercado</span><strong>${result.max_price || 'N/D'} €</strong></div>
                </div>
                <div class="valuation-realistic">
                    <span>Precio Realista Ajustado</span>
                    <strong>${result.realistic_price || 'N/D'} €</strong>
                </div>
                <div class="valuation-justification">
                    <h4><i class="fas fa-info-circle"></i> Justificación del Tasador</h4>
                    <p>${result.justification || 'No se pudo generar justificación.'}</p>
                </div>
            `;
        } catch(error) {
            valuationResult.innerHTML = `<p style="color:red;">Error al tasar: ${error.message}</p>`;
        }
    }
    
    // === FUNCIONES CSV ===
    
    async function loadUploadedCSVs() {
        try {
            const response = await fetch(`${API_URL}/list_uploaded_csvs`);
            const result = await response.json();
            
            if (!response.ok) throw new Error(result.error || 'Error cargando archivos');
            
            uploadedCSVFiles = result.files || [];
            renderCSVFilesList();
            
        } catch (error) {
            console.error('[CSV] Error:', error);
        }
    }
    
    function renderCSVFilesList() {
        if (uploadedCSVFiles.length === 0) {
            csvFilesList.innerHTML = '<p class="no-data">No hay archivos CSV. Sube uno para comenzar.</p>';
            return;
        }
        
        csvFilesList.innerHTML = uploadedCSVFiles.map(file => `
            <div class="csv-file-item">
                <div class="csv-file-info">
                    <strong>${file.filename}</strong>
                    <span>${file.size_kb} KB - ${file.modified}</span>
                </div>
            </div>
        `).join('');
    }
    
    uploadCSVBtn.addEventListener('click', () => {
        uploadCSVInput.click();
    });
    
    uploadCSVInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        if (!file.name.endsWith('.csv')) {
            alert('Por favor, selecciona un archivo CSV válido.');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        uploadCSVBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Subiendo...';
        uploadCSVBtn.disabled = true;
        
        try {
            const response = await fetch(`${API_URL}/upload_csv`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!response.ok) throw new Error(result.error || 'Error al subir');
            
            showConnectionNotification(`CSV subido: ${result.filename}`, 'success');
            loadUploadedCSVs();
            uploadCSVInput.value = '';
            
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            uploadCSVBtn.innerHTML = '<i class="fas fa-file-upload"></i> Subir CSV';
            uploadCSVBtn.disabled = false;
        }
    });
    
    downloadCSVBtn.addEventListener('click', async () => {
        try {
            const response = await fetch(`${API_URL}/download_current_csv`);
            
            if (!response.ok) throw new Error('No hay datos CSV');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `sentinel_data_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            
            showConnectionNotification('CSV descargado correctamente', 'success');
            
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });
    
    // === FUNCIONES DE MANTENIMIENTO ===
    
    function renderMaintenanceLog() {
        if (maintenanceHistory.length === 0) {
            maintenanceLog.innerHTML = '<li class="no-data">No hay registros.</li>';
        } else {
            maintenanceLog.innerHTML = maintenanceHistory
                .slice()
                .reverse()
                .map((item, index) => `
                    <li>
                        <strong>${item.type}</strong> - ${item.date}
                        <i class="fas fa-trash-alt delete-btn" data-index="${maintenanceHistory.length - 1 - index}"></i>
                    </li>
                `).join('');
        }
    }
    
    function saveMaintenanceLog() {
        const activeVehicleId = localStorage.getItem('activeVehicleId');
        if (activeVehicleId) {
            localStorage.setItem(`maintenanceHistory_${activeVehicleId}`, JSON.stringify(maintenanceHistory));
        }
    }

    function loadMaintenanceLog() {
        const activeVehicleId = localStorage.getItem('activeVehicleId');
        if (activeVehicleId) {
            const stored = localStorage.getItem(`maintenanceHistory_${activeVehicleId}`);
            if (stored) {
                maintenanceHistory = JSON.parse(stored);
            } else {
                maintenanceHistory = [];
            }
            renderMaintenanceLog();
        } else {
            clearMaintenanceLog();
        }
    }

    function clearMaintenanceLog() {
        maintenanceHistory = [];
        if (maintenanceLog) {
            maintenanceLog.innerHTML = '<li class="no-data"><i class="fas fa-info-circle"></i> No hay vehículo activo. Selecciona o crea un vehículo.</li>';
        }
    }
    
    // Toggle formulario de mantenimiento
    const toggleMaintenanceFormBtn = document.getElementById('toggleMaintenanceFormBtn');
    const maintenanceFormContainer = document.getElementById('maintenanceFormContainer');
    const cancelMaintenanceBtn = document.getElementById('cancelMaintenanceBtn');

    if (toggleMaintenanceFormBtn && maintenanceFormContainer) {
        toggleMaintenanceFormBtn.addEventListener('click', () => {
            const isHidden = maintenanceFormContainer.style.display === 'none';
            maintenanceFormContainer.style.display = isHidden ? 'block' : 'none';

            if (isHidden) {
                toggleMaintenanceFormBtn.innerHTML = '<i class="fas fa-minus"></i> Cerrar';
                toggleMaintenanceFormBtn.classList.remove('btn-primary');
                toggleMaintenanceFormBtn.classList.add('btn-secondary');
            } else {
                toggleMaintenanceFormBtn.innerHTML = '<i class="fas fa-plus"></i> Agregar';
                toggleMaintenanceFormBtn.classList.remove('btn-secondary');
                toggleMaintenanceFormBtn.classList.add('btn-primary');
            }
        });
    }

    if (cancelMaintenanceBtn && maintenanceFormContainer && toggleMaintenanceFormBtn) {
        cancelMaintenanceBtn.addEventListener('click', () => {
            maintenanceFormContainer.style.display = 'none';
            maintenanceForm.reset();
            toggleMaintenanceFormBtn.innerHTML = '<i class="fas fa-plus"></i> Agregar';
            toggleMaintenanceFormBtn.classList.remove('btn-secondary');
            toggleMaintenanceFormBtn.classList.add('btn-primary');
        });
    }

    maintenanceForm.addEventListener('submit', (e) => {
        e.preventDefault();
        maintenanceHistory.push({
            type: document.getElementById('maintenanceType').value,
            date: document.getElementById('maintenanceDate').value
        });
        saveMaintenanceLog();
        renderMaintenanceLog();
        maintenanceForm.reset();

        // Ocultar formulario después de guardar
        if (maintenanceFormContainer && toggleMaintenanceFormBtn) {
            maintenanceFormContainer.style.display = 'none';
            toggleMaintenanceFormBtn.innerHTML = '<i class="fas fa-plus"></i> Agregar';
            toggleMaintenanceFormBtn.classList.remove('btn-secondary');
            toggleMaintenanceFormBtn.classList.add('btn-primary');
        }
    });
    
    maintenanceLog.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-btn')) {
            maintenanceHistory.splice(e.target.dataset.index, 1);
            saveMaintenanceLog();
            renderMaintenanceLog();
        }
    });
    
    // === DESCARGAR REPORTE ===
    
    async function downloadReport() {
        downloadReportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
        downloadReportBtn.disabled = true;
        
        try {
            const response = await fetch(`${API_URL}/generate_report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicleInfo: getVehicleInfo(),
                    maintenanceHistory
                })
            });
            
            if (!response.ok) throw new Error('Error generando informe');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'sentinel_pro_informe.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            downloadReportBtn.innerHTML = '<i class="fas fa-file-pdf"></i> Descargar Informe';
            downloadReportBtn.disabled = false;
        }
    }
    
    // === EVENT LISTENERS ===
    
    analyzeTripBtn.addEventListener('click', analyzeTrip);
    downloadReportBtn.addEventListener('click', downloadReport);
    commonFailuresBtn.addEventListener('click', getCommonFailures);
    valuationBtn.addEventListener('click', getValuation);
    
    // === INICIALIZACIÓN ===

    console.log('[INIT] SENTINEL PRO v9.0 iniciado');
    console.log('[INIT] Optimizaciones:');
    console.log('  ✓ Datos críticos cada 3s: RPM, velocidad, acelerador, carga, MAF');
    console.log('  ✓ Datos térmicos cada 60s: temperaturas');
    console.log('  ✓ Análisis salud automático cada 90s');

    initModeSelector();
    loadVehicleInfo();
    loadMaintenanceLog();
    updateAnalyzeButton();
    loadUploadedCSVs();
    
    // Polling de datos OBD
    fetchLiveData();
    setInterval(fetchLiveData, POLL_INTERVAL);
    
    // Polling de salud del vehículo
    fetchVehicleHealth();
    setInterval(fetchVehicleHealth, 10000);
    
    console.log('[INIT] ✓ Sistema activo');
});