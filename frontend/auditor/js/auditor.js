/**
 * AutoMech Sentinel AI — Autonomous Diagnostic Arbiter
 * Client Controller & Real-Time Telemetry Engine
 */

(function () {
    'use strict';

    // State Store
    const state = {
        activeTab: 'tab-audit',
        activeFilter: 'all',
        searchQuery: '',
        queue: [],
        selectedJobId: null,
        selectedJobData: null,
        auditorConfig: {
            auto_greenflag: true,
            strictness: 'balanced',
            auto_prune: true
        },
        stats: {
            total_jobcards: 0,
            audited_count: 0,
            green_flags_granted: 0,
            unnecessary_replacements_blocked: 0,
            total_customer_savings: 0
        }
    };

    // DOM Elements
    const elements = {
        // Tabs
        tabButtons: document.querySelectorAll('.tab-btn'),
        tabPanes: document.querySelectorAll('.tab-pane'),

        // Config & Tickers
        toggleAutoGreenFlag: document.getElementById('toggle-autogreenflag'),
        modeLabel: document.getElementById('mode-label'),
        strictnessSelect: document.getElementById('strictness-select'),
        statAudited: document.getElementById('stat-audited'),
        statUnnecessary: document.getElementById('stat-unnecessary'),
        statSavings: document.getElementById('stat-savings'),
        statGreenFlags: document.getElementById('stat-greenflags'),

        // Queue
        queueCount: document.getElementById('queue-count'),
        queueListContainer: document.getElementById('queue-list-container'),
        queueSearchInput: document.getElementById('queue-search-input'),
        queueFilterChips: document.querySelectorAll('.chip-btn'),
        btnRefreshQueue: document.getElementById('btn-refresh-queue'),

        // Dossier
        dossierEmptyState: document.getElementById('dossier-empty-state'),
        dossierContentView: document.getElementById('dossier-content-view'),
        dossierJcId: document.getElementById('dossier-jc-id'),
        dossierVehicle: document.getElementById('dossier-vehicle'),
        dossierReg: document.getElementById('dossier-reg'),
        dossierVerdictPill: document.getElementById('dossier-verdict-pill'),
        dossierIntegrityBadge: document.getElementById('dossier-integrity-badge'),
        dossierComplaint: document.getElementById('dossier-complaint'),
        dossierFault: document.getElementById('dossier-fault'),
        dossierVerdictSummary: document.getElementById('dossier-verdict-summary'),
        dossierPartsTbody: document.getElementById('dossier-parts-tbody'),
        dossierOrigCost: document.getElementById('dossier-orig-cost'),
        dossierAuditedCost: document.getElementById('dossier-audited-cost'),
        dossierSavings: document.getElementById('dossier-savings'),
        dossierSavingsPct: document.getElementById('dossier-savings-pct'),
        dossierProcedureText: document.getElementById('dossier-procedure-text'),
        dossierSealHash: document.getElementById('dossier-seal-hash'),
        dossierTimestamp: document.getElementById('dossier-timestamp'),

        // Dossier Actions
        btnActionGreenflag: document.getElementById('btn-action-greenflag'),
        btnActionPruneGreenflag: document.getElementById('btn-action-prune-greenflag'),
        btnActionReject: document.getElementById('btn-action-reject'),
        btnActionChatJob: document.getElementById('btn-action-chat-job'),
        btnActionExport: document.getElementById('btn-action-export'),

        // Copilot
        copilotContextBadge: document.getElementById('copilot-context-badge'),
        chatViewport: document.getElementById('chat-viewport'),
        copilotInput: document.getElementById('copilot-input'),
        btnCopilotSend: document.getElementById('btn-copilot-send'),

        // Sandbox
        simVehicle: document.getElementById('sim-vehicle'),
        simStrictness: document.getElementById('sim-strictness'),
        simComplaint: document.getElementById('sim-complaint'),
        simFault: document.getElementById('sim-fault'),
        simParts: document.getElementById('sim-parts'),
        btnRunSimulation: document.getElementById('btn-run-simulation'),
        simResultCard: document.getElementById('sim-result-card'),
        simVerdictPill: document.getElementById('sim-verdict-pill'),
        simMetaStats: document.getElementById('sim-meta-stats'),
        simSummaryText: document.getElementById('sim-summary-text'),
        simTableTbody: document.getElementById('sim-table-tbody'),

        // Ontology
        ontologyGrid: document.getElementById('ontology-grid')
    };

    // ─────────────────────────────────────────────────────────────
    // API Client
    // ─────────────────────────────────────────────────────────────
    const api = {
        async getStatus() {
            const res = await fetch('/api/auditor/status');
            return await res.json();
        },
        async updateConfig(data) {
            const res = await fetch('/api/auditor/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await res.json();
        },
        async getQueue(filter) {
            const url = filter ? `/api/auditor/queue?filter_verdict=${encodeURIComponent(filter)}` : '/api/auditor/queue';
            const res = await fetch(url);
            return await res.json();
        },
        async getJobCard(jcId) {
            const res = await fetch(`/api/auditor/jobcard/${encodeURIComponent(jcId)}`);
            return await res.json();
        },
        async grantGreenFlag(jcId, prune) {
            const res = await fetch(`/api/auditor/greenflag/${encodeURIComponent(jcId)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prune_unnecessary: prune })
            });
            return await res.json();
        },
        async rejectJobCard(jcId, reason) {
            const res = await fetch(`/api/auditor/reject/${encodeURIComponent(jcId)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });
            return await res.json();
        },
        async evaluateSandbox(payload) {
            const res = await fetch('/api/auditor/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            return await res.json();
        },
        async chat(message, jcId) {
            const res = await fetch('/api/auditor/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, jobcard_id: jcId })
            });
            return await res.json();
        }
    };

    // ─────────────────────────────────────────────────────────────
    // UI Helpers & Notifications
    // ─────────────────────────────────────────────────────────────
    function showToast(message, type = 'info') {
        let toastContainer = document.getElementById('sentinel-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'sentinel-toast-container';
            toastContainer.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:10px;';
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        toast.style.cssText = `
            background: #0d1527;
            border-left: 4px solid ${type === 'success' ? '#00f59b' : (type === 'error' ? '#ff3366' : '#00d2ff')};
            border-radius: 8px;
            padding: 12px 18px;
            color: #ffffff;
            font-size: 0.82rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
            display: flex;
            align-items: center;
            gap: 10px;
            animation: fadeIn 0.2s ease-out;
            max-width: 360px;
        `;
        toast.innerHTML = `<span>${type === 'success' ? '✅' : (type === 'error' ? '⚠️' : 'ℹ️')}</span><div>${message}</div>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3800);
    }

    function formatCurrency(amount) {
        return '₹' + Number(amount || 0).toLocaleString('en-IN');
    }

    // ─────────────────────────────────────────────────────────────
    // App Initialization
    // ─────────────────────────────────────────────────────────────
    async function init() {
        bindEvents();
        renderOntologyGrid();
        await loadStatus();
        await loadQueue();
    }

    // ─────────────────────────────────────────────────────────────
    // Event Handlers
    // ─────────────────────────────────────────────────────────────
    function bindEvents() {
        // Tab switching
        elements.tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                switchTab(targetTab);
            });
        });

        // Config Toggles
        elements.toggleAutoGreenFlag.addEventListener('change', async (e) => {
            const active = e.target.checked;
            elements.modeLabel.textContent = active ? 'ACTIVE' : 'MANUAL';
            elements.modeLabel.className = active ? 'pill-value text-cyan' : 'pill-value text-amber';
            try {
                await api.updateConfig({ auto_greenflag: active });
                showToast(`Autonomous Green Flag ${active ? 'Enabled' : 'Disabled (Manual Review Mode)'}`, 'info');
            } catch (err) {
                console.error(err);
            }
        });

        elements.strictnessSelect.addEventListener('change', async (e) => {
            const strictness = e.target.value;
            try {
                await api.updateConfig({ strictness });
                showToast(`Frugality strictness set to: ${strictness.toUpperCase()}`, 'info');
                await loadQueue();
            } catch (err) {
                console.error(err);
            }
        });

        // Queue search & filters
        elements.btnRefreshQueue.addEventListener('click', () => loadQueue());

        elements.queueSearchInput.addEventListener('input', (e) => {
            state.searchQuery = e.target.value.toLowerCase();
            renderQueue();
        });

        elements.queueFilterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                elements.queueFilterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                state.activeFilter = chip.getAttribute('data-filter');
                renderQueue();
            });
        });

        // Action Buttons
        elements.btnActionGreenflag.addEventListener('click', () => handleGreenFlagAction(false));
        elements.btnActionPruneGreenflag.addEventListener('click', () => handleGreenFlagAction(true));
        elements.btnActionReject.addEventListener('click', handleRejectAction);
        elements.btnActionChatJob.addEventListener('click', () => {
            if (state.selectedJobData) {
                switchTab('tab-copilot');
                elements.copilotInput.value = `Why did you audit ${state.selectedJobData.jobcard.jobcard_id} with verdict ${state.selectedJobData.ai_audit.verdict}?`;
                elements.copilotInput.focus();
            }
        });
        elements.btnActionExport.addEventListener('click', handleExportDossier);

        // Copilot Chat
        elements.btnCopilotSend.addEventListener('click', handleSendMessage);
        elements.copilotInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        // Delegated prompt chip clicks
        elements.chatViewport.addEventListener('click', (e) => {
            if (e.target.classList.contains('prompt-chip')) {
                const query = e.target.getAttribute('data-query');
                elements.copilotInput.value = query;
                handleSendMessage();
            }
        });

        // Sandbox Simulation
        elements.btnRunSimulation.addEventListener('click', handleRunSimulation);
    }

    function switchTab(tabId) {
        state.activeTab = tabId;
        elements.tabButtons.forEach(b => {
            b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
        });
        elements.tabPanes.forEach(p => {
            p.classList.toggle('active', p.id === tabId);
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Load Status & Tickers
    // ─────────────────────────────────────────────────────────────
    async function loadStatus() {
        try {
            const data = await api.getStatus();
            state.auditorConfig = {
                auto_greenflag: data.auto_greenflag,
                strictness: data.strictness,
                auto_prune: data.auto_prune
            };
            state.stats = data.stats || state.stats;

            // Update UI elements
            elements.toggleAutoGreenFlag.checked = data.auto_greenflag;
            elements.modeLabel.textContent = data.auto_greenflag ? 'ACTIVE' : 'MANUAL';
            elements.strictnessSelect.value = data.strictness || 'balanced';

            elements.statAudited.textContent = state.stats.audited_count;
            elements.statUnnecessary.textContent = state.stats.unnecessary_replacements_blocked;
            elements.statSavings.textContent = formatCurrency(state.stats.total_customer_savings);
            elements.statGreenFlags.textContent = state.stats.green_flags_granted;
        } catch (e) {
            console.error('Error loading auditor status:', e);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Load & Render Queue
    // ─────────────────────────────────────────────────────────────
    async function loadQueue() {
        try {
            elements.queueListContainer.innerHTML = `
                <div class="loading-shimmer"><div class="shimmer-line"></div><div class="shimmer-line short"></div></div>
            `;
            const data = await api.getQueue();
            state.queue = data.queue || [];
            elements.queueCount.textContent = state.queue.length;
            renderQueue();

            // Auto-select first jobcard if none selected
            if (state.queue.length > 0) {
                if (!state.selectedJobId || !state.queue.some(j => j.jobcard_id === state.selectedJobId)) {
                    selectJobCard(state.queue[0].jobcard_id);
                } else {
                    selectJobCard(state.selectedJobId);
                }
            } else {
                elements.dossierEmptyState.classList.remove('hidden');
                elements.dossierContentView.classList.add('hidden');
            }
        } catch (e) {
            console.error('Error loading queue:', e);
            elements.queueListContainer.innerHTML = '<div style="color:#ff3366;font-size:0.8rem;padding:12px;">Failed to load queue.</div>';
        }
    }

    function renderQueue() {
        let filtered = state.queue.slice();

        // Filter chips
        if (state.activeFilter === 'GREEN_FLAG') {
            filtered = filtered.filter(j => j.verdict === 'GREEN_FLAG_APPROVED');
        } else if (state.activeFilter === 'OPTIMIZED') {
            filtered = filtered.filter(j => j.verdict === 'GREEN_FLAG_OPTIMIZED');
        } else if (state.activeFilter === 'OVERREPLACEMENT') {
            filtered = filtered.filter(j => j.verdict === 'FLAGGED_OVERREPLACEMENT' || j.unnecessary_blocked > 0);
        }

        // Search text
        if (state.searchQuery) {
            filtered = filtered.filter(j => 
                (j.jobcard_id || '').toLowerCase().includes(state.searchQuery) ||
                (j.vehicle_make || '').toLowerCase().includes(state.searchQuery) ||
                (j.vehicle_model || '').toLowerCase().includes(state.searchQuery) ||
                (j.vehicle_reg || '').toLowerCase().includes(state.searchQuery) ||
                (j.complaint || '').toLowerCase().includes(state.searchQuery)
            );
        }

        if (filtered.length === 0) {
            elements.queueListContainer.innerHTML = `
                <div style="text-align:center;padding:24px;color:var(--text-secondary);font-size:0.8rem;">
                    No job cards found matching filters.
                </div>
            `;
            return;
        }

        elements.queueListContainer.innerHTML = filtered.map(j => {
            const isSelected = j.jobcard_id === state.selectedJobId;
            let badgeClass = 'badge-pending';
            let badgeText = 'PENDING AUDIT';

            if (j.verdict === 'GREEN_FLAG_APPROVED') {
                badgeClass = 'badge-green';
                badgeText = 'GREEN FLAG';
            } else if (j.verdict === 'GREEN_FLAG_OPTIMIZED') {
                badgeClass = 'badge-optimized';
                badgeText = 'OPTIMIZED';
            } else if (j.verdict === 'FLAGGED_OVERREPLACEMENT') {
                badgeClass = 'badge-flagged';
                badgeText = 'OVERREPLACEMENT';
            }

            return `
                <div class="queue-card ${isSelected ? 'selected' : ''}" data-id="${j.jobcard_id}">
                    <div class="qc-header">
                        <span class="qc-id">${j.jobcard_id}</span>
                        <span class="qc-badge ${badgeClass}">${badgeText}</span>
                    </div>
                    <div class="qc-vehicle">${j.vehicle_make} ${j.vehicle_model} <span style="font-weight:400;color:var(--text-muted);">(${j.vehicle_reg || 'N/A'})</span></div>
                    <div class="qc-complaint">${j.complaint || j.diagnosis_fault || 'Inspection required'}</div>
                    <div class="qc-footer">
                        <span>🛡️ Integrity: ${j.integrity_score || '--'}%</span>
                        ${j.customer_savings > 0 ? `<span class="qc-savings">Saved ${formatCurrency(j.customer_savings)}</span>` : '<span>0 Overkill</span>'}
                    </div>
                </div>
            `;
        }).join('');

        // Attach click listeners to cards
        elements.queueListContainer.querySelectorAll('.queue-card').forEach(card => {
            card.addEventListener('click', () => {
                const jcId = card.getAttribute('data-id');
                selectJobCard(jcId);
            });
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Select & Render Deep-Dive Dossier
    // ─────────────────────────────────────────────────────────────
    async function selectJobCard(jcId) {
        state.selectedJobId = jcId;
        renderQueue(); // Update selected card visual

        try {
            const data = await api.getJobCard(jcId);
            if (!data || !data.jobcard) return;
            state.selectedJobData = data;
            renderDossier(data.jobcard, data.ai_audit);
        } catch (e) {
            console.error('Error fetching jobcard detail:', e);
            showToast(`Could not load details for ${jcId}`, 'error');
        }
    }

    function renderDossier(jc, audit) {
        elements.dossierEmptyState.classList.add('hidden');
        elements.dossierContentView.classList.remove('hidden');

        // Header
        elements.dossierJcId.textContent = jc.jobcard_id;
        elements.dossierVehicle.textContent = `${jc.vehicle_make || ''} ${jc.vehicle_model || ''} (${jc.vehicle_year || 'Year N/A'})`.trim();
        elements.dossierReg.textContent = jc.vehicle_reg || 'NO REG';

        // Verdict Badge
        const verdict = audit ? audit.verdict : 'PENDING';
        let badgeColor = 'badge-green';
        if (verdict === 'GREEN_FLAG_OPTIMIZED') badgeColor = 'badge-optimized';
        else if (verdict === 'FLAGGED_OVERREPLACEMENT') badgeColor = 'badge-flagged';
        elements.dossierVerdictPill.className = `verdict-banner-pill ${badgeColor}`;
        elements.dossierVerdictPill.textContent = audit ? audit.verdict_badge : 'PENDING EVALUATION';

        // Root Cause & Diagnostic Summary
        elements.dossierIntegrityBadge.textContent = `Integrity: ${audit ? audit.integrity_score : '--'}/100`;
        elements.dossierComplaint.textContent = jc.complaint || 'No complaint specified';
        elements.dossierFault.textContent = jc.diagnosis_fault || 'Diagnostic evaluation in progress';
        elements.dossierVerdictSummary.textContent = audit ? audit.verdict_summary : 'Evaluation pending.';

        // Scrutiny Table
        const parts = (audit && audit.parts_analysis) ? audit.parts_analysis : [];
        if (parts.length === 0) {
            elements.dossierPartsTbody.innerHTML = `
                <tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:18px;">No replacement components quoted for this repair.</td></tr>
            `;
        } else {
            elements.dossierPartsTbody.innerHTML = parts.map(p => {
                const score = p.necessity_score || 0;
                let fillClass = 'fill-crimson';
                let tagClass = 'tag-unnecessary';

                if (score >= 80) { fillClass = 'fill-emerald'; tagClass = 'tag-essential'; }
                else if (score >= 55) { fillClass = 'fill-cyan'; tagClass = 'tag-preventative'; }
                else if (p.status === 'REDUNDANT') { fillClass = 'fill-amber'; tagClass = 'tag-redundant'; }

                const isPruned = p.action_taken === 'PRUNED';

                return `
                    <tr>
                        <td>
                            <div class="part-cell-name">${p.part_name}</div>
                            <div class="part-cell-id">${p.part_id}</div>
                        </td>
                        <td><span style="font-size:0.75rem;color:var(--text-secondary);">${p.category || 'Mechanical'}</span></td>
                        <td style="font-family:var(--font-mono);font-weight:700;">${formatCurrency(p.unit_price)}</td>
                        <td>
                            <div class="necessity-bar-wrap">
                                <div class="necessity-progress-bar">
                                    <div class="necessity-fill ${fillClass}" style="width:${score}%"></div>
                                </div>
                                <span class="necessity-num">${score}%</span>
                            </div>
                        </td>
                        <td><span class="status-tag ${tagClass}">${p.status}</span></td>
                        <td><span class="action-pill ${isPruned ? 'action-pruned' : 'action-approved'}">${p.action_taken}</span></td>
                        <td><div class="rationale-text">${p.technical_rationale}</div></td>
                    </tr>
                `;
            }).join('');
        }

        // Financial Ledger
        const metrics = audit ? audit.metrics : {};
        const origCost = metrics.original_parts_cost || 0;
        const auditCost = metrics.audited_parts_cost || 0;
        const savings = metrics.customer_savings || 0;
        const pct = metrics.savings_percentage || 0;

        elements.dossierOrigCost.textContent = formatCurrency(origCost);
        elements.dossierAuditedCost.textContent = formatCurrency(auditCost);
        elements.dossierSavings.textContent = formatCurrency(savings);
        elements.dossierSavingsPct.textContent = savings > 0 ? `${pct}% wasteful expense eliminated` : '0% waste detected (Optimal)';

        // Procedure Guidance
        const guidance = (audit && audit.engineering_guidance) ? audit.engineering_guidance.recommended_diagnostic_procedure : 'Follow standard OEM test protocols.';
        elements.dossierProcedureText.textContent = guidance;

        // Seal & Hash
        elements.dossierSealHash.textContent = audit ? audit.audit_seal : 'PENDING-SEAL';
        elements.dossierTimestamp.textContent = audit ? new Date(audit.timestamp).toLocaleString() : 'N/A';

        // Update copilot context badge
        elements.copilotContextBadge.textContent = `Context: ${jc.jobcard_id} (${jc.vehicle_make} ${jc.vehicle_model})`;
    }

    // ─────────────────────────────────────────────────────────────
    // Dossier Actions
    // ─────────────────────────────────────────────────────────────
    async function handleGreenFlagAction(prune) {
        if (!state.selectedJobId) return;
        try {
            const res = await api.grantGreenFlag(state.selectedJobId, prune);
            if (res.success) {
                showToast(`✅ AI Green Flag awarded to ${state.selectedJobId}${prune ? ' (with unnecessary parts pruned)' : ''}!`, 'success');
                await loadStatus();
                await selectJobCard(state.selectedJobId);
            } else {
                showToast(`Failed to grant Green Flag: ${res.message || 'Error'}`, 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('Error executing green flag.', 'error');
        }
    }

    async function handleRejectAction() {
        if (!state.selectedJobId) return;
        const reason = prompt('Enter specific reason for rejecting this repair quotation:', 'Unjustified over-replacement of parts detected by AI Sentinel.');
        if (!reason) return;

        try {
            const res = await api.rejectJobCard(state.selectedJobId, reason);
            if (res.success) {
                showToast(`⛔ Job card ${state.selectedJobId} marked as Rejected. Re-diagnosis required.`, 'error');
                await loadStatus();
                await selectJobCard(state.selectedJobId);
            }
        } catch (e) {
            console.error(e);
            showToast('Error rejecting job card.', 'error');
        }
    }

    function handleExportDossier() {
        if (!state.selectedJobData) return;
        const jc = state.selectedJobData.jobcard;
        const audit = state.selectedJobData.ai_audit;

        const exportPayload = {
            certificate_title: "AUTOMECH SENTINEL AI - CERTIFIED DIAGNOSTIC QUALITY DOSSIER",
            generated_at: new Date().toISOString(),
            jobcard_id: jc.jobcard_id,
            vehicle: `${jc.vehicle_make} ${jc.vehicle_model} (${jc.vehicle_reg})`,
            complaint: jc.complaint,
            diagnosed_fault: jc.diagnosis_fault,
            verdict: audit ? audit.verdict : "N/A",
            integrity_score: audit ? audit.integrity_score : 0,
            customer_savings: audit ? audit.metrics.customer_savings : 0,
            cryptographic_seal: audit ? audit.audit_seal : "N/A",
            parts_scrutiny: audit ? audit.parts_analysis : []
        };

        const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `SENTINEL_AUDIT_${jc.jobcard_id}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast(`Audit dossier for ${jc.jobcard_id} exported!`, 'info');
    }

    // ─────────────────────────────────────────────────────────────
    // AI Developer Copilot Chat
    // ─────────────────────────────────────────────────────────────
    async function handleSendMessage() {
        const text = elements.copilotInput.value.trim();
        if (!text) return;

        // Append User Bubble
        appendChatBubble('user', text);
        elements.copilotInput.value = '';

        // Add Loading Indicator
        const loadingId = 'loading-' + Date.now();
        const loadingBubble = document.createElement('div');
        loadingBubble.id = loadingId;
        loadingBubble.className = 'chat-bubble ai-bubble';
        loadingBubble.innerHTML = `
            <div class="bubble-header"><span class="ai-role-tag">SENTINEL AI ARBITER</span></div>
            <div class="bubble-body" style="color:var(--neon-emerald);font-family:var(--font-mono);font-size:0.8rem;">
                Analyzing telemetry & formulating engineering response...
            </div>
        `;
        elements.chatViewport.appendChild(loadingBubble);
        elements.chatViewport.scrollTop = elements.chatViewport.scrollHeight;

        try {
            const res = await api.chat(text, state.selectedJobId);
            loadingBubble.remove();
            appendChatBubble('ai', res.reply || 'No response returned.', res.suggestions || []);
        } catch (e) {
            console.error(e);
            loadingBubble.remove();
            appendChatBubble('ai', 'Error connecting to the AI Diagnostic Arbiter engine.');
        }
    }

    function appendChatBubble(role, content, suggestions = []) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role === 'user' ? 'user-bubble' : 'ai-bubble'}`;

        const roleTag = role === 'user' ? 'GARAGE TECHNICIAN' : 'SENTINEL AI ARBITER';
        const formattedBody = formatMarkdown(content);

        let chipsHtml = '';
        if (suggestions && suggestions.length > 0) {
            chipsHtml = `
                <div class="bubble-chips">
                    ${suggestions.map(s => `<button class="prompt-chip" data-query="${s}">${s}</button>`).join('')}
                </div>
            `;
        }

        bubble.innerHTML = `
            <div class="bubble-header">
                <span class="${role === 'user' ? 'user-role-tag' : 'ai-role-tag'}">${roleTag}</span>
                <span class="bubble-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div class="bubble-body">${formattedBody}</div>
            ${chipsHtml}
        `;

        elements.chatViewport.appendChild(bubble);
        elements.chatViewport.scrollTop = elements.chatViewport.scrollHeight;
    }

    function formatMarkdown(text) {
        if (!text) return '';
        let escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Headers
        escaped = escaped.replace(/^### (.*$)/gim, '<h4>$1</h4>');
        escaped = escaped.replace(/^#### (.*$)/gim, '<h5>$1</h5>');

        // Bold & Italic
        escaped = escaped.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
        escaped = escaped.replace(/\*(.*?)\*/gim, '<em>$1</em>');
        escaped = escaped.replace(/`([^`]+)`/gim, '<code style="background:rgba(0,210,255,0.1);color:#00d2ff;padding:2px 5px;border-radius:4px;font-family:var(--font-mono);font-size:0.75rem;">$1</code>');

        // Pre code blocks
        escaped = escaped.replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>');

        // Blockquotes
        escaped = escaped.replace(/^> (.*$)/gim, '<blockquote style="border-left:3px solid #00f59b;margin:6px 0;padding-left:10px;color:#00f59b;">$1</blockquote>');

        // Markdown tables to HTML
        escaped = escaped.replace(/\|(.+)\|/gim, function (match) {
            const cells = match.split('|').filter(c => c.trim().length > 0);
            return `<tr>${cells.map(c => `<td>${c.trim()}</td>`).join('')}</tr>`;
        });

        // Wrap paragraphs
        return escaped.replace(/\n\n/g, '<br><br>');
    }

    // ─────────────────────────────────────────────────────────────
    // Diagnostic Sandbox Simulator
    // ─────────────────────────────────────────────────────────────
    async function handleRunSimulation() {
        const vehicleStr = elements.simVehicle.value.trim();
        const strictness = elements.simStrictness.value;
        const complaint = elements.simComplaint.value.trim();
        const fault = elements.simFault.value.trim();
        const partsText = elements.simParts.value.trim();

        if (!complaint || !partsText) {
            showToast('Please provide both complaint and parts to scrutinize.', 'error');
            return;
        }

        const partsList = partsText.split(',').map(p => p.trim()).filter(Boolean);

        try {
            elements.btnRunSimulation.disabled = true;
            elements.btnRunSimulation.innerHTML = '<span>Simulating Audit Telemetry...</span>';

            const res = await api.evaluateSandbox({
                vehicle: { make: vehicleStr },
                strictness: strictness,
                complaint: complaint,
                fault_name: fault,
                parts: partsList
            });

            elements.simResultCard.classList.remove('hidden');

            // Verdict Pill
            let badgeClass = 'badge-green';
            if (res.verdict === 'GREEN_FLAG_OPTIMIZED') badgeClass = 'badge-optimized';
            else if (res.verdict === 'FLAGGED_OVERREPLACEMENT') badgeClass = 'badge-flagged';
            elements.simVerdictPill.className = `verdict-banner-pill ${badgeClass}`;
            elements.simVerdictPill.textContent = res.verdict_badge;

            // Stats
            const m = res.metrics;
            elements.simMetaStats.innerHTML = `
                Integrity: <strong>${res.integrity_score}/100</strong> | 
                Unnecessary Blocked: <strong>${m.unnecessary_parts_blocked}</strong> | 
                Customer Savings: <strong style="color:var(--neon-emerald);">${formatCurrency(m.customer_savings)}</strong>
            `;
            elements.simSummaryText.textContent = res.verdict_summary;

            // Table
            elements.simTableTbody.innerHTML = res.parts_analysis.map(p => {
                const isPruned = p.action_taken === 'PRUNED';
                return `
                    <tr>
                        <td style="font-weight:600;color:#ffffff;">${p.part_name}</td>
                        <td style="font-family:var(--font-mono);">${formatCurrency(p.unit_price)}</td>
                        <td style="font-family:var(--font-mono);font-weight:700;">${p.necessity_score}%</td>
                        <td><span class="status-tag ${p.status === 'ESSENTIAL' ? 'tag-essential' : 'tag-unnecessary'}">${p.status}</span></td>
                        <td><span class="action-pill ${isPruned ? 'action-pruned' : 'action-approved'}">${p.action_taken}</span></td>
                        <td style="font-size:0.72rem;color:var(--text-secondary);">${p.technical_rationale}</td>
                    </tr>
                `;
            }).join('');

            showToast('Simulation audit complete!', 'success');
        } catch (e) {
            console.error(e);
            showToast('Simulation audit failed.', 'error');
        } finally {
            elements.btnRunSimulation.disabled = false;
            elements.btnRunSimulation.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                <span>Run Anti-Overreplacement Audit</span>
            `;
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Render Causal Ontology Grid
    // ─────────────────────────────────────────────────────────────
    function renderOntologyGrid() {
        const rules = [
            {
                subsystem: "Electrical: Charging Loop",
                icon: "⚡",
                failure: "Alternator Diode Pack / Voltage Regulator",
                essential: ["Alternator Assembly", "Drive Belt", "Regulator"],
                overkill: ["Starter Motor (unrelated circuit)", "Fuel Pump", "Spark Plugs"],
                procedure: "Perform alternator load test; confirm 13.8V-14.4V charging output before replacement."
            },
            {
                subsystem: "Electrical: Starting Loop",
                icon: "🔋",
                failure: "Starter Relay / Solenoid Drop",
                essential: ["Starter Relay", "Starter Motor", "Battery Terminal"],
                overkill: ["Alternator (car not running yet)", "Fuel Tank", "Timing Chain"],
                procedure: "Measure voltage drop across B+ and relay terminal (<0.20V) before condemning motor."
            },
            {
                subsystem: "Braking & Hydraulics",
                icon: "🛑",
                failure: "Friction Lining Squeal & Wear",
                essential: ["Front Brake Pad Set", "Brake Rotor", "Hardware Kit"],
                overkill: ["ABS Hydraulic Modulator", "Master Cylinder", "Suspension Strut"],
                procedure: "Measure pad lining with depth gauge (>3mm) and rotor runout with dial indicator."
            },
            {
                subsystem: "Engine Reciprocating Assembly",
                icon: "⚙️",
                failure: "Connecting Rod Bearing Knock",
                essential: ["Rod Bearing Set", "Oil Pan Gasket", "Engine Oil"],
                overkill: ["Starter Motor", "AC Compressor", "Steering Column"],
                procedure: "Drop oil pan and measure bearing journal clearance with Plastigage (<0.05mm)."
            },
            {
                subsystem: "Ignition & Combustion",
                icon: "🔥",
                failure: "Cylinder Misfire (P0300-P0304)",
                essential: ["Spark Plug Set", "Ignition Coil Pack", "Fuel Injector"],
                overkill: ["ECU Mainboard", "Catalytic Converter", "Transmission Gearbox"],
                procedure: "Read live OBD misfire counts; swap coil to adjacent cylinder to observe DTC migration."
            },
            {
                subsystem: "Cooling Loop",
                icon: "❄️",
                failure: "Thermostat Stuck / Radiator Leak",
                essential: ["Thermostat", "Coolant Hose", "Radiator Cap", "Coolant"],
                overkill: ["Full Engine Short Block", "Starter Motor", "Steering Rack"],
                procedure: "Conduct cooling system pressure test at 15 PSI to locate external weeping points."
            }
        ];

        elements.ontologyGrid.innerHTML = rules.map(r => `
            <div class="ontology-card">
                <div class="oc-head">
                    <span class="oc-icon">${r.icon}</span>
                    <div class="oc-title">${r.subsystem}</div>
                </div>
                <div class="oc-section">
                    <span class="oc-label">TARGET FAILURE MODE</span>
                    <div style="color:var(--neon-cyan);">${r.failure}</div>
                </div>
                <div class="oc-section">
                    <span class="oc-label">PERMITTED ESSENTIAL COMPONENTS</span>
                    <div class="oc-tag-list">
                        ${r.essential.map(e => `<span class="oc-tag essential">${e}</span>`).join('')}
                    </div>
                </div>
                <div class="oc-section">
                    <span class="oc-label">BLOCKED OVER-REPLACEMENT TRAPS</span>
                    <div class="oc-tag-list">
                        ${r.overkill.map(o => `<span class="oc-tag overkill">${o}</span>`).join('')}
                    </div>
                </div>
                <div class="oc-section">
                    <span class="oc-label">MINIMUM MANDATORY DIAGNOSTIC PROBE</span>
                    <div style="color:var(--text-secondary);font-size:0.7rem;line-height:1.35;">${r.procedure}</div>
                </div>
            </div>
        `).join('');
    }

    // Auto-initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
