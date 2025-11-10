# FASE 2 - Estado de Implementación

## ✅ COMPLETADO

### Backend (obd_server.py)
- ✅ Endpoint `/api/ai/analyze-current-trip` (líneas 828-930)
  - Analiza viaje en curso
  - Mínimo 100 puntos de datos (5 minutos)
  - Respuesta: driving_score, style, positives, concerns, recommendations

- ✅ Endpoint `/api/ai/analyze-vehicle-history` (líneas 932-1069)
  - Análisis histórico completo
  - Componentes en riesgo
  - Predicciones 6-12 meses
  - Estimación de costes

### Frontend - Dashboard (index.html)
- ✅ Indicador de estado OBD en header
- ✅ Botón cambiado: "Análisis Predictivo IA" → "Analizar Viaje Actual"
- ✅ Botón usa clases `.btn-ai .btn-large`
- ✅ Mensaje informativo: "disponible después de 5 minutos"
- ✅ Placeholder actualizado

## 🔄 PENDIENTE - JavaScript Dashboard

### Modificaciones necesarias en script.js:

```javascript
// === TRACKING DE VIAJE ACTUAL ===
let currentTripStartTime = null;
let currentTripData = [];

// Almacenar datos OBD cada lectura
function storeObdDataPoint(data) {
    if (currentTripStartTime) {
        currentTripData.push({
            timestamp: Date.now(),
            rpm: data.RPM || 0,
            speed: data.SPEED || 0,
            load: data.ENGINE_LOAD || 0,
            temp: data.COOLANT_TEMP || 0,
            maf: data.MAF || 0
        });

        // Actualizar estado del botón
        updateAnalyzeButton();
    }
}

// Actualizar botón de análisis según tiempo de viaje
function updateAnalyzeButton() {
    const btn = document.getElementById('analyzeTripBtn');
    const indicator = document.getElementById('obdStatusIndicator');

    if (!currentTripStartTime) {
        btn.disabled = true;
        indicator.className = 'status-indicator';
        indicator.innerHTML = '<i class="fas fa-circle"></i><span>Desconectado</span>';
        return;
    }

    const elapsed = (Date.now() - currentTripStartTime) / 1000 / 60; // minutos
    const dataPoints = currentTripData.length;

    // Indicador EN VIVO
    const vehicleInfo = getVehicleInfo();
    const vehicleName = `${vehicleInfo.brand} ${vehicleInfo.model}`.trim() || 'Vehículo';

    indicator.className = 'status-indicator connected';
    indicator.innerHTML = `<i class="fas fa-circle"></i><span>EN VIVO - ${vehicleName}</span>`;

    // Habilitar botón tras 5 minutos (100 puntos a 3s cada uno)
    if (dataPoints >= 100 && elapsed >= 5) {
        btn.disabled = false;
        btn.title = `${dataPoints} puntos de datos - ${elapsed.toFixed(1)} min`;
    } else {
        btn.disabled = true;
        btn.title = `Necesitas ${100 - dataPoints} puntos más (${(5 - elapsed).toFixed(1)} min)`;
    }
}

// Modificar función analyzeTrip para usar nuevo endpoint
async function analyzeTrip() {
    if (currentTripData.length < 100) {
        SENTINEL.Toast.warning('Datos insuficientes. Conduce al menos 5 minutos.');
        return;
    }

    const vehicleInfo = getVehicleInfo();
    const transmission = document.getElementById('vehicleTransmission')?.value || 'manual';

    showLoadingState('Analizando tu conducción con IA...');

    try {
        const response = await fetch(`${API_URL}/api/ai/analyze-current-trip`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                vehicle_info: vehicleInfo,
                trip_data: currentTripData,
                transmission: transmission
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error en análisis');
        }

        const analysis = await response.json();
        displayCurrentTripAnalysis(analysis);

    } catch (error) {
        console.error('[ANALYZE-TRIP] Error:', error);
        displayAiError(`Error: ${error.message}`);
    }
}

// Nueva función para mostrar análisis del viaje actual
function displayCurrentTripAnalysis(analysis) {
    aiPlaceholder.style.display = 'none';
    aiResults.style.display = 'block';

    const scoreClass = analysis.driving_score >= 80 ? 'excellent' :
                      analysis.driving_score >= 60 ? 'good' :
                      analysis.driving_score >= 40 ? 'warning' : 'critical';

    aiResults.innerHTML = `
        <div class="card ai-analysis-card">
            <h2><i class="fas fa-brain"></i> Análisis del Viaje Actual</h2>

            <div class="score-display" style="text-align: center; margin: 2rem 0;">
                <div class="score-circle ${scoreClass}" style="width: 150px; height: 150px; margin: 0 auto;">
                    <span class="score-value" style="font-size: 3rem;">${analysis.driving_score}</span>
                    <span class="score-label">/100</span>
                </div>
                <h3 style="margin-top: 1rem; color: #1e293b;">Estilo: ${analysis.style}</h3>
                <p style="color: #64748b;">${analysis.trip_summary || ''}</p>
            </div>

            ${analysis.positives && analysis.positives.length > 0 ? `
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i>
                <div>
                    <strong>✅ Aspectos Positivos:</strong>
                    <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                        ${analysis.positives.map(p => `<li>${p}</li>`).join('')}
                    </ul>
                </div>
            </div>
            ` : ''}

            ${analysis.concerns && analysis.concerns.length > 0 ? `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <div>
                    <strong>⚠️ Puntos de Atención:</strong>
                    <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                        ${analysis.concerns.map(c => `<li>${c}</li>`).join('')}
                    </ul>
                </div>
            </div>
            ` : ''}

            ${analysis.recommendations && analysis.recommendations.length > 0 ? `
            <div class="alert alert-info">
                <i class="fas fa-lightbulb"></i>
                <div>
                    <strong>💡 Recomendaciones:</strong>
                    <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                        ${analysis.recommendations.map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            </div>
            ` : ''}

            ${analysis.trip_stats ? `
            <div style="margin-top: 2rem; padding: 1rem; background: #f8fafc; border-radius: 8px;">
                <h3 style="margin: 0 0 1rem 0; color: #1e293b;"><i class="fas fa-chart-bar"></i> Estadísticas del Viaje</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem;">
                    <div>
                        <span style="color: #64748b; font-size: 0.85rem;">Duración</span>
                        <strong style="display: block; color: #1e293b; font-size: 1.1rem;">${analysis.trip_stats.duration_min} min</strong>
                    </div>
                    <div>
                        <span style="color: #64748b; font-size: 0.85rem;">RPM Promedio</span>
                        <strong style="display: block; color: #1e293b; font-size: 1.1rem;">${analysis.trip_stats.rpm_avg}</strong>
                    </div>
                    <div>
                        <span style="color: #64748b; font-size: 0.85rem;">Velocidad Prom.</span>
                        <strong style="display: block; color: #1e293b; font-size: 1.1rem;">${analysis.trip_stats.speed_avg} km/h</strong>
                    </div>
                    <div>
                        <span style="color: #64748b; font-size: 0.85rem;">Temp. Máxima</span>
                        <strong style="display: block; color: #1e293b; font-size: 1.1rem;">${analysis.trip_stats.temp_max}°C</strong>
                    </div>
                </div>
            </div>
            ` : ''}

            <p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 1.5rem;">
                <i class="fas fa-clock"></i> Análisis realizado: ${new Date(analysis.analyzed_at).toLocaleString('es-ES')}
            </p>
        </div>
    `;
}

// Modificar inicio de viaje
async function startTrip() {
    // ... código existente ...

    currentTripStartTime = Date.now();
    currentTripData = [];

    updateAnalyzeButton();
}

// Modificar fin de viaje
async function stopTrip() {
    // ... código existente ...

    currentTripStartTime = null;
    currentTripData = [];

    updateAnalyzeButton();
}

// Llamar storeObdDataPoint en cada lectura OBD
// Modificar fetchLiveData():
async function fetchLiveData() {
    try {
        const response = await fetch(`${API_URL}/data`);
        const data = await response.json();

        // Almacenar punto de datos
        storeObdDataPoint(data);

        // ... resto del código existente ...
    } catch (error) {
        // ... manejo de errores ...
    }
}
```

