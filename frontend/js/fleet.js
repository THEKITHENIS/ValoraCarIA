// =============================================================================
// SENTINEL PRO v10.0 - FLEET MANAGEMENT
// Gestión completa de flotas de vehículos
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[FLEET] Sistema de gestión de flotas iniciado');

    // === VARIABLES GLOBALES ===
    let allVehicles = [];
    let filteredVehicles = [];
    let currentVehicleId = null;
    let deleteVehicleId = null;

    // === REFERENCIAS DOM ===
    // Stats
    const totalVehiclesEl = document.getElementById('total_vehicles');
    const totalTripsEl = document.getElementById('total_trips');
    const totalDistanceEl = document.getElementById('total_distance');
    const activeTripsEl = document.getElementById('active_trips');

    // Filtros
    const filterBrand = document.getElementById('filterBrand');
    const filterFuel = document.getElementById('filterFuel');
    const filterTransmission = document.getElementById('filterTransmission');
    const filterHealth = document.getElementById('filterHealth');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');

    // Vehículos
    const vehiclesGrid = document.getElementById('vehiclesGrid');
    const noVehiclesMessage = document.getElementById('noVehiclesMessage');
    const viewGridBtn = document.getElementById('viewGrid');
    const viewListBtn = document.getElementById('viewList');

    // Botones
    const addVehicleFloatingBtn = document.getElementById('addVehicleFloatingBtn');
    const addFirstVehicleBtn = document.getElementById('addFirstVehicleBtn');

    // Modal
    const vehicleModal = document.getElementById('vehicleModal');
    const closeModal = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const vehicleForm = document.getElementById('vehicleForm');
    const modalTitle = document.getElementById('modalTitle');

    // Modal Delete
    const deleteModal = document.getElementById('deleteModal');
    const closeDeleteModal = document.getElementById('closeDeleteModal');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const deleteVehicleName = document.getElementById('deleteVehicleName');

    // Form fields
    const vehicleIdField = document.getElementById('vehicleId');
    const vehicleVin = document.getElementById('vehicleVin');
    const vehicleBrandModal = document.getElementById('vehicleBrandModal');
    const vehicleModelModal = document.getElementById('vehicleModelModal');
    const vehicleYearModal = document.getElementById('vehicleYearModal');
    const vehicleMileageModal = document.getElementById('vehicleMileageModal');
    const vehicleTransmissionModal = document.getElementById('vehicleTransmissionModal');
    const vehicleFuelModal = document.getElementById('vehicleFuelModal');
    const vehicleNotes = document.getElementById('vehicleNotes');

    // === FUNCIONES PRINCIPALES ===

    /**
     * Cargar estadísticas de la flota
     */
    async function loadFleetStats() {
        try {
            const data = await SENTINEL.API.get('/api/fleet/stats');

            if (data.success) {
                const stats = data.fleet_stats;
                totalVehiclesEl.textContent = stats.total_vehicles || 0;
                totalTripsEl.textContent = stats.total_trips || 0;
                totalDistanceEl.textContent = SENTINEL.Formatter.number(stats.total_distance, 0);
                activeTripsEl.textContent = stats.active_trips || 0;
            }
        } catch (error) {
            console.error('[FLEET] Error cargando estadísticas:', error);
        }
    }

    /**
     * Cargar vehículos de la flota
     */
    async function loadVehicles() {
        try {
            SENTINEL.Loading.show(vehiclesGrid, 'Cargando vehículos...');

            const data = await SENTINEL.API.get('/api/vehicles');

            if (data.success) {
                allVehicles = data.vehicles || [];
                filteredVehicles = [...allVehicles];

                // Actualizar opciones de filtro de marcas
                updateBrandFilter();

                // Renderizar vehículos
                renderVehicles();

                // Mostrar mensaje si no hay vehículos
                if (allVehicles.length === 0) {
                    vehiclesGrid.style.display = 'none';
                    noVehiclesMessage.style.display = 'flex';
                } else {
                    vehiclesGrid.style.display = 'grid';
                    noVehiclesMessage.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('[FLEET] Error cargando vehículos:', error);
            SENTINEL.Toast.error('Error al cargar los vehículos');
            vehiclesGrid.innerHTML = '<p class="error">Error al cargar vehículos</p>';
        }
    }

    /**
     * Actualizar opciones del filtro de marcas
     */
    function updateBrandFilter() {
        const brands = [...new Set(allVehicles.map(v => v.brand))].sort();
        filterBrand.innerHTML = '<option value="">Todas las marcas</option>';
        brands.forEach(brand => {
            const option = document.createElement('option');
            option.value = brand;
            option.textContent = brand;
            filterBrand.appendChild(option);
        });
    }

    /**
     * Renderizar vehículos
     */
    function renderVehicles() {
        if (filteredVehicles.length === 0) {
            vehiclesGrid.innerHTML = '<p class="no-results">No hay vehículos que coincidan con los filtros</p>';
            return;
        }

        vehiclesGrid.innerHTML = filteredVehicles.map(vehicle => createVehicleCard(vehicle)).join('');

        // Añadir event listeners
        document.querySelectorAll('.vehicle-card').forEach(card => {
            const vehicleId = parseInt(card.dataset.vehicleId);

            card.querySelector('.btn-view').addEventListener('click', (e) => {
                e.stopPropagation();
                viewVehicleDetails(vehicleId);
            });

            card.querySelector('.btn-edit').addEventListener('click', (e) => {
                e.stopPropagation();
                openEditModal(vehicleId);
            });

            card.querySelector('.btn-delete').addEventListener('click', (e) => {
                e.stopPropagation();
                openDeleteModal(vehicleId);
            });

            card.querySelector('.btn-start-trip').addEventListener('click', (e) => {
                e.stopPropagation();
                startTrip(vehicleId);
            });

            card.querySelector('.btn-ai').addEventListener('click', (e) => {
                e.stopPropagation();
                analyzeFleetVehicle(vehicleId);
            });
        });
    }

    /**
     * Crear tarjeta de vehículo
     */
    function createVehicleCard(vehicle) {
        const healthScore = vehicle.health_score || 100;
        const healthClass = SENTINEL.HealthUtils.getHealthClass(healthScore);
        const healthText = SENTINEL.HealthUtils.getHealthText(healthScore);

        return `
            <div class="vehicle-card" data-vehicle-id="${vehicle.id}">
                <div class="vehicle-card-header">
                    <div class="vehicle-icon">
                        <i class="fas fa-car"></i>
                    </div>
                    <div class="vehicle-header-info">
                        <h3>${vehicle.brand} ${vehicle.model}</h3>
                        <span class="vehicle-year">${vehicle.year} | ${capitalizeFirst(vehicle.fuel_type)}</span>
                    </div>
                    <div class="vehicle-health ${healthClass}">
                        <span class="health-score">${healthScore}</span>
                        <span class="health-label">/100</span>
                    </div>
                </div>

                <div class="vehicle-card-body">
                    <div class="vehicle-info-row">
                        <div class="info-item">
                            <i class="fas fa-gears"></i>
                            <span>${capitalizeFirst(vehicle.transmission)}</span>
                        </div>
                        <div class="info-item">
                            <i class="fas fa-road"></i>
                            <span>${SENTINEL.Formatter.number(vehicle.mileage, 0)} km</span>
                        </div>
                    </div>

                    <div class="vehicle-stats-mini">
                        <div class="stat-mini">
                            <i class="fas fa-route"></i>
                            <div>
                                <strong>${vehicle.total_trips || 0}</strong>
                                <span>Viajes</span>
                            </div>
                        </div>
                        <div class="stat-mini">
                            <i class="fas fa-wrench"></i>
                            <div>
                                <strong>${vehicle.maintenance_count || 0}</strong>
                                <span>Mantenimientos</span>
                            </div>
                        </div>
                    </div>

                    ${vehicle.notes ? `
                    <div class="vehicle-notes">
                        <i class="fas fa-note-sticky"></i>
                        <span>${vehicle.notes}</span>
                    </div>
                    ` : ''}
                </div>

                <div class="vehicle-card-footer">
                    <button class="btn-card btn-view" title="Ver detalles">
                        <i class="fas fa-eye"></i>
                        Detalles
                    </button>
                    <button class="btn-card btn-start-trip" title="Iniciar viaje">
                        <i class="fas fa-play"></i>
                        Viaje
                    </button>
                    <button class="btn-card btn-ai" title="Análisis IA completo">
                        <i class="fas fa-brain"></i>
                    </button>
                    <button class="btn-card btn-edit" title="Editar">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-card btn-delete" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Aplicar filtros
     */
    function applyFilters() {
        filteredVehicles = allVehicles.filter(vehicle => {
            // Filtro de marca
            if (filterBrand.value && vehicle.brand !== filterBrand.value) {
                return false;
            }

            // Filtro de combustible
            if (filterFuel.value && vehicle.fuel_type !== filterFuel.value) {
                return false;
            }

            // Filtro de transmisión
            if (filterTransmission.value && vehicle.transmission !== filterTransmission.value) {
                return false;
            }

            // Filtro de salud
            if (filterHealth.value) {
                const health = vehicle.health_score || 100;
                const healthClass = SENTINEL.HealthUtils.getHealthClass(health);
                if (healthClass !== filterHealth.value) {
                    return false;
                }
            }

            return true;
        });

        renderVehicles();
    }

    /**
     * Limpiar filtros
     */
    function clearFilters() {
        filterBrand.value = '';
        filterFuel.value = '';
        filterTransmission.value = '';
        filterHealth.value = '';
        applyFilters();
    }

    /**
     * Abrir modal para añadir vehículo
     */
    function openAddModal() {
        currentVehicleId = null;
        vehicleForm.reset();
        vehicleIdField.value = '';
        modalTitle.innerHTML = '<i class="fas fa-car-side"></i> Añadir Vehículo';
        vehicleModal.classList.add('show');
    }

    /**
     * Abrir modal para editar vehículo
     */
    async function openEditModal(vehicleId) {
        try {
            const data = await SENTINEL.API.get(`/api/vehicles/${vehicleId}`);

            if (data.success) {
                const vehicle = data.vehicle;
                currentVehicleId = vehicleId;

                vehicleIdField.value = vehicleId;
                vehicleVin.value = vehicle.vin || '';
                vehicleBrandModal.value = vehicle.brand;
                vehicleModelModal.value = vehicle.model;
                vehicleYearModal.value = vehicle.year;
                vehicleMileageModal.value = vehicle.mileage || 0;
                vehicleTransmissionModal.value = vehicle.transmission;
                vehicleFuelModal.value = vehicle.fuel_type;
                vehicleNotes.value = vehicle.notes || '';

                modalTitle.innerHTML = '<i class="fas fa-edit"></i> Editar Vehículo';
                vehicleModal.classList.add('show');
            }
        } catch (error) {
            console.error('[FLEET] Error cargando vehículo:', error);
            SENTINEL.Toast.error('Error al cargar el vehículo');
        }
    }

    /**
     * Cerrar modal
     */
    function closeVehicleModal() {
        vehicleModal.classList.remove('show');
        vehicleForm.reset();
        currentVehicleId = null;
    }

    /**
     * Guardar vehículo (crear o actualizar)
     */
    async function saveVehicle(e) {
        e.preventDefault();

        const vehicleData = {
            vin: vehicleVin.value.trim() || undefined,
            brand: vehicleBrandModal.value.trim(),
            model: vehicleModelModal.value.trim(),
            year: parseInt(vehicleYearModal.value),
            fuel_type: vehicleFuelModal.value,
            transmission: vehicleTransmissionModal.value,
            mileage: parseInt(vehicleMileageModal.value) || 0,
            notes: vehicleNotes.value.trim() || undefined
        };

        try {
            if (currentVehicleId) {
                // Actualizar vehículo
                await SENTINEL.API.put(`/api/vehicles/${currentVehicleId}`, vehicleData);
                SENTINEL.Toast.success('Vehículo actualizado correctamente');
            } else {
                // Crear vehículo
                const result = await SENTINEL.API.post('/api/vehicles', vehicleData);
                SENTINEL.Toast.success('Vehículo añadido correctamente');

                // Guardar como vehículo activo
                if (result.vehicle_id) {
                    SENTINEL.ActiveVehicle.set(result.vehicle_id);
                }
            }

            closeVehicleModal();
            await loadVehicles();
            await loadFleetStats();

        } catch (error) {
            console.error('[FLEET] Error guardando vehículo:', error);
            SENTINEL.Toast.error(error.message || 'Error al guardar el vehículo');
        }
    }

    /**
     * Abrir modal de confirmación de eliminación
     */
    function openDeleteModal(vehicleId) {
        deleteVehicleId = vehicleId;
        const vehicle = allVehicles.find(v => v.id === vehicleId);

        if (vehicle) {
            deleteVehicleName.textContent = `${vehicle.brand} ${vehicle.model} (${vehicle.year})`;
            deleteModal.classList.add('show');
        }
    }

    /**
     * Cerrar modal de eliminación
     */
    function closeConfirmDeleteModal() {
        deleteModal.classList.remove('show');
        deleteVehicleId = null;
    }

    /**
     * Eliminar vehículo
     */
    async function deleteVehicle() {
        if (!deleteVehicleId) return;

        try {
            await SENTINEL.API.delete(`/api/vehicles/${deleteVehicleId}`);
            SENTINEL.Toast.success('Vehículo eliminado correctamente');

            closeConfirmDeleteModal();
            await loadVehicles();
            await loadFleetStats();

        } catch (error) {
            console.error('[FLEET] Error eliminando vehículo:', error);
            SENTINEL.Toast.error('Error al eliminar el vehículo');
        }
    }

    /**
     * Ver detalles del vehículo
     */
    function viewVehicleDetails(vehicleId) {
        // Guardar como vehículo activo
        SENTINEL.ActiveVehicle.set(vehicleId);
        const vehicle = allVehicles.find(v => v.id === vehicleId);
        if (vehicle) {
            SENTINEL.ActiveVehicle.setInfo(vehicle);
        }

        // Redirigir a la página de detalles (o al dashboard por ahora)
        SENTINEL.Toast.info('Redirigiendo al dashboard del vehículo...');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);
    }

    /**
     * Iniciar viaje
     */
    async function startTrip(vehicleId) {
        try {
            const result = await SENTINEL.API.post('/api/trips/start', { vehicle_id: vehicleId });

            if (result.success) {
                SENTINEL.Toast.success('Viaje iniciado. Redirigiendo al dashboard...');

                // Guardar como vehículo activo
                SENTINEL.ActiveVehicle.set(vehicleId);
                const vehicle = allVehicles.find(v => v.id === vehicleId);
                if (vehicle) {
                    SENTINEL.ActiveVehicle.setInfo(vehicle);
                }

                // Redirigir al dashboard
                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 1000);
            }
        } catch (error) {
            console.error('[FLEET] Error iniciando viaje:', error);
            SENTINEL.Toast.error('Error al iniciar el viaje');
        }
    }

    /**
     * Analizar vehículo con IA (FASE 2 - v10.0)
     */
    async function analyzeFleetVehicle(vehicleId) {
        SENTINEL.Toast.info('Analizando vehículo con IA...');

        try {
            const response = await fetch(`${SENTINEL.API.BASE_URL}/api/ai/analyze-vehicle-history`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicle_id: vehicleId,
                    include_predictions: true
                })
            });

            if (!response.ok) {
                throw new Error('Error en análisis');
            }

            const analysis = await response.json();
            showAIAnalysisModal(analysis, vehicleId);

        } catch (error) {
            console.error('[FLEET-AI] Error:', error);
            SENTINEL.Toast.error('Error al analizar el vehículo');
        }
    }

    /**
     * Mostrar modal con análisis IA (FASE 2 - v10.0)
     */
    function showAIAnalysisModal(analysis, vehicleId) {
        const vehicle = allVehicles.find(v => v.id === vehicleId);
        const vehicleName = vehicle ? `${vehicle.brand} ${vehicle.model} (${vehicle.year})` : 'Vehículo';

        // Crear modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content large">
                <div class="modal-header">
                    <h2><i class="fas fa-brain"></i> Análisis Predictivo Completo - ${vehicleName}</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${renderAIAnalysisContent(analysis)}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-close-btn">Cerrar</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Event listeners
        const closeModal = () => modal.remove();
        modal.querySelector('.modal-close').addEventListener('click', closeModal);
        modal.querySelector('.modal-close-btn').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        // Mostrar modal con animación
        setTimeout(() => modal.classList.add('show'), 10);
    }

    /**
     * Renderizar contenido del análisis IA
     */
    function renderAIAnalysisContent(analysis) {
        const scoreClass = analysis.overall_score >= 80 ? 'excellent' :
                          analysis.overall_score >= 60 ? 'good' :
                          analysis.overall_score >= 40 ? 'warning' : 'critical';

        let html = `
            <div class="ai-analysis-summary">
                <div class="score-display" style="text-align: center; margin: 2rem 0;">
                    <div class="score-circle ${scoreClass}" style="width: 150px; height: 150px; margin: 0 auto;">
                        <span class="score-value" style="font-size: 3rem;">${analysis.overall_score}</span>
                        <span class="score-label">/100</span>
                    </div>
                    <h3 style="margin-top: 1rem; color: #1e293b;">Estado General del Vehículo</h3>
                </div>
        `;

        // Componentes en riesgo
        if (analysis.components_at_risk && analysis.components_at_risk.length > 0) {
            html += `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    <div>
                        <strong>⚠️ Componentes en Riesgo:</strong>
                        <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                            ${analysis.components_at_risk.map(comp => `
                                <li><strong>${comp.component}:</strong> ${comp.risk_level} - ${comp.reason}</li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }

        // Predicciones
        if (analysis.predictions && analysis.predictions.length > 0) {
            html += `
                <div class="alert alert-info">
                    <i class="fas fa-crystal-ball"></i>
                    <div>
                        <strong>🔮 Predicciones (6-12 meses):</strong>
                        <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                            ${analysis.predictions.map(pred => `
                                <li><strong>${pred.timeframe}:</strong> ${pred.maintenance} - ${pred.estimated_cost}</li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }

        // Recomendaciones
        if (analysis.recommendations && analysis.recommendations.length > 0) {
            html += `
                <div class="alert alert-success">
                    <i class="fas fa-lightbulb"></i>
                    <div>
                        <strong>💡 Recomendaciones:</strong>
                        <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                            ${analysis.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }

        // Resumen de costes
        if (analysis.cost_summary) {
            html += `
                <div style="margin-top: 2rem; padding: 1rem; background: #f8fafc; border-radius: 8px;">
                    <h3 style="margin: 0 0 1rem 0; color: #1e293b;"><i class="fas fa-euro-sign"></i> Estimación de Costes</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                        <div>
                            <span style="color: #64748b; font-size: 0.85rem;">Mantenimiento Inmediato</span>
                            <strong style="display: block; color: #1e293b; font-size: 1.3rem;">${analysis.cost_summary.immediate}€</strong>
                        </div>
                        <div>
                            <span style="color: #64748b; font-size: 0.85rem;">Próximos 6 meses</span>
                            <strong style="display: block; color: #1e293b; font-size: 1.3rem;">${analysis.cost_summary.next_6_months}€</strong>
                        </div>
                        <div>
                            <span style="color: #64748b; font-size: 0.85rem;">Total Anual Estimado</span>
                            <strong style="display: block; color: #1e293b; font-size: 1.3rem;">${analysis.cost_summary.annual_estimate}€</strong>
                        </div>
                    </div>
                </div>
            `;
        }

        html += `
                <p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 1.5rem;">
                    <i class="fas fa-clock"></i> Análisis realizado: ${new Date(analysis.analyzed_at).toLocaleString('es-ES')}
                </p>
            </div>
        `;

        return html;
    }

    /**
     * Cambiar vista (grid/list)
     */
    function changeView(view) {
        if (view === 'grid') {
            vehiclesGrid.classList.remove('list-view');
            vehiclesGrid.classList.add('grid-view');
            viewGridBtn.classList.add('active');
            viewListBtn.classList.remove('active');
        } else {
            vehiclesGrid.classList.remove('grid-view');
            vehiclesGrid.classList.add('list-view');
            viewListBtn.classList.add('active');
            viewGridBtn.classList.remove('active');
        }
    }

    /**
     * Capitalizar primera letra
     */
    function capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // === EVENT LISTENERS ===

    // Botones añadir vehículo
    addVehicleFloatingBtn.addEventListener('click', openAddModal);
    if (addFirstVehicleBtn) {
        addFirstVehicleBtn.addEventListener('click', openAddModal);
    }
    const addVehicleHeaderBtn = document.getElementById('addVehicleHeaderBtn');
    if (addVehicleHeaderBtn) {
        addVehicleHeaderBtn.addEventListener('click', openAddModal);
    }

    // Modal
    closeModal.addEventListener('click', closeVehicleModal);
    cancelBtn.addEventListener('click', closeVehicleModal);
    vehicleForm.addEventListener('submit', saveVehicle);

    // Modal Delete
    closeDeleteModal.addEventListener('click', closeConfirmDeleteModal);
    cancelDeleteBtn.addEventListener('click', closeConfirmDeleteModal);
    confirmDeleteBtn.addEventListener('click', deleteVehicle);

    // Cerrar modal al hacer click fuera
    window.addEventListener('click', (e) => {
        if (e.target === vehicleModal) closeVehicleModal();
        if (e.target === deleteModal) closeConfirmDeleteModal();
    });

    // Filtros
    filterBrand.addEventListener('change', applyFilters);
    filterFuel.addEventListener('change', applyFilters);
    filterTransmission.addEventListener('change', applyFilters);
    filterHealth.addEventListener('change', applyFilters);
    clearFiltersBtn.addEventListener('click', clearFilters);

    // Vista
    viewGridBtn.addEventListener('click', () => changeView('grid'));
    viewListBtn.addEventListener('click', () => changeView('list'));

    // === INICIALIZACIÓN ===
    await loadFleetStats();
    await loadVehicles();

    console.log('[FLEET] ✓ Sistema de flotas listo');
});
