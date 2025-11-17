// =============================================================================
// SENTINEL PRO - ALERTS PAGE JAVASCRIPT
// =============================================================================

// API URL se inicializa después de verificar SENTINEL
let API_URL = 'http://localhost:5000';

// State
let currentVehicles = [];
let currentAlerts = [];
let currentRules = [];
let currentStats = {};
let editingRuleId = null;

// Charts
let severityChart = null;
let typeChart = null;

// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[ALERTS] Inicializando sistema de alertas...');

    // Verificar que SENTINEL existe
    if (typeof SENTINEL === 'undefined') {
        console.error('[Error] SENTINEL no está definido. ¿Se cargó common.js?');
        return;
    }

    // Actualizar API_URL desde configuración
    API_URL = SENTINEL.CONFIG.API_URL || API_URL;

    // Setup tabs
    setupTabs();

    // Setup event listeners
    setupEventListeners();

    // Load vehicles
    await loadVehicles();

    // Load initial data
    await loadAlerts();
    await loadRules();
    await loadStats();

    console.log('[ALERTS] ✓ Sistema de alertas inicializado');
});

// =============================================================================
// TABS
// =============================================================================

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            // Update buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');

            // Load data for tab
            if (tabId === 'stats-tab' && !severityChart) {
                loadStats();
            }
        });
    });
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

function setupEventListeners() {
    // Alert filters
    document.getElementById('filterVehicle')?.addEventListener('change', loadAlerts);
    document.getElementById('filterSeverity')?.addEventListener('change', loadAlerts);
    document.getElementById('filterAcknowledged')?.addEventListener('change', loadAlerts);

    // Acknowledge all button
    document.getElementById('acknowledgeAllBtn')?.addEventListener('click', acknowledgeAllAlerts);

    // Rule filters
    document.getElementById('ruleVehicleFilter')?.addEventListener('change', loadRules);

    // Add rule button
    document.getElementById('addRuleBtn')?.addEventListener('click', openRuleModal);

    // Rule modal
    document.getElementById('closeRuleModal')?.addEventListener('click', closeRuleModal);
    document.getElementById('cancelRuleBtn')?.addEventListener('click', closeRuleModal);
    document.getElementById('ruleForm')?.addEventListener('submit', handleRuleSubmit);

    // Delete rule modal
    document.getElementById('closeDeleteRuleModal')?.addEventListener('click', closeDeleteRuleModal);
    document.getElementById('cancelDeleteRuleBtn')?.addEventListener('click', closeDeleteRuleModal);
    document.getElementById('confirmDeleteRuleBtn')?.addEventListener('click', confirmDeleteRule);

    // Parameter change for threshold hints
    document.getElementById('ruleParameter')?.addEventListener('change', updateThresholdHint);

    // Cerrar modales con ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeRuleModal();
            closeDeleteRuleModal();
        }
    });

    // Cerrar modal al hacer clic fuera
    const ruleModal = document.getElementById('ruleModal');
    const deleteModal = document.getElementById('deleteRuleModal');

    if (ruleModal) {
        ruleModal.addEventListener('click', (e) => {
            if (e.target === ruleModal) {
                closeRuleModal();
            }
        });
    }

    if (deleteModal) {
        deleteModal.addEventListener('click', (e) => {
            if (e.target === deleteModal) {
                closeDeleteRuleModal();
            }
        });
    }
}

// =============================================================================
// LOAD VEHICLES
// =============================================================================

async function loadVehicles() {
    try {
        const response = await fetch(`${API_URL}/api/vehicles`);
        const data = await response.json();

        if (data.success) {
            currentVehicles = data.vehicles;
            populateVehicleSelects();
        }
    } catch (error) {
        console.error('[ALERTS] Error cargando vehículos:', error);
    }
}

function populateVehicleSelects() {
    const selects = [
        'filterVehicle',
        'ruleVehicleFilter',
        'ruleVehicle'
    ];

    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (!select) return;

        // Clear existing options (except first one)
        while (select.options.length > 1) {
            select.remove(1);
        }

        // Add vehicle options
        currentVehicles.forEach(vehicle => {
            const option = document.createElement('option');
            option.value = vehicle.id;
            option.textContent = `${vehicle.brand} ${vehicle.model} (${vehicle.year})`;
            select.appendChild(option);
        });
    });
}

// =============================================================================
// LOAD ALERTS
// =============================================================================

