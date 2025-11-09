// =============================================================================
// SENTINEL PRO - COMMON FUNCTIONS
// Funciones compartidas para todas las páginas del frontend
// =============================================================================

// Configuración global
const SENTINEL_CONFIG = {
    API_URL: 'http://localhost:5000',
    POLL_INTERVAL: 3000,
    VERSION: '10.0',
    APP_NAME: 'SENTINEL PRO'
};

// =============================================================================
// GESTIÓN DE LOCAL STORAGE
// =============================================================================

const StorageManager = {
    /**
     * Guarda datos en localStorage
     * @param {string} key - Clave
     * @param {*} value - Valor (se convierte a JSON automáticamente)
     */
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('[Storage] Error guardando:', e);
            return false;
        }
    },

    /**
     * Obtiene datos de localStorage
     * @param {string} key - Clave
     * @param {*} defaultValue - Valor por defecto si no existe
     * @returns {*} Valor parseado o defaultValue
     */
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('[Storage] Error leyendo:', e);
            return defaultValue;
        }
    },

    /**
     * Elimina un elemento del localStorage
     * @param {string} key - Clave
     */
    remove(key) {
        localStorage.removeItem(key);
    },

    /**
     * Limpia todo el localStorage
     */
    clear() {
        localStorage.clear();
    }
};

// =============================================================================
// GESTIÓN DE VEHÍCULO ACTIVO
// =============================================================================

const ActiveVehicle = {
    /**
     * Guarda el vehículo activo
     * @param {number} vehicleId - ID del vehículo
     */
    set(vehicleId) {
        StorageManager.set('active_vehicle_id', vehicleId);
    },

    /**
     * Obtiene el ID del vehículo activo
     * @returns {number|null} ID del vehículo o null
     */
    get() {
        return StorageManager.get('active_vehicle_id', null);
    },

    /**
     * Guarda información completa del vehículo activo
     * @param {Object} vehicleData - Datos del vehículo
     */
    setInfo(vehicleData) {
        StorageManager.set('active_vehicle_info', vehicleData);
    },

    /**
     * Obtiene información completa del vehículo activo
     * @returns {Object|null} Datos del vehículo
     */
    getInfo() {
        return StorageManager.get('active_vehicle_info', null);
    },

    /**
     * Limpia el vehículo activo
     */
    clear() {
        StorageManager.remove('active_vehicle_id');
        StorageManager.remove('active_vehicle_info');
    }
};

// =============================================================================
// FUNCIONES DE RED (FETCH API)
// =============================================================================

