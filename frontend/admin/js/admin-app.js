/**
 * Nova AI — Admin Dashboard Application
 */
document.addEventListener('DOMContentLoaded', () => {
    const $ = s => document.querySelector(s);
    const $$ = s => document.querySelectorAll(s);
    let currentTab = 'overview';
    const adminRole = sessionStorage.getItem('admin_role') || 'super_admin';
    const adminName = sessionStorage.getItem('admin_name') || 'Admin';

    // Set admin info
    const nameEl = $('#admin-name');
    const roleEl = $('#admin-role');
    if (nameEl) nameEl.textContent = adminName;
    if (roleEl) roleEl.textContent = adminRole.replace('_', ' ');

    // ━━━ Tab Navigation ━━━
    $$('.admin-nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.dataset.tab;
            if (tab) switchTab(tab);
        });
    });

    function switchTab(tab) {
        currentTab = tab;
        $$('.admin-nav-item').forEach(n => n.classList.toggle('active', n.dataset.tab === tab));
        $$('.admin-tab').forEach(t => t.classList.toggle('active', t.id === `tab-${tab}`));
        loadTabData(tab);
    }

    function loadTabData(tab) {
        const loaders = {
            overview: loadOverview,
            workforce: loadWorkforce,
            attendance: loadAttendance,
            payroll: loadPayroll,
            insurance: loadInsurance
        };
        if (loaders[tab]) loaders[tab]();
    }

    // ━━━ Toast ━━━
    function toast(msg, type = 'info') {
        const c = $('#admin-toast');
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        t.textContent = msg;
        c.appendChild(t);
        setTimeout(() => t.remove(), 4500);
    }

    // ━━━ OVERVIEW TAB ━━━
    async function loadOverview() {
        try {
            const data = await adminApi.getDashboard();
            $('#ov-total-mechanics').textContent = data.total_mechanics || 0;
            $('#ov-present-today').textContent = data.present_today || 0;
            $('#ov-jobs-completed').textContent = data.total_jobs_completed || 0;
            $('#ov-jobs-pending').textContent = data.total_jobs_pending || 0;
            $('#ov-salary-pending').textContent = '₹' + (data.salary_summary?.total_pending || 0).toLocaleString();
            $('#ov-insurance-expiring').textContent = data.expiring_soon || 0;

            // MOTM
            const motm = data.mechanic_of_month;
            if (motm) {
                $('#motm-name').textContent = motm.name;
                $('#motm-detail').textContent = `${motm.completed_jobs} jobs | ${motm.present_days} days present | Score: ${motm.score}`;
            } else {
                $('#motm-name').textContent = 'No data yet';
                $('#motm-detail').textContent = 'Mark attendance and complete jobs to see results';
            }

            // Live Status
            const live = data.live_status || [];
            $('#live-status-grid').innerHTML = live.length ? live.map(m => `
                <div class="live-card ${m.vehicles.length ? 'active' : ''}">
                    <div class="live-header">
                        <div class="live-avatar">${(m.name||'?')[0]}</div>
                        <div>
                            <div class="live-name">${m.name}</div>
                            <div class="live-spec">${m.specialization} | ${m.status}</div>
                        </div>
                        <span class="badge-status ${m.status.toLowerCase()}">${m.status}</span>
                    </div>
                    ${m.vehicles.length ? `<div class="live-vehicles">${m.vehicles.map(v => `
                        <div class="live-vehicle">
                            <span class="lv-id">${v.jobcard_id}</span>
                            <span class="lv-car">${v.vehicle}</span>
                            <span class="lv-reg">${v.vehicle_reg}</span>
                            <span class="badge-status ${(v.priority||'').toLowerCase()}">${v.priority}</span>
                        </div>
                    `).join('')}</div>` : '<div class="live-empty">No active vehicles</div>'}
                </div>
            `).join('') : '<div class="empty-state"><div class="empty-state-text">No mechanics found</div></div>';
        } catch (e) { console.error(e); toast('Failed to load overview', 'error'); }
    }

    // ━━━ WORKFORCE TAB ━━━
    async function loadWorkforce() {
        try {
            const data = await adminApi.getPerformance();
            const perfs = data.performance || [];
            $('#workforce-table').innerHTML = perfs.length ? `<table><thead><tr>
                <th>Mechanic</th><th>Specialization</th><th>Total Jobs</th><th>Completed</th>
                <th>Completion %</th><th>Avg Time</th><th>Attendance %</th><th>Active Tasks</th>
            </tr></thead><tbody>${perfs.map(p => `<tr>
                <td><strong>${p.name}</strong></td>
                <td>${p.specialization}</td>
                <td class="text-mono">${p.total_jobs}</td>
                <td class="text-mono text-accent">${p.completed_jobs}</td>
                <td><div class="perf-bar-wrap"><div class="perf-bar" style="width:${p.completion_rate}%"></div><span>${p.completion_rate}%</span></div></td>
                <td>${p.avg_repair_time_hrs}h</td>
                <td>${p.attendance_rate}%</td>
                <td class="text-mono">${p.active_pipeline_tasks}</td>
            </tr>`).join('')}</tbody></table>` : '<div class="empty-state"><div class="empty-state-text">No performance data yet</div></div>';

            // Leaderboard
            const sorted = [...perfs].sort((a, b) => b.completed_jobs - a.completed_jobs);
            $('#leaderboard').innerHTML = sorted.slice(0, 5).map((p, i) => `
                <div class="lb-item ${i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''}">
                    <span class="lb-rank">#${i + 1}</span>
                    <span class="lb-name">${p.name}</span>
                    <span class="lb-score">${p.completed_jobs} jobs</span>
                </div>
            `).join('') || '<div class="empty-state"><div class="empty-state-text">No data</div></div>';
        } catch (e) { console.error(e); toast('Failed to load workforce', 'error'); }
    }

    // ━━━ ATTENDANCE TAB ━━━
    async function loadAttendance() {
        try {
            const data = await adminApi.getAttendance();
            const att = data.attendance || [];
            $('#attendance-grid').innerHTML = att.length ? att.map(a => `
                <div class="att-card ${a.marked ? '' : 'unmarked'}">
                    <div class="att-name">${a.mechanic_name}</div>
                    <div class="att-id">${a.mechanic_id}</div>
                    <div class="att-status">
                        <span class="badge-status ${(a.status||'').toLowerCase().replace(' ','-')}">${a.status}</span>
                    </div>
                    ${!a.marked ? `<div class="att-actions">
                        <button class="btn btn-success btn-xs" onclick="window.markAtt('${a.mechanic_id}','${a.mechanic_name}','Present')">Present</button>
                        <button class="btn btn-danger btn-xs" onclick="window.markAtt('${a.mechanic_id}','${a.mechanic_name}','Absent')">Absent</button>
                        <button class="btn btn-secondary btn-xs" onclick="window.markAtt('${a.mechanic_id}','${a.mechanic_name}','Half-Day')">Half</button>
                    </div>` : `<div class="att-time">In: ${a.check_in || '-'}</div>`}
                </div>
            `).join('') : '<div class="empty-state"><div class="empty-state-text">No mechanics found. Add mechanics first.</div></div>';
        } catch (e) { console.error(e); toast('Failed to load attendance', 'error'); }
    }

    window.markAtt = async (id, name, status) => {
        try {
            await adminApi.markAttendance({ mechanic_id: id, mechanic_name: name, status });
            toast(`${name} marked as ${status}`, 'success');
            loadAttendance();
        } catch (e) { toast('Error marking attendance', 'error'); }
    };

    // ━━━ PAYROLL TAB ━━━
    async function loadPayroll() {
        try {
            const [salData, sumData, mechData] = await Promise.all([
                adminApi.getSalaries(), adminApi.getSalarySummary(), adminApi.getMechanics()
            ]);
            const sals = salData.salaries || [];
            const mechs = mechData.mechanics || [];

            $('#pay-total-paid').textContent = '₹' + (sumData.total_paid || 0).toLocaleString();
            $('#pay-total-pending').textContent = '₹' + (sumData.total_pending || 0).toLocaleString();
            $('#pay-unpaid-count').textContent = sumData.unpaid_count || 0;

            $('#salary-table').innerHTML = sals.length ? `<table><thead><tr>
                <th>ID</th><th>Mechanic</th><th>Base</th><th>Bonus</th><th>Deductions</th>
                <th>Net</th><th>Month</th><th>Status</th><th>Actions</th>
            </tr></thead><tbody>${sals.map(s => `<tr>
                <td class="text-mono">${s.salary_id}</td>
                <td>${s.mechanic_name}</td>
                <td>₹${parseInt(s.base_salary).toLocaleString()}</td>
                <td class="text-accent">₹${parseInt(s.bonus || 0).toLocaleString()}</td>
                <td class="text-danger">₹${parseInt(s.deductions || 0).toLocaleString()}</td>
                <td><strong>₹${parseInt(s.net_salary).toLocaleString()}</strong></td>
                <td>${s.month}/${s.year}</td>
                <td><span class="badge-status ${s.paid === 'Yes' ? 'completed' : 'pending'}">${s.paid === 'Yes' ? 'Paid' : 'Unpaid'}</span></td>
                <td>${s.paid !== 'Yes' ? `<button class="btn btn-success btn-xs" onclick="window.paySal('${s.salary_id}')">Pay</button>` : `<span class="text-muted">${s.paid_date}</span>`}</td>
            </tr>`).join('')}</tbody></table>` : '<div class="empty-state"><div class="empty-state-text">No salary records. Create one below.</div></div>';

            // Populate mechanic dropdown for new salary
            const sel = $('#sal-mechanic');
            if (sel) {
                sel.innerHTML = mechs.map(m => `<option value="${m.mechanic_id}" data-name="${m.name}">${m.name} (${m.mechanic_id})</option>`).join('');
                if (mechs.length > 0) sel.dispatchEvent(new Event('change'));
            }
        } catch (e) { console.error(e); toast('Failed to load payroll', 'error'); }
    }

    window.paySal = async (id) => {
        try {
            await adminApi.paySalary(id);
            toast('Salary marked as paid', 'success');
            loadPayroll();
        } catch (e) { toast('Error', 'error'); }
    };

    // Create salary
    const selMechanic = $('#sal-mechanic');
    if (selMechanic) {
        selMechanic.addEventListener('change', async () => {
            const val = selMechanic.value;
            if (!val) return;
            try {
                const res = await adminApi.autoCalculateSalary(val);
                if (res.auto_calculated) {
                    $('#sal-base').value = res.auto_calculated.base_salary;
                    $('#sal-bonus').value = res.auto_calculated.bonus;
                    $('#sal-notes').value = res.auto_calculated.notes;
                    toast('Auto-calculated based on performance!', 'info');
                }
            } catch (e) {
                console.error("Auto calculation failed", e);
            }
        });
    }

    const salForm = $('#create-salary-btn');
    if (salForm) salForm.addEventListener('click', async () => {
        const sel = $('#sal-mechanic');
        const opt = sel.options[sel.selectedIndex];
        if (!opt) return;
        const data = {
            mechanic_id: sel.value,
            mechanic_name: opt.dataset.name,
            base_salary: parseInt($('#sal-base').value) || 15000,
            bonus: parseInt($('#sal-bonus').value) || 0,
            deductions: parseInt($('#sal-deductions').value) || 0,
            notes: $('#sal-notes').value || ''
        };
        try {
            const res = await adminApi.createSalary(data);
            if (res.salary?.error) { toast(res.salary.error, 'warning'); }
            else { toast('Salary record created!', 'success'); loadPayroll(); }
        } catch (e) { toast('Error creating salary', 'error'); }
    });

    // ━━━ INSURANCE TAB ━━━
    async function loadInsurance() {
        try {
            const [insData, expData] = await Promise.all([
                adminApi.getInsurance(), adminApi.getExpiringInsurance()
            ]);
            const ins = insData.insurance || [];
            const exp = expData.expiring || [];

            $('#ins-total').textContent = ins.length;
            $('#ins-expiring').textContent = exp.length;

            $('#insurance-table').innerHTML = ins.length ? `<table><thead><tr>
                <th>ID</th><th>Vehicle</th><th>Owner</th><th>Provider</th>
                <th>Policy #</th><th>Expiry</th><th>Type</th><th>Premium</th><th>Status</th><th>Actions</th>
            </tr></thead><tbody>${ins.map(i => `<tr>
                <td class="text-mono">${i.insurance_id}</td>
                <td class="text-accent">${i.vehicle_reg}</td>
                <td>${i.owner_name}</td>
                <td>${i.provider}</td>
                <td class="text-mono">${i.policy_number}</td>
                <td>${i.expiry_date}</td>
                <td>${i.type}</td>
                <td>₹${parseInt(i.premium || 0).toLocaleString()}</td>
                <td><span class="badge-status ${(i.status||'active').toLowerCase()}">${i.status}</span></td>
                <td><button class="btn btn-danger btn-xs" onclick="window.delIns('${i.insurance_id}')">Del</button></td>
            </tr>`).join('')}</tbody></table>` : '<div class="empty-state"><div class="empty-state-text">No insurance records</div></div>';

            if (exp.length) {
                $('#expiring-alerts').innerHTML = exp.map(e => `
                    <div class="exp-alert ${e.days_until_expiry < 0 ? 'expired' : e.days_until_expiry < 7 ? 'critical' : ''}">
                        <strong>${e.vehicle_reg}</strong> — ${e.provider} — 
                        ${e.days_until_expiry < 0 ? `<span class="text-danger">Expired ${Math.abs(e.days_until_expiry)} days ago</span>` :
                          `<span class="text-warning">Expires in ${e.days_until_expiry} days</span>`}
                    </div>
                `).join('');
            } else {
                $('#expiring-alerts').innerHTML = '<div class="empty-state"><div class="empty-state-text">No expiring policies</div></div>';
            }
        } catch (e) { console.error(e); toast('Failed to load insurance', 'error'); }
    }

    window.delIns = async (id) => {
        if (confirm('Delete this insurance record?')) {
            try { await adminApi.deleteInsurance(id); toast('Deleted', 'info'); loadInsurance(); }
            catch (e) { toast('Error', 'error'); }
        }
    };

    // Add insurance
    const insForm = $('#add-insurance-btn');
    if (insForm) insForm.addEventListener('click', async () => {
        const data = {
            vehicle_reg: $('#ins-reg').value,
            owner_name: $('#ins-owner').value,
            owner_phone: $('#ins-phone').value || '',
            provider: $('#ins-provider').value,
            policy_number: $('#ins-policy').value,
            expiry_date: $('#ins-expiry').value,
            type: $('#ins-type').value,
            premium: parseInt($('#ins-premium').value) || 0,
            notes: ''
        };
        if (!data.vehicle_reg || !data.provider) { toast('Vehicle reg and provider are required', 'warning'); return; }
        try {
            await adminApi.addInsurance(data);
            toast('Insurance added!', 'success');
            loadInsurance();
            // Clear form
            ['ins-reg','ins-owner','ins-phone','ins-provider','ins-policy','ins-expiry','ins-premium'].forEach(id => { const el = $(`#${id}`); if(el) el.value = ''; });
        } catch (e) { toast('Error', 'error'); }
    });

    // ━━━ Logout ━━━
    const logoutBtn = $('#logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => {
        sessionStorage.clear();
        window.location.href = '/';
    });

    // ━━━ Init ━━━
    loadOverview();
});
