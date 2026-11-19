/* Nova AI — Customer Portal Logic */

// Dynamic API Base
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE = isLocalhost ? 'http://localhost:8000/api' : '/api';

// ━━━ Tab Navigation ━━━
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

function switchTab(tab) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
    const navBtn = document.querySelector(`.nav-btn[data-tab="${tab}"]`);
    const section = document.querySelector(`.tab-section[data-tab="${tab}"]`);
    if (navBtn) navBtn.classList.add('active');
    if (section) section.classList.add('active');
}

// ━━━ Search Toggle ━━━
let searchType = 'reg';
document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        searchType = btn.dataset.type;
        const input = document.getElementById('search-input');
        input.placeholder = searchType === 'reg'
            ? 'Enter registration number (e.g. MH-04-AB-1234)'
            : 'Enter job card ID (e.g. JC-001)';
        input.value = '';
    });
});

// ━━━ Search Vehicle ━━━
async function searchVehicle() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    const resultsEl = document.getElementById('search-results');
    const detailEl = document.getElementById('vehicle-detail');
    detailEl.classList.add('hidden');
    resultsEl.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div><p class="empty-text">Searching...</p></div>';

    try {
        const res = await fetch(`${API_BASE}/jobcards`);
        const data = await res.json();
        const jcards = data.jobcards || [];

        // Filter by search
        const matches = jcards.filter(jc => {
            const q = query.toLowerCase();
            if (searchType === 'reg') {
                return (jc.vehicle_reg || '').toLowerCase().includes(q);
            } else {
                return (jc.jobcard_id || '').toLowerCase().includes(q);
            }
        });

        if (matches.length === 0) {
            resultsEl.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><p class="empty-text">No vehicles found for "${query}"</p></div>`;
            return;
        }

        resultsEl.innerHTML = matches.map(jc => {
            const statusClass = (jc.status || 'Pending').toLowerCase().replace(/\s+/g, '-');
            return `
                <div class="jc-item" onclick="showDetail('${jc.jobcard_id}')">
                    <div>
                        <div class="jc-title">
                            <span>${jc.vehicle_make || ''} ${jc.vehicle_model || ''}</span>
                            <span class="status-badge ${statusClass}">${jc.status || 'Pending'}</span>
                        </div>
                        <div class="jc-meta">${jc.vehicle_reg || 'N/A'} · ${jc.jobcard_id} · ${jc.created_at || ''}</div>
                    </div>
                    <span class="jc-arrow">→</span>
                </div>`;
        }).join('');
    } catch (e) {
        resultsEl.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><p class="empty-text">Could not connect to server</p></div>`;
    }
}

// Enter key search
document.getElementById('search-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') searchVehicle();
});