const API = {
    /**
     * Realiza una petición GET
     * @param {string} endpoint - Endpoint de la API
     * @returns {Promise<Object>} Respuesta de la API
     */
    async get(endpoint) {
        try {
            const response = await fetch(`${SENTINEL_CONFIG.API_URL}${endpoint}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('[API GET] Error:', error);
            throw error;
        }
    },

    /**
     * Realiza una petición POST
     * @param {string} endpoint - Endpoint de la API
     * @param {Object} data - Datos a enviar
     * @returns {Promise<Object>} Respuesta de la API
     */
    async post(endpoint, data = {}) {
        try {
            const response = await fetch(`${SENTINEL_CONFIG.API_URL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('[API POST] Error:', error);
            throw error;
        }
    },

    /**
     * Realiza una petición PUT
     * @param {string} endpoint - Endpoint de la API
     * @param {Object} data - Datos a enviar
     * @returns {Promise<Object>} Respuesta de la API
     */
    async put(endpoint, data = {}) {
        try {
            const response = await fetch(`${SENTINEL_CONFIG.API_URL}${endpoint}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('[API PUT] Error:', error);
            throw error;
        }
    },

    /**
     * Realiza una petición DELETE
     * @param {string} endpoint - Endpoint de la API
     * @returns {Promise<Object>} Respuesta de la API
     */
    async delete(endpoint) {
        try {
            const response = await fetch(`${SENTINEL_CONFIG.API_URL}${endpoint}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('[API DELETE] Error:', error);
            throw error;
        }
    },

    /**
     * Descarga un archivo
     * @param {string} endpoint - Endpoint de la API
     * @param {string} filename - Nombre del archivo
     */
    async download(endpoint, filename) {
        try {
            const response = await fetch(`${SENTINEL_CONFIG.API_URL}${endpoint}`);

            if (!response.ok) {
                throw new Error('Error descargando archivo');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (error) {
            console.error('[API DOWNLOAD] Error:', error);
            throw error;
        }
    },

    /**
     * Sube un archivo
     * @param {string} endpoint - Endpoint de la API
     * @param {FormData} formData - Datos del formulario
     * @returns {Promise<Object>} Respuesta de la API
     */
    async upload(endpoint, formData) {
        try {
            const response = await fetch(`${SENTINEL_CONFIG.API_URL}${endpoint}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error subiendo archivo');
            }

            return await response.json();
        } catch (error) {
            console.error('[API UPLOAD] Error:', error);
            throw error;
        }
    }
};

// =============================================================================
// FORMATEO DE FECHAS Y NÚMEROS
// =============================================================================

const Formatter = {
    /**
     * Formatea una fecha
     * @param {string|Date} date - Fecha
     * @param {boolean} includeTime - Incluir hora
     * @returns {string} Fecha formateada
     */
    date(date, includeTime = false) {
        const d = new Date(date);
        if (isNaN(d.getTime())) return 'Fecha inválida';

        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        };

        if (includeTime) {
            options.hour = '2-digit';
            options.minute = '2-digit';
            options.second = '2-digit';
        }

        return d.toLocaleDateString('es-ES', options);
    },

    /**
     * Formatea un número
     * @param {number} num - Número
     * @param {number} decimals - Decimales
     * @returns {string} Número formateado
     */
    number(num, decimals = 0) {
        if (num === null || num === undefined || isNaN(num)) return '---';
        return Number(num).toFixed(decimals);
    },

    /**
     * Formatea distancia en km
     * @param {number} km - Kilómetros
     * @returns {string} Distancia formateada
     */
    distance(km) {
        if (km === null || km === undefined || isNaN(km)) return '---';
        return `${this.number(km, 2)} km`;
    },

    /**
     * Formatea velocidad
     * @param {number} speed - Velocidad en km/h
     * @returns {string} Velocidad formateada
     */
    speed(speed) {
        if (speed === null || speed === undefined || isNaN(speed)) return '---';
        return `${Math.round(speed)} km/h`;
    },

    /**
     * Formatea duración en segundos
     * @param {number} seconds - Segundos
     * @returns {string} Duración formateada
     */
    duration(seconds) {
        if (seconds === null || seconds === undefined || isNaN(seconds)) return '---';

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    },

    /**
     * Formatea precio en euros
     * @param {number} price - Precio
     * @returns {string} Precio formateado
     */
    price(price) {
        if (price === null || price === undefined || isNaN(price)) return '---';
        return `${this.number(price, 2)}€`;
    },

    /**
     * Formatea porcentaje
     * @param {number} value - Valor
     * @returns {string} Porcentaje formateado
     */
    percentage(value) {
        if (value === null || value === undefined || isNaN(value)) return '---';
        return `${Math.round(value)}%`;
    }
};

// =============================================================================
// VALIDACIONES
// =============================================================================

const Validator = {
    /**
     * Valida email
     * @param {string} email - Email
     * @returns {boolean} True si es válido
     */
    email(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    /**
     * Valida VIN (17 caracteres)
     * @param {string} vin - VIN
     * @returns {boolean} True si es válido
     */
    vin(vin) {
        return /^[A-HJ-NPR-Z0-9]{17}$/.test(vin);
    },

    /**
     * Valida año de vehículo
     * @param {number} year - Año
     * @returns {boolean} True si es válido
     */
    year(year) {
        const currentYear = new Date().getFullYear();
        return year >= 1996 && year <= currentYear + 1;
    },

    /**
     * Valida que un campo no esté vacío
     * @param {*} value - Valor
     * @returns {boolean} True si no está vacío
     */
    required(value) {
        return value !== null && value !== undefined && value !== '';
    },

    /**
     * Valida número positivo
     * @param {number} value - Valor
     * @returns {boolean} True si es positivo
     */
    positive(value) {
        return !isNaN(value) && Number(value) > 0;
    }
};

// =============================================================================
// SISTEMA DE NOTIFICACIONES (TOASTS)
// =============================================================================

const Toast = {
    /**
     * Muestra una notificación
     * @param {string} message - Mensaje
     * @param {string} type - Tipo (success, error, warning, info)
     * @param {number} duration - Duración en ms
     */
    show(message, type = 'info', duration = 4000) {
        // Eliminar notificación existente
        const existing = document.querySelector('.sentinel-toast');
        if (existing) {
            existing.remove();
        }

        // Crear notificación
        const toast = document.createElement('div');
        toast.className = `sentinel-toast sentinel-toast-${type}`;

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        toast.innerHTML = `
            <i class="fas ${icons[type] || icons.info}"></i>
            <span>${message}</span>
        `;

        document.body.appendChild(toast);

        // Mostrar con animación
        setTimeout(() => toast.classList.add('show'), 10);

        // Ocultar y eliminar
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    success(message, duration = 4000) {
        this.show(message, 'success', duration);
    },

    error(message, duration = 4000) {
        this.show(message, 'error', duration);
    },

    warning(message, duration = 4000) {
        this.show(message, 'warning', duration);
    },

    info(message, duration = 4000) {
        this.show(message, 'info', duration);
    }
};

// =============================================================================
// LOADING SPINNER
// =============================================================================

const Loading = {
    /**
     * Muestra spinner de carga
     * @param {HTMLElement} element - Elemento donde mostrar el spinner
     * @param {string} message - Mensaje
     */
    show(element, message = 'Cargando...') {
        if (!element) return;

        const spinner = document.createElement('div');
        spinner.className = 'sentinel-loading';
        spinner.innerHTML = `
            <div class="spinner"></div>
            <p>${message}</p>
        `;

        element.innerHTML = '';
        element.appendChild(spinner);
    },

    /**
     * Oculta spinner de carga
     * @param {HTMLElement} element - Elemento
     */
    hide(element) {
        if (!element) return;
        const spinner = element.querySelector('.sentinel-loading');
        if (spinner) {
            spinner.remove();
        }
    }
};

// =============================================================================
// UTILIDADES GPS
// =============================================================================

const GPS = {
    /**
     * Obtiene la posición actual del usuario
     * @returns {Promise<Object>} Posición GPS
     */
    async getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocalización no soportada'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                position => resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    speed: position.coords.speed
                }),
                error => reject(error),
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0
                }
            );
        });
    },

    /**
     * Inicia el seguimiento GPS
     * @param {Function} callback - Función callback con la posición
     * @returns {number} ID del watch
     */
    watchPosition(callback) {
        if (!navigator.geolocation) {
            console.error('[GPS] Geolocalización no soportada');
            return null;
        }

        return navigator.geolocation.watchPosition(
            position => callback({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy,
                speed: position.coords.speed,
                timestamp: position.timestamp
            }),
            error => console.error('[GPS] Error:', error),
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );
    },

    /**
     * Detiene el seguimiento GPS
     * @param {number} watchId - ID del watch
     */
    clearWatch(watchId) {
        if (watchId && navigator.geolocation) {
            navigator.geolocation.clearWatch(watchId);
        }
    },

    /**
     * Calcula distancia entre dos puntos GPS (fórmula Haversine)
     * @param {number} lat1 - Latitud punto 1
     * @param {number} lon1 - Longitud punto 1
     * @param {number} lat2 - Latitud punto 2
     * @param {number} lon2 - Longitud punto 2
     * @returns {number} Distancia en kilómetros
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Radio de la Tierra en km
        const dLat = this._toRad(lat2 - lat1);
        const dLon = this._toRad(lon2 - lon1);
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(this._toRad(lat1)) * Math.cos(this._toRad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    },

    _toRad(degrees) {
        return degrees * (Math.PI / 180);
    }
};

// =============================================================================
// UTILIDADES DE SALUD DEL VEHÍCULO
// =============================================================================

const HealthUtils = {
    /**
     * Obtiene la clase CSS según el score de salud
     * @param {number} score - Score de salud (0-100)
     * @returns {string} Clase CSS
     */
    getHealthClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 60) return 'good';
        if (score >= 40) return 'warning';
        return 'critical';
    },

    /**
     * Obtiene el color según el score de salud
     * @param {number} score - Score de salud (0-100)
     * @returns {string} Color hexadecimal
     */
    getHealthColor(score) {
        if (score >= 80) return '#10b981';
        if (score >= 60) return '#3b82f6';
        if (score >= 40) return '#f59e0b';
        return '#ef4444';
    },

    /**
     * Obtiene el texto según el score de salud
     * @param {number} score - Score de salud (0-100)
     * @returns {string} Texto descriptivo
     */
    getHealthText(score) {
        if (score >= 80) return 'Excelente';
        if (score >= 60) return 'Bueno';
        if (score >= 40) return 'Atención';
        return 'Crítico';
    }
};

// =============================================================================
// NAVEGACIÓN
// =============================================================================

const Navigation = {
    /**
     * Navega a una página
     * @param {string} page - Nombre de la página
     */
    goto(page) {
        window.location.href = page;
    },

    /**
     * Actualiza los links de navegación activos
     * @param {string} currentPage - Página actual
     */
    updateActiveLinks(currentPage) {
        document.querySelectorAll('.nav-link').forEach(link => {
            if (link.getAttribute('href') === currentPage) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }
};

// =============================================================================
// DEBUGGING
// =============================================================================

const Debug = {
    /**
     * Log con timestamp
     * @param {string} message - Mensaje
     * @param {*} data - Datos adicionales
     */
    log(message, data = null) {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] ${message}`, data || '');
    },

    /**
     * Error con timestamp
     * @param {string} message - Mensaje
     * @param {Error} error - Error
     */
    error(message, error = null) {
        const timestamp = new Date().toISOString();
        console.error(`[${timestamp}] ${message}`, error || '');
    }
};

// Exportar para uso global
window.SENTINEL = {
    CONFIG: SENTINEL_CONFIG,
    Storage: StorageManager,
    ActiveVehicle,
    API,
    Formatter,
    Validator,
    Toast,
    Loading,
    GPS,
    HealthUtils,
    Navigation,
    Debug
};

// =============================================================================
// INICIALIZACIÓN DE NAVBAR (MARCAR PÁGINA ACTIVA)
// =============================================================================

// Marcar página activa en navbar
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage) {
            link.classList.add('active');
        }
    });

    // Mostrar link de vehicle-detail solo si hay un vehículo activo en localStorage
    const activeVehicleId = localStorage.getItem('activeVehicleId');
    if (activeVehicleId) {
        const vehicleDetailLink = document.getElementById('nav-vehicle-detail');
        if (vehicleDetailLink) {
            vehicleDetailLink.style.display = 'flex';
            vehicleDetailLink.href = `vehicle-detail.html?id=${activeVehicleId}`;
        }
    }

    // Mostrar link de importación solo si import.html existe
    fetch('import.html', {method: 'HEAD'})
        .then(res => {
            if (res.ok) {
                const importLink = document.getElementById('nav-import');
                if (importLink) {
                    importLink.style.display = 'flex';
                }
            }
        })
        .catch(() => {});
});

console.log('[SENTINEL COMMON] ✓ Módulo cargado correctamente');
