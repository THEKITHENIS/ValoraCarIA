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
    const vehicleType = document.getElementById('vehicleType');
    const vehicleDataInputs = [vehicleBrand, vehicleModel, vehicleYear, vehicleMileage, vehicleType];
    
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
    
    // === FUNCIONES DE ALMACENAMIENTO ===
    
    function saveVehicleInfo() {
        const vehicleInfo = {
            brand: vehicleBrand.value,
            model: vehicleModel.value,
            year: vehicleYear.value,
            mileage: vehicleMileage.value,
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
            vehicleType.value = vehicleInfo.type || 'gasolina';
        }
    }
    
    function getVehicleInfo() {
        return {
            brand: vehicleBrand.value,
            model: vehicleModel.value,
            year: vehicleYear.value,
            type: vehicleType.value,
            mileage: vehicleMileage.value
        };
    }
    
    vehicleDataInputs.forEach(input => input.addEventListener('change', saveVehicleInfo));
    
    // === FUNCIONES DE ACTUALIZACIÓN UI ===
    
    function updateLiveData(data) {
        // RPM
        if (data.rpm !== null && data.rpm !== undefined) {
            liveRpm.textContent = Math.round(data.rpm);
            liveRpm.classList.remove('offline');
        } else {
            liveRpm.textContent = '---';
            liveRpm.classList.add('offline');
        }

        // SPEED
        if (data.speed !== null && data.speed !== undefined) {
            liveSpeed.textContent = Math.round(data.speed);
            liveSpeed.classList.remove('offline');
        } else {
            liveSpeed.textContent = '---';
            liveSpeed.classList.add('offline');
        }

        // DISTANCE (usando distance_since_clear)
        if (data.distance_since_clear !== null && data.distance_since_clear !== undefined) {
            liveDistance.textContent = data.distance_since_clear.toFixed(3);
            liveDistance.classList.remove('offline');
        } else {
            liveDistance.textContent = '---';
            liveDistance.classList.add('offline');
        }

        // THROTTLE
        if (data.throttle_pos !== null && data.throttle_pos !== undefined) {
            liveThrottle.textContent = Math.round(data.throttle_pos);
            liveThrottle.classList.remove('offline');
        } else {
            liveThrottle.textContent = '---';
            liveThrottle.classList.add('offline');
        }

        // ENGINE LOAD
        if (data.engine_load !== null && data.engine_load !== undefined) {
            liveLoad.textContent = Math.round(data.engine_load);
            liveLoad.classList.remove('offline');
        } else {
            liveLoad.textContent = '---';
            liveLoad.classList.add('offline');
        }

        // MAF
        if (data.maf !== null && data.maf !== undefined) {
            liveMaf.textContent = data.maf.toFixed(1);
            liveMaf.classList.remove('offline');
        } else {
            liveMaf.textContent = '---';
            liveMaf.classList.add('offline');
        }

        // COOLANT TEMP (datos térmicos - mantener último valor si null)
        if (data.coolant_temp !== null && data.coolant_temp !== undefined) {
            liveCoolantTemp.textContent = Math.round(data.coolant_temp);
            liveCoolantTemp.classList.remove('offline');
        } else if (data.connected === false) {
            liveCoolantTemp.textContent = '---';
            liveCoolantTemp.classList.add('offline');
        }
        // Si es null pero connected=true, mantener último valor (no actualizar)

        // INTAKE TEMP (datos térmicos - mantener último valor si null)
        if (data.intake_temp !== null && data.intake_temp !== undefined) {
            liveIntakeTemp.textContent = Math.round(data.intake_temp);
            liveIntakeTemp.classList.remove('offline');
        } else if (data.connected === false) {
            liveIntakeTemp.textContent = '---';
            liveIntakeTemp.classList.add('offline');
        }
        // Si es null pero connected=true, mantener último valor (no actualizar)

        // Log adicional de PIDs disponibles en consola (para debug)
        if (data.connected) {
            const allPIDs = {
                rpm: data.rpm,
                speed: data.speed,
                throttle_pos: data.throttle_pos,
                engine_load: data.engine_load,
                maf: data.maf,
                coolant_temp: data.coolant_temp,
                intake_temp: data.intake_temp,
                distance_since_clear: data.distance_since_clear,
                intake_pressure: data.intake_pressure,
                voltage: data.voltage,
                fuel_pressure: data.fuel_pressure,
                barometric_pressure: data.barometric_pressure,
                distance_mil: data.distance_mil,
                relative_throttle: data.relative_throttle,
                ambient_temp: data.ambient_temp,
                accelerator_d: data.accelerator_d,
                accelerator_e: data.accelerator_e,
                run_time: data.run_time
            };

            // Log cada 30 segundos para no saturar la consola
            const now = Date.now();
            if (!window.lastPIDLog || now - window.lastPIDLog > 30000) {
                console.log('[OBD] PIDs disponibles:', allPIDs);
                window.lastPIDLog = now;
            }
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
    
    // === FUNCIONES DE RED ===
    
    async function fetchLiveData() {
        try {
            const response = await fetch(`${API_URL}/api/live_data`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.connected === false) {
                if (isOBDConnected) {
                    console.log('[OBD] Conexión perdida');
                    isOBDConnected = false;
                }
                consecutiveFailures++;
                updateLiveData({
                    rpm: null,
                    speed: null,
                    throttle_pos: null,
                    engine_load: null,
                    maf: null,
                    coolant_temp: null,
                    intake_temp: null,
                    distance_since_clear: null
                });
            } else {
                if (!isOBDConnected) {
                    console.log('[OBD] ✓ Conectado - 21 PIDs activos');
                    showConnectionNotification('OBD conectado - 21 PIDs activos (críticos 3s, térmicos 60s)', 'success');
                }
                isOBDConnected = true;
                consecutiveFailures = 0;
                updateLiveData(data);
            }

            updateAnalyzeButton();

        } catch (error) {
            consecutiveFailures++;

            if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES && isOBDConnected) {
                console.log('[OBD] Múltiples fallos detectados');
                showConnectionNotification('Conexión OBD perdida. Modo offline activado.', 'warning');
            }

            isOBDConnected = false;
            updateLiveData({
                rpm: null,
                speed: null,
                throttle_pos: null,
                engine_load: null,
                maf: null,
                coolant_temp: null,
                intake_temp: null,
                distance_since_clear: null
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
        localStorage.setItem('maintenanceHistory', JSON.stringify(maintenanceHistory));
    }
    
    function loadMaintenanceLog() {
        const stored = localStorage.getItem('maintenanceHistory');
        if (stored) {
            maintenanceHistory = JSON.parse(stored);
            renderMaintenanceLog();
        }
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

    console.log('[INIT] SENTINEL PRO v9.0 - INTEGRACIÓN OBD COMPLETA');
    console.log('[INIT] Optimizaciones:');
    console.log('  ✓ 21 PIDs confirmados activos');
    console.log('  ✓ Datos críticos cada 3s: RPM, velocidad, acelerador, carga, MAF, presión admisión, voltaje');
    console.log('  ✓ Datos térmicos cada 60s: temperaturas refrigerante/admisión');
    console.log('  ✓ Datos adicionales: presión combustible, presión barométrica, acelerador D/E, tiempo marcha, distancia');
    console.log('  ✓ Todos los PIDs guardados en CSV para análisis posterior');
    console.log('  ✓ Análisis salud automático cada 90s');
    
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