// ━━━ Show Detail ━━━
async function showDetail(jcId) {
    document.getElementById('search-results').innerHTML = '';
    const detailEl = document.getElementById('vehicle-detail');
    detailEl.classList.remove('hidden');

    try {
        // Use the dedicated customer detail API
        const res = await fetch(`${API_BASE}/customer/vehicle/${jcId}`);
        const data = await res.json();
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        const jc = data.jobcard;
        const mech = data.mechanic;
        const quote = data.quotation;
        const parts = data.parts;
        const timeline = data.timeline;

        // Banner
        const statusClass = (jc.status || 'Pending').toLowerCase().replace(/\s+/g, '-');
        document.getElementById('detail-banner').innerHTML = `
            <div class="banner-info">
                <h2>${jc.vehicle || ''} ${jc.vehicle_year || ''}</h2>
                <p>Reg: ${jc.vehicle_reg || 'N/A'} · Bay: ${jc.bay_number || 'N/A'} · ${jc.id}</p>
                ${jc.complaint ? `<p style="margin-top:4px;opacity:0.6;font-size:0.85em">Complaint: ${jc.complaint}</p>` : ''}
            </div>
            <div class="banner-meta">
                <div class="banner-stat"><div class="banner-stat-val">${jc.priority || 'Medium'}</div><div class="banner-stat-lbl">Priority</div></div>
                <span class="status-badge ${statusClass}">${jc.status || 'Pending'}</span>
            </div>`;

        // ━━━ Approval Card (Feature 2: Unbiased Diagnostics) ━━━
        const approvalArea = document.getElementById('approval-card-area');
        const approvalStat = data.approval_status || jc.approval_status || 'LEGACY_APPROVED';
        const estData = data.estimate || quote || {};

        if (approvalArea) {
            if (approvalStat === 'PENDING_CUSTOMER_APPROVAL') {
                const workItems = (estData.work_items || [
                    'Independent diagnostic verification',
                    `Repair procedure: ${jc.fault || 'Targeted automotive repair'}`,
                    'Certified parts replacement & bench quality inspection',
                    'Post-install calibration & road test validation'
                ]);

                approvalArea.innerHTML = `
                <div class="approval-card">
                    <div class="approval-header">
                        <div class="approval-title-wrap">
                            <span class="approval-icon">⚡</span>
                            <div>
                                <h3 class="approval-title">Approval Required: Independent Repair Estimate</h3>
                                <div class="approval-subtitle">Verified & Audited by Sentinel AI Diagnostic Arbiter · Unbiased Anti-Overreplacement Guarantee</div>
                                ${jc.customer_savings > 0 ? `<div style="display:inline-flex;align-items:center;gap:6px;background:rgba(0,245,155,0.12);border:1px solid #00f59b;color:#00f59b;padding:3px 8px;border-radius:10px;font-size:0.7rem;font-weight:700;margin-top:4px;">🛡️ Sentinel AI: Pruned Unnecessary Parts · ₹${Number(jc.customer_savings).toLocaleString()} Saved</div>` : ''}
                            </div>
                        </div>
                        <span class="approval-badge badge-action-needed">Action Required</span>
                    </div>
                    <div class="approval-body-text">
                        Our independent company diagnostic team has verified this issue directly to prevent shop inflation.
                        Please review the approved work items and cost quotation below, then authorize service to begin repair.
                    </div>
                    <div class="approval-work-list">
                        <div class="approval-work-title">Authorized Work Items:</div>
                        <div>
                            ${workItems.map(item => `<span class="work-item-pill">✓ ${item}</span>`).join('')}
                        </div>
                    </div>
                    <div style="font-size:0.95rem; font-weight:600; color:var(--text-primary); margin-top:10px;">
                        Estimated Total: <span style="color:var(--neon-blue); font-size:1.15rem; font-weight:700;">₹ ${(estData.total_min || 0).toLocaleString()} – ₹ ${(estData.total_max || 0).toLocaleString()}</span>
                    </div>
                    <div class="approval-actions">
                        <button class="btn-approve" onclick="submitCustomerDecision('${jc.id}', 'approve', '${jc.vehicle_reg}')">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18"><polyline points="20 6 9 17 4 12"/></svg>
                            Authorize & Approve Service
                        </button>
                        <button class="btn-decline" onclick="submitCustomerDecision('${jc.id}', 'decline', '${jc.vehicle_reg}')">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                            Decline Service
                        </button>
                    </div>
                    <div class="approval-auth-note">
                        🔒 Authenticated for Vehicle Reg: <strong>${jc.vehicle_reg}</strong>. Mechanics and garage staff cannot modify this estimate.
                    </div>
                </div>`;
            } else if (approvalStat === 'PENDING_COMPANY_REVIEW') {
                approvalArea.innerHTML = `
                <div class="approval-card status-pending-review">
                    <div class="approval-header">
                        <div class="approval-title-wrap">
                            <span class="approval-icon">🔍</span>
                            <div>
                                <h3 class="approval-title">Independent Company Review in Progress</h3>
                                <div class="approval-subtitle">Unbiased Diagnostic Workflow</div>
                            </div>
                        </div>
                        <span class="approval-badge">Under Technical Review</span>
                    </div>
                    <div class="approval-body-text">
                        To guarantee fair and honest service without garage bias, our company technical review team is actively inspecting the AI diagnostic findings for your vehicle. An official quotation will be presented here for your approval shortly.
                    </div>
                </div>`;
            } else if (approvalStat === 'CUSTOMER_APPROVED') {
                approvalArea.innerHTML = `
                <div class="approval-card status-approved">
                    <div class="approval-header">
                        <div class="approval-title-wrap">
                            <span class="approval-icon">✅</span>
                            <div>
                                <h3 class="approval-title">Service Authorized by Customer</h3>
                                <div class="approval-subtitle">Approved Estimate · Repair in Progress</div>
                            </div>
                        </div>
                        <span class="approval-badge" style="color:var(--success); border-color:var(--success);">Authorized</span>
                    </div>
                    <div class="approval-body-text" style="border-left-color:var(--success);">
                        You have approved the repair estimate. A mechanic and bay have been assigned, and the repair procedure is underway according to company standards.
                    </div>
                </div>`;
            } else if (approvalStat === 'CUSTOMER_DECLINED') {
                approvalArea.innerHTML = `
                <div class="approval-card status-declined">
                    <div class="approval-header">
                        <div class="approval-title-wrap">
                            <span class="approval-icon">✕</span>
                            <div>
                                <h3 class="approval-title">Service Estimate Declined</h3>
                                <div class="approval-subtitle">Closed Request</div>
                            </div>
                        </div>
                        <span class="approval-badge" style="color:var(--danger); border-color:var(--danger);">Declined</span>
                    </div>
                    <div class="approval-body-text" style="border-left-color:var(--danger);">
                        You declined the repair estimate. The service request has been closed without charge. Contact customer support if you need further assistance.
                    </div>
                </div>`;
            } else {
                approvalArea.innerHTML = '';
            }
        }

        // Timeline — use server-provided timeline with done/current states
        if (timeline && timeline.length > 0) {
            // Find the current step: last done step
            let currentIdx = -1;
            for (let i = timeline.length - 1; i >= 0; i--) {
                if (timeline[i].done) { currentIdx = i; break; }
            }

            document.getElementById('timeline-body').innerHTML = `
                <div class="timeline">
                    ${timeline.map((step, i) => {
                        let cls = '';
                        if (step.done && i < currentIdx) cls = 'done';
                        else if (i === currentIdx) cls = 'current';
                        let icon = cls === 'done' ? '✓' : (i === currentIdx ? '●' : (i + 1));
                        return `<div class="tl-step ${cls}"><div class="tl-dot">${icon}</div><div class="tl-content"><div class="tl-title">${step.label}</div>${step.time ? `<div class="tl-time">${step.time}</div>` : ''}</div></div>`;
                    }).join('')}
                </div>`;
        } else {
            document.getElementById('timeline-body').innerHTML = `<div class="empty-state"><div class="empty-icon">📍</div><p class="empty-text">No timeline data</p></div>`;
        }

        // Mechanic
        if (mech) {
            const initials = (mech.name || 'N/A').split(' ').map(w => w[0]).join('').toUpperCase();
            document.getElementById('mechanic-body').innerHTML = `
                <div class="mech-info">
                    <div class="mech-avatar">${initials}</div>
                    <div><div class="mech-name">${mech.name}</div><div class="mech-spec">${mech.specialization || 'General'} Specialist</div></div>
                </div>
                <div class="mech-stats">
                    <div class="mech-stat"><div class="mech-stat-val">${mech.skill_level || 'N/A'}</div><div class="mech-stat-lbl">Skill Level</div></div>
                    <div class="mech-stat"><div class="mech-stat-val" style="color:${mech.status === 'Available' ? '#10b981' : '#38bdf8'}">${mech.status || 'N/A'}</div><div class="mech-stat-lbl">Status</div></div>
                </div>`;
        } else {
            document.getElementById('mechanic-body').innerHTML = `<div class="empty-state"><div class="empty-icon">⏳</div><p class="empty-text">Mechanic will be assigned soon</p></div>`;
        }

        // Quotation
        if (quote) {
            let actualHtml = '';
            if (quote.actual_cost) {
                actualHtml = `<div class="q-total" style="margin-top:8px"><span>Final Cost</span><span style="color:#10b981">₹ ${parseInt(quote.actual_cost).toLocaleString()}</span></div>`;
            }
            document.getElementById('quotation-body').innerHTML = `
                <table class="q-table">
                    <thead><tr><th>Item</th><th>Amount</th></tr></thead>
                    <tbody>
                        <tr><td>Parts Cost</td><td>₹ ${(quote.parts_cost || 0).toLocaleString()}</td></tr>
                        <tr><td>Labour (${quote.labour_hours || 0} hrs × ₹${quote.labour_rate}/hr)</td><td>₹ ${(quote.labour_cost || 0).toLocaleString()}</td></tr>
                    </tbody>
                </table>
                <div class="q-total"><span>Estimated Total</span><span>₹ ${(quote.total_min || 0).toLocaleString()} – ₹ ${(quote.total_max || 0).toLocaleString()}</span></div>
                ${actualHtml}
                <p style="margin-top:12px;font-size:0.78em;opacity:0.5">Diagnosed Issue: ${quote.fault}</p>`;
        } else {
            document.getElementById('quotation-body').innerHTML = `<div class="empty-state"><div class="empty-icon">💰</div><p class="empty-text">Quotation available after inspection</p></div>`;
        }

        // Parts
        if (parts && parts.length > 0) {
            document.getElementById('parts-body').innerHTML = parts.map(p => {
                const stockClass = p.in_stock ? 'in-stock' : 'ordering';
                const stockText = p.in_stock ? '✓ In Stock' : '⏳ Ordering';
                return `<div class="part-item">
                    <div><span class="part-name">${p.name}</span><span class="part-cat">${p.category || p.part_id}</span></div>
                    <div style="text-align:right"><span class="part-price">₹ ${(p.unit_price || 0).toLocaleString()}</span><span class="part-stock ${stockClass}">${stockText}</span></div>
                </div>`;
            }).join('');
        } else {
            document.getElementById('parts-body').innerHTML = `<div class="empty-state"><div class="empty-icon">🔩</div><p class="empty-text">No parts required or sourcing in progress</p></div>`;
        }

    } catch (e) {
        showToast('Could not load vehicle details', 'error');
    }
}

