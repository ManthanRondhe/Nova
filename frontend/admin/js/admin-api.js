/**
 * AutoMech AI — Admin API Client
 */
// Automatically use the current hostname if deployed, otherwise fallback to local backend for testing
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
// IMPORTANT: Replace this placeholder with your actual Render URL later!
const RENDER_BACKEND_URL = 'https://nova-backend-ftga.onrender.com';
const API_BASE = isLocalhost ? 'http://localhost:8000/api/admin' : `${RENDER_BACKEND_URL}/api/admin`;

const adminApi = {
    BASE: API_BASE,

    async _fetch(path, options = {}) {
        const res = await fetch(`${this.BASE}${path}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        return res.json();
    },

    // Auth
    login(password) { return this._fetch('/login', { method: 'POST', body: JSON.stringify({ password }) }); },

    // Dashboard
    getDashboard() { return this._fetch('/dashboard'); },

    // Attendance
    getAttendance(date, mechanic_id) {
        const params = new URLSearchParams();
        if (date) params.set('date', date);
        if (mechanic_id) params.set('mechanic_id', mechanic_id);
        const q = params.toString();
        return this._fetch(`/attendance${q ? '?' + q : ''}`);
    },
    markAttendance(data) { return this._fetch('/attendance', { method: 'POST', body: JSON.stringify(data) }); },
    getMonthlyAttendance(mechanic_id, month, year) {
        const params = new URLSearchParams();
        if (month) params.set('month', month);
        if (year) params.set('year', year);
        return this._fetch(`/attendance/monthly/${mechanic_id}?${params}`);
    },

    // Salaries
    getSalaries(month, year, mechanic_id) {
        const params = new URLSearchParams();
        if (month) params.set('month', month);
        if (year) params.set('year', year);
        if (mechanic_id) params.set('mechanic_id', mechanic_id);
        return this._fetch(`/salaries?${params}`);
    },
    createSalary(data) { return this._fetch('/salaries', { method: 'POST', body: JSON.stringify(data) }); },
    paySalary(id) { return this._fetch(`/salaries/${id}/pay`, { method: 'PUT' }); },
    getSalarySummary() { return this._fetch('/salaries/summary'); },
    checkSalaryReminder() { return this._fetch('/salaries/reminder'); },

    // Performance
    getPerformance() { return this._fetch('/performance'); },
    getMechanicPerformance(id) { return this._fetch(`/performance/${id}`); },
    getMechanicOfMonth(month, year) {
        const params = new URLSearchParams();
        if (month) params.set('month', month);
        if (year) params.set('year', year);
        return this._fetch(`/mechanic-of-month?${params}`);
    },
    getEmployeeOfYear(year) {
        const params = year ? `?year=${year}` : '';
        return this._fetch(`/employee-of-year${params}`);
    },

    // Live Status
    getLiveStatus() { return this._fetch('/live-status'); },

    // Insurance
    getInsurance(status) {
        const q = status ? `?status=${status}` : '';
        return this._fetch(`/insurance${q}`);
    },
    addInsurance(data) { return this._fetch('/insurance', { method: 'POST', body: JSON.stringify(data) }); },
    updateInsurance(id, data) { return this._fetch(`/insurance/${id}`, { method: 'PUT', body: JSON.stringify(data) }); },
    deleteInsurance(id) { return this._fetch(`/insurance/${id}`, { method: 'DELETE' }); },
    getExpiringInsurance(days = 30) { return this._fetch(`/insurance/expiring?days=${days}`); },

    // Mechanics (from main API)
    getMechanics() { return fetch('/api/mechanics').then(r => r.json()); },
};
