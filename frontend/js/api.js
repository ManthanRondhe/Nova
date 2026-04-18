/**
 * AutoMech AI - API Client
 * Handles all communication with the FastAPI backend
 */
// TODO: To deploy, change this URL to your Render backend URL (e.g. 'https://automech-backend.onrender.com/api')
// Automatically use the current hostname if deployed, otherwise fallback to local backend for testing
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
// IMPORTANT: Replace this placeholder with your actual Render URL later!
const RENDER_BACKEND_URL = 'https://your-automech-backend-url.onrender.com';
const API_BASE = isLocalhost ? 'http://localhost:8000/api' : `${RENDER_BACKEND_URL}/api`;



const api = {
    async request(endpoint, options = {}) {
        try {
            const url = `${API_BASE}${endpoint}`;
            const config = {
                headers: { 'Content-Type': 'application/json' },
                ...options,
            };
            if (config.body && typeof config.body === 'object') {
                config.body = JSON.stringify(config.body);
            }
            const response = await fetch(url, config);
            if (!response.ok) throw new Error(`API Error: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // Dashboard
    getDashboard: () => api.request('/dashboard'),

    // Diagnosis
    diagnose: (query, vehicleType, vehicleModel) =>
        api.request('/diagnose', { method: 'POST', body: { query, vehicle_type: vehicleType, vehicle_model: vehicleModel } }),

    // Voice
    processVoice: (text, context = []) =>
        api.request('/voice/process', { method: 'POST', body: { text, context } }),

    // Job Cards
    getJobCards: (status) => api.request(`/jobcards${status ? `?status=${status}` : ''}`),
    createJobCard: (data) => api.request('/jobcards', { method: 'POST', body: data }),
    updateJobCard: (id, data) => api.request(`/jobcards/${id}`, { method: 'PUT', body: data }),
    completeJobCard: (id, actualCost) => api.request(`/jobcards/${id}/complete`, { method: 'PUT', body: { actual_cost: actualCost } }),
    deleteJobCard: (id) => api.request(`/jobcards/${id}`, { method: 'DELETE' }),

    // Mechanics
    getMechanics: () => api.request('/mechanics'),
    addMechanic: (data) => api.request('/mechanics', { method: 'POST', body: data }),
    updateMechanic: (id, data) => api.request(`/mechanics/${id}`, { method: 'PUT', body: data }),
    deleteMechanic: (id) => api.request(`/mechanics/${id}`, { method: 'DELETE' }),
    setMechanicStatus: (id, status) => api.request(`/mechanics/${id}/status`, { method: 'PUT', body: { status } }),

    // Inventory
    getInventory: () => api.request('/inventory'),
    getInventoryAlerts: () => api.request('/inventory/alerts'),
    searchInventory: (query) => api.request(`/inventory/search/${encodeURIComponent(query)}`),
    addStock: (partId, quantity) => api.request(`/inventory/${partId}/add`, { method: 'PUT', body: { quantity } }),
    getPartsCatalog: () => api.request('/parts'),

    // Dealers
    getDealers: () => api.request('/dealers'),
    addDealer: (data) => api.request('/dealers', { method: 'POST', body: data }),
    updateDealer: (id, data) => api.request(`/dealers/${id}`, { method: 'PUT', body: data }),
    deleteDealer: (id) => api.request(`/dealers/${id}`, { method: 'DELETE' }),

    // Orders
    getOrders: (status) => api.request(`/orders${status ? `?status=${status}` : ''}`),
    updateOrderStatus: (id, status) => api.request(`/orders/${id}/status`, { method: 'PUT', body: { status } }),

    // Pipeline
    getPipeline: () => api.request('/pipeline'),
    getWorkload: () => api.request('/pipeline/workload'),
    updatePipelineStatus: (id, status, mechanicId) => api.request(`/pipeline/${id}/status`, { method: 'PUT', body: { status, mechanic_id: mechanicId } }),

    // Estimates
    getEstimate: (query) => api.request('/estimate', { method: 'POST', body: { query } }),

    // Notifications
    getNotifications: () => api.request('/notifications'),
    getTelegramStatus: () => api.request('/telegram/status'),
};