## 🔄 PENDIENTE - Fleet

### fleet.html - Añadir botón en tarjetas:
```html
<!-- En línea ~236, dentro de .vehicle-actions -->
<button class="btn-card btn-ai" onclick="analyzeFleetVehicle(${vehicle.id})" title="Análisis IA completo">
    <i class="fas fa-brain"></i>
</button>
```

### fleet.js - Función de análisis:
```javascript
async function analyzeFleetVehicle(vehicleId) {
    SENTINEL.Toast.info('Analizando vehículo con IA...');

    try {
        const response = await fetch(`${API_URL}/api/ai/analyze-vehicle-history`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                vehicle_id: vehicleId,
                include_predictions: true
            })
        });

        if (!response.ok) {
            throw new Error('Error en análisis');
        }

        const analysis = await response.json();
        showAIAnalysisModal(analysis);

    } catch (error) {
        console.error('[FLEET-AI] Error:', error);
        SENTINEL.Toast.error('Error al analizar el vehículo');
    }
}

function showAIAnalysisModal(analysis) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content large">
            <div class="modal-header">
                <h2><i class="fas fa-brain"></i> Análisis Predictivo Completo</h2>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <!-- Renderizar análisis aquí -->
                ${renderAIAnalysisContent(analysis)}
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cerrar</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Cerrar al hacer clic en close o fondo
    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}
```

## 📊 PRÓXIMOS PASOS

1. Implementar modificaciones JavaScript en script.js
2. Añadir botón IA en fleet.html
3. Implementar modal de análisis en fleet.js
4. Testing exhaustivo
5. Commit Fase 2

## 🎯 BENEFICIOS AL COMPLETAR

- Dashboard enfocado 100% en monitoreo en vivo
- Análisis IA del viaje actual (no histórico)
- Fleet con análisis predictivo por vehículo
- Backend robusto con nuevos endpoints
- UX mejorada con feedback claro
