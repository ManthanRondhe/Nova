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
            const actionPageMap = { diagnosis: 'diagnosis', diagnosis_followup: 'diagnosis', create_jobcard: 'jobcards', inventory: 'inventory', mechanics: 'mechanics', estimate: 'diagnosis', orders: 'dealers', pipeline: 'pipeline', dashboard: 'dashboard' };
            if (actionPageMap[result.action]) navigateTo(actionPageMap[result.action]);

            // Populate data
            if ((result.action === 'diagnosis' || result.action === 'diagnosis_followup') && result.data?.results) {
                renderDiagnosisResults(
                    result.data.results,
                    result.data.estimate,
                    result.data.repair_guide || result.data.video_guide,
                    result.data.differential_question
                );
            }
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
            renderDiagnosisResults(
                result.results,
                result.top_estimate,
                result.repair_guide || result.video_guide,
                result.differential_question
            );
            toast(`Found ${result.total_matches} potential faults`, 'success');
        } catch (err) { toast('Diagnosis failed', 'error'); }
        finally { $('#diagnose-btn').disabled = false; $('#diagnose-btn').innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>Run Diagnosis'; }
    });

    function buildTechnicalPlaceholderSvg(label, faultName = '', stepNum = 1) {
        const safeLabel = (label || 'Technical Component Schematic').replace(/"/g, "'").replace(/</g, '').slice(0, 48);
        const safeFault = (faultName || 'Automotive Assembly').replace(/"/g, "'").replace(/</g, '').slice(0, 44);
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" width="100%" height="100%">
            <defs>
                <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
                    <path d="M 24 0 L 0 0 0 24" fill="none" stroke="rgba(0,229,255,0.07)" stroke-width="1"/>
                </pattern>
            </defs>
            <rect width="640" height="360" fill="#050c1d"/>
            <rect width="640" height="360" fill="url(#grid)"/>
            <rect x="16" y="16" width="608" height="328" rx="8" fill="none" stroke="rgba(0,229,255,0.3)" stroke-width="1.5"/>
            <rect x="16" y="16" width="608" height="34" rx="8" fill="rgba(0,229,255,0.09)"/>
            <text x="30" y="37" fill="#00e5ff" font-family="monospace, sans-serif" font-size="11" font-weight="bold">STEP ${stepNum} CAD SCHEMATIC // MECHANICAL &amp; ELECTRICAL ASSEMBLY</text>
            <text x="610" y="37" text-anchor="end" fill="#94a3b8" font-family="monospace" font-size="10">ILLUSTRATIVE BLUEPRINT</text>
            <rect x="155" y="75" width="330" height="145" rx="8" fill="#0f2942" stroke="#00e5ff" stroke-width="2"/>
            <circle cx="235" cy="147" r="34" fill="#060d1f" stroke="#38bdf8" stroke-width="2"/>
            <circle cx="320" cy="147" r="34" fill="#060d1f" stroke="#00e5ff" stroke-width="2"/>
            <circle cx="405" cy="147" r="34" fill="#060d1f" stroke="#38bdf8" stroke-width="2"/>
            <line x1="185" y1="147" x2="455" y2="147" stroke="rgba(0,229,255,0.45)" stroke-width="2" stroke-dasharray="5,4"/>
            <circle cx="235" cy="95" r="9" fill="#f59e0b"/><text x="235" y="99" text-anchor="middle" fill="#000" font-family="monospace" font-size="10" font-weight="bold">1</text>
            <circle cx="320" cy="95" r="9" fill="#f59e0b"/><text x="320" y="99" text-anchor="middle" fill="#000" font-family="monospace" font-size="10" font-weight="bold">2</text>
            <circle cx="405" cy="95" r="9" fill="#f59e0b"/><text x="405" y="99" text-anchor="middle" fill="#000" font-family="monospace" font-size="10" font-weight="bold">3</text>
            <text x="320" y="242" text-anchor="middle" fill="#fde68a" font-family="monospace" font-size="11">[Inspect Fasteners, Seals, Clearances &amp; Electrical Terminals]</text>
            <line x1="16" y1="268" x2="624" y2="268" stroke="rgba(0,229,255,0.2)" stroke-width="1"/>
            <text x="32" y="292" fill="#e8edf8" font-family="monospace, sans-serif" font-size="14" font-weight="bold">${safeLabel}</text>
            <text x="32" y="314" fill="#38bdf8" font-family="sans-serif" font-size="12">Target Assembly: ${safeFault}</text>
            <text x="32" y="332" fill="#64748b" font-family="sans-serif" font-size="10">Illustrative CAD blueprint — Verify exact fastener layout in OEM factory manual</text>
        </svg>`;
        return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
    }

    function openImageLightbox(src, title, source) {
        let modal = document.getElementById('rg-lightbox-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'rg-lightbox-modal';
            modal.className = 'rg-lightbox-overlay';
            modal.onclick = (e) => {
                if (e.target === modal || e.target.classList.contains('rg-lightbox-close')) {
                    modal.classList.remove('active');
                }
            };
            document.body.appendChild(modal);
        }
        modal.innerHTML = `
            <div class="rg-lightbox-card">
                <div class="rg-lightbox-header">
                    <div class="rg-lightbox-title">${title || 'Technical Reference Diagram'}</div>
                    <button type="button" class="rg-lightbox-close">&times;</button>
                </div>
                <div class="rg-lightbox-body">
                    <img src="${src}" alt="${title || ''}" class="rg-lightbox-img" />
                </div>
                <div class="rg-lightbox-footer">
                    <span>Source: ${source || 'Technical Reference'}</span>
                    <span class="text-muted">Click outside or &times; to close</span>
                </div>
            </div>
        `;
        modal.classList.add('active');
    }

    function renderVisualRepairGuideHtml(guide, containerId = 'primary-repair-guide') {
        if (!guide) return '';

        const steps = guide.repair_steps || [];
        if (!steps.length) return '';

        const tools = guide.required_tools || [];
        const safety = guide.safety_precautions || [];
        const verification = guide.final_verification || [];
        const difficulty = guide.difficulty || 'Intermediate';
        const diffClass = difficulty.toLowerCase().includes('advanced') || difficulty.toLowerCase().includes('pro')
            ? 'diff-hard' : difficulty.toLowerCase().includes('begin') ? 'diff-easy' : 'diff-med';
        const sourceBadge = (guide.source_type || '').includes('llm') ? 'AI LLM Generated' : 'AI Technical Blueprint';

        return `
        <div class="repair-guide-container" id="${containerId}">
            <div class="repair-guide-toggle" onclick="this.closest('.repair-guide-container').classList.toggle('collapsed')">
                <div class="rg-toggle-title">
                    <span class="rg-icon">&#128736;</span>
                    <div>
                        <div class="rg-kicker">AI-GENERATED REPAIR ASSISTANCE &bull; ${sourceBadge}</div>
                        <div class="rg-main-heading">${guide.repair_title || 'Step-by-Step Visual Repair Guide'}</div>
                    </div>
                </div>
                <div class="rg-header-badges">
                    <span class="rg-difficulty-badge ${diffClass}">${difficulty}</span>
                    ${guide.estimated_time ? `<span class="rg-time-badge">&#9201; ${guide.estimated_time}</span>` : ''}
                    <span class="rg-chevron">&#9660;</span>
                </div>
            </div>

            <div class="repair-guide-body">
                <!-- Predicted Fault & Vehicle Context Banner -->
                <div class="rg-summary-banner">
                    <div class="rg-summary-main">
                        <div class="rg-meta-pills">
                            <div class="rg-fault-tag">
                                <span class="rg-label">Predicted Fault (Possible):</span>
                                <strong class="text-accent">${guide.predicted_fault || 'Vehicle Component Fault'}</strong>
                            </div>
                            <div class="rg-vehicle-tag">
                                <span class="rg-label">Target Vehicle:</span>
                                <strong>${guide.vehicle_context || 'Standard Vehicle (Verify OEM Specs)'}</strong>
                            </div>
                        </div>
                        <p class="rg-explanation">${guide.fault_explanation || ''}</p>
                    </div>

                    <!-- Vehicle Specificity Customization -->
                    <div class="rg-vehicle-customizer">
                        <div class="rg-customizer-title">Vehicle-Specific Procedure Refinement</div>
                        <div class="rg-customizer-inputs">
                            <input type="text" class="rg-v-make" placeholder="Make (e.g. Maruti, Hyundai)" value="" />
                            <input type="text" class="rg-v-model" placeholder="Model (e.g. Swift, Creta)" value="" />
                            <input type="number" class="rg-v-year" placeholder="Year (e.g. 2022)" min="1990" max="2027" value="" />
                            <button type="button" class="btn btn-primary btn-xs rg-tailor-btn"
                                data-fault="${(guide.predicted_fault || '').replace(/"/g, '&quot;')}"
                                data-container="${containerId}">
                                Tailor Guide
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Required Tools & Safety Precautions Grid -->
                <div class="rg-prereq-grid">
                    <div class="rg-tools-box">
                        <h4 class="rg-box-title">&#129520; Required Tools &amp; Test Instruments</h4>
                        <div class="rg-tools-list">
                            ${tools.length ? tools.map(t => `<span class="rg-tool-pill">${t}</span>`).join('') : '<span class="text-muted">Standard automotive hand tools</span>'}
                        </div>
                    </div>

                    <div class="rg-safety-box">
                        <h4 class="rg-box-title">&#9888;&#65039; Mandatory Safety Precautions</h4>
                        <ul class="rg-safety-list">
                            ${safety.length ? safety.map(s => `<li>${s}</li>`).join('') : '<li>Disconnect battery negative terminal and wear PPE before beginning work.</li>'}
                        </ul>
                    </div>
                </div>

                <!-- Step-by-Step Repair Cards -->
                <div class="rg-steps-section-header">
                    <h4>Step-by-Step Visual Repair Instructions (${steps.length} Chronological Steps)</h4>
                    <span class="rg-steps-hint">Click any technical diagram to enlarge</span>
                </div>
                <div class="repair-stages-timeline">
                    ${steps.map(st => {
                        const placeholderUri = buildTechnicalPlaceholderSvg(st.title || st.image_search_query, guide.predicted_fault, st.step_number);
                        const imgSrc = st.image_url || placeholderUri;
                        const isPlaceholder = !st.image_url || String(st.image_url).startsWith('data:image/svg+xml');
                        const safeTitle = (st.title || 'Repair step diagram').replace(/"/g, '&quot;');
                        const safeSource = (st.image_source || 'Technical Reference').replace(/"/g, '&quot;');
                        return `
                        <div class="repair-stage-card visual-step-card">
                            <div class="stage-timeline-bullet">${st.step_number}</div>
                            <div class="stage-content">
                                <div class="stage-header-row">
                                    <h4 class="stage-title">${st.title}</h4>
                                    <span class="stage-badge">Step ${st.step_number} of ${steps.length}</span>
                                </div>
                                <div class="visual-step-grid">
                                    <div class="visual-step-details">
                                        <p class="stage-desc">${st.instruction}</p>
                                        ${st.warning ? `
                                            <div class="rg-step-warning">
                                                <strong>&#9888; Technician Caution:</strong> ${st.warning}
                                            </div>
                                        ` : ''}
                                    </div>
                                    <div class="visual-step-media">
                                        <div class="rg-image-frame ${isPlaceholder ? 'is-placeholder' : ''}"
                                             data-title="${safeTitle}"
                                             data-source="${safeSource}">
                                            <img src="${imgSrc}"
                                                 alt="${safeTitle}"
                                                 class="rg-step-image"
                                                 loading="lazy"
                                                 onerror="this.onerror=null; this.src='${placeholderUri}'; this.closest('.rg-image-frame').classList.add('is-placeholder');" />
                                            <span class="rg-zoom-badge">&#128269; Inspect</span>
                                        </div>
                                        <div class="rg-image-meta">
                                            <span class="rg-image-source">&#128247; ${st.image_source || 'Technical Reference'}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>`;
                    }).join('')}
                </div>

                <!-- Final Verification Checklist -->
                ${verification.length ? `
                    <div class="rg-verification-box">
                        <h4 class="rg-box-title">&#9989; Final Post-Repair Verification Checklist</h4>
                        <div class="rg-verification-list">
                            ${verification.map((v, idx) => `
                                <label class="rg-check-item">
                                    <input type="checkbox" class="rg-check-input" />
                                    <span class="rg-check-text">${v}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Engineering Disclaimer -->
                <div class="rg-disclaimer">
                    &#9432; <strong>Technical Notice:</strong> ${guide.disclaimer || 'Predicted faults are probable diagnoses based on reported symptoms. Always confirm physically and consult OEM service manuals for exact torque specifications.'}
                </div>
            </div>
        </div>`;
    }

    function bindRepairGuideEvents() {
        document.querySelectorAll('.rg-image-frame').forEach(frame => {
            frame.onclick = () => {
                const img = frame.querySelector('img');
                if (img) {
                    openImageLightbox(img.src, frame.dataset.title, frame.dataset.source);
                }
            };
        });

        document.querySelectorAll('.rg-tailor-btn').forEach(btn => {
            btn.onclick = async () => {
                const containerId = btn.dataset.container;
                const container = document.getElementById(containerId);
                if (!container) return;

                const fault = btn.dataset.fault;
                const make = container.querySelector('.rg-v-make')?.value.trim() || '';
                const model = container.querySelector('.rg-v-model')?.value.trim() || '';
                const yearVal = container.querySelector('.rg-v-year')?.value.trim() || '';
                const year = yearVal ? parseInt(yearVal, 10) : null;

                if (!make && !model && !year) {
                    toast('Enter Vehicle Make, Model, or Year to tailor the guide', 'warning');
                    return;
                }

                btn.disabled = true;
                btn.textContent = 'Generating...';
                try {
                    const res = await api.generateRepairGuide({
                        predicted_fault: fault,
                        vehicle_make: make,
                        vehicle_model: model,
                        vehicle_year: year,
                        symptoms: $('#diagnosis-input')?.value.trim() || ''
                    });
                    if (res.success && res.repair_guide) {
                        container.outerHTML = renderVisualRepairGuideHtml(res.repair_guide, containerId);
                        bindRepairGuideEvents();
                        toast(`Repair guide tailored for ${[year, make, model].filter(Boolean).join(' ')}`, 'success');
                    } else {
                        toast(res.error || 'Could not generate tailored guide', 'error');
                    }
                } catch (err) {
                    toast('Failed to tailor repair guide', 'error');
                } finally {
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = 'Tailor Guide';
                    }
                }
            };
        });

        document.querySelectorAll('.load-alt-guide-btn').forEach(btn => {
            btn.onclick = async () => {
                const fault = btn.dataset.fault;
                const proc = btn.dataset.proc || '';
                const sys = btn.dataset.sys || '';
                const targetId = btn.dataset.target;
                const slot = document.getElementById(targetId);
                if (!slot) return;

                btn.disabled = true;
                btn.textContent = 'Generating AI Visual Repair Guide...';
                try {
                    const vtype = $('#diag-vehicle-type')?.value || '';
                    const vmodel = $('#diag-vehicle-model')?.value || '';
                    const res = await api.generateRepairGuide({
                        predicted_fault: fault,
                        vehicle_make: vtype,
                        vehicle_model: vmodel,
                        fix_procedure: proc,
                        system: sys,
                        symptoms: $('#diagnosis-input')?.value.trim() || ''
                    });
                    if (res.success && res.repair_guide) {
                        slot.innerHTML = renderVisualRepairGuideHtml(res.repair_guide, `rg-${targetId}`);
                        bindRepairGuideEvents();
                        btn.remove();
                    } else {
                        toast('Failed to generate repair guide', 'error');
                        btn.disabled = false;
                        btn.textContent = 'Generate AI Visual Repair Guide';
                    }
                } catch (err) {
                    toast('Error generating repair guide', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Generate AI Visual Repair Guide';
                }
            };
        });
    }

    function renderDiagnosisResults(results, estimate, repairGuide, differentialQuestion = null) {
        if (!results || !results.length) {
            $('#diagnosis-results').innerHTML = '<div class="empty-state"><div class="empty-state-icon">&#128269;</div><div class="empty-state-text">No matching faults found. Try describing the symptoms differently.</div></div>';
            return;
        }

        const top1 = results[0];
        const top2 = results.length > 1 ? results[1] : null;
        const followupBanner = differentialQuestion ? `
            <div class="card" style="margin-bottom:16px;border:1px solid rgba(245,158,11,0.5);background:linear-gradient(135deg,rgba(245,158,11,0.12),rgba(0,229,255,0.05));padding:16px;border-radius:12px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="font-size:1.25rem;">&#129504;</span>
                    <strong style="color:#fbbf24;font-size:0.95rem;letter-spacing:0.3px;">DIFFERENTIAL DIAGNOSTIC VERIFICATION REQUIRED</strong>
                </div>
                <p style="margin:0 0 12px 0;color:#e2e8f0;font-size:0.92rem;line-height:1.5;">${differentialQuestion}</p>
                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                    <button type="button" class="btn btn-primary btn-xs diff-quick-reply" data-reply="Yes, confirmed for ${top1.fault_name}">
                        &#9989; Yes — Matches ${top1.fault_name}
                    </button>
                    ${top2 ? `
                    <button type="button" class="btn btn-secondary btn-xs diff-quick-reply" data-reply="No, it matches ${top2.fault_name} (${(top2.confirming_keywords || '').split(',')[0] || top2.matched_symptom})">
                        &#128260; No — Matches ${top2.fault_name}
                    </button>` : ''}
                </div>
            </div>
        ` : '';

        $('#diagnosis-results').innerHTML = followupBanner + results.map((r, i) => {
            const confPct = Math.round((r.confidence || 0) * 100);
            const dashOffset = 188.5 - (188.5 * confPct / 100);
            const confColor = confPct >= 78 ? 'var(--success)' : confPct >= 50 ? 'var(--warning)' : 'var(--danger)';
            const isTop = i === 0;
            const slotId = `repair-guide-slot-${i}`;

            return `
            <div class="diagnosis-result ${isTop ? 'top-result' : ''}">
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
                ${r.fix_procedure ? `<div class="diag-fix"><div class="diag-fix-title">Summary Repair Procedure</div><div class="diag-fix-text">${r.fix_procedure}</div></div>` : ''}
                ${isTop && repairGuide ? renderVisualRepairGuideHtml(repairGuide, `primary-rg-${i}`) : `
                    <div id="${slotId}" style="margin-top:12px;">
                        <button type="button" class="btn btn-outline-cyan btn-xs load-alt-guide-btn"
                            data-fault="${(r.fault_name || '').replace(/"/g, '&quot;')}"
                            data-proc="${(r.fix_procedure || '').replace(/"/g, '&quot;')}"
                            data-sys="${(r.system || '').replace(/"/g, '&quot;')}"
                            data-target="${slotId}">
                            &#128736; Generate AI Visual Repair Guide
                        </button>
                    </div>
                `}
            </div>`;
        }).join('');

        document.querySelectorAll('.diff-quick-reply').forEach(btn => {
            btn.onclick = () => {
                const reply = btn.dataset.reply;
                if (!reply) return;
                const currentQuery = $('#diagnosis-input')?.value.trim() || '';
                if (currentQuery && chatContext.length === 0) {
                    chatContext.push({ role: 'user', text: currentQuery });
                    if (differentialQuestion) {
                        chatContext.push({ role: 'assistant', text: differentialQuestion });
                    }
                }
                voicePanel.classList.remove('hidden');
                voicePanel.classList.add('visible');
                addVoiceMessage(reply, 'user');
                processVoiceCommand(reply);
            };
        });

        bindRepairGuideEvents();
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