function backToResults() {
    document.getElementById('vehicle-detail').classList.add('hidden');
    searchVehicle();
}

// ━━━ Book Service ━━━
async function bookService() {
    const make = document.getElementById('v-make').value.trim();
    const model = document.getElementById('v-model').value.trim();
    const year = document.getElementById('v-year').value.trim();
    const reg = document.getElementById('v-reg').value.trim();
    const name = document.getElementById('o-name').value.trim();
    const phone = document.getElementById('o-phone').value.trim();
    const complaint = document.getElementById('v-complaint').value.trim();

    if (!make || !model || !reg || !complaint) {
        showToast('Please fill in all required fields', 'error');
        return;
    }

    const btn = document.getElementById('book-btn');
    btn.disabled = true;
    btn.innerHTML = '<span>Submitting...</span>';

    try {
        const res = await fetch(`${API_BASE}/jobcards`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                vehicle_make: make, vehicle_model: model,
                vehicle_year: year, vehicle_reg: reg,
                owner_name: name, owner_phone: phone,
                complaint: complaint
            })
        });
        const data = await res.json();
        if (data.jobcard) {
            showToast(`Booking created: ${data.jobcard.jobcard_id}`, 'success');
            // Clear form
            ['v-make','v-model','v-year','v-reg','o-name','o-phone','v-complaint'].forEach(id => {
                document.getElementById(id).value = '';
            });
        } else {
            showToast('Failed to create booking', 'error');
        }
    } catch (e) {
        showToast('Could not connect to server', 'error');
    }

    btn.disabled = false;
    btn.innerHTML = '<span>Submit Booking</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
}

// ━━━ Toast ━━━
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4500);
}

// ━━━ Feature 2: Customer Estimate Decision Handler ━━━
window.submitCustomerDecision = async function(jcId, decision, defaultReg) {
    let identifier = defaultReg;
    if (!identifier) {
        identifier = prompt("Please confirm your Vehicle Registration Number or Owner Phone to authenticate:");
        if (!identifier) return;
    }

    const confirmMsg = decision === 'approve'
        ? "Authorize Repair Service?\n\nBy confirming, you authorize our garage to proceed with the independently verified repair items and parts."
        : "Decline Service Estimate?\n\nBy declining, this service ticket will be cancelled and closed.";

    if (!confirm(confirmMsg)) return;

    try {
        const res = await fetch(`${API_BASE}/customer/approval`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                jobcard_id: jcId,
                decision: decision,
                customer_identifier: identifier
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            // Refresh detail view
            setTimeout(() => showDetail(jcId), 400);
        } else {
            showToast(data.message || 'Action failed', 'error');
        }
    } catch (e) {
        showToast('Network error while processing your decision', 'error');
    }
};
