/**
 * Nova AI - Main Application Controller
 * Wires voice engine, API, and UI together
 */
document.addEventListener('DOMContentLoaded', () => {
    const voice = new VoiceEngine();
    let currentPage = 'dashboard';
    let chatContext = [];

    // ━━━ DOM References ━━━
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const voiceBtn = $('#voice-btn');
    const voicePanel = $('#voice-panel');
    const voiceConvo = $('#voice-conversation');
    const voiceTextInput = $('#voice-text-input');
    const voiceSendBtn = $('#voice-send-btn');
    const voiceStatusEl = $('#voice-status');
    const breadcrumb = $('#breadcrumb');
    const sidebarToggle = $('#sidebar-toggle');
    const sidebar = $('#sidebar');

    // ━━━ Toast System ━━━
    function toast(message, type = 'info') {
        const container = $('#toast-container');
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        t.textContent = message;
        container.appendChild(t);
        setTimeout(() => t.remove(), 4500);
    }

    // ━━━ Modal System ━━━
    function openModal(title, bodyHTML, footerHTML = '') {
        $('#modal-title').textContent = title;
        $('#modal-body').innerHTML = bodyHTML;
        $('#modal-footer').innerHTML = footerHTML;
        $('#modal-overlay').classList.remove('hidden');
    }
    function closeModal() { $('#modal-overlay').classList.add('hidden'); }
    $('#modal-close').addEventListener('click', closeModal);
    $('#modal-overlay').addEventListener('click', (e) => { if (e.target.id === 'modal-overlay') closeModal(); });

    // ━━━ Navigation ━━━
    $$('.nav-links li').forEach(li => {
        li.addEventListener('click', () => {
            const page = li.dataset.page;
            if (page) navigateTo(page);
        });
    });

    function navigateTo(page) {
        currentPage = page;
        $$('.nav-links li').forEach(l => l.classList.toggle('active', l.dataset.page === page));
        $$('.page').forEach(p => p.classList.toggle('active', p.id === `page-${page}`));
        breadcrumb.textContent = page.charAt(0).toUpperCase() + page.slice(1);
        loadPageData(page);
        if (window.innerWidth <= 768) sidebar.classList.remove('open');
    }

    sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));

    // ━━━ Voice Engine ━━━
    voice.onStart = () => {
        voiceBtn.classList.add('listening');
        voiceStatusEl.classList.add('listening');
        voiceStatusEl.querySelector('.status-text').textContent = 'Listening...';
        voicePanel.classList.remove('hidden');
        voicePanel.classList.add('visible');
    };

    voice.onEnd = () => {
        voiceBtn.classList.remove('listening');
        voiceStatusEl.classList.remove('listening');
        voiceStatusEl.querySelector('.status-text').textContent = 'Click mic to speak';
    };

    voice.onError = (error) => {
        if (error === 'not-supported') toast('Voice not supported. Use Chrome or Edge.', 'error');
        else if (error === 'not-allowed') toast('Microphone access denied. Please allow mic access.', 'error');
        else if (error === 'network') toast('Microphone network error. If on Brave, enable Google Services in settings.', 'error');
        else if (error !== 'no-speech') toast(`Voice error: ${error}`, 'error');
    };

    voice.onResult = (text, isFinal) => {
        if (isFinal) {
            addVoiceMessage(text, 'user');
            processVoiceCommand(text);
        }
    };

    voiceBtn.addEventListener('click', () => {
        voice.toggle();
        voicePanel.classList.remove('hidden');
        voicePanel.classList.add('visible');
    });

    voiceSendBtn.addEventListener('click', sendTextInput);
    voiceTextInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendTextInput(); });

    function sendTextInput() {
        const text = voiceTextInput.value.trim();
        if (!text) return;
        voiceTextInput.value = '';
        voicePanel.classList.remove('hidden');
        voicePanel.classList.add('visible');
        addVoiceMessage(text, 'user');
        processVoiceCommand(text);
    }

    function addVoiceMessage(text, role) {
        const msg = document.createElement('div');
        msg.className = `voice-msg ${role}`;
        msg.textContent = text;
        voiceConvo.appendChild(msg);
        voiceConvo.scrollTop = voiceConvo.scrollHeight;

        if (role === 'user' || role === 'assistant') {
            chatContext.push({role: role, text: text});
            if (chatContext.length > 6) chatContext.shift();
        }
    }

    async function processVoiceCommand(text) {
        try {
            const result = await api.processVoice(text, chatContext);
            addVoiceMessage(result.response, 'assistant');
            
            // Speak and auto-resume listening if it asks a question
            voice.speak(result.response, () => {
                const text = result.response;
                if (text.includes('?') || text.toLowerCase().includes('what would you like to do')) {
                    // Slight delay to ensure mic becomes available
                    setTimeout(() => voice.start(), 300);
                }
            });

            // Navigate based on action
            const actionPageMap = { diagnosis: 'diagnosis', create_jobcard: 'jobcards', inventory: 'inventory', mechanics: 'mechanics', estimate: 'diagnosis', orders: 'dealers', pipeline: 'pipeline', dashboard: 'dashboard' };
            if (actionPageMap[result.action]) navigateTo(actionPageMap[result.action]);

            // Populate data
            if (result.action === 'diagnosis' && result.data?.results) renderDiagnosisResults(result.data.results, result.data.estimate);
        } catch (err) {
            addVoiceMessage('Sorry, I encountered an error. Please try again.', 'assistant');
            toast('Failed to process command', 'error');
        }
    }

    // ━━━ Page Data Loading ━━━
    function loadPageData(page) {
        const loaders = { dashboard: loadDashboard, diagnosis: loadDiagnosis, jobcards: loadJobCards, mechanics: loadMechanics, inventory: loadInventory, dealers: loadDealers, pipeline: loadPipeline, notifications: loadNotifications };
        if (loaders[page]) loaders[page]();
    }

    // ━━━ DASHBOARD ━━━
    async function loadDashboard() {
        try {
            const data = await api.getDashboard();
            const jc = data.jobcards || {};
            const inv = data.inventory || {};
            const mech = data.mechanics || {};
            const ord = data.orders || {};

            $('#dashboard-stats').innerHTML = `
                <div class="stat-card"><div class="stat-icon blue">&#128203;</div><div class="stat-info"><div class="stat-value">${jc.total || 0}</div><div class="stat-label">Total Job Cards</div></div></div>
                <div class="stat-card"><div class="stat-icon orange">&#9881;</div><div class="stat-info"><div class="stat-value">${jc.in_progress || 0}</div><div class="stat-label">In Progress</div></div></div>
                <div class="stat-card"><div class="stat-icon green">&#9989;</div><div class="stat-info"><div class="stat-value">${mech.available || 0}/${mech.total || 0}</div><div class="stat-label">Mechanics Available</div></div></div>
                <div class="stat-card"><div class="stat-icon red">&#9888;</div><div class="stat-info"><div class="stat-value">${inv.low_stock_count || 0}</div><div class="stat-label">Low Stock Alerts</div></div></div>
                <div class="stat-card"><div class="stat-icon purple">&#128230;</div><div class="stat-info"><div class="stat-value">${ord.pending || 0}</div><div class="stat-label">Pending Orders</div></div></div>
            `;

            // Telegram status
            const tgDot = $('#telegram-status .status-dot');
            const tgText = $('#telegram-status span');
            if (data.telegram?.status === 'connected') { tgDot.className = 'status-dot connected'; tgText.textContent = `Telegram: ${data.telegram.bot?.first_name || 'Connected'}`; }
            else { tgDot.className = 'status-dot'; tgText.textContent = 'Telegram: Not configured'; }

            // Recent job cards
            const jcData = await api.getJobCards();
            const recent = (jcData.jobcards || []).slice(-5).reverse();
            $('#recent-jobcards').innerHTML = recent.length ? recent.map(j => `
                <div class="flex-between" style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                    <div><span class="text-mono text-accent">${j.jobcard_id}</span> <span style="margin-left:8px">${j.vehicle_make} ${j.vehicle_model}</span></div>
                    <span class="badge-status ${(j.status||'').toLowerCase().replace(' ','-')}">${j.status}</span>
                </div>
            `).join('') : '<div class="empty-state"><div class="empty-state-icon">&#128203;</div><div class="empty-state-text">No job cards yet</div></div>';

            // Low stock
            const alerts = await api.getInventoryAlerts();
            const lowStock = alerts.alerts || [];
            $('#low-stock-alerts').innerHTML = lowStock.length ? lowStock.slice(0, 5).map(a => `
                <div class="flex-between" style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                    <span>${a.part_name}</span>
                    <span class="badge-status low-stock">Stock: ${a.current_stock}</span>
                </div>
            `).join('') : '<div class="empty-state"><div class="empty-state-text">All stock levels OK</div></div>';

            // Mechanic status
            const mechData = await api.getMechanics();
            const mechs = mechData.mechanics || [];
            $('#mechanic-status-overview').innerHTML = mechs.length ? mechs.map(m => `
                <div class="flex-between" style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                    <span>${m.name} <span class="text-muted">(${m.specialization})</span></span>
                    <span class="badge-status ${(m.status||'').toLowerCase().replace(' ','-')}">${m.status}</span>
                </div>
            `).join('') : '<div class="empty-state"><div class="empty-state-text">No mechanics added yet. Add mechanics to get started!</div></div>';

        } catch (err) { console.error('Dashboard error:', err); toast('Failed to load dashboard', 'error'); }
    }

    // ━━━ DIAGNOSIS ━━━
    function loadDiagnosis() {}

    $('#diagnose-btn').addEventListener('click', async () => {
        const query = $('#diagnosis-input').value.trim();
        if (!query) { toast('Please describe the problem', 'warning'); return; }
        $('#diagnose-btn').disabled = true;
        $('#diagnose-btn').textContent = 'Analyzing...';
        try {
            const vtype = $('#diag-vehicle-type').value;
            const vmodel = $('#diag-vehicle-model').value;
            const result = await api.diagnose(query, vtype, vmodel);
            renderDiagnosisResults(result.results, result.top_estimate);
            toast(`Found ${result.total_matches} potential faults`, 'success');
        } catch (err) { toast('Diagnosis failed', 'error'); }
        finally { $('#diagnose-btn').disabled = false; $('#diagnose-btn').innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>Run Diagnosis'; }
    });

    function renderDiagnosisResults(results, estimate) {
        if (!results || !results.length) {
            $('#diagnosis-results').innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#128269;</div><div class="empty-state-text">No matching faults found. Try describing the symptoms differently.</div></div>';
            return;
        }
        $('#diagnosis-results').innerHTML = results.map((r, i) => {
            const confPct = Math.round((r.confidence || 0) * 100);
            const dashOffset = 188.5 - (188.5 * confPct / 100);
            const confColor = confPct >= 80 ? 'var(--success)' : confPct >= 60 ? 'var(--warning)' : 'var(--danger)';
            return `
            <div class="diagnosis-result ${i === 0 ? 'top-result' : ''}">
                <div class="diag-header">
                    <div><div class="diag-fault-name">${r.fault_name}</div><div class="diag-system">${r.system} | ${r.vehicle_type} | ${r.severity}</div></div>
                    <div class="confidence-gauge">
                        <svg viewBox="0 0 64 64"><circle class="bg" cx="32" cy="32" r="30"/><circle class="fill" cx="32" cy="32" r="30" style="stroke:${confColor};stroke-dashoffset:${dashOffset}"/></svg>
                        <span class="confidence-value" style="color:${confColor}">${confPct}%</span>
                    </div>
                </div>
                <div class="diag-details">
                    <div class="diag-detail"><span class="diag-detail-label">OBD Code</span><span class="diag-detail-value text-mono">${r.obd_code || 'N/A'}</span></div>
                    <div class="diag-detail"><span class="diag-detail-label">Est. Time</span><span class="diag-detail-value">${r.estimated_time_hours || '?'} hours</span></div>
                    <div class="diag-detail"><span class="diag-detail-label">Est. Cost</span><span class="diag-detail-value">Rs ${r.estimated_cost_range || 'N/A'}</span></div>
                    <div class="diag-detail"><span class="diag-detail-label">Parts Needed</span><span class="diag-detail-value">${r.required_parts || 'None'}</span></div>
                    <div class="diag-detail"><span class="diag-detail-label">Common In</span><span class="diag-detail-value">${r.common_vehicles || 'Various'}</span></div>
                    <div class="diag-detail"><span class="diag-detail-label">Matched Symptom</span><span class="diag-detail-value text-muted">${r.matched_symptom || ''}</span></div>
                </div>
                ${r.fix_procedure ? `<div class="diag-fix"><div class="diag-fix-title">Repair Procedure</div><div class="diag-fix-text">${r.fix_procedure}</div></div>` : ''}
            </div>`;
        }).join('');
    }

    // ━━━ JOB CARDS ━━━
    async function loadJobCards(statusFilter) {
        try {
            const data = await api.getJobCards(statusFilter);
            const jcs = data.jobcards || [];
            if (!jcs.length) {
                $('#jobcards-table').innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#128203;</div><div class="empty-state-text">No job cards found</div></div>';
                return;
            }
            $('#jobcards-table').innerHTML = `<table><thead><tr><th>ID</th><th>Vehicle</th><th>Owner</th><th>Complaint</th><th>Mechanic</th><th>Status</th><th>Priority</th><th>Actions</th></tr></thead><tbody>
            ${jcs.reverse().map(j => `<tr>
                <td class="text-mono text-accent">${j.jobcard_id}</td>
                <td>${j.vehicle_make} ${j.vehicle_model} ${j.vehicle_year}</td>
                <td>${j.owner_name || '-'}</td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${j.complaint || ''}">${j.complaint || '-'}</td>
                <td>${j.assigned_mechanic_name || '<span class="text-muted">Unassigned</span>'}</td>
                <td><span class="badge-status ${(j.status||'').toLowerCase().replace(' ','-')}">${j.status}</span></td>
                <td><span class="badge-status ${(j.priority||'').toLowerCase()}">${j.priority}</span></td>
                <td>
                    ${j.status !== 'Completed' ? `<button class="btn btn-success btn-xs" onclick="window.appCompleteJC('${j.jobcard_id}')">Complete</button>` : ''}
                    <button class="btn btn-danger btn-xs" onclick="window.appDeleteJC('${j.jobcard_id}')">Del</button>
                </td>
            </tr>`).join('')}</tbody></table>`;
        } catch (err) { toast('Failed to load job cards', 'error'); }
    }

    // Job card filter chips
    $$('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            $$('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const filter = chip.dataset.filter;
            loadJobCards(filter === 'all' ? null : filter);
        });
    });

    // New Job Card
    $('#new-jobcard-btn').addEventListener('click', () => {
        openModal('Create New Job Card', `
            <div class="form-row"><div class="form-group"><label>Vehicle Make</label><input id="jc-make" placeholder="e.g. Maruti, Hyundai"></div><div class="form-group"><label>Vehicle Model</label><input id="jc-model" placeholder="e.g. Swift, Creta"></div></div>
            <div class="form-row"><div class="form-group"><label>Vehicle Year</label><input id="jc-year" placeholder="e.g. 2022"></div><div class="form-group"><label>Registration No.</label><input id="jc-reg" placeholder="e.g. MH-12-AB-1234"></div></div>
            <div class="form-row"><div class="form-group"><label>Owner Name</label><input id="jc-owner" placeholder="Full name"></div><div class="form-group"><label>Owner Phone</label><input id="jc-phone" placeholder="10-digit number"></div></div>
            <div class="form-group"><label>Complaint / Symptoms</label><textarea id="jc-complaint" rows="3" placeholder="Describe the problem..."></textarea></div>
        `, `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').classList.add('hidden')">Cancel</button>
            <button class="btn btn-primary" id="jc-submit-btn">Create Job Card</button>`);

        document.getElementById('jc-submit-btn').addEventListener('click', async () => {
            const data = {
                vehicle_make: $('#jc-make').value, vehicle_model: $('#jc-model').value,
                vehicle_year: $('#jc-year').value, vehicle_reg: $('#jc-reg').value,
                owner_name: $('#jc-owner').value, owner_phone: $('#jc-phone').value,
                complaint: $('#jc-complaint').value
            };
            if (!data.vehicle_make || !data.complaint) { toast('Vehicle make and complaint are required', 'warning'); return; }
            try {
                const result = await api.createJobCard(data);
                closeModal();
                toast(result.message, 'success');
                loadJobCards();
                if (result.assigned_mechanic) toast(`Mechanic: ${result.assigned_mechanic.name}`, 'info');
                if (result.diagnosis) toast(`Diagnosis: ${result.diagnosis.fault_name} (${Math.round(result.diagnosis.confidence*100)}%)`, 'info');
                if (result.orders_created?.length) toast(`${result.orders_created.length} part(s) auto-ordered`, 'warning');
            } catch (err) { toast('Failed to create job card', 'error'); }
        });
    });

    window.appCompleteJC = async (id) => { try { await api.completeJobCard(id); toast(`${id} completed!`, 'success'); loadJobCards(); } catch(e) { toast('Error', 'error'); } };
    window.appDeleteJC = async (id) => { if (confirm(`Delete ${id}?`)) { try { await api.deleteJobCard(id); toast(`${id} deleted`, 'info'); loadJobCards(); } catch(e) { toast('Error', 'error'); } } };

    // ━━━ MECHANICS ━━━
    async function loadMechanics() {
        try {
            const data = await api.getMechanics();
            const mechs = data.mechanics || [];
            if (!mechs.length) {
                $('#mechanics-grid').innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-state-icon">&#128104;&#8205;&#128295;</div><div class="empty-state-text">No mechanics added yet. Add your team to get started!</div></div>';
                return;
            }
            $('#mechanics-grid').innerHTML = mechs.map(m => `
                <div class="mechanic-card">
                    <div class="mechanic-header">
                        <div class="mechanic-avatar">${(m.name||'?')[0].toUpperCase()}</div>
                        <div><div class="mechanic-name">${m.name}</div><div class="mechanic-spec">${m.specialization} | ${m.skill_level}</div></div>
                        <span class="badge-status ${(m.status||'').toLowerCase().replace(' ','-')}" style="margin-left:auto">${m.status}</span>
                    </div>
                    <div class="mechanic-stats">
                        <div class="mechanic-stat-item"><div class="mechanic-stat-num">${m.current_jobs || 0}</div><div class="mechanic-stat-label">Active Jobs</div></div>
                        <div class="mechanic-stat-item"><div class="mechanic-stat-num">${m.phone || '-'}</div><div class="mechanic-stat-label">Phone</div></div>
                        <div class="mechanic-stat-item"><div class="mechanic-stat-num">${m.telegram_chat_id ? 'Yes' : 'No'}</div><div class="mechanic-stat-label">Telegram</div></div>
                    </div>
                    <div class="mechanic-actions">
                        <button class="btn btn-secondary btn-xs" onclick="window.appToggleMechStatus('${m.mechanic_id}', '${m.status}')">${m.status === 'Available' ? 'Set Busy' : 'Set Available'}</button>
                        <button class="btn btn-danger btn-xs" onclick="window.appDeleteMech('${m.mechanic_id}')">Remove</button>
                    </div>
                </div>
            `).join('');
        } catch (err) { toast('Failed to load mechanics', 'error'); }
    }

    $('#add-mechanic-btn').addEventListener('click', () => {
        openModal('Add Mechanic', `
            <div class="form-row"><div class="form-group"><label>Name</label><input id="mech-name" placeholder="Full name"></div><div class="form-group"><label>Phone</label><input id="mech-phone" placeholder="Phone number"></div></div>
            <div class="form-row"><div class="form-group"><label>Specialization</label><select id="mech-spec"><option>General</option><option>Engine</option><option>Electrical</option><option>Transmission</option><option>Brakes</option><option>Suspension</option><option>AC/HVAC</option><option>Body</option><option>Bike</option></select></div><div class="form-group"><label>Skill Level</label><select id="mech-skill"><option>Senior</option><option>Expert</option><option>Junior</option></select></div></div>
            <div class="form-group"><label>Telegram Chat ID <span class="text-muted">(optional - send /start to your bot first)</span></label><input id="mech-telegram" placeholder="e.g. 123456789"></div>
        `, `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').classList.add('hidden')">Cancel</button>
            <button class="btn btn-primary" id="mech-submit">Add Mechanic</button>`);

        document.getElementById('mech-submit').addEventListener('click', async () => {
            const data = { name: $('#mech-name').value, phone: $('#mech-phone').value, specialization: $('#mech-spec').value, skill_level: $('#mech-skill').value, telegram_chat_id: $('#mech-telegram').value };
            if (!data.name) { toast('Name is required', 'warning'); return; }
            try { await api.addMechanic(data); closeModal(); toast(`${data.name} added!`, 'success'); loadMechanics(); } catch(e) { toast('Error', 'error'); }
        });
    });

    window.appToggleMechStatus = async (id, current) => { try { await api.setMechanicStatus(id, current === 'Available' ? 'Busy' : 'Available'); loadMechanics(); } catch(e) { toast('Error','error'); } };
    window.appDeleteMech = async (id) => { if (confirm('Remove mechanic?')) { try { await api.deleteMechanic(id); toast('Removed', 'info'); loadMechanics(); } catch(e) { toast('Error','error'); } } };

    // ━━━ INVENTORY ━━━
    async function loadInventory(searchQuery) {
        try {
            let items;
            if (searchQuery) { const data = await api.searchInventory(searchQuery); items = data.results || []; }
            else { const data = await api.getInventory(); items = data.inventory || []; }

            if (!items.length) { $('#inventory-table').innerHTML = '<div class="empty-state"><div class="empty-state-text">No parts found</div></div>'; return; }

            $('#inventory-table').innerHTML = `<table><thead><tr><th>Part ID</th><th>Name</th><th>Category</th><th>Stock</th><th>Min Level</th><th>Price (Rs)</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            ${items.map(p => {
                const stock = parseInt(p.current_stock || 0);
                const min = parseInt(p.min_stock_level || 0);
                const pct = min > 0 ? Math.min(100, (stock / (min * 2)) * 100) : 100;
                const barClass = stock <= 0 ? 'empty' : stock <= min ? 'low' : 'good';
                const statusClass = stock <= 0 ? 'low-stock' : stock <= min ? 'urgent' : 'in-stock';
                const statusText = stock <= 0 ? 'Out' : stock <= min ? 'Low' : 'OK';
                return `<tr>
                    <td class="text-mono">${p.part_id}</td><td>${p.part_name}</td><td>${p.category}</td>
                    <td>${stock} <div class="stock-bar"><div class="stock-bar-fill ${barClass}" style="width:${pct}%"></div></div></td>
                    <td>${min}</td><td>${parseInt(p.unit_price || 0).toLocaleString()}</td>
                    <td><span class="badge-status ${statusClass}">${statusText}</span></td>
                    <td><button class="btn btn-secondary btn-xs" onclick="window.appAddStock('${p.part_id}','${p.part_name}')">+ Stock</button></td>
                </tr>`;
            }).join('')}</tbody></table>`;
        } catch (err) { toast('Failed to load inventory', 'error'); }
    }

    let searchTimeout;
    $('#inventory-search').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadInventory(e.target.value.trim()), 300);
    });

    window.appAddStock = (partId, partName) => {
        const qty = prompt(`Add stock for ${partName}. Enter quantity:`);
        if (qty && parseInt(qty) > 0) {
            api.addStock(partId, parseInt(qty)).then(() => { toast(`Added ${qty} units of ${partName}`, 'success'); loadInventory(); }).catch(() => toast('Error', 'error'));
        }
    };

    // ━━━ DEALERS ━━━
    async function loadDealers() {
        try {
            const data = await api.getDealers();
            const dealers = data.dealers || [];
            if (!dealers.length) {
                $('#dealers-grid').innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-state-icon">&#127978;</div><div class="empty-state-text">No dealers added yet</div></div>';
                return;
            }
            $('#dealers-grid').innerHTML = dealers.map(d => `
                <div class="dealer-card">
                    <div class="dealer-info-row"><div class="dealer-name">${d.name}</div><div class="dealer-rating">${'&#9733;'.repeat(parseInt(d.rating||3))}</div></div>
                    <div class="dealer-detail">Phone: ${d.phone || '-'}</div>
                    <div class="dealer-detail">Email: ${d.email || '-'}</div>
                    <div class="dealer-detail">Category: ${d.parts_category || 'General'}</div>
                    <div class="dealer-detail">Location: ${d.location || '-'}</div>
                    <div class="dealer-detail">Delivery: ${d.delivery_time_days || '?'} days</div>
                    <div class="dealer-detail">Telegram: ${d.telegram_chat_id ? 'Connected' : 'Not set'}</div>
                    <div class="dealer-actions">
                        <button class="btn btn-danger btn-xs" onclick="window.appDeleteDealer('${d.dealer_id}')">Remove</button>
                    </div>
                </div>
            `).join('');
        } catch (err) { toast('Failed to load dealers', 'error'); }
    }

    $('#add-dealer-btn').addEventListener('click', () => {
        openModal('Add Spare Part Dealer', `
            <div class="form-row"><div class="form-group"><label>Dealer Name</label><input id="dlr-name" placeholder="Shop/dealer name"></div><div class="form-group"><label>Phone</label><input id="dlr-phone" placeholder="Phone number"></div></div>
            <div class="form-row"><div class="form-group"><label>Email</label><input id="dlr-email" placeholder="email@example.com"></div><div class="form-group"><label>Location</label><input id="dlr-location" placeholder="City/Area"></div></div>
            <div class="form-row"><div class="form-group"><label>Parts Category</label><select id="dlr-category"><option>General</option><option>Engine</option><option>Electrical</option><option>Brakes</option><option>Suspension</option><option>Cooling</option><option>AC</option><option>Body</option><option>Bike</option><option>Truck</option><option>Fluids</option><option>Filters</option></select></div><div class="form-group"><label>Avg Delivery (days)</label><input id="dlr-delivery" type="number" value="2" min="1"></div></div>
            <div class="form-row"><div class="form-group"><label>Rating (1-5)</label><input id="dlr-rating" type="number" value="4" min="1" max="5"></div><div class="form-group"><label>Telegram Chat ID</label><input id="dlr-telegram" placeholder="optional"></div></div>
        `, `<button class="btn btn-secondary" onclick="document.querySelector('#modal-overlay').classList.add('hidden')">Cancel</button>
            <button class="btn btn-primary" id="dlr-submit">Add Dealer</button>`);

        document.getElementById('dlr-submit').addEventListener('click', async () => {
            const data = { name: $('#dlr-name').value, phone: $('#dlr-phone').value, email: $('#dlr-email').value, location: $('#dlr-location').value, parts_category: $('#dlr-category').value, delivery_time_days: $('#dlr-delivery').value, rating: $('#dlr-rating').value, telegram_chat_id: $('#dlr-telegram').value };
            if (!data.name) { toast('Name is required', 'warning'); return; }
            try { await api.addDealer(data); closeModal(); toast(`${data.name} added!`, 'success'); loadDealers(); } catch(e) { toast('Error', 'error'); }
        });
    });

    window.appDeleteDealer = async (id) => { if (confirm('Remove dealer?')) { try { await api.deleteDealer(id); toast('Removed', 'info'); loadDealers(); } catch(e) { toast('Error','error'); } } };

    // ━━━ PIPELINE ━━━
    async function loadPipeline() {
        try {
            const data = await api.getWorkload();
            const workload = data.workload || [];
            if (!workload.length) { $('#pipeline-container').innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#128200;</div><div class="empty-state-text">No mechanics in pipeline. Add mechanics and create job cards to see workflow.</div></div>'; return; }

            $('#pipeline-container').innerHTML = workload.map(w => `
                <div class="pipeline-mechanic">
                    <div class="pipeline-mechanic-header">
                        <div><strong>${w.name}</strong> <span class="text-muted">(${w.specialization})</span></div>
                        <div class="inline-flex">
                            <span class="badge-status ${w.status.toLowerCase().replace(' ','-')}">${w.status}</span>
                            <span class="text-muted">${w.active_tasks} task(s)</span>
                        </div>
                    </div>
                    ${w.tasks.length ? `<div class="pipeline-tasks">${w.tasks.map(t => `
                        <div class="pipeline-task">
                            <div class="pipeline-task-info">
                                <span class="pipeline-task-id">${t.jobcard_id}</span>
                                <span class="pipeline-task-desc">${t.task_description}</span>
                            </div>
                            <div class="inline-flex">
                                <span class="badge-status ${(t.priority||'').toLowerCase()}">${t.priority}</span>
                                <span class="badge-status ${(t.status||'').toLowerCase()}">${t.status}</span>
                                ${t.status !== 'Done' ? `<button class="btn btn-success btn-xs" onclick="window.appCompletePipeline('${t.pipeline_id}','${w.mechanic_id}')">Done</button>` : ''}
                            </div>
                        </div>
                    `).join('')}</div>` : '<div class="pipeline-empty">No active tasks</div>'}
                </div>
            `).join('');
        } catch (err) { toast('Failed to load pipeline', 'error'); }
    }

    window.appCompletePipeline = async (pid, mid) => { try { await api.updatePipelineStatus(pid, 'Done', mid); toast('Task completed!', 'success'); loadPipeline(); } catch(e) { toast('Error','error'); } };

    // ━━━ NOTIFICATIONS ━━━
    async function loadNotifications() {
        try {
            const data = await api.getNotifications();
            const notifs = data.notifications || [];
            if (!notifs.length) { $('#notifications-list').innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#128276;</div><div class="empty-state-text">No notifications yet. Create a job card to see Telegram messages here.</div></div>'; return; }

            $('#notifications-list').innerHTML = notifs.reverse().map(n => `
                <div class="notif-item">
                    <div class="notif-header">
                        <span class="badge-status ${n.status === 'sent' ? 'completed' : n.status === 'simulated' ? 'pending' : 'urgent'}">${n.status}</span>
                        <span class="notif-time">Chat: ${n.chat_id || 'N/A'}</span>
                    </div>
                    <div class="notif-message">${(n.message||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>
                </div>
            `).join('');

            const badge = $('#notif-badge');
            if (notifs.length) { badge.textContent = notifs.length; badge.classList.add('show'); }
        } catch (err) { toast('Failed to load notifications', 'error'); }
    }

    // ━━━ Init ━━━
    loadDashboard();
    // Load voices for TTS
    if (window.speechSynthesis) speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
});