async function loadAlerts() {
    try {
        const vehicleId = document.getElementById('filterVehicle')?.value;
        const acknowledged = document.getElementById('filterAcknowledged')?.value;

        let url = `${API_URL}/api/alerts?limit=100`;
        if (acknowledged !== '') {
            url += `&acknowledged=${acknowledged}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            currentAlerts = data.alerts;

            // Filter by vehicle if selected
            if (vehicleId) {
                currentAlerts = currentAlerts.filter(a => a.vehicle_id == vehicleId);
            }

            // Filter by severity if selected
            const severity = document.getElementById('filterSeverity')?.value;
            if (severity) {
                currentAlerts = currentAlerts.filter(a => a.severity === severity);
            }

            renderAlerts();
            updateAlertStats();
        }
    } catch (error) {
        console.error('[ALERTS] Error cargando alertas:', error);
        showToast('Error cargando alertas', 'error');
    }
}

function renderAlerts() {
    const alertsList = document.getElementById('alertsList');
    if (!alertsList) return;

    if (currentAlerts.length === 0) {
        alertsList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-check-circle"></i>
                <h3>No hay alertas</h3>
                <p>No se encontraron alertas con los filtros seleccionados</p>
            </div>
        `;
        return;
    }

    alertsList.innerHTML = currentAlerts.map(alert => `
        <div class="alert-item severity-${alert.severity} ${alert.acknowledged ? 'acknowledged' : ''}">
            <div class="alert-icon">
                ${getAlertIcon(alert.severity)}
            </div>
            <div class="alert-content">
                <div class="alert-header">
                    <div class="alert-title">
                        ${alert.brand} ${alert.model} ${alert.vin ? '(VIN: ' + alert.vin + ')' : ''}
                    </div>
                    <span class="alert-badge badge-${alert.severity}">
                        ${getSeverityText(alert.severity)}
                    </span>
                </div>
                <div class="alert-message">
                    ${alert.message}
                </div>
                <div class="alert-meta">
                    <div class="alert-meta-item">
                        <i class="fas fa-clock"></i>
                        ${formatDate(alert.timestamp)}
                    </div>
                    ${alert.value ? `
                        <div class="alert-meta-item">
                            <i class="fas fa-gauge"></i>
                            Valor: ${alert.value} (Umbral: ${alert.threshold})
                        </div>
                    ` : ''}
                    ${alert.acknowledged ? `
                        <div class="alert-meta-item">
                            <i class="fas fa-check"></i>
                            Reconocida ${formatDate(alert.acknowledged_at)}
                        </div>
                    ` : ''}
                </div>
            </div>
            ${!alert.acknowledged ? `
                <div class="alert-actions">
                    <button class="btn-icon btn-check" onclick="acknowledgeAlert(${alert.id})" title="Reconocer">
                        <i class="fas fa-check"></i>
                    </button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function getAlertIcon(severity) {
    const icons = {
        critical: '<i class="fas fa-exclamation-circle"></i>',
        high: '<i class="fas fa-exclamation-triangle"></i>',
        medium: '<i class="fas fa-info-circle"></i>',
        low: '<i class="fas fa-info"></i>'
    };
    return icons[severity] || icons.medium;
}

function getSeverityText(severity) {
    const texts = {
        critical: 'Crítico',
        high: 'Alto',
        medium: 'Medio',
        low: 'Bajo'
    };
    return texts[severity] || severity;
}

function updateAlertStats() {
    // Count by severity
    const counts = {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0
    };

    currentAlerts.forEach(alert => {
        if (!alert.acknowledged && counts.hasOwnProperty(alert.severity)) {
            counts[alert.severity]++;
        }
    });

    document.getElementById('critical_count').textContent = counts.critical;
    document.getElementById('high_count').textContent = counts.high;
    document.getElementById('medium_count').textContent = counts.medium;
}

// =============================================================================
// ALERT ACTIONS
// =============================================================================

async function acknowledgeAlert(alertId) {
    try {
        const response = await fetch(`${API_URL}/api/alerts/${alertId}/acknowledge`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showToast('Alerta reconocida correctamente', 'success');
            await loadAlerts();
        } else {
            showToast('Error reconociendo alerta', 'error');
        }
    } catch (error) {
        console.error('[ALERTS] Error reconociendo alerta:', error);
        showToast('Error reconociendo alerta', 'error');
    }
}

async function acknowledgeAllAlerts() {
    if (!confirm('¿Deseas reconocer todas las alertas no reconocidas?')) {
        return;
    }

    try {
        const vehicleId = document.getElementById('filterVehicle')?.value;

        const response = await fetch(`${API_URL}/api/alerts/acknowledge-all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vehicle_id: vehicleId || null
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`${data.acknowledged_count} alertas reconocidas`, 'success');
            await loadAlerts();
        } else {
            showToast('Error reconociendo alertas', 'error');
        }
    } catch (error) {
        console.error('[ALERTS] Error reconociendo todas las alertas:', error);
        showToast('Error reconociendo alertas', 'error');
    }
}

// =============================================================================
// LOAD RULES
// =============================================================================

async function loadRules() {
    try {
        const vehicleId = document.getElementById('ruleVehicleFilter')?.value;

        let url = `${API_URL}/api/alert-rules?enabled_only=false`;
        if (vehicleId) {
            url += `&vehicle_id=${vehicleId}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            currentRules = data.rules;
            renderRules();
            updateRuleStats();
        }
    } catch (error) {
        console.error('[ALERTS] Error cargando reglas:', error);
        showToast('Error cargando reglas', 'error');
    }
}

function renderRules() {
    const rulesList = document.getElementById('rulesList');
    if (!rulesList) return;

    if (currentRules.length === 0) {
        rulesList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-sliders-h"></i>
                <h3>No hay reglas de alertas</h3>
                <p>Crea tu primera regla para comenzar a monitorear parámetros</p>
                <button class="btn btn-primary" onclick="openRuleModal()">
                    <i class="fas fa-plus"></i> Crear Primera Regla
                </button>
            </div>
        `;
        return;
    }

    rulesList.innerHTML = currentRules.map(rule => `
        <div class="rule-card ${!rule.enabled ? 'disabled' : ''}">
            <div class="rule-header">
                <div class="rule-title">
                    <span class="rule-status ${rule.enabled ? 'active' : 'inactive'}"></span>
                    ${rule.name}
                </div>
                <div class="rule-actions">
                    <button class="btn-icon" onclick="toggleRule(${rule.id}, ${!rule.enabled})" title="${rule.enabled ? 'Desactivar' : 'Activar'}">
                        <i class="fas fa-power-off"></i>
                    </button>
                    <button class="btn-icon" onclick="editRule(${rule.id})" title="Editar">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="deleteRule(${rule.id}, '${rule.name}')" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>

            <div class="rule-condition">
                <span class="rule-condition-text">
                    SI <span class="condition-value">${getParameterName(rule.parameter)}</span>
                    ${rule.condition}
                    <span class="condition-value">${rule.threshold}</span>
                </span>
            </div>

            <div class="rule-meta">
                <div class="alert-meta-item">
                    <i class="fas fa-exclamation-triangle"></i>
                    Severidad: ${getSeverityText(rule.severity)}
                </div>
                ${rule.vehicle_id ? `
                    <div class="alert-meta-item">
                        <i class="fas fa-car"></i>
                        ${getVehicleName(rule.vehicle_id)}
                    </div>
                ` : `
                    <div class="alert-meta-item">
                        <i class="fas fa-globe"></i>
                        Global (todos los vehículos)
                    </div>
                `}
                ${rule.notify_sound ? `
                    <div class="alert-meta-item">
                        <i class="fas fa-volume-high"></i>
                        Sonido
                    </div>
                ` : ''}
                ${rule.notify_email ? `
                    <div class="alert-meta-item">
                        <i class="fas fa-envelope"></i>
                        Email
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function getParameterName(parameter) {
    const names = {
        rpm: 'RPM del Motor',
        speed: 'Velocidad',
        coolant_temp: 'Temperatura del Refrigerante',
        intake_temp: 'Temperatura de Admisión',
        engine_load: 'Carga del Motor',
        throttle_pos: 'Posición del Acelerador',
        fuel_pressure: 'Presión de Combustible',
        maf: 'Flujo de Aire (MAF)'
    };
    return names[parameter] || parameter;
}

function getVehicleName(vehicleId) {
    const vehicle = currentVehicles.find(v => v.id == vehicleId);
    return vehicle ? `${vehicle.brand} ${vehicle.model}` : `Vehículo #${vehicleId}`;
}

function updateRuleStats() {
    const activeRules = currentRules.filter(r => r.enabled).length;
    document.getElementById('active_rules').textContent = activeRules;
}

// =============================================================================
// RULE ACTIONS
// =============================================================================

function openRuleModal(ruleId = null) {
    editingRuleId = ruleId;

    if (ruleId) {
        // Edit mode
        const rule = currentRules.find(r => r.id === ruleId);
        if (!rule) return;

        document.getElementById('ruleModalTitle').innerHTML = '<i class="fas fa-edit"></i> Editar Regla de Alerta';
        document.getElementById('ruleId').value = rule.id;
        document.getElementById('ruleName').value = rule.name;
        document.getElementById('ruleVehicle').value = rule.vehicle_id || '';
        document.getElementById('ruleParameter').value = rule.parameter;
        document.getElementById('ruleCondition').value = rule.condition;
        document.getElementById('ruleThreshold').value = rule.threshold;
        document.getElementById('ruleSeverity').value = rule.severity;
        document.getElementById('ruleMessage').value = rule.message_template || '';
        document.getElementById('ruleNotifySound').checked = rule.notify_sound;
        document.getElementById('ruleNotifyEmail').checked = rule.notify_email;
    } else {
        // Create mode
        document.getElementById('ruleModalTitle').innerHTML = '<i class="fas fa-plus"></i> Nueva Regla de Alerta';
        document.getElementById('ruleForm').reset();
        document.getElementById('ruleId').value = '';
    }

    updateThresholdHint();

    // Abrir modal
    const modal = document.getElementById('ruleModal');
    modal.style.display = 'flex';
    modal.classList.add('active');
}

function closeRuleModal() {
    const modal = document.getElementById('ruleModal');
    modal.style.display = 'none';
    modal.classList.remove('active');
    editingRuleId = null;
}

async function handleRuleSubmit(e) {
    e.preventDefault();

    const ruleId = document.getElementById('ruleId').value;
    const vehicleId = document.getElementById('ruleVehicle').value;

    const ruleData = {
        vehicle_id: vehicleId || null,
        name: document.getElementById('ruleName').value,
        parameter: document.getElementById('ruleParameter').value,
        condition: document.getElementById('ruleCondition').value,
        threshold: parseFloat(document.getElementById('ruleThreshold').value),
        severity: document.getElementById('ruleSeverity').value,
        message_template: document.getElementById('ruleMessage').value || null,
        notify_sound: document.getElementById('ruleNotifySound').checked,
        notify_email: document.getElementById('ruleNotifyEmail').checked
    };

    try {
        const url = ruleId
            ? `${API_URL}/api/alert-rules/${ruleId}`
            : `${API_URL}/api/alert-rules`;

        const response = await fetch(url, {
            method: ruleId ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ruleData)
        });

        const data = await response.json();

        if (data.success) {
            showToast(ruleId ? 'Regla actualizada correctamente' : 'Regla creada correctamente', 'success');
            closeRuleModal();
            await loadRules();
        } else {
            showToast('Error guardando regla', 'error');
        }
    } catch (error) {
        console.error('[ALERTS] Error guardando regla:', error);
        showToast('Error guardando regla', 'error');
    }
}

function editRule(ruleId) {
    openRuleModal(ruleId);
}

function deleteRule(ruleId, ruleName) {
    editingRuleId = ruleId;

    // Actualizar mensaje con nombre de la regla
    const modal = document.getElementById('deleteRuleModal');
    const message = modal.querySelector('.confirm-message');
    if (message && ruleName) {
        message.textContent = `¿Estás seguro de que deseas eliminar la regla "${ruleName}"?`;
    }

    document.getElementById('deleteRuleName').textContent = ruleName;

    // Abrir modal
    modal.style.display = 'flex';
    modal.classList.add('active');
}

function closeDeleteRuleModal() {
    const modal = document.getElementById('deleteRuleModal');
    modal.style.display = 'none';
    modal.classList.remove('active');
    editingRuleId = null;
}

async function confirmDeleteRule() {
    if (!editingRuleId) return;

    try {
        const response = await fetch(`${API_URL}/api/alert-rules/${editingRuleId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showToast('Regla eliminada correctamente', 'success');
            closeDeleteRuleModal();
            await loadRules();
        } else {
            showToast('Error eliminando regla', 'error');
        }
    } catch (error) {
        console.error('[ALERTS] Error eliminando regla:', error);
        showToast('Error eliminando regla', 'error');
    }
}

async function toggleRule(ruleId, enabled) {
    try {
        const response = await fetch(`${API_URL}/api/alert-rules/${ruleId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });

        const data = await response.json();

        if (data.success) {
            showToast(enabled ? 'Regla activada' : 'Regla desactivada', 'success');
            await loadRules();
        } else {
            showToast('Error alternando regla', 'error');
        }
    } catch (error) {
        console.error('[ALERTS] Error alternando regla:', error);
        showToast('Error alternando regla', 'error');
    }
}

function updateThresholdHint() {
    const parameter = document.getElementById('ruleParameter').value;
    const hints = {
        rpm: 'Ej: 6000 RPM',
        speed: 'Ej: 180 km/h',
        coolant_temp: 'Ej: 95°C',
        intake_temp: 'Ej: 50°C',
        engine_load: 'Ej: 85%',
        throttle_pos: 'Ej: 90%',
        fuel_pressure: 'Ej: 250 kPa',
        maf: 'Ej: 50 g/s'
    };

    document.getElementById('thresholdHint').textContent = hints[parameter] || 'Valor para comparar';
}

// =============================================================================
// LOAD STATS
// =============================================================================

async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/api/alerts/stats?days=7`);
        const data = await response.json();

        if (data.success) {
            currentStats = data.stats;
            renderStats();
            renderCharts();
        }
    } catch (error) {
        console.error('[ALERTS] Error cargando estadísticas:', error);
        showToast('Error cargando estadísticas', 'error');
    }
}

function renderStats() {
    const statsContent = document.getElementById('statsContent');
    if (!statsContent) return;

    statsContent.innerHTML = `
        <div class="stat-box">
            <div class="stat-box-value">${currentStats.total_alerts || 0}</div>
            <div class="stat-box-label">Total Alertas</div>
        </div>
        <div class="stat-box">
            <div class="stat-box-value">${currentStats.unacknowledged || 0}</div>
            <div class="stat-box-label">Sin Reconocer</div>
        </div>
        <div class="stat-box">
            <div class="stat-box-value">${currentStats.acknowledgement_rate || 0}%</div>
            <div class="stat-box-label">Tasa de Reconocimiento</div>
        </div>
        <div class="stat-box">
            <div class="stat-box-value">${currentStats.period_days || 7}</div>
            <div class="stat-box-label">Días Analizados</div>
        </div>
    `;
}

function renderCharts() {
    renderSeverityChart();
    renderTypeChart();
}

function renderSeverityChart() {
    const ctx = document.getElementById('severityChart');
    if (!ctx) return;

    const bySeverity = currentStats.by_severity || {};

    if (severityChart) {
        severityChart.destroy();
    }

    severityChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Crítico', 'Alto', 'Medio', 'Bajo'],
            datasets: [{
                data: [
                    bySeverity.critical || 0,
                    bySeverity.high || 0,
                    bySeverity.medium || 0,
                    bySeverity.low || 0
                ],
                backgroundColor: [
                    '#dc2626',
                    '#f59e0b',
                    '#3b82f6',
                    '#10b981'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function renderTypeChart() {
    const ctx = document.getElementById('typeChart');
    if (!ctx) return;

    const byType = currentStats.by_type || {};
    const labels = Object.keys(byType).map(key => getParameterName(key));
    const data = Object.values(byType);

    if (typeChart) {
        typeChart.destroy();
    }

    typeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Alertas',
                data: data,
                backgroundColor: '#667eea'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function formatDate(timestamp) {
    if (!timestamp) return 'N/A';

    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // Less than 1 minute
    if (diff < 60000) {
        return 'Hace un momento';
    }

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `Hace ${minutes} minuto${minutes > 1 ? 's' : ''}`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `Hace ${hours} hora${hours > 1 ? 's' : ''}`;
    }

    // More than 24 hours
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showToast(message, type = 'info') {
    // Usar SENTINEL.Toast si está disponible, sino implementación propia
    if (window.SENTINEL && window.SENTINEL.Toast) {
        if (type === 'success') {
            window.SENTINEL.Toast.success(message);
        } else if (type === 'error') {
            window.SENTINEL.Toast.error(message);
        } else if (type === 'warning') {
            window.SENTINEL.Toast.warning(message);
        } else {
            window.SENTINEL.Toast.info(message);
        }
        return;
    }

    // Fallback: implementación propia
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
