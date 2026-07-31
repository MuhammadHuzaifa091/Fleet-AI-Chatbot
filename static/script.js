/**
 * AI - Telemetrix | Premium Fleet Intelligence v5.0
 * Fully upgraded architecture with role-based filtering, advanced charts,
 * and high-fidelity tactical maps.
 */

// Initialize Lucide Icons
function safeCreateIcons() {
    try { lucide.createIcons(); } catch (e) { }
}

window.onerror = function (msg, url, line, col, error) {
    console.error("Global System Error:", msg, "at", url, ":", line);
    return false;
};

/**
 * Universal View Switcher
 * Transitions between SPA sub-views and handles initialization logic.
 */
function switchView(view) {
    if (!view) return;
    console.log(`Switching to view: ${view}`);
    
    // Update Nav UI
    document.querySelectorAll('.nav-item').forEach(i => {
        i.classList.remove('active');
        if (i.getAttribute('data-view') === view) i.classList.add('active');
    });

    // Update View Containers
    document.querySelectorAll('.sub-view').forEach(v => {
        v.classList.remove('active-view');
        v.classList.add('hidden-view');
        if (v.id === `view-${view}`) {
            v.classList.remove('hidden-view');
            v.classList.add('active-view');
        }
    });

    // View-specific Init logic
    if (view === 'analytics') if (typeof loadDashboardData === 'function') loadDashboardData();
    if (view === 'vehicle-intel') if (typeof initVehicleIntel === 'function') initVehicleIntel();
    if (view === 'fuel') if (typeof initFuelAnalytics === 'function') initFuelAnalytics();
    if (view === 'maintenance') if (typeof initMaintenanceCenter === 'function') initMaintenanceCenter();
    if (view === 'planner') if (typeof initPlanner === 'function') initPlanner();
    if (view === 'workshop') if (typeof initWorkshop === 'function') initWorkshop();
    if (view === 'data-import') if (typeof initDataImportView === 'function') initDataImportView();
    if (view === 'alerts') if (typeof loadAlertsPage === 'function') loadAlertsPage();
    if (view === 'driver') if (typeof initDriverView === 'function') initDriverView();
    
    if (view === 'map') {
        setTimeout(() => {
            if (typeof initMap === 'function') initMap();
            if (typeof map !== 'undefined' && map) {
                map.invalidateSize();
                setTimeout(() => map.invalidateSize(), 500);
            }
            if (typeof startMapUpdates === 'function') startMapUpdates();
        }, 400);
    } else {
        if (typeof stopMapUpdates === 'function') stopMapUpdates();
    }
}
window.switchView = switchView;

console.log("AI - Telemetrix Engine Starting...");

// ── Dynamic Greeting ────────────────────────────────────────────
function updateGreeting() {
    const el = document.getElementById('greeting-title');
    if (!el) return;
    const hour = new Date().getHours();
    let salutation, emoji;
    if (hour < 12)      { salutation = 'Good morning';  emoji = '☀️'; }
    else if (hour < 17) { salutation = 'Good afternoon'; emoji = '👋'; }
    else                { salutation = 'Good evening';   emoji = '🌙'; }

    // Try to get username from the displayed user element
    const userEl = document.getElementById('user-name-display') || document.querySelector('.user-name');
    const name = userEl ? userEl.textContent.trim().split(' ')[0] : ''; // first name only
    el.textContent = name ? `${salutation}, ${name} ${emoji}` : `${salutation} ${emoji}`;
}

document.addEventListener('DOMContentLoaded', () => {
    updateGreeting();
    setInterval(updateGreeting, 60000); // refresh every minute

    // Initialize Fleet Lottie animations
    try {
        if (typeof lottie !== 'undefined') {
            const lottieConfigs = [
                { id: 'fleet-lottie', path: '/static/wired-gradient-860-electric-car-hover-pinch.json' },
                { id: 'ops-lottie', path: '/static/wired-gradient-1121-iota-internet-of-things-hover-pinch.json' },
                { id: 'alerts-lottie', path: '/static/wired-gradient-1140-error-hover-enlarge.json' }
            ];
            lottieConfigs.forEach(cfg => {
                const el = document.getElementById(cfg.id);
                if (el) {
                    lottie.loadAnimation({
                        container: el,
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: cfg.path
                    });
                }
            });
        }
    } catch (e) { console.warn('Lottie init failed:', e); }
});

// DOM Elements will be initialized in initAuthElements()

// --- FleetOS Dashboard Logic (Matching Image) ---
// --- Dashboard V2 Elements ---
let fleetStatusDonutChart = null;
let matrixSearchTerm = '';
let matrixStatusFilter = '';

function updateExecutiveDashboard(data) {
    if (!data) return;
    const k = {
        total: data.kpis?.total || data.total_vehicles || 0,
        online: data.kpis?.active || data.kpis?.online || 0,
        moving: data.kpis?.moving || data.kpis?.active || 0,
        idle: data.kpis?.idle || data.kpis?.stationary || 0,
        offline: data.kpis?.stale || data.kpis?.offline || 0,
        completedToday: data.kpis?.completedToday || 0,
        totalDistanceKm: data.kpis?.totalDistanceKm || 0
    };

    // 1. Update KPI Main Values
    animateCounter('kpi-total-v2', k.total);
    animateCounter('kpi-online-v2', k.online);
    animateCounter('kpi-moving-v2', k.moving);
    animateCounter('kpi-idle-v2', k.idle); // Not in primary UI but kept for logic
    animateCounter('kpi-offline-v2', k.offline);

    const calcPct = (val) => k.total > 0 ? Math.round((val / k.total) * 100) : 0;
    
    // 2. Update Trends/Pct Labels
    const setPct = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = `${calcPct(val)}%`;
    };

    setPct('kpi-online-pct', k.online);
    setPct('kpi-moving-pct', k.moving);
    setPct('kpi-offline-pct', k.offline);

    // Trips KPI
    const activeTrips = k.moving || 0;
    const completedTrips = k.completedToday || 0;
    animateCounter('kpi-trips-total-v2', activeTrips + completedTrips);
    if (document.getElementById('kpi-trips-running')) document.getElementById('kpi-trips-running').innerText = activeTrips;
    if (document.getElementById('kpi-trips-completed')) document.getElementById('kpi-trips-completed').innerText = completedTrips;
    if (document.getElementById('kpi-total-distance-v2')) {
        const distKm = k.totalDistanceKm || 0;
        document.getElementById('kpi-total-distance-v2').innerHTML = Math.round(distKm).toLocaleString() + ' <small>km</small>';
    }
    
    // Alerts KPI
    const alerts = (data.recent_events || []).filter(e => alertPreferences[e.type] !== false);
    animateCounter('kpi-alerts-count-v2', alerts.length);
    if (document.getElementById('selected-alerts-summary')) {
        const activeAlerts = TRACCAR_EVENT_TYPES.filter(t => alertPreferences[t.id] !== false).length;
        document.getElementById('selected-alerts-summary').innerText = `Selected (${activeAlerts}/${TRACCAR_EVENT_TYPES.length})`;
    }

    // 3. Update Visual Widgets
    updateStatusDonutV2(k);
    updateFleetInsights(k, data);
    updateFleetHealthScore(k);
    
    // Filter events by alert preferences for timeline feed
    const filteredTimelineEvents = (data.recent_events || []).filter(e => alertPreferences[e.type] !== false);
    updateDashboardTimelineFeed(filteredTimelineEvents);
    
    // Populate notifications from events
    if (typeof populateNotifFromEvents === 'function') {
        populateNotifFromEvents(filteredTimelineEvents);
    }
    if (typeof updateNotifBadge === 'function') {
        updateNotifBadge();
    }
    
    updateTripsSparkline();

    // Re-init icons for new cards
    lucide.createIcons();
}

let kpiTripsChart = null;
function updateTripsSparkline() {
    const ctx = document.getElementById('kpiTripsSparkline');
    if (!ctx) return;
    

    if (kpiTripsChart) kpiTripsChart.destroy();

    const emptyData = [];
    kpiTripsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: emptyData.map((_, i) => i),
            datasets: [{
                data: emptyData,
                borderColor: '#3b82f6',
                borderWidth: 3,
                fill: true,
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: { x: { display: false }, y: { display: false } }
        }
    });
}

function updateStatusDonutV2(stats) {
    const ctx = document.getElementById('fleetStatusDonutChart');
    if (!ctx) return;

    const colors = ['#059669', '#3b82f6', '#d97706', '#dc2626'];
    const dataPoints = [stats.online, stats.moving, stats.idle, stats.offline];
    
    document.getElementById('donut-total-val').innerText = stats.total;
    document.getElementById('legend-online').innerText = stats.online;
    document.getElementById('legend-moving').innerText = stats.moving;
    document.getElementById('legend-idle').innerText = stats.idle;
    document.getElementById('legend-offline').innerText = stats.offline;

    if (fleetStatusDonutChart) {
        fleetStatusDonutChart.data.datasets[0].data = dataPoints;
        fleetStatusDonutChart.update();
    } else {
        fleetStatusDonutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Moving', 'Idle', 'Offline'],
                datasets: [{
                    data: dataPoints,
                    backgroundColor: colors,
                    hoverOffset: 25,
                    borderWidth: 4,
                    borderColor: 'transparent',
                    borderRadius: 10,
                    spacing: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '82%',
                plugins: { 
                    legend: { display: false }, 
                    tooltip: { 
                        backgroundColor: '#111827',
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        padding: 12,
                        cornerRadius: 12,
                        displayColors: true
                    }
                },
                animation: { animateRotate: true, animateScale: true }
            }
        });
    }
}

function updateFleetInsights(k, data) {
    const availability = k.total > 0 ? Math.round(((k.online + k.moving + k.idle) / k.total) * 100) : 0;
    const utilization = k.total > 0 ? Math.round((k.moving / k.total) * 100) : 0;
    const completion = k.total > 0 ? Math.round((k.online / k.total) * 100) : 0;
    const alertRate = data.recent_events ? (data.recent_events.length / 10).toFixed(1) : "0.0";

    const updateInsight = (id, val, barId) => {
        const el = document.getElementById(id);
        const bar = document.getElementById(barId);
        if (el) el.innerText = typeof val === 'number' ? `${val}%` : val;
        if (bar) bar.style.width = typeof val === 'number' ? `${val}%` : `${Math.min(parseFloat(val) * 10, 100)}%`;
    };

    updateInsight('insight-availability', availability, 'bar-availability');
    updateInsight('insight-utilization', utilization, 'bar-utilization');
    updateInsight('insight-completion', completion, 'bar-completion');
    updateInsight('insight-alert-rate', alertRate, 'bar-alerts');
}

async function loadKEFleetOverview() {
    try {
        const authH = { 'Authorization': `Bearer ${authToken}` };

        const [kemisRes, keLiveRes] = await Promise.all([
            fetch('/api/fleet/fdb/kemis-stats', { headers: authH }).catch(() => null),
            fetch('/api/fleet/fdb/ke-live', { headers: authH }).catch(() => null)
        ]);

        const kemisData = (kemisRes && kemisRes.ok) ? await kemisRes.json() : {};
        let keLive = { vehicles: [], total: 0, online: 0, offline: 0 };
        if (keLiveRes && keLiveRes.ok) {
            keLive = await keLiveRes.json();
        }

        const onlineDevices = (keLive.vehicles || []).filter(v => v.status === 'online');
        const kemisVehicles = kemisData.unique_vehicles || 0;
        const totalKE = keLive.total || parseInt(document.getElementById('fdb-stat-total')?.textContent?.replace(/,/g, '') || '1706');
        const onlineCount = keLive.online || onlineDevices.length;

        const badge = document.getElementById('ke-data-badge');
        if (badge) badge.textContent = `Live Status`;

        setTextSafe('ke-total-count', totalKE);
        setTextSafe('ke-online-count', onlineCount);
        setTextSafe('ke-offline-count', totalKE - onlineCount);
        setTextSafe('ke-mis-count', kemisVehicles);

        const listEl = document.getElementById('ke-online-list');
        if (listEl) {
            if (onlineCount === 0) {
                listEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-dim);">No KE vehicles online right now</div>';
            } else {
                listEl.innerHTML = '<div style="font-size:0.75rem;font-weight:700;color:var(--text-secondary);margin-bottom:8px;">Online KE Vehicles (' + onlineCount + ')</div>' +
                    onlineDevices.slice(0, 30).map(v => {
                        const keName = v.keName || v.name || v.uniqueId || 'Unknown';
                        const traccarName = v.name || '';
                        return '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--border-light);cursor:pointer;" onclick="openVehicleMIS(\'' + keName.replace(/'/g, "\\'") + '\')">' +
                            '<div style="display:flex;align-items:center;gap:8px;">' +
                            '<span style="width:8px;height:8px;border-radius:50%;background:#059669;"></span>' +
                            '<div>' +
                            '<span style="font-size:0.85rem;font-weight:600;color:var(--text-primary);">' + keName + '</span>' +
                            (traccarName && traccarName !== keName ? '<br><span style="font-size:0.7rem;color:var(--text-dim);">' + traccarName + '</span>' : '') +
                            '</div>' +
                            '</div>' +
                            '</div>';
                    }).join('');
            }
        }

        const misList = document.getElementById('ke-mis-quick-list');
        if (misList) {
            misList.innerHTML = '<div style="text-align:center;padding:16px;">' +
                '<p style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:12px;">' + kemisVehicles + ' vehicles with MIS data available</p>' +
                '<button onclick="document.querySelector(\'[data-view=data-import]\')?.click(); setTimeout(() => { const btn = document.querySelector(\'[onclick*=kemis]\'); if(btn) btn.click(); }, 300);" class="glass-btn primary-glow" style="padding:10px 20px;font-size:0.85rem;">Open KEMIS MIS Tab</button>' +
                '<p style="font-size:0.7rem;color:var(--text-dim);margin-top:8px;">Click any vehicle name in KEMIS table to view full MIS report</p>' +
                '</div>';
        }
    } catch (e) {
        console.error('KE Fleet overview error:', e);
    }
}

function setTextSafe(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function toggleKpiExpansion(type) {
    const cards = document.querySelectorAll('.dash-v2-kpi-card');
    cards.forEach(c => {
        if (c.id === `kpi-card-${type}`) {
            c.classList.toggle('expanded');
        } else {
            c.classList.remove('expanded');
        }
    });
}

function toggleAlertSelector(event) {
    event.stopPropagation();
    const modal = document.getElementById('alert-selection-modal');
    const overlay = document.querySelector('.modal-overlay');
    // modal is in index.html
    document.getElementById('alert-selection-modal').classList.add('active');
    document.querySelector('.modal-overlay').classList.add('active');
    initDashboardAlertSelectionGrid();
}

function closeAlertSelector() {
    document.getElementById('alert-selection-modal').classList.remove('active');
    document.querySelector('.modal-overlay').classList.remove('active');
}

function filterDashboardAlertTypes() {
    const search = document.getElementById('dashboard-alert-search').value.toLowerCase();
    document.querySelectorAll('#dashboard-alert-selection-grid .pref-item-detailed').forEach(item => {
        const label = item.textContent.toLowerCase();
        item.style.display = label.includes(search) ? 'flex' : 'none';
    });
}

function initDashboardAlertSelectionGrid() {
    const grid = document.getElementById('dashboard-alert-selection-grid');
    if (!grid) return;

    grid.innerHTML = TRACCAR_EVENT_TYPES.map(type => {
        const isChecked = alertPreferences[type.id] !== false;
        return `
            <div class="pref-item-detailed ${isChecked ? 'active' : ''}" data-type-id="${type.id}" onclick="toggleDashboardPref(this)">
                <input type="checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleDashboardPref(this.parentElement)">
                <span>${type.label}</span>
            </div>
        `;
    }).join('');
}

function toggleDashboardPref(el) {
    const checkbox = el.querySelector('input');
    checkbox.checked = !checkbox.checked;
    const typeId = el.dataset.typeId;
    alertPreferences[typeId] = checkbox.checked;
    el.classList.toggle('active', checkbox.checked);
}

function selectAllDashboardAlerts(enable) {
    document.querySelectorAll('#dashboard-alert-selection-grid .pref-item-detailed').forEach(item => {
        const checkbox = item.querySelector('input');
        checkbox.checked = enable;
        const typeId = item.dataset.typeId;
        alertPreferences[typeId] = enable;
        item.classList.toggle('active', enable);
    });
}

async function saveDashboardAlertPreferences() {
    const saveBtn = document.getElementById('save-dashboard-alerts-btn');
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="spin" data-lucide="loader-2" style="width:14px;"></i> Saving...';
    safeCreateIcons();

    const newPrefs = {};
    document.querySelectorAll('#dashboard-alert-selection-grid .pref-item-detailed').forEach(item => {
        const typeId = item.dataset.typeId;
        const isChecked = item.querySelector('input').checked;
        newPrefs[typeId] = isChecked;
    });

    try {
        const resp = await fetch('/api/v1/settings/alert-preferences', {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newPrefs)
        });

        if (resp.ok) {
            alertPreferences = newPrefs;
            showNotification('Dashboard alerts updated successfully.', 'success');
            if (typeof addNotification === 'function') {
                const activeCount = Object.values(newPrefs).filter(v => v !== false).length;
                addNotification('info', 'Alert Preferences Updated', `${activeCount} alert type${activeCount !== 1 ? 's' : ''} now active.`, 'system');
            }
            closeAlertSelector();
            loadDashboardData();
        } else {
            throw new Error('Sync failed');
        }
    } catch (e) {
        console.error("Save Dashboard Prefs Error:", e);
        showNotification('Update failed. Connection error.', 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalText;
        safeCreateIcons();
    }
}

async function loadAlertPreferences() {
    if (!authToken) return;
    try {
        const resp = await fetch('/api/v1/settings/alert-preferences', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            const data = await resp.json();
            if (data.preferences) {
                alertPreferences = data.preferences;
            }
        }
    } catch (e) {
        console.log("Using default alert preferences.");
    }
}

function filterMatrixByStatus(status) {
    matrixStatusFilter = status;
    // Update matrix filter pills
    document.querySelectorAll('.matrix-filter-pill').forEach(pill => {
        const txt = pill.innerText.toLowerCase();
        pill.classList.toggle('active', (status === '' && txt === 'all') || txt === status);
    });
    // Sync header quick-status pills
    document.querySelectorAll('.quick-status-group .status-pill-v2').forEach(pill => {
        pill.classList.toggle('active', pill.classList.contains(status));
    });
    filterMatrixTable();
}

function updateFleetHealthScore(k) {
    const scoreEl = document.getElementById('fleet-health-score');
    const ringEl = document.getElementById('fleet-health-ring');
    const badgeEl = document.getElementById('health-status-badge');
    if (!scoreEl) return;
    
    let score = 100;
    if (k.total > 0) {
        score -= (k.offline / k.total) * 40;
    }
    const finalScore = Math.max(Math.min(Math.round(score), 100), 0);
    scoreEl.innerText = finalScore;
    
    let color = 'var(--brand-success)';
    let badgeText = 'Excellent';
    let badgeClass = 'success';
    if (finalScore <= 50) {
        color = 'var(--brand-danger)';
        badgeText = 'Critical';
        badgeClass = 'danger';
    } else if (finalScore <= 80) {
        color = 'var(--brand-warning)';
        badgeText = 'Needs Attention';
        badgeClass = 'warning';
    }
    scoreEl.style.color = color;

    if (ringEl) {
        const circumference = 2 * Math.PI * 52;
        const offset = circumference - (finalScore / 100) * circumference;
        ringEl.style.stroke = color;
        ringEl.style.strokeDasharray = `${circumference} ${circumference}`;
        ringEl.style.strokeDashoffset = offset;
    }

    if (badgeEl) {
        badgeEl.className = `stats-badge ${badgeClass}`;
        badgeEl.innerText = badgeText;
    }
}

function getTimelineEventMeta(type) {
    const t = (type || '').toLowerCase();
    if (t.includes('overspeed')) return { icon: 'zap', color: '#f59e0b', label: 'Overspeed Alert' };
    if (t.includes('offline')) return { icon: 'wifi-off', color: '#64748b', label: 'Connectivity Loss' };
    if (t.includes('geofence')) return { icon: 'map-pin', color: '#8b5cf6', label: 'Geofence Event' };
    if (t.includes('ignition')) return { icon: 'key', color: '#3b82f6', label: 'Ignition Event' };
    if (t.includes('moving') || t.includes('started')) return { icon: 'navigation', color: '#059669', label: 'Trip Started' };
    if (t.includes('stopped') || t.includes('stop')) return { icon: 'octagon', color: '#dc2626', label: 'Vehicle Stopped' };
    if (t.includes('fuel')) return { icon: 'fuel', color: '#d97706', label: 'Fuel Event' };
    return { icon: 'bell', color: '#ef4444', label: type.replace(/([A-Z])/g, ' $1').trim() || 'Fleet Event' };
}

function updateDashboardTimelineFeed(events) {
    const feed = document.getElementById('dashboard-activity-feed');
    const countEl = document.getElementById('timeline-event-count');
    if (!feed) return;

    if (!events || !events.length) {
        feed.innerHTML = `
            <div class="timeline-item-refined timeline-empty">
                <div class="timeline-icon-v2" style="background:rgba(59,130,246,0.1); color:#3b82f6;"><i data-lucide="info"></i></div>
                <div class="timeline-info-v2">
                    <h5>System Initialized</h5>
                    <p>Awaiting live telemetry stream...</p>
                </div>
            </div>`;
        if (countEl) countEl.innerText = '0 Events';
        lucide.createIcons({ el: feed });
        return;
    }

    const recent = events.slice(0, 6);
    if (countEl) countEl.innerText = `${recent.length} Events`;

    feed.innerHTML = recent.map(e => {
        const meta = getTimelineEventMeta(e.type);
        const vehicle = e.vehicleName || e.vehicle || 'Unknown Asset';
        const timeStr = e.eventTime ? new Date(e.eventTime).toLocaleString() : (e.time || 'Just now');
        return `
            <div class="timeline-item-refined">
                <div class="timeline-icon-v2" style="background:${meta.color}18; color:${meta.color};">
                    <i data-lucide="${meta.icon}"></i>
                </div>
                <div class="timeline-info-v2">
                    <div class="timeline-title-row">
                        <h5>${meta.label}</h5>
                        <span class="timeline-time-v2">${timeStr}</span>
                    </div>
                    <p><strong>${vehicle}</strong> triggered a fleet event${e.geofenceName ? ` near <em>${e.geofenceName}</em>` : ''}.</p>
                </div>
            </div>
        `;
    }).join('');
    
    lucide.createIcons({ el: feed });
}

function updateExecGreeting() {
    const greetingEl = document.getElementById('exec-greeting');
    if (!greetingEl) return;
    const hour = new Date().getHours();
    let greet = "Good morning";
    if (hour >= 12 && hour < 17) greet = "Good afternoon";
    else if (hour >= 17) greet = "Good evening";
    greetingEl.innerText = `${greet}, ${userName || 'Alex'} 👋`;
}

function updatePerformanceCharts(data) {
    // Trips by Status Donut
    const tripsCtx = document.getElementById('tripsStatusChart');
    if (tripsCtx) {
        if (tripsStatusChart) tripsStatusChart.destroy();
        const counts = data.trips?.counts || { completed: 0, progress: 0, delayed: 0 };
        document.getElementById('perf-trips-count').innerText = counts.completed + counts.progress + counts.delayed;
        document.getElementById('perf-completed').innerText = counts.completed;
        document.getElementById('perf-progress').innerText = counts.progress;
        document.getElementById('perf-delayed').innerText = counts.delayed;

        tripsStatusChart = new Chart(tripsCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [counts.completed, counts.progress, counts.delayed],
                    backgroundColor: ['#10b981', '#3b82f6', '#f59e0b'],
                    borderWidth: 0,
                    cutout: '80%'
                }]
            },
            options: { plugins: { legend: { display: false }, tooltip: { enabled: false } }, responsive: true, maintainAspectRatio: false }
        });
    }

    // Distance Line Chart
    const distCtx = document.getElementById('distanceLineChart');
    if (distCtx) {
        if (distanceLineChart) distanceLineChart.destroy();
        const distData = [];
        document.getElementById('perf-dist').innerText = "0 mi";
        distanceLineChart = createSparkline(distCtx, distData, '#3b82f6');
    }

    // Fuel Consumption Line Chart
    const fuelCtx = document.getElementById('fuelLineChart');
    if (fuelCtx) {
        if (fuelLineChart) fuelLineChart.destroy();
        const fuelData = [];
        document.getElementById('perf-fuel').innerText = "0 L";
        fuelLineChart = createSparkline(fuelCtx, fuelData, '#10b981');
    }
}

function updateLowerAnalytics(data) {
    // Alerts List
    const alertsContainer = document.getElementById('alerts-list-container');
    if (alertsContainer) {
        const alerts = data.recent_events || [];
        document.getElementById('alert-count-badge').innerText = alerts.length;
        alertsContainer.innerHTML = alerts.map(a => `
            <div class="alert-item">
                <div class="alert-icon-circle" style="background:${a.color}; color:${a.iconColor};">
                    <i data-lucide="${a.icon}" style="width:18px;"></i>
                </div>
                <div class="alert-text" style="flex:1;">
                    <h4>${a.title}</h4>
                    <p>${a.sub}</p>
                </div>
                <div style="font-size:0.7rem; color:var(--fleet-text-sub);">${a.time}</div>
            </div>
        `).join('');
        lucide.createIcons({ el: alertsContainer });
    }

    // Eco Score Donut
    const ecoCtx = document.getElementById('ecoScoreChart');
    if (ecoCtx) {
        if (ecoScoreChart) ecoScoreChart.destroy();
        ecoScoreChart = new Chart(ecoCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#10b981', '#f1f5f9'],
                    borderWidth: 0,
                    cutout: '80%',
                    circumference: 180,
                    rotation: 270
                }]
            },
            options: { plugins: { legend: { display: false }, tooltip: { enabled: false } }, responsive: true, maintainAspectRatio: false }
        });
    }

    // Fuel Cost Over Time
    const costCtx = document.getElementById('fuelCostTimeChart');
    if (costCtx) {
        if (fuelCostTimeChart) fuelCostTimeChart.destroy();
        const costData = [];
        fuelCostTimeChart = createSparkline(costCtx, costData, '#3b82f6');
    }
}

function createSparkline(ctx, data, color) {
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map((_, i) => i),
            datasets: [{
                data: data,
                borderColor: color,
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                backgroundColor: color + '10',
                tension: 0.4
            }]
        },
        options: { 
            plugins: { legend: { display: false } }, 
            scales: { x: { display: false }, y: { display: false } },
            responsive: true, maintainAspectRatio: false 
        }
    });
}

let execMap = null;

function initExecutiveMap() {
    const mapDiv = document.getElementById('exec-dashboard-map');
    if (!mapDiv || execMap) return;

    execMap = L.map('exec-dashboard-map', {
        zoomControl: false,
        attributionControl: false
    }).setView([24.8607, 67.0011], 12);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png').addTo(execMap);
}
// DOM Elements - Query after DOM is likely ready
let loginView, appView, loginForm, loginError, logoutBtn, userNameDisplay, roleDisplay, roleText;

function initAuthElements() {
    loginView = document.getElementById('login-view');
    appView = document.getElementById('app-view');
    loginForm = document.getElementById('login-form');
    loginError = document.getElementById('login-error');
    logoutBtn = document.getElementById('logout-btn');
    userNameDisplay = document.getElementById('user-name-display');
    roleDisplay = document.getElementById('role-display');
    roleText = document.getElementById('role-text');
}

const adminSyncBtn = document.getElementById('admin-sync-btn');

const chatPanel = document.getElementById('chat-panel');
const chatTrigger = document.getElementById('chat-trigger');
const closeChatBtn = document.getElementById('close-chat-panel');
const fullscreenChatBtn = document.getElementById('fullscreen-chat');
const minChatBtn = document.getElementById('minimize-chat');
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const historyList = document.getElementById('history-list');
const historySearchInput = document.getElementById('history-search-input');
const typingIndicator = document.getElementById('typing-indicator');

// Global State
let currentSessionId = localStorage.getItem('fleet_session_id') || ('session-' + Math.random().toString(36).substr(2, 9));
localStorage.setItem('fleet_session_id', currentSessionId);
let currentLang = 'en';
let alertPreferences = {};
let alertsInterval = null;

const TRACCAR_EVENT_TYPES = [
    { id: 'deviceOnline', label: 'Device Online', category: 'General' },
    { id: 'deviceOffline', label: 'Device Offline', category: 'General' },
    { id: 'deviceMoving', label: 'Device Moving', category: 'General' },
    { id: 'deviceStopped', label: 'Device Stopped', category: 'General' },
    { id: 'ignitionOn', label: 'Ignition ON', category: 'General' },
    { id: 'ignitionOff', label: 'Ignition OFF', category: 'General' },
    { id: 'sos', label: 'SOS / Panic', category: 'Emergency' },
    { id: 'accident', label: 'Accident Detected', category: 'Emergency' },
    { id: 'fallDown', label: 'Fall Down', category: 'Emergency' },
    { id: 'deviceOverspeed', label: 'Overspeed', category: 'Safety' },
    { id: 'hardAcceleration', label: 'Hard Acceleration', category: 'Safety' },
    { id: 'hardBraking', label: 'Hard Braking', category: 'Safety' },
    { id: 'hardCornering', label: 'Hard Cornering', category: 'Safety' },
    { id: 'fatigueDriving', label: 'Fatigue Driving', category: 'Safety' },
    { id: 'geofenceEnter', label: 'Geofence Enter', category: 'Security' },
    { id: 'geofenceExit', label: 'Geofence Exit', category: 'Security' },
    { id: 'powerCut', label: 'Power Cut', category: 'Security' },
    { id: 'powerRestored', label: 'Power Restored', category: 'Security' },
    { id: 'jamming', label: 'GPS Jamming', category: 'Security' },
    { id: 'tampering', label: 'Device Tampering', category: 'Security' },
    { id: 'removing', label: 'Device Removal', category: 'Security' },
    { id: 'tow', label: 'Towing Detected', category: 'Security' },
    { id: 'vibration', label: 'Vibration Alert', category: 'Security' },
    { id: 'lowBattery', label: 'Low Battery', category: 'Status' },
    { id: 'lowPower', label: 'Low Power', category: 'Status' },
    { id: 'fault', label: 'Engine Fault', category: 'Maintenance' },
    { id: 'temperature', label: 'Temperature Alert', category: 'Sensors' },
    { id: 'fuelLeak', label: 'Fuel Leak', category: 'Sensors' },
    { id: 'door', label: 'Door Alert', category: 'Sensors' },
    { id: 'lock', label: 'Lock Engaged', category: 'Sensors' },
    { id: 'unlock', label: 'Unlock Engaged', category: 'Sensors' },
    { id: 'powerOn', label: 'Power ON', category: 'General' },
    { id: 'powerOff', label: 'Power OFF', category: 'General' },
    { id: 'gpsAntennaCut', label: 'GPS Antenna Cut', category: 'Security' },
    { id: 'idle', label: 'Idle Detected', category: 'General' },
    { id: 'highRpm', label: 'High RPM', category: 'Safety' },
    { id: 'laneChange', label: 'Lane Change', category: 'Safety' },
    { id: 'parking', label: 'Parking Alert', category: 'General' },
    { id: 'bonnet', label: 'Bonnet Opened', category: 'Sensors' },
    { id: 'footBrake', label: 'Foot Brake Alert', category: 'Safety' },
    { id: 'lowSpeed', label: 'Low Speed Alert', category: 'Safety' },
    { id: 'movement', label: 'Movement Alert', category: 'Security' },
    { id: 'general', label: 'General Alert', category: 'General' }
];

const translations = {
    en: {
        login_title: "AI - Telemetrix", login_subtitle: "Enterprise Intelligence Portal", label_email: "Corporate Email", label_password: "Security Key", label_name: "Full Name", btn_access: "Access System", new_to: "New to Telemetrix?", req_access: "Request Access", demo_access: "Demo Access:", demo_note: "Valid for all modules",
        nav_dashboard: "Dashboard", nav_map: "Live Map", nav_intel: "Vehicle Intel", nav_driver: "Driver Intel", nav_fuel: "Fuel Analytics", nav_maint: "Maintenance", nav_planner: "Planner & Rules",
        dash_title: "Dashboard Overview", dash_subtitle: "Real-time updates", stat_active: "Active Units", stat_moving: "Moving", stat_fuel: "Fleet Fuel", stat_alerts: "Alerts",
        kpi_total: "Total Units", kpi_moving: "Moving", kpi_idle: "Idle", kpi_stopped: "Stopped", kpi_offline: "Offline", kpi_alerts: "Active Alerts", kpi_overspeed: "Overspeed", kpi_ignition: "Ignition", kpi_geofence: "Geofence", kpi_tamper: "Tamper"
    }
};

function updateUILanguage(lang = null) {
    if (lang) {
        currentLang = lang;
        localStorage.setItem('fleet_lang', lang);
    }

    // Update direction for RTL languages
    if (currentLang === 'ur' || currentLang === 'ar' || currentLang === 'fa') {
        document.body.style.direction = 'rtl';
        document.body.classList.add('rtl-mode');
    } else {
        document.body.style.direction = 'ltr';
        document.body.classList.remove('rtl-mode');
    }

    const dict = translations[currentLang] || translations.en;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
            const innerSpan = el.querySelector('span');
            if (innerSpan) {
                innerSpan.innerText = dict[key];
            } else {
                let textNode = Array.from(el.childNodes).find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0);
                if (textNode) {
                    textNode.textContent = dict[key];
                } else if (el.childNodes.length === 0) {
                    el.innerText = dict[key];
                }
            }
        }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (dict[key]) el.placeholder = dict[key];
    });
}

// Attach listener to language dropdown
document.addEventListener('DOMContentLoaded', () => {
    const langSelect = document.getElementById('ui-lang-select');
    if (langSelect) {
        langSelect.value = currentLang;
        langSelect.addEventListener('change', (e) => {
            updateUILanguage(e.target.value);
        });
    }
    updateUILanguage();
});

let map = null;
let markers = {};
let mapInterval = null;
let markerClusterGroup = null;
let darkLayer, lightLayer, standardLayer, satelliteLayer, terrainLayer, osmLayer;
let latestVehicles = [];
let currentFuelPricePKR = 272.89; // Default fallback in case of sync delay

// ── Notification System (Global) ───────────────────────
let notifications = [];
let notifFilter = 'all';

function getNotifIconClass(type) {
    if (type === 'offline' || type === 'deviceOffline') return 'offline';
    if (type === 'alert' || type === 'sos' || type === 'accident' || type === 'jamming' || type === 'tampering' || type === 'removing') return 'alert';
    if (type === 'warning' || type === 'overspeed' || type === 'hardBraking' || type === 'hardAcceleration' || type === 'hardCornering' || type === 'fatigueDriving' || type === 'lowBattery') return 'warning';
    if (type === 'success' || type === 'deviceOnline' || type === 'powerRestored') return 'success';
    return 'info';
}

function getNotifIcon(type) {
    const map = {
        offline: 'wifi-off', deviceOffline: 'wifi-off',
        alert: 'alert-triangle', sos: 'sos', accident: 'alert-octagon',
        jamming: 'radar', tampering: 'shield-alert', removing: 'trash-2',
        warning: 'alert-triangle', overspeed: 'gauge', hardBraking: 'circle-dot',
        hardAcceleration: 'zap', hardCornering: 'rotate-cw', fatigueDriving: 'bed',
        lowBattery: 'battery-low', lowPower: 'battery-warning',
        success: 'check-circle', deviceOnline: 'wifi', powerRestored: 'power',
        info: 'info', geofenceEnter: 'log-in', geofenceExit: 'log-out',
        powerCut: 'power-off', fault: 'wrench', maintenance: 'tool',
        tow: 'truck', vibration: 'vibrate', deviceMoving: 'move', deviceStopped: 'square',
        ignitionOn: 'key', ignitionOff: 'key', fallDown: 'arrow-down'
    };
    return map[type] || 'bell';
}

function getNotifTimeAgo(ts) {
    if (!ts) return 'just now';
    const diff = Date.now() - new Date(ts).getTime();
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    return Math.floor(diff / 86400000) + 'd ago';
}

function addNotification(type, title, desc, category) {
    const now = Date.now();
    const exists = notifications.find(n => n.type === type && n.desc === desc && (now - new Date(n.time).getTime()) < 60000);
    if (exists) return;
    notifications.unshift({ type, title, desc, category: category || 'system', time: new Date().toISOString(), id: now + Math.random() });
    if (notifications.length > 100) notifications.pop();
    renderNotifSidebar();
    updateNotifBadge();
}

function renderNotifSidebar() {
    const notifList = document.getElementById('notif-sidebar-list');
    if (!notifList) return;
    const filtered = notifFilter === 'all' ? notifications :
        notifications.filter(n => n.category === notifFilter);
    if (filtered.length === 0) {
        notifList.innerHTML = '<div class="notif-empty">No notifications yet</div>';
        return;
    }
    notifList.innerHTML = filtered.map(n => `
        <div class="notif-item" data-id="${n.id}">
            <div class="notif-item-icon ${getNotifIconClass(n.type)}">
                <i data-lucide="${getNotifIcon(n.type)}"></i>
            </div>
            <div class="notif-item-body">
                <div class="notif-item-title">${n.title}</div>
                <div class="notif-item-desc">${n.desc || ''}</div>
            </div>
            <div class="notif-item-time">${getNotifTimeAgo(n.time)}</div>
        </div>
    `).join('');
    lucide.createIcons({ el: notifList });
}

function updateNotifBadge() {
    const notifBadge = document.getElementById('notif-badge');
    if (!notifBadge) return;
    const count = notifications.length +
        latestVehicles.filter(v => getVehicleStatus(v).class === 'offline').length;
    if (count > 0) {
        notifBadge.style.display = 'flex';
        notifBadge.textContent = count > 99 ? '99+' : count;
    } else {
        notifBadge.style.display = 'none';
    }
}

function populateNotifFromVehicles() {
    latestVehicles.forEach(v => {
        const status = getVehicleStatus(v);
        if (status.class === 'offline') {
            const exists = notifications.find(n => n.type === 'offline' && n.desc.includes(v.name));
            if (!exists) {
                addNotification('offline', 'Vehicle Offline', `${v.name} is currently offline.`, 'alerts');
            }
        }
    });
}

function populateNotifFromEvents(events) {
    if (!events || !events.length) return;
    events.forEach(ev => {
        if (alertPreferences[ev.type] === false) return;
        const label = TRACCAR_EVENT_TYPES.find(t => t.id === ev.type)?.label || ev.type.replace(/([A-Z])/g, ' $1').trim();
        const cat = TRACCAR_EVENT_TYPES.find(t => t.id === ev.type)?.category;
        const catKey = (!cat || ['General','Emergency','Safety','Security'].includes(cat)) ? 'alerts' : 'system';
        const vehicle = ev.vehicleName || ev.vehicle || 'Unknown Asset';
        addNotification(ev.type, label, vehicle, catKey);
    });
}
// ── End Notification System ────────────────────────────

// -----------------------------------------
// STATUS LOGIC HELPER
// -----------------------------------------
function getVehicleStatus(v) {
    if (v.attributes?.alarm || v.attributes?.motion === false && v.attributes?.ignition === true) {
        return { label: 'Alert active', color: '#f59e0b', class: 'alert' }; // Orange/Warning
    }

    if (!v.lastUpdate) return { label: 'Offline', color: '#ef4444', class: 'offline' };

    const lastUpdate = new Date(v.lastUpdate);
    const now = new Date();
    const diffMinutes = (now - lastUpdate) / (1000 * 60);

    // Offline if no update for more than 10 minutes
    if (diffMinutes > 10) return { label: 'Offline', color: '#ef4444', class: 'offline' };

    const ignition = v.attributes?.ignition === true || v.attributes?.ignition === 'true' || (v.attributes?.ignition === undefined && v.speed > 2);

    if (v.speed > 2) {
        return { label: 'Moving', color: '#22c55e', class: 'moving' }; // Green
    } else if (ignition) {
        return { label: 'Idle', color: '#eab308', class: 'idle' }; // Yellow
    } else {
        return { label: 'Online', color: '#3b82f6', class: 'online' }; // Blue
    }
}

let authToken = localStorage.getItem('fleet_token');
let userRole = localStorage.getItem('fleet_role');
let userName = localStorage.getItem('fleet_name');
let selectedVehicle = null;

function authHeaders() { return { 'Authorization': `Bearer ${authToken}` }; }

function formatPKR(amount, showDecimals = false) {
    if (amount == null || isNaN(amount)) return 'Rs. 0';
    const num = Number(amount);
    if (showDecimals) return 'Rs. ' + num.toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return 'Rs. ' + num.toLocaleString('en-PK', { maximumFractionDigits: 0 });
}

const MAINT_TYPES = {
    oil_change: { name: 'Oil Change', default_km: 5000, default_days: 180, color: '#3b82f6' },
    filter_change: { name: 'Filter Change', default_km: 10000, default_days: 365, color: '#10b981' },
    brake_service: { name: 'Brake Service', default_km: 20000, default_days: 730, color: '#f59e0b' },
    tire_rotation: { name: 'Tire Rotation', default_km: 10000, default_days: 365, color: '#8b5cf6' },
    transmission: { name: 'Transmission Service', default_km: 40000, default_days: 1460, color: '#ef4444' },
    coolant: { name: 'Coolant Flush', default_km: 50000, default_days: 1095, color: '#06b6d4' },
    spark_plugs: { name: 'Spark Plugs', default_km: 30000, default_days: 730, color: '#f97316' },
    inspection: { name: 'General Inspection', default_km: 10000, default_days: 365, color: '#6366f1' },
};

// Chart Instances
let velocityChart = null;
let statusDonutChart = null;
let lifecycleChart = null;
let fuelTrendChart = null;
let fuelTimelineChart = null;
let idleCostChart = null;


// -----------------------------------------
// CENTRALIZED NAMING ENGINE (Task 1 & 2)
// -----------------------------------------
function formatVehicleDisplayName(v) {
    if (!v) return 'Unknown Asset';
    const imei = String(v.uniqueId || v.uniqueid || '');
    const last6 = imei.length >= 6 ? imei.slice(-6) : imei;
    const rawName = (v.name || '').trim();

    // Check if name is generic (IMEI-based or starts with specific generic prefixes)
    const genericPattern = /^(HINO|CAR|TRUCK|VEHICLE|BUS)-(\d{6})$/i;
    const match = rawName.match(genericPattern);

    if (!rawName || rawName.toLowerCase() === 'unknown' || rawName.toLowerCase() === 'null' || rawName === imei || (match && match[2] === last6)) {
        return `vehicle-${last6}`;
    }

    // Case B: Existing Name - Append suffix only if not already present
    if (rawName.toLowerCase().endsWith(`-${last6}`)) {
        return rawName;
    }
    return `${rawName}-${last6}`;
}

function formatDriverDisplayName(v) {
    if (!v) return 'No Driver';
    const imei = String(v.uniqueId || v.uniqueid || '');
    const last6 = imei.length >= 6 ? imei.slice(-6) : imei;
    return `driver-${last6}`;
}

function timeAgo(date) {
    if (!date || isNaN(date.getTime())) return '—';
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
}

// -----------------------------------------
// MODULE INITIALIZERS
// -----------------------------------------

async function fetchLiveFuelPrices() {
    try {
        const resp = await fetch('/api/analytics/fuel-prices', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const data = await resp.json();
        const prices = data.prices || {};
        const source = data.source || 'Unknown';

        const priceEl = document.getElementById('fuel-live-price');
        const syncBadge = document.getElementById('fuel-sync-badge');
        const sourceEl = document.getElementById('fuel-price-source');

        if (prices.Petrol) {
            currentFuelPricePKR = prices.Petrol;
            if (priceEl) priceEl.innerText = `Rs. ${currentFuelPricePKR.toFixed(2)}`;
            if (syncBadge) {
                syncBadge.innerText = 'Last Synced: Just Now';
                syncBadge.className = 'stats-badge success';
            }

            // Update fuel price source display
            if (sourceEl) {
                sourceEl.innerHTML = `<i data-lucide="info"></i> ${source}`;
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }

            // Sync with fuel dashboard mini-stat if it exists
            const dashboardFuelCost = document.querySelector('#view-fuel .mini-stat:nth-child(1) .card-value');
            if (dashboardFuelCost) dashboardFuelCost.innerText = `Rs. ${currentFuelPricePKR.toFixed(2)}`;
        }
    } catch (e) { console.error("Fuel Price Sync Error:", e); }
}

// ---- FUEL SCOPE STATE ----
let currentFuelScope = 'org'; // 'org' | 'vehicle'

function initFuelAnalytics() {
    const trendCtx = document.getElementById('fuelConsumptionChart');
    const timelineCtx = document.getElementById('fuelTimelineChart');
    if (!trendCtx || fuelTrendChart) return;

    fuelTrendChart = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [
                { label: 'Consumption (L)', data: [], borderColor: '#0ea5e9', backgroundColor: 'rgba(14, 165, 233, 0.1)', fill: true, tension: 0.4 },
                { label: 'Distance (KM)', data: [], borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.1)', fill: true, tension: 0.4 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { title: { display: true, text: 'No Data Available', color: '#64748b' } }
        }
    });

    fuelTimelineChart = new Chart(timelineCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{ label: 'Fuel Level %', data: [], borderColor: '#10b981', fill: false, stepped: false }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { title: { display: true, text: 'No Data Available', color: '#64748b' } }
        }
    });

    fetchLiveFuelPrices();
    // Respect current scope on init
    if (currentFuelScope === 'vehicle' && selectedVehicle) {
        updateFuelForSelected();
    } else {
        switchFuelScope('org');
    }
}

// ---- FUEL SCOPE SWITCHER LOGIC ----

function switchFuelScope(scope) {
    currentFuelScope = scope;
    const orgBtn = document.getElementById('fuel-scope-org');
    const vehicleBtn = document.getElementById('fuel-scope-vehicle');
    const selectorWrap = document.getElementById('fuel-vehicle-selector-wrap');
    const contextBadge = document.getElementById('fuel-asset-context');

    if (orgBtn) orgBtn.classList.toggle('active', scope === 'org');
    if (vehicleBtn) vehicleBtn.classList.toggle('active', scope === 'vehicle');

    if (scope === 'org') {
        if (selectorWrap) selectorWrap.style.display = 'none';
        if (contextBadge) contextBadge.innerText = 'Global Fleet Summary';
        loadOrgFuelAnalytics();
    } else {
        if (selectorWrap) selectorWrap.style.display = 'block';
        if (contextBadge) contextBadge.innerText = 'Vehicle Level';
        const searchInput = document.getElementById('fuel-vehicle-search');
        if (searchInput) { searchInput.value = ''; searchInput.focus(); }
    }
}

let _fuelSearchDebounce = null;

function searchFuelVehicle(query) {
    const container = document.getElementById('fuel-search-results');
    if (!container) return;
    clearTimeout(_fuelSearchDebounce);
    _fuelSearchDebounce = setTimeout(() => {
        fetch(`/api/analytics/driver/search?q=${encodeURIComponent(query || '')}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
            .then(r => r.ok ? r.json() : [])
            .then(devices => {
                if (!devices || !devices.length) {
                    container.innerHTML = '<div style="padding:12px; color:#94a3b8; font-size:0.8rem;">No vehicles found</div>';
                    container.style.display = 'block';
                    return;
                }
                container.innerHTML = devices.map(d => {
                    const statusColor = d.status === 'online' ? '#10b981' : d.status === 'offline' ? '#ef4444' : '#94a3b8';
                    const onclick = d.id
                        ? `selectFuelVehicle(${d.id}, '${(d.name||'').replace(/'/g,"\\'")}', 'traccar')`
                        : `selectFuelVehicle(null, '${(d.name||'').replace(/'/g,"\\'")}', 'fleet_alerts')`;
                    return `<div class="fuel-search-item" onclick="${onclick}" style="padding:8px 12px; cursor:pointer; border-bottom:1px solid #f1f5f9; display:flex; align-items:center; gap:8px; transition:0.15s;" onmouseover="this.style.background='#f0f4ff'" onmouseout="this.style.background=''">
                        <span style="width:8px; height:8px; border-radius:50%; background:${statusColor}; flex-shrink:0;"></span>
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:600; font-size:0.82rem; color:#1e293b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${d.name || d.id}</div>
                            <div style="font-size:0.7rem; color:#94a3b8;">${d.id ? 'ID: ' + d.id : 'Fleet vehicle'}</div>
                        </div>
                    </div>`;
                }).join('');
                container.style.display = 'block';
            })
            .catch(() => { container.style.display = 'none'; });
    }, 200);
}

function selectFuelVehicle(deviceId, name, source) {
    const input = document.getElementById('fuel-vehicle-search');
    const container = document.getElementById('fuel-search-results');
    if (input) input.value = name || '';
    if (container) container.style.display = 'none';
    const badge = document.getElementById('fuel-asset-context');
    if (badge) badge.innerText = name || deviceId;
    if (deviceId) {
        window._selectedFuelDeviceId = deviceId;
        updateFuelForSelected();
    }
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('#fuel-vehicle-selector-wrap')) {
        const c = document.getElementById('fuel-search-results');
        if (c) c.style.display = 'none';
    }
});

async function loadOrgFuelAnalytics() {
    if (!authToken) return;
    try {
        const resp = await fetch('/api/analytics/fuel/organization/summary', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) throw new Error('Org fuel fetch failed');
        const data = await resp.json();
        applyFuelDataToUI(data, true);
    } catch (e) { console.warn('Org fuel analytics error:', e); }
}

function applyFuelDataToUI(data, isOrgMode) {
    const totalCostEl = document.getElementById('fuel-total-cost');
    const livePriceEl = document.getElementById('fuel-live-price');
    const levelEl = document.getElementById('fuel-live-level');
    const methodEl = document.getElementById('fuel-method-badge');
    const validEl = document.getElementById('fuel-efficiency-validation');
    const effEl = document.getElementById('efficiency-badge');
    const ecoVal = document.getElementById('eco-score-val');
    const ecoGrade = document.getElementById('eco-grade-val');
    const idleCostEl = document.getElementById('fuel-idle-cost');
    const idleTimeEl = document.getElementById('fuel-idle-time');

    if (totalCostEl) totalCostEl.innerText = `Rs. ${(data.total_cost_pkr || 0).toLocaleString()}`;
    if (data.price_pkr && data.price_pkr > 0 && livePriceEl) livePriceEl.innerText = `Rs. ${data.price_pkr.toFixed(2)}`;
    if (levelEl) levelEl.innerText = isOrgMode ? `${data.device_count || 0} Vehicles` : `${(data.fuel_level_percent ?? 0).toFixed(1)}%`;
    if (methodEl) { methodEl.innerHTML = isOrgMode ? `<i data-lucide="layers"></i> Fleet Aggregation` : `<i data-lucide="gauge"></i> ${data.method === 'sensor' ? 'Real-time Sensor' : 'AI Estimated'}`; safeCreateIcons(); }
    if (validEl && data.efficiency_validation) {
        const val = data.efficiency_validation; const score = val.score ?? 70;
        validEl.className = `stats-badge ${score >= 85 ? 'success' : (score >= 70 ? 'primary' : 'warning')}`;
        validEl.innerText = `Eco Validation: ${val.label || 'N/A'} (${score})`;
    }
    if (effEl) { effEl.className = isOrgMode ? 'stats-badge primary' : (data.tier === 'A' ? 'stats-badge success' : 'stats-badge warning'); effEl.innerText = isOrgMode ? `Fleet: ${data.device_count} Vehicles` : (data.tier === 'A' ? '⚡ ECU Verified' : 'AI Estimated'); }
    if (ecoVal) ecoVal.textContent = isOrgMode ? '--' : '70+';
    if (ecoGrade) ecoGrade.textContent = isOrgMode ? 'Fleet Avg' : (data.tier === 'A' ? 'A' : 'B');
    const idleData = data.idle_breakdown || data.trip_costing || {};
    if (idleCostEl) idleCostEl.innerText = `Rs. ${(idleData.idle_cost || 0).toLocaleString()}`;
    if (idleTimeEl) { idleTimeEl.innerHTML = isOrgMode ? `<i data-lucide="clock"></i> Fleet idle estimate` : `<i data-lucide="clock"></i> ${idleData.idle_time_min || 0} min idle`; safeCreateIcons(); }

    if (fuelTrendChart) {
        const history = data.history || [];
        fuelTrendChart.data.labels = history.map(h => h.time);
        fuelTrendChart.data.datasets[0].data = history.map(h => h.consumption);
        fuelTrendChart.data.datasets[1].data = history.map(h => h.distance);
        fuelTrendChart.options.plugins.title.text = isOrgMode ? 'Fleet Fuel Consumption (7d)' : (history.length > 0 ? 'Vehicle Consumption vs Distance' : 'No Historical Data');
        fuelTrendChart.update();
    }
    if (fuelTimelineChart) {
        fuelTimelineChart.data.labels = [];
        fuelTimelineChart.data.datasets[0].data = [];
        fuelTimelineChart.options.plugins.title.text = isOrgMode ? 'Organisation Drain Timeline (N/A)' : 'No Data Available';
        fuelTimelineChart.update();
    }

    const stationBody = document.getElementById('fuel-station-body');
    const stationCount = document.getElementById('station-log-count');
    const logs = data.station_logs || [];
    if (stationCount) stationCount.innerText = `${logs.length} Records`;
    if (stationBody) {
        stationBody.innerHTML = logs.length === 0
            ? '<tr><td colspan="5" style="text-align:center;color:var(--text-dim);padding:24px;">No fuel station visits recorded</td></tr>'
            : logs.map(log => `<tr><td>${log.time}</td><td>${log.station || 'Unknown'}${isOrgMode ? ` <span class="stats-badge" style="font-size:0.65rem;">${log.vehicle}</span>` : ''}</td><td>${log.duration || '--'}</td><td>${(log.liters || 0).toFixed(1)} L</td><td>Rs. ${(log.cost || 0).toLocaleString()}</td></tr>`).join('');
    }
    const alertBanner = document.getElementById('fuel-profile-alert');
    if (alertBanner) alertBanner.classList.toggle('hidden-view', isOrgMode || data.status !== 'AWAITING_USER_INPUT');
}

async function updateFuelForSelected() {
    const deviceId = window._selectedFuelDeviceId || (selectedVehicle && selectedVehicle.id);
    if (!deviceId || !fuelTrendChart) return;

    try {
        const resp = await fetch(`/api/analytics/fuel/${deviceId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) throw new Error("Fuel Analytics Fetch Failed");
        const data = await resp.json();

        // Handle Status Flag (AWAITING_USER_INPUT)
        const alertBanner = document.getElementById('fuel-profile-alert');
        if (alertBanner) {
            if (data.status === 'AWAITING_USER_INPUT') {
                alertBanner.classList.remove('hidden-view');
            } else {
                alertBanner.classList.add('hidden-view');
            }
        }

        // Update Chart: Consumption vs Distance (Strictly NO MOCK data)
        const history = data.history || [];
        if (history.length > 0) {
            fuelTrendChart.data.labels = history.map(h => h.time);
            fuelTrendChart.data.datasets[0].data = history.map(h => h.consumption);
            fuelTrendChart.data.datasets[1].data = history.map(h => h.distance);
            fuelTrendChart.options.plugins.title.text = `Last 7 Days Consumption vs. Distance`;
        } else {
            fuelTrendChart.data.labels = [];
            fuelTrendChart.data.datasets[0].data = [];
            fuelTrendChart.data.datasets[1].data = [];
            fuelTrendChart.options.plugins.title.text = `No Historical Data Available`;
        }
        fuelTrendChart.update();

        // Update Fuel Timeline (Linear Drain Graph)
        if (fuelTimelineChart) {
            // We use the last 24h positions if available, or just the current level for now
            // In a production app, you'd fetch /api/v1/telemetry/history/{id}
            fuelTimelineChart.data.labels = history.map(h => h.time);
            // Simulate drain based on daily consumption for the timeline visualization
            let currentLvl = data.current_level;
            const drainPoints = history.map(h => {
                currentLvl -= (h.consumption / 10); // Simplified visual drain
                return Math.max(0, currentLvl);
            });
            fuelTimelineChart.data.datasets[0].data = drainPoints;
            fuelTimelineChart.update();
        }

        // Update Summary Cards
        const totalCost = document.getElementById('fuel-total-cost');
        const livePrice = document.getElementById('fuel-live-price');
        const loyalty = document.getElementById('fuel-loyalty-brand');
        const visits = document.getElementById('fuel-visits-count');
        const effBadge = document.getElementById('efficiency-badge');
        const ecoScore = document.getElementById('eco-score-val');
        const fuelLiveLevel = document.getElementById('fuel-live-level');
        const fuelMethodBadge = document.getElementById('fuel-method-badge');
        const fuelValidationBadge = document.getElementById('fuel-efficiency-validation');


        if (totalCost) totalCost.innerText = `Rs. ${(data.total_cost_pkr || 0).toLocaleString()}`;
        // Only update live price if backend returned a valid PKR value — NEVER overwrite with 0 or non-PKR
        if (data.price_pkr && data.price_pkr > 0) {
            currentFuelPricePKR = data.price_pkr; // Keep global in sync
            if (livePrice) livePrice.innerText = `Rs. ${currentFuelPricePKR.toFixed(2)}`;
        } else if (livePrice && currentFuelPricePKR > 0) {
            // Fallback: show cached global price, never show 0
            livePrice.innerText = `Rs. ${currentFuelPricePKR.toFixed(2)}`;
        }
        if (fuelLiveLevel) fuelLiveLevel.innerText = `${(data.fuel_level_percent ?? data.current_level ?? 0).toFixed(1)}%`;
        if (fuelMethodBadge) {
            const methodText = data.method === 'sensor'
                ? 'Real-time Sensor / OBD'
                : (data.tier === 'B' ? 'AI Estimated Fallback' : 'Regularized Fallback');
            fuelMethodBadge.innerHTML = `<i data-lucide="gauge"></i> ${methodText}`;
        }
        if (fuelValidationBadge) {
            const val = data.efficiency_validation || {};
            const score = val.score ?? 0;
            const label = val.label || 'N/A';
            fuelValidationBadge.className = `stats-badge ${score >= 85 ? 'success' : (score >= 70 ? 'primary' : 'warning')}`;
            fuelValidationBadge.innerText = `Eco Validation: ${label} (${score})`;
        }

        if (effBadge) {
            if (data.tier === 'A') {
                effBadge.className = 'stats-badge success';
                effBadge.innerText = 'ECU Verified';
            } else if (data.tier === 'B') {
                effBadge.className = 'stats-badge primary';
                effBadge.innerText = 'AI-Estimated';
            } else {
                effBadge.className = 'stats-badge warning';
                effBadge.innerText = 'Regularized Fallback';
            }
        }

        // Update Station Logs Table
        const tableBody = document.getElementById('fuel-station-body');
        const logCount = document.getElementById('station-log-count');
        const logs = data.station_logs || [];

        if (tableBody) {
            if (logs.length > 0) {
                tableBody.innerHTML = logs.map(l => `
                    <tr>
                        <td>${l.time}</td>
                        <td style="font-weight:700;">${l.brand} <small style="color:var(--text-dim); display:block; font-weight:400;">${l.branch}</small></td>
                        <td>${l.duration}</td>
                        <td style="color:var(--brand-success); font-weight:700;">+${l.liters} L</td>
                        <td style="font-family:var(--map-mono);">Rs. ${l.cost.toLocaleString()}</td>
                    </tr>
                `).join('');
                if (loyalty) loyalty.innerText = logs[0].brand;
                if (visits) visits.innerHTML = `<i data-lucide="map-pin"></i> ${logs.length} Visits This Month`;
            } else {
                tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:40px; color:var(--text-dim);">No station visits detected for this period.</td></tr>';
                if (loyalty) loyalty.innerText = 'N/A';
            }
            if (logCount) logCount.innerText = `${logs.length} Records`;
        }

        // Trip Costing Breakdown (exact expense per trip)
        const tripBody = document.getElementById('trip-cost-body');
        const tripCount = document.getElementById('trip-cost-count');
        const trips = data.trip_costing || [];
        if (tripBody) {
            if (trips.length > 0) {
                tripBody.innerHTML = trips.map(t => `
                    <tr>
                        <td><strong>${t.start_time}</strong><br><small style="color:var(--text-dim)">to ${t.end_time}</small></td>
                        <td>${t.distance_km} km</td>
                        <td>${t.fuel_liters} L</td>
                        <td style="font-weight:700;">Rs. ${Number(t.cost_pkr || 0).toLocaleString()}</td>
                    </tr>
                `).join('');
            } else {
                tripBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:28px; color:var(--text-dim);">No trip costing available for selected window.</td></tr>';
            }
        }
        if (tripCount) tripCount.innerText = `${trips.length} Trips`;

        // Smart Fuel Theft Detection Alerts
        const theftList = document.getElementById('fuel-theft-list');
        const theftCount = document.getElementById('fuel-theft-count');
        const theftAlerts = data.theft_alerts || [];
        if (theftList) {
            if (theftAlerts.length > 0) {
                theftList.innerHTML = theftAlerts.map(a => `
                    <div style="border:1px solid rgba(239,68,68,0.25); background:rgba(239,68,68,0.08); border-radius:10px; padding:10px 12px;">
                        <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
                            <strong style="color:var(--brand-danger);">${a.severity || 'CRITICAL'}</strong>
                            <small style="color:var(--text-muted);">${a.time || ''}</small>
                        </div>
                        <div style="margin-top:6px; font-size:0.85rem;">${a.message || 'Suspicious fuel drop detected'}</div>
                        <div style="margin-top:4px; font-size:0.78rem; color:var(--text-dim);">Location: ${a.location || 'Unknown'}</div>
                    </div>
                `).join('');
            } else {
                theftList.innerHTML = '<div class="stats-badge success" style="padding:10px 12px; width:fit-content;">No suspicious drops detected.</div>';
            }
        }
        if (theftCount) theftCount.innerText = `${theftAlerts.length} Alerts`;

        // Update Idle Waste Cards (vehicle mode)
        const idleCost = document.getElementById('fuel-idle-cost');
        const idleTime = document.getElementById('fuel-idle-time');
        const idleBreakdown = data.idle_breakdown || {};
        if (idleCost) idleCost.innerText = `Rs. ${(idleBreakdown.cost_pkr || 0).toLocaleString()}`;
        if (idleTime) idleTime.innerHTML = `<i data-lucide="clock"></i> ${idleBreakdown.idle_minutes || 0} min idle | ${idleBreakdown.liters_wasted || 0}L wasted`;

        // Update Eco-Score (Based on actual speeding events)
        if (ecoScore) {
            const summaryResp = await fetch('/api/analytics/summary', {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (summaryResp.ok) {
                const summaryData = await summaryResp.json();
                const overspeed = summaryData.kpis?.overspeed || 0;
                // Simple calculation: start at 100, deduct 5 points per overspeed event in last 24h
                const score = Math.max(0, 100 - (overspeed * 5));
                ecoScore.textContent = score;
                const circle = document.querySelector('.eco-circle');
                if (circle) circle.setAttribute('stroke-dasharray', `${score}, 100`);

                const scoreGrade = document.querySelector('.score-label strong');
                if (scoreGrade) {
                    let grade = 'A+';
                    if (score < 60) grade = 'D';
                    else if (score < 75) grade = 'C';
                    else if (score < 90) grade = 'B';
                    scoreGrade.innerText = grade;
                }
            }
        }

        lucide.createIcons({ el: document.getElementById('view-fuel') });

    } catch (e) {
        console.error("Fuel Update Error:", e);
    }
}

function updateMaintForSelected() {
    if (!selectedVehicle) return;
    const attrs = selectedVehicle.attributes || {};
    let activeDtcs = [];

    if (attrs.dtcs || attrs.obdFaults) {
        let codesStr = attrs.dtcs || attrs.obdFaults;
        activeDtcs = String(codesStr).split(',').filter(Boolean).map(c => ({ code: c.trim(), desc: 'ECU Fault Detected', severity: 'Critical' }));
    }

    const dtcList = document.getElementById('active-dtc-list');
    if (dtcList) {
        dtcList.innerHTML = activeDtcs.length > 0 ? activeDtcs.map(c => `
            <div class="dtc-item">
                <div><span class="dtc-code">${c.code}</span><div style="font-size:0.8rem; color:var(--text-secondary);">${c.desc}</div></div>
                <span class="stats-badge danger">Critical</span>
            </div>`).join('') : '<div style="color:var(--brand-success); padding:20px; text-align:center;">Vehicle ECU Clear - No Faults</div>';
    }
}

let maintTabState = 'upcoming';
let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth() + 1;
let maintDashboardData = null;
let _maintHealthChart = null, _maintByTypeChart = null, _maintCategoryChart = null;

function initMaintenanceCenter() {
    loadMaintenanceDashboard();
}

async function loadMaintenanceDashboard() {
    if (!authToken) return;
    try {
        const [dashResp, summaryResp, typesResp, tmplResp] = await Promise.all([
            fetch('/api/maintenance/dashboard', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/types/summary', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/types?page_size=200&sort_by=updated_at&sort_order=desc', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/templates?page_size=500', { headers: { 'Authorization': `Bearer ${authToken}` } })
        ]);
        if (!dashResp.ok) throw new Error(`Dashboard fetch failed: ${dashResp.status}`);
        const data = await dashResp.json();
        const summary = summaryResp.ok ? await summaryResp.json() : { total: 0, active: 0, inactive: 0, deleted: 0 };
        const typesData = typesResp.ok ? await typesResp.json() : { items: [] };
        const tmplData = tmplResp.ok ? await tmplResp.json() : { total: 0, items: [] };
        const tmplItems = tmplData.items || [];
        data._typeSummary = summary;
        data._types = typesData.items || [];
        data._templateSummary = {
            total: tmplData.total || 0,
            active: tmplItems.filter(t => t.is_active && !t.is_archived).length,
            inactive: tmplItems.filter(t => !t.is_active && !t.is_archived).length,
            archived: tmplItems.filter(t => t.is_archived).length
        };
        data._templates = tmplItems;
        maintDashboardData = data;
        renderMaintenanceKPI(data.kpis, summary, data._templateSummary);
        renderMaintenanceHealth(data.fleet_health_summary, data.kpis);
        renderMaintenanceByTypeChart(data.maintenance_by_type);
        renderTypeCategoryChart(data._types);
        renderRecentTypeActivity(data._types);
        renderTemplateCategoryChart(data._templates);
        renderRecentTemplateActivity(data._templates);
        switchMaintTab(maintTabState);
        lucide.createIcons({ el: document.getElementById('view-maintenance') });
    } catch (e) {
        console.error('Maintenance dashboard error:', e);
        const tc = document.getElementById('maint-tab-content');
        if (tc) tc.innerHTML = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Failed to load maintenance data.</div>';
    }
}

function renderMaintenanceKPI(kpis, typeSummary, templateSummary) {
    const container = document.getElementById('maint-kpi-cards');
    if (!container) return;
    const items = [
        { label: 'Total Vehicles', value: kpis.total_vehicles || 0, icon: 'car', color: '#3b82f6' },
        { label: 'Overdue', value: kpis.overdue_maintenance || 0, icon: 'alert-circle', color: '#ef4444' },
        { label: 'Due Today', value: kpis.due_today || 0, icon: 'clock', color: '#f59e0b' },
        { label: 'Due This Week', value: kpis.due_this_week || 0, icon: 'calendar', color: '#8b5cf6' },
        { label: 'Active Jobs', value: kpis.active_workshop_jobs || 0, icon: 'wrench', color: '#06b6d4' },
        { label: 'Fleet Health', value: (kpis.fleet_health_score || 0) + '%', icon: 'heart', color: '#10b981' },
        { label: 'Total Types', value: typeSummary ? typeSummary.total : 0, icon: 'list', color: '#6366f1' },
        { label: 'Active Types', value: typeSummary ? typeSummary.active : 0, icon: 'check-circle', color: '#10b981' },
        { label: 'Inactive Types', value: typeSummary ? typeSummary.inactive : 0, icon: 'pause-circle', color: '#f59e0b' },
        { label: 'Deleted Types', value: typeSummary ? typeSummary.deleted : 0, icon: 'trash-2', color: '#ef4444' },
        { label: 'Total Templates', value: templateSummary ? templateSummary.total : 0, icon: 'layers', color: '#8b5cf6' },
        { label: 'Active Templates', value: templateSummary ? templateSummary.active : 0, icon: 'check-circle', color: '#10b981' },
        { label: 'Inactive Templates', value: templateSummary ? templateSummary.inactive : 0, icon: 'pause-circle', color: '#f59e0b' },
        { label: 'Archived Templates', value: templateSummary ? templateSummary.archived : 0, icon: 'archive', color: '#94a3b8' },
    ];
    container.innerHTML = items.map(i => `
        <div class="premium-card mini-stat">
            <span class="card-label">${i.label}</span>
            <span class="card-value" style="color:${i.color};">${i.value}</span>
        </div>
    `).join('');
}

function renderMaintenanceHealth(health, kpis) {
    const legend = document.getElementById('maintHealthLegend');
    const score = document.getElementById('maintHealthScore');
    if (!legend || !score) return;
    score.innerText = (kpis.fleet_health_score || 0) + '%';
    const colors = { healthy: '#10b981', warning: '#f59e0b', critical: '#ef4444', unknown: '#94a3b8' };
    legend.innerHTML = Object.entries(health).map(([k, v]) => `
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="display:flex; align-items:center; gap:8px; font-size:0.82rem;">
                <span style="width:10px; height:10px; border-radius:50%; background:${colors[k]};"></span> ${k.charAt(0).toUpperCase() + k.slice(1)}
            </span>
            <span style="font-weight:700; font-size:0.9rem;">${v}</span>
        </div>
    `).join('');
    const ctx = document.getElementById('maintHealthDonut');
    if (ctx && typeof Chart !== 'undefined') {
        if (_maintHealthChart) _maintHealthChart.destroy();
        _maintHealthChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(health).map(k => k.charAt(0).toUpperCase() + k.slice(1)),
                datasets: [{ data: Object.values(health), backgroundColor: Object.keys(health).map(k => colors[k]), borderWidth: 0 }]
            },
            options: { responsive: true, maintainAspectRatio: true, cutout: '70%', plugins: { legend: { display: false } } }
        });
    }
}

function renderMaintenanceByTypeChart(byType) {
    const ctx = document.getElementById('maintByTypeChart');
    if (!ctx || typeof Chart === 'undefined') return;
    if (_maintByTypeChart) _maintByTypeChart.destroy();
    const labels = Object.keys(byType).map(k => (MAINT_TYPES && MAINT_TYPES[k]) ? MAINT_TYPES[k].name : k);
    const colors = Object.keys(byType).map(k => (MAINT_TYPES && MAINT_TYPES[k]) ? MAINT_TYPES[k].color : '#64748b');
    _maintByTypeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Healthy', data: Object.values(byType).map(v => v.ok || 0), backgroundColor: '#10b981' },
                { label: 'Due Soon', data: Object.values(byType).map(v => v.due_soon || 0), backgroundColor: '#f59e0b' },
                { label: 'Overdue', data: Object.values(byType).map(v => v.overdue || 0), backgroundColor: '#ef4444' }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: true,
            scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } },
            plugins: { legend: { position: 'bottom' } }
        }
    });
}

function renderTypeCategoryChart(types) {
    const ctx = document.getElementById('maintTypeCategoryChart');
    if (!ctx || typeof Chart === 'undefined') return;
    const counts = {};
    types.forEach(t => { const cat = t.category || 'uncategorized'; counts[cat] = (counts[cat] || 0) + 1; });
    const labels = Object.keys(counts).map(k => k.charAt(0).toUpperCase() + k.slice(1));
    const data = Object.values(counts);
    if (!labels.length) {
        const parent = ctx.parentElement;
        if (parent) parent.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-dim); font-size:0.85rem;">No Maintenance Types Found</div>';
        return;
    }
    const palette = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#06b6d4','#84cc16','#f97316','#6366f1'];
    if (_maintCategoryChart) _maintCategoryChart.destroy();
    _maintCategoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: palette.slice(0, labels.length), borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: true, cutout: '60%', plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } } } }
    });
}

function renderTemplateCategoryChart(templates) {
    const canvas = document.getElementById('maintTemplateCategoryChart');
    if (!canvas) return;
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
    const cats = {};
    (templates || []).forEach(t => {
        const cat = t.vehicle_category || 'Uncategorized';
        cats[cat] = (cats[cat] || 0) + 1;
    });
    const labels = Object.keys(cats);
    const values = Object.values(cats);
    const colors = ['#8b5cf6','#3b82f6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#94a3b8'];
    new Chart(canvas, {
        type: 'doughnut',
        data: { labels, datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length), borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 10 } } } } }
    });
}

function renderRecentTemplateActivity(templates) {
    const container = document.getElementById('maint-template-activity');
    if (!container) return;
    if (!templates || !templates.length) {
        container.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-dim); font-size:0.85rem;">No Templates Found</div>';
        return;
    }
    const recent = templates.slice(0, 15);
    const events = recent.map(t => {
        let action = 'Updated', icon = 'edit', color = '#8b5cf6';
        if (t.is_archived) { action = 'Archived'; icon = 'archive'; color = '#94a3b8'; }
        else if (t.is_deleted) { action = 'Deleted'; icon = 'trash-2'; color = '#ef4444'; }
        else if (!t.is_active) { action = 'Deactivated'; icon = 'pause-circle'; color = '#f59e0b'; }
        else if (t.is_active && t.updated_at === t.created_at) { action = 'Created'; icon = 'plus-circle'; color = '#10b981'; }
        const time = t.updated_at ? t.updated_at.split('T')[0] : '';
        return { action, icon, color, name: t.name, time, cat: t.vehicle_category || '' };
    });
    container.innerHTML = events.map(e => `
        <div style="display:flex; gap:12px; padding:8px 0; border-bottom:1px solid var(--border-light); align-items:center;">
            <div style="width:32px; height:32px; border-radius:50%; background:${e.color}15; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                <i data-lucide="${e.icon}" style="width:14px; color:${e.color};"></i>
            </div>
            <div style="flex:1; min-width:0;">
                <div style="font-weight:600; font-size:0.82rem; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${e.name}</div>
                <div style="font-size:0.7rem; color:var(--text-dim);">${e.action}${e.cat ? ' · ' + e.cat : ''}</div>
            </div>
            <span style="font-size:0.7rem; color:var(--text-dim); white-space:nowrap;">${e.time}</span>
        </div>
    `).join('');
    lucide.createIcons({ el: container });
}

function renderRecentTypeActivity(types) {
    const container = document.getElementById('maint-type-activity');
    if (!container) return;
    if (!types.length) {
        container.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-dim); font-size:0.85rem;">No Maintenance Types Found</div>';
        return;
    }
    const recent = types.slice(0, 15);
    const events = recent.map(t => {
        let action = 'Updated', icon = 'edit', color = '#3b82f6';
        if (t.is_deleted) { action = 'Deleted'; icon = 'trash-2'; color = '#ef4444'; }
        else if (!t.is_active) { action = 'Deactivated'; icon = 'pause-circle'; color = '#f59e0b'; }
        else if (t.is_active && t.updated_at === t.created_at) { action = 'Created'; icon = 'plus-circle'; color = '#10b981'; }
        const time = t.updated_at ? t.updated_at.split('T')[0] : '';
        const timeAgo = time ? time : '';
        return { action, icon, color, name: t.name, time: timeAgo, cat: t.category || '' };
    });
    container.innerHTML = events.map(e => `
        <div style="display:flex; gap:12px; padding:8px 0; border-bottom:1px solid var(--border-light); align-items:center;">
            <div style="width:32px; height:32px; border-radius:50%; background:${e.color}15; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                <i data-lucide="${e.icon}" style="width:14px; color:${e.color};"></i>
            </div>
            <div style="flex:1; min-width:0;">
                <div style="font-weight:600; font-size:0.82rem; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${e.name}</div>
                <div style="font-size:0.7rem; color:var(--text-dim);">${e.action}${e.cat ? ' · ' + e.cat : ''}</div>
            </div>
            <span style="font-size:0.7rem; color:var(--text-dim); white-space:nowrap;">${e.time}</span>
        </div>
    `).join('');
    lucide.createIcons({ el: container });
}

function switchMaintTab(tab) {
    maintTabState = tab;
    document.querySelectorAll('.maint-tab-btn').forEach(b => {
        b.classList.remove('primary');
        b.style.background = 'transparent';
        b.style.color = 'var(--text-secondary)';
    });
    const activeBtn = document.querySelector(`.maint-tab-btn[data-tab="${tab}"]`);
    if (activeBtn) {
        activeBtn.classList.add('primary');
        activeBtn.style.background = 'var(--brand-primary)';
        activeBtn.style.color = '#fff';
    }
    renderMaintTab(tab, maintDashboardData);
}

async function renderMaintTab(tab, data) {
    const tc = document.getElementById('maint-tab-content');
    if (!tc) return;
    if (!data) {
        tc.innerHTML = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Loading...</div>';
        return;
    }
    let html = '';
    if (tab === 'upcoming') {
        const resp = await fetch('/api/maintenance/planner/scheduler/upcoming?page=1&page_size=20', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) {
            const result = await resp.json();
            html = renderMaintTable(result.items || [], ['Vehicle', 'Type', 'Rule', 'Due Date', 'KM Left', 'Days Left', 'Priority'], r => [
                r.vehicle_name, r.type_name || '-', r.rule_name || '-',
                r.next_due_date ? r.next_due_date.split('T')[0] : 'N/A',
                r.km_remaining != null ? Math.round(r.km_remaining).toLocaleString() + ' km' : 'N/A',
                r.days_remaining != null ? r.days_remaining + ' days' : 'N/A',
                `<span class="stats-badge ${r.priority === 'critical' ? 'danger' : r.priority === 'high' ? 'danger' : r.priority === 'medium' ? 'warning' : 'primary'}">${r.priority || 'low'}</span>`
            ]);
            if (result.total_pages > 1) html += renderPagination(result, 'upcoming');
        } else {
            html = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No upcoming maintenance</div>';
        }
    } else if (tab === 'overdue') {
        const resp = await fetch('/api/maintenance/planner/scheduler/overdue?page=1&page_size=20', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) {
            const result = await resp.json();
            html = renderMaintTable(result.items || [], ['Vehicle', 'Type', 'Rule', 'Days Overdue', 'KM Overdue', 'Risk Level'], r => [
                r.vehicle_name, r.type_name || '-', r.rule_name || '-',
                r.days_overdue ? r.days_overdue + ' days' : 'N/A',
                r.km_overdue ? Math.round(r.km_overdue).toLocaleString() + ' km' : 'N/A',
                `<span class="stats-badge ${r.risk_level === 'Critical' ? 'danger' : r.risk_level === 'High' ? 'warning' : r.risk_level === 'Medium' ? 'warning' : 'primary'}">${r.risk_level || 'Low'}</span>`
            ]);
            if (result.total_pages > 1) html += renderPagination(result, 'overdue');
        } else {
            html = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No overdue items</div>';
        }
    } else if (tab === 'calendar') {
        const resp = await fetch(`/api/maintenance/planner/scheduler/calendar?year=${calYear}&month=${calMonth}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) {
            const result = await resp.json();
            const events = result.events || [];
            const daysInMonth = new Date(calYear, calMonth, 0).getDate();
            const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
            html = `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <button class="glass-btn" onclick="calNav(-1)" style="padding:6px 12px; font-size:0.8rem; border:none; cursor:pointer; border-radius:6px;">&larr; Prev</button>
                <span style="font-weight:700; font-size:1rem;">${monthNames[calMonth - 1]} ${calYear}</span>
                <button class="glass-btn" onclick="calNav(1)" style="padding:6px 12px; font-size:0.8rem; border:none; cursor:pointer; border-radius:6px;">Next &rarr;</button>
            </div>`;
            html += '<div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:4px; text-align:center;">';
            ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => { html += `<div style="font-weight:700; padding:8px; font-size:0.75rem; color:var(--text-dim);">${d}</div>`; });
            for (let i = 1; i <= daysInMonth; i++) {
                const dayEvents = events.filter(e => e.day === i);
                const hasOverdue = dayEvents.some(e => e.is_overdue);
                const hasUpcoming = dayEvents.some(e => !e.is_overdue);
                const bg = hasOverdue ? '#fef2f2' : hasUpcoming ? '#f0f4ff' : 'transparent';
                const evNames = dayEvents.map(e => `${e.vehicle_name}: ${e.type_name}`).join('\n');
                html += `<div style="padding:8px; border-radius:8px; background:${bg}; min-height:60px; font-size:0.78rem; cursor:${dayEvents.length ? 'pointer' : 'default'};" title="${evNames.replace(/"/g, '&quot;')}">${i}${dayEvents.length ? `<div style="font-size:0.65rem; margin-top:4px;">${dayEvents.length} item${dayEvents.length > 1 ? 's' : ''}</div>` : ''}</div>`;
            }
            html += '</div>';
        } else {
            html = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No calendar data</div>';
        }
    } else if (tab === 'activity') {
        const resp = await fetch('/api/maintenance/planner/scheduler/activity?limit=50', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) {
            const result = await resp.json();
            const activities = result.activities || [];
            html = activities.length ? activities.map(a => {
                const icon = a.type === 'rule_change' ? 'settings' : 'wrench';
                const color = a.type === 'rule_change' ? '#8b5cf6' : '#3b82f6';
                const bg = a.type === 'rule_change' ? '#f3e8ff' : '#dbeafe';
                return `
                <div style="display:flex; gap:16px; padding:12px 0; border-bottom:1px solid var(--border-light);">
                    <div style="width:40px; height:40px; border-radius:50%; background:${bg}; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                        <i data-lucide="${icon}" style="width:18px; color:${color};"></i>
                    </div>
                    <div style="flex:1;">
                        <div style="font-weight:600; font-size:0.85rem;">${a.description || 'Activity'}</div>
                        <div style="font-size:0.75rem; color:var(--text-secondary);">${a.reason || ''} — ${a.created_at ? a.created_at.split('T')[0] : ''}</div>
                    </div>
                    <span class="stats-badge ${a.type === 'rule_change' ? 'primary' : 'success'}">${(a.type || '').replace('_', ' ')}</span>
                </div>`;
            }).join('') : '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No recent activity</div>';
        } else {
            html = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Failed to load activity</div>';
        }
    } else if (tab === 'workshops') {
        const resp = await fetch('/api/maintenance/workshops', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) {
            const result = await resp.json();
            const workshops = result.workshops || [];
            html = workshops.length ? workshops.map(w => `
                <div class="premium-card" style="padding:20px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div><strong>${w.name}</strong> <span style="font-size:0.75rem; color:var(--text-dim);">${w.code || ''}</span></div>
                        <span class="stats-badge primary">${w.rating ? w.rating + '/5' : 'N/A'}</span>
                    </div>
                    <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:6px;">${w.address || ''} — ${w.city || ''}</div>
                    <div style="font-size:0.75rem; color:var(--text-dim); margin-top:4px;">${w.phone || ''} ${w.email || ''}</div>
                </div>
            `).join('') : '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No workshops configured</div>';
        } else {
            html = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Failed to load workshops</div>';
        }
    }
    tc.innerHTML = html;
    lucide.createIcons({ el: tc });
}

function renderMaintTable(items, columns, rowRenderer) {
    if (!items.length) return '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No data</div>';
    return `<table class="modern-table" style="width:100%;"><thead><tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${items.map(rowRenderer).map(r => `<tr>${r.map(c => `<td>${c || ''}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

function renderPagination(result, tab) {
    return `<div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; padding:12px;"><span style="font-size:0.8rem; color:var(--text-dim);">${result.total} total items</span><div style="display:flex; gap:6px;">${Array.from({length: Math.min(result.total_pages, 5)}, (_, i) => `<button class="glass-btn" onclick="loadMaintPage('${tab}', ${i + 1})" style="padding:6px 12px; font-size:0.75rem;">${i + 1}</button>`).join('')}</div></div>`;
}

async function loadMaintPage(tab, page) {
    const url = `/api/maintenance/planner/scheduler/${tab}?page=${page}&page_size=20`;
    const resp = await fetch(url, { headers: { 'Authorization': `Bearer ${authToken}` } });
    if (!resp.ok) return;
    const result = await resp.json();
    const tc = document.getElementById('maint-tab-content');
    if (!tc) return;
    let cols, renderer;
    if (tab === 'upcoming') { cols = ['Vehicle', 'Type', 'Rule', 'Due Date', 'KM Left', 'Days Left', 'Priority']; renderer = r => [r.vehicle_name, r.type_name || '-', r.rule_name || '-', r.next_due_date ? r.next_due_date.split('T')[0] : 'N/A', r.km_remaining != null ? Math.round(r.km_remaining).toLocaleString() + ' km' : 'N/A', r.days_remaining != null ? r.days_remaining + ' days' : 'N/A', `<span class="stats-badge ${r.priority === 'critical' ? 'danger' : r.priority === 'high' ? 'danger' : r.priority === 'medium' ? 'warning' : 'primary'}">${r.priority || 'low'}</span>`]; }
    else { cols = ['Vehicle', 'Type', 'Rule', 'Days Overdue', 'KM Overdue', 'Risk Level']; renderer = r => [r.vehicle_name, r.type_name || '-', r.rule_name || '-', r.days_overdue ? r.days_overdue + ' days' : 'N/A', r.km_overdue ? Math.round(r.km_overdue).toLocaleString() + ' km' : 'N/A', `<span class="stats-badge ${r.risk_level === 'Critical' ? 'danger' : r.risk_level === 'High' ? 'warning' : r.risk_level === 'Medium' ? 'warning' : 'primary'}">${r.risk_level || 'Low'}</span>`]; }
    tc.innerHTML = renderMaintTable(result.items || [], cols, renderer) + (result.total_pages > 1 ? renderPagination(result, tab) : '');
}

function calNav(dir) {
    calMonth += dir;
    if (calMonth > 12) { calMonth = 1; calYear++; }
    if (calMonth < 1) { calMonth = 12; calYear--; }
    renderMaintTab('calendar', maintDashboardData);
}

async function recalculateFleet() {
    if (!authToken) return;
    const btn = document.querySelector('[onclick="recalculateFleet()"]');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i data-lucide="loader" style="width:14px; animation:spin 1s linear infinite;"></i> Recalculating...'; lucide.createIcons({ el: btn }); }
    try {
        const resp = await fetch('/api/maintenance/planner/scheduler/recalculate', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) {
            const result = await resp.json();
            maintDashboardData = null;
            await loadMaintenanceDashboard();
            if (btn) { btn.innerHTML = `<i data-lucide="check-circle" style="width:14px;"></i> Done (${result.health_score || 0}%)`; lucide.createIcons({ el: btn }); }
            setTimeout(() => { if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="refresh-cw" style="width:14px;"></i> Recalculate Fleet'; lucide.createIcons({ el: btn }); } }, 2000);
        } else {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="refresh-cw" style="width:14px;"></i> Recalculate Fleet'; lucide.createIcons({ el: btn }); }
        }
    } catch (e) {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="refresh-cw" style="width:14px;"></i> Recalculate Fleet'; lucide.createIcons({ el: btn }); }
    }
}

function openMaintenanceLogModal() {
    const modal = document.getElementById('maint-log-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.remove('hidden-view');
    fetchMaintLogDropdowns();
}

function closeMaintenanceLogModal() {
    const modal = document.getElementById('maint-log-modal');
    if (modal) { modal.style.display = 'none'; modal.classList.add('hidden-view'); }
    document.getElementById('maint-log-form')?.reset();
}

async function fetchMaintLogDropdowns() {
    try {
        const vResp = await fetch('/api/v1/vehicles/live?limit=100', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (vResp.ok) {
            const vehicles = await vResp.json();
            const vSel = document.getElementById('maint-log-vehicle');
            if (vSel && vehicles.length) vSel.innerHTML = vehicles.map(v => `<option value="${v.id}">${v.name || v.plate || 'Vehicle ' + v.id}</option>`).join('');
        }
    } catch(e) {}
    const typeSel = document.getElementById('maint-log-type');
    if (typeSel) {
        try {
            const tResp = await fetch('/api/maintenance/planner/types?page_size=50&active_only=true', { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (tResp.ok) {
                const tData = await tResp.json();
                const types = tData.items || tData || [];
                typeSel.innerHTML = '<option value="">-- Select --</option>' + types.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
            } else {
                const defaultNames = { oil_change: 'Oil Change', filter_change: 'Filter Change', brake_service: 'Brake Service', tire_rotation: 'Tire Rotation', transmission: 'Transmission Service', coolant: 'Coolant Flush', spark_plugs: 'Spark Plugs', inspection: 'General Inspection' };
                typeSel.innerHTML = '<option value="">-- Select --</option>' + Object.entries(MAINT_TYPES).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join('');
            }
        } catch(e) {
            const defaultNames = { oil_change: 'Oil Change', filter_change: 'Filter Change', brake_service: 'Brake Service', tire_rotation: 'Tire Rotation', transmission: 'Transmission Service', coolant: 'Coolant Flush', spark_plugs: 'Spark Plugs', inspection: 'General Inspection' };
            typeSel.innerHTML = '<option value="">-- Select --</option>' + Object.entries(MAINT_TYPES).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join('');
        }
    }
    try {
        const wResp = await fetch('/api/maintenance/workshops', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (wResp.ok) {
            const result = await wResp.json();
            const workshops = result.workshops || [];
            const wSel = document.getElementById('maint-log-workshop');
            if (wSel) wSel.innerHTML = '<option value="">-- Select --</option>' + workshops.map(w => `<option value="${w.id}">${w.name}</option>`).join('');
        }
    } catch(e) {}
}

async function submitMaintenanceLog(e) {
    e.preventDefault();
    if (!authToken) return;
    const payload = {
        device_id: parseInt(document.getElementById('maint-log-vehicle')?.value) || 0,
        schedule_id: parseInt(document.getElementById('maint-log-type')?.value) || 1,
        service_value: parseFloat(document.getElementById('maint-log-odo')?.value) || 0,
        service_type: document.getElementById('maint-log-stype')?.value || 'scheduled',
        workshop_id: parseInt(document.getElementById('maint-log-workshop')?.value) || null,
        technician: document.getElementById('maint-log-tech')?.value || '',
        cost: parseFloat(document.getElementById('maint-log-cost')?.value) || 0,
        notes: document.getElementById('maint-log-notes')?.value || ''
    };
    try {
        const resp = await fetch('/api/maintenance/log', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` }, body: JSON.stringify(payload) });
        if (resp.ok) { closeMaintenanceLogModal(); showNotification('Maintenance log recorded', 'scheduled'); loadMaintenanceDashboard(); }
        else { showNotification('Failed to save log', 'fault'); }
    } catch(err) { showNotification('Error saving log', 'fault'); }
}

window.submitMaintenanceLog = submitMaintenanceLog;
window.openMaintenanceLogForm = openMaintenanceLogModal;

// ==================== PLANNER & RULE ENGINE ====================

let plannerTabState = 'types';

function initPlanner() {
    loadPlannerDashboard();
}

async function loadPlannerDashboard() {
    if (!authToken) return;
    try {
        const [typesResp, rulesResp, templatesResp] = await Promise.all([
            fetch('/api/maintenance/planner/types', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/rules', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/templates', { headers: { 'Authorization': `Bearer ${authToken}` } })
        ]);
        const types = typesResp.ok ? await typesResp.json() : { items: [], total: 0 };
        const rules = rulesResp.ok ? await rulesResp.json() : { items: [], total: 0 };
        let templates = templatesResp.ok ? await templatesResp.json() : { items: [], total: 0 };
        if (!templates.items || templates.items.length === 0) {
            const seedResp = await fetch('/api/maintenance/planner/templates/seed', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } });
            if (seedResp.ok) {
                const reResp = await fetch('/api/maintenance/planner/templates', { headers: { 'Authorization': `Bearer ${authToken}` } });
                templates = reResp.ok ? await reResp.json() : templates;
            }
        }
        const hasZeroRules = (templates.items || []).some(t => (t.rule_count || 0) === 0);
        if (hasZeroRules) {
            const valResp = await fetch('/api/maintenance/planner/validate', { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (valResp.ok) {
                const reResp = await fetch('/api/maintenance/planner/templates', { headers: { 'Authorization': `Bearer ${authToken}` } });
                templates = reResp.ok ? await reResp.json() : templates;
            }
        }
        renderPlannerTab(plannerTabState, { types, rules, templates });
    } catch (e) {
        console.error('Planner load error:', e);
        const tc = document.getElementById('planner-tab-content');
        if (tc) tc.innerHTML = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Failed to load planner data.</div>';
    }
}

function switchPlannerTab(tab) {
    plannerTabState = tab;
    document.querySelectorAll('.planner-tab-btn').forEach(b => {
        b.classList.remove('primary');
        b.style.background = 'transparent';
        b.style.color = 'var(--text-secondary)';
    });
    const activeBtn = document.querySelector(`.planner-tab-btn[data-planner="${tab}"]`);
    if (activeBtn) {
        activeBtn.classList.add('primary');
        activeBtn.style.background = 'var(--brand-primary)';
        activeBtn.style.color = '#fff';
    }
    loadPlannerDashboard();
}

async function renderPlannerTab(tab, cachedData) {
    const tc = document.getElementById('planner-tab-content');
    if (!tc) return;
    let html = '';

    if (tab === 'types') {
        html = await renderTypesTable(cachedData ? cachedData.types : null);
    } else if (tab === 'rules') {
        html = await renderRulesTable(cachedData ? cachedData.rules : null);
    } else if (tab === 'templates') {
        html = await renderTemplatesTable(cachedData ? cachedData.templates : null);
    } else if (tab === 'plans') {
        html = await renderPlansTable();
    } else if (tab === 'overrides') {
        html = await renderOverridesTable();
    } else if (tab === 'history') {
        html = await renderHistoryTable();
    }

    tc.innerHTML = html || '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No data available</div>';
    lucide.createIcons({ el: tc });
}

// ==================== MAINTENANCE TYPES MANAGEMENT ====================

let typesState = { page: 1, pageSize: 50, search: '', category: '', status: 'active', sortBy: 'name', sortOrder: 'asc', total: 0, totalPages: 0 };

async function renderTypesTable(typesData) {
    if (!typesData) {
        typesData = await loadTypesData();
    }
    const items = typesData.items || [];
    const total = typesData.total || 0;
    const totalPages = typesData.total_pages || 1;

    // Fetch summary and categories for the toolbar
    let summary = { total: 0, active: 0, inactive: 0, deleted: 0, system: 0 };
    let categories = [];
    try {
        const [sResp, cResp] = await Promise.all([
            fetch('/api/maintenance/planner/types/summary', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/types/categories', { headers: { 'Authorization': `Bearer ${authToken}` } })
        ]);
        if (sResp.ok) summary = await sResp.json();
        if (cResp.ok) categories = await cResp.json();
    } catch (e) {}

    const statusOpts = ['active','inactive','deleted','all'];
    const currentStatus = typesState.status;
    const currentCategory = typesState.category;
    const currentSearch = typesState.search;

    let html = `
    <div style="display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:20px;">
        <div class="premium-card" style="padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:var(--brand-primary);">${summary.total}</div><div style="font-size:0.75rem; color:var(--text-dim); font-weight:600; text-transform:uppercase;">Total Types</div></div>
        <div class="premium-card" style="padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:var(--brand-success);">${summary.active}</div><div style="font-size:0.75rem; color:var(--text-dim); font-weight:600; text-transform:uppercase;">Active</div></div>
        <div class="premium-card" style="padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:var(--brand-warning);">${summary.inactive}</div><div style="font-size:0.75rem; color:var(--text-dim); font-weight:600; text-transform:uppercase;">Inactive</div></div>
        <div class="premium-card" style="padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:var(--brand-danger);">${summary.deleted}</div><div style="font-size:0.75rem; color:var(--text-dim); font-weight:600; text-transform:uppercase;">Deleted</div></div>
        <div class="premium-card" style="padding:16px; text-align:center;"><div style="font-size:1.8rem; font-weight:800; color:var(--text-secondary);">${summary.system}</div><div style="font-size:0.75rem; color:var(--text-dim); font-weight:600; text-transform:uppercase;">System</div></div>
    </div>
    <div class="premium-card" style="padding:20px;">
        <div style="display:flex; gap:10px; align-items:center; margin-bottom:16px; flex-wrap:wrap;">
            <div class="dash-search-container" style="flex:1; min-width:200px;">
                <i data-lucide="search" style="position:absolute; left:14px; top:50%; transform:translateY(-50%); width:16px; color:var(--text-dim);"></i>
                <input type="text" id="types-search" placeholder="Search types..." value="${currentSearch}" onkeyup="if(event.key==='Enter'){ typesState.search=this.value; typesState.page=1; loadPlannerDashboard(); }" style="width:100%; padding:10px 14px 10px 40px; border-radius:10px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <select id="types-category-filter" onchange="typesState.category=this.value; typesState.page=1; loadPlannerDashboard();" style="padding:10px 14px; border-radius:10px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; min-width:140px;">
                <option value="">All Categories</option>
                ${categories.map(c => `<option value="${c}" ${c === currentCategory ? 'selected' : ''}>${c}</option>`).join('')}
            </select>
            <select id="types-status-filter" onchange="typesState.status=this.value; typesState.page=1; loadPlannerDashboard();" style="padding:10px 14px; border-radius:10px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; min-width:120px;">
                <option value="active" ${currentStatus==='active'?'selected':''}>Active</option>
                <option value="inactive" ${currentStatus==='inactive'?'selected':''}>Inactive</option>
                <option value="deleted" ${currentStatus==='deleted'?'selected':''}>Deleted</option>
                <option value="all" ${currentStatus==='all'?'selected':''}>All</option>
            </select>
            <button class="glass-btn" onclick="typesState.search=''; document.getElementById('types-search').value=''; typesState.page=1; loadPlannerDashboard();" style="padding:10px 16px;" title="Refresh"><i data-lucide="refresh-cw" style="width:16px;"></i></button>
            <button class="glass-btn primary" onclick="openTypeModal()" style="padding:10px 16px;"><i data-lucide="plus" style="width:16px;"></i> Add Type</button>
            <button class="glass-btn" onclick="exportTypesCSV()" style="padding:10px 16px;" title="Export CSV"><i data-lucide="download" style="width:16px;"></i></button>
        </div>

        <div style="overflow-x:auto;">
        <table class="modern-table" style="width:100%;">
            <thead><tr>
                <th onclick="sortTypes('name')" style="cursor:pointer;">Name ${typesState.sortBy==='name'?(typesState.sortOrder==='asc'?'▲':'▼'):''}</th>
                <th onclick="sortTypes('category')" style="cursor:pointer;">Category ${typesState.sortBy==='category'?(typesState.sortOrder==='asc'?'▲':'▼'):''}</th>
                <th onclick="sortTypes('default_interval_km')" style="cursor:pointer;">Default KM ${typesState.sortBy==='default_interval_km'?(typesState.sortOrder==='asc'?'▲':'▼'):''}</th>
                <th onclick="sortTypes('default_interval_days')" style="cursor:pointer;">Default Days ${typesState.sortBy==='default_interval_days'?(typesState.sortOrder==='asc'?'▲':'▼'):''}</th>
                <th onclick="sortTypes('priority')" style="cursor:pointer;">Priority ${typesState.sortBy==='priority'?(typesState.sortOrder==='asc'?'▲':'▼'):''}</th>
                <th>Engine Hrs</th>
                <th onclick="sortTypes('updated_at')" style="cursor:pointer;">Updated ${typesState.sortBy==='updated_at'?(typesState.sortOrder==='asc'?'▲':'▼'):''}</th>
                <th>Status</th>
                <th>Actions</th>
            </tr></thead>
            <tbody>
                ${items.length === 0 ? '<tr><td colspan="9" style="text-align:center; padding:40px; color:var(--text-dim);">No types found.</td></tr>' :
                items.map(t => {
                    const isDeleted = t.is_deleted;
                    const isActive = t.is_active && !isDeleted;
                    const badgeClass = isDeleted ? 'danger' : (isActive ? 'success' : 'warning');
                    const badgeText = isDeleted ? 'Deleted' : (isActive ? 'Active' : 'Inactive');
                    const priorityClass = t.priority === 'critical' ? 'danger' : (t.priority === 'high' ? 'warning' : 'primary');
                    return `<tr>
                        <td><strong>${t.name}</strong>${t.is_system ? ' <span style="font-size:0.65rem; color:var(--text-dim);">[System]</span>' : ''}</td>
                        <td>${t.category || '—'}</td>
                        <td>${t.default_interval_km > 0 ? t.default_interval_km.toLocaleString() + ' km' : '—'}</td>
                        <td>${t.default_interval_days > 0 ? t.default_interval_days + ' days' : '—'}</td>
                        <td><span class="stats-badge ${priorityClass}">${t.priority || 'medium'}</span></td>
                        <td>${t.default_engine_hours != null ? t.default_engine_hours + ' hrs' : '—'}</td>
                        <td style="font-size:0.75rem; color:var(--text-dim);">${t.updated_at ? t.updated_at.split('T')[0] : '—'}</td>
                        <td><span class="stats-badge ${badgeClass}">${badgeText}</span></td>
                        <td>
                            <div style="display:flex; gap:4px; flex-wrap:wrap;">
                                <button class="glass-btn secondary" onclick="editType(${t.id})" style="padding:4px 8px; font-size:0.7rem;" title="Edit"><i data-lucide="pencil" style="width:12px;"></i></button>
                                ${isDeleted ? 
                                    `<button class="glass-btn primary" onclick="restoreType(${t.id})" style="padding:4px 8px; font-size:0.7rem;" title="Restore"><i data-lucide="rotate-ccw" style="width:12px;"></i></button>` :
                                    (isActive ? 
                                        `<button class="glass-btn warning" onclick="deactivateType(${t.id})" style="padding:4px 8px; font-size:0.7rem;" title="Deactivate"><i data-lucide="pause" style="width:12px;"></i></button>` :
                                        `<button class="glass-btn success" onclick="activateType(${t.id})" style="padding:4px 8px; font-size:0.7rem;" title="Activate"><i data-lucide="play" style="width:12px;"></i></button>`
                                    )
                                }
                                ${!isDeleted && !t.is_system ? 
                                    `<button class="glass-btn danger" onclick="deleteType(${t.id})" style="padding:4px 8px; font-size:0.7rem;" title="Delete"><i data-lucide="trash-2" style="width:12px;"></i></button>` : ''
                                }
                            </div>
                        </td>
                    </tr>`;
                }).join('')}
            </tbody>
        </table>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px;">
            <span style="font-size:0.8rem; color:var(--text-dim);">${total} type${total !== 1 ? 's' : ''}</span>
            <div style="display:flex; gap:4px; align-items:center;">
                <button class="glass-btn" onclick="typesState.page=Math.max(1,typesState.page-1); loadPlannerDashboard();" ${typesState.page <= 1 ? 'disabled style="opacity:0.4;"' : ''} style="padding:6px 12px; font-size:0.75rem;"><i data-lucide="chevron-left" style="width:14px;"></i></button>
                ${generatePagination(totalPages, typesState.page).map(p => 
                    `<button class="glass-btn ${p === typesState.page ? 'primary' : ''}" onclick="typesState.page=${p}; loadPlannerDashboard();" style="padding:6px 12px; font-size:0.75rem; ${p === typesState.page ? 'background:var(--brand-primary); color:#fff;' : ''}">${p}</button>`
                ).join('')}
                <button class="glass-btn" onclick="typesState.page=Math.min(${totalPages},typesState.page+1); loadPlannerDashboard();" ${typesState.page >= totalPages ? 'disabled style="opacity:0.4;"' : ''} style="padding:6px 12px; font-size:0.75rem;"><i data-lucide="chevron-right" style="width:14px;"></i></button>
            </div>
        </div>
    </div>`;
    return html;
}

function sortTypes(field) {
    if (typesState.sortBy === field) {
        typesState.sortOrder = typesState.sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        typesState.sortBy = field;
        typesState.sortOrder = 'asc';
    }
    typesState.page = 1;
    loadPlannerDashboard();
}

function generatePagination(totalPages, current) {
    const pages = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        pages.push(1);
        if (current > 3) pages.push('...');
        for (let i = Math.max(2, current - 1); i <= Math.min(totalPages - 1, current + 1); i++) pages.push(i);
        if (current < totalPages - 2) pages.push('...');
        pages.push(totalPages);
    }
    return pages.filter(p => p !== '...' ? true : Math.random() > -1);
}

async function loadTypesData() {
    const params = new URLSearchParams({
        page: typesState.page, page_size: typesState.pageSize,
        sort_by: typesState.sortBy, sort_order: typesState.sortOrder
    });
    if (typesState.search) params.set('search', typesState.search);
    if (typesState.category) params.set('category', typesState.category);
    if (typesState.status === 'active') { params.set('active_only', 'true'); }
    else if (typesState.status === 'inactive') { params.set('active_only', 'false'); }
    else if (typesState.status === 'deleted') { params.set('deleted_only', 'true'); }
    try {
        const resp = await fetch(`/api/maintenance/planner/types?${params}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        const data = resp.ok ? await resp.json() : { items: [], total: 0 };
        typesState.total = data.total;
        typesState.totalPages = data.total_pages || 1;
        return data;
    } catch (e) {
        return { items: [], total: 0 };
    }
}

function exportTypesCSV() {
    const rows = [['Name','Slug','Category','Default KM','Default Days','Engine Hours','Priority','Status','Created']];
    // Fetch all types and export
    fetch('/api/maintenance/planner/types?page_size=1000', { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.json())
        .then(data => {
            (data.items || []).forEach(t => {
                rows.push([t.name, t.slug, t.category||'', t.default_interval_km||'', t.default_interval_days||'', t.default_engine_hours||'', t.priority||'medium', t.is_deleted ? 'Deleted' : (t.is_active ? 'Active' : 'Inactive'), t.created_at||'']);
            });
            const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n');
            const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'maintenance_types.csv';
            a.click();
            URL.revokeObjectURL(a.href);
            showNotification('CSV exported', 'scheduled');
        })
        .catch(() => showNotification('Export failed', 'fault'));
}

// ==================== TYPE MODAL ====================

function openTypeModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px);';
    modal.innerHTML = `
    <div class="premium-card" style="width:560px; max-width:92vw; max-height:90vh; overflow-y:auto; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.2rem; font-weight:700; color:var(--text-primary);"><i data-lucide="settings" style="width:20px; vertical-align:middle; margin-right:8px;"></i> Add Maintenance Type</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; color:var(--text-dim); cursor:pointer; font-size:1.4rem; padding:4px;">&times;</button>
        </div>
        <form id="type-form" onsubmit="submitTypeModal(event)" style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
            <div style="grid-column:1/-1;">
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Name *</label>
                <input type="text" id="type-name" required placeholder="e.g., Engine Oil" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Slug</label>
                <input type="text" id="type-slug" placeholder="e.g., engine_oil" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Category</label>
                <input type="text" id="type-category" placeholder="e.g., engine, brakes" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Priority</label>
                <select id="type-priority" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                    <option value="low">Low</option>
                    <option value="medium" selected>Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                </select>
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Default Interval (KM)</label>
                <input type="number" id="type-km" placeholder="5000" min="0" step="100" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Default Interval (Days)</label>
                <input type="number" id="type-days" placeholder="180" min="0" step="1" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Engine Hours</label>
                <input type="number" id="type-hours" placeholder="e.g., 250" min="0" step="10" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Color</label>
                <input type="color" id="type-color" value="#3b82f6" style="width:100%; height:40px; padding:4px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); cursor:pointer;">
            </div>
            <div style="grid-column:1/-1;">
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Description</label>
                <textarea id="type-description" rows="2" placeholder="Optional description..." style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; resize:vertical;"></textarea>
            </div>
            <div style="grid-column:1/-1; display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:12px; border-radius:8px; border:1px solid var(--border-light); background:transparent; color:var(--text-secondary); cursor:pointer; font-weight:600; font-size:0.85rem;">Cancel</button>
                <button type="submit" style="flex:1; padding:12px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600; font-size:0.85rem;"><i data-lucide="check" style="width:16px; vertical-align:middle; margin-right:6px;"></i> Create Type</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
    lucide.createIcons({ el: modal });
}

async function submitTypeModal(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true; btn.textContent = 'Creating...';
    const payload = {
        name: document.getElementById('type-name').value.trim(),
        slug: document.getElementById('type-slug').value.trim() || undefined,
        category: document.getElementById('type-category').value.trim() || null,
        priority: document.getElementById('type-priority').value,
        default_interval_km: parseFloat(document.getElementById('type-km').value) || 0,
        default_interval_days: parseInt(document.getElementById('type-days').value) || 0,
        default_engine_hours: parseFloat(document.getElementById('type-hours').value) || null,
        color: document.getElementById('type-color').value,
        description: document.getElementById('type-description').value.trim() || null
    };
    if (!payload.name) { showNotification('Name is required', 'fault'); btn.disabled = false; btn.innerHTML = '<i data-lucide="check" style="width:16px; vertical-align:middle; margin-right:6px;"></i> Create Type'; lucide.createIcons(); return; }
    try {
        const resp = await fetch('/api/maintenance/planner/types', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify(payload)
        });
        if (resp.ok) {
            closeModal();
            typesState.page = 1;
            await loadPlannerDashboard();
            await refreshMaintDashboardCache();
            showNotification('Type created successfully', 'scheduled');
        } else {
            const err = await resp.json();
            showNotification(err.detail || 'Failed to create type', 'fault');
        }
    } catch (err) { showNotification('Error creating type', 'fault'); }
    btn.disabled = false; btn.innerHTML = '<i data-lucide="check" style="width:16px; vertical-align:middle; margin-right:6px;"></i> Create Type'; lucide.createIcons();
}

function closeModal() { document.querySelector('.modal-overlay')?.remove(); }

async function editType(id) {
    let typeData = null;
    try {
        const resp = await fetch(`/api/maintenance/planner/types/${id}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) typeData = await resp.json();
    } catch (e) {}
    if (!typeData) { showNotification('Could not load type data', 'fault'); return; }

    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px);';
    modal.innerHTML = `
    <div class="premium-card" style="width:560px; max-width:92vw; max-height:90vh; overflow-y:auto; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.2rem; font-weight:700; color:var(--text-primary);"><i data-lucide="edit" style="width:20px; vertical-align:middle; margin-right:8px;"></i> Edit: ${typeData.name}</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; color:var(--text-dim); cursor:pointer; font-size:1.4rem; padding:4px;">&times;</button>
        </div>
        <form id="edit-type-form" onsubmit="submitEditTypeModal(event, ${id})" style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">
            <div style="grid-column:1/-1;">
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Name *</label>
                <input type="text" id="edit-type-name" required value="${typeData.name}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Slug</label>
                <input type="text" id="edit-type-slug" value="${typeData.slug || ''}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Category</label>
                <input type="text" id="edit-type-category" value="${typeData.category || ''}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Priority</label>
                <select id="edit-type-priority" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                    ${['low','medium','high','critical'].map(p => `<option value="${p}" ${typeData.priority === p ? 'selected' : ''}>${p.charAt(0).toUpperCase()+p.slice(1)}</option>`).join('')}
                </select>
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Default Interval (KM)</label>
                <input type="number" id="edit-type-km" value="${typeData.default_interval_km || ''}" min="0" step="100" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Default Interval (Days)</label>
                <input type="number" id="edit-type-days" value="${typeData.default_interval_days || ''}" min="0" step="1" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Engine Hours</label>
                <input type="number" id="edit-type-hours" value="${typeData.default_engine_hours || ''}" min="0" step="10" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Color</label>
                <input type="color" id="edit-type-color" value="${typeData.color || '#3b82f6'}" style="width:100%; height:40px; padding:4px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); cursor:pointer;">
            </div>
            <div style="grid-column:1/-1;">
                <label style="display:block; font-size:0.75rem; font-weight:700; color:var(--text-dim); margin-bottom:4px;">Description</label>
                <textarea id="edit-type-description" rows="2" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; resize:vertical;">${typeData.description || ''}</textarea>
            </div>
            <div style="grid-column:1/-1; display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:12px; border-radius:8px; border:1px solid var(--border-light); background:transparent; color:var(--text-secondary); cursor:pointer; font-weight:600; font-size:0.85rem;">Cancel</button>
                <button type="submit" style="flex:1; padding:12px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600; font-size:0.85rem;"><i data-lucide="save" style="width:16px; vertical-align:middle; margin-right:6px;"></i> Save Changes</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
    lucide.createIcons({ el: modal });
}

async function submitEditTypeModal(e, id) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true; btn.textContent = 'Saving...';
    const payload = {
        name: document.getElementById('edit-type-name').value.trim(),
        slug: document.getElementById('edit-type-slug').value.trim() || null,
        category: document.getElementById('edit-type-category').value.trim() || null,
        priority: document.getElementById('edit-type-priority').value,
        default_interval_km: parseFloat(document.getElementById('edit-type-km').value) || 0,
        default_interval_days: parseInt(document.getElementById('edit-type-days').value) || 0,
        default_engine_hours: parseFloat(document.getElementById('edit-type-hours').value) || null,
        color: document.getElementById('edit-type-color').value,
        description: document.getElementById('edit-type-description').value.trim() || null
    };
    if (!payload.name) { showNotification('Name is required', 'fault'); btn.disabled = false; btn.innerHTML = '<i data-lucide="save" style="width:16px; vertical-align:middle; margin-right:6px;"></i> Save Changes'; lucide.createIcons(); return; }
    try {
        const resp = await fetch(`/api/maintenance/planner/types/${id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify(payload)
        });
        if (resp.ok) {
            closeModal();
            await loadPlannerDashboard();
            await refreshMaintDashboardCache();
            showNotification('Type updated successfully', 'scheduled');
        } else {
            const err = await resp.json();
            showNotification(err.detail || 'Failed to update type', 'fault');
        }
    } catch (err) { showNotification('Error updating type', 'fault'); }
    btn.disabled = false; btn.innerHTML = '<i data-lucide="save" style="width:16px; vertical-align:middle; margin-right:6px;"></i> Save Changes'; lucide.createIcons();
}

function deleteType(id) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px);';
    modal.innerHTML = `
    <div class="premium-card" style="width:400px; max-width:90vw; padding:32px; text-align:center;">
        <div style="font-size:3rem; margin-bottom:16px; color:var(--brand-danger);"><i data-lucide="alert-triangle" style="width:48px; height:48px;"></i></div>
        <h3 style="font-size:1.1rem; font-weight:700; margin-bottom:8px; color:var(--text-primary);">Delete Maintenance Type?</h3>
        <p style="color:var(--text-dim); font-size:0.85rem; margin-bottom:20px;">This will soft-delete this type. You can restore it later.</p>
        <div style="display:flex; gap:10px;">
            <button onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:12px; border-radius:8px; border:1px solid var(--border-light); background:transparent; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
            <button onclick="confirmDeleteType(${id})" style="flex:1; padding:12px; border-radius:8px; border:none; background:var(--brand-danger); color:#fff; cursor:pointer; font-weight:600;"><i data-lucide="trash-2" style="width:16px; vertical-align:middle; margin-right:6px;"></i> Delete</button>
        </div>
    </div>`;
    document.body.appendChild(modal);
    lucide.createIcons({ el: modal });
}

async function confirmDeleteType(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/types/${id}`, {
            method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            closeModal();
            await loadPlannerDashboard();
            await refreshMaintDashboardCache();
            showNotification('Type deleted', 'scheduled');
        } else {
            const err = await resp.json();
            showNotification(err.detail || 'Failed to delete', 'fault');
        }
    } catch (err) { showNotification('Error deleting type', 'fault'); }
}

async function restoreType(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/types/${id}/restore`, {
            method: 'PATCH', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) { await loadPlannerDashboard(); await refreshMaintDashboardCache(); showNotification('Type restored', 'scheduled'); }
        else { const err = await resp.json(); showNotification(err.detail || 'Failed to restore', 'fault'); }
    } catch (err) { showNotification('Error restoring type', 'fault'); }
}

async function activateType(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/types/${id}/activate`, {
            method: 'PATCH', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) { await loadPlannerDashboard(); await refreshMaintDashboardCache(); showNotification('Type activated', 'scheduled'); }
        else { const err = await resp.json(); showNotification(err.detail || 'Failed to activate', 'fault'); }
    } catch (err) { showNotification('Error activating type', 'fault'); }
}

async function deactivateType(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/types/${id}/deactivate`, {
            method: 'PATCH', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) { await loadPlannerDashboard(); await refreshMaintDashboardCache(); showNotification('Type deactivated', 'scheduled'); }
        else { const err = await resp.json(); showNotification(err.detail || 'Failed to deactivate', 'fault'); }
    } catch (err) { showNotification('Error deactivating type', 'fault'); }
}

async function renderRulesTable(rulesData) {
    if (!rulesData) {
        const resp = await fetch('/api/maintenance/planner/rules', { headers: { 'Authorization': `Bearer ${authToken}` } });
        rulesData = resp.ok ? await resp.json() : { items: [], total: 0 };
    }
    const items = rulesData.items || [];
    if (!items.length) return '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No rules configured.</div>';
    return `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;"><span style="font-size:0.85rem; color:var(--text-dim);">${rulesData.total} rules</span><button class="glass-btn primary" onclick="openRuleModal()" style="padding:8px 16px; font-size:0.8rem;"><i data-lucide="plus" style="width:14px; margin-right:4px;"></i> Add Rule</button></div><table class="modern-table" style="width:100%;"><thead><tr><th>Name</th><th>Type</th><th>Trigger KM</th><th>Trigger Days</th><th>Trigger Hrs</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead><tbody>${items.map(r => `<tr><td>${r.name}</td><td>${r.type_name || r.type_id}</td><td>${r.trigger_km != null ? r.trigger_km.toLocaleString() + ' km' : '—'}</td><td>${r.trigger_days != null ? r.trigger_days + ' days' : '—'}</td><td>${r.trigger_hours != null ? r.trigger_hours + ' hrs' : '—'}</td><td><span class="stats-badge ${r.priority === 'critical' ? 'danger' : r.priority === 'high' ? 'warning' : r.priority === 'medium' ? 'warning' : 'primary'}">${r.priority}</span></td><td><span class="stats-badge ${r.is_active ? 'success' : 'warning'}">${r.is_active ? 'Active' : 'Inactive'}</span></td><td><div style="display:flex; gap:4px;"><button class="glass-btn secondary" onclick="editRule(${r.id})" style="padding:4px 8px; font-size:0.7rem;">Edit</button><button class="glass-btn danger" onclick="deleteRule(${r.id})" style="padding:4px 8px; font-size:0.7rem;">Del</button></div></td></tr>`).join('')}</tbody></table>`;
}

let _tmplState = { search: '', category: '', status: 'all', page: 1, sortField: 'name', sortOrder: 'asc' };

async function renderTemplatesTable(templatesData) {
    if (!templatesData) {
        const params = new URLSearchParams({
            page: _tmplState.page, page_size: 20,
            search: _tmplState.search, category: _tmplState.category,
            status: _tmplState.status
        });
        const resp = await fetch(`/api/maintenance/planner/templates?${params}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        templatesData = resp.ok ? await resp.json() : { items: [], total: 0, categories: [] };
    }
    const items = templatesData.items || [];
    const categories = templatesData.categories || [];
    let html = '';
    // Top bar
    html += `<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:16px;">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <input type="text" id="tmpl-search" placeholder="Search templates..." value="${_tmplState.search}" oninput="debouncedTmplSearch()" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.82rem;width:180px;">
            <select id="tmpl-category-filter" onchange="switchTmplFilter()" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.82rem;">
                <option value="">All Categories</option>
                ${categories.map(c => `<option value="${c}" ${_tmplState.category === c ? 'selected' : ''}>${c}</option>`).join('')}
            </select>
            <select id="tmpl-status-filter" onchange="switchTmplFilter()" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.82rem;">
                <option value="all" ${_tmplState.status === 'all' ? 'selected' : ''}>All</option>
                <option value="active" ${_tmplState.status === 'active' ? 'selected' : ''}>Active</option>
                <option value="inactive" ${_tmplState.status === 'inactive' ? 'selected' : ''}>Inactive</option>
                <option value="archived" ${_tmplState.status === 'archived' ? 'selected' : ''}>Archived</option>
            </select>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
            <span style="font-size:0.85rem;color:var(--text-dim);">${templatesData.total} templates</span>
            <button class="glass-btn primary" onclick="openTemplateModal()" style="padding:8px 16px;font-size:0.8rem;"><i data-lucide="plus" style="width:14px;margin-right:4px;"></i> New Template</button>
            <button class="glass-btn secondary" onclick="seedDefaultTemplates()" style="padding:8px 12px;font-size:0.7rem;" title="Seed defaults if empty"><i data-lucide="database" style="width:12px;"></i></button>
        </div>
    </div>`;

    if (!items.length) {
        html += '<div class="premium-card" style="padding:40px;text-align:center;color:var(--text-dim);">No templates found. Click <strong>New Template</strong> to create one or seed defaults.</div>';
        return html;
    }

    html += `<table class="modern-table" style="width:100%;"><thead><tr>
        <th onclick="sortTmplTable('name')" style="cursor:pointer;">Template ${_tmplState.sortField === 'name' ? (_tmplState.sortOrder === 'asc' ? '▲' : '▼') : ''}</th>
        <th>Category</th>
        <th onclick="sortTmplTable('rule_count')" style="cursor:pointer;">Rules ${_tmplState.sortField === 'rule_count' ? (_tmplState.sortOrder === 'asc' ? '▲' : '▼') : ''}</th>
        <th onclick="sortTmplTable('vehicle_count')" style="cursor:pointer;">Vehicles ${_tmplState.sortField === 'vehicle_count' ? (_tmplState.sortOrder === 'asc' ? '▲' : '▼') : ''}</th>
        <th>Status</th>
        <th>Created</th>
        <th>Actions</th>
    </tr></thead><tbody>`;
    items.forEach(t => {
        const statusBadge = t.is_archived ? '<span class="stats-badge warning">Archived</span>' :
            t.is_active ? '<span class="stats-badge success">Active</span>' :
            '<span class="stats-badge warning">Inactive</span>';
        html += `<tr>
            <td><strong style="cursor:pointer;color:var(--brand-primary);" onclick="viewTemplateRules(${t.id})">${t.name}</strong>
                ${t.is_system ? '<span style="font-size:0.65rem;color:var(--text-dim);margin-left:4px;">(system)</span>' : ''}
                ${t.description ? `<div style="font-size:0.7rem;color:var(--text-dim);">${t.description.substring(0, 50)}${t.description.length > 50 ? '...' : ''}</div>` : ''}
            </td>
            <td>${t.vehicle_category || t.vehicle_type || '—'}</td>
            <td>${t.rule_count || 0}</td>
            <td>${t.vehicle_count || 0}</td>
            <td>${statusBadge}</td>
            <td style="font-size:0.75rem;color:var(--text-dim);">${t.created_at ? t.created_at.split('T')[0] : '—'}</td>
            <td><div style="display:flex;gap:4px;">
                <button class="glass-btn secondary" onclick="viewTemplateRules(${t.id})" style="padding:4px 8px;font-size:0.7rem;">View</button>
                <button class="glass-btn secondary" onclick="editTemplate(${t.id})" style="padding:4px 8px;font-size:0.7rem;">Edit</button>
                ${!t.is_archived && t.is_active ? `<button class="glass-btn secondary" onclick="deactivateTemplateAction(${t.id})" style="padding:4px 8px;font-size:0.7rem;">Deact</button>` : ''}
                ${!t.is_active && !t.is_archived ? `<button class="glass-btn secondary" onclick="activateTemplateAction(${t.id})" style="padding:4px 8px;font-size:0.7rem;">Activate</button>` : ''}
                ${t.is_archived ? `<button class="glass-btn secondary" onclick="activateTemplateAction(${t.id})" style="padding:4px 8px;font-size:0.7rem;">Restore</button>` : ''}
                ${!t.is_system ? `<button class="glass-btn secondary" onclick="duplicateTemplateAction(${t.id})" style="padding:4px 8px;font-size:0.7rem;">Dup</button>` : ''}
                ${!t.is_system ? `<button class="glass-btn danger" onclick="deleteTemplate(${t.id})" style="padding:4px 8px;font-size:0.7rem;">Del</button>` : ''}
            </div></td>
        </tr>`;
    });
    html += '</tbody></table>';

    if (templatesData.total_pages > 1) {
        html += `<div style="display:flex;justify-content:center;gap:8px;margin-top:16px;">
            ${Array.from({length: templatesData.total_pages}, (_, i) => i + 1).map(p =>
                `<button class="glass-btn ${p === _tmplState.page ? 'primary' : ''}" onclick="gotoTmplPage(${p})" style="padding:6px 14px;font-size:0.8rem;">${p}</button>`
            ).join('')}
        </div>`;
    }
    return html;
}

function switchTmplFilter() {
    _tmplState.category = document.getElementById('tmpl-category-filter')?.value || '';
    _tmplState.status = document.getElementById('tmpl-status-filter')?.value || 'all';
    _tmplState.page = 1;
    switchPlannerTab('templates');
}

let _tmplDebounceTimer = null;
function debouncedTmplSearch() {
    clearTimeout(_tmplDebounceTimer);
    _tmplDebounceTimer = setTimeout(() => {
        _tmplState.search = document.getElementById('tmpl-search')?.value || '';
        _tmplState.page = 1;
        switchPlannerTab('templates');
    }, 400);
}

function sortTmplTable(field) {
    if (_tmplState.sortField === field) _tmplState.sortOrder = _tmplState.sortOrder === 'asc' ? 'desc' : 'asc';
    else { _tmplState.sortField = field; _tmplState.sortOrder = 'asc'; }
    switchPlannerTab('templates');
}

function gotoTmplPage(p) { _tmplState.page = p; switchPlannerTab('templates'); }

async function seedDefaultTemplates() {
    try {
        const resp = await fetch('/api/maintenance/planner/templates/seed', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } });
        const data = resp.ok ? await resp.json() : { seeded: 0 };
        if (data.seeded > 0) {
            await switchPlannerTab('templates');
            await refreshMaintDashboardCache();
            showNotification(`${data.seeded} default templates created`, 'scheduled');
        } else showNotification('Templates already exist', 'scheduled');
    } catch(e) { showNotification('Error seeding templates', 'fault'); }
}

// ==================== TEMPLATE BUILDER MODAL ====================

let _templateEditId = null;
let _templateRules = [];

async function openTemplateModal(editId) {
    _templateEditId = editId || null;
    _templateRules = [];
    let templateData = null;
    if (editId) {
        try {
            const resp = await fetch(`/api/maintenance/planner/templates/${editId}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (resp.ok) templateData = await resp.json();
        } catch(e) {}
    }
    if (templateData) _templateRules = (templateData.rules || []).map(r => ({ ...r, uid: Date.now() + Math.random() }));

    const [rulesResp, typesResp] = await Promise.all([
        fetch('/api/maintenance/planner/rules?page_size=200&active_only=true', { headers: { 'Authorization': `Bearer ${authToken}` } }),
        fetch('/api/maintenance/planner/types?page_size=200', { headers: { 'Authorization': `Bearer ${authToken}` } })
    ]);
    const allRules = (rulesResp.ok ? await rulesResp.json() : { items: [] }).items || [];
    const allTypes = (typesResp.ok ? await typesResp.json() : { items: [] }).items || [];

    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:10000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
    modal.innerHTML = `<div class="premium-card" style="width:750px;max-width:94vw;max-height:92vh;overflow-y:auto;padding:28px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
            <h3 style="font-size:1.15rem;font-weight:700;"><i data-lucide="layers" style="width:20px;vertical-align:middle;margin-right:8px;"></i> ${editId ? 'Edit' : 'Create'} Template</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.4rem;padding:4px;">&times;</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px;">
            <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Template Name *</label>
                <input type="text" id="tmpl-name" required value="${templateData ? templateData.name : ''}" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;"></div>
            <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Vehicle Category</label>
                <select id="tmpl-category" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
                    <option value="">Select category...</option>
                    ${['Car','Van','Pickup','Truck','Heavy Truck','Tanker','Bus','Motorcycle','Trailer','Generator','Heavy Equipment'].map(c =>
                        `<option value="${c}" ${templateData && (templateData.vehicle_category === c || templateData.vehicle_type === c) ? 'selected' : ''}>${c}</option>`
                    ).join('')}
                </select>
            </div>
            <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Est. Service Cost</label>
                <input type="number" id="tmpl-cost" value="${templateData && templateData.estimated_service_cost != null ? templateData.estimated_service_cost : ''}" step="100" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;"></div>
            <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Est. Annual Maint.</label>
                <input type="number" id="tmpl-annual" value="${templateData && templateData.estimated_annual_maint != null ? templateData.estimated_annual_maint : ''}" step="100" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;"></div>
            <div style="grid-column:1/-1;"><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Description</label>
                <textarea id="tmpl-description" rows="2" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;resize:vertical;">${templateData ? (templateData.description || '') : ''}</textarea>
            </div>
        </div>

        <div style="border:1px solid var(--border-light);border-radius:10px;padding:16px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <h4 style="font-size:0.9rem;font-weight:700;"><i data-lucide="list" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Maintenance Rules</h4>
                <div style="display:flex;gap:6px;">
                    <select id="tmpl-add-rule-select" style="padding:8px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.8rem;min-width:180px;">
                        <option value="">Select a rule to add...</option>
                        ${allRules.map(r => `<option value="${r.id}" data-type-name="${r.type_name || ''}">${r.name}${r.type_name ? ' (' + r.type_name + ')' : ''}</option>`).join('')}
                    </select>
                    <button type="button" class="glass-btn primary" onclick="addRuleToTemplateBuilder()" style="padding:8px 14px;font-size:0.8rem;">+ Add</button>
                </div>
            </div>
            <div id="tmpl-rules-list">
                ${_templateRules.length ? _templateRules.map((r, i) => renderTemplateRuleRow(r, i)).join('') :
                    '<div style="padding:20px;text-align:center;color:var(--text-dim);font-size:0.85rem;">No rules added yet. Select a rule above and click Add.</div>'}
            </div>
        </div>

        <div style="display:flex;gap:10px;justify-content:flex-end;">
            <button type="button" onclick="this.closest('.modal-overlay').remove()" style="padding:12px 24px;border-radius:8px;border:1px solid var(--border-light);background:transparent;color:var(--text-secondary);cursor:pointer;font-weight:600;font-size:0.85rem;">Cancel</button>
            <button type="button" id="tmpl-save-btn" class="glass-btn primary" onclick="saveTemplate()" style="padding:12px 24px;font-size:0.85rem;"><i data-lucide="save" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Save Template</button>
        </div>
    </div>`;
    document.body.appendChild(modal);
    lucide.createIcons({ el: modal });
}

function renderTemplateRuleRow(r, idx) {
    const ruleData = r.rule || r;
    return `<div class="tmpl-rule-row" data-index="${idx}" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--border-light);border-radius:8px;margin-bottom:6px;background:var(--fleet-bg);">
        <span style="color:var(--text-dim);font-size:0.75rem;min-width:24px;">#${idx + 1}</span>
        <div style="flex:1;min-width:0;">
            <div style="font-weight:600;font-size:0.82rem;">${ruleData.name || 'Rule #' + r.rule_id}</div>
            <div style="font-size:0.72rem;color:var(--text-dim);">
                ${ruleData.trigger_km ? ruleData.trigger_km.toLocaleString() + ' km' : ''}
                ${ruleData.trigger_km && ruleData.trigger_days ? ' | ' : ''}
                ${ruleData.trigger_days ? ruleData.trigger_days + ' days' : ''}
                ${(ruleData.trigger_km || ruleData.trigger_days) && ruleData.trigger_hours ? ' | ' : ''}
                ${ruleData.trigger_hours ? ruleData.trigger_hours + ' hrs' : ''}
                ${ruleData.type_name ? ' · ' + ruleData.type_name : ''}
            </div>
        </div>
        <input type="number" class="tmpl-override-km" placeholder="Override KM" value="${r.override_km != null ? r.override_km : ''}" step="100" style="width:100px;padding:6px;border-radius:6px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.75rem;">
        <input type="number" class="tmpl-override-days" placeholder="Override Days" value="${r.override_days != null ? r.override_days : ''}" style="width:80px;padding:6px;border-radius:6px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.75rem;">
        <label style="display:flex;align-items:center;gap:4px;font-size:0.7rem;white-space:nowrap;"><input type="checkbox" class="tmpl-rule-enabled" ${r.is_enabled !== false ? 'checked' : ''}> Active</label>
        <button type="button" onclick="moveRuleInBuilder(${idx}, -1)" class="glass-btn secondary" style="padding:4px 6px;font-size:0.65rem;" title="Move Up">▲</button>
        <button type="button" onclick="moveRuleInBuilder(${idx}, 1)" class="glass-btn secondary" style="padding:4px 6px;font-size:0.65rem;" title="Move Down">▼</button>
        <button type="button" onclick="removeRuleFromBuilder(${idx})" class="glass-btn danger" style="padding:4px 8px;font-size:0.7rem;">✕</button>
        <input type="hidden" class="tmpl-rule-id" value="${r.rule_id || r.rule?.id}">
        <input type="hidden" class="tmpl-type-id" value="${ruleData.type_id || r.type_id || ''}">
    </div>`;
}

function addRuleToTemplateBuilder() {
    const sel = document.getElementById('tmpl-add-rule-select');
    if (!sel || !sel.value) { showNotification('Select a rule first', 'fault'); return; }
    const ruleId = parseInt(sel.value);
    const option = sel.options[sel.selectedIndex];
    if (_templateRules.some(r => (r.rule_id || r.rule?.id) === ruleId)) { showNotification('Rule already added', 'fault'); return; }
    // Fetch full rule data from the select option attributes
    const ruleName = option.text.split(' (')[0];
    _templateRules.push({ uid: Date.now() + Math.random(), rule_id: ruleId, rule: { id: ruleId, name: ruleName }, is_enabled: true, override_km: null, override_days: null, override_hours: null });
    renderTemplateRulesList();
    sel.value = '';
}

function moveRuleInBuilder(idx, dir) {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= _templateRules.length) return;
    [_templateRules[idx], _templateRules[newIdx]] = [_templateRules[newIdx], _templateRules[idx]];
    renderTemplateRulesList();
}

function removeRuleFromBuilder(idx) {
    _templateRules.splice(idx, 1);
    renderTemplateRulesList();
}

function renderTemplateRulesList() {
    const container = document.getElementById('tmpl-rules-list');
    if (!container) return;
    if (!_templateRules.length) {
        container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-dim);font-size:0.85rem;">No rules added yet.</div>';
        return;
    }
    container.innerHTML = _templateRules.map((r, i) => renderTemplateRuleRow(r, i)).join('');
    lucide.createIcons({ el: container });
}

async function saveTemplate() {
    const btn = document.getElementById('tmpl-save-btn');
    btn.disabled = true; btn.innerHTML = 'Saving...';

    // Read override values from DOM
    const rows = document.querySelectorAll('.tmpl-rule-row');
    rows.forEach((row, idx) => {
        if (_templateRules[idx]) {
            _templateRules[idx].override_km = parseFloat(row.querySelector('.tmpl-override-km')?.value) || null;
            _templateRules[idx].override_days = parseInt(row.querySelector('.tmpl-override-days')?.value) || null;
            _templateRules[idx].is_enabled = row.querySelector('.tmpl-rule-enabled')?.checked ?? true;
        }
    });

    const payload = {
        name: document.getElementById('tmpl-name').value.trim(),
        vehicle_category: document.getElementById('tmpl-category').value || null,
        description: document.getElementById('tmpl-description').value.trim() || null,
        estimated_service_cost: parseFloat(document.getElementById('tmpl-cost').value) || null,
        estimated_annual_maint: parseFloat(document.getElementById('tmpl-annual').value) || null,
        is_active: true
    };
    if (!payload.name) { showNotification('Template name is required', 'fault'); btn.disabled = false; btn.innerHTML = '<i data-lucide="save" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Save Template'; lucide.createIcons(); return; }
    if (!_templateRules.length) { showNotification('Add at least one rule', 'fault'); btn.disabled = false; btn.innerHTML = '<i data-lucide="save" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Save Template'; lucide.createIcons(); return; }

    try {
        let templateId = _templateEditId;
        if (templateId) {
            const resp = await fetch(`/api/maintenance/planner/templates/${templateId}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                body: JSON.stringify(payload)
            });
            if (!resp.ok) { const e = await resp.json(); showNotification(e.detail || 'Failed to update', 'fault'); btn.disabled = false; btn.innerHTML = '<i data-lucide="save" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Save Template'; lucide.createIcons(); return; }
        } else {
            const resp = await fetch('/api/maintenance/planner/templates', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                body: JSON.stringify(payload)
            });
            if (!resp.ok) { const e = await resp.json(); showNotification(e.detail || 'Failed to create', 'fault'); btn.disabled = false; btn.innerHTML = '<i data-lucide="save" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Save Template'; lucide.createIcons(); return; }
            const result = await resp.json();
            templateId = result.id;
        }

        // Sync rules: remove old, add new
        if (_templateEditId) {
            const oldResp = await fetch(`/api/maintenance/planner/templates/${_templateEditId}/rules`, { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (oldResp.ok) {
                const oldRules = await oldResp.json();
                for (const or of oldRules) {
                    await fetch(`/api/maintenance/planner/templates/${_templateEditId}/rules/${or.rule_id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` } });
                }
            }
        }

        for (let i = 0; i < _templateRules.length; i++) {
            const r = _templateRules[i];
            const ruleId = r.rule_id || r.rule?.id;
            if (!ruleId) continue;
            await fetch(`/api/maintenance/planner/templates/${templateId}/rules`, {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                body: JSON.stringify({
                    rule_id: ruleId, execution_order: i,
                    override_km: r.override_km, override_days: r.override_days,
                    override_hours: r.override_hours, override_priority: r.override_priority,
                    is_enabled: r.is_enabled !== false
                })
            });
        }

        document.querySelector('.modal-overlay.active')?.remove();
        await switchPlannerTab('templates');
        await refreshMaintDashboardCache();
        showNotification(`Template ${_templateEditId ? 'updated' : 'created'} with ${_templateRules.length} rules`, 'scheduled');
    } catch(e) { showNotification('Error saving template', 'fault'); btn.disabled = false; btn.innerHTML = '<i data-lucide="save" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Save Template'; lucide.createIcons(); }
}

async function editTemplate(id) { await openTemplateModal(id); }

// ==================== TEMPLATE DETAIL / PREVIEW ====================

async function viewTemplateRules(templateId) {
    try {
        const resp = await fetch(`/api/maintenance/planner/templates/${templateId}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!resp.ok) { showNotification('Failed to load template', 'fault'); return; }
        const t = await resp.json();

        const modal = document.createElement('div');
        modal.className = 'modal-overlay active';
        modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:10000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
        modal.innerHTML = `<div class="premium-card" style="width:780px;max-width:94vw;max-height:92vh;overflow-y:auto;padding:28px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <div>
                    <h3 style="font-size:1.2rem;font-weight:700;"><i data-lucide="layers" style="width:20px;vertical-align:middle;margin-right:8px;"></i> ${t.name}</h3>
                    ${t.description ? `<p style="font-size:0.82rem;color:var(--text-dim);margin-top:4px;">${t.description}</p>` : ''}
                </div>
                <button onclick="this.closest('.modal-overlay').remove()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.4rem;padding:4px;">&times;</button>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;">
                <div class="premium-card mini-stat"><span class="card-label">Category</span><span class="card-value" style="font-size:0.85rem;">${t.vehicle_category || t.vehicle_type || '—'}</span></div>
                <div class="premium-card mini-stat"><span class="card-label">Rules</span><span class="card-value">${(t.rules || []).length}</span></div>
                <div class="premium-card mini-stat"><span class="card-label">Vehicles</span><span class="card-value">${t.vehicle_count || 0}</span></div>
                <div class="premium-card mini-stat"><span class="card-label">Status</span><span class="card-value" style="font-size:0.85rem;">${t.is_active ? 'Active' : t.is_archived ? 'Archived' : 'Inactive'}</span></div>
            </div>
            <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
                <button class="glass-btn secondary" onclick="editTemplate(${t.id})" style="padding:6px 14px;font-size:0.8rem;"><i data-lucide="edit" style="width:14px;margin-right:4px;"></i> Edit</button>
                ${!t.is_system ? `<button class="glass-btn secondary" onclick="duplicateTemplateAction(${t.id})" style="padding:6px 14px;font-size:0.8rem;"><i data-lucide="copy" style="width:14px;margin-right:4px;"></i> Duplicate</button>` : ''}
                ${t.is_active ? `<button class="glass-btn warning" onclick="deactivateTemplateAction(${t.id})" style="padding:6px 14px;font-size:0.8rem;"><i data-lucide="pause-circle" style="width:14px;margin-right:4px;"></i> Deactivate</button>` :
                    `<button class="glass-btn secondary" onclick="activateTemplateAction(${t.id})" style="padding:6px 14px;font-size:0.8rem;"><i data-lucide="play" style="width:14px;margin-right:4px;"></i> Activate</button>`}
            </div>`;

        const rules = t.rules || [];
        if (rules.length) {
            modal.innerHTML += `<h4 style="font-size:0.9rem;font-weight:700;margin-bottom:12px;">Assigned Rules (${rules.length})</h4>
            <table class="modern-table" style="width:100%;"><thead><tr>
                <th>#</th><th>Rule</th><th>Type</th><th>Trigger KM</th><th>Trigger Days</th><th>Trigger Hrs</th><th>Priority</th><th>Status</th>
            </tr></thead><tbody>${rules.map((r, i) => {
                const rd = r.rule || {};
                return `<tr>
                    <td>${i + 1}</td>
                    <td>${rd.name || 'Rule #' + r.rule_id}</td>
                    <td>${rd.type_name || '—'}</td>
                    <td>${r.override_km != null ? r.override_km.toLocaleString() : rd.trigger_km != null ? rd.trigger_km.toLocaleString() : '—'}</td>
                    <td>${r.override_days != null ? r.override_days : rd.trigger_days != null ? rd.trigger_days : '—'}</td>
                    <td>${r.override_hours != null ? r.override_hours : rd.trigger_hours != null ? rd.trigger_hours : '—'}</td>
                    <td><span class="stats-badge ${r.override_priority === 'critical' ? 'danger' : r.override_priority === 'high' ? 'warning' : 'primary'}">${r.override_priority || rd.priority || 'medium'}</span></td>
                    <td><span class="stats-badge ${r.is_enabled !== false ? 'success' : 'warning'}">${r.is_enabled !== false ? 'Enabled' : 'Disabled'}</span></td>
                </tr>`;
            }).join('')}</tbody></table>`;
        } else {
            modal.innerHTML += '<div class="premium-card" style="padding:20px;text-align:center;color:var(--text-dim);">No rules assigned to this template.</div>';
        }

        if (t.vehicles && t.vehicles.length) {
            modal.innerHTML += `<h4 style="font-size:0.9rem;font-weight:700;margin:16px 0 12px;">Vehicles Using This Template (${t.vehicles.length})</h4>
            <table class="modern-table" style="width:100%;"><thead><tr><th>Plan Name</th><th>Device ID</th><th>Status</th></tr></thead><tbody>
                ${t.vehicles.map(v => `<tr><td>${v.name || 'Plan #' + v.id}</td><td>${v.device_id}</td><td><span class="stats-badge ${v.is_active ? 'success' : 'warning'}">${v.is_active ? 'Active' : 'Inactive'}</span></td></tr>`).join('')}
            </tbody></table>`;
        }

        modal.innerHTML += `</div>`;
        document.body.appendChild(modal);
        lucide.createIcons({ el: modal });
    } catch(e) { showNotification('Error loading template', 'fault'); }
}

// ==================== TEMPLATE ACTIONS ====================

async function deleteTemplate(id) {
    if (!confirm('Delete this template permanently?')) return;
    try {
        const resp = await fetch(`/api/maintenance/planner/templates/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) { await switchPlannerTab('templates'); await refreshMaintDashboardCache(); showNotification('Template deleted', 'scheduled'); }
        else { const e = await resp.json(); showNotification(e.detail || 'Failed to delete', 'fault'); }
    } catch(e) { showNotification('Error deleting template', 'fault'); }
}

async function duplicateTemplateAction(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/templates/${id}/duplicate`, { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) { await switchPlannerTab('templates'); showNotification('Template duplicated', 'scheduled'); }
        else { const e = await resp.json(); showNotification(e.detail || 'Failed to duplicate', 'fault'); }
    } catch(e) { showNotification('Error duplicating template', 'fault'); }
}

async function activateTemplateAction(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/templates/${id}/activate`, { method: 'PATCH', headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) { await switchPlannerTab('templates'); showNotification('Template activated', 'scheduled'); }
        else { const e = await resp.json(); showNotification(e.detail || 'Failed', 'fault'); }
    } catch(e) { showNotification('Error', 'fault'); }
}

async function deactivateTemplateAction(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/templates/${id}/deactivate`, { method: 'PATCH', headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) { await switchPlannerTab('templates'); showNotification('Template deactivated', 'scheduled'); }
        else { const e = await resp.json(); showNotification(e.detail || 'Failed', 'fault'); }
    } catch(e) { showNotification('Error', 'fault'); }
}

let _planSearchState = { search: '', status: 'all', health: 'all', category: 'all', page: 1, sortField: 'name', sortOrder: 'asc', selectedPlanId: null };

async function renderPlansTable() {
    const container = document.getElementById('planner-tab-content');
    if (container) container.innerHTML = '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Loading vehicles...</div>';

    const params = new URLSearchParams({
        page: _planSearchState.page, page_size: 50,
        search: _planSearchState.search || '',
        status: _planSearchState.status,
        health: _planSearchState.health,
        category: _planSearchState.category
    });
    const resp = await fetch(`/api/maintenance/planner/vehicles-plans?${params}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
    if (!resp.ok) return '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Failed to load vehicle plans.</div>';
    const data = await resp.json();
    const items = data.items || [];
    const categories = data.categories || [];

    let html = `<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <input type="text" id="plan-search-input" placeholder="Search vehicle..." value="${_planSearchState.search}" oninput="debouncedPlanSearch()" style="padding:8px 12px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.82rem; width:200px;">
            <select id="plan-status-filter" onchange="switchPlanFilter()" style="padding:8px 12px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.82rem;">
                <option value="all" ${_planSearchState.status === 'all' ? 'selected' : ''}>All Plans</option>
                <option value="active" ${_planSearchState.status === 'active' ? 'selected' : ''}>Active</option>
                <option value="inactive" ${_planSearchState.status === 'inactive' ? 'selected' : ''}>Inactive</option>
                <option value="no plan" ${_planSearchState.status === 'no plan' ? 'selected' : ''}>No Plan</option>
            </select>
            <select id="plan-health-filter" onchange="switchPlanFilter()" style="padding:8px 12px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.82rem;">
                <option value="all" ${_planSearchState.health === 'all' ? 'selected' : ''}>All Health</option>
                <option value="healthy" ${_planSearchState.health === 'healthy' ? 'selected' : ''}>Healthy</option>
                <option value="due_soon" ${_planSearchState.health === 'due_soon' ? 'selected' : ''}>Due Soon</option>
                <option value="overdue" ${_planSearchState.health === 'overdue' ? 'selected' : ''}>Overdue</option>
            </select>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
            <span id="bulk-select-count" style="font-size:0.82rem;color:var(--text-dim);"></span>
            <button id="bulk-assign-btn" class="glass-btn primary" onclick="openBulkAssignModal()" style="padding:8px 16px;font-size:0.8rem;display:none;"><i data-lucide="layers" style="width:14px;margin-right:4px;"></i> Bulk Assign</button>
            <span style="font-size:0.85rem; color:var(--text-dim);">${data.total} vehicles</span>
        </div>
    </div>`;

    if (!items.length) {
        html += '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No vehicles found matching your criteria.</div>';
        return html;
    }

    html += `<table class="modern-table" style="width:100%;"><thead><tr>
        <th style="width:36px;"><input type="checkbox" onchange="toggleSelectAll()" style="cursor:pointer;"></th>
        <th onclick="sortPlanTable('name')" style="cursor:pointer;">Vehicle ${_planSearchState.sortField === 'name' ? (_planSearchState.sortOrder === 'asc' ? '▲' : '▼') : ''}</th>
        <th>Device ID</th>
        <th onclick="sortPlanTable('category')" style="cursor:pointer;">Category ${_planSearchState.sortField === 'category' ? (_planSearchState.sortOrder === 'asc' ? '▲' : '▼') : ''}</th>
        <th>Odometer</th>
        <th>Template</th>
        <th>Plan Status</th>
        <th onclick="sortPlanTable('health_status')" style="cursor:pointer;">Health ${_planSearchState.sortField === 'health_status' ? (_planSearchState.sortOrder === 'asc' ? '▲' : '▼') : ''}</th>
        <th>Next Service</th>
        <th>Actions</th>
    </tr></thead><tbody>`;

    items.forEach(v => {
        const healthColor = v.health_status === 'overdue' ? '#ef4444' : v.health_status === 'due_soon' ? '#f59e0b' : '#10b981';
        const odometerDisplay = v.current_km != null ? v.current_km.toLocaleString() + ' km' : '<span style="color:var(--text-dim);">No Data</span>';
        const nextDisplay = v.next_service_km != null ? v.next_service_km.toLocaleString() + ' km' : v.next_service_days != null ? v.next_service_days + ' days' : '<span style="color:var(--text-dim);">—</span>';
        const planBadge = v.plan_status === 'Active' ? '<span class="stats-badge success">Active</span>' : v.plan_status === 'Inactive' ? '<span class="stats-badge warning">Inactive</span>' : '<span class="stats-badge primary">No Plan</span>';
        const actions = v.plan_id ? `
            <button class="glass-btn secondary" onclick="openVehicleDetail(${v.id})" style="padding:4px 8px; font-size:0.7rem;">Detail</button>
            <button class="glass-btn secondary" onclick="viewPlanOverrides(${v.plan_id})" style="padding:4px 8px; font-size:0.7rem;">Overrides</button>
            ${v.template_name ? `<button class="glass-btn secondary" onclick="openPlanModal(${v.id})" style="padding:4px 8px; font-size:0.7rem;">Replace</button>` : ''}
            ${v.template_name ? `<button class="glass-btn danger" onclick="unassignTemplate(${v.plan_id})" style="padding:4px 8px; font-size:0.7rem;">Unassign</button>` : ''}
            ${v.plan_is_active ? `<button class="glass-btn danger" onclick="deletePlan(${v.plan_id})" style="padding:4px 8px; font-size:0.7rem;">Del</button>` : ''}
        ` : `<button class="glass-btn primary" onclick="openPlanModal(${v.id})" style="padding:4px 8px; font-size:0.7rem;">Assign</button>`;

        html += `<tr>
            <td><input type="checkbox" class="plan-bulk-check" data-device-id="${v.id}" onchange="toggleBulkSelect(${v.id})" style="cursor:pointer;"></td>
            <td><strong style="cursor:pointer;color:var(--brand-primary);" onclick="openVehicleDetail(${v.id})">${v.name || 'Unknown'}</strong></td>
            <td style="font-size:0.75rem;color:var(--text-dim);">${v.uniqueId || v.id}</td>
            <td>${v.category || '—'}</td>
            <td>${odometerDisplay}</td>
            <td>${v.template_name || '<span style="color:var(--text-dim);">Not Assigned</span>'}</td>
            <td>${planBadge}</td>
            <td><span style="color:${healthColor};font-weight:600;">${v.health_status === 'overdue' ? 'Overdue' : v.health_status === 'due_soon' ? 'Due Soon' : 'Healthy'}</span></td>
            <td>${nextDisplay}</td>
            <td><div style="display:flex;gap:4px;">${actions}</div></td>
        </tr>`;
    });

    html += '</tbody></table>';

    if (data.total_pages > 1) {
        html += `<div style="display:flex;justify-content:center;gap:8px;margin-top:16px;">
            ${Array.from({length: data.total_pages}, (_, i) => i + 1).map(p =>
                `<button class="glass-btn ${p === _planSearchState.page ? 'primary' : ''}" onclick="gotoPlanPage(${p})" style="padding:6px 14px;font-size:0.8rem;">${p}</button>`
            ).join('')}
        </div>`;
    }
    return html;
}

function switchPlanFilter() {
    _planSearchState.status = document.getElementById('plan-status-filter')?.value || 'all';
    _planSearchState.health = document.getElementById('plan-health-filter')?.value || 'all';
    _planSearchState.page = 1;
    switchPlannerTab('plans');
}

let _planDebounceTimer = null;
function debouncedPlanSearch() {
    clearTimeout(_planDebounceTimer);
    _planDebounceTimer = setTimeout(() => {
        _planSearchState.search = document.getElementById('plan-search-input')?.value || '';
        _planSearchState.page = 1;
        switchPlannerTab('plans');
    }, 400);
}

function sortPlanTable(field) {
    if (_planSearchState.sortField === field) {
        _planSearchState.sortOrder = _planSearchState.sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        _planSearchState.sortField = field;
        _planSearchState.sortOrder = 'asc';
    }
    switchPlannerTab('plans');
}

function gotoPlanPage(p) {
    _planSearchState.page = p;
    switchPlannerTab('plans');
}

// ==================== VEHICLE DETAIL MODAL ====================

async function openVehicleDetail(deviceId) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px);';
    modal.innerHTML = `<div class="premium-card" style="width:720px; max-width:92vw; max-height:90vh; overflow-y:auto; padding:32px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
            <h3 style="font-size:1.2rem;font-weight:700;"><i data-lucide="truck" style="width:20px;vertical-align:middle;margin-right:8px;"></i> Loading...</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.4rem;padding:4px;">&times;</button>
        </div>
        <div id="vehicle-detail-content" style="text-align:center;padding:20px;color:var(--text-dim);">Loading vehicle data...</div>
    </div>`;
    document.body.appendChild(modal);
    lucide.createIcons({ el: modal });

    try {
        const [vpResp, calcResp] = await Promise.all([
            fetch(`/api/maintenance/planner/vehicles-plans?page_size=1&search=${deviceId}`, { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch(`/api/maintenance/planner/due-calculation/${deviceId}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        ]);
        const vpData = vpResp.ok ? await vpResp.json() : { items: [] };
        const vehicle = (vpData.items || []).find(v => v.id === deviceId);
        const calc = calcResp.ok ? await calcResp.json() : { items: [], current_km: 0, summary: {} };

        let logResp, lastLogs = [];
        try {
            logResp = await fetch(`/api/maintenance/log?device_id=${deviceId}&page_size=5`, { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (logResp.ok) { const ld = await logResp.json(); lastLogs = ld.items || ld; }
        } catch(e) {}

        const summary = calc.summary || {};
        let content = '';
        if (vehicle) {
            const odometer = vehicle.current_km != null ? vehicle.current_km.toLocaleString() + ' km' : 'No Odometer Data';
            const healthColor = vehicle.health_status === 'overdue' ? '#ef4444' : vehicle.health_status === 'due_soon' ? '#f59e0b' : '#10b981';
            content = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
                <div class="premium-card" style="padding:16px;">
                    <h4 style="font-size:0.9rem;font-weight:700;margin-bottom:12px;"><i data-lucide="info" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Vehicle Info</h4>
                    <div style="font-size:0.82rem;display:grid;gap:6px;">
                        <div><strong>Name:</strong> ${vehicle.name}</div>
                        <div><strong>Device ID:</strong> ${vehicle.uniqueId || vehicle.id}</div>
                        <div><strong>Category:</strong> ${vehicle.category || '—'}</div>
                        <div><strong>Model:</strong> ${vehicle.model || '—'}</div>
                        <div><strong>Phone:</strong> ${vehicle.phone || '—'}</div>
                        <div><strong>Status:</strong> <span class="stats-badge ${vehicle.status === 'online' ? 'success' : 'warning'}">${vehicle.status || 'offline'}</span></div>
                    </div>
                </div>
                <div class="premium-card" style="padding:16px;">
                    <h4 style="font-size:0.9rem;font-weight:700;margin-bottom:12px;"><i data-lucide="activity" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Plan Status</h4>
                    <div style="font-size:0.82rem;display:grid;gap:6px;">
                        <div><strong>Plan:</strong> ${vehicle.plan_name || 'No Plan'}</div>
                        <div><strong>Template:</strong> ${vehicle.template_name || 'Not Assigned'}</div>
                        ${vehicle.plan_created_at ? '<div><strong>Assigned:</strong> ' + vehicle.plan_created_at.split('T')[0] + '</div>' : ''}
                        ${vehicle.template_updated_at ? '<div><strong>Template Version:</strong> ' + vehicle.template_updated_at.split('T')[0] + '</div>' : ''}
                        <div><strong>Status:</strong> ${vehicle.plan_status === 'Active' ? '<span class="stats-badge success">Active</span>' : '<span class="stats-badge warning">Inactive</span>'}</div>
                        <div><strong>Health:</strong> <span style="color:${healthColor};font-weight:600;">${vehicle.health_status === 'overdue' ? 'Overdue' : vehicle.health_status === 'due_soon' ? 'Due Soon' : 'Healthy'}</span></div>
                        <div><strong>Odometer:</strong> ${odometer}</div>
                    </div>
                    ${vehicle.plan_id ? '<div style="margin-top:12px;display:flex;gap:6px;">' +
                        '<button class="glass-btn secondary" onclick="this.closest(\'.modal-overlay\').remove();openPlanModal(' + deviceId + ')" style="padding:6px 12px;font-size:0.75rem;">Replace</button>' +
                        '<button class="glass-btn danger" onclick="this.closest(\'.modal-overlay\').remove();unassignTemplate(' + vehicle.plan_id + ')" style="padding:6px 12px;font-size:0.75rem;">Unassign</button>' +
                    '</div>' : ''}
                </div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;">
                <div class="premium-card mini-stat"><span class="card-label">Total Rules</span><span class="card-value">${summary.total || 0}</span></div>
                <div class="premium-card mini-stat"><span class="card-label">Healthy</span><span class="card-value" style="color:#10b981;">${summary.healthy || 0}</span></div>
                <div class="premium-card mini-stat"><span class="card-label">Due Soon</span><span class="card-value" style="color:#f59e0b;">${summary.due_soon || 0}</span></div>
                <div class="premium-card mini-stat"><span class="card-label">Overdue</span><span class="card-value" style="color:#ef4444;">${summary.overdue || 0}</span></div>
            </div>`;
        } else {
            content = `<div class="premium-card" style="padding:20px;text-align:center;color:var(--text-dim);">Vehicle data not available.</div>`;
        }

        if (calc.items && calc.items.length > 0) {
            content += `<h4 style="font-size:0.9rem;font-weight:700;margin-bottom:12px;"><i data-lucide="clipboard-list" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Assigned Rules</h4>
            <table class="modern-table" style="width:100%;margin-bottom:20px;"><thead><tr>
                <th>Type</th><th>Rule</th><th>Interval KM</th><th>Interval Days</th><th>KM Left</th><th>Days Left</th><th>Status</th>
            </tr></thead><tbody>${calc.items.map(r => {
                const st = r.overall_status;
                const stColor = st === 'overdue' ? '#ef4444' : st === 'due_soon' ? '#f59e0b' : '#10b981';
                return `<tr><td>${r.type_name || '—'}</td><td>${r.rule_name || '—'}</td>
                    <td>${r.km_interval != null ? r.km_interval.toLocaleString() : '—'}</td>
                    <td>${r.days_interval || '—'}</td>
                    <td>${r.km_remaining != null ? r.km_remaining.toLocaleString() : '—'}</td>
                    <td>${r.days_remaining != null ? r.days_remaining : '—'}</td>
                    <td><span style="color:${stColor};font-weight:600;">${st}</span></td></tr>`;
            }).join('')}</tbody></table>`;
        }

        if (lastLogs.length > 0) {
            content += `<h4 style="font-size:0.9rem;font-weight:700;margin-bottom:12px;"><i data-lucide="history" style="width:16px;vertical-align:middle;margin-right:6px;"></i> Last Services</h4>
            <table class="modern-table" style="width:100%;"><thead><tr><th>Date</th><th>Type</th><th>KM</th><th>Workshop</th><th>Cost</th><th>Technician</th></tr></thead><tbody>
            ${lastLogs.map(l => `<tr><td>${l.service_date ? l.service_date.split('T')[0] : '—'}</td>
                <td>${l.service_type || '—'}</td>
                <td>${l.service_value ? l.service_value.toLocaleString() : '—'}</td>
                <td>${l.workshop_name || '—'}</td>
                <td>${l.cost ? l.cost.toLocaleString() : '—'}</td>
                <td>${l.technician || '—'}</td></tr>`).join('')}</tbody></table>`;
        }

        const detailContent = modal.querySelector('#vehicle-detail-content');
        if (detailContent) {
            detailContent.innerHTML = content;
            lucide.createIcons({ el: detailContent });
        }
        const titleEl = modal.querySelector('h3');
        if (titleEl) titleEl.innerHTML = `<i data-lucide="truck" style="width:20px;vertical-align:middle;margin-right:8px;"></i> ${vehicle ? vehicle.name : 'Vehicle Detail'}`;
        lucide.createIcons({ el: modal });
    } catch(e) {
        const detailContent = modal.querySelector('#vehicle-detail-content');
        if (detailContent) detailContent.innerHTML = '<div style="color:var(--text-dim);">Failed to load vehicle data.</div>';
    }
}

// ==================== ASSIGN TEMPLATE MODAL ====================

let _planEditVehicleId = null;

async function openPlanModal(deviceId) {
    _planEditVehicleId = deviceId || null;
    const isEdit = !!_planEditVehicleId;

    const [vehiclesResp, templatesResp, plansResp] = await Promise.all([
        fetch('/api/v1/vehicles/live', { headers: { 'Authorization': `Bearer ${authToken}` } }),
        fetch('/api/maintenance/planner/templates?page_size=200&active_only=true', { headers: { 'Authorization': `Bearer ${authToken}` } }),
        fetch(`/api/maintenance/planner/plans?device_id=${deviceId || 0}&active_only=true`, { headers: { 'Authorization': `Bearer ${authToken}` } })
    ]);
    const vehicles = vehiclesResp.ok ? await vehiclesResp.json() : [];
    const tmplData = templatesResp.ok ? await templatesResp.json() : { items: [] };
    const templates = tmplData.items || [];
    const plansData = plansResp.ok ? await plansResp.json() : { items: [] };
    const existingPlan = (plansData.items || []).find(p => p.device_id === deviceId && p.template_id);
    const isReplace = !!existingPlan;

    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px);';
    modal.innerHTML = `<div class="premium-card" style="width:520px; max-width:90vw; padding:32px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
            <h3 style="font-size:1.1rem;font-weight:700;">${isReplace ? 'Replace Template' : isEdit ? 'Assign Template' : 'Create Plan'}</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.3rem;padding:4px;">&times;</button>
        </div>
        ${isReplace ? '<div style="background:#f59e0b15;border:1px solid #f59e0b40;border-radius:8px;padding:12px;margin-bottom:16px;font-size:0.82rem;color:#f59e0b;">This vehicle already has template <strong>' + (existingPlan.template_name || '') + '</strong>. Selecting a new template will replace it.</div>' : ''}
        <form id="plan-form" style="display:flex;flex-direction:column;gap:12px;">
            <label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Vehicle</label>
            <select id="plan-device-id" required style="padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
                <option value="">Select Vehicle...</option>
                ${vehicles.map(v => `<option value="${v.id}" ${v.id === deviceId ? 'selected' : ''}>${v.name || 'Vehicle ' + v.id} (${v.uniqueId || v.id})</option>`).join('')}
            </select>
            <label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Template</label>
            <select id="plan-template-id" required style="padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
                <option value="">Select Template...</option>
                ${templates.map(t => `<option value="${t.id}" ${existingPlan && existingPlan.template_id === t.id ? 'selected' : ''}>${t.name} (${t.vehicle_category || t.vehicle_type || 'General'}) — ${t.rule_count || 0} rules</option>`).join('')}
            </select>
            <label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Plan Name</label>
            <input type="text" id="plan-name" placeholder="e.g., Standard Maintenance Plan" required value="${isReplace ? existingPlan.name : ''}" style="padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
            <label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Description (optional)</label>
            <textarea id="plan-description" rows="2" style="padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;resize:vertical;"></textarea>
            <label style="display:flex;align-items:center;gap:8px;font-size:0.85rem;"><input type="checkbox" id="plan-is-active" checked> Active</label>
            <div style="display:flex;gap:10px;margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1;padding:12px;border-radius:8px;border:1px solid var(--border-light);background:transparent;color:var(--text-secondary);cursor:pointer;font-weight:600;font-size:0.85rem;">Cancel</button>
                <button type="submit" style="flex:1;padding:12px;border-radius:8px;border:none;background:var(--brand-primary);color:#fff;cursor:pointer;font-weight:600;font-size:0.85rem;">${isReplace ? 'Replace Template' : isEdit ? 'Assign Template' : 'Create Plan'}</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
    lucide.createIcons({ el: modal });

    const form = document.getElementById('plan-form');
    form.onsubmit = async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true; btn.textContent = 'Saving...';
        const payload = {
            device_id: parseInt(document.getElementById('plan-device-id').value),
            name: document.getElementById('plan-name').value.trim(),
            description: document.getElementById('plan-description').value.trim() || null,
            is_active: document.getElementById('plan-is-active').checked,
            template_id: parseInt(document.getElementById('plan-template-id').value) || null
        };
        if (!payload.device_id) { showNotification('Select a vehicle', 'fault'); btn.disabled = false; btn.textContent = 'Save'; return; }
        if (!payload.template_id) { showNotification('Select a template', 'fault'); btn.disabled = false; btn.textContent = 'Save'; return; }
        try {
            let resp;
            const alreadyHas = existingPlan && existingPlan.template_id;
            if (alreadyHas) {
                resp = await fetch('/api/maintenance/planner/plans/replace-template', {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ device_id: payload.device_id, template_id: payload.template_id })
                });
            } else if (payload.template_id) {
                resp = await fetch('/api/maintenance/planner/plans/assign-template', {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ device_id: payload.device_id, template_id: payload.template_id })
                });
            } else {
                resp = await fetch('/api/maintenance/planner/plans', {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify(payload)
                });
            }
            if (resp.ok) {
                modal.remove();
                await switchPlannerTab('plans');
                await refreshMaintDashboardCache();
                showNotification(alreadyHas ? 'Template replaced' : 'Template assigned', 'scheduled');
            } else {
                const err = await resp.json();
                showNotification(err.detail || 'Failed to save plan', 'fault');
                btn.disabled = false; btn.textContent = 'Save';
            }
        } catch(err) { showNotification('Error saving plan', 'fault'); btn.disabled = false; btn.textContent = 'Save'; }
    };
}

let _bulkSelectedIds = [];

function toggleBulkSelect(deviceId) {
    const idx = _bulkSelectedIds.indexOf(deviceId);
    if (idx >= 0) _bulkSelectedIds.splice(idx, 1);
    else _bulkSelectedIds.push(deviceId);
    const countEl = document.getElementById('bulk-select-count');
    if (countEl) countEl.textContent = _bulkSelectedIds.length + ' selected';
    const bulkBtn = document.getElementById('bulk-assign-btn');
    if (bulkBtn) bulkBtn.style.display = _bulkSelectedIds.length > 0 ? '' : 'none';
}

function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.plan-bulk-check');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    _bulkSelectedIds = [];
    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
        if (!allChecked) _bulkSelectedIds.push(parseInt(cb.dataset.deviceId));
    });
    const countEl = document.getElementById('bulk-select-count');
    if (countEl) countEl.textContent = _bulkSelectedIds.length + ' selected';
    const bulkBtn = document.getElementById('bulk-assign-btn');
    if (bulkBtn) bulkBtn.style.display = _bulkSelectedIds.length > 0 ? '' : 'none';
}

async function openBulkAssignModal() {
    if (!_bulkSelectedIds.length) { showNotification('Select vehicles first', 'fault'); return; }
    const templatesResp = await fetch('/api/maintenance/planner/templates?page_size=200&active_only=true', { headers: { 'Authorization': `Bearer ${authToken}` } });
    const tmplData = templatesResp.ok ? await templatesResp.json() : { items: [] };
    const templates = tmplData.items || [];

    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px);';
    modal.innerHTML = `<div class="premium-card" style="width:480px; max-width:90vw; padding:32px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
            <h3 style="font-size:1.1rem;font-weight:700;">Bulk Assign Template</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.3rem;padding:4px;">&times;</button>
        </div>
        <p style="font-size:0.82rem;color:var(--text-dim);margin-bottom:16px;">Assigning to ${_bulkSelectedIds.length} vehicle(s). Existing templates will be replaced.</p>
        <form id="bulk-form" style="display:flex;flex-direction:column;gap:12px;">
            <label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Select Template</label>
            <select id="bulk-template-id" required style="padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
                <option value="">Select Template...</option>
                ${templates.map(t => `<option value="${t.id}">${t.name} (${t.vehicle_category || t.vehicle_type || 'General'}) — ${t.rule_count || 0} rules</option>`).join('')}
            </select>
            <div style="display:flex;gap:10px;margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1;padding:12px;border-radius:8px;border:1px solid var(--border-light);background:transparent;color:var(--text-secondary);cursor:pointer;font-weight:600;font-size:0.85rem;">Cancel</button>
                <button type="submit" style="flex:1;padding:12px;border-radius:8px;border:none;background:var(--brand-primary);color:#fff;cursor:pointer;font-weight:600;font-size:0.85rem;">Assign to All</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);

    document.getElementById('bulk-form').onsubmit = async (e) => {
        e.preventDefault();
        const btn = modal.querySelector('button[type="submit"]');
        btn.disabled = true; btn.textContent = 'Assigning...';
        const templateId = parseInt(document.getElementById('bulk-template-id').value);
        if (!templateId) { showNotification('Select a template', 'fault'); btn.disabled = false; btn.textContent = 'Assign to All'; return; }
        try {
            const resp = await fetch('/api/maintenance/planner/plans/bulk-assign', {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                body: JSON.stringify({ device_ids: _bulkSelectedIds, template_id: templateId })
            });
            if (resp.ok) {
                const result = await resp.json();
                modal.remove();
                _bulkSelectedIds = [];
                await switchPlannerTab('plans');
                await refreshMaintDashboardCache();
                showNotification(`Assigned to ${result.success.length} vehicle(s), ${result.failed.length} failed`, 'scheduled');
            } else {
                const err = await resp.json();
                showNotification(err.detail || 'Bulk assign failed', 'fault');
                btn.disabled = false; btn.textContent = 'Assign to All';
            }
        } catch(err) { showNotification('Error in bulk assign', 'fault'); btn.disabled = false; btn.textContent = 'Assign to All'; }
    };
}

async function unassignTemplate(planId) {
    if (!confirm('Remove template from this vehicle? Rule overrides will be disabled but history is preserved.')) return;
    try {
        const resp = await fetch(`/api/maintenance/planner/plans/${planId}/unassign`, {
            method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            await switchPlannerTab('plans');
            await refreshMaintDashboardCache();
            showNotification('Template unassigned', 'scheduled');
        } else {
            const err = await resp.json();
            showNotification(err.detail || 'Failed to unassign', 'fault');
        }
    } catch(err) { showNotification('Error unassigning template', 'fault'); }
}

// ==================== RULE OVERRIDES ====================

let _overridePlanId = null;

async function viewPlanOverrides(planId) {
    _overridePlanId = planId;
    _planSearchState.selectedPlanId = planId;
    switchPlannerTab('overrides');
}

async function renderOverridesTable() {
    if (!_overridePlanId) return '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Select a vehicle plan to view its rule overrides.</div>';
    try {
        const resp = await fetch(`/api/maintenance/planner/plans/${_overridePlanId}/overrides`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!resp.ok) return '<div class="premium-card" style="padding:40px;text-align:center;color:var(--text-dim);">Failed to load overrides.</div>';
        const overrides = await resp.json();
        if (!overrides.length) return `<div class="premium-card" style="padding:40px;text-align:center;color:var(--text-dim);">
            No rule overrides for this plan. <button class="glass-btn primary" onclick="openRuleOverrideModal(${_overridePlanId})" style="margin-left:8px;padding:6px 14px;font-size:0.8rem;">Add Override</button>
        </div>`;
        let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <span style="font-size:0.85rem;color:var(--text-dim);">${overrides.length} overrides</span>
            <button class="glass-btn primary" onclick="openRuleOverrideModal(${_overridePlanId})" style="padding:8px 16px;font-size:0.8rem;"><i data-lucide="plus" style="width:14px;margin-right:4px;"></i> Add Override</button>
        </div>
        <table class="modern-table" style="width:100%;"><thead><tr>
            <th>Type</th><th>Rule</th><th>Override KM</th><th>Override Days</th><th>Override Hrs</th><th>Priority</th><th>Status</th><th>Reason</th><th>Actions</th>
        </tr></thead><tbody>`;
        overrides.forEach(o => {
            html += `<tr>
                <td>${o.type_name || '—'}</td>
                <td>${o.rule_name || '—'}</td>
                <td>${o.override_km != null ? o.override_km.toLocaleString() : '—'}</td>
                <td>${o.override_days != null ? o.override_days : '—'}</td>
                <td>${o.override_hours != null ? o.override_hours : '—'}</td>
                <td><span class="stats-badge ${o.override_priority === 'critical' ? 'danger' : o.override_priority === 'high' ? 'warning' : 'primary'}">${o.override_priority || '—'}</span></td>
                <td><span class="stats-badge ${o.is_enabled ? 'success' : 'warning'}">${o.is_enabled ? 'Enabled' : 'Disabled'}</span></td>
                <td style="font-size:0.75rem;color:var(--text-dim);max-width:120px;overflow:hidden;text-overflow:ellipsis;">${o.reason || '—'}</td>
                <td><div style="display:flex;gap:4px;">
                    <button class="glass-btn secondary" onclick="openRuleOverrideModal(${_overridePlanId}, ${o.id})" style="padding:4px 8px;font-size:0.7rem;">Edit</button>
                    <button class="glass-btn danger" onclick="deletePlanOverride(${o.id})" style="padding:4px 8px;font-size:0.7rem;">Del</button>
                </div></td>
            </tr>`;
        });
        html += '</tbody></table>';
        return html;
    } catch(e) {
        return '<div class="premium-card" style="padding:40px;text-align:center;color:var(--text-dim);">Error loading overrides.</div>';
    }
}

async function openRuleOverrideModal(planId, overrideId) {
    let overrideData = null;
    if (overrideId) {
        try {
            const resp = await fetch(`/api/maintenance/planner/plans/${planId}/overrides`, { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (resp.ok) {
                const overrides = await resp.json();
                overrideData = overrides.find(o => o.id === overrideId);
            }
        } catch(e) {}
    }

    const [typesResp, rulesResp] = await Promise.all([
        fetch('/api/maintenance/planner/types?page_size=200&active_only=true', { headers: { 'Authorization': `Bearer ${authToken}` } }),
        fetch('/api/maintenance/planner/rules?page_size=200&active_only=true', { headers: { 'Authorization': `Bearer ${authToken}` } })
    ]);
    const types = (typesResp.ok ? await typesResp.json() : { items: [] }).items || [];
    const rules = (rulesResp.ok ? await rulesResp.json() : { items: [] }).items || [];

    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(4px);';
    modal.innerHTML = `<div class="premium-card" style="width:520px;max-width:90vw;padding:32px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
            <h3 style="font-size:1.1rem;font-weight:700;">${overrideId ? 'Edit' : 'Add'} Rule Override</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.3rem;padding:4px;">&times;</button>
        </div>
        <form id="override-form" style="display:flex;flex-direction:column;gap:12px;">
            <label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Maintenance Type</label>
            <select id="override-type-id" required style="padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
                <option value="">Select Type...</option>
                ${types.map(t => `<option value="${t.id}" ${overrideData && overrideData.type_id === t.id ? 'selected' : ''}>${t.name}</option>`).join('')}
            </select>
            <label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Rule</label>
            <select id="override-rule-id" required style="padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
                <option value="">Select Rule...</option>
                ${rules.map(r => `<option value="${r.id}" ${overrideData && overrideData.rule_id === r.id ? 'selected' : ''}>${r.name}</option>`).join('')}
            </select>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Override KM</label><input type="number" id="override-km" value="${overrideData && overrideData.override_km != null ? overrideData.override_km : ''}" step="100" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;"></div>
                <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Override Days</label><input type="number" id="override-days" value="${overrideData && overrideData.override_days != null ? overrideData.override_days : ''}" step="1" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;"></div>
                <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Override Hours</label><input type="number" id="override-hours" value="${overrideData && overrideData.override_hours != null ? overrideData.override_hours : ''}" step="0.5" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;"></div>
                <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Priority</label>
                    <select id="override-priority" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;">
                        <option value="">Default</option>
                        <option value="low" ${overrideData && overrideData.override_priority === 'low' ? 'selected' : ''}>Low</option>
                        <option value="medium" ${overrideData && overrideData.override_priority === 'medium' ? 'selected' : ''}>Medium</option>
                        <option value="high" ${overrideData && overrideData.override_priority === 'high' ? 'selected' : ''}>High</option>
                        <option value="critical" ${overrideData && overrideData.override_priority === 'critical' ? 'selected' : ''}>Critical</option>
                    </select>
                </div>
            </div>
            <div><label style="font-size:0.75rem;font-weight:700;color:var(--text-dim);">Reason (optional)</label><textarea id="override-reason" rows="2" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-light);background:var(--fleet-bg);color:var(--text-primary);font-size:0.85rem;resize:vertical;">${overrideData ? (overrideData.reason || '') : ''}</textarea></div>
            <label style="display:flex;align-items:center;gap:8px;font-size:0.85rem;"><input type="checkbox" id="override-is-enabled" ${!overrideData || overrideData.is_enabled ? 'checked' : ''}> Enabled</label>
            <div style="display:flex;gap:10px;margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1;padding:12px;border-radius:8px;border:1px solid var(--border-light);background:transparent;color:var(--text-secondary);cursor:pointer;font-weight:600;font-size:0.85rem;">Cancel</button>
                <button type="submit" style="flex:1;padding:12px;border-radius:8px;border:none;background:var(--brand-primary);color:#fff;cursor:pointer;font-weight:600;font-size:0.85rem;">${overrideId ? 'Update' : 'Create'} Override</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
    lucide.createIcons({ el: modal });

    const form = document.getElementById('override-form');
    form.onsubmit = async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true; btn.textContent = 'Saving...';
        const payload = {
            rule_id: parseInt(document.getElementById('override-rule-id').value),
            type_id: parseInt(document.getElementById('override-type-id').value),
            override_km: parseFloat(document.getElementById('override-km').value) || null,
            override_days: parseInt(document.getElementById('override-days').value) || null,
            override_hours: parseFloat(document.getElementById('override-hours').value) || null,
            override_priority: document.getElementById('override-priority').value || null,
            is_enabled: document.getElementById('override-is-enabled').checked,
            reason: document.getElementById('override-reason').value.trim() || null
        };
        if (!payload.rule_id || !payload.type_id) { showNotification('Select type and rule', 'fault'); btn.disabled = false; btn.textContent = 'Save'; return; }
        try {
            let resp;
            if (overrideId) {
                resp = await fetch(`/api/maintenance/planner/overrides/${overrideId}`, {
                    method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify(payload)
                });
            } else {
                resp = await fetch(`/api/maintenance/planner/plans/${planId}/overrides`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify(payload)
                });
            }
            if (resp.ok) {
                modal.remove();
                await viewPlanOverrides(planId);
                showNotification(`Override ${overrideId ? 'updated' : 'created'}`, 'scheduled');
            } else {
                const err = await resp.json();
                showNotification(err.detail || 'Failed to save override', 'fault');
                btn.disabled = false; btn.textContent = 'Save';
            }
        } catch(err) { showNotification('Error saving override', 'fault'); btn.disabled = false; btn.textContent = 'Save'; }
    };
}

async function deletePlanOverride(overrideId) {
    if (!confirm('Delete this rule override permanently?')) return;
    try {
        const resp = await fetch(`/api/maintenance/planner/overrides/${overrideId}`, {
            method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            await viewPlanOverrides(_overridePlanId);
            showNotification('Override deleted', 'scheduled');
        } else {
            const err = await resp.json();
            showNotification(err.detail || 'Failed to delete', 'fault');
        }
    } catch(err) { showNotification('Error deleting override', 'fault'); }
}

// ==================== DELETE PLAN ====================

async function deletePlan(planId) {
    if (!confirm('Delete this maintenance plan? This will remove all rule overrides.')) return;
    try {
        const resp = await fetch(`/api/maintenance/planner/plans/${planId}`, {
            method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            await switchPlannerTab('plans');
            await refreshMaintDashboardCache();
            showNotification('Plan deleted', 'scheduled');
        } else {
            const err = await resp.json();
            showNotification(err.detail || 'Failed to delete', 'fault');
        }
    } catch(err) { showNotification('Error deleting plan', 'fault'); }
}

async function renderHistoryTable() {
    const resp = await fetch('/api/maintenance/planner/history?page_size=20', { headers: { 'Authorization': `Bearer ${authToken}` } });
    if (!resp.ok) return '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">Failed to load history.</div>';
    const data = await resp.json();
    const items = data.items || [];
    if (!items.length) return '<div class="premium-card" style="padding:40px; text-align:center; color:var(--text-dim);">No history entries yet.</div>';
    return `<table class="modern-table" style="width:100%;"><thead><tr><th>Date</th><th>Field</th><th>Old Value</th><th>New Value</th><th>Reason</th></tr></thead><tbody>${items.map(h => `<tr><td>${h.created_at ? h.created_at.split('T')[0] : '—'}</td><td>${h.field_name || '—'}</td><td>${h.old_value || '—'}</td><td>${h.new_value || '—'}</td><td>${h.reason || '—'}</td></tr>`).join('')}</tbody></table>`;
}

// ==================== RULE MODAL ====================
let ruleEditId = null;

async function openRuleModal(editData) {
    ruleEditId = editData ? editData.id : null;
    const isEdit = !!ruleEditId;

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.5); z-index:1000; display:flex; align-items:center; justify-content:center;';

    const typesResp = await fetch('/api/maintenance/planner/types?page_size=200', { headers: { 'Authorization': `Bearer ${authToken}` } });
    const typesData = typesResp.ok ? await typesResp.json() : { items: [] };
    const typeOptions = typesData.items.map(t => `<option value="${t.id}" ${editData && editData.type_id === t.id ? 'selected' : ''}>${t.name}</option>`).join('');

    modal.innerHTML = `<div class="premium-card" style="width:560px; max-width:90vw; max-height:90vh; overflow-y:auto; padding:32px;">
        <h3 style="font-size:1.1rem; font-weight:700; margin-bottom:16px;">${isEdit ? 'Edit' : 'Add'} Maintenance Rule</h3>
        <form onsubmit="submitRuleModal(event)" style="display:flex; flex-direction:column; gap:10px;">
            <input type="text" id="rule-name" placeholder="Rule Name" required value="${editData ? editData.name : ''}" style="padding:10px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
            <select id="rule-type-id" required style="padding:10px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"><option value="">Select Maintenance Type...</option>${typeOptions}</select>
            <textarea id="rule-description" placeholder="Description (optional)" style="padding:10px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); resize:vertical; min-height:50px;">${editData ? (editData.description || '') : ''}</textarea>

            <div style="border:1px solid var(--border-light); border-radius:8px; padding:12px;">
                <label style="font-weight:600; font-size:0.8rem; display:block; margin-bottom:6px;">Trigger Methods</label>
                <label style="display:flex; align-items:center; gap:6px; font-size:0.85rem; margin-bottom:6px;"><input type="checkbox" id="rule-trigger-manual" ${editData && editData.trigger_manual ? 'checked' : ''}/> Manual trigger only</label>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <input type="number" id="rule-trigger-km" placeholder="Trigger KM" step="100" value="${editData && editData.trigger_km != null ? editData.trigger_km : ''}" style="flex:1; min-width:120px; padding:8px; border-radius:6px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                    <input type="number" id="rule-trigger-days" placeholder="Trigger Days" step="1" value="${editData && editData.trigger_days != null ? editData.trigger_days : ''}" style="flex:1; min-width:120px; padding:8px; border-radius:6px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                    <input type="number" id="rule-trigger-hours" placeholder="Trigger Engine Hrs" step="0.5" value="${editData && editData.trigger_hours != null ? editData.trigger_hours : ''}" style="flex:1; min-width:120px; padding:8px; border-radius:6px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                </div>
            </div>

            <div style="display:flex; gap:8px;">
                <input type="number" id="rule-grace-km" placeholder="Grace KM" value="${editData && editData.grace_km != null ? editData.grace_km : 0}" step="100" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                <input type="number" id="rule-grace-days" placeholder="Grace Days" value="${editData && editData.grace_days != null ? editData.grace_days : 0}" step="1" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
            </div>

            <div style="display:flex; gap:8px;">
                <select id="rule-priority" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);">
                    <option value="low" ${editData && editData.priority === 'low' ? 'selected' : ''}>Low</option>
                    <option value="medium" ${editData && editData.priority === 'medium' ? 'selected' : ''}>Medium</option>
                    <option value="high" ${editData && editData.priority === 'high' ? 'selected' : ''}>High</option>
                    <option value="critical" ${editData && editData.priority === 'critical' ? 'selected' : ''}>Critical</option>
                </select>
                <input type="number" id="rule-order" placeholder="Order" value="${editData && editData.rule_order != null ? editData.rule_order : 0}" step="1" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
            </div>

            <div style="border:1px solid var(--border-light); border-radius:8px; padding:12px;">
                <label style="font-weight:600; font-size:0.8rem; display:block; margin-bottom:6px;">Validation Intervals (optional)</label>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <input type="number" id="rule-min-km" placeholder="Min KM" step="100" value="${editData && editData.min_interval_km != null ? editData.min_interval_km : ''}" style="flex:1; min-width:100px; padding:8px; border-radius:6px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                    <input type="number" id="rule-max-km" placeholder="Max KM" step="100" value="${editData && editData.max_interval_km != null ? editData.max_interval_km : ''}" style="flex:1; min-width:100px; padding:8px; border-radius:6px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                    <input type="number" id="rule-min-days" placeholder="Min Days" step="1" value="${editData && editData.min_interval_days != null ? editData.min_interval_days : ''}" style="flex:1; min-width:100px; padding:8px; border-radius:6px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                    <input type="number" id="rule-max-days" placeholder="Max Days" step="1" value="${editData && editData.max_interval_days != null ? editData.max_interval_days : ''}" style="flex:1; min-width:100px; padding:8px; border-radius:6px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary);"/>
                </div>
            </div>

            <label style="display:flex; align-items:center; gap:6px; font-size:0.85rem;"><input type="checkbox" id="rule-is-active" ${!editData || editData.is_active ? 'checked' : ''}/> Active</label>

            <div style="display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">${isEdit ? 'Update' : 'Create'} Rule</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
}

async function submitRuleModal(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('rule-name').value,
        type_id: parseInt(document.getElementById('rule-type-id').value),
        description: document.getElementById('rule-description').value || null,
        trigger_km: parseFloat(document.getElementById('rule-trigger-km').value) || null,
        trigger_days: parseInt(document.getElementById('rule-trigger-days').value) || null,
        trigger_hours: parseFloat(document.getElementById('rule-trigger-hours').value) || null,
        trigger_manual: document.getElementById('rule-trigger-manual').checked,
        grace_km: parseFloat(document.getElementById('rule-grace-km').value) || 0,
        grace_days: parseInt(document.getElementById('rule-grace-days').value) || 0,
        priority: document.getElementById('rule-priority').value,
        rule_order: parseInt(document.getElementById('rule-order').value) || 0,
        min_interval_km: parseFloat(document.getElementById('rule-min-km').value) || null,
        max_interval_km: parseFloat(document.getElementById('rule-max-km').value) || null,
        min_interval_days: parseInt(document.getElementById('rule-min-days').value) || null,
        max_interval_days: parseInt(document.getElementById('rule-max-days').value) || null,
        is_active: document.getElementById('rule-is-active').checked
    };
    if (!payload.type_id) { showNotification('Please select a maintenance type', 'fault'); return; }
    try {
        const url = ruleEditId ? `/api/maintenance/planner/rules/${ruleEditId}` : '/api/maintenance/planner/rules';
        const method = ruleEditId ? 'PUT' : 'POST';
        const resp = await fetch(url, { method, headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` }, body: JSON.stringify(payload) });
        if (resp.ok) { closeModal(); await loadPlannerDashboard(); await refreshMaintDashboardCache(); showNotification(`Rule ${ruleEditId ? 'updated' : 'created'}`, 'scheduled'); }
        else { const err = await resp.json(); showNotification(err.detail || 'Failed to save rule', 'fault'); }
    } catch (err) { showNotification('Error saving rule', 'fault'); }
}

async function editRule(id) {
    try {
        const resp = await fetch(`/api/maintenance/planner/rules`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!resp.ok) { showNotification('Failed to load rules', 'fault'); return; }
        const data = await resp.json();
        const rule = (data.items || []).find(r => r.id === id);
        if (rule) openRuleModal(rule);
        else showNotification('Rule not found', 'fault');
    } catch (err) { showNotification('Error loading rule', 'fault'); }
}

async function deleteRule(id) {
    if (!confirm('Delete this rule permanently?')) return;
    try {
        const resp = await fetch(`/api/maintenance/planner/rules/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` } });
        if (resp.ok) { await loadPlannerDashboard(); await refreshMaintDashboardCache(); showNotification('Rule deleted', 'scheduled'); }
        else { const err = await resp.json(); showNotification(err.detail || 'Failed to delete', 'fault'); }
    } catch (err) { showNotification('Error deleting rule', 'fault'); }
}

// Refresh dashboard cache after type/rule/template mutations
async function refreshMaintDashboardCache() {
    try {
        const [dashboardResp, summaryResp, tmplResp] = await Promise.all([
            fetch('/api/maintenance/dashboard', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/types/summary', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/maintenance/planner/templates?page_size=500', { headers: { 'Authorization': `Bearer ${authToken}` } })
        ]);
        if (dashboardResp.ok) maintDashboardData = await dashboardResp.json();
        if (summaryResp.ok) {
            if (!maintDashboardData) maintDashboardData = {};
            maintDashboardData.type_summary = await summaryResp.json();
        }
        if (tmplResp.ok) {
            const tmplData = await tmplResp.json();
            const tmplItems = tmplData.items || [];
            if (!maintDashboardData) maintDashboardData = {};
            maintDashboardData._templateSummary = {
                total: tmplData.total || 0,
                active: tmplItems.filter(t => t.is_active && !t.is_archived).length,
                inactive: tmplItems.filter(t => !t.is_active && !t.is_archived).length,
                archived: tmplItems.filter(t => t.is_archived).length
            };
            maintDashboardData._templates = tmplItems;
        }
        // Also fetch recent types for activity
        const typesResp = await fetch('/api/maintenance/planner/types?page_size=200&sort_by=updated_at&sort_order=desc', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (typesResp.ok) {
            const typesData = await typesResp.json();
            if (!maintDashboardData) maintDashboardData = {};
            maintDashboardData.recent_types = typesData.items || [];
        }
        // Re-render KPI with updated data
        const kpis = maintDashboardData?.kpis || {};
        const tSummary = maintDashboardData?.type_summary || maintDashboardData?._typeSummary;
        const tmplSummary = maintDashboardData?._templateSummary;
        const tmplItems = maintDashboardData?._templates || [];
        renderMaintenanceKPI(kpis, tSummary, tmplSummary);
        renderTemplateCategoryChart(tmplItems);
        renderRecentTemplateActivity(tmplItems);
    } catch (e) { /* silent - dashboard just uses stale data if refresh fails */ }
}

window.initPlanner = initPlanner;
window.loadPlannerDashboard = loadPlannerDashboard;
window.switchPlannerTab = switchPlannerTab;
window.renderPlannerTab = renderPlannerTab;
window.openTypeModal = openTypeModal;
window.submitTypeModal = submitTypeModal;
window.closeModal = closeModal;
window.editType = editType;
window.deleteType = deleteType;
window.openRuleModal = openRuleModal;
window.submitRuleModal = submitRuleModal;
window.editRule = editRule;
window.deleteRule = deleteRule;
window.openTemplateModal = openTemplateModal;
window.viewTemplateRules = viewTemplateRules;
window.deleteTemplate = deleteTemplate;
window.editTemplate = editTemplate;
window.duplicateTemplateAction = duplicateTemplateAction;
window.activateTemplateAction = activateTemplateAction;
window.deactivateTemplateAction = deactivateTemplateAction;
window.seedDefaultTemplates = seedDefaultTemplates;
window.switchTmplFilter = switchTmplFilter;
window.debouncedTmplSearch = debouncedTmplSearch;
window.sortTmplTable = sortTmplTable;
window.gotoTmplPage = gotoTmplPage;
window.addRuleToTemplateBuilder = addRuleToTemplateBuilder;
window.moveRuleInBuilder = moveRuleInBuilder;
window.removeRuleFromBuilder = removeRuleFromBuilder;
window.saveTemplate = saveTemplate;
window.renderTemplateRulesList = renderTemplateRulesList;
window.openPlanModal = openPlanModal;
window.viewPlanOverrides = viewPlanOverrides;
window.deletePlan = deletePlan;
window.openVehicleDetail = openVehicleDetail;
window.openRuleOverrideModal = openRuleOverrideModal;
window.deletePlanOverride = deletePlanOverride;
window.gotoPlanPage = gotoPlanPage;
window.sortPlanTable = sortPlanTable;
window.switchPlanFilter = switchPlanFilter;
window.debouncedPlanSearch = debouncedPlanSearch;

// -----------------------------------------
// UI Utility Functions
// -----------------------------------------
function animateCounter(id, target, duration = 1500) {
    const el = document.getElementById(id);
    if (!el) return;
    const start = parseInt(el.innerText) || 0;
    const range = target - start;
    let startTime = null;

    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        const progress = Math.min((timestamp - startTime) / duration, 1);
        el.innerText = Math.floor(progress * range + start);
        if (progress < 1) window.requestAnimationFrame(step);
    }
    window.requestAnimationFrame(step);
}

function toggleAnalyticsGroup(groupId) {
    const group = document.getElementById(groupId);
    if (group) group.classList.toggle('expanded');
}

function showNotification(msg, type) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content" style="position:fixed; bottom:40px; left:50%; transform:translateX(-50%); background:rgba(10, 15, 30, 0.95); backdrop-filter:blur(10px); padding:16px 24px; border-radius:16px; border:1px solid var(--border-strong); z-index:9999; display:flex; align-items:center; gap:12px; color:#fff; font-weight:600; box-shadow:0 20px 50px rgba(0,0,0,0.5);">
            <i data-lucide="${type === 'success' ? 'check-circle' : 'alert-triangle'}" style="color:${type === 'success' ? 'var(--brand-success)' : 'var(--brand-danger)'}"></i>
            <span>${msg}</span>
        </div>
    `;
    document.body.appendChild(toast);
    lucide.createIcons({ el: toast });
    setTimeout(() => {
        toast.style.transition = '0.5s opacity';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

// -----------------------------------------
// -----------------------------------------
// TELEMATICS AI CHATBOT (UPGRADED)
// -----------------------------------------
let currentChatId = null;
let isGenerating = false;
let abortController = null;

async function loadChatHistory() {
    if (!authToken) return;
    try {
        const response = await fetch('/api/v1/chat/sessions', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const sessions = await response.json();
        renderHistoryList(sessions);
    } catch (err) {
        console.error("Failed to load history:", err);
    }
}

function renderHistoryList(sessions) {
    const historyList = document.getElementById('history-list');
    if (!historyList) return;

    if (sessions.length === 0) {
        historyList.innerHTML = '<div class="history-empty">No previous chats</div>';
        return;
    }

    historyList.innerHTML = sessions.map(s => `
        <div class="history-item ${currentChatId === s.id ? 'active' : ''}" onclick="switchChat(${s.id})">
            <i data-lucide="message-square"></i>
            <div class="history-info">
                <span class="history-title">${s.title || 'Untitled Chat'}</span>
                <span class="history-meta">${new Date(s.updated_at).toLocaleDateString()} â€¢ ${s.message_count} msgs</span>
            </div>
            <button class="history-delete-btn" onclick="event.stopPropagation(); deleteChat(${s.id})">
                <i data-lucide="trash-2"></i>
            </button>
        </div>
    `).join('');
    lucide.createIcons({ el: historyList });
}

async function switchChat(chatId) {
    if (isGenerating) {
        alert("Please wait for the current response to finish or stop it.");
        return;
    }
    currentChatId = chatId;
    chatMessages.innerHTML = '';
    if (typingIndicator) typingIndicator.style.display = 'flex';

    try {
        const response = await fetch(`/api/v1/chat/${chatId}/messages`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const messages = await response.json();
        if (typingIndicator) typingIndicator.style.display = 'none';
        
        messages.forEach(m => {
            appendMessage(m.role === 'assistant' ? 'bot' : 'user', m.content);
        });
        
        loadChatHistory(); // Refresh sidebar active state
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (err) {
        console.error("Switch chat error:", err);
        if (typingIndicator) typingIndicator.style.display = 'none';
    }
}

async function startNewChat() {
    if (isGenerating) stopGeneration();
    currentChatId = null;
    chatMessages.innerHTML = `
        <div class="chat-welcome-state">
            <div class="bot-avatar-glow"><div class="bot-avatar"><i data-lucide="bot"></i></div></div>
            <h2>Fleet Intelligence Assistant</h2>
            <p>Model: DeepSeek-V3 | Latency: &lt;1.5s</p>
            <div class="welcome-suggestions">
                <button onclick="fillAndSend('Show all active vehicles')">Show active vehicles</button>
                <button onclick="fillAndSend('Fuel consumption last 24h')">Fuel analysis</button>
                <button onclick="fillAndSend('Any overspeed alerts today?')">Alerts check</button>
            </div>
        </div>
    `;
    lucide.createIcons({ el: chatMessages });
    loadChatHistory();
}

function fillAndSend(text) {
    userInput.value = text;
    sendMessage();
}

async function deleteChat(chatId) {
    if (!confirm("Permanently delete this conversation?")) return;
    try {
        await fetch(`/api/v1/chat/${chatId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (currentChatId === chatId) startNewChat();
        else loadChatHistory();
    } catch (err) {
        console.error("Delete error:", err);
    }
}

function stopGeneration() {
    if (abortController) {
        abortController.abort();
        isGenerating = false;
        if (typingIndicator) typingIndicator.style.display = 'none';
        const stopBtn = document.getElementById('stop-btn');
        if (stopBtn) stopBtn.style.display = 'none';
    }
}

function appendMessage(type, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type === 'user' ? 'user-message' : 'bot-message'}`;
    const content = document.createElement('div');
    content.className = 'message-content';

    let htmlContent = '';
    if (typeof marked !== 'undefined') {
        htmlContent = marked.parse(text);
    } else {
        htmlContent = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    if (type === 'bot') {
        htmlContent = htmlContent.replace(/<table>/g, '<div class="visual-table-wrap"><table class="modern-table">');
        htmlContent = htmlContent.replace(/<\/table>/g, '</table></div>');

        const metricPattern = /<li>(.*?):\s*([\d.,]+)\s*(\w*)\s*<\/li>/g;
        if (metricPattern.test(htmlContent)) {
            let kpiHtml = '<div class="visual-kpi-grid">';
            htmlContent = htmlContent.replace(metricPattern, (match, label, value, unit) => {
                kpiHtml += `
                    <div class="visual-kpi-item">
                        <span class="visual-kpi-label">${label}</span>
                        <span class="visual-kpi-value">${value} <small style="font-size:0.55rem;opacity:0.6;font-weight:400;">${unit}</small></span>
                    </div>`;
                return '';
            });
            kpiHtml += '</div>';
            htmlContent += kpiHtml;
        }

        // Chart detection: look for tables with numeric data
        htmlContent = htmlContent.replace(/<table class="modern-table">([\s\S]*?)<\/table><\/div>/g, (match, tableContent) => {
            const rows = tableContent.match(/<tr>[\s\S]*?<\/tr>/g);
            if (rows && rows.length >= 3) {
                const headerRow = rows[0];
                const headers = [...headerRow.matchAll(/<th[^>]*>(.*?)<\/th>/g)].map(m => m[1].trim());
                const dataRows = rows.slice(1).filter(r => !r.includes('</th>'));
                const numericCols = headers.filter((h, ci) => dataRows.some(r => {
                    const cells = [...r.matchAll(/<td[^>]*>(.*?)<\/td>/g)];
                    return cells[ci] && /^[\d.,]+$/.test(cells[ci][1].trim().replace(/,/g,''));
                }));
                if (numericCols.length >= 1 && dataRows.length >= 2 && dataRows.length <= 15) {
                    const chartId = 'chart_' + Date.now() + '_' + Math.random().toString(36).substr(2,5);
                    let chartHtml = match;
                    chartHtml += `<div class="chat-chart-container"><canvas id="${chartId}" width="350" height="${Math.max(120, dataRows.length * 28)}"></canvas></div>`;
                    setTimeout(() => renderChatChart(chartId, headers, dataRows, headers.indexOf(numericCols[0])), 100);
                    return chartHtml;
                }
            }
            return match;
        });
    }

    content.innerHTML = htmlContent;
    msgDiv.appendChild(content);
    
    const timeSpan = document.createElement('div');
    timeSpan.className = 'message-time';
    timeSpan.textContent = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    msgDiv.appendChild(timeSpan);
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    msgDiv.style.opacity = '0';
    msgDiv.style.transform = 'translateY(12px)';
    setTimeout(() => {
        msgDiv.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
        msgDiv.style.opacity = '1';
        msgDiv.style.transform = 'translateY(0)';
    }, 20);
    lucide.createIcons({ el: msgDiv });
}

function renderChatChart(canvasId, headers, rows, valueColIndex) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width;
    const h = canvas.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);

    const isDark = document.body.classList.contains('dark-theme') || !document.body.classList.contains('light-theme');
    const textColor = isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.6)';
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    const barColors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#06b6d4', '#f97316', '#ec4899', '#14b8a6', '#8b5cf6'];

    const nameCol = 0;
    const gap = 8;
    const barHeight = Math.min(22, (h - 30) / rows.length - gap);
    const leftMargin = 80;
    const rightMargin = 12;
    const chartW = w - leftMargin - rightMargin;

    const vals = rows.map(r => {
        const cells = [...r.matchAll(/<td[^>]*>(.*?)<\/td>/g)];
        const val = parseFloat((cells[valueColIndex]?.[1] || '0').replace(/,/g, ''));
        return { label: _stripHtml(cells[nameCol]?.[1] || ''), val };
    });
    const maxVal = Math.max(...vals.map(v => v.val), 1);

    ctx.clearRect(0, 0, w, h);

    // Title
    ctx.fillStyle = textColor;
    ctx.font = '600 9px system-ui, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(headers[valueColIndex] || 'Values', 0, 11);

    // Grid lines + bars
    vals.forEach((v, i) => {
        const y = 22 + i * (barHeight + gap);
        const barW = (v.val / maxVal) * chartW;

        ctx.fillStyle = gridColor;
        ctx.fillRect(leftMargin, y, chartW, barHeight);

        ctx.fillStyle = barColors[i % barColors.length];
        ctx.beginPath();
        ctx.roundRect(leftMargin, y, Math.max(barW, 4), barHeight, 4);
        ctx.fill();

        ctx.fillStyle = textColor;
        ctx.font = '500 8px system-ui, sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(v.label.length > 10 ? v.label.slice(0, 9) + '..' : v.label, leftMargin - 6, y + barHeight / 2 + 3);

        ctx.textAlign = 'left';
        ctx.fillStyle = isDark ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.8)';
        ctx.font = '600 8px system-ui, sans-serif';
        ctx.fillText(v.val.toLocaleString(), leftMargin + barW + 6, y + barHeight / 2 + 3);
    });
}

function _stripHtml(html) {
    const d = document.createElement('div');
    d.innerHTML = html;
    return d.textContent || '';
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || !authToken || isGenerating) return;

    console.log(`[CHAT_REQUEST_RECEIVED] Query: ${text}`);
    const startTime = Date.now();

    appendMessage('user', text);
    userInput.value = '';
    isGenerating = true;
    
    if (typingIndicator) typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const stopBtn = document.getElementById('stop-btn');
    if (stopBtn) stopBtn.style.display = 'flex';

    abortController = new AbortController();

    try {
        const response = await fetch('/api/v1/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify({ query: text, chat_id: currentChatId }),
            signal: abortController.signal
        });

        if (!response.ok) throw new Error("Stream connection failed");
        if (typingIndicator) typingIndicator.style.display = 'none';
        
        const botMsgDiv = document.createElement('div');
        botMsgDiv.className = 'message bot-message streaming';
        const botContent = document.createElement('div');
        botContent.className = 'message-content';
        botMsgDiv.appendChild(botContent);
        chatMessages.appendChild(botMsgDiv);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = "";
        let firstTokenReceived = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);
                    if (data.chat_id) {
                        currentChatId = data.chat_id;
                    } else if (data.token) {
                        if (!firstTokenReceived) {
                            console.log(`[FIRST_TOKEN_LATENCY] ${Date.now() - startTime}ms`);
                            firstTokenReceived = true;
                        }
                        fullResponse += data.token;
                        botContent.innerHTML = marked.parse(fullResponse);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    } else if (data.status === 'completed') {
                        console.log(`[RESPONSE_COMPLETED] Total time: ${Date.now() - startTime}ms`);
                    }
                } catch (e) {}
            }
        }

        botMsgDiv.classList.remove('streaming');
        isGenerating = false;
        if (stopBtn) stopBtn.style.display = 'none';
        loadChatHistory();

    } catch (err) {
        if (err.name !== 'AbortError') {
            appendMessage('bot', 'Network intelligence node unreachable.');
        }
        isGenerating = false;
        if (typingIndicator) typingIndicator.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'none';
    }
}

// -----------------------------------------
// ANALYTICS & DASHBOARD ENGINE
// -----------------------------------------
async function loadDashboardData() {
    if (!authToken) return;
    try {
        console.log("Fetching fleet dashboard data...");

        const summaryResp = await fetch('/api/analytics/summary', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!summaryResp.ok) throw new Error(`Analytics Fetch Failed: ${summaryResp.status}`);

        const summaryData = await summaryResp.json();
        const raw = summaryData.kpis || summaryData;

        // Also fetch stats for accurate moving count
        let moving = 0;
        try {
            const statsResp = await fetch('/api/v1/stats/summary', {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (statsResp.ok) {
                const statsData = await statsResp.json();
                moving = statsData.moving || 0;
            }
        } catch (e) {
            console.log("Stats fetch failed, using fallback");
        }

        const k = {
            total: raw.total || raw.total_vehicles || 0,
            moving: moving || raw.active || raw.moving || 0,
            stationary: raw.idle || raw.stationary || 0,
            offline: raw.stale || raw.offline || 0,
            overspeed: raw.overspeed || raw.overspeed_today || 0,
            online: raw.active || raw.online || 0
        };

        console.log("Fetching live vehicle data...");
        const vehiclesResp = await fetch('/api/v1/vehicles/live?limit=5000', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!vehiclesResp.ok) throw new Error(`Vehicles Fetch Failed: ${vehiclesResp.status}`);

        const vehiclesData = await vehiclesResp.json();
        const vehicles = Array.isArray(vehiclesData) ? vehiclesData : [];
        latestVehicles = vehicles;
        window._cachedFleetVehicles = vehicles; // Cache for fuel dropdown

        // Initialize Executive Map
        initExecutiveMap();

        console.log(`Loaded ${vehicles.length} vehicles. Updating dashboard UI...`);

        // Add moving count to kpis if available from stats endpoint
        if (summaryData.kpis && moving > 0) {
            summaryData.kpis.moving = moving;
        }

        // Update Expandable Master Cards
        updateExecutiveDashboard(summaryData);
        
        // Ensure legacy elements if they exist are still updated
        animateCounter('kpi-total', k.total);
        animateCounter('kpi-moving', k.moving);
        animateCounter('kpi-idle', k.stationary);
        animateCounter('kpi-stopped', k.stationary);
        animateCounter('kpi-offline', k.offline);
        animateCounter('kpi-offline-alerts', k.offline);

        // Update Alerts KPIs
        animateCounter('kpi-alerts-total', k.overspeed);
        animateCounter('kpi-overspeed', k.overspeed);

        // Update Trips KPI
        animateCounter('kpi-trips-total', k.moving);
        animateCounter('kpi-running-trips', k.moving);

        // Update Charts
        updateVelocityChart(vehicles);

        const stats = {
            total: k.total,
            moving: k.moving,
            idle: k.stationary,
            stopped: 0,
            offline: k.offline
        };
        // updateStatusDonut(stats); // Legacy

        // Task 5: Remove all mock data in fuel view
        const fuelCost = document.querySelector('#view-fuel .mini-stat:nth-child(1) .card-value');
        const avgEff = document.querySelector('#view-fuel .mini-stat:nth-child(2) .card-value');
        if (fuelCost) fuelCost.innerText = `Rs. ${currentFuelPricePKR.toFixed(2)}`;
        // Compute avg efficiency from recent fuel vehicles if available
        if (avgEff) {
            const fuelVehicles = (vehicles || []).filter(v => v.status === 'online' && (v.speed || 0) > 5);
            if (fuelVehicles.length > 0) {
                const avgKmpl = fuelVehicles.reduce((s, v) => s + (v.kmpl || 10), 0) / fuelVehicles.length;
                avgEff.innerText = `${avgKmpl.toFixed(1)} km/L`;
            } else {
                avgEff.innerText = `-- km/L`;
            }
        }

        // Update Asset Grid
        renderDashV2Matrix(vehicles);

        // --- ALERTS & SECURITY FILTERING ---
        const allEvents = summaryData.recent_events || summaryData.recentEvents || [];
        const filteredEvents = allEvents.filter(e => alertPreferences[e.type] !== false);
        
        // Individual counts for dashboard sub-cards
        const counts = {
            overspeed: filteredEvents.filter(e => e.type.toLowerCase().includes('overspeed')).length,
            ignition: filteredEvents.filter(e => e.type.toLowerCase().includes('ignition')).length,
            geofence: filteredEvents.filter(e => e.type.toLowerCase().includes('geofence')).length,
            offline: filteredEvents.filter(e => e.type.toLowerCase().includes('offline')).length,
            total: filteredEvents.length
        };

        // Update Alerts Master Card
        animateCounter('kpi-alerts-total', counts.total);
        animateCounter('kpi-overspeed', counts.overspeed);
        animateCounter('kpi-ignition', counts.ignition);
        animateCounter('kpi-geofence', counts.geofence);
        animateCounter('kpi-offline-alerts', counts.offline);

        const badge = document.getElementById('vehicle-count-badge');
        if (badge) badge.innerText = `${k.total.toLocaleString()} Total Units`;

        console.log("Dashboard update complete.");

        // --- NEW: Update Alerts Card V2 ---
        if (summaryData.securityStats) {
            const tamper = summaryData.securityStats.tamper || 0;
            const geofence = summaryData.securityStats.geofence || 0;
            const secTotal = tamper + geofence;
            animateCounter('kpi-alerts-count-v2', secTotal);
            
            const summaryEl = document.getElementById('selected-alerts-summary');
            if (summaryEl) {
                summaryEl.textContent = `Tamper: ${tamper} | Geofence: ${geofence}`;
            }
        }
        
        if (summaryData.recent_events) {
            updateDashboardTimelineFeed(summaryData.recent_events);
        }

    } catch (e) {
        console.error("Dashboard Engine Failure:", e);
        showNotification("Critical engine sync error. Retrying...", "error");
    }
}

function updateVelocityChart(vehicles) {
    const ctx = document.getElementById('fleetTrendChart');
    if (!ctx) return;

    const labels = vehicles.slice(0, 8).map(v => formatVehicleDisplayName(v));
    const speedData = vehicles.slice(0, 8).map(v => v.speed || 0);
    const fuelData = vehicles.slice(0, 8).map(v => v.attributes?.fuelLevel || v.attributes?.fuel || 0);

    if (velocityChart) {
        velocityChart.data.labels = labels;
        velocityChart.data.datasets[0].data = speedData;
        velocityChart.data.datasets[1].data = fuelData;
        velocityChart.update();
    } else {
        velocityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Velocity (km/h)', data: speedData, borderColor: '#0ea5e9', backgroundColor: 'rgba(14, 165, 233, 0.1)', fill: true, tension: 0.4 },
                    { label: 'Energy (%)', data: fuelData, borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', fill: true, tension: 0.4 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                    x: { grid: { display: false }, ticks: { color: '#64748b' } }
                }
            }
        });
    }
}

function updateStatusDonut(stats) {
    const ctx = document.getElementById('fleetStatusChart');
    if (!ctx) return;

    const data = [stats.moving, stats.idle, stats.stopped, stats.offline];
    const labels = ['Moving', 'Idle', 'Stopped', 'Offline'];
    const colors = ['#10b981', '#f59e0b', '#ef4444', '#64748b'];

    document.getElementById('donut-total').innerText = stats.total;

    if (statusDonutChart) {
        statusDonutChart.data.datasets[0].data = data;
        statusDonutChart.update();
    } else {
        statusDonutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 10 }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                plugins: { legend: { display: false } }
            }
        });
    }

    const legend = document.getElementById('donut-legend');
    // --- Dashboard V2 Logic ---
    document.getElementById('global-theme-toggle-v2')?.addEventListener('click', () => {
        const isLight = document.body.classList.toggle('light-theme');
        document.body.setAttribute('data-theme', isLight ? 'light' : 'dark');
        const icon = document.querySelector('#global-theme-toggle-v2 i');
        if (icon) icon.setAttribute('data-lucide', isLight ? 'moon' : 'sun');
        lucide.createIcons();
    });
}

function filterMatrixTable() {
    const searchEl = document.getElementById('matrix-search-input');
    const q = (searchEl?.value || '').toLowerCase();
    const s = matrixStatusFilter;
    
    const filtered = latestVehicles.filter(v => {
        const matchesQ = !q || 
            formatVehicleDisplayName(v).toLowerCase().includes(q) || 
            formatDriverDisplayName(v).toLowerCase().includes(q) || 
            (v.uniqueId || '').toLowerCase().includes(q);
        
        const statusClass = getVehicleStatus(v).class;
        const matchesS = !s || statusClass === s;
        return matchesQ && matchesS;
    });

    renderDashV2Matrix(filtered);
}

function renderDashV2Matrix(vehicles) {
    const body = document.getElementById('dash-v2-matrix-body');
    if (!body) return;

    document.getElementById('matrix-asset-count').innerText = `${vehicles.length} Assets`;

    if (vehicles.length === 0) {
        body.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:60px; color:var(--fleet-text-sub); font-weight:700;">No assets match your search criteria.</td></tr>`;
        return;
    }

    body.innerHTML = vehicles.map(v => {
        const statusInfo = getVehicleStatus(v);
        const status = statusInfo.class;
        const displayName = formatVehicleDisplayName(v);
        const driverName = formatDriverDisplayName(v);

        return `
            <tr class="matrix-row-refined" onclick="navigateToMap(${v.id})">
                <td>
                    <div class="asset-identity">
                        <div class="asset-avatar status-${status}"><i data-lucide="truck"></i></div>
                        <div class="asset-info">
                            <span class="name">${displayName}</span>
                            <span class="imei">ID: ${v.uniqueId || 'N/A'}</span>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="driver-cell">
                        <span class="driver-name">${driverName}</span>
                        <span class="driver-meta">${v.model || 'GEN-4 TELEMETRY'}</span>
                    </div>
                </td>
                <td>
                    <span class="status-pill-v2 ${status}">${statusInfo.label}</span>
                </td>
                <td class="td-actions">
                    <button class="view-btn-eye" onclick="event.stopPropagation(); navigateToMap(${v.id})" title="Focus on Map">
                        <i data-lucide="eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    lucide.createIcons({ el: body });
}

function navigateToMap(deviceId) {
    const navItem = document.querySelector('.nav-item[data-view="map"]');
    if (navItem) {
        navItem.click();
        // The stopMapUpdates/startMapUpdates logic is already in the nav-item listener
        // We might need to select the vehicle on the map
        setTimeout(() => {
            const vehicle = latestVehicles.find(v => String(v.id) === String(deviceId));
            if (vehicle) focusVehicleOnMap(vehicle.id);
        }, 500);
    }
}

function renderAssetGrid(vehicles) {
    // Store for filtering — do NOT clear latestVehicles (used by map)
    window._allAssetGridVehicles = vehicles;
    _renderAssetRows(vehicles);
}

function applyAssetFilters() {
    const all = window._allAssetGridVehicles || [];
    const globalQ = (document.getElementById('alr-search-global')?.value || '').toLowerCase();

    const filtered = all.filter(v => {
        const displayName = formatVehicleDisplayName(v).toLowerCase();
        const driverName = formatDriverDisplayName(v).toLowerCase();
        const uniqueId = (v.uniqueId || '').toLowerCase();

        return !globalQ || displayName.includes(globalQ) || driverName.includes(globalQ) || uniqueId.includes(globalQ);
    });

    _renderAssetRows(filtered);
}

function _renderAssetRows(vehicles) {
    const grid = document.getElementById('asset-grid');
    if (!grid) return;

    if (!vehicles || vehicles.length === 0) {
        grid.innerHTML = `<tr><td colspan="4"><div class="asset-empty-state" style="text-align:center; padding:40px; color:var(--text-dim);"><i data-lucide="truck" style="width:40px;height:40px;opacity:0.2;margin-bottom:12px;"></i><p>No fleet assets match your filters</p></div></td></tr>`;
        lucide.createIcons({ el: grid });
        return;
    }

    grid.innerHTML = vehicles.map((v, idx) => {
        const speedKmh = (v.speed * 1.852).toFixed(1);
        const fuelLevel = v.attributes?.fuelLevel || 0;
        const displayName = formatVehicleDisplayName(v);
        
        return `
            <tr style="animation: fadeIn 0.4s ease-out forwards; animation-delay: ${idx * 15}ms;">
                <td>
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div style="width:40px; height:40px; background:rgba(59, 130, 246, 0.1); border-radius:10px; display:flex; align-items:center; justify-content:center; color:var(--brand-primary);">
                            <i data-lucide="truck" style="width:20px;"></i>
                        </div>
                        <div>
                            <div style="font-weight:700; font-size:0.95rem; color:var(--text-primary);">${displayName}</div>
                            <div style="font-size:0.75rem; color:var(--text-dim);">ID: ${v.uniqueId}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <div style="display:flex; flex-direction:column; gap:4px;">
                        <span style="font-size:0.8rem; font-weight:600; color:var(--text-secondary);">${v.model || 'GEN-4 SENSOR'}</span>
                        <div style="width:100px; height:4px; background:rgba(255,255,255,0.05); border-radius:2px; overflow:hidden;">
                            <div style="width:${fuelLevel}%; height:100%; background:linear-gradient(90deg, var(--brand-primary), var(--brand-secondary));"></div>
                        </div>
                    </div>
                </td>
                <td>
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <div style="width:8px; height:8px; border-radius:50%; background:${v.status === 'online' ? 'var(--brand-success)' : 'var(--brand-danger)'};"></div>
                            <span style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:${v.status === 'online' ? 'var(--brand-success)' : 'var(--brand-danger)'};">${v.status}</span>
                        </div>
                        <div style="font-size:0.8rem; font-weight:600; color:var(--text-secondary);">
                            <i data-lucide="gauge" style="width:12px; vertical-align:middle; margin-right:4px;"></i>${speedKmh} km/h
                        </div>
                    </div>
                </td>
                <td style="text-align:right;">
                    <button class="icon-btn-small" onclick="openDetailsModal('${v.id}')" style="background:rgba(255,255,255,0.03); border:1px solid var(--border-light); border-radius:8px; width:32px; height:32px; color:var(--brand-primary); cursor:pointer; transition:var(--transition-fast);">
                        <i data-lucide="external-link" style="width:16px;"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    lucide.createIcons({ el: grid });
}


// -----------------------------------------
// VEHICLE INTELLIGENCE ENGINE (real API)
// -----------------------------------------

let currentIntelDeviceId = null;   // track which device is loaded in the intel panel

async function openVehicleIntel(identifier) {
    const v = latestVehicles.find(x => x.name === identifier || String(x.id) === String(identifier));
    if (!v) return;

    selectedVehicle = v;
    currentIntelDeviceId = v.id;
    activeVinDeviceId = v.id;

    const displayName = formatVehicleDisplayName(v);

    // Update Context Labels
    const contextText = `Asset: ${displayName} (${v.uniqueId || 'N/A'})`;
    ['fuel-asset-context', 'maint-asset-context'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerText = contextText;
    });

    // Navigate to Vehicle Intelligence view
    const navItem = document.querySelector('.nav-item[data-view="vehicle-intel"]');
    if (navItem) navItem.click();

    // Load intel data from backend
    await loadVehicleIntel(v.id);

    // Also update other modules in background
    updateFuelForSelected();
    updateMaintForSelected();
}

/**
 * Task 4: Fix Navigation back to Dashboard
 */
function backToIntelDashboard() {
    const noSel = document.getElementById('intel-no-selection');
    const mainGrid = document.getElementById('intel-main-grid');
    const banner = document.getElementById('intel-amber-banner');

    if (noSel) noSel.style.display = 'block';
    if (mainGrid) mainGrid.style.display = 'none';
    if (banner) banner.style.display = 'none';

    // Smooth scroll to top
    const container = document.querySelector('.module-content-container');
    if (container) container.scrollTo({ top: 0, behavior: 'smooth' });

    selectedVehicle = null;
    currentIntelDeviceId = null;

    lucide.createIcons();
}

async function loadVehicleIntel(deviceId) {
    if (!deviceId || !authToken) return;

    // Show main grid, hide no-selection placeholder
    const noSel = document.getElementById('intel-no-selection');
    const mainGrid = document.getElementById('intel-main-grid');
    const banner = document.getElementById('intel-amber-banner');
    if (noSel) noSel.style.display = 'none';
    if (mainGrid) mainGrid.style.display = 'block';

    // Spinner on refresh button
    const refreshBtn = document.getElementById('intel-refresh-btn');
    if (refreshBtn) refreshBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:13px;"></i> Loading...';

    try {
        const resp = await fetch(`/api/v1/vehicles/${deviceId}/intel`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!resp.ok) throw new Error(`Intel API ${resp.status}`);
        const d = await resp.json();

        console.log(`[VIN Intel] Device ${deviceId} | VIN: ${d.vin} | source: ${d.vin_source} | badge: ${d.badge?.label}`);

        // ΓöÇΓöÇ Header ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        const vData = latestVehicles.find(x => x.id === deviceId) || d;
        const displayName = formatVehicleDisplayName(vData);

        const nameEl = document.getElementById('intel-v-name');
        const vinEl = document.getElementById('intel-v-vin');
        const badgeEl = document.getElementById('intel-vin-badge');
        const breadcrumbName = document.getElementById('intel-breadcrumb-name');

        if (nameEl) nameEl.innerText = displayName;
        if (vinEl) vinEl.innerText = d.vin || 'Not Assigned';
        if (breadcrumbName) breadcrumbName.innerText = displayName;

        // Populate Configuration Card
        const configVin = document.getElementById('intel-config-vin');
        if (configVin) configVin.value = d.vin || '';

        if (badgeEl) {
            if (d.vin && d.badge) {
                badgeEl.style.display = 'inline-block';
                badgeEl.innerText = d.badge.label;
                badgeEl.className = `stats-badge ${d.badge.class || ''}`;
            } else {
                badgeEl.style.display = 'none';
            }
        }

        // ΓöÇΓöÇ Amber Banner ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        if (banner) {
            if (d.is_incomplete) banner.classList.remove('vin-hidden');
            else banner.classList.add('vin-hidden');
        }

        // ΓöÇΓöÇ Specs Grid ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        const s = d.specs || {};
        const setField = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val || 'N/A';
        };
        setField('intel-make', s.make);
        setField('intel-model', s.model);
        setField('intel-year', s.year ? String(s.year) : null);
        setField('intel-engine', s.engine);
        setField('intel-fuel', s.fuel_type);
        setField('intel-category', s.category);

        // ΓöÇΓöÇ Odometer ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        const odoEl = document.getElementById('intel-odometer');
        if (odoEl) odoEl.innerText = d.odometer_km > 0 ? `${d.odometer_km.toLocaleString()} km` : '-- km';

        // ΓöÇΓöÇ Profile Status Badge ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        const statusEl = document.getElementById('intel-profile-status');
        if (statusEl) {
            const statusMap = {
                'obd_verified': ['OBD Verified', 'success'],
                'manual_enriched': ['Manual Enriched', 'primary'],
            };
            const [label, cls] = statusMap[d.profile_status] || ['Pending / Unknown', ''];
            statusEl.innerText = label;
            statusEl.className = `stats-badge ${cls}`;
        }

        // ΓöÇΓöÇ Rich Technical Specs (NEW) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        renderRichVinData(s);

        // === Overspeed Count (Real Data) ===
        var overspeedEl = document.getElementById('intel-overspeed-count');
        if (overspeedEl) overspeedEl.innerText = (d.overspeed_count || 0) + ' Events';

        // === FDB + GPS Data ===
        var fdb = d.fdb_data || {};
        var gps = d.gps_summary || {};

        var nextServiceEl = document.getElementById('next-service-val');
        var brakeLifeEl = document.getElementById('brake-life-val');
        if (nextServiceEl) {
            nextServiceEl.innerText = fdb.benchmark_kmpl ? (fdb.benchmark_kmpl + ' km/L benchmark') : 'No benchmark data';
        }
        if (brakeLifeEl) {
            brakeLifeEl.innerText = gps.avg_daily_km ? (gps.avg_daily_km + ' km/day avg') : 'No GPS data';
        }

        var alertsContainer = document.getElementById('intel-recent-alerts');
        if (alertsContainer && d.recent_alerts && d.recent_alerts.length > 0) {
            var sevColors = { critical: '#ef4444', warning: '#f59e0b', info: '#3b82f6' };
            alertsContainer.innerHTML = d.recent_alerts.map(function(a) {
                var color = sevColors[a.severity] || '#6b7280';
                var time = a.time ? new Date(a.time).toLocaleDateString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }) : '';
                return '<div style="display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid var(--fleet-border); font-size:12px;">' +
                    '<span style="width:8px; height:8px; border-radius:50%; background:' + color + '; flex-shrink:0;"></span>' +
                    '<span style="flex:1;">' + (a.title || '') + '</span>' +
                    '<span style="color:#999; white-space:nowrap;">' + time + '</span></div>';
            }).join('');
        } else if (alertsContainer) {
            alertsContainer.innerHTML = '<div style="padding:16px; text-align:center; color:#999; font-size:12px;">No recent alerts for this vehicle</div>';
        }
        const depr = d.depreciation || {};
        const hasDeprData = depr.labels && depr.labels.length > 0 && s.year;

        const noDataEl = document.getElementById('intel-depr-no-data');
        const chartWrap = document.getElementById('intel-depr-chart-wrap');
        const summaryEl = document.getElementById('intel-depr-summary');

        if (hasDeprData) {
            if (noDataEl) noDataEl.style.display = 'none';
            if (chartWrap) chartWrap.style.display = 'block';
            if (summaryEl) summaryEl.style.display = 'flex';

            const chartData = {
                labels: depr.labels,
                datasets: [
                    {
                        label: 'Projected Value (%)',
                        data: depr.projected,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139,92,246,0.12)',
                        borderDash: [6, 3],
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                    },
                    {
                        label: 'Actual Value (%)',
                        data: depr.actual,
                        borderColor: '#0ea5e9',
                        backgroundColor: 'rgba(14,165,233,0.12)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                    }
                ]
            };

            if (lifecycleChart) {
                lifecycleChart.data = chartData;
                lifecycleChart.update();
            } else {
                const ctx = document.getElementById('lifecycleChart');
                if (ctx) {
                    lifecycleChart = new Chart(ctx, {
                        type: 'line',
                        data: chartData,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { labels: { color: '#94a3b8', font: { size: 11 } } },
                                tooltip: {
                                    callbacks: {
                                        label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}%`
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    min: 0, max: 100,
                                    grid: { color: 'rgba(255,255,255,0.05)' },
                                    ticks: { color: '#64748b', callback: v => `${v}%` }
                                },
                                x: {
                                    grid: { display: false },
                                    ticks: { color: '#64748b' }
                                }
                            }
                        }
                    });
                }
            }

            // Summary row
            const currentYear = new Date().getFullYear();
            const age = s.year ? (currentYear - s.year) : null;
            const pctEl = document.getElementById('intel-depr-pct');
            const ageEl = document.getElementById('intel-vehicle-age');
            const deprOdo = document.getElementById('intel-depr-odo');
            if (pctEl) pctEl.innerText = `${depr.current_pct}%`;
            if (ageEl) ageEl.innerText = age !== null ? `${age} yr${age !== 1 ? 's' : ''}` : '--';
            if (deprOdo) deprOdo.innerText = d.odometer_km > 0 ? `${d.odometer_km.toLocaleString()} km` : '--';

        } else {
            if (noDataEl) noDataEl.style.display = 'flex';
            if (chartWrap) chartWrap.style.display = 'none';
            if (summaryEl) summaryEl.style.display = 'none';
        }

        safeCreateIcons();

    } catch (err) {
        console.error('[VIN Intel] Error loading intel:', err);
        showNotification('Could not load vehicle intelligence data.', 'error');
    } finally {
        if (refreshBtn) {
            refreshBtn.innerHTML = '<i data-lucide="refresh-cw" style="width:13px;"></i> Refresh';
            safeCreateIcons();
        }
    }
}

function refreshIntelForCurrent() {
    if (currentIntelDeviceId) loadVehicleIntel(currentIntelDeviceId);
}

function renderRichVinData(specs) {
    const container = document.getElementById('vin-data-container');
    if (!container) return;

    if (!specs || (Object.keys(specs).length < 5 && !specs.brand)) {
        container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">
            <i data-lucide="info" style="width:24px; opacity:0.5; margin-bottom:8px;"></i>
            <p>Insufficient technical data for this profile. Try refreshing the sync or entering the VIN manually.</p>
        </div>`;
        lucide.createIcons({ el: container });
        return;
    }

    // Group fields logically
    const groups = {
        "Manufacturing": ["make", "brand", "manufacturer", "country", "plant_city", "plant_state", "year"],
        "Powertrain": ["engine", "displacement", "fuel_type", "drive_type", "cylinders", "transmission", "displacement_l"],
        "Body & Chassis": ["body_class", "vehicle_type", "doors", "gross_vehicle_weight_rating", "wheel_base_type"]
    };

    let html = '';
    for (const [title, fields] of Object.entries(groups)) {
        const groupFields = fields.filter(f => specs[f] && specs[f] !== 'N/A' && specs[f] !== 'Unknown');
        if (groupFields.length === 0) continue;

        html += `
            <div class="vin-group">
                <div class="vin-group-title">
                    <i data-lucide="${title === 'Powertrain' ? 'zap' : (title === 'Manufacturing' ? 'factory' : 'truck')}"></i>
                    ${title}
                </div>
                ${groupFields.map(f => `
                    <div class="vin-field">
                        <span class="vin-label">${f.replace(/_/g, ' ').toUpperCase()}</span>
                        <span class="vin-value">${specs[f]}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    container.innerHTML = html || `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">No detailed specs found.</div>`;
    lucide.createIcons({ el: container });
}

async function vinSearchAnalyze() {
    const term = (document.getElementById('vin-search')?.value || '').trim().toUpperCase();
    if (!term) {
        showNotification('Enter a VIN or vehicle name to search.', 'error');
        return;
    }

    const analyzeBtn = document.querySelector('button[onclick="vinSearchAnalyze()"]');
    const originalText = analyzeBtn.innerHTML;
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;"></i> Analyzing...';
    lucide.createIcons({ el: analyzeBtn });

    // 1. Search in local list
    const v = latestVehicles.find(x =>
        (x.vin || '').toUpperCase() === term ||
        (x.name || '').toUpperCase().includes(term) ||
        (x.uniqueId || '').toUpperCase() === term
    );

    if (v) {
        openVehicleIntel(v.name);
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = originalText;
        lucide.createIcons({ el: analyzeBtn });
        return;
    }

    // 2. Not found locally? Perform Global VIN Intelligence Lookup
    try {
        const resp = await fetch(`/api/v1/vehicles/vin/${term}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (resp.ok) {
            const data = await resp.json();
            showVinAnalysisModal(data, term);
        } else {
            showNotification(`No record found for "${term}".`, 'error');
        }
    } catch (e) {
        showNotification('Intelligence node connectivity error.', 'error');
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = originalText;
        lucide.createIcons({ el: analyzeBtn });
    }
}

function showVinAnalysisModal(data, vin) {
    const modal = document.getElementById('vin-analysis-modal');
    const container = document.getElementById('vin-analysis-details');
    const vinCode = document.getElementById('analysis-modal-vin');
    const pinBtn = document.getElementById('pin-vin-btn');

    if (vinCode) vinCode.innerText = vin;

    // Inject Specs using the existing rich renderer style
    if (container) {
        // Reuse the rich specs logic but targeting the modal
        const specs = data.full_specs || data;
        const groups = {
            'Manufacturing': ['brand', 'model', 'year', 'manufacturer', 'country', 'vehicle_type', 'plant_city'],
            'Powertrain': ['engine', 'displacement', 'cylinders', 'fuel_type', 'transmission', 'drive_type'],
            'Body & Chassis': ['body_class', 'gross_vehicle_weight_rating', 'doors', 'wheel_base_type']
        };

        let html = '';
        for (const [title, fields] of Object.entries(groups)) {
            const groupFields = fields.filter(f => specs[f] && specs[f] !== 'N/A' && specs[f] !== 'Unknown');
            if (groupFields.length === 0) continue;

            html += `
                <div class="vin-group">
                    <div class="vin-group-title">
                        <i data-lucide="${title === 'Powertrain' ? 'zap' : (title === 'Manufacturing' ? 'factory' : 'truck')}"></i>
                        ${title}
                    </div>
                    <div class="vin-fields-grid" style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:10px;">
                        ${groupFields.map(f => `
                            <div class="vin-field">
                                <span class="vin-label" style="font-size:0.65rem; color:var(--text-dim); text-transform:uppercase;">${f.replace(/_/g, ' ')}</span>
                                <span class="vin-value" style="display:block; font-size:0.85rem; font-weight:600;">${specs[f]}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        container.innerHTML = html || '<p style="text-align:center; padding:20px;">No additional specs available.</p>';
        lucide.createIcons({ el: container });
    }

    if (pinBtn) {
        pinBtn.onclick = () => pinVinToDashboard(vin);
        pinBtn.innerHTML = '<i data-lucide="plus-circle"></i> Add to Managed Dashboard';
        lucide.createIcons({ el: pinBtn });
    }

    modal.classList.remove('hidden-view');
    modal.style.display = 'flex';
}

function closeVinAnalysisModal() {
    const modal = document.getElementById('vin-analysis-modal');
    modal.classList.add('hidden-view');
    modal.style.display = 'none';
}

async function pinVinToDashboard(vin) {
    const pinBtn = document.getElementById('pin-vin-btn');
    pinBtn.disabled = true;
    pinBtn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Saving...';
    lucide.createIcons({ el: pinBtn });

    try {
        const resp = await fetch(`/api/v1/vehicles/vin/${vin}/pin`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            showNotification("Intelligence profile saved to dashboard.", "success");
            closeVinAnalysisModal();

            // Switch view state to Dashboard mode immediately
            const noSel = document.getElementById('intel-no-selection');
            const mainGrid = document.getElementById('intel-main-grid');
            if (noSel) noSel.style.display = 'block';
            if (mainGrid) mainGrid.style.display = 'none';

            loadVinDashboard();
        } else {
            showNotification("Failed to save profile.", "error");
        }
    } catch (e) {
        showNotification("Connectivity error.", "error");
    } finally {
        pinBtn.disabled = false;
        pinBtn.innerHTML = '<i data-lucide="plus-circle"></i> Add to Managed Dashboard';
        lucide.createIcons({ el: pinBtn });
    }
}

async function loadVinDashboard() {
    const grid = document.getElementById('vin-dashboard-grid');
    const countEl = document.getElementById('saved-vins-count');
    if (!grid) return;

    try {
        const resp = await fetch('/api/v1/vehicles/vin/saved', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await resp.json();

        if (!Array.isArray(data)) {
            if (countEl) countEl.innerText = "0 Profiles";
            return;
        }

        if (countEl) countEl.innerText = `${data.length} Profile${data.length !== 1 ? 's' : ''}`;

        if (data.length === 0) {
            grid.innerHTML = `
                <div class="empty-dashboard-placeholder" style="grid-column:1/-1; text-align:center; padding:60px; color:var(--text-dim); background:var(--bg-card); border-radius:16px; border:1px dashed var(--border-light);">
                    <i data-lucide="database-zap" style="width:40px; height:40px; opacity:0.3; margin-bottom:12px;"></i>
                    <p>No managed intelligence profiles yet. <br>Analyze a VIN above to start building your fleet knowledge base.</p>
                </div>`;
            safeCreateIcons();
            return;
        }

        grid.innerHTML = data.map(v => `
            <div class="vin-dash-card fade-in">
                <div class="vin-dash-header">
                    <div class="vin-dash-title">
                        <h4>${v.brand || 'Unknown'} ${v.model || ''}</h4>
                        <code>${v.vin}</code>
                    </div>
                    <div class="vin-dash-actions">
                        <button class="icon-btn-small" onclick="openVehicleIntelByVin('${v.vin}')" title="Edit Profile"><i data-lucide="edit-3"></i></button>
                        <button class="icon-btn-small danger" onclick="deleteSavedVin('${v.vin}')" title="Delete Profile"><i data-lucide="trash-2"></i></button>
                    </div>
                </div>
                <div class="vin-dash-body">
                    <div class="vin-dash-item">
                        <span class="vin-dash-label">Year</span>
                        <span class="vin-dash-value">${v.year || 'N/A'}</span>
                    </div>
                    <div class="vin-dash-item">
                        <span class="vin-dash-label">Engine</span>
                        <span class="vin-dash-value">${v.engine || 'N/A'}</span>
                    </div>
                </div>
                <div class="vin-dash-footer">
                    <code style="font-size:0.6rem; color:var(--text-dim);">DB-REF: ${v.vin.substring(0, 8)}</code>
                </div>
            </div>
        `).join('');
        lucide.createIcons({ el: grid });
    } catch (e) {
        console.error("Dashboard load failed", e);
        showNotification("Intelligence node refresh failed.", "error");
    }
}

async function openVehicleIntelByVin(vin) {
    showNotification("Retrieving intelligence profile...", "info");
    try {
        const resp = await fetch(`/api/v1/vehicles/vin/${vin}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            const data = await resp.json();
            showVinAnalysisModal(data, vin);
        } else {
            showNotification("Failed to retrieve profile details.", "error");
        }
    } catch (e) {
        showNotification("Connectivity error.", "error");
    }
}

async function deleteSavedVin(vin) {
    if (!confirm(`Remove intelligence profile for ${vin} from dashboard?`)) return;
    try {
        const resp = await fetch(`/api/v1/vehicles/vin/${vin}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            showNotification("Profile removed.", "success");
            loadVinDashboard();
        }
    } catch (e) {
        showNotification("Failed to remove profile.", "error");
    }
}

function initVehicleIntel() {
    if (lifecycleChart) {
        try { lifecycleChart.resize(); } catch (e) { }
    }
    if (!selectedVehicle) {
        const noSel = document.getElementById('intel-no-selection');
        const mainGrid = document.getElementById('intel-main-grid');
        const banner = document.getElementById('intel-amber-banner');
        if (noSel) noSel.style.display = 'block';
        if (mainGrid) mainGrid.style.display = 'none';
        if (banner) banner.classList.add('vin-hidden');
        loadVinDashboard();
    } else {
        openVehicleIntel(selectedVehicle.name);
    }
}

async function updateVinFromIntel() {
    const vinInput = document.getElementById('intel-config-vin');
    const vin = (vinInput?.value || '').trim().toUpperCase();

    if (!currentIntelDeviceId) {
        showNotification('No vehicle selected for calibration.', 'error');
        return;
    }

    if (vin.length !== 17) {
        showNotification('A valid VIN must be exactly 17 characters.', 'warning');
        return;
    }

    try {
        const resp = await fetch(`/api/v1/vehicles/${currentIntelDeviceId}/vin`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ vin })
        });

        if (resp.ok) {
            showNotification('Intelligence profiling initiated. Full technical specs will populate shortly.', 'success');
            // Refresh after a small delay to allow backend to start processing
            setTimeout(() => loadVehicleIntel(currentIntelDeviceId), 1500);
        } else {
            const err = await resp.json();
            showNotification(err.detail || 'Failed to update VIN.', 'error');
        }
    } catch (e) {
        showNotification('Calibration node unreachable.', 'error');
    }
}

// ΓöÇΓöÇ Manual VIN Modal Logic ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

let activeVinDeviceId = null;

function triggerManualVinEntry(deviceId = null) {
    activeVinDeviceId = deviceId || currentIntelDeviceId || (selectedVehicle ? selectedVehicle.id : null);

    if (!activeVinDeviceId) {
        showNotification('Please select a vehicle first.', 'warning');
        return;
    }

    const modal = document.getElementById('vinEntryOverlay');
    const input = document.getElementById('vinInput');
    const errorMsg = document.getElementById('vinErrorMsg');
    const submitBtn = document.getElementById('vinSubmitBtn');

    if (modal) {
        modal.classList.remove('hidden-view');
        modal.style.display = 'flex';
    }

    if (input) {
        input.value = '';
        input.classList.remove('is-invalid');
        input.focus();
    }

    if (errorMsg) errorMsg.innerText = '';
    if (submitBtn) submitBtn.disabled = true;

    // Attach real-time validation
    input?.addEventListener('input', validateVinInput);
}

function closeVinModal() {
    const modal = document.getElementById('vinEntryOverlay');
    if (modal) {
        modal.classList.add('hidden-view');
        modal.style.display = 'none';
    }
    activeVinDeviceId = null;
}

function validateVinInput() {
    const input = document.getElementById('vinInput');
    const submitBtn = document.getElementById('vinSubmitBtn');
    const errorMsg = document.getElementById('vinErrorMsg');

    let vin = input.value.trim().toUpperCase();
    input.value = vin; // auto-uppercase

    // Remove invalid characters immediately
    vin = vin.replace(/[^A-HJ-NPR-Z0-9]/g, '');
    if (input.value !== vin) {
        input.value = vin;
    }

    const isValid = /^[A-HJ-NPR-Z0-9]{17}$/.test(vin);

    if (vin.length > 0 && vin.length < 17) {
        errorMsg.innerText = `${17 - vin.length} characters remaining...`;
        errorMsg.style.color = 'var(--text-dim)';
    } else if (vin.length === 17 && !isValid) {
        errorMsg.innerText = 'Invalid characters in VIN.';
        errorMsg.style.color = '#ef4444';
    } else {
        errorMsg.innerText = '';
    }

    submitBtn.disabled = !isValid;
}

async function submitManualVIN() {
    if (!activeVinDeviceId || !authToken) return;

    const vinInput = document.getElementById('vinInput');
    const vin = vinInput.value.trim().toUpperCase();
    const submitBtn = document.getElementById('vinSubmitBtn');

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px; display:inline-block;"></i> Saving...';
    safeCreateIcons();

    try {
        const resp = await fetch(`/api/v1/vehicles/${activeVinDeviceId}/vin`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ vin: vin })
        });

        const data = await resp.json();
        if (resp.ok) {
            showNotification('VIN updated successfully. Enrichment in progress...', 'success');
            closeVinModal();
            // Refresh the current view if it's the intel view
            if (activeVinDeviceId === currentIntelDeviceId) {
                setTimeout(() => loadVehicleIntel(activeVinDeviceId), 1500);
            }
        } else {
            showNotification(data.detail || 'Failed to update VIN.', 'error');
            submitBtn.disabled = false;
            submitBtn.innerText = 'Save Profiling Data';
        }
    } catch (err) {
        console.error('[VIN] Error submitting VIN:', err);
        showNotification('System error while saving VIN.', 'error');
        submitBtn.disabled = false;
        submitBtn.innerText = 'Save Profiling Data';
    }
}


// ── FLEET EXPLORER — MAP ENGINE ───────────────────────

const focState = {
    statusFilter: null,
    search: '',
    followVehicleId: null,
    selectedId: null,
    mapMode: 'dark',
};

function switchMapMode(mode) {
    if (!map) return;
    [darkLayer, lightLayer, standardLayer, satelliteLayer, terrainLayer, osmLayer].forEach(l => { if (l) map.removeLayer(l); });
    const layers = { dark: darkLayer, light: lightLayer, satellite: satelliteLayer, terrain: terrainLayer, osm: osmLayer };
    if (layers[mode]) map.addLayer(layers[mode]);
    focState.mapMode = mode;
}

function initMap() {
    if (map || !document.getElementById('live-map')) return;

    // Use OSM as default
    map = L.map('live-map', {
        zoomControl: false,
        attributionControl: false,
        fadeAnimation: true,
        markerZoomAnimation: true,
        worldCopyJump: true,
        maxZoom: 19
    }).setView([24.8607, 67.0011], 12);

    // Initialization of layers with proper OSM tiles
    osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19 
    });
    satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { 
        attribution: '&copy; Esri' 
    });
    terrainLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', { 
        attribution: '&copy; OpenTopoMap' 
    });
    darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { 
        attribution: '&copy; CartoDB' 
    });
    lightLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { 
        attribution: '&copy; CartoDB' 
    });

    // Default to OSM as requested
    osmLayer.addTo(map);
    focState.mapMode = 'osm';

    // Premium Clustering
    markerClusterGroup = L.markerClusterGroup({
        disableClusteringAtZoom: 16,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        maxClusterRadius: 40,
        polygonOptions: {
            fillColor: 'var(--brand-primary)',
            color: 'var(--brand-primary)',
            weight: 2,
            opacity: 0.3,
            fillOpacity: 0.1
        },
        iconCreateFunction: (cluster) => {
            const count = cluster.getChildCount();
            return L.divIcon({
                html: `<div class="foc-cluster-icon">${count}</div>`,
                className: '',
                iconSize: [42, 42],
                iconAnchor: [21, 21]
            });
        }
    });

    map.addLayer(markerClusterGroup);

    // Initialize Map-Specific Listeners
    initLmControls();
    initLmSearch();
    initLmFilters();

    // Trigger initial load – two calls to catch layout + font delays
    setTimeout(() => { map.invalidateSize(); }, 200);
    setTimeout(() => {
        map.invalidateSize();
        updateVehicleMarkers();
    }, 800);

    startMapUpdates();
}

function initLmControls() {
    const toggle = document.getElementById('fleet-panel-toggle');
    const panel = document.getElementById('fleet-panel');
    if (toggle && panel) {
        toggle.addEventListener('click', () => {
            panel.classList.toggle('collapsed');
            const icon = panel.classList.contains('collapsed') ? 'panel-left-open' : 'panel-left-close';
            toggle.querySelector('i')?.setAttribute('data-lucide', icon);
            lucide.createIcons({ el: toggle });
            setTimeout(() => map && map.invalidateSize(), 400);
        });
    }

    const layerToggle = document.getElementById('lm-layer-toggle');
    const layerMenu = document.getElementById('lm-layer-menu');
    if (layerToggle && layerMenu) {
        layerToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            layerMenu.classList.toggle('open');
        });
        document.addEventListener('click', () => layerMenu.classList.remove('open'));
    }
    const geoToggle = document.getElementById('toggle-geofences');
    if(geoToggle && window.geofenceLayer) {
        geoToggle.addEventListener('change', (e) => {
            if(e.target.checked) map.addLayer(geofenceLayer);
            else map.removeLayer(geofenceLayer);
        });
    }

}

function switchMapLayer(mode) {
    if (!map) return;
    const layers = { osm: osmLayer, satellite: satelliteLayer, terrain: terrainLayer, dark: darkLayer, light: lightLayer };
    
    // Remove all potentially active layers
    Object.values(layers).forEach(l => { if (l && map.hasLayer(l)) map.removeLayer(l); });
    
    if (layers[mode]) {
        map.addLayer(layers[mode]);
        focState.mapMode = mode;
        
        // Update UI
        document.querySelectorAll('.lm-layer-opt').forEach(opt => {
            opt.classList.toggle('active', opt.dataset.layer === mode);
        });
    }
    
    // Close menu
    document.getElementById('lm-layer-menu')?.classList.remove('open');
}

function locateMe() {
    if (!map) return;
    map.locate({setView: true, maxZoom: 16});
}

function resetMapView() {
    if (!map) return;
    map.flyTo([24.8607, 67.0011], 12, { duration: 1.5 });
}

function fitFleet() {
    if (!map || !Object.keys(markers).length) return;
    const group = new L.featureGroup(Object.values(markers));
    map.fitBounds(group.getBounds(), { padding: [50, 50], duration: 1 });
}



function toggleFollowMode() {
    if (!map || !focState.selectedId) return showNotification('Select a vehicle first to use Follow mode.', 'warning');
    const wasFollowing = !!focState.followVehicleId;
    focState.followVehicleId = wasFollowing ? null : focState.selectedId;
    const btn = document.getElementById('lm-follow-btn');
    if (!btn) return;
    if (focState.followVehicleId) {
        btn.innerHTML = `<i data-lucide="navigation" style="color:yellow;"></i> <span>Following...</span>`;
        if (markers[focState.followVehicleId]) {
            const ll = markers[focState.followVehicleId].getLatLng();
            map.flyTo(ll, 16, { duration: 0.5 });
        }
    } else {
        btn.innerHTML = `<i data-lucide="navigation"></i> <span>Follow vehicle</span>`;
    }
    if (typeof lucide !== 'undefined') lucide.createIcons({ el: btn });
}

function toggleMapFullscreen() {
    const layout = document.querySelector('.lm-layout');
    if (!document.fullscreenElement) {
        layout.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
}


function vehiclePassesFilter(v) {
    if (!v) return false;
    
    // Status Filter (focState.listFilter)
    if (focState.listFilter && focState.listFilter !== 'all') {
        const s = getVehicleStatus(v).class;
        if (s !== focState.listFilter && !(focState.listFilter === 'offline' && s === 'alert')) {
            return false;
        }
    }
    
    // Search Query (focState.searchQuery)
    if (focState.searchQuery && focState.searchQuery !== '') {
        const q = focState.searchQuery.toLowerCase();
        const name = formatVehicleDisplayName(v).toLowerCase();
        let driver = '';
        if (typeof formatDriverDisplayName === 'function') {
            driver = formatDriverDisplayName(v).toLowerCase();
        }
        const id = String(v.uniqueId || '').toLowerCase();
        
        if (!name.includes(q) && !driver.includes(q) && !id.includes(q)) {
            return false;
        }
    }
    
    return true;
}

function initLmSearch() {
    const input = document.getElementById('fleet-search');
    const mapInput = document.getElementById('map-area-search');
    
    const applySearch = (e) => {
        focState.searchQuery = e.target.value;
        renderLmVehicleList(latestVehicles);
        updateVehicleMarkers();
    };

    if (input) input.addEventListener('input', applySearch);
    if (mapInput) mapInput.addEventListener('input', applySearch);
}

function initLmFilters() {
    const filters = document.querySelectorAll('.lm-kpi');
    filters.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const target = e.currentTarget;
            if (!target.dataset.filter) return;
            
            filters.forEach(b => b.classList.remove('active'));
            target.classList.add('active');
            
            focState.listFilter = target.dataset.filter;
            
            // Re-render map markers and list 
            // Re-evaluating passes filter
            renderLmVehicleList(latestVehicles);
            updateVehicleMarkers();
        });
    });
}

async function updateVehicleMarkers() {
    if (!authToken || !map || !document.getElementById('view-map')?.classList.contains('active-view')) return;
    
    try {
        const resp = await fetch('/api/v1/vehicles/live?limit=5000', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const vehicles = await resp.json();
        latestVehicles = vehicles;

        updateLmKPIs(vehicles);
        renderLmVehicleList(vehicles);

        // Preserve current selection logic
        const prevSelectedId = focState.selectedId;

        markerClusterGroup.clearLayers();
        markers = {};

        vehicles.forEach(v => {
            if (!v.latitude || !v.longitude) return;
            if (!vehiclePassesFilter(v)) return;

            const status = getVehicleStatus(v);
            const name = formatVehicleDisplayName(v);
            const isSelected = prevSelectedId === v.id;

            const iconHtml = `
                <div class="foc-marker-wrap" id="marker-${v.id}">
                    <div class="foc-marker-modern ${status.class} ${isSelected ? 'selected' : ''}">
                        <img src="https://cdn-icons-png.flaticon.com/512/3204/3204121.png" alt="car" style="width: 24px; height: 24px;">
                    </div>
                    <div class="foc-marker-label">${name}</div>
                </div>`;

            const icon = L.divIcon({
                html: iconHtml,
                className: '',
                iconSize: [44, 44],
                iconAnchor: [22, 22]
            });

            const marker = L.marker([v.latitude, v.longitude], {
                icon,
                title: name,
                zIndexOffset: status.class === 'moving' ? 1000 : 0
            });

            // Tooltip (Hover)
            marker.bindTooltip(`
                <div class="lm-mini-tooltip">
                    <strong>${name}</strong><br/>
                    <span style="color:${status.color}">${status.label}</span> • ${v.speed.toFixed(1)} km/h
                </div>`, {
                direction: 'top',
                offset: [0, -10],
                opacity: 0.9,
                className: 'lm-tooltip-popup'
            });

            marker.on('click', () => {
                focState.selectedId = v.id;
                showLmPopup(v);
                map.flyTo([v.latitude, v.longitude], Math.max(map.getZoom(), 15), { duration: 0.8 });
                renderLmVehicleList(latestVehicles);
                highlightMarker(v.id);
            });

            markers[v.id] = marker;
            markerClusterGroup.addLayer(marker);
        });

        // Following logic
        if (focState.followVehicleId) {
            const fv = vehicles.find(v => v.id === focState.followVehicleId);
            if (fv && fv.latitude && fv.longitude) {
                map.panTo([fv.latitude, fv.longitude], { animate: true });
            }
        }

        lucide.createIcons();
    } catch (e) {
        console.error("Map Data Pipeline Error:", e);
    }
}

function highlightMarker(id) {
    Object.keys(markers).forEach(mid => {
        const el = markers[mid].getElement();
        if (!el) return;
        const dot = el.querySelector('.foc-marker-dot');
        if (dot) {
            if (parseInt(mid) === id) dot.classList.add('selected');
            else dot.classList.remove('selected');
        }
    });
}

function updateLmKPIs(vehicles) {
    let moving = 0, idle = 0, offline = 0;
    vehicles.forEach(v => {
        const s = getVehicleStatus(v);
        if (s.class === 'moving') moving++;
        else if (s.class === 'idle') idle++;
        else offline++;
    });
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('fleet-kpi-all', vehicles.length);
    set('fleet-kpi-online', vehicles.length - offline);
    set('fleet-kpi-moving', moving);
    set('fleet-kpi-idle', idle);
    set('fleet-kpi-offline', offline);
}

// ── MAP INTERACTIONS & GEOCODING ─────────────────

window.geoCache = {};
async function fetchReverseGeocode(lat, lon, elementId) {
    if (!lat || !lon) return;
    const cacheKey = `${lat.toFixed(4)},${lon.toFixed(4)}`;
    if (window.geoCache[cacheKey]) {
        const el = document.getElementById(elementId);
        if (el) el.textContent = window.geoCache[cacheKey];
        return;
    }
    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`);
        if(res.ok) {
            const data = await res.json();
            const addressStr = data.display_name || 'Unknown Address';
            window.geoCache[cacheKey] = addressStr;
            const el = document.getElementById(elementId);
            if (el) el.textContent = addressStr;
        }
    } catch(err) {
        console.error('Geocode err:', err);
    }
}

function followVehicleFromPopup() {
    if (!focState.selectedId) return;
    // Toggle follow: if already following same vehicle, stop it
    if (focState.followVehicleId === focState.selectedId) {
        focState.followVehicleId = null;
        const btn = document.getElementById('lm-follow-btn');
        if (btn) { btn.innerHTML = `<i data-lucide="navigation"></i> <span>Follow vehicle</span>`; if (typeof lucide !== 'undefined') lucide.createIcons({ el: btn }); }
        showNotification('Follow mode disabled.', 'info');
    } else {
        focState.followVehicleId = focState.selectedId;
        const btn = document.getElementById('lm-follow-btn');
        if (btn) { btn.innerHTML = `<i data-lucide="navigation" style="color:yellow;"></i> <span>Following...</span>`; if (typeof lucide !== 'undefined') lucide.createIcons({ el: btn }); }
        const v = latestVehicles.find(x => x.id === focState.selectedId);
        if (v && v.latitude && v.longitude && map) map.flyTo([v.latitude, v.longitude], 16, { duration: 0.8 });
        showNotification('Now following vehicle on map.', 'success');
    }
}

function openDetailsModalFromPopup() {
    if (focState.selectedId) {
        const v = latestVehicles.find(x => x.id === focState.selectedId);
        if(v) {
            openVehicleIntel(v.id);
        }
    }
}

function showRoutePlayback() {
    const v = latestVehicles.find(x => x.id === focState.selectedId);
    if (!v) { showNotification('Please select a vehicle first.', 'warning'); return; }

    const modal = document.getElementById('route-playback-modal');
    if (!modal) return;

    // Reset state
    _replayVehicle = v;
    _replayPositions = [];
    _replayIdx = 0;
    _replayPlaying = false;
    if (_replayInterval) clearInterval(_replayInterval);

    const titleEl = document.getElementById('replay-modal-title');
    if (titleEl) titleEl.textContent = `Route Playback — ${formatVehicleDisplayName(v)}`;

    // Default date range: yesterday
    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(0, 0, 0, 0);
    const todayEnd = new Date(now);
    todayEnd.setHours(23, 59, 0, 0);
    const toLocal = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    const fromEl = document.getElementById('replay-from');
    const toEl = document.getElementById('replay-to');
    if (fromEl) fromEl.value = toLocal(yesterday);
    if (toEl) toEl.value = toLocal(todayEnd);

    modal.style.display = 'flex';
    if (typeof lucide !== 'undefined') lucide.createIcons({ el: modal });

    // Init replay map if needed
    if (!_replayMap) {
        _replayMap = L.map('replay-map', { zoomControl: true }).setView([24.86, 67.0], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap',
            maxZoom: 19
        }).addTo(_replayMap);
    }
    setTimeout(() => _replayMap && _replayMap.invalidateSize(), 300);
}

function closeRoutePlayback() {
    const modal = document.getElementById('route-playback-modal');
    if (modal) modal.style.display = 'none';
    if (_replayInterval) { clearInterval(_replayInterval); _replayInterval = null; }
    _replayPlaying = false;
}

// -- Replay State --
let _replayVehicle = null;
let _replayPositions = [];
let _replayIdx = 0;
let _replayPlaying = false;
let _replayInterval = null;
let _replayMap = null;
let _replayPolyline = null;
let _replayMarker = null;
let _replayDonePolyline = null;

async function loadRoutePlayback() {
    if (!_replayVehicle) return;

    const fromEl = document.getElementById('replay-from');
    const toEl = document.getElementById('replay-to');
    const placeholder = document.getElementById('replay-placeholder');
    const controls = document.getElementById('replay-controls');
    const statsBar = document.getElementById('replay-stats-bar');

    const fromVal = fromEl?.value;
    const toVal = toEl?.value;
    if (!fromVal || !toVal) { showNotification('Please select a date range.', 'warning'); return; }

    if (placeholder) { placeholder.style.display = 'flex'; placeholder.innerHTML = '<div style="text-align:center"><div style="width:30px;height:30px;border:3px solid var(--fleet-border);border-top-color:var(--brand-primary);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 12px;"></div><p style="font-size:13px;font-weight:600;color:var(--fleet-text-sub);">Loading positions…</p></div>'; }
    if (controls) controls.style.display = 'none';
    if (statsBar) statsBar.innerHTML = '';

    // Stop any running playback
    if (_replayInterval) { clearInterval(_replayInterval); _replayInterval = null; }
    _replayPlaying = false;

    try {
        const from = new Date(fromVal).toISOString();
        const to = new Date(toVal).toISOString();
        const url = `/api/v1/vehicles/positions?deviceId=${_replayVehicle.id}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
        const res = await fetch(url, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
        const positions = await res.json();

        if (!Array.isArray(positions) || positions.length < 2) {
            if (placeholder) { placeholder.style.display = 'flex'; placeholder.innerHTML = '<div style="text-align:center"><i data-lucide="map-off" style="width:40px;height:40px;opacity:0.3;margin-bottom:8px;"></i><p style="font-size:13px;font-weight:600;opacity:0.6;">No GPS data found for this period</p></div>'; if (typeof lucide !== 'undefined') lucide.createIcons({ el: placeholder }); }
            return;
        }

        _replayPositions = positions;
        _replayIdx = 0;

        // Clear old layers
        if (_replayPolyline) _replayMap.removeLayer(_replayPolyline);
        if (_replayMarker) _replayMap.removeLayer(_replayMarker);
        if (_replayDonePolyline) _replayMap.removeLayer(_replayDonePolyline);

        // Draw full faded trail
        const allLatLngs = positions.map(p => [p.latitude, p.longitude]);
        _replayPolyline = L.polyline(allLatLngs, { color: '#94a3b8', weight: 2, opacity: 0.35, dashArray: '4,4' }).addTo(_replayMap);
        _replayDonePolyline = L.polyline([], { color: '#2563eb', weight: 3, opacity: 0.85 }).addTo(_replayMap);

        // Start/End markers
        const startPos = positions[0];
        const endPos = positions[positions.length - 1];
        L.marker([startPos.latitude, startPos.longitude], { icon: L.divIcon({ html: '<div style="background:#10b981;width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);"></div>', className: '', iconSize: [12, 12], iconAnchor: [6, 6] }) }).bindTooltip('Start').addTo(_replayMap);
        L.marker([endPos.latitude, endPos.longitude], { icon: L.divIcon({ html: '<div style="background:#ef4444;width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);"></div>', className: '', iconSize: [12, 12], iconAnchor: [6, 6] }) }).bindTooltip('End').addTo(_replayMap);

        // Moving marker
        _replayMarker = L.marker([startPos.latitude, startPos.longitude], { icon: L.divIcon({ html: '<div style="background:#2563eb;width:14px;height:14px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(37,99,235,0.6);"></div>', className: '', iconSize: [14, 14], iconAnchor: [7, 7] }) }).addTo(_replayMap);

        _replayMap.fitBounds(_replayPolyline.getBounds(), { padding: [30, 30] });

        // Stats
        const totalKm = positions.reduce((sum, _, i) => {
            if (i === 0) return 0;
            const a = positions[i - 1], b = positions[i];
            const R = 6371, dLat = (b.latitude - a.latitude) * Math.PI / 180, dLon = (b.longitude - a.longitude) * Math.PI / 180;
            const aa = Math.sin(dLat / 2) ** 2 + Math.cos(a.latitude * Math.PI / 180) * Math.cos(b.latitude * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
            return sum + R * 2 * Math.atan2(Math.sqrt(aa), Math.sqrt(1 - aa));
        }, 0);
        const maxSpeed = Math.max(...positions.map(p => p.speed || 0));
        const dur = (new Date(endPos.fixTime) - new Date(startPos.fixTime)) / 60000;

        if (statsBar) statsBar.innerHTML = `
            <div style="display:flex;align-items:center;gap:6px;"><span style="font-size:11px;color:var(--fleet-text-sub);font-weight:600;">Points:</span><span style="font-size:13px;font-weight:800;color:var(--fleet-text-main);">${positions.length.toLocaleString()}</span></div>
            <div style="display:flex;align-items:center;gap:6px;"><span style="font-size:11px;color:var(--fleet-text-sub);font-weight:600;">Distance:</span><span style="font-size:13px;font-weight:800;color:var(--brand-primary);">${totalKm.toFixed(1)} km</span></div>
            <div style="display:flex;align-items:center;gap:6px;"><span style="font-size:11px;color:var(--fleet-text-sub);font-weight:600;">Max Speed:</span><span style="font-size:13px;font-weight:800;color:var(--brand-warning);">${(maxSpeed * 1.852).toFixed(0)} km/h</span></div>
            <div style="display:flex;align-items:center;gap:6px;"><span style="font-size:11px;color:var(--fleet-text-sub);font-weight:600;">Duration:</span><span style="font-size:13px;font-weight:800;color:var(--fleet-text-main);">${Math.floor(dur / 60)}h ${Math.round(dur % 60)}m</span></div>
        `;

        // Setup slider & controls
        const slider = document.getElementById('replay-slider');
        if (slider) { slider.max = positions.length - 1; slider.value = 0; }
        updateReplayTimeLabel(0);

        if (placeholder) placeholder.style.display = 'none';
        if (controls) { controls.style.display = 'flex'; if (typeof lucide !== 'undefined') lucide.createIcons({ el: controls }); }

        // Reset play icon
        const icon = document.getElementById('replay-play-icon');
        if (icon) icon.setAttribute('data-lucide', 'play');
        if (typeof lucide !== 'undefined' && icon) lucide.createIcons({ el: icon.parentElement });

    } catch (err) {
        console.error('[Replay]', err);
        if (placeholder) { placeholder.style.display = 'flex'; placeholder.innerHTML = `<p style="color:var(--brand-danger);font-size:13px;font-weight:600;">Error: ${err.message}</p>`; }
    }
}

function updateReplayTimeLabel(idx) {
    const el = document.getElementById('replay-time-label');
    if (!el || !_replayPositions[idx]) return;
    const t = new Date(_replayPositions[idx].fixTime);
    el.textContent = t.toLocaleString('en-PK', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function onReplaySliderChange() {
    const slider = document.getElementById('replay-slider');
    if (!slider) return;
    _replayIdx = parseInt(slider.value);
    seekReplayTo(_replayIdx);
}

function seekReplayTo(idx) {
    if (!_replayPositions[idx]) return;
    const pos = _replayPositions[idx];
    const latLng = [pos.latitude, pos.longitude];
    if (_replayMarker) _replayMarker.setLatLng(latLng);
    if (_replayDonePolyline) _replayDonePolyline.setLatLngs(_replayPositions.slice(0, idx + 1).map(p => [p.latitude, p.longitude]));
    updateReplayTimeLabel(idx);
}

function toggleReplayPlayback() {
    if (_replayPositions.length < 2) return;
    _replayPlaying = !_replayPlaying;
    const icon = document.getElementById('replay-play-icon');
    if (icon) { icon.setAttribute('data-lucide', _replayPlaying ? 'pause' : 'play'); if (typeof lucide !== 'undefined') lucide.createIcons({ el: icon.parentElement }); }

    if (_replayPlaying) {
        if (_replayIdx >= _replayPositions.length - 1) _replayIdx = 0;
        const advance = () => {
            if (!_replayPlaying || _replayIdx >= _replayPositions.length - 1) {
                _replayPlaying = false;
                if (icon) { icon.setAttribute('data-lucide', 'play'); if (typeof lucide !== 'undefined') lucide.createIcons({ el: icon.parentElement }); }
                return;
            }
            _replayIdx++;
            const slider = document.getElementById('replay-slider');
            if (slider) slider.value = _replayIdx;
            seekReplayTo(_replayIdx);
            const speed = parseInt(document.getElementById('replay-speed')?.value || 10);
            const interval = Math.max(50, 1000 / speed);
            _replayInterval = setTimeout(advance, interval);
        };
        const speed = parseInt(document.getElementById('replay-speed')?.value || 10);
        _replayInterval = setTimeout(advance, Math.max(50, 1000 / speed));
    } else {
        if (_replayInterval) { clearTimeout(_replayInterval); _replayInterval = null; }
    }
}

function replayGoToStart() {
    _replayIdx = 0;
    seekReplayTo(0);
    const slider = document.getElementById('replay-slider');
    if (slider) slider.value = 0;
}

function replayGoToEnd() {
    _replayIdx = _replayPositions.length - 1;
    seekReplayTo(_replayIdx);
    const slider = document.getElementById('replay-slider');
    if (slider) slider.value = _replayIdx;
}

// Ensure toggles listen continuously - real implementations
document.addEventListener('DOMContentLoaded', () => {
    const geo = document.getElementById('toggle-geofences');
    if (geo) {
        // Real geofence toggle is handled in initLmControls once map is ready
        // This is a fallback notification
        geo.addEventListener('change', (e) => {
            if (map && window.geofenceLayer) {
                if (e.target.checked) map.addLayer(geofenceLayer);
                else map.removeLayer(geofenceLayer);
            }
        });
    }
    const traf = document.getElementById('toggle-traffic');
    if (traf) {
        let trafficLayer = null;
        traf.addEventListener('change', (e) => {
            if (!map) return;
            if (e.target.checked) {
                // OpenStreetMap has no free traffic layer; use a general road highlight via CartoDB
                trafficLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
                    attribution: '© CartoDB',
                    maxZoom: 19,
                    opacity: 0.7
                });
                map.addLayer(trafficLayer);
                showNotification('Road layer overlay enabled.', 'info');
            } else {
                if (trafficLayer) { map.removeLayer(trafficLayer); trafficLayer = null; }
                showNotification('Road layer overlay disabled.', 'info');
            }
        });
    }
});

// ── FLOATING POPUP CARD ─────────────────────────────

function showLmPopup(vehicle) {
    const popup = document.getElementById('vehicle-popup-card');
    if (!popup || !vehicle) return;

    const status = getVehicleStatus(vehicle);
    const name = formatVehicleDisplayName(vehicle);
    const speed = vehicle.speed ? `${vehicle.speed.toFixed(1)} km/h` : '--';
    const ignition = vehicle.attributes?.ignition ? 'ON' : 'OFF';
    const fuel = vehicle.attributes?.fuelLevel != null ? `${vehicle.attributes.fuelLevel}%` : '--';
    const battery = vehicle.attributes?.batteryLevel != null ? `${vehicle.attributes.batteryLevel}%` :
                   vehicle.attributes?.power ? `${vehicle.attributes.power}V` : '--';
    const lastUpdate = vehicle.lastUpdate ? timeAgo(new Date(vehicle.lastUpdate)) : '--';
    const address = vehicle.address || 'Resolving Location...';
    
    // Trigger lazy reverse geocode if no address
    if (!vehicle.address && vehicle.latitude && vehicle.longitude) {
        fetchReverseGeocode(vehicle.latitude, vehicle.longitude, 'popup-address');
    }
    
    const todayDistance = vehicle.attributes?.todayDistance ?
                        `${(vehicle.attributes.todayDistance / 1000).toFixed(1)} km` : '-- km';
    const lat = vehicle.latitude ? vehicle.latitude.toFixed(6) : '--';
    const lon = vehicle.longitude ? vehicle.longitude.toFixed(6) : '--';
    const coords = vehicle.latitude && vehicle.longitude ? `${lat}, ${lon}` : '--';
    const rssi = vehicle.attributes?.rssi || vehicle.attributes?.signal || 0;
    let signalText = '--';
    if (rssi > 20) signalText = 'Strong';
    else if (rssi > 10) signalText = 'Moderate';
    else if (rssi > 0) signalText = 'Weak';
    const gpsText = vehicle.valid ? 'Active' : 'Lost';
    const driveTime = vehicle.attributes?.driveTime ? formatDuration(vehicle.attributes.driveTime) : '--';
    const idleTime = vehicle.attributes?.idleTime ? formatDuration(vehicle.attributes.idleTime) : '--';
    const stops = vehicle.attributes?.stops != null ? vehicle.attributes.stops : '--';
    const vin = vehicle.vin || vehicle.attributes?.vin || '--';
    const manufacturer = vehicle.attributes?.manufacturer || vehicle.make || '--';
    const model = vehicle.model || '--';
    const healthScore = computeHealthScore(vehicle);

    const setText = (id, val, color) => {
        const el = document.getElementById(id);
        if (el) { el.textContent = val; if (color) el.style.color = color; }
    };

    setText('popup-vehicle-name', name);
    setText('popup-vehicle-plate', vehicle.uniqueId || '');

    const statusText = document.getElementById('popup-status-text');
    if (statusText) { statusText.textContent = status.label; statusText.style.color = status.color; }

    const statusBadge = document.getElementById('popup-vehicle-status');
    if (statusBadge) {
        const dot = statusBadge.querySelector('.lm-popup-dot');
        if (dot) dot.style.background = status.color;
    }

    setText('popup-speed', speed);
    setText('popup-ignition', ignition, vehicle.attributes?.ignition ? '#22c55e' : '#ef4444');
    setText('popup-fuel', fuel);
    setText('popup-battery', battery);
    setText('popup-signal', signalText);
    setText('popup-gps', gpsText, vehicle.valid ? '#22c55e' : '#ef4444');
    setText('popup-address', address);
    setText('popup-coords', coords);
    setText('popup-last-update', lastUpdate);
    setText('popup-distance', todayDistance);
    setText('popup-drive-time', driveTime);
    setText('popup-idle-time', idleTime);
    setText('popup-stops', stops);
    setText('popup-vin', vin);
    setText('popup-manufacturer', manufacturer);
    setText('popup-model', model);
    setText('popup-health', healthScore != null ? `${healthScore}%` : '--');

    popup.style.display = 'flex';
    lucide.createIcons({ el: popup });
}

function closeVehiclePopup() {
    const popup = document.getElementById('vehicle-popup-card');
    if (popup) popup.style.display = 'none';
    focState.selectedId = null;
    highlightMarker(null);
    renderLmVehicleList(latestVehicles);
}

function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '0m';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

function computeHealthScore(v) {
    let score = 100;
    if (v.attributes?.batteryLevel != null && v.attributes.batteryLevel < 20) score -= 15;
    if (v.attributes?.fuelLevel != null && v.attributes.fuelLevel < 15) score -= 10;
    if (v.attributes?.alarm) score -= 20;
    if (!v.valid) score -= 15;
    const rssi = v.attributes?.rssi || v.attributes?.signal || 0;
    if (rssi > 0 && rssi < 10) score -= 10;
    return Math.max(0, Math.min(100, score));
}

// ── VEHICLE LIST ────────────────────────────────────

function renderLmVehicleList(vehicles) {
    const list = document.getElementById('fleet-vehicle-list');
    if (!list) return;

    const filtered = vehicles.filter(v => vehiclePassesFilter(v));

    if (filtered.length === 0) {
        list.innerHTML = '<div style="text-align:center; padding:40px 16px; color:var(--fleet-text-muted); font-size:0.78rem;">No vehicles found.</div>';
        return;
    }

    list.innerHTML = filtered.map(v => {
        const status = getVehicleStatus(v);
        const name = formatVehicleDisplayName(v);
        const isSelected = focState.selectedId === v.id;
        const speed = v.speed ? v.speed.toFixed(0) : '0';
        const address = v.address || 'Locating...';
        const rssi = v.attributes?.rssi || v.attributes?.signal || 0;
        
        let sigClass1 = rssi > 0 ? 'active' : '';
        let sigClass2 = rssi > 10 ? 'active' : '';
        let sigClass3 = rssi > 15 ? 'active' : '';
        let sigClass4 = rssi > 20 ? 'active' : '';

        // Match the mockup badge classes (moving, online, idle, offline)
        let badgeClass = status.class;
        if (badgeClass === 'alert') badgeClass = 'offline'; // fallback

        // Fallback or generic thumb icon
        let thumbContent = `<i data-lucide="truck"></i>`;

        return `
        <div class="lm-v-item ${isSelected ? 'active' : ''}" onclick="selectVehicleOnMap(${v.id})">
            <div class="lm-v-thumb">
                ${thumbContent}
            </div>
            <div class="lm-v-main">
                <div class="lm-v-top">
                    <div class="lm-v-name">${name}</div>
                    <div class="lm-v-status-badge ${badgeClass}">${status.label}</div>
                </div>
                <div class="lm-v-details">
                    <div class="lm-v-detail">Speed: ${speed} km/h</div>
                    <div class="lm-v-detail">${address}</div>
                </div>
                <div class="lm-v-meta">
                    <div class="lm-v-signal" title="Signal Strength">
                        <span class="${sigClass1}"></span>
                        <span class="${sigClass2}"></span>
                        <span class="${sigClass3}"></span>
                        <span class="${sigClass4}"></span>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');

    setTimeout(() => {
        lucide.createIcons({
            root: list
        });
    }, 10);
}

function selectVehicleOnMap(id) {
    const v = latestVehicles.find(veh => veh.id === id);
    if (!v || !map) return;
    focState.selectedId = id;
    map.flyTo([v.latitude, v.longitude], Math.max(map.getZoom(), 14), { duration: 0.8 });
    showLmPopup(v);
    highlightMarker(id);
    renderLmVehicleList(latestVehicles);
}

function toggleAlertFocus() {
    const btn = document.getElementById('lm-alert-btn');
    if (focState.statusFilter === 'alert') {
        focState.statusFilter = null;
        if (btn) btn.classList.remove('active');
        document.querySelectorAll('.lm-kpi').forEach(b => b.classList.remove('active'));
        document.querySelector('.lm-kpi[data-filter="all"]')?.classList.add('active');
    } else {
        focState.statusFilter = 'alert';
        if (btn) btn.classList.add('active');
        document.querySelectorAll('.lm-kpi').forEach(b => b.classList.remove('active'));
        document.querySelector('.lm-kpi[data-filter="alert"]')?.classList.add('active');
    }
    renderLmVehicleList(latestVehicles);
}

function refreshFleet() {
    showNotification("Refreshing Fleet Intelligence...", "info");
    updateVehicleMarkers();
}

// ── VEHICLE DETAILS MODAL ───────────────────────────

let selectedVehicleIdForDetails = null;

function openDetailsModal(id) {
    const v = latestVehicles.find(veh => veh.id === id);
    if (!v) return;
    selectedVehicleIdForDetails = id;

    document.getElementById('det-name').innerText = v.name || 'Unknown';
    document.getElementById('det-uid').innerText = v.uniqueId || 'N/A';
    document.getElementById('det-vin').innerText = v.vin || v.attributes?.vin || 'N/A';
    document.getElementById('det-model').innerText = v.model || 'N/A';
    document.getElementById('det-category').innerText = v.category || 'N/A';
    document.getElementById('det-group').innerText = v.groupId || 'Default';
    document.getElementById('det-driver').innerText = v.contact || 'Not Assigned';
    document.getElementById('det-phone').innerText = v.phone || 'N/A';

    const fuelMethod = v.attributes?.fuelMethod || 'estimated';
    const fuelLabel = fuelMethod === 'sensor' ? 'Verified' : 'AI-Est';
    const fuelColor = fuelMethod === 'sensor' ? 'var(--brand-success)' : 'var(--brand-warning)';

    document.getElementById('det-speed').innerText = `${(v.speed || 0).toFixed(1)} km/h`;
    document.getElementById('det-ignition').innerText = v.attributes?.ignition ? 'ON' : 'OFF';
    document.getElementById('det-fuel').innerHTML = v.attributes?.fuelLevel ?
        `${v.attributes.fuelLevel}% <span style="font-size:0.6rem; padding:2px 6px; border-radius:4px; background:${fuelColor}20; color:${fuelColor}; margin-left:8px; border:1px solid ${fuelColor}40;">${fuelLabel}</span>` : 'N/A';
    document.getElementById('det-odometer').innerText = `${((v.attributes?.totalDistance || 0) / 1000).toFixed(1)} km`;
    document.getElementById('det-altitude').innerText = `${(v.altitude || 0).toFixed(0)} m`;
    document.getElementById('det-course').innerText = `${(v.course || 0)}°`;

    document.getElementById('det-voltage').innerText = v.attributes?.batteryLevel ? `${v.attributes.batteryLevel}%` : (v.attributes?.power ? `${v.attributes.power}V` : 'N/A');
    document.getElementById('det-last-update').innerText = v.lastUpdate ? new Date(v.lastUpdate).toLocaleString() : 'N/A';

    const gpsStatus = v.valid ? 'Active' : 'Lost / Invalid';
    document.getElementById('det-gps').innerText = gpsStatus;
    document.getElementById('det-gps').style.color = v.valid ? 'var(--brand-success)' : 'var(--brand-danger)';

    const rssi = v.attributes?.rssi || v.attributes?.signal || 0;
    let signalText = 'N/A', signalColor = 'var(--text-dim)';
    if (rssi > 0) {
        if (rssi > 20) { signalText = 'Strong'; signalColor = 'var(--brand-success)'; }
        else if (rssi > 10) { signalText = 'Moderate'; signalColor = 'var(--brand-warning)'; }
        else { signalText = 'Weak'; signalColor = 'var(--brand-danger)'; }
    }
    document.getElementById('det-gsm').innerText = signalText;
    document.getElementById('det-gsm').style.color = signalColor;

    const detailsModal = document.getElementById('vehicle-details-modal');
    detailsModal.classList.remove('hidden-view');
    detailsModal.style.display = 'flex';
    safeCreateIcons();
}

function closeDetailsModal() {
    const detailsModal = document.getElementById('vehicle-details-modal');
    detailsModal.classList.add('hidden-view');
    detailsModal.style.display = 'none';
}

function focusVehicleOnMap(deviceId) {
    if (deviceId) {
        const v = latestVehicles.find(x => String(x.id) === String(deviceId));
        if (v && v.latitude && v.longitude) {
            map.setView([v.latitude, v.longitude], 16);
            if (markers[v.id]) markers[v.id].fire('click');
        }
    } else if (selectedVehicleIdForDetails) {
        const v = latestVehicles.find(veh => veh.id === selectedVehicleIdForDetails);
        if (v) selectVehicleOnMap(v.id);
    }
}

// -----------------------------------------
// VEHICLE EDIT MODAL LOGIC
// -----------------------------------------
function openEditModal(id) {
    const v = latestVehicles.find(veh => veh.id === id);
    if (!v) return;

    document.getElementById('edit-vehicle-id').value = v.id;
    document.getElementById('edit-vehicle-name').value = v.name || '';
    document.getElementById('edit-vehicle-uid').value = v.uniqueId || '';
    document.getElementById('edit-vehicle-vin').value = v.vin || v.attributes?.vin || '';
    document.getElementById('edit-vehicle-model').value = v.model || '';
    document.getElementById('edit-vehicle-category').value = v.category || 'car';
    const groupEl = document.getElementById('edit-vehicle-group');
    const phoneEl = document.getElementById('edit-vehicle-phone');
    const notesEl = document.getElementById('edit-vehicle-notes');
    document.getElementById('edit-vehicle-contact').value = v.contact || '';
    if (groupEl) groupEl.value = v.groupId || '';
    if (phoneEl) phoneEl.value = v.phone || '';
    if (notesEl) notesEl.value = v.attributes?.notes || '';

    const editModal = document.getElementById('edit-vehicle-modal');
    editModal.classList.remove('hidden-view');
    editModal.style.display = 'flex';
    lucide.createIcons({ el: editModal });
}

function closeEditModal() {
    document.getElementById('edit-vehicle-modal').classList.add('hidden-view');
}

document.getElementById('edit-vehicle-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-vehicle-id').value;
    const groupEl = document.getElementById('edit-vehicle-group');
    const phoneEl = document.getElementById('edit-vehicle-phone');
    const notesEl = document.getElementById('edit-vehicle-notes');
    const data = {
        name: document.getElementById('edit-vehicle-name').value,
        uniqueid: document.getElementById('edit-vehicle-uid').value,
        vin: document.getElementById('edit-vehicle-vin').value,
        model: document.getElementById('edit-vehicle-model').value,
        category: document.getElementById('edit-vehicle-category').value,
        groupId: groupEl ? (parseInt(groupEl.value, 10) || 0) : 0,
        contact: document.getElementById('edit-vehicle-contact').value,
        phone: phoneEl ? phoneEl.value : '',
        attributes: {
            notes: notesEl ? notesEl.value : ''
        }
    };

    const btn = e.submitter || document.querySelector('#edit-vehicle-form .auth-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span>Saving...</span> <i data-lucide="loader-2" class="spin"></i>`;
    lucide.createIcons({ el: btn });

    try {
        const resp = await fetch(`/api/v1/vehicles/${id}`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (resp.ok) {
            showNotification("Vehicle intelligence updated successfully", "success");
            closeEditModal();
            updateVehicleMarkers();
        } else {
            const err = await resp.json();
            showNotification(err.error || "Intelligence update failed", "error");
        }
    } catch (e) {
        showNotification("Security node unreachable", "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
        lucide.createIcons({ el: btn });
    }
});

function showOnMap(lat, lon, name, id) {
    const mapNav = document.querySelector('.nav-item[data-view="map"]');
    if (mapNav) mapNav.click();

    // Smooth transition
    setTimeout(() => {
        if (map) {
            // High-precision zoom for tactical target
            map.flyTo([lat, lon], 17);

            // Search marker by ID for precision
            if (id && markers[id]) {
                const marker = markers[id];
                // If marker is in a cluster, zoom to it then open popup
                if (markerClusterGroup) {
                    markerClusterGroup.zoomToShowLayer(marker, () => {
                        marker.openPopup();
                    });
                } else {
                    marker.openPopup();
                }
            } else {
                // Precision fallback: search by location if ID fails
                for (let mid in markers) {
                    const mPos = markers[mid].getLatLng();
                    if (Math.abs(mPos.lat - lat) < 0.0001 && Math.abs(mPos.lng - lon) < 0.0001) {
                        if (markerClusterGroup) {
                            markerClusterGroup.zoomToShowLayer(markers[mid], () => markers[mid].openPopup());
                        } else {
                            markers[mid].openPopup();
                        }
                        break;
                    }
                }
            }
        }
    }, 500);
}

// -----------------------------------------
// CORE INITIALIZATION
// -----------------------------------------
function checkAuthState() {
    if (!loginView || !appView) initAuthElements();
    if (!loginView || !appView) {
        console.error("Auth Views missing from DOM");
        return;
    }

    if (authToken) {
        loginView.classList.replace('active-view', 'hidden-view');
        loginView.classList.add('hidden-view'); // Force it if replace fails
        appView.classList.replace('hidden-view', 'active-view');
        appView.classList.add('active-view'); // Force it if replace fails
        // Apply Role-Based Access
        if (roleText) {
            roleText.innerText = userRole || 'USER';
        }
        if (roleDisplay) roleDisplay.style.color = (userRole === 'SUPERADMIN' || userRole === 'ADMIN') ? 'var(--brand-success)' : 'var(--brand-primary)';

        userNameDisplay.innerText = userName || 'Operator';
        setupRoleUI();
        loadDashboardData();
        loadChatHistory();
        loadVinDashboard();
        loadAlertPreferences();
        startAlertsPolling();

        // If map is already the active view (e.g. after refresh), init it
        if (document.getElementById('view-map').classList.contains('active-view')) {
            setTimeout(() => {
                initMap();
                if (map) map.invalidateSize();
                startMapUpdates();
            }, 500);
        }
    } else {
        appView.classList.replace('active-view', 'hidden-view');
        appView.classList.add('hidden-view');
        loginView.classList.replace('hidden-view', 'active-view');
        loginView.classList.add('active-view');
        stopMapUpdates();
    }
}

function setupRoleUI() {
    const navItems = document.querySelectorAll('#main-nav-menu .nav-item');
    navItems.forEach(item => {
        item.style.display = 'flex';
    });

    // Show sync buttons only for Admins
    const manualSyncBtn = document.getElementById('manual-pc12-sync-btn');
    const isAdmin = userRole === 'SUPERADMIN' || userRole === 'ADMIN';

    if (adminSyncBtn) adminSyncBtn.style.display = isAdmin ? 'inline-flex' : 'none';
    if (manualSyncBtn) manualSyncBtn.style.display = isAdmin ? 'flex' : 'none';

    // Show FDB upload button for all authenticated users
    const fdbBtn = document.getElementById('fdb-upload-btn');
    if (fdbBtn) {
        fdbBtn.style.display = 'flex';
        safeCreateIcons();
    }
}

function applySavedTheme() {
    const savedTheme = localStorage.getItem('fleet_theme');
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
    const shouldUseLight = savedTheme ? savedTheme === 'light' : prefersLight;
    document.body.classList.toggle('light-theme', shouldUseLight);
    document.body.setAttribute('data-theme', shouldUseLight ? 'light' : 'dark');

    const icon = document.querySelector('#global-theme-toggle i');
    if (icon) {
        icon.setAttribute('data-lucide', shouldUseLight ? 'moon' : 'sun');
    }

    // Task 3: Sync Map Theme on apply
    if (map) {
        if (shouldUseLight) switchMapMode('light');
        else switchMapMode('dark');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initAuthElements();
    
    try {
        applySavedTheme();
    } catch (e) { console.error("Theme init error:", e); }
    
    try {
        checkAuthState();
    } catch (e) { console.error("Auth init error:", e); }
    safeCreateIcons();

    // Global Theme Toggle
    document.getElementById('global-theme-toggle')?.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const isLight = document.body.classList.contains('light-theme');
        document.body.setAttribute('data-theme', isLight ? 'light' : 'dark');
        localStorage.setItem('fleet_theme', isLight ? 'light' : 'dark');

        // Update icon
        const icon = document.querySelector('#global-theme-toggle i');
        if (icon) {
            icon.setAttribute('data-lucide', isLight ? 'moon' : 'sun');
            safeCreateIcons();
        }

        // Sync with Map if needed
        if (isLight && typeof switchMapMode === 'function') {
            switchMapMode('light');
        } else if (!isLight && typeof switchMapMode === 'function') {
            switchMapMode('dark');
        }
    });

    // Global Sidebar Toggle
    document.getElementById('toggle-sidebar')?.addEventListener('click', () => {
        const sidebar = document.getElementById('sidebar');
        const icon = document.querySelector('#toggle-sidebar i');
        sidebar.classList.toggle('minimized');

        // Tooltip logic for minimized state
        const navItems = document.querySelectorAll('.nav-item');
        if (sidebar.classList.contains('minimized')) {
            navItems.forEach(item => {
                const text = item.querySelector('span').innerText;
                item.setAttribute('title', text);
            });
        } else {
            navItems.forEach(item => item.removeAttribute('title'));
        }

        setTimeout(() => {
            if (map) map.invalidateSize();
            if (velocityChart) velocityChart.resize();
            if (statusDonutChart) statusDonutChart.resize();
        }, 400);
    });

    // ── Global Search ──────────────────────────────────────
    const searchInput = document.getElementById('header-search-input');
    const searchDropdown = document.getElementById('header-search-dropdown');
    const searchWrap = document.getElementById('header-search-wrap');

    if (searchInput && searchDropdown) {
        searchInput.addEventListener('input', function() {
            const q = this.value.trim().toLowerCase();
            if (!q || !latestVehicles.length) {
                searchDropdown.style.display = 'none';
                return;
            }
            const matches = latestVehicles.filter(v =>
                (v.name || '').toLowerCase().includes(q) ||
                (v.uniqueId || '').toLowerCase().includes(q) ||
                (v.vin || '').toLowerCase().includes(q)
            ).slice(0, 8);
            if (!matches.length) {
                searchDropdown.innerHTML = '<div class="search-dropdown-empty">No results found</div>';
                searchDropdown.style.display = 'block';
                return;
            }
            searchDropdown.innerHTML = matches.map(v => {
                const status = getVehicleStatus(v);
                return `<div class="search-dropdown-item" data-id="${v.id}">
                    <i data-lucide="truck"></i>
                    <span>${formatVehicleDisplayName(v)}</span>
                    <span style="margin-left:auto; font-size:0.7rem; color:${status.color};">${status.label}</span>
                </div>`;
            }).join('');
            searchDropdown.style.display = 'block';
            lucide.createIcons({ el: searchDropdown });
            searchDropdown.querySelectorAll('.search-dropdown-item').forEach(item => {
                item.addEventListener('click', () => {
                    const id = parseInt(item.dataset.id);
                    const vehicle = latestVehicles.find(v => v.id === id);
                    if (vehicle) {
                        searchInput.value = formatVehicleDisplayName(vehicle);
                        searchDropdown.style.display = 'none';
                        const matrixSearch = document.getElementById('matrix-search-input');
                        if (matrixSearch) {
                            matrixSearch.value = formatVehicleDisplayName(vehicle);
                            filterMatrixTable();
                            document.querySelector('[data-view="analytics"]')?.click();
                        }
                    }
                });
            });
        });

        searchInput.addEventListener('blur', () => {
            setTimeout(() => { searchDropdown.style.display = 'none'; }, 200);
        });

        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim() && latestVehicles.length) {
                searchInput.dispatchEvent(new Event('input'));
            }
        });
    }

    // Keyboard shortcut "/" to focus search
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
            e.preventDefault();
            searchInput?.focus();
        }
    });

    // ── Notification Sidebar ──────────────────────────────────
    const notifBtn = document.getElementById('notif-bell-btn');
    const notifSidebar = document.getElementById('notif-sidebar');
    const notifClearAll = document.getElementById('notif-clear-all');

    if (notifBtn) {
        notifBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (!notifSidebar) return;
            const isOpen = notifSidebar.classList.contains('open');
            if (!isOpen) {
                populateNotifFromVehicles();
                renderNotifSidebar();
            }
            notifSidebar.classList.toggle('open');
        });
    }

    if (notifSidebar) {
        notifSidebar.addEventListener('click', function(e) { e.stopPropagation(); });
    }

    document.addEventListener('click', function() {
        if (notifSidebar) notifSidebar.classList.remove('open');
    });

    document.querySelectorAll('.notif-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.notif-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            notifFilter = this.dataset.tab;
            renderNotifSidebar();
        });
    });

    if (notifClearAll) {
        notifClearAll.addEventListener('click', function() {
            notifications = [];
            renderNotifSidebar();
            updateNotifBadge();
        });
    }

    // Toast notification system
    function showNotifToast(type, msg) {
        let container = document.querySelector('.notif-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notif-toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = 'notif-toast';
        const iconMap = { alert: 'alert-triangle', info: 'info', success: 'check-circle' };
        const colorMap = { alert: 'var(--brand-warning)', info: 'var(--brand-primary)', success: 'var(--brand-success)' };
        const icon = iconMap[type] || 'info';
        const color = colorMap[type] || 'var(--text-muted)';
        toast.innerHTML = `<i data-lucide="${icon}" style="color:${color};"></i>
            <span class="toast-msg">${msg}</span>
            <span class="toast-time">just now</span>`;
        container.appendChild(toast);
        lucide.createIcons({ el: toast });
        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 250);
        }, 3500);
    }


    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.getAttribute('data-view');
            switchView(view);
        });
    });

    // Hook into existing updateExecutiveDashboard to update badge
    const origUpdateExec = window.updateExecutiveDashboard;
    if (origUpdateExec) {
        window.updateExecutiveDashboard = function(data) {
            origUpdateExec(data);
            setTimeout(updateNotifBadge, 100);
        };
    }

    // Initialize Login Form
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email')?.value.trim();
            const password = document.getElementById('password')?.value.trim();
            const nameField = document.getElementById('name');
            const nameGroup = document.getElementById('name-group');

            if (!email || !password) {
                if (loginError) loginError.innerText = 'Please enter both email and security key.';
                return;
            }

            // Check if we are in registration mode
            const isRegister = nameGroup && (nameGroup.style.display === 'block' || window.getComputedStyle(nameGroup).display === 'block');

            const endpoint = isRegister ? '/api/v1/auth/register' : '/api/v1/auth/login';

            let body;
            let headers = {};

            if (isRegister) {
                headers['Content-Type'] = 'application/json';
                body = JSON.stringify({
                    email: email,
                    password: password,
                    name: nameField?.value.trim() || 'New User'
                });
            } else {
                headers['Content-Type'] = 'application/x-www-form-urlencoded';
                body = `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`;
            }

            const btn = e.submitter || loginForm.querySelector('.auth-btn');
            if (!btn) return;

            const originalBtnText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<span>${isRegister ? 'Creating Account...' : 'Authenticating...'}</span> <i data-lucide="loader-2" class="spin"></i>`;
            safeCreateIcons();
            if (loginError) loginError.innerText = '';

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: headers,
                    body: body
                });
                const data = await response.json();
                if (response.ok) {
                    authToken = data.access_token;
                    userRole = data.role;
                    userName = data.name;
                    localStorage.setItem('fleet_token', authToken);
                    localStorage.setItem('fleet_role', userRole);
                    localStorage.setItem('fleet_name', userName);
                    checkAuthState();
                } else {
                    if (loginError) loginError.innerText = data.detail || 'Authentication failed. Please check credentials.';
                }
            } catch (err) {
                console.error("Auth Error:", err);
                if (loginError) loginError.innerText = 'Security node unreachable. Check connection.';
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalBtnText;
                safeCreateIcons();
            }
        });
    }

    // Toggle between Login and Registration
    function toggleAuthMode(e) {
        if (e) e.preventDefault();
        const nmGroup = document.getElementById('name-group');
        const authBtnSpan = document.querySelector('.auth-btn span');
        const toggText = document.getElementById('toggle-text');
        const lTitle = document.querySelector('.login-title');
        const lSubtitle = document.querySelector('.login-subtitle');

        if (!nmGroup) return;

        const isLog = nmGroup.style.display === 'none' || window.getComputedStyle(nmGroup).display === 'none';
        if (isLog) {
            nmGroup.style.display = 'block';
            if (authBtnSpan) authBtnSpan.innerText = 'Create Account';
            if (toggText) toggText.innerHTML = 'Already have access? <a href="#" id="toggle-auth" style="color: var(--brand-primary); text-decoration: none; font-weight: 700;">Sign In</a>';
            if (lTitle) lTitle.innerText = 'Join AI - Telemetrix';
            if (lSubtitle) lSubtitle.innerText = 'Create your enterprise fleet account';
        } else {
            nmGroup.style.display = 'none';
            if (authBtnSpan) authBtnSpan.innerText = 'Access System';
            if (toggText) toggText.innerHTML = 'New to Telemetrix? <a href="#" id="toggle-auth" style="color: var(--brand-primary); text-decoration: none; font-weight: 700;">Request Access</a>';
            if (lTitle) lTitle.innerText = 'AI - Telemetrix';
            if (lSubtitle) lSubtitle.innerText = 'Enterprise Intelligence Portal';
        }

        // Re-attach listener because we replaced innerHTML
        document.getElementById('toggle-auth')?.addEventListener('click', toggleAuthMode);
        safeCreateIcons();
    }

    document.getElementById('toggle-auth')?.addEventListener('click', toggleAuthMode);
    
    // Explicit Logout Hook
    document.getElementById('logout-btn')?.addEventListener('click', () => { 
        localStorage.clear(); 
        location.reload(); 
    });
});

// --- SECURITY MODULE LOGIC ---
async function initSecurityModule() {
    const list = document.getElementById('security-incident-list');
    if (!list) return;

    try {
        const resp = await fetch('/api/analytics/summary', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const data = await resp.json();
        const events = data.recent_events || [];
        
        // Security logic: focus on Tamper, Geofence, Power Cut, Unknown movement
        const securityEvents = events.filter(e => {
            const t = e.type.toLowerCase();
            const isSec = t.includes('tamper') || t.includes('geofence') || t.includes('powercut') || t.includes('moving');
            return isSec && (alertPreferences[e.type] !== false);
        });

        const securityStats = data.securityStats || { tamper: 0, geofence: 0, movement: 0 };

        // Populate notifications from security events
        if (typeof populateNotifFromEvents === 'function') {
            populateNotifFromEvents(securityEvents);
        }

        const kpiTamper = document.getElementById('sec-kpi-tamper');
        const kpiGeofence = document.getElementById('sec-kpi-geofence');
        const kpiMovement = document.getElementById('sec-kpi-movement');

        if (kpiTamper) animateCounter('sec-kpi-tamper', securityStats.tamper);
        if (kpiGeofence) animateCounter('sec-kpi-geofence', securityStats.geofence);
        if (kpiMovement) animateCounter('sec-kpi-movement', securityStats.movement);

        if (securityEvents.length === 0) {
            list.innerHTML = '<div class="empty-state"><i data-lucide="shield-check"></i><p>No critical security incidents detected</p></div>';
        } else {
            list.innerHTML = securityEvents.map(e => `
                <div class="incident-item">
                    <div class="alert-icon critical"><i data-lucide="shield"></i></div>
                    <div style="flex:1">
                        <div style="font-weight:700; color:#fff;">${e.type.replace(/([A-Z])/g, ' $1').trim()}</div>
                        <div style="font-size:0.8rem; color:var(--text-dim);">${e.vehicle} - Secure Perimeter Alert</div>
                    </div>
                    <div class="incident-time">${e.time}</div>
                </div>
            `).join('');
        }
        lucide.createIcons({ el: list });
    } catch (e) {
        console.error("Security Init Error:", e);
    }
}

// Chat UI Controls
document.getElementById('toggle-chat-history')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const sidebar = document.getElementById('chat-history-sidebar');
    sidebar.classList.toggle('hidden');
    localStorage.setItem('chatHistoryVisible', !sidebar.classList.contains('hidden'));
});

chatTrigger?.addEventListener('click', () => {
    chatPanel.classList.toggle('collapsed');
    if (!chatPanel.classList.contains('collapsed')) {
        userInput.focus();
        if (!chatMessages.children.length) loadChatHistory();

        // Restore history visibility preference
        const historyVisible = localStorage.getItem('chatHistoryVisible') !== 'false';
        const sidebar = document.getElementById('chat-history-sidebar');
        if (historyVisible) sidebar.classList.remove('hidden');
        else sidebar.classList.add('hidden');
    }
});

document.getElementById('close-chat-panel')?.addEventListener('click', () => chatPanel.classList.add('collapsed'));

document.getElementById('fullscreen-chat')?.addEventListener('click', () => {
    chatPanel.classList.toggle('fullscreen');
    const icon = document.querySelector('#fullscreen-chat i');
    if (chatPanel.classList.contains('fullscreen')) {
        icon.setAttribute('data-lucide', 'minimize-2');
    } else {
        icon.setAttribute('data-lucide', 'maximize-2');
    }
    lucide.createIcons();
});

['vin-analysis-modal', 'edit-vehicle-modal', 'vehicle-details-modal'].forEach((modalId) => {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) return;
    modalEl.addEventListener('click', (e) => {
        if (e.target !== modalEl) return;
        if (modalId === 'vin-analysis-modal') closeVinAnalysisModal();
        if (modalId === 'edit-vehicle-modal') closeEditModal();
        if (modalId === 'vehicle-details-modal') closeDetailsModal();
    });
});

document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (!document.getElementById('vin-analysis-modal')?.classList.contains('hidden-view')) closeVinAnalysisModal();
    if (!document.getElementById('edit-vehicle-modal')?.classList.contains('hidden-view')) closeEditModal();
    if (!document.getElementById('vehicle-details-modal')?.classList.contains('hidden-view')) closeDetailsModal();
});

sendBtn?.addEventListener('click', sendMessage);
userInput?.addEventListener('keypress', (e) => e.key === 'Enter' && sendMessage());

// Draggable Chat
let isDragging = false, currentX, currentY, initialX, initialY, xOffset = 0, yOffset = 0;
document.querySelector('.chat-panel-header')?.addEventListener('mousedown', (e) => {
    if (chatPanel.classList.contains('fullscreen') || chatPanel.classList.contains('collapsed')) return;
    initialX = e.clientX - xOffset; initialY = e.clientY - yOffset;
    isDragging = true;
});
document.addEventListener('mousemove', (e) => {
    if (isDragging) {
        e.preventDefault();
        currentX = e.clientX - initialX; currentY = e.clientY - initialY;
        xOffset = currentX; yOffset = currentY;
        chatPanel.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;
    }
});
document.addEventListener('mouseup', () => isDragging = false);

// Matrix Toggle
document.getElementById('toggle-asset-matrix')?.addEventListener('click', () => {
    document.getElementById('asset-matrix-container').classList.toggle('matrix-collapsed');
});

// Consolidated VIN Search Intelligence listener removed as it is now handled by vinSearchAnalyze()

// Admin Actions - Cloud Sync
adminSyncBtn?.addEventListener('click', async () => {
    adminSyncBtn.style.pointerEvents = 'none';
    adminSyncBtn.style.opacity = '1';
    adminSyncBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:12px;"></i>';
    safeCreateIcons();

    showNotification("Synchronizing with PC12 Intelligence Node...", "success");

    try {
        const resp = await fetch('/api/v1/sync/start', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await resp.json();

        if (resp.ok) {
            showNotification(`Sync Successful: ${data.synced.devices} devices updated.`, "success");
            loadDashboardData(); // Refresh UI with new data
        } else {
            showNotification(`Sync Node Busy: ${data.detail || 'Access Restricted'}`, "error");
        }
    } catch (e) {
        showNotification("Intelligence sync interrupted. Check connection.", "error");
    } finally {
        setTimeout(() => {
            adminSyncBtn.style.pointerEvents = 'auto';
            adminSyncBtn.style.opacity = '0.3';
            adminSyncBtn.innerHTML = '<i data-lucide="cloud-lightning" style="width:12px;"></i>';
            safeCreateIcons();
        }, 2000);
    }
});

// Manual Full Sync Button (Header)
document.getElementById('manual-pc12-sync-btn')?.addEventListener('click', async function handleSyncClick() {
    const btn = document.getElementById('manual-pc12-sync-btn');
    if (!btn) return;

    // If already in confirm-pending state, proceed with sync
    if (btn.dataset.confirming === 'true') {
        btn.dataset.confirming = 'false';
        btn.style.pointerEvents = 'none';
        btn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> <span>Synchronizing...</span>';
        safeCreateIcons();
        showNotification('Synchronizing with PC12 Node...', 'success');

        try {
            const resp = await fetch('/api/v1/sync/start', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            const data = await resp.json();

            if (resp.ok && data.status === 'success') {
                showNotification(`Sync Complete - ${data.synced.devices || 0} Assets Updated`, 'success');
                loadDashboardData();
            } else if (data.status === 'busy') {
                showNotification('Sync already running. Please wait...', 'error');
            } else {
                showNotification(`Sync Error: ${data.detail || data.errors?.[0] || 'Unknown error'}`, 'error');
            }
        } catch (e) {
            showNotification('Sync interrupted. Check connection.', 'error');
        } finally {
            setTimeout(() => {
                btn.style.pointerEvents = 'auto';
                btn.innerHTML = '<i data-lucide="cloud-download"></i> <span>Sync PC12 Data</span>';
                safeCreateIcons();
            }, 1500);
        }
        return;
    }

    // First click ΓÇö show inline confirmation
    btn.dataset.confirming = 'true';
    const origHtml = btn.innerHTML;
    btn.innerHTML = '<i data-lucide="check-circle"></i> <span>Click Again to Confirm</span>';
    btn.style.background = 'rgba(239, 68, 68, 0.2)';
    btn.style.borderColor = 'var(--brand-danger)';
    btn.style.color = 'var(--brand-danger)';
    safeCreateIcons();

    // Auto-cancel after 4 seconds if not confirmed
    setTimeout(() => {
        if (btn.dataset.confirming === 'true') {
            btn.dataset.confirming = 'false';
            btn.innerHTML = origHtml;
            btn.style.background = 'rgba(245, 158, 11, 0.1)';
            btn.style.borderColor = 'var(--brand-warning)';
            btn.style.color = 'var(--brand-warning)';
            safeCreateIcons();
        }
    }, 4000);
});

document.getElementById('deploy-btn')?.addEventListener('click', () => {
    showNotification("Deploying platform updates to edge nodes...", "success");
    setTimeout(() => showNotification("Platform Update 5.0.1 successfully deployed.", "success"), 2000);
});

// --- REAL-TIME ALERT POLLING ---
let lastProcessedEventId = null;

function startAlertsPolling() {
    if (alertsInterval) clearInterval(alertsInterval);
    alertsInterval = setInterval(async () => {
        // 1. Check for new alerts (Toast Notifications)
        await checkNewAlerts();
        
        // 2. Refresh active views
        const viewSecurity = document.getElementById('view-security');
        if (viewSecurity && viewSecurity.classList.contains('active-view')) initSecurityModule();
    }, 15000); 
}

async function checkNewAlerts() {
    if (!authToken) return;
    try {
        const resp = await fetch('/api/analytics/summary', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const data = await resp.json();
        const events = data.recent_events || [];
        if (events.length > 0) {
            const latest = events[0];
            if (lastProcessedEventId && latest.id !== lastProcessedEventId) {
                // New event detected - Respect user preferences
                if (alertPreferences[latest.type] !== false) {
                    const eventTitle = latest.type.replace(/([A-Z])/g, ' $1').trim();
                    showNotification(`Critical Alert: ${eventTitle} detected on ${latest.vehicle}`, 'warning');
                    if (typeof addNotification === 'function') {
                        const cat = TRACCAR_EVENT_TYPES.find(t => t.id === latest.type)?.category;
                        const catKey = (!cat || ['General','Emergency','Safety','Security'].includes(cat)) ? 'alerts' : 'system';
                        addNotification(latest.type, eventTitle, latest.vehicle || 'Unknown vehicle', catKey);
                    }
                }
            }
            lastProcessedEventId = latest.id;
        }
    } catch (e) {
        console.warn("Alert Polling Error:", e);
    }
}

function showVehicleHistory() { showNotification('Vehicle history coming soon', 'info'); }

let mapRefreshInterval = null;
function startMapUpdates() {
    if (mapRefreshInterval) clearInterval(mapRefreshInterval);
    mapRefreshInterval = setInterval(() => {
        if (document.getElementById('view-map')?.classList.contains('active-view')) {
            updateVehicleMarkers();
        }
    }, 30000);
}

function stopMapUpdates() {
    if (mapRefreshInterval) { clearInterval(mapRefreshInterval); mapRefreshInterval = null; }
}

// ── FDB Upload (live in initDataImportView) ────────────────────────────────────


/* -- FDB VIEW LOGIC (TABBED) -- */
function switchFdbTab(tabId, btn) {
    // Update buttons
    const container = btn.closest('.glass-segmented-control');
    container.querySelectorAll('.segment-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Update visibility
    document.querySelectorAll('.fdb-sub-tab').forEach(t => t.style.display = 'none');
    document.getElementById(`fdb-tab-${tabId}`).style.display = 'block';

    // Trigger loads
    if (tabId === 'explorer') { window._fdbExplorerLoading = false; loadFdbExplorer(); }
    if (tabId === 'fuel-txns') { loadFuelTxnStats(); loadFuelTransactions(); setupFuelUpload(); }
    if (tabId === 'overview') loadFdbStats();
    if (tabId === 'kemis') { loadKemisStats().then(() => { loadKemisData(1); loadKemisEfficiency('top'); }); }
}

function drawDonut(canvas, values, colors) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const total = values.reduce((s, v) => s + v, 0);
    const cssSize = 160;
    const outer = cssSize / 2 - 4, inner = outer * 0.58;
    canvas.width = cssSize * dpr;
    canvas.height = cssSize * dpr;
    canvas.style.width = cssSize + 'px';
    canvas.style.height = cssSize + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssSize, cssSize);
    const cx = cssSize / 2, cy = cssSize / 2;
    let start = -Math.PI / 2;
    values.forEach((v, i) => {
        const angle = (v / total) * Math.PI * 2;
        ctx.beginPath();
        ctx.arc(cx, cy, outer, start, start + angle);
        ctx.arc(cx, cy, inner, start + angle, start, true);
        ctx.closePath();
        ctx.fillStyle = colors[i % colors.length];
        ctx.fill();
        start += angle;
    });
    ctx.beginPath();
    ctx.arc(cx, cy, inner - 1, 0, Math.PI * 2);
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    ctx.fillStyle = isDark ? '#14162a' : '#ffffff';
    ctx.fill();
    ctx.fillStyle = isDark ? '#ffffff' : '#1a1a2e';
    ctx.font = `bold ${Math.round(cssSize * 0.16)}px 'Space Grotesk', sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(total.toLocaleString(), cx, cy - 4);
    ctx.font = `${Math.round(cssSize * 0.085)}px 'Inter', sans-serif`;
    ctx.fillStyle = isDark ? '#8b8da3' : '#6b7280';
    ctx.fillText('TOTAL', cx, cy + 12);
}

async function loadFdbStats() {
    try {
        const res = await fetch('/api/fleet/fdb/fdb-stats', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        
        document.getElementById('fdb-stat-total').innerText = (data.total_vehicles || 0).toLocaleString();
        document.getElementById('fdb-stat-benchmark').innerText = (data.with_benchmark || 0).toLocaleString();
        document.getElementById('fdb-stat-shift').innerText = (data.with_shift_data || 0).toLocaleString();

        // Render Category Stats — Donut Chart
        const catCanvas = document.getElementById('fdb-category-donut');
        const catLegend = document.getElementById('fdb-category-legend');
        if (catCanvas && catLegend && data.categories) {
            const cats = data.categories.slice(0, 6);
            const total = cats.reduce((s, c) => s + c.count, 0);
            const catColors = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#06b6d4', '#22d3ee'];
            drawDonut(catCanvas, cats.map(c => c.count), catColors);
            catLegend.innerHTML = cats.map((c, i) => {
                const pct = (c.count / total * 100).toFixed(1);
                return `<div style="display:flex; align-items:center; gap:8px;">
                    <div style="width:10px; height:10px; border-radius:3px; background:${catColors[i % catColors.length]}; flex-shrink:0;"></div>
                    <span style="font-size:0.78rem; font-weight:600; color:var(--text-secondary); flex:1; overflow-wrap:anywhere;">${c.category}</span>
                    <span style="font-size:0.75rem; font-weight:800; color:var(--text-primary); white-space:nowrap;">${c.count.toLocaleString()}</span>
                    <span style="font-size:0.68rem; color:var(--text-dim); white-space:nowrap;">${pct}%</span>
                </div>`;
            }).join('');
        }

        // Render Vendor Stats — Donut Chart
        const venCanvas = document.getElementById('fdb-vendor-donut');
        const venLegend = document.getElementById('fdb-vendor-legend');
        if (venCanvas && venLegend && data.top_vendors) {
            const vens = data.top_vendors.slice(0, 6);
            const total = vens.reduce((s, v) => s + v.count, 0);
            const venColors = ['#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6'];
            drawDonut(venCanvas, vens.map(v => v.count), venColors);
            venLegend.innerHTML = vens.map((v, i) => {
                const pct = (v.count / total * 100).toFixed(1);
                return `<div style="display:flex; align-items:center; gap:8px;">
                    <div style="width:10px; height:10px; border-radius:3px; background:${venColors[i % venColors.length]}; flex-shrink:0;"></div>
                    <span style="font-size:0.78rem; font-weight:600; color:var(--text-secondary); flex:1; overflow-wrap:anywhere;">${v.vendor}</span>
                    <span style="font-size:0.75rem; font-weight:800; color:var(--text-primary); white-space:nowrap;">${v.count.toLocaleString()}</span>
                    <span style="font-size:0.68rem; color:var(--text-dim); white-space:nowrap;">${pct}%</span>
                </div>`;
            }).join('');
        }

    } catch(err) {
        console.error('Failed to load FDB stats', err);
    }
}

// ── FDB Explorer Status Filter ────────────────────────────────────────────────
let fdbStatusFilter = '';

function filterFdbByStatus(status, btn) {
    fdbStatusFilter = status;
    if (btn) {
        btn.closest('.matrix-filter-group').querySelectorAll('.matrix-filter-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
    }
    window._fdbExplorerLoading = false;
    loadFdbExplorer();
}

async function loadFdbExplorer() {
    if (window._fdbExplorerLoading) return;
    window._fdbExplorerLoading = true;

    const body = document.getElementById('fdb-explorer-body');
    const searchInput = document.getElementById('fdb-explorer-search');
    const countEl = document.getElementById('fdb-explorer-count');
    const imeiHeader = document.querySelector('#fdb-explorer-head th:nth-child(2)');
    const isAdmin = userRole === 'SUPERADMIN' || userRole === 'ADMIN';
    if (imeiHeader) imeiHeader.style.display = isAdmin ? '' : 'none';
    
    const searchVal = searchInput?.value || '';
    if (!body) { window._fdbExplorerLoading = false; return; }
    
    const loadColspan = (userRole === 'SUPERADMIN' || userRole === 'ADMIN') ? 9 : 8;
    body.innerHTML = `<tr><td colspan="${loadColspan}" style="text-align:center; padding:40px;"><div class="loader-spinner"></div> Loading master records & live status...</td></tr>`;
    
    try {
        let url = `/api/fleet/fdb/fdb-explorer?search=${encodeURIComponent(searchVal)}`;
        if (fdbStatusFilter) url += `&status=${fdbStatusFilter}`;
        
        const res = await fetch(url, {
             headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const contentType = res.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const text = await res.text();
            console.error("Non-JSON response from Explorer:", text.substring(0, 200));
            throw new Error("Backend returned HTML instead of JSON. Possible 404 or server error.");
        }

        const records = await res.json();
        
        if (!Array.isArray(records)) {
            throw new Error(records.detail || "Invalid server response");
        }
        
        // Update count
        if (countEl) {
            const online = records.filter(r => r.status === 'online').length;
            const offline = records.filter(r => r.status === 'offline').length;
            const unmapped = records.filter(r => r.status === 'unmapped').length;
            countEl.innerHTML = `<span style="font-weight:700;">${records.length}</span> vehicles` +
                (fdbStatusFilter ? ` <span style="opacity:0.6;">(${fdbStatusFilter})</span>` : '') +
                ` &mdash; <span style="color:var(--brand-success);">${online} online</span>, ` +
                `<span style="color:var(--text-dim);">${offline} offline</span>, ` +
                `<span style="color:var(--brand-warning);">${unmapped} unmapped</span>`;
        }
        
        if (records.length === 0) {
            body.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:60px; color:var(--text-dim);">
                <i data-lucide="search-x" style="width:48px; height:48px; opacity:0.1; margin-bottom:16px;"></i>
                <p>No vehicles found matching "${searchVal || fdbStatusFilter || 'all'}".</p>
                <button class="glass-btn small" onclick="document.getElementById('fdb-explorer-search').value=''; fdbStatusFilter=''; window._fdbExplorerLoading=false; loadFdbExplorer()">Clear Filter</button>
            </td></tr>`;
            safeCreateIcons();
            return;
        }

        const isAdmin = userRole === 'SUPERADMIN' || userRole === 'ADMIN';
        const imeiHtml = (r) => isAdmin ? `<td style="font-family:monospace; font-size:0.8rem;">${r.imei || '---'}</td>` : '';
        body.innerHTML = records.map(r => `
            <tr>
                <td style="font-weight:800; color:var(--brand-primary);">${r.registration}</td>
                ${imeiHtml(r)}
                <td style="font-size:0.8rem;">${r.group || 'N/A'}</td>
                <td><span class="stats-badge" style="background:rgba(0,0,0,0.05); color:var(--text-secondary);">${r.category || 'N/A'}</span></td>
                <td style="font-size:0.8rem; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${r.vendor || ''}">${r.vendor || 'N/A'}</td>
                <td style="font-weight:700;">${r.benchmark || '--'} km/l</td>
                <td>
                    <span class="stats-badge ${r.status_class}">${r.status.toUpperCase()}</span>
                </td>
                <td style="font-size:0.75rem; color:var(--text-dim);">${r.last_signal}</td>
                <td>
                    <button class="icon-btn-small" onclick="openVehicleIntel('${r.registration}')"><i data-lucide="external-link"></i></button>
                </td>
            </tr>
        `).join('');
        
        safeCreateIcons();
    } catch(err) {
        body.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:40px; color:var(--brand-danger);">
            <p>Explorer service unavailable.</p>
            <span style="font-size:0.7rem; opacity:0.7;">${err.message}</span>
        </td></tr>`;
    } finally {
        window._fdbExplorerLoading = false;
    }
}

function filterFdbTable() {
    clearTimeout(window.fdbSearchTimer);
    window.fdbSearchTimer = setTimeout(loadFdbExplorer, 500);
}

// Override original init function to show Overview by default
function initDataImportView() {
    loadFdbStats().then(() => loadKEFleetOverview());
    
    const fileInput = document.getElementById('fdb-file-input');
    if (fileInput && !fileInput._listenerAttached) {
        fileInput._listenerAttached = true;

        const dropZone = document.getElementById('fdb-drop-zone');
        if (dropZone) {
            ['dragenter', 'dragover'].forEach(evt => {
                dropZone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('dragover'); });
            });
            ['dragleave', 'drop'].forEach(evt => {
                dropZone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('dragover'); });
            });
            dropZone.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length) { fileInput.files = e.dataTransfer.files; fileInput.dispatchEvent(new Event('change')); }
            });
            dropZone.addEventListener('click', (e) => { if (e.target.tagName !== 'INPUT') fileInput.click(); });
        }

        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const statusDiv = document.getElementById('fdb-upload-status');
            const resultDiv = document.getElementById('fdb-upload-result');
            const msg = document.getElementById('fdb-upload-msg');
            
            statusDiv.style.display = 'block';
            resultDiv.style.display = 'none';
            msg.innerHTML = `Uploading ${file.name}... Reconciliation in progress.`;

            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const res = await fetch('/api/fleet/fdb/fdb-upload', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${authToken}` },
                    body: formData
                });
                const data = await res.json();
                
                if (res.ok) {
                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = `
                    <div style="background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.3); padding: 24px; border-radius: 16px;">
                        <div style="display:flex; align-items:center; gap:12px; color: #065f46; font-weight:800; margin-bottom:12px;">
                            <i data-lucide="check-circle"></i> FDB Import Complete
                        </div>
                        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px;">
                            <div style="text-align:center; padding:12px; background:rgba(255,255,255,0.5); border-radius:12px;">
                                <div style="font-size:0.7rem; color:var(--text-dim);">NEW</div>
                                <div style="font-weight:800; font-size:1.1rem;">${data.summary.inserted}</div>
                            </div>
                            <div style="text-align:center; padding:12px; background:rgba(255,255,255,0.5); border-radius:12px;">
                                <div style="font-size:0.7rem; color:var(--text-dim);">UPDATED</div>
                                <div style="font-weight:800; font-size:1.1rem;">${data.summary.updated}</div>
                            </div>
                            <div style="text-align:center; padding:12px; background:rgba(255,255,255,0.5); border-radius:12px;">
                                <div style="font-size:0.7rem; color:var(--text-dim);">UNCHANGED</div>
                                <div style="font-weight:800; font-size:1.1rem;">${data.summary.unchanged}</div>
                            </div>
                        </div>
                    </div>`;
                    loadFdbStats();
                } else {
                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = `<div class="stats-badge danger" style="padding:16px; width:100%; justify-content:center;">${data.detail || 'Upload Error'}</div>`;
                }
            } catch(err) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<div class="stats-badge danger" style="padding:16px;">Network Failure: ${err.message}</div>`;
            } finally {
                statusDiv.style.display = 'none';
                fileInput.value = '';
                safeCreateIcons();
            }
        });
    }
}

/* -- FUEL TRANSACTIONS LOGIC -- */
let fuelTxnPage = 1;
let fuelTxnProduct = '';
let fuelUploadSetup = false;

function setupFuelUpload() {
    if (fuelUploadSetup) return;
    fuelUploadSetup = true;
    const fileInput = document.getElementById('fuel-file-input');
    if (!fileInput) return;
    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const statusDiv = document.getElementById('fuel-upload-status');
        const resultDiv = document.getElementById('fuel-upload-result');
        const msg = document.getElementById('fuel-upload-msg');
        statusDiv.style.display = 'block';
        resultDiv.style.display = 'none';
        msg.innerHTML = `Uploading ${file.name}... Parsing transactions.`;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch('/api/fleet/fdb/fuel-upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}` },
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3); padding:20px; border-radius:12px;">
                    <div style="font-weight:800; font-size:1rem; margin-bottom:8px; color:#065f46;">Fuel Import Complete</div>
                    <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:12px;">
                        <div style="text-align:center; padding:10px; background:rgba(255,255,255,0.5); border-radius:10px;">
                            <div style="font-size:0.7rem; color:var(--text-dim);">INSERTED</div>
                            <div style="font-weight:800; font-size:1.1rem;">${data.summary.inserted}</div>
                        </div>
                        <div style="text-align:center; padding:10px; background:rgba(255,255,255,0.5); border-radius:10px;">
                            <div style="font-size:0.7rem; color:var(--text-dim);">VOIDS SKIPPED</div>
                            <div style="font-weight:800; font-size:1.1rem;">${data.summary.skipped_void}</div>
                        </div>
                        <div style="text-align:center; padding:10px; background:rgba(255,255,255,0.5); border-radius:10px;">
                            <div style="font-size:0.7rem; color:var(--text-dim);">DUPLICATES</div>
                            <div style="font-weight:800; font-size:1.1rem;">${data.summary.duplicates_skipped}</div>
                        </div>
                        <div style="text-align:center; padding:10px; background:rgba(255,255,255,0.5); border-radius:10px;">
                            <div style="font-size:0.7rem; color:var(--text-dim);">TOTAL FUEL</div>
                            <div style="font-weight:800; font-size:1.1rem;">${data.summary.total_fuel_liters}L</div>
                        </div>
                    </div>
                </div>`;
                loadFuelTxnStats();
                loadFuelTransactions();
            } else {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); padding:16px; border-radius:12px; color:#991b1b;">
                    <div style="font-weight:800; margin-bottom:4px;">Upload Failed</div>
                    <div style="font-size:0.85rem;">${data.detail || 'Unknown error'}</div>
                </div>`;
            }
        } catch (err) {
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); padding:16px; border-radius:12px; color:#991b1b;">
                <div style="font-weight:800;">Network Error</div><div>${err.message}</div></div>`;
        } finally {
            statusDiv.style.display = 'none';
            fileInput.value = '';
        }
    });
}

async function loadFuelTxnStats() {
    try {
        const res = await fetch('/api/fleet/fdb/fuel-stats', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) return;
        const d = await res.json();
        document.getElementById('fuel-txn-count').innerText = (d.total_transactions || 0).toLocaleString();
        document.getElementById('fuel-txn-liters').innerText = (d.total_fuel_liters || 0).toLocaleString() + ' L';
        document.getElementById('fuel-txn-amount').innerText = 'PKR ' + (d.total_amount_pkr || 0).toLocaleString();
        document.getElementById('fuel-txn-vehicles').innerText = (d.unique_vehicles || 0).toLocaleString();
    } catch (e) { console.warn('Fuel stats error:', e); }
}

async function loadFuelTransactions(page) {
    if (!page) fuelTxnPage = 1;
    const body = document.getElementById('fuel-txn-body');
    const searchVal = document.getElementById('fuel-txn-search')?.value || '';
    if (!body) return;
    body.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px;"><div class="loader-spinner"></div> Loading transactions...</td></tr>';
    try {
        let url = `/api/fleet/fdb/fuel-transactions?page=${fuelTxnPage}&limit=50`;
        if (searchVal) url += `&search=${encodeURIComponent(searchVal)}`;
        if (fuelTxnProduct) url += `&product=${encodeURIComponent(fuelTxnProduct)}`;
        const res = await fetch(url, { headers: { 'Authorization': `Bearer ${authToken}` } });
        const data = await res.json();
        const countEl = document.getElementById('fuel-txn-count-label');
        if (countEl) countEl.innerHTML = `<span style="font-weight:700;">${data.total}</span> transactions — Page ${data.page} of ${data.pages}`;
        if (!data.records || data.records.length === 0) {
            body.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:40px; color:var(--text-dim);">No transactions found. Upload a Transaction Report Excel to get started.</td></tr>';
            return;
        }
        body.innerHTML = data.records.map(r => `
            <tr>
                <td style="font-weight:800; color:var(--brand-primary);">${r.vehicle_registration || ''}</td>
                <td style="font-size:0.85rem;">${r.txn_date || ''}</td>
                <td style="font-size:0.85rem;">${r.txn_time || ''}</td>
                <td style="font-size:0.8rem; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${r.retail_outlet || ''}">${r.retail_outlet || 'N/A'}</td>
                <td><span class="stats-badge" style="background:${r.product === 'Hi Cetane' ? 'rgba(14,165,233,0.1); color:#0ea5e9' : 'rgba(34,197,94,0.1); color:#16a34a'};">${r.product || 'N/A'}</span></td>
                <td style="font-weight:700; color:var(--brand-success);">${r.quantity_liters || 0} L</td>
                <td style="font-family:var(--map-mono);">PKR ${(r.amount_pkr || 0).toLocaleString()}</td>
            </tr>
        `).join('');
        renderFuelPagination(data.page, data.pages);
        safeCreateIcons();
    } catch (err) {
        body.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:40px; color:var(--brand-danger);">Error: ${err.message}</td></tr>`;
    }
}

function renderFuelPagination(current, total) {
    const el = document.getElementById('fuel-txn-pagination');
    if (!el) return;
    let html = '';
    if (current > 1) html += `<button class="glass-btn small" onclick="fuelTxnPage=${current - 1}; loadFuelTransactions(${current - 1});">Prev</button>`;
    for (let i = Math.max(1, current - 2); i <= Math.min(total, current + 2); i++) {
        html += `<button class="glass-btn small ${i === current ? 'primary-glow' : ''}" onclick="fuelTxnPage=${i}; loadFuelTransactions(${i});">${i}</button>`;
    }
    if (current < total) html += `<button class="glass-btn small" onclick="fuelTxnPage=${current + 1}; loadFuelTransactions(${current + 1});">Next</button>`;
    el.innerHTML = html;
}

function filterFuelByProduct(product, btn) {
    fuelTxnProduct = product;
    fuelTxnPage = 1;
    if (btn) {
        btn.closest('.matrix-filter-group').querySelectorAll('.matrix-filter-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
    }
    loadFuelTransactions(1);
}

function searchFuelTransactions() {
    clearTimeout(window.fuelSearchTimer);
    window.fuelSearchTimer = setTimeout(() => { fuelTxnPage = 1; loadFuelTransactions(1); }, 500);
}

/* ================================================================
   KEMIS MIS TAB LOGIC
   ================================================================ */
let kemisPage = 1;
let kemisRemarks = '';
let kemisVendor = '';
let kemisSearchTimer = null;
let kemisTrendData = [];
let kemisEffMode = 'top';

async function loadKemisStats() {
    try {
        const dateFrom = document.getElementById('kemis-search-date-from')?.value || '';
        const dateTo = document.getElementById('kemis-search-date-to')?.value || '';
        let url = '/api/fleet/fdb/kemis-stats?';
        if (dateFrom) url += `date_from=${dateFrom}&`;
        if (dateTo) url += `date_to=${dateTo}`;
        const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('kemis-stat-total').innerText = (data.total_rows || 0).toLocaleString();
        document.getElementById('kemis-stat-vehicles').innerText = (data.unique_vehicles || 0).toLocaleString();
        document.getElementById('kemis-stat-km').innerText = (data.total_km || 0).toLocaleString() + ' km';
        document.getElementById('kemis-stat-fuel').innerText = (data.total_fuel_consumed || 0).toLocaleString() + ' L';
        document.getElementById('kemis-stat-avgkm').innerText = (data.avg_km_per_vehicle_day || 0).toFixed(1) + ' km';
        document.getElementById('kemis-stat-avgbench').innerText = (data.avg_benchmark || 0).toFixed(1) + ' km/L';

        // Category stats
        const catBox = document.getElementById('kemis-category-stats');
        if (catBox && data.categories) {
            const maxCat = Math.max(...data.categories.map(c => c.count));
            catBox.innerHTML = data.categories.slice(0, 6).map(c => {
                const pct = (c.count / maxCat * 100).toFixed(0);
                return `
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                        <span style="font-size:0.82rem; font-weight:600; color:var(--text-secondary); word-break:normal; overflow-wrap:anywhere;">${c.category}</span>
                        <span style="font-size:0.82rem; font-weight:800; color:var(--brand-primary); margin-left:8px; flex-shrink:0;">${c.count.toLocaleString()}</span>
                    </div>
                    <div style="height:8px; background:var(--fleet-bg); border-radius:4px; overflow:hidden;">
                        <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, var(--brand-primary), rgba(99,102,241,0.5)); border-radius:4px; transition:width 0.6s;"></div>
                    </div>
                </div>`;
            }).join('');
        }

        // Group stats
        const grpBox = document.getElementById('kemis-group-stats');
        if (grpBox && data.groups) {
            const maxGrp = Math.max(...data.groups.map(g => g.count));
            grpBox.innerHTML = data.groups.slice(0, 6).map(g => {
                const pct = (g.count / maxGrp * 100).toFixed(0);
                return `
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                        <span style="font-size:0.82rem; font-weight:600; color:var(--text-secondary); word-break:normal; overflow-wrap:anywhere;">${g.group}</span>
                        <span style="font-size:0.82rem; font-weight:800; color:var(--brand-success); margin-left:8px; flex-shrink:0;">${g.count.toLocaleString()}</span>
                    </div>
                    <div style="height:8px; background:var(--fleet-bg); border-radius:4px; overflow:hidden;">
                        <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, var(--brand-success), rgba(34,197,94,0.5)); border-radius:4px; transition:width 0.6s;"></div>
                    </div>
                </div>`;
            }).join('');
        }

        // Vendor stats (interactive)
        const vendorBox = document.getElementById('kemis-vendor-stats');
        if (vendorBox && data.vendors) {
            const maxVendorCount = Math.max(...data.vendors.map(v => v.count));
            vendorBox.innerHTML = data.vendors.slice(0, 8).map(v => {
                const isActive = kemisVendor === v.vendor;
                const pct = (v.count / maxVendorCount * 100).toFixed(0);
                return `
                <div style="cursor:pointer; padding:10px 14px; border-radius:10px; border:1px solid ${isActive ? 'var(--brand-primary)' : 'var(--fleet-border)'}; background:${isActive ? 'rgba(99,102,241,0.08)' : 'var(--fleet-card)'}; transition:all 0.2s;" 
                     onclick="filterKemisByVendor('${v.vendor.replace(/'/g, "\\'")}')" 
                     onmouseover="this.style.borderColor='var(--brand-primary)'; this.style.background='rgba(99,102,241,0.05)'"
                     onmouseout="this.style.borderColor='${isActive ? 'var(--brand-primary)' : 'var(--fleet-border)'}'; this.style.background='${isActive ? 'rgba(99,102,241,0.08)' : 'var(--fleet-card)'}'">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                        <span style="font-size:0.82rem; font-weight:700; color:var(--text-primary); line-height:1.3; word-break:normal; overflow-wrap:anywhere;">${v.vendor}</span>
                        <span style="font-size:0.78rem; color:var(--brand-primary); font-weight:700; white-space:nowrap; flex-shrink:0;">${v.total_km.toLocaleString()} km</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                        <span style="font-size:0.72rem; color:var(--text-dim); font-weight:500;">${v.count.toLocaleString()} records</span>
                        <span style="font-size:0.72rem; color:var(--brand-success); font-weight:600;">${v.total_fuel.toLocaleString()} L</span>
                    </div>
                    <div style="height:5px; background:var(--fleet-bg); border-radius:3px; overflow:hidden; margin-top:8px;">
                        <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, var(--brand-primary), rgba(99,102,241,0.4)); border-radius:3px; transition:width 0.6s;"></div>
                    </div>
                </div>`;
            }).join('');
        }

        // Trend chart
        if (data.trend && data.trend.length > 0) {
            kemisTrendData = data.trend;
            populateKemisTrendMonths(data.trend);
            // Render filtered view (selected month or latest if nothing selected)
            const sel = document.getElementById('kemis-month-select');
            const selectedMonth = sel ? sel.value : '';
            const filtered = selectedMonth
                ? data.trend.filter(d => d.date && d.date.startsWith(selectedMonth))
                : data.trend;
            renderKemisTrendChart(filtered.length ? filtered : data.trend);
        }
    } catch (e) {
        console.error('KEMIS stats error:', e);
    }
}

// ---- Kemis Trend Month Filter ----

function populateKemisTrendMonths(trendData) {
    const sel = document.getElementById('kemis-month-select');
    if (!sel) return;
    
    const monthsSet = new Set();
    trendData.forEach(d => {
        if (!d.date) return;
        // Robust extraction of YYYY-MM
        let mMatch = d.date.match(/^(\d{4})-(\d{2})/);
        if (mMatch) {
            monthsSet.add(`${mMatch[1]}-${mMatch[2]}`);
        } else {
            // Fallback for DD/MM/YYYY
            let dmMatch = d.date.match(/(\d{2})[/-](\d{2})[/-](\d{4})/);
            if (dmMatch) monthsSet.add(`${dmMatch[3]}-${dmMatch[2]}`);
        }
    });

    const months = Array.from(monthsSet).sort().reverse(); // Show newest months first
    const currentVal = sel.value;
    
    sel.innerHTML = '<option value="">All Months</option>';
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    
    months.forEach(m => {
        const [year, month] = m.split('-');
        const label = monthNames[parseInt(month) - 1] + ' ' + year;
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = label;
        if (m === currentVal) opt.selected = true;
        sel.appendChild(opt);
    });

    // If we have data but no month is selected, auto-select the latest month
    if (months.length > 0 && !sel.value) {
        sel.value = months[0];
    }
}

function filterKemisTrendByMonth() {
    const sel = document.getElementById('kemis-month-select');
    if (!sel || !kemisTrendData.length) return;
    const selectedMonth = sel.value;
    const filtered = selectedMonth
        ? kemisTrendData.filter(d => {
            if (!d.date) return false;
            return d.date.includes(selectedMonth) || 
                   (d.date.match(/(\d{2})[/-](\d{2})[/-](\d{4})/) && `${d.date.split(/[/-]/)[2]}-${d.date.split(/[/-]/)[1]}` === selectedMonth);
        })
        : kemisTrendData;
    
    renderKemisTrendChart(filtered);
}

function renderKemisTrendChart(trendData) {
    const canvas = document.getElementById('kemis-trend-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;
    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const cw = rect.width;
    const ch = 340;
    
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    ctx.scale(dpr, dpr);

    const padding = { top: 30, right: 72, bottom: 60, left: 72 };
    const w = cw - padding.left - padding.right;
    const h = ch - padding.top - padding.bottom;

    const n = trendData.length;
    if (n === 0) return;

    const maxKM = Math.max(...trendData.map(d => d.total_km)) * 1.15 || 1000;
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    
    function fmtDate(ds) {
        if (!ds) return '';
        const parts = ds.split(/[-/]/);
        if (parts.length < 3) return ds;
        // Try to detect YYYY-MM-DD vs DD/MM/YYYY
        if (parts[0].length === 4) {
            return monthNames[parseInt(parts[1]) - 1] + ' ' + parseInt(parts[2]);
        } else {
            return monthNames[parseInt(parts[1]) - 1] + ' ' + parseInt(parts[0]);
        }
    }

    const efficiencies = trendData.map(d => d.fuel_consumed > 0 ? d.total_km / d.fuel_consumed : 0);
    const effValues = efficiencies.filter(e => e > 0);
    const minEff = effValues.length ? Math.min(...effValues) * 0.8 : 0;
    const maxEff = effValues.length ? Math.max(...effValues) * 1.2 : 12;
    const effRange = maxEff - minEff || 1;
    const avgEff = effValues.length ? effValues.reduce((a, b) => a + b, 0) / effValues.length : 10;

    const groupW = w / n;
    const kmBarW = Math.max(8, Math.min(groupW * 0.45, 24));
    const effBarW = Math.max(4, Math.min(groupW * 0.22, 12));

    ctx.clearRect(0, 0, cw, ch);

    // Draw background grid
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (h / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + w, y);
        ctx.stroke();
    }

    // --- Draw Total KM Bars ---
    trendData.forEach((d, i) => {
        const cx = padding.left + i * groupW + groupW / 2;
        const barH = (d.total_km / maxKM) * h;
        const bx = cx - kmBarW / 2 - 2;
        const by = padding.top + h - barH;
        
        // Rounded top
        const r = 4;
        ctx.beginPath();
        ctx.roundRect(bx, by, kmBarW, barH, [r, r, 0, 0]);
        
        const grad = ctx.createLinearGradient(bx, by, bx, padding.top + h);
        grad.addColorStop(0, '#06b6d4');   // Cyan 500
        grad.addColorStop(0.5, '#0891b2'); // Cyan 600
        grad.addColorStop(1, '#164e63');   // Cyan 900
        ctx.fillStyle = grad;
        ctx.fill();
        
        // Subtle highlight
        ctx.strokeStyle = 'rgba(255,255,255,0.15)';
        ctx.lineWidth = 0.5;
        ctx.stroke();
    });

    // --- Draw Efficiency Bars (Offset) ---
    trendData.forEach((d, i) => {
        const cx = padding.left + i * groupW + groupW / 2 + (kmBarW / 2) + 2;
        const eff = efficiencies[i];
        if (eff <= 0) return;
        
        const barH = ((eff - minEff) / effRange) * h;
        const bx = cx - effBarW / 2;
        const by = padding.top + h - barH;
        
        let color;
        if (eff < avgEff * 0.8) color = '#f43f5e';      // Rose 500
        else if (eff < avgEff * 0.95) color = '#f59e0b'; // Amber 500
        else color = '#10b981';                         // Emerald 500

        ctx.beginPath();
        ctx.roundRect(bx, by, effBarW, barH, [2, 2, 0, 0]);
        
        const grad = ctx.createLinearGradient(bx, by, bx, padding.top + h);
        grad.addColorStop(0, color);
        grad.addColorStop(1, color + '33');
        ctx.fillStyle = grad;
        ctx.fill();
    });

    // Labels
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.font = '500 11px Inter, sans-serif';
    ctx.textAlign = 'center';
    
    const xStep = Math.max(1, Math.floor(n / 10));
    trendData.forEach((d, i) => {
        if (i % xStep === 0 || i === n - 1) {
            const cx = padding.left + i * groupW + groupW / 2;
            ctx.fillText(fmtDate(d.date), cx, ch - 22);
        }
    });

    // Y Axis Left (KM)
    ctx.fillStyle = '#22d3ee'; // cyan 400
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
        const val = maxKM / 5 * (5 - i);
        const y = padding.top + (h / 5) * i;
        ctx.fillText(val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val.toFixed(0), padding.left - 12, y + 4);
    }

    // Y Axis Right (Efficiency)
    ctx.fillStyle = '#34d399'; // emerald 400
    ctx.textAlign = 'left';
    for (let i = 0; i <= 5; i++) {
        const val = minEff + effRange / 5 * (5 - i);
        const y = padding.top + (h / 5) * i;
        ctx.fillText(val.toFixed(1), padding.left + w + 12, y + 4);
    }

    // Interactive Hover
    canvas.onmousemove = function(e) {
        const canvasRect = canvas.getBoundingClientRect();
        const mx = e.clientX - canvasRect.left;
        const my = e.clientY - canvasRect.top;
        const tooltip = document.getElementById('kemis-trend-tooltip');
        
        let idx = -1;
        for (let i = 0; i < n; i++) {
            const cx = padding.left + i * groupW + groupW / 2;
            if (Math.abs(mx - cx) < groupW / 2) { idx = i; break; }
        }

        if (idx >= 0 && my > padding.top - 20 && my < padding.top + h + 20) {
            const d = trendData[idx];
            const eff = efficiencies[idx];
            const cx = padding.left + idx * groupW + groupW / 2;
            
            // Re-render to show hover state
            renderKemisTrendChart(trendData);
            
            // Draw hover highlight
            ctx.fillStyle = 'rgba(255,255,255,0.03)';
            ctx.fillRect(padding.left + idx * groupW + 2, padding.top, groupW - 4, h);
            
            tooltip.style.display = 'block';
            tooltip.style.left = (cx > cw / 2) ? (cx - 240) + 'px' : (cx + 20) + 'px';
            tooltip.style.top = '20px';
            
            const effColor = eff >= avgEff ? '#10b981' : (eff < avgEff * 0.8 ? '#f43f5e' : '#f59e0b');
            tooltip.innerHTML = `
                <div style="font-weight:800; margin-bottom:10px; font-size:1rem; color:#22d3ee; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:8px;">${fmtDate(d.date)}</div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;"><span style="color:rgba(255,255,255,0.6);">Distance</span><strong style="color:#22d3ee;">${d.total_km.toLocaleString()} km</strong></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;"><span style="color:rgba(255,255,255,0.6);">Fuel</span><strong style="color:#fff;">${d.fuel_consumed.toLocaleString()} L</strong></div>
                <div style="display:flex; justify-content:space-between; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1);"><span style="color:rgba(255,255,255,0.6);">Efficiency</span><strong style="color:${effColor};">${eff.toFixed(2)} km/L</strong></div>
            `;
        } else {
            tooltip.style.display = 'none';
        }
    };

    canvas.onmouseleave = () => {
        document.getElementById('kemis-trend-tooltip').style.display = 'none';
        renderKemisTrendChart(trendData);
    };
}

async function loadKemisEfficiency(mode) {
    kemisEffMode = mode;
    const topBtn = document.getElementById('eff-top-btn');
    const botBtn = document.getElementById('eff-bottom-btn');
    if (topBtn) { topBtn.className = mode === 'top' ? 'glass-btn small primary-glow' : 'glass-btn small'; }
    if (botBtn) { botBtn.className = mode === 'bottom' ? 'glass-btn small primary-glow' : 'glass-btn small'; }

    const box = document.getElementById('kemis-efficiency-body');
    if (!box) return;
    box.innerHTML = '<div style="text-align:center; padding:20px;"><div class="loader-spinner"></div></div>';

    try {
        const order = mode === 'top' ? 'desc' : 'asc';
        const res = await fetch(`/api/fleet/fdb/kemis-efficiency?sort_by=benchmark&order=${order}&limit=15`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) { box.innerHTML = '<div style="color:var(--brand-error); text-align:center; padding:20px;">Error loading data</div>'; return; }
        const data = await res.json();

        if (!data.records || data.records.length === 0) {
            box.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-dim);">No data available</div>';
            return;
        }

        const maxBench = Math.max(...data.records.map(r => r.benchmark));
        const isTop = mode === 'top';

        box.innerHTML = `
            <div style="overflow-x:auto;">
                <table class="premium-table" style="min-width:900px;">
                    <thead>
                        <tr>
                            <th style="width:40px;">#</th>
                            <th>Vehicle</th>
                            <th>Category</th>
                            <th>Vendor</th>
                            <th>Group</th>
                            <th style="text-align:center;">Days</th>
                            <th style="text-align:right;">Benchmark (km/L)</th>
                            <th style="text-align:right;">Total KM</th>
                            <th style="text-align:right;">Total Fuel (L)</th>
                            <th style="text-align:right;">Avg Daily KM</th>
                            <th style="text-align:right;">Actual km/L</th>
                            <th style="width:120px;">Efficiency</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.records.map((r, i) => {
                            const barWidth = (r.benchmark / maxBench * 100).toFixed(0);
                            const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i + 1);
                            const barColor = isTop ? 'var(--brand-primary)' : 'var(--brand-error)';
                            const effDiff = r.actual_kmpl - r.benchmark;
                            const effColor = effDiff >= 0 ? 'var(--brand-success)' : 'var(--brand-error)';
                            return `<tr>
                                <td style="text-align:center; font-weight:700; font-size:1rem;">${medal}</td>
                                <td><strong style="color:var(--brand-primary); cursor:pointer;" onclick="openVehicleMIS('${r.vehicle}')">${r.vehicle}</strong></td>
                                <td style="font-size:0.8rem;">${r.category}</td>
                                <td style="font-size:0.8rem;">${r.vendor}</td>
                                <td style="font-size:0.8rem;">${r.group}</td>
                                <td style="text-align:center;">${r.days}</td>
                                <td style="text-align:right; font-weight:700;">${r.benchmark.toFixed(1)}</td>
                                <td style="text-align:right;">${r.total_km.toLocaleString()}</td>
                                <td style="text-align:right;">${r.total_fuel.toLocaleString()}</td>
                                <td style="text-align:right;">${r.avg_daily_km.toFixed(1)}</td>
                                <td style="text-align:right; font-weight:700; color:${effColor};">${r.actual_kmpl.toFixed(1)}</td>
                                <td>
                                    <div style="height:6px; background:var(--fleet-bg); border-radius:3px; overflow:hidden;">
                                        <div style="width:${barWidth}%; height:100%; background:${barColor}; opacity:0.7; border-radius:3px;"></div>
                                    </div>
                                </td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (e) {
        console.error('KEMIS efficiency error:', e);
        box.innerHTML = `<div style="color:var(--brand-error); text-align:center; padding:20px;">Error: ${e.message}</div>`;
    }
}

function applyKemisDateRange() {
    kemisPage = 1;
    loadKemisData(1);
}

async function loadKemisData(page = 1) {
    try {
        const body = document.getElementById('kemis-body');
        if (!body) return;
        body.innerHTML = '<tr><td colspan="26" style="text-align:center; padding:40px;"><div class="loader-spinner"></div> Loading KEMIS data...</td></tr>';

        const search = document.getElementById('kemis-search')?.value || '';
        const dateFrom = document.getElementById('kemis-search-date-from')?.value || '';
        const dateTo = document.getElementById('kemis-search-date-to')?.value || '';

        let url = `/api/fleet/fdb/kemis-data?page=${page}&limit=25`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (dateFrom) url += `&date_from=${dateFrom}`;
        if (dateTo) url += `&date_to=${dateTo}`;
        if (kemisRemarks) url += `&remarks=${encodeURIComponent(kemisRemarks)}`;
        if (kemisVendor) url += `&vendor=${encodeURIComponent(kemisVendor)}`;

        const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) {
            body.innerHTML = `<tr><td colspan="26" style="text-align:center; color:var(--brand-error);">Error loading data</td></tr>`;
            return;
        }
        const data = await res.json();

        const label = document.getElementById('kemis-count-label');
        if (label) {
            let filterInfo = `Showing ${data.records.length} of ${data.total} records (Page ${data.page} of ${data.pages})`;
            if (kemisVendor) filterInfo = `Vendor: <strong style="color:var(--brand-primary);">${kemisVendor}</strong> | ${filterInfo}`;
            if (kemisRemarks) filterInfo = `Remarks: <strong>${kemisRemarks}</strong> | ${filterInfo}`;
            label.innerHTML = filterInfo;
        }

        // Show/hide vendor badge
        const vendorBadge = document.getElementById('kemis-vendor-badge');
        const vendorName = document.getElementById('kemis-vendor-name');
        if (vendorBadge && vendorName) {
            if (kemisVendor) {
                vendorBadge.style.display = 'inline-flex';
                vendorName.textContent = kemisVendor;
            } else {
                vendorBadge.style.display = 'none';
            }
        }

        if (data.records.length === 0) {
            if (data.auto_generated) {
                body.innerHTML = `<tr><td colspan="26" style="text-align:center; padding:40px;">
                    <div style="margin-bottom:16px;">
                        <i data-lucide="cpu" style="width:48px; height:48px; color:var(--brand-success); margin-bottom:12px;"></i>
                    </div>
                    <div style="font-size:1.1rem; font-weight:700; color:var(--text-primary); margin-bottom:8px;">No KEMIS data for this date range</div>
                    <div style="font-size:0.9rem; color:var(--brand-success); margin-bottom:16px;">MIS generation started from GPS data for all KE vehicles...</div>
                    <div style="font-size:0.8rem; color:var(--text-dim); margin-bottom:16px;">This takes 5-10 minutes for ~1,700 vehicles. Click Refresh after a few minutes.</div>
                    <button class="glass-btn primary-glow" onclick="loadKemisData(1)" style="padding:8px 20px;">
                        <i data-lucide="refresh-cw" style="width:14px;"></i> Refresh
                    </button>
                </td></tr>`;
                safeCreateIcons();
            } else {
                body.innerHTML = '<tr><td colspan="26" style="text-align:center; padding:40px; color:var(--text-dim);">No records found</td></tr>';
            }
            renderKemisPagination(1, 1);
            return;
        }

        body.innerHTML = data.records.map(r => {
            const remarksClass = r.remarks === 'Reporting' ? 'style="color:var(--brand-success);"' :
                                 r.remarks === 'ER' ? 'style="color:var(--brand-error);"' :
                                 r.remarks === 'TNR' ? 'style="color:var(--brand-warning);"' : '';
            const onRoadBadge = r.on_off_road === 'On Road' ?
                '<span style="color:var(--brand-success);font-weight:600;">On Road</span>' :
                r.on_off_road === 'Off Road' ? '<span style="color:var(--brand-warning);">Off Road</span>' : (r.on_off_road || '--');
            const hiredBadge = r.hired_own === 'Hired' ?
                '<span style="background:var(--brand-warning);color:#000;padding:2px 6px;border-radius:8px;font-size:0.7rem;">Hired</span>' :
                '<span style="background:var(--brand-success);color:#fff;padding:2px 6px;border-radius:8px;font-size:0.7rem;">Own</span>';
            const loc = r.last_location ? r.last_location.split('|').pop().trim() : '--';
            const km = parseFloat(r.total_km) || 0;
            const fc = parseFloat(r.fuel_consumed) || 0;
            const fd = parseFloat(r.fuel_drawn) || 0;
            const diff = parseFloat(r.fuel_difference) || 0;
            const kmColor = km > 100 ? 'var(--brand-success)' : km > 0 ? 'var(--brand-primary)' : 'var(--text-dim)';
            const diffColor = diff > 0 ? 'var(--brand-success)' : diff < 0 ? 'var(--brand-error)' : 'var(--text-dim)';
            return `<tr>
                <td style="white-space:nowrap;font-weight:600;">${r.record_date || '--'}</td>
                <td><strong style="color:var(--brand-primary);cursor:pointer;" onclick="openVehicleMIS('${r.vehicle}')">${r.vehicle}</strong></td>
                <td>${hiredBadge}</td>
                <td style="font-size:0.8rem;">${r.vendor || '--'}</td>
                <td>${r.category || '--'}</td>
                <td style="font-size:0.8rem;">${r.fleet_group || '--'}</td>
                <td style="font-size:0.75rem;">${r.cluster || '--'}</td>
                <td style="font-size:0.75rem;">${r.ibc_vibc || '--'}</td>
                <td style="text-align:center;">${r.shift_hrs || '--'}</td>
                <td style="font-size:0.75rem;">${r.shift_timing || '--'}</td>
                <td>${onRoadBadge}</td>
                <td style="text-align:center;font-weight:600;">${r.benchmark || '0'}</td>
                <td style="text-align:right;font-weight:700;color:${kmColor};">${parseFloat(r.peak_hour || 0).toFixed(1)}</td>
                <td style="text-align:right;font-weight:700;">${parseFloat(r.peak_off || 0).toFixed(1)}</td>
                <td style="text-align:right;font-weight:800;color:${kmColor};">${km.toFixed(1)} km</td>
                <td style="text-align:right;font-weight:700;color:var(--brand-success);">${fd > 0 ? fd.toFixed(1) + ' L' : '--'}</td>
                <td style="text-align:right;font-weight:700;">${fc > 0 ? fc.toFixed(1) + ' L' : '--'}</td>
                <td style="text-align:right;font-weight:800;color:${diffColor};">${diff > 0 ? '+' : ''}${diff.toFixed(1)}</td>
                <td style="text-align:center;">${r.excess_idling_mins || '--'}</td>
                <td style="text-align:center;font-weight:700;${r.harsh_braking > 0 ? 'color:var(--brand-error);' : ''}">${r.harsh_braking || 0}</td>
                <td style="text-align:center;font-weight:700;${r.speed_violation > 0 ? 'color:var(--brand-error);' : ''}">${r.speed_violation || 0}</td>
                <td style="text-align:center;">${r.travel_time_mins || '--'}</td>
                <td style="text-align:center;">${r.stop_time_mins || '--'}</td>
                <td ${remarksClass} style="font-weight:600;">${r.remarks || '--'}</td>
                <td style="font-size:0.75rem;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${r.last_location || ''}">${loc}</td>
                <td style="text-align:center;">${r.no_of_polls || '--'}</td>
            </tr>`;
        }).join('');

        renderKemisPagination(data.page, data.pages);
    } catch (e) {
        console.error('KEMIS data error:', e);
        const body = document.getElementById('kemis-body');
        if (body) body.innerHTML = `<tr><td colspan="26" style="text-align:center; color:var(--brand-error);">Error: ${e.message}</td></tr>`;
    }
}

function renderKemisPagination(current, total) {
    const el = document.getElementById('kemis-pagination');
    if (!el) return;
    let html = '';
    if (current > 1) html += `<button class="glass-btn small" onclick="kemisPage=${current - 1}; loadKemisData(${current - 1});">Prev</button>`;
    for (let i = Math.max(1, current - 2); i <= Math.min(total, current + 2); i++) {
        html += `<button class="glass-btn small ${i === current ? 'primary-glow' : ''}" onclick="kemisPage=${i}; loadKemisData(${i});">${i}</button>`;
    }
    if (current < total) html += `<button class="glass-btn small" onclick="kemisPage=${current + 1}; loadKemisData(${current + 1});">Next</button>`;
    el.innerHTML = html;
}

function filterKemisByRemarks(remarks, btn) {
    kemisRemarks = remarks;
    kemisPage = 1;
    if (btn) {
        btn.closest('.matrix-filter-group').querySelectorAll('.matrix-filter-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
    }
    loadKemisData(1);
}

async function triggerKemisSync() {
    const btn = document.getElementById('kemis-sync-btn');
    const originalContent = btn.innerHTML;
    const dateTo = document.getElementById('kemis-search-date-to')?.value || '';
    
    // We usually sync for the "date-to" selected, or yesterday if empty
    let syncDate = dateTo;
    if (!syncDate) {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        syncDate = yesterday.toISOString().split('T')[0];
    }

    if (!confirm(`Trigger automated Performance Sync for ${syncDate}?\nThis will process live telemetry for the entire fleet.`)) {
        return;
    }

    try {
        btn.disabled = true;
        btn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:12px;"></i> Syncing...`;
        safeCreateIcons();

        const res = await fetch(`/api/fleet/fdb/kemis-sync?target_date=${syncDate}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await res.json();
        if (res.ok) {
            showNotifToast('success', `Sync Started for ${data.summary.date}. It is processing in the background, please check back in a few minutes.`);
            // Optionally reload after some delay or user manual refresh
            setTimeout(() => { loadKemisStats(); loadKemisData(1); }, 3000);
        } else {
            showNotifToast('alert', `Sync Failed: ${data.detail || 'Internal Error'}`);
        }
    } catch (err) {
        console.error("Sync Error:", err);
        showNotifToast('alert', 'Network error during performance sync.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
        safeCreateIcons();
    }
}

async function triggerBatchGenerate() {
    const btn = document.getElementById('kemis-generate-btn');
    const originalContent = btn.innerHTML;
    const dateFrom = document.getElementById('kemis-search-date-from')?.value || '2026-06-01';
    const dateTo = document.getElementById('kemis-search-date-to')?.value || new Date(Date.now()-86400000).toISOString().split('T')[0];

    if (!confirm(`Generate MIS from GPS for all KE vehicles?\nFrom: ${dateFrom}  To: ${dateTo}\n\nThis runs in background and may take 5-15 minutes. You can check back after.`)) return;

    try {
        btn.disabled = true;
        btn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:12px;"></i> Generating...`;
        safeCreateIcons();

        const res = await fetch(`/api/fleet/fdb/kemis-generate-batch?start_date=${dateFrom}&end_date=${dateTo}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (res.ok) {
            showNotifToast('success', `Batch generation started for ${dateFrom} to ${dateTo}. Processing in background, check back in 5-10 minutes.`);
        } else {
            showNotifToast('alert', `Failed: ${data.detail || 'Error'}`);
        }
    } catch (err) {
        console.error('Batch Gen Error:', err);
        showNotifToast('alert', 'Network error during batch generation.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
        safeCreateIcons();
    }
}

function searchKemisData() {
    clearTimeout(kemisSearchTimer);
    kemisSearchTimer = setTimeout(() => { kemisPage = 1; loadKemisData(1); }, 500);
}

function filterKemisByVendor(vendor) {
    if (kemisVendor === vendor) {
        kemisVendor = '';
    } else {
        kemisVendor = vendor;
    }
    kemisPage = 1;
    loadKemisStats();
    loadKemisData(1);
}

async function openKemisVehicleDetail(vehicle) {
    try {
        const res = await fetch(`/api/fleet/fdb/kemis-vehicle/${encodeURIComponent(vehicle)}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) return;
        const data = await res.json();

        if (!data.records || data.records.length === 0) {
            alert(`No KEMIS data found for vehicle: ${vehicle}`);
            return;
        }

        const totalKM = data.records.reduce((s, r) => s + (parseFloat(r.total_km) || 0), 0);
        const totalFuel = data.records.reduce((s, r) => s + (parseFloat(r.fuel_consumed) || 0), 0);
        const avgBenchmark = data.records.filter(r => r.benchmark > 0).reduce((s, r) => s + parseFloat(r.benchmark), 0) / Math.max(1, data.records.filter(r => r.benchmark > 0).length);
        const reporting = data.records.filter(r => r.remarks === 'Reporting').length;
        const totalHarsh = data.records.reduce((s, r) => s + (parseInt(r.harsh_braking) || 0), 0);
        const totalSpeed = data.records.reduce((s, r) => s + (parseInt(r.speed_violation) || 0), 0);
        const avgPeakHour = data.records.filter(r => r.remarks === 'Reporting').reduce((s, r) => s + (parseFloat(r.peak_hour) || 0), 0) / Math.max(1, reporting);

        const tableRows = data.records.map(r => `
            <tr>
                <td>${r.record_date || '--'}</td>
                <td style="text-align:right;font-weight:700;">${parseFloat(r.total_km || 0).toFixed(1)}</td>
                <td style="text-align:right;">${parseFloat(r.peak_hour || 0).toFixed(1)}</td>
                <td style="text-align:right;">${parseFloat(r.peak_off || 0).toFixed(1)}</td>
                <td style="text-align:right;">${r.fuel_drawn > 0 ? parseFloat(r.fuel_drawn).toFixed(1) : '--'}</td>
                <td style="text-align:right;">${r.fuel_consumed > 0 ? parseFloat(r.fuel_consumed).toFixed(1) : '--'}</td>
                <td style="text-align:center;font-weight:700;${r.harsh_braking > 0 ? 'color:var(--brand-error);' : ''}">${r.harsh_braking || 0}</td>
                <td style="text-align:center;font-weight:700;${r.speed_violation > 0 ? 'color:var(--brand-error);' : ''}">${r.speed_violation || 0}</td>
                <td style="font-weight:600;${r.remarks === 'Reporting' ? 'color:var(--brand-success);' : ''}">${r.remarks || '--'}</td>
            </tr>
        `).join('');

        const html = `
            <div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px;" onclick="this.remove()">
                <div style="background:var(--card-bg);border:1px solid var(--border-light);border-radius:16px;max-width:1000px;width:100%;max-height:90vh;overflow-y:auto;padding:32px;" onclick="event.stopPropagation()">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
                        <h3 style="font-size:1.3rem;font-weight:800;color:var(--text-primary);">${vehicle} — Quick View</h3>
                        <div style="display:flex;gap:8px;align-items:center;">
                            <button onclick="openVehicleMIS('${vehicle}')" class="glass-btn primary-glow" style="padding:8px 16px;font-size:0.8rem;display:flex;align-items:center;gap:6px;"><i data-lucide="file-bar-chart" style="width:14px;"></i> Full MIS</button>
                            <button onclick="this.closest('[style*=fixed]').remove()" style="background:none;border:none;cursor:pointer;font-size:1.5rem;color:var(--text-dim);">&times;</button>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px;">
                        <div class="premium-card mini-stat primary-glow">
                            <span class="card-label">Total KM</span>
                            <span class="card-value">${totalKM.toFixed(1)} km</span>
                        </div>
                        <div class="premium-card mini-stat">
                            <span class="card-label">Fuel Consumed</span>
                            <span class="card-value">${totalFuel.toFixed(1)} L</span>
                        </div>
                        <div class="premium-card mini-stat">
                            <span class="card-label">Avg Benchmark</span>
                            <span class="card-value">${avgBenchmark.toFixed(1)} km/L</span>
                        </div>
                        <div class="premium-card mini-stat">
                            <span class="card-label">Reporting Days</span>
                            <span class="card-value">${reporting} / ${data.records.length}</span>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px;">
                        <div class="premium-card mini-stat">
                            <span class="card-label">Avg Peak Hour KM</span>
                            <span class="card-value">${avgPeakHour.toFixed(1)} km</span>
                        </div>
                        <div class="premium-card mini-stat">
                            <span class="card-label">Total Harsh Braking</span>
                            <span class="card-value" style="${totalHarsh > 0 ? 'color:var(--brand-error);' : ''}">${totalHarsh}</span>
                        </div>
                        <div class="premium-card mini-stat">
                            <span class="card-label">Total Speed Violations</span>
                            <span class="card-value" style="${totalSpeed > 0 ? 'color:var(--brand-error);' : ''}">${totalSpeed}</span>
                        </div>
                    </div>
                    <h4 style="margin-bottom:12px;font-weight:700;">Daily Breakdown</h4>
                    <table class="premium-table">
                        <thead><tr>
                            <th>Date</th><th>Total KM</th><th>Peak Hr KM</th><th>Peak Off KM</th><th>Fuel Drawn</th><th>Fuel Consumed</th><th>Harsh Brake</th><th>Speed Viol.</th><th>Remarks</th>
                        </tr></thead>
                        <tbody>${tableRows}</tbody>
                    </table>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', html);
    } catch (e) {
        console.error('KEMIS vehicle detail error:', e);
    }
}

async function openVehicleMIS(vehicle) {
    document.querySelectorAll('[style*="position:fixed"]').forEach(el => {
        if (el.querySelector('h3')?.textContent?.includes('MIS Summary')) el.remove();
    });

    const overlay = document.createElement('div');
    overlay.className = 'vehicle-mis-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const modal = document.createElement('div');
    modal.className = 'vehicle-mis-modal';
    modal.onclick = (e) => e.stopPropagation();

    modal.innerHTML = '<div style="text-align:center;padding:40px;"><div class="loader-spinner"></div><p style="margin-top:12px;">Generating MIS Report for ' + vehicle + '...</p></div>';
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    try {
        const kemisDateFrom = document.getElementById('kemis-search-date-from')?.value || '';
        const kemisDateTo = document.getElementById('kemis-search-date-to')?.value || '';
        let vehicleUrl = `/api/fleet/fdb/kemis-vehicle-mis/${encodeURIComponent(vehicle)}`;
        const params = [];
        if (kemisDateFrom) params.push(`date_from=${kemisDateFrom}`);
        if (kemisDateTo) params.push(`date_to=${kemisDateTo}`);
        if (params.length) vehicleUrl += '?' + params.join('&');
        const res = await fetch(vehicleUrl, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error('Failed to fetch MIS data');
        const data = await res.json();
        const s = data.summary;
        const daily = data.daily;

        if (!s || !s.total_km) {
            modal.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim);">No reporting data available for this vehicle.</div>';
            return;
        }

        const peakColor = '#06b6d4';
        const offPeakColor = '#a78bfa';

        modal.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;border-bottom:1px solid var(--border-light);padding-bottom:16px;">
                <div>
                    <h2 style="font-size:1.5rem;font-weight:800;color:var(--text-primary);margin:0;">${vehicle} — Full MIS Report</h2>
                    <p style="font-size:0.8rem;color:var(--text-dim);margin:4px 0 0;">${s.vendor || ''} | ${s.category || ''} | ${s.hired_own || ''} | ${s.fleet_group || ''}</p>
                </div>
                <div style="display:flex;gap:8px;">
                    <button onclick="downloadVehicleMIS('${vehicle}')" class="glass-btn primary-glow" style="padding:8px 16px;font-size:0.8rem;display:flex;align-items:center;gap:6px;"><i data-lucide="download" style="width:14px;"></i> Download Excel</button>
                    <button onclick="this.closest('[style*=fixed]').remove()" style="background:none;border:none;cursor:pointer;font-size:1.5rem;color:var(--text-dim);">&times;</button>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:24px;">
                <div class="premium-card mini-stat primary-glow">
                    <span class="card-label">Total KM</span>
                    <span class="card-value">${s.total_km.toLocaleString()} km</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">On-Peak KM</span>
                    <span class="card-value" style="color:${peakColor};">${s.on_peak_km.toLocaleString()} km</span>
                    <span style="font-size:0.65rem;color:var(--text-secondary);">${s.on_peak_pct}%</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Off-Peak KM</span>
                    <span class="card-value" style="color:${offPeakColor};">${s.off_peak_km.toLocaleString()} km</span>
                    <span style="font-size:0.65rem;color:var(--text-secondary);">${s.off_peak_pct}%</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Fuel Consumed</span>
                    <span class="card-value">${s.fuel_consumed.toLocaleString()} L</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Actual km/L</span>
                    <span class="card-value" style="color:${s.actual_kmpl >= s.avg_benchmark ? 'var(--brand-success)' : 'var(--brand-error)'};">${s.actual_kmpl}</span>
                    <span style="font-size:0.65rem;color:var(--text-secondary);">Benchmark: ${s.avg_benchmark}</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Reporting Days</span>
                    <span class="card-value">${s.reporting_days} / ${s.total_days}</span>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:24px;">
                <div class="premium-card mini-stat">
                    <span class="card-label">Avg Shift Hours</span>
                    <span class="card-value">${s.avg_shift_hrs} hrs</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Total Shift Hours</span>
                    <span class="card-value">${s.total_shift_hrs.toLocaleString()} hrs</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Avg Daily KM</span>
                    <span class="card-value">${s.avg_daily_km} km</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Fuel Drawn</span>
                    <span class="card-value">${s.fuel_drawn.toLocaleString()} L</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Fuel Difference</span>
                    <span class="card-value" style="color:${s.fuel_difference > 0 ? 'var(--brand-success)' : s.fuel_difference < 0 ? 'var(--brand-error)' : 'var(--text-dim)'};">${s.fuel_difference > 0 ? '+' : ''}${s.fuel_difference.toLocaleString()} L</span>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px;">
                <div class="premium-card mini-stat">
                    <span class="card-label">Harsh Braking</span>
                    <span class="card-value" style="${s.total_harsh_braking > 0 ? 'color:var(--brand-error);' : ''}">${s.total_harsh_braking}</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Speed Violations</span>
                    <span class="card-value" style="${s.total_speed_violation > 0 ? 'color:var(--brand-error);' : ''}">${s.total_speed_violation}</span>
                </div>
                <div class="premium-card mini-stat">
                    <span class="card-label">Excess Idling</span>
                    <span class="card-value" style="${s.total_excess_idling > 0 ? 'color:var(--brand-warning);' : ''}">${s.total_excess_idling} min</span>
                </div>
            </div>

            <div class="premium-card" style="margin-bottom:20px;">
                <div class="chart-header">
                    <h3 class="chart-title">On-Peak vs Off-Peak Daily KM</h3>
                </div>
                <div style="position:relative;overflow:visible;padding:8px;">
                    <canvas id="vehicle-mis-chart" height="260"></canvas>
                </div>
                <div style="display:flex;justify-content:center;gap:20px;padding:8px 0;border-top:1px solid var(--border-light);">
                    <div style="display:flex;align-items:center;gap:6px;"><div style="width:14px;height:10px;background:${peakColor};border-radius:2px;"></div><span style="font-size:0.8rem;color:var(--text-secondary);font-weight:600;">On-Peak KM</span></div>
                    <div style="display:flex;align-items:center;gap:6px;"><div style="width:14px;height:10px;background:${offPeakColor};border-radius:2px;"></div><span style="font-size:0.8rem;color:var(--text-secondary);font-weight:600;">Off-Peak KM</span></div>
                </div>
            </div>

            <div class="premium-card section-card">
                <div class="section-header" style="padding:16px 20px;">
                    <h3 class="section-title">Daily Breakdown</h3>
                </div>
                <div style="overflow-x:auto;">
                    <table class="premium-table" style="min-width:1100px;">
                        <thead><tr>
                            <th>Date</th><th>Shift Hrs</th><th>On-Peak KM</th><th>Off-Peak KM</th><th>Total KM</th><th>Fuel Drawn</th><th>Fuel Consumed</th><th>Difference</th><th>Efficiency</th><th>Harsh</th><th>Speed</th><th>Remarks</th>
                        </tr></thead>
                        <tbody>${daily.map(r => {
                            const eff = r.fuel_consumed > 0 ? (r.total_km / r.fuel_consumed).toFixed(1) : '--';
                            const diffColor = r.fuel_difference > 0 ? 'var(--brand-success)' : r.fuel_difference < 0 ? 'var(--brand-error)' : 'var(--text-dim)';
                            const remColor = r.remarks === 'Reporting' ? 'var(--brand-success)' : r.remarks === 'TNR' ? 'var(--brand-warning)' : r.remarks === 'ER' ? 'var(--brand-error)' : 'var(--text-dim)';
                            return `<tr>
                                <td style="white-space:nowrap;font-weight:600;">${r.date}</td>
                                <td style="text-align:center;">${r.shift_hrs || '--'}</td>
                                <td style="text-align:right;font-weight:700;color:${peakColor};">${r.on_peak_km.toFixed(1)}</td>
                                <td style="text-align:right;font-weight:700;color:${offPeakColor};">${r.off_peak_km.toFixed(1)}</td>
                                <td style="text-align:right;font-weight:800;">${r.total_km.toFixed(1)}</td>
                                <td style="text-align:right;">${r.fuel_drawn > 0 ? r.fuel_drawn.toFixed(1) : '--'}</td>
                                <td style="text-align:right;">${r.fuel_consumed > 0 ? r.fuel_consumed.toFixed(1) : '--'}</td>
                                <td style="text-align:right;font-weight:700;color:${diffColor};">${r.fuel_difference > 0 ? '+' : ''}${r.fuel_difference.toFixed(1)}</td>
                                <td style="text-align:center;font-weight:700;">${eff}</td>
                                <td style="text-align:center;font-weight:700;${r.harsh_braking > 0 ? 'color:var(--brand-error);' : ''}">${r.harsh_braking}</td>
                                <td style="text-align:center;font-weight:700;${r.speed_violation > 0 ? 'color:var(--brand-error);' : ''}">${r.speed_violation}</td>
                                <td style="font-weight:600;color:${remColor};">${r.remarks || '--'}</td>
                            </tr>`;
                        }).join('')}</tbody>
                    </table>
                </div>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        safeCreateIcons();

        setTimeout(() => renderVehicleMISChart(daily), 200);
    } catch (e) {
        modal.innerHTML = `<div style="text-align:center;padding:40px;color:var(--brand-error);">Error: ${e.message}</div>`;
        console.error('Vehicle MIS error:', e);
    }
}

function renderVehicleMISChart(daily) {
    const canvas = document.getElementById('vehicle-mis-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;
    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const cw = rect.width;
    const ch = 260;
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = cw + 'px';
    canvas.style.height = ch + 'px';
    ctx.scale(dpr, dpr);

    const padding = { top: 16, right: 20, bottom: 44, left: 50 };
    const w = cw - padding.left - padding.right;
    const h = ch - padding.top - padding.bottom;

    const n = daily.length;
    const maxKM = Math.max(...daily.map(d => d.on_peak_km + d.off_peak_km), 1) * 1.1;
    const groupW = w / n;
    const barW = Math.max(4, Math.min(groupW * 0.7, 18));

    ctx.clearRect(0, 0, cw, ch);

    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (h / 4) * i;
        ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(padding.left + w, y); ctx.stroke();
    }

    daily.forEach((d, i) => {
        const cx = padding.left + i * groupW + groupW / 2;

        const offH = (d.off_peak_km / maxKM) * h;
        const onH = (d.on_peak_km / maxKM) * h;
        const totalH = offH + onH;

        const bx = cx - barW / 2;
        const by = padding.top + h - totalH;
        const r = Math.min(barW / 2, 3);

        if (offH > 0) {
            ctx.beginPath();
            ctx.rect(bx, padding.top + h - offH, barW, offH);
            ctx.fillStyle = '#a78bfa';
            ctx.fill();
        }

        if (onH > 0) {
            const onY = padding.top + h - totalH;
            ctx.beginPath();
            ctx.moveTo(bx + r, onY);
            ctx.lineTo(bx + barW - r, onY);
            ctx.quadraticCurveTo(bx + barW, onY, bx + barW, onY + r);
            ctx.lineTo(bx + barW, padding.top + h - offH);
            ctx.lineTo(bx, padding.top + h - offH);
            ctx.lineTo(bx, onY + r);
            ctx.quadraticCurveTo(bx, onY, bx + r, onY);
            ctx.closePath();
            ctx.fillStyle = '#06b6d4';
            ctx.fill();
        }
    });

    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    const xStep = Math.max(1, Math.floor(n / 10));
    daily.forEach((d, i) => {
        if (i % xStep === 0 || i === n - 1) {
            const cx = padding.left + i * groupW + groupW / 2;
            ctx.fillText(d.date.substring(5), cx, ch - 10);
        }
    });

    ctx.fillStyle = 'var(--text-dim, #94a3b8)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
        const val = maxKM / 4 * (4 - i);
        const y = padding.top + (h / 4) * i;
        ctx.fillText(val >= 100 ? (val / 100).toFixed(0) + '0' : val.toFixed(0), padding.left - 8, y + 3);
    }
}

function downloadVehicleMIS(vehicle) {
    const kemisDateFrom = document.getElementById('kemis-search-date-from')?.value || '';
    const kemisDateTo = document.getElementById('kemis-search-date-to')?.value || '';
    let url = `/api/fleet/fdb/kemis-vehicle-mis/${encodeURIComponent(vehicle)}`;
    const params = [];
    if (kemisDateFrom) params.push(`date_from=${kemisDateFrom}`);
    if (kemisDateTo) params.push(`date_to=${kemisDateTo}`);
    if (params.length) url += '?' + params.join('&');
    fetch(url, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.json())
        .then(data => {
            if (!data.daily || !data.daily.length) { alert('No data'); return; }
            const headers = ['Date','Shift Hrs','On-Peak KM','Off-Peak KM','Total KM','Fuel Drawn','Fuel Consumed','Difference','Efficiency','Harsh Braking','Speed Violation','Remarks'];
            const rows = data.daily.map(r => [
                r.date, r.shift_hrs, r.on_peak_km.toFixed(1), r.off_peak_km.toFixed(1),
                r.total_km.toFixed(1), r.fuel_drawn.toFixed(1), r.fuel_consumed.toFixed(1),
                r.fuel_difference.toFixed(1),
                r.fuel_consumed > 0 ? (r.total_km / r.fuel_consumed).toFixed(2) : '',
                r.harsh_braking, r.speed_violation, r.remarks
            ]);
            const s = data.summary;
            const summaryRows = [
                ['VEHICLE MIS REPORT'], [vehicle], [`Vendor: ${s.vendor}`, `Category: ${s.category}`, `Group: ${s.fleet_group}`], [],
                ['Summary'], ['Total KM', s.total_km], ['On-Peak KM', `${s.on_peak_km} (${s.on_peak_pct}%)`],
                ['Off-Peak KM', `${s.off_peak_km} (${s.off_peak_pct}%)`], ['Fuel Consumed', s.fuel_consumed],
                ['Actual km/L', s.actual_kmpl], ['Benchmark', s.avg_benchmark], ['Avg Daily KM', s.avg_daily_km],
                ['Total Shift Hrs', s.total_shift_hrs], ['Avg Shift Hrs', s.avg_shift_hrs],
                ['Harsh Braking', s.total_harsh_braking], ['Speed Violations', s.total_speed_violation], [],
                ['Daily Breakdown']
            ];
            const csv = [...summaryRows, headers, ...rows].map(r => r.join(',')).join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `MIS_${vehicle}_${new Date().toISOString().slice(0,10)}.csv`;
            a.click();
        })
        .catch(e => alert('Download error: ' + e.message));
}

async function generateMISFromDB(vehicle) {
    document.querySelectorAll('.vehicle-mis-overlay').forEach(el => el.remove());

    const overlay = document.createElement('div');
    overlay.className = 'vehicle-mis-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const modal = document.createElement('div');
    modal.className = 'vehicle-mis-modal';
    modal.style.maxWidth = '900px';
    modal.onclick = (e) => e.stopPropagation();

    modal.innerHTML = '<div style="text-align:center;padding:40px;"><div class="loader-spinner"></div><p style="margin-top:12px;color:var(--text-secondary);">Generating MIS from GPS data for <strong>' + vehicle + '</strong>...</p><p style="font-size:0.75rem;color:var(--text-dim);margin-top:4px;">Computing from Traccar positions...</p></div>';
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    try {
        const res = await fetch(`/api/fleet/fdb/generate-mis/${encodeURIComponent(vehicle)}?start_date=2026-04-01&end_date=2026-04-30`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to generate MIS');
        }
        const data = await res.json();
        const s = data.summary;
        const recs = data.records || [];

        modal.innerHTML = `
            <div style="padding:20px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                    <div>
                        <h2 style="font-size:1.2rem;font-weight:800;color:var(--text-primary);margin:0;">Generated MIS Report</h2>
                        <p style="font-size:0.8rem;color:var(--text-dim);margin:4px 0 0;">From GPS Positions — ${data.date_range.start} to ${data.date_range.end}</p>
                    </div>
                    <button onclick="this.closest('.vehicle-mis-overlay').remove()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.2rem;padding:8px;">✕</button>
                </div>

                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;">
                    <div class="premium-card mini-stat" style="border-left:3px solid var(--brand-primary);">
                        <span class="card-label">Vehicle</span>
                        <span class="card-value" style="font-size:1rem;">${vehicle}</span>
                        <span class="card-sub">${data.category} | ${data.vendor}</span>
                    </div>
                    <div class="premium-card mini-stat" style="border-left:3px solid var(--brand-success);">
                        <span class="card-label">Total KM</span>
                        <span class="card-value" style="color:var(--brand-success);">${s.total_km} km</span>
                        <span class="card-sub">${s.total_days} days tracked</span>
                    </div>
                    <div class="premium-card mini-stat" style="border-left:3px solid var(--brand-warning);">
                        <span class="card-label">Fuel Consumed</span>
                        <span class="card-value" style="color:var(--brand-warning);">${s.total_fuel_consumed} L</span>
                        <span class="card-sub">Benchmark: ${data.benchmark} km/L</span>
                    </div>
                    <div class="premium-card mini-stat" style="border-left:3px solid ${s.avg_efficiency >= data.benchmark ? 'var(--brand-success)' : 'var(--brand-error)'};">
                        <span class="card-label">Efficiency</span>
                        <span class="card-value" style="color:${s.avg_efficiency >= data.benchmark ? 'var(--brand-success)' : 'var(--brand-error)'};">${s.avg_efficiency} km/L</span>
                        <span class="card-sub">Diff: ${s.benchmark_diff > 0 ? '+' : ''}${s.benchmark_diff}</span>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px;">
                    <div class="premium-card mini-stat">
                        <span class="card-label">On-Peak KM (6AM-6PM)</span>
                        <span class="card-value" style="color:#06b6d4;">${s.on_peak_km} km</span>
                        <span class="card-sub">${s.on_peak_pct}% of total</span>
                    </div>
                    <div class="premium-card mini-stat">
                        <span class="card-label">Off-Peak KM (6PM-6AM)</span>
                        <span class="card-value" style="color:#a78bfa;">${s.off_peak_km} km</span>
                        <span class="card-sub">${s.off_peak_pct}% of total</span>
                    </div>
                    <div class="premium-card mini-stat">
                        <span class="card-label">Speed Violations</span>
                        <span class="card-value" style="${s.total_speed_violations > 0 ? 'color:var(--brand-error);' : ''}">${s.total_speed_violations}</span>
                        <span class="card-sub">Over 120 km/h</span>
                    </div>
                </div>

                <div class="premium-card" style="margin-bottom:16px;">
                    <div style="padding:16px;">
                        <h3 style="font-size:0.9rem;font-weight:700;color:var(--text-primary);margin-bottom:12px;">Daily Breakdown</h3>
                        <div style="overflow-x:auto;max-height:300px;overflow-y:auto;">
                            <table style="width:100%;border-collapse:collapse;font-size:0.78rem;">
                                <thead style="position:sticky;top:0;background:var(--card-bg,var(--surface));">
                                    <tr>
                                        <th style="text-align:left;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">Date</th>
                                        <th style="text-align:right;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">KM</th>
                                        <th style="text-align:right;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">On-Peak</th>
                                        <th style="text-align:right;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">Off-Peak</th>
                                        <th style="text-align:right;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">Fuel (L)</th>
                                        <th style="text-align:right;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">Eff km/L</th>
                                        <th style="text-align:right;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">Avg Spd</th>
                                        <th style="text-align:right;padding:8px 6px;border-bottom:2px solid var(--border-light);color:var(--text-secondary);">Violations</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${recs.map(r => `
                                        <tr style="border-bottom:1px solid var(--border-light);">
                                            <td style="padding:6px;color:var(--text-primary);">${r.record_date}</td>
                                            <td style="padding:6px;text-align:right;font-weight:700;color:var(--text-primary);">${r.total_km}</td>
                                            <td style="padding:6px;text-align:right;color:#06b6d4;">${r.on_peak_km}</td>
                                            <td style="padding:6px;text-align:right;color:#a78bfa;">${r.off_peak_km}</td>
                                            <td style="padding:6px;text-align:right;">${r.fuel_consumed}</td>
                                            <td style="padding:6px;text-align:right;font-weight:700;color:${r.efficiency_kmpl >= data.benchmark ? 'var(--brand-success)' : 'var(--brand-error)'};">${r.efficiency_kmpl}</td>
                                            <td style="padding:6px;text-align:right;">${r.avg_speed_kmh}</td>
                                            <td style="padding:6px;text-align:right;${r.speed_violations > 0 ? 'color:var(--brand-error);font-weight:700;' : ''}">${r.speed_violations}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div style="text-align:center;">
                    <button onclick="downloadGeneratedMIS('${vehicle}')" class="glass-btn primary-glow" style="padding:10px 24px;font-size:0.85rem;">Download CSV</button>
                </div>
            </div>
        `;

        window._generatedMISData = { vehicle, records: recs };
    } catch (e) {
        modal.innerHTML = '<div style="text-align:center;padding:40px;color:var(--brand-error);"><p style="font-size:1rem;margin-bottom:8px;">Failed to generate MIS</p><p style="font-size:0.85rem;">' + (e.message || 'Unknown error') + '</p></div>';
    }
}

function downloadGeneratedMIS(vehicle) {
    const data = window._generatedMISData;
    if (!data || !data.records || !data.records.length) { alert('No data'); return; }
    const records = data.records;
    const headers = ['Date','Vehicle','KM','On-Peak','Off-Peak','Fuel(L)','Eff km/L','Avg Speed','Max Speed','Violations'];
    const rows = records.map(r => [
        r.record_date, r.vehicle, r.total_km, r.on_peak_km, r.off_peak_km,
        r.fuel_consumed, r.efficiency_kmpl, r.avg_speed_kmh, r.max_speed_kmh, r.speed_violations
    ]);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `GeneratedMIS_${vehicle}_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
}

// ---- Alerts Monitor Functions ----

async function loadAlertsHistory() {
    const tbody = document.getElementById('alerts-history-body');
    if (!tbody) return;

    try {
        const resp = await fetch('/api/analytics/alerts', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const alerts = await resp.json();
        
        if (!alerts || alerts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="padding:40px; text-align:center; color:var(--text-dim);">No alerts detected in current cycle.</td></tr>';
            return;
        }

        tbody.innerHTML = alerts.map(a => {
            const sevClass = a.severity === 'CRITICAL' ? 'status-pill-v2 danger' : (a.severity === 'WARNING' ? 'status-pill-v2 warning' : 'status-pill-v2 success');
            const icon = a.severity === 'CRITICAL' ? 'alert-triangle' : (a.severity === 'WARNING' ? 'zap' : 'info');
            
            return `
                <tr class="alert-row" data-severity="${a.severity}">
                    <td>
                        <div class="${sevClass}" style="display:inline-flex; align-items:center; gap:6px;">
                            <i data-lucide="${icon}" style="width:12px;"></i>
                            ${a.severity}
                        </div>
                    </td>
                    <td>
                        <div style="font-weight:700; color:var(--text-primary); cursor:pointer;" onclick="navigateToMap(${a.device_id})">${a.vehicle}</div>
                        <div style="font-size:0.7rem; color:var(--text-dim);">${a.unique_id}</div>
                    </td>
                    <td style="font-weight:600;">${a.label}</td>
                    <td style="font-size:0.85rem; color:var(--text-secondary);">${a.time}</td>
                    <td style="max-width:300px;">
                        <div style="font-size:0.8rem; color:var(--text-dim); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${a.message}">
                            ${a.message}
                        </div>
                    </td>
                    <td>
                        <div style="display:flex; gap:8px;">
                            <button class="icon-btn-v2" onclick="navigateToMap(${a.device_id})" title="Locate on Map">
                                <i data-lucide="map-pin"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (e) {
        console.error("Alert History Load Error:", e);
        tbody.innerHTML = '<tr><td colspan="6" style="padding:40px; text-align:center; color:var(--brand-danger);">Failed to connect to security feed.</td></tr>';
    }
}

function filterAlertMatrix() {
    const q = document.getElementById('alert-matrix-search')?.value.toLowerCase() || "";
    document.querySelectorAll('#alerts-history-body tr.alert-row').forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
    });
}


// ============================================================================
// ALERT MODAL FUNCTIONS
// ============================================================================

let _alertModalOffset = 0;
const _alertModalLimit = 20;
let _alertSearchTimeout = null;

function _escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function openAlertModal() {
    const modal = document.getElementById('alert-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    _alertModalOffset = 0;
    loadAlertModalData();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeAlertModal() {
    const modal = document.getElementById('alert-modal');
    if (modal) modal.style.display = 'none';
}

function debounceAlertSearch() {
    clearTimeout(_alertSearchTimeout);
    _alertSearchTimeout = setTimeout(() => { _alertModalOffset = 0; loadAlertModalData(); }, 300);
}

async function loadAlertModalData() {
    const type = document.getElementById('alert-filter-type')?.value || '';
    const severity = document.getElementById('alert-filter-severity')?.value || '';
    const dateFrom = document.getElementById('alert-filter-date-from')?.value || '';
    const dateTo = document.getElementById('alert-filter-date-to')?.value || '';
    const vehicle = document.getElementById('alert-filter-vehicle')?.value || '';

    const params = new URLSearchParams();
    if (type) params.set('alert_type', type);
    if (severity) params.set('severity', severity);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    if (vehicle) params.set('vehicle', vehicle);
    params.set('limit', _alertModalLimit);
    params.set('offset', _alertModalOffset);

    try {
        const res = await fetch(`/api/fleet/fdb/alerts?${params}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) throw new Error('Failed to load alerts');
        const data = await res.json();
        renderAlertModalStats(data.total, data.unread);
        renderAlertModalList(data.alerts);
        renderAlertModalPagination(data.total);
        updateAlertBellBadge(data.unread);
    } catch (e) {
        console.error('Alert load error:', e);
        document.getElementById('alert-modal-list').innerHTML = '<div style="padding:40px; text-align:center; color:var(--fleet-muted);">Failed to load alerts</div>';
    }
}

function renderAlertModalStats(total, unread) {
    const el = document.getElementById('alert-modal-stats');
    if (!el) return;
    el.innerHTML = `
        <div class="alert-stat-card" style="flex:1;">
            <div>
                <div class="count" style="color:var(--fleet-text);">${total}</div>
                <div class="label">Total Alerts</div>
            </div>
        </div>
        <div class="alert-stat-card" style="flex:1;">
            <div>
                <div class="count" style="color:#ef4444;">${unread}</div>
                <div class="label">Unread</div>
            </div>
        </div>
        <div class="alert-stat-card" style="flex:1;">
            <div>
                <div class="count" style="color:#f59e0b;">${Math.max(0, total - unread)}</div>
                <div class="label">Read</div>
            </div>
        </div>
    `;
}

function renderAlertModalList(alerts) {
    const el = document.getElementById('alert-modal-list');
    if (!el) return;
    if (!alerts || alerts.length === 0) {
        el.innerHTML = '<div style="padding:60px; text-align:center; color:var(--fleet-muted);"><i data-lucide="bell-off" style="width:48px; height:48px; margin-bottom:12px; opacity:0.3;"></i><br>No alerts found</div>';
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return;
    }

    const icons = {
        'vehicle_transfer': 'truck', 'device_offline': 'wifi-off', 'imei_missing': 'hash',
        'speed_alert': 'gauge', 'fuel_theft': 'fuel', 'idle_alert': 'clock',
        'maintenance': 'wrench', 'geofence': 'map-pin', 'harsh_driving': 'alert-triangle',
        'hard_acceleration': 'zap', 'hard_braking': 'shield-alert', 'hard_cornering': 'rotate-cw',
        'overspeed': 'gauge', 'device_moving': 'move', 'device_stopped': 'square',
        'device_online': 'wifi', 'ignition_on': 'power', 'ignition_off': 'power',
        'driver_changed': 'user', 'jamming': 'radio', 'fatigue_driving': 'bed',
        'accident': 'alert-octagon', 'low_battery': 'battery-low', 'power_off': 'power',
        'fault': 'alert-circle', 'excessive_idle': 'clock',
        'geofence_enter': 'log-in', 'geofence_exit': 'log-out', 'custom_alert': 'message-square'
    };

    el.innerHTML = alerts.map(a => {
        const icon = icons[a.alert_type] || 'bell';
        const time = new Date(a.created_at).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' });
        const ackBadge = a.is_acknowledged ? `<span style="padding:2px 8px; border-radius:6px; background:rgba(34,197,94,0.12); color:#22c55e; font-size:10px; font-weight:700;">ACK by ${_escHtml(a.acknowledged_by || 'Unknown')}</span>` : '';
        const actionBadge = a.action_taken ? `<span style="padding:2px 8px; border-radius:6px; background:rgba(59,130,246,0.12); color:#3b82f6; font-size:10px; font-weight:700; text-transform:capitalize;">${_escHtml(a.action_taken)}</span>` : '';
        const ackBtn = a.is_acknowledged ? '' : `<button onclick="event.stopPropagation(); acknowledgeAlert(${a.id})" style="padding:4px 10px; border-radius:6px; border:1px solid rgba(34,197,94,0.3); background:rgba(34,197,94,0.08); color:#22c55e; font-size:10px; font-weight:700; cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='rgba(34,197,94,0.2)'" onmouseout="this.style.background='rgba(34,197,94,0.08)'">Acknowledge</button>`;
        const actionSelect = a.is_acknowledged ? `<select onclick="event.stopPropagation()" onchange="setAlertAction(${a.id}, this.value); this.value=''" style="padding:4px 8px; border-radius:6px; border:1px solid var(--fleet-border); background:var(--fleet-card-bg); color:var(--fleet-text); font-size:10px; cursor:pointer;">
            <option value="">Action...</option>
            <option value="escalated">Escalate</option>
            <option value="dismissed">Dismiss</option>
            <option value="assigned">Assign</option>
            <option value="resolved">Resolve</option>
        </select>` : '';
        const shareText = `[Alert] ${a.title} | ${a.vehicle} | ${a.message || ''} | ${a.severity.toUpperCase()} | ${time}`;
        const shareBtns = `
            <button onclick="event.stopPropagation(); shareAlertEmail('${_escHtml(a.title)}', '${_escHtml(a.vehicle)}', '${_escHtml(a.message || '')}', '${a.severity}')" title="Send via Email" style="padding:4px 8px; border-radius:6px; border:1px solid rgba(59,130,246,0.3); background:rgba(59,130,246,0.08); color:#3b82f6; font-size:10px; font-weight:700; cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='rgba(59,130,246,0.2)'" onmouseout="this.style.background='rgba(59,130,246,0.08)'"><i data-lucide="mail" style="width:12px; height:12px; vertical-align:middle;"></i></button>
            <button onclick="event.stopPropagation(); shareAlertWhatsApp('${_escHtml(a.title)}', '${_escHtml(a.vehicle)}', '${_escHtml(a.message || '')}', '${a.severity}')" title="Send via WhatsApp" style="padding:4px 8px; border-radius:6px; border:1px solid rgba(37,211,102,0.3); background:rgba(37,211,102,0.08); color:#25d366; font-size:10px; font-weight:700; cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='rgba(37,211,102,0.2)'" onmouseout="this.style.background='rgba(37,211,102,0.08)'"><i data-lucide="message-circle" style="width:12px; height:12px; vertical-align:middle;"></i></button>
            <button onclick="event.stopPropagation(); copyAlertLink(${a.id}, '${_escHtml(a.title)}', '${_escHtml(a.vehicle)}', '${_escHtml(a.message || '')}')" title="Copy Alert Info" style="padding:4px 8px; border-radius:6px; border:1px solid rgba(168,85,247,0.3); background:rgba(168,85,247,0.08); color:#a855f7; font-size:10px; font-weight:700; cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='rgba(168,85,247,0.2)'" onmouseout="this.style.background='rgba(168,85,247,0.08)'"><i data-lucide="copy" style="width:12px; height:12px; vertical-align:middle;"></i></button>
            ${a.alert_type !== 'custom_alert' ? `<button onclick="event.stopPropagation(); dismissAlert(${a.id})" title="Dismiss permanently" style="padding:4px 8px; border-radius:6px; border:1px solid rgba(239,68,68,0.3); background:rgba(239,68,68,0.08); color:#ef4444; font-size:10px; font-weight:700; cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='rgba(239,68,68,0.2)'" onmouseout="this.style.background='rgba(239,68,68,0.08)'"><i data-lucide="x" style="width:12px; height:12px; vertical-align:middle;"></i></button>` : ''}
        `;
        return `
            <div class="alert-item ${a.is_read ? 'read' : 'unread'}" onclick="markAlertRead(${a.id})" style="border-bottom:1px solid var(--fleet-border); padding:14px 0; transition:background 0.15s;" onmouseover="this.style.background='var(--fleet-hover,rgba(59,130,246,0.04))'" onmouseout="this.style.background=''">
                <div style="display:flex; align-items:flex-start; gap:12px;">
                    <div class="alert-icon ${a.severity}" style="flex-shrink:0;">
                        <i data-lucide="${icon}" style="width:18px; height:18px;"></i>
                    </div>
                    <div class="alert-content" style="flex:1; min-width:0;">
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <div class="alert-title">${_escHtml(a.title)}</div>
                            ${ackBadge}
                            ${actionBadge}
                        </div>
                        <div class="alert-message">${_escHtml(a.message || '')}</div>
                        <div class="alert-meta">
                            <span class="alert-severity-badge ${a.severity}">${a.severity}</span>
                            <span><i data-lucide="car" style="width:12px; height:12px;"></i> ${_escHtml(a.vehicle)}</span>
                            <span><i data-lucide="tag" style="width:12px; height:12px;"></i> ${_escHtml(a.alert_type.replace(/_/g, ' '))}</span>
                        </div>
                        <div style="display:flex; gap:6px; margin-top:8px; align-items:center; flex-wrap:wrap;" onclick="event.stopPropagation()">
                            ${ackBtn}
                            ${actionSelect}
                            ${shareBtns}
                            ${a.alert_type === 'custom_alert' ? `<button onclick="event.stopPropagation(); deleteCustomAlert(${a.id}, '${_escHtml(a.title)}')" style="padding:5px 12px; border-radius:6px; border:1px solid rgba(239,68,68,0.5); background:rgba(239,68,68,0.15); color:#ef4444; font-size:10px; font-weight:800; cursor:pointer; transition:all 0.15s; letter-spacing:0.3px;" onmouseover="this.style.background='rgba(239,68,68,0.3)'" onmouseout="this.style.background='rgba(239,68,68,0.15)'"><i data-lucide="trash-2" style="width:11px; height:11px; vertical-align:middle; margin-right:4px;"></i>Delete Alert</button>` : ''}
                        </div>
                    </div>
                    <div class="alert-time" style="flex-shrink:0;">${time}</div>
                </div>
            </div>
        `;
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function renderAlertModalPagination(total) {
    const el = document.getElementById('alert-modal-pagination');
    if (!el) return;
    const totalPages = Math.ceil(total / _alertModalLimit);
    const currentPage = Math.floor(_alertModalOffset / _alertModalLimit) + 1;
    el.innerHTML = `
        <span style="font-size:12px; color:var(--fleet-muted);">Showing ${_alertModalOffset + 1}-${Math.min(_alertModalOffset + _alertModalLimit, total)} of ${total}</span>
        <div style="display:flex; gap:6px;">
            <button class="glass-btn secondary" style="padding:6px 12px; font-size:11px;" ${currentPage <= 1 ? 'disabled' : ''} onclick="alertModalPrev()">Previous</button>
            <button class="glass-btn secondary" style="padding:6px 12px; font-size:11px;" ${currentPage >= totalPages ? 'disabled' : ''} onclick="alertModalNext()">Next</button>
        </div>
    `;
}

function alertModalPrev() { _alertModalOffset = Math.max(0, _alertModalOffset - _alertModalLimit); loadAlertModalData(); }
function alertModalNext() { _alertModalOffset += _alertModalLimit; loadAlertModalData(); }

async function markAlertRead(id) {
    try {
        await fetch('/api/fleet/fdb/alerts/mark-read', {
            method: 'POST', headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ alert_ids: [id] })
        });
        loadAlertModalData();
        fetchAlertUnreadCount();
    } catch (e) { console.error('Mark read error:', e); }
}

async function markAllAlertsRead() {
    try {
        await fetch('/api/fleet/fdb/alerts/mark-read', {
            method: 'POST', headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ all: true })
        });
        loadAlertModalData();
        fetchAlertUnreadCount();
    } catch (e) { console.error('Mark all read error:', e); }
}

async function acknowledgeAlert(id) {
    try {
        await fetch(`/api/fleet/fdb/alerts/${id}/acknowledge`, {
            method: 'PUT', headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' }
        });
        loadAlertModalData();
    } catch (e) { console.error('Acknowledge error:', e); }
}

async function setAlertAction(id, action) {
    try {
        await fetch(`/api/fleet/fdb/alerts/${id}/action`, {
            method: 'PUT', headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        loadAlertModalData();
    } catch (e) { console.error('Set action error:', e); }
}

async function dismissAlert(id) {
    if (!confirm('Dismiss this alert permanently?')) return;
    try {
        const res = await fetch(`/api/fleet/fdb/alerts/${id}/dismiss`, {
            method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            _alertsSummaryLoaded = false;
            loadAlertModalData();
            if (document.getElementById('alerts-page-body')) loadAlertsPage();
        }
    } catch (e) { console.error('Dismiss error:', e); }
}

async function deleteCustomAlert(id, title) {
    if (!confirm(`Delete custom alert "${title}"?\n\nThis will permanently remove it.`)) return;
    try {
        const res = await fetch(`/api/fleet/fdb/alerts/${id}/dismiss`, {
            method: 'DELETE', headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            _alertsSummaryLoaded = false;
            loadAlertModalData();
            if (document.getElementById('alerts-page-body')) loadAlertsPage();
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed; bottom:24px; right:24px; padding:12px 20px; border-radius:10px; background:rgba(239,68,68,0.95); color:#fff; font-size:13px; font-weight:600; z-index:99999; box-shadow:0 4px 20px rgba(0,0,0,0.2);';
            toast.textContent = 'Custom alert deleted';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2500);
        }
    } catch (e) { console.error('Delete custom alert error:', e); }
}

// ============================================================================
// CUSTOM ALERT FORM
// ============================================================================

function openCustomAlertForm() {
    const modal = document.getElementById('custom-alert-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    loadCustomAlertVehicles();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeCustomAlertForm() {
    const modal = document.getElementById('custom-alert-modal');
    if (modal) modal.style.display = 'none';
}

async function loadCustomAlertVehicles() {
    const sel = document.getElementById('custom-alert-vehicle');
    if (!sel) return;
    try {
        const resp = await fetch('/api/fleet/fdb/ke-vehicles', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!resp.ok) return;
        const data = await resp.json();
        const vehicles = data.vehicles || [];
        sel.innerHTML = '<option value="">Select Vehicle...</option>' +
            vehicles.map(v => `<option value="${v.alias_name || v.name || v.uniqueId}">${v.alias_name || v.name || v.uniqueId}</option>`).join('');
    } catch (e) { console.warn('Custom alert vehicles error:', e); }
}

async function submitCustomAlert() {
    const vehicle = document.getElementById('custom-alert-vehicle')?.value || '';
    const severity = document.getElementById('custom-alert-severity')?.value || 'warning';
    const title = document.getElementById('custom-alert-title')?.value || '';
    const message = document.getElementById('custom-alert-message')?.value || '';
    if (!vehicle || !title) {
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed; bottom:24px; right:24px; padding:12px 20px; border-radius:10px; background:rgba(239,68,68,0.95); color:#fff; font-size:13px; font-weight:600; z-index:99999; box-shadow:0 4px 20px rgba(0,0,0,0.2);';
        toast.textContent = 'Vehicle and Title are required!';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2500);
        return;
    }
    try {
        const resp = await fetch('/api/fleet/fdb/alerts/create', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ vehicle, alert_type: 'custom_alert', severity, title, message })
        });
        if (resp.ok) {
            closeCustomAlertForm();
            document.getElementById('custom-alert-title').value = '';
            document.getElementById('custom-alert-message').value = '';
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed; bottom:24px; right:24px; padding:12px 20px; border-radius:10px; background:rgba(34,197,94,0.95); color:#fff; font-size:13px; font-weight:600; z-index:99999; box-shadow:0 4px 20px rgba(0,0,0,0.2);';
            toast.textContent = 'Custom alert created for ' + vehicle;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2500);
            _alertsSummaryLoaded = false;
            loadAlertsPage();
        }
    } catch (e) { console.error('Create custom alert error:', e); }
}

function shareAlertEmail(title, vehicle, message, severity) {
    const subject = encodeURIComponent(`[Fleet Alert] ${title} - ${vehicle}`);
    const body = encodeURIComponent(`Alert: ${title}\nVehicle: ${vehicle}\nSeverity: ${severity.toUpperCase()}\nDetails: ${message}\n\nSent from Fleet Management System`);
    window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
}

function shareAlertWhatsApp(title, vehicle, message, severity) {
    const text = encodeURIComponent(`🚨 *Fleet Alert*\n\n*${title}*\nVehicle: ${vehicle}\nSeverity: ${severity.toUpperCase()}\n${message}\n\n_Sent from Fleet Management System_`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
}

function copyAlertLink(id, title, vehicle, message) {
    const text = `Alert #${id}: ${title} | Vehicle: ${vehicle} | ${message}`;
    navigator.clipboard.writeText(text).then(() => {
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed; bottom:24px; right:24px; padding:12px 20px; border-radius:10px; background:rgba(34,197,94,0.95); color:#fff; font-size:13px; font-weight:600; z-index:99999; box-shadow:0 4px 20px rgba(0,0,0,0.2);';
        toast.textContent = 'Alert info copied to clipboard!';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2500);
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta);
        ta.select(); document.execCommand('copy');
        ta.remove();
    });
}

async function fetchAlertUnreadCount() {
    try {
        const res = await fetch('/api/fleet/fdb/alerts/unread-count', { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) return;
        const data = await res.json();
        updateAlertBellBadge(data.unread);
    } catch (e) { console.error('Unread count error:', e); }
}

function updateAlertBellBadge(count) {
    const badge = document.getElementById('alert-badge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

// Auto-fetch unread count on page load
setTimeout(fetchAlertUnreadCount, 2000);
setInterval(fetchAlertUnreadCount, 30000);


// ============================================================================
// ALERTS PAGE FUNCTIONS (Full page view)
// ============================================================================

let _alertsPageOffset = 0;
const _alertsPageLimit = 50;
let _alertsPageSearchTimeout = null;

function debounceAlertsPageSearch() {
    clearTimeout(_alertsPageSearchTimeout);
    _alertsPageSearchTimeout = setTimeout(() => { _alertsPageOffset = 0; loadAlertsPage(); }, 300);
}

// ============================================================================
// ALERTS SUMMARY DASHBOARD CARDS
// ============================================================================

let _alertsSummaryLoaded = false;

async function loadAlertsSummary() {
    if (_alertsSummaryLoaded) return;
    const el = document.getElementById('alerts-dashboard-cards');
    if (!el) return;
    try {
        const [summaryRes, contextRes] = await Promise.all([
            fetch('/api/fleet/fdb/alerts/summary', { headers: { 'Authorization': `Bearer ${authToken}` } }),
            fetch('/api/fleet/fdb/alerts/severity-context', { headers: { 'Authorization': `Bearer ${authToken}` } })
        ]);
        if (!summaryRes.ok) throw new Error('Failed');
        const data = await summaryRes.json();
        if (contextRes.ok) {
            const contextData = await contextRes.json();
            data.severityContext = contextData;
        }
        renderAlertDashboardCards(data);
        _alertsSummaryLoaded = true;
    } catch (e) { console.error('Alerts summary error:', e); }
}

function renderAlertDashboardCards(data) {
    const el = document.getElementById('alerts-dashboard-cards');
    if (!el) return;

    const brk = data.behavior?.hard_braking || 0;
    const acc = data.behavior?.hard_acceleration || 0;
    const crn = data.behavior?.hard_cornering || 0;
    const idle = data.behavior?.idle || 0;
    const spd = data.behavior?.overspeed || 0;
    const harsh = data.behavior?.harsh_driving || 0;
    const brkTrend = data.behavior_trend?.hard_braking || {};
    const accTrend = data.behavior_trend?.hard_acceleration || {};
    const crnTrend = data.behavior_trend?.hard_cornering || {};
    const idleTrend = data.behavior_trend?.idle || {};
    const spdTrend = data.behavior_trend?.overspeed || {};
    const harshTrend = data.behavior_trend?.harsh_driving || {};

    function trendHtml(t) {
        const tw = t.this_week || 0;
        const lw = t.last_week || 0;
        if (tw === 0 && lw === 0) return `<span style="color:var(--fleet-muted); font-size:10px; font-weight:600;">No recent</span>`;
        const up = t.change_pct > 0;
        const same = t.change_pct === 0;
        const color = same ? 'var(--fleet-muted)' : up ? '#ef4444' : '#22c55e';
        const arrow = same ? '&#9654;' : up ? '&#9650;' : '&#9660;';
        const pct = Math.abs(t.change_pct);
        return `<span style="color:${color}; font-size:10px; font-weight:700;">${arrow} ${pct}%<span style="font-weight:400; color:var(--fleet-muted);"> (30d)</span></span>`;
    }

    function miniBar(current, max) {
        const w = max > 0 ? Math.round(current / max * 100) : 0;
        return `<div style="width:60px; height:4px; border-radius:2px; background:rgba(255,255,255,0.06); overflow:hidden;"><div style="height:100%; width:${Math.max(w, 2)}%; border-radius:2px; background:currentColor; opacity:0.4;"></div></div>`;
    }

    const critCount = data.severity?.critical || 0;
    const warnCount = data.severity?.warning || 0;
    const infoCount = data.severity?.info || 0;
    const totalSev = critCount + warnCount + infoCount || 1;
    const critPct = Math.round(critCount / totalSev * 100);
    const warnPct = Math.round(warnCount / totalSev * 100);
    const infoPct = 100 - critPct - warnPct;

    const topVehicles = (data.top_vehicles || []).slice(0, 5);

    el.innerHTML = `
        <!-- CARD 1: Eco Driving -->
        <div style="background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:16px; padding:20px; display:flex; flex-direction:column; gap:14px;">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:36px; height:36px; border-radius:10px; background:rgba(34,197,94,0.12); display:flex; align-items:center; justify-content:center;">
                        <i data-lucide="leaf" style="width:18px; height:18px; color:#22c55e;"></i>
                    </div>
                    <span style="font-size:14px; font-weight:800; color:var(--fleet-text);">Eco Driving</span>
                </div>
                <span style="font-size:10px; color:var(--fleet-muted);">30-day trend</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
                ${(() => {
                    function ecoRow(color, label, total, trend, bgAlpha) {
                        return `
                        <div style="padding:8px 12px; background:rgba(${bgAlpha},0.06); border-radius:8px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                                <div style="display:flex; align-items:center; gap:6px;">
                                    <div style="width:7px; height:7px; border-radius:50%; background:${color};"></div>
                                    <span style="font-size:11px; font-weight:600; color:var(--fleet-text);">${label}</span>
                                </div>
                                <div style="display:flex; align-items:center; gap:6px;">
                                    <span style="font-size:15px; font-weight:800; color:${color};">${total.toLocaleString()}</span>
                                    ${trendHtml(trend)}
                                </div>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; font-size:9px; color:var(--fleet-muted);">
                                <span>30d: <b style="color:var(--fleet-text);">${trend.this_week || 0}</b></span>
                                <span>Prev: <b style="color:var(--fleet-text);">${trend.last_week || 0}</b></span>
                            </div>
                        </div>`;
                    }
                    return ecoRow('#ef4444', 'Hard Braking', brk, brkTrend, 239)
                         + ecoRow('#f59e0b', 'Hard Acceleration', acc, accTrend, 245)
                         + ecoRow('#a855f7', 'Hard Cornering', crn, crnTrend, 168)
                         + ecoRow('#3b82f6', 'Excessive Idle', idle, idleTrend, 59)
                         + ecoRow('#06b6d4', 'Overspeed', spd, spdTrend, 6)
                         + ecoRow('#f97316', 'Harsh Driving (All)', harsh, harshTrend, 249);
                })()}
            </div>
            <div style="padding:8px 12px; background:rgba(34,197,94,0.06); border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:11px; font-weight:700; color:var(--fleet-text);">Total Eco Events</span>
                <span style="font-size:16px; font-weight:800; color:#22c55e;">${harsh.toLocaleString()}</span>
            </div>
        </div>

        <!-- CARD 2: Severity Breakdown -->
        <div style="background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:16px; padding:20px; display:flex; flex-direction:column; gap:16px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:36px; height:36px; border-radius:10px; background:rgba(245,158,11,0.12); display:flex; align-items:center; justify-content:center;">
                    <i data-lucide="pie-chart" style="width:18px; height:18px; color:#f59e0b;"></i>
                </div>
                <span style="font-size:14px; font-weight:800; color:var(--fleet-text);">Severity Breakdown</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:12px;">
                ${(() => {
                    const ctx = data.severityContext || {};
                    const critCtx = ctx.critical?.context || '';
                    const warnCtx = ctx.warning?.context || '';
                    const infoCtx = ctx.info?.context || '';
                    const sevDefs = {
                        critical: 'Offline vehicles (>5 days), safety critical (accident, fatigue)',
                        warning: 'Geofence breaches, device issues (battery, power off, fault)',
                        info: 'Routine ignition/movement, maintenance, custom alerts'
                    };
                    function sevRow(color, label, count, pct, sevKey, dynamicCtx) {
                        const def = sevDefs[sevKey] || '';
                        const display = dynamicCtx || def;
                        return `
                        <div style="padding:10px 12px; background:rgba(255,255,255,0.02); border-radius:10px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <div style="width:10px; height:10px; border-radius:3px; background:${color};"></div>
                                    <span style="font-size:12px; font-weight:600; color:var(--fleet-text);">${label}</span>
                                </div>
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <span style="font-size:16px; font-weight:800; color:${color};">${count.toLocaleString()}</span>
                                    <span style="font-size:11px; color:var(--fleet-muted);">${pct}%</span>
                                </div>
                            </div>
                            <div style="width:100%; height:6px; border-radius:3px; background:rgba(255,255,255,0.05); overflow:hidden; margin:6px 0 0;">
                                <div style="height:100%; width:${Math.max(pct, 2)}%; background:${color}; border-radius:3px;"></div>
                            </div>
                            <div style="font-size:10px; color:var(--fleet-muted); margin-top:6px; line-height:1.4; padding:4px 8px; background:rgba(255,255,255,0.02); border-radius:6px; border-left:2px solid ${color}40;">
                                ${_escHtml(display)}
                            </div>
                        </div>`;
                    }
                    return sevRow('#ef4444', 'Critical', critCount, critPct, 'critical', critCtx)
                         + sevRow('#f59e0b', 'Warning', warnCount, warnPct, 'warning', warnCtx)
                         + sevRow('#3b82f6', 'Info', infoCount, infoPct, 'info', infoCtx);
                })()}
                <div style="width:100%; height:8px; border-radius:4px; background:rgba(255,255,255,0.05); overflow:hidden; display:flex; margin-top:4px;">
                    <div style="height:100%; width:${critPct}%; background:#ef4444; border-radius:4px 0 0 4px;"></div>
                    <div style="height:100%; width:${warnPct}%; background:#f59e0b;"></div>
                    <div style="height:100%; width:${infoPct}%; background:#3b82f6; border-radius:0 4px 4px 0;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:4px; font-size:11px; color:var(--fleet-muted);">
                    <span>Unread: <b style="color:var(--fleet-text);">${data.unread?.toLocaleString() || 0}</b></span>
                    <span>Acknowledged: <b style="color:#22c55e;">${data.acknowledged?.toLocaleString() || 0}</b></span>
                </div>
            </div>
        </div>

        <!-- CARD 3: Top Offenders -->
        <div style="background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:16px; padding:20px; display:flex; flex-direction:column; gap:16px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:36px; height:36px; border-radius:10px; background:rgba(239,68,68,0.12); display:flex; align-items:center; justify-content:center;">
                    <i data-lucide="trophy" style="width:18px; height:18px; color:#ef4444;"></i>
                </div>
                <span style="font-size:14px; font-weight:800; color:var(--fleet-text);">Top Offenders</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
                ${topVehicles.length === 0 ? '<div style="text-align:center; color:var(--fleet-muted); font-size:12px; padding:20px;">No data available</div>' :
                topVehicles.map((v, i) => {
                    const maxTotal = topVehicles[0]?.total || 1;
                    const barWidth = Math.round(v.total / maxTotal * 100);
                    const rankColors = ['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#6b7280'];
                    const rankColor = rankColors[i] || '#6b7280';
                    return `
                    <div style="display:flex; align-items:center; gap:10px; padding:8px 10px; background:rgba(255,255,255,0.02); border-radius:8px; cursor:pointer; transition:background 0.15s;" onmouseover="this.style.background='var(--fleet-hover,rgba(59,130,246,0.04))'" onmouseout="this.style.background='rgba(255,255,255,0.02)'" onclick="document.getElementById('alerts-page-vehicle').value='${v.vehicle}'; _alertsSummaryLoaded=false; loadAlertsPage();">
                        <span style="width:20px; height:20px; border-radius:50%; background:${rankColor}; color:#fff; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:800; flex-shrink:0;">${i + 1}</span>
                        <div style="flex:1; min-width:0;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <span style="font-size:12px; font-weight:700; color:var(--fleet-text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${_escHtml(v.vehicle)}</span>
                                <span style="font-size:11px; color:var(--fleet-muted); flex-shrink:0;">${v.total}</span>
                            </div>
                            <div style="width:100%; height:4px; border-radius:2px; background:rgba(255,255,255,0.05); overflow:hidden;">
                                <div style="height:100%; width:${barWidth}%; background:${rankColor}; border-radius:2px;"></div>
                            </div>
                            <div style="display:flex; gap:6px; margin-top:3px; font-size:9px; color:var(--fleet-muted);">
                                <span style="color:#ef4444;">B:${v.braking}</span>
                                <span style="color:#f59e0b;">A:${v.accel}</span>
                                <span style="color:#a855f7;">C:${v.cornering}</span>
                                <span style="color:#3b82f6;">S:${v.speeding}</span>
                                <span style="color:#06b6d4;">I:${v.idle || 0}</span>
                            </div>
                        </div>
                    </div>`;
                }).join('')}
            </div>
        </div>
    `;
    if (typeof lucide !== 'undefined') lucide.createIcons();
    renderAlertTrendChart(data.daily_trend || []);
}

function renderAlertTrendChart(daily) {
    const el = document.getElementById('alerts-trend-chart');
    if (!el || !daily || daily.length === 0) { if (el) el.innerHTML = ''; return; }

    const maxCount = Math.max(...daily.map(d => d.count), 1);
    const totalAlerts = daily.reduce((s, d) => s + d.count, 0);
    const avgDaily = Math.round(totalAlerts / daily.length);
    const today = daily[daily.length - 1];
    const yesterday = daily.length > 1 ? daily[daily.length - 2] : null;
    const trendPct = yesterday && yesterday.count > 0 ? Math.round(((today.count - yesterday.count) / yesterday.count) * 100) : 0;
    const trendColor = trendPct > 0 ? '#ef4444' : trendPct < 0 ? '#22c55e' : '#6b7280';
    const trendArrow = trendPct > 0 ? '&#9650;' : trendPct < 0 ? '&#9660;' : '&#9654;';
    const bestDay = daily.reduce((min, d) => d.count < min.count ? d : min, daily[0]);
    const worstDay = daily.reduce((max, d) => d.count > max.count ? d : max, daily[0]);

    const barGradients = daily.map(d => {
        const ratio = d.count / maxCount;
        if (ratio > 0.8) return ['#ef4444', '#dc2626'];
        if (ratio > 0.5) return ['#f59e0b', '#d97706'];
        if (ratio > 0.25) return ['#3b82f6', '#2563eb'];
        return ['#60a5fa', '#3b82f6'];
    });

    const weekDays = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

    el.innerHTML = `
        <div style="background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:16px; padding:24px; overflow:hidden;">
            <!-- Header with title and export buttons -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:40px; height:40px; border-radius:12px; background:linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.15)); display:flex; align-items:center; justify-content:center;">
                        <i data-lucide="bar-chart-3" style="width:20px; height:20px; color:#3b82f6;"></i>
                    </div>
                    <div>
                        <div style="font-size:15px; font-weight:800; color:var(--fleet-text);">Alert Trend</div>
                        <div style="font-size:11px; color:var(--fleet-muted);">Last ${daily.length} days overview</div>
                    </div>
                </div>
                <div style="display:flex; gap:6px; align-items:center;">
                    <button onclick="exportAlertTrend('csv')" style="padding:6px 12px; border-radius:8px; border:1px solid var(--fleet-border); background:var(--fleet-card-bg); color:var(--fleet-text); font-size:11px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:4px; transition:all 0.15s;" onmouseover="this.style.background='var(--fleet-hover,rgba(59,130,246,0.04))'" onmouseout="this.style.background='var(--fleet-card-bg)'"><i data-lucide="download" style="width:12px; height:12px;"></i> CSV</button>
                    <button onclick="exportAlertTrend('copy')" style="padding:6px 12px; border-radius:8px; border:1px solid var(--fleet-border); background:var(--fleet-card-bg); color:var(--fleet-text); font-size:11px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:4px; transition:all 0.15s;" onmouseover="this.style.background='var(--fleet-hover,rgba(59,130,246,0.04))'" onmouseout="this.style.background='var(--fleet-card-bg)'"><i data-lucide="copy" style="width:12px; height:12px;"></i> Copy</button>
                </div>
            </div>

            <!-- Stats Row -->
            <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:12px; margin-bottom:24px;">
                <div style="text-align:center; padding:12px 8px; background:rgba(59,130,246,0.06); border-radius:10px;">
                    <div style="font-size:20px; font-weight:800; color:#3b82f6;">${today?.count || 0}</div>
                    <div style="font-size:10px; color:var(--fleet-muted); font-weight:600;">Today</div>
                </div>
                <div style="text-align:center; padding:12px 8px; background:rgba(255,255,255,0.03); border-radius:10px;">
                    <div style="font-size:20px; font-weight:800; color:var(--fleet-text);">${yesterday?.count || 0}</div>
                    <div style="font-size:10px; color:var(--fleet-muted); font-weight:600;">Yesterday</div>
                </div>
                <div style="text-align:center; padding:12px 8px; background:rgba(255,255,255,0.03); border-radius:10px;">
                    <div style="font-size:20px; font-weight:800; color:${trendColor};">${trendArrow} ${Math.abs(trendPct)}%</div>
                    <div style="font-size:10px; color:var(--fleet-muted); font-weight:600;">vs Yesterday</div>
                </div>
                <div style="text-align:center; padding:12px 8px; background:rgba(34,197,94,0.06); border-radius:10px;">
                    <div style="font-size:20px; font-weight:800; color:#22c55e;">${bestDay.count}</div>
                    <div style="font-size:10px; color:var(--fleet-muted); font-weight:600;">Best Day</div>
                    <div style="font-size:9px; color:var(--fleet-muted);">${new Date(bestDay.date).toLocaleDateString('en-US', {month:'short', day:'numeric'})}</div>
                </div>
                <div style="text-align:center; padding:12px 8px; background:rgba(239,68,68,0.06); border-radius:10px;">
                    <div style="font-size:20px; font-weight:800; color:#ef4444;">${worstDay.count}</div>
                    <div style="font-size:10px; color:var(--fleet-muted); font-weight:600;">Worst Day</div>
                    <div style="font-size:9px; color:var(--fleet-muted);">${new Date(worstDay.date).toLocaleDateString('en-US', {month:'short', day:'numeric'})}</div>
                </div>
            </div>

            <!-- Chart Area -->
            <div style="position:relative; height:160px; margin-bottom:12px;">
                <!-- Grid lines -->
                <div style="position:absolute; top:0; left:0; right:0; bottom:24px; display:flex; flex-direction:column; justify-content:space-between; pointer-events:none;">
                    ${[1,0.75,0.5,0.25,0].map(p => `<div style="border-bottom:1px dashed rgba(255,255,255,0.06); position:relative;"><span style="position:absolute; left:-2px; top:-8px; font-size:9px; color:var(--fleet-muted);">${Math.round(maxCount * p)}</span></div>`).join('')}
                </div>
                <!-- Bars -->
                <div style="position:absolute; top:8px; left:36px; right:0; bottom:24px; display:flex; align-items:flex-end; gap:${Math.max(2, 8 - daily.length)}px;">
                    ${daily.map((d, i) => {
                        const h = Math.max(3, (d.count / maxCount) * 100);
                        const dateLabel = new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                        const dayName = weekDays[new Date(d.date).getDay()];
                        const isToday = i === daily.length - 1;
                        const grad = barGradients[i];
                        return `<div style="flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; position:relative;" onmouseenter="document.getElementById('tooltip-${i}').style.display='block'" onmouseleave="document.getElementById('tooltip-${i}').style.display='none'">
                            <div id="tooltip-${i}" style="display:none; position:absolute; bottom:calc(${h}% + 8px); left:50%; transform:translateX(-50%); background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:8px; padding:6px 10px; font-size:10px; white-space:nowrap; z-index:10; box-shadow:0 4px 12px rgba(0,0,0,0.2);">
                                <div style="font-weight:700; color:var(--fleet-text);">${dateLabel} (${dayName})</div>
                                <div style="color:var(--fleet-muted);">${d.count} alerts</div>
                            </div>
                            <div style="width:100%; max-width:${daily.length > 10 ? 28 : 36}px; height:${h}%; border-radius:4px 4px 0 0; background:linear-gradient(180deg, ${grad[0]}, ${grad[1]}); opacity:${isToday ? 1 : 0.75}; transition:all 0.2s; cursor:pointer; ${isToday ? 'box-shadow:0 0 8px ' + grad[0] + '40;' : ''}" onmouseover="this.style.opacity=1; this.style.transform='scaleY(1.02)'" onmouseout="this.style.opacity=${isToday ? 1 : 0.75}; this.style.transform='scaleY(1)'"></div>
                            <div style="font-size:${daily.length > 10 ? '8' : '9'}px; color:var(--fleet-muted); margin-top:4px; ${isToday ? 'font-weight:700; color:var(--fleet-text);' : ''}">${dayName}</div>
                        </div>`;
                    }).join('')}
                </div>
            </div>

            <!-- Legend -->
            <div style="display:flex; justify-content:space-between; align-items:center; padding-top:12px; border-top:1px solid var(--fleet-border);">
                <div style="display:flex; gap:14px; font-size:10px; color:var(--fleet-muted);">
                    <span style="display:flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; border-radius:3px; background:linear-gradient(180deg, #ef4444, #dc2626);"></span> High (&gt;80%)</span>
                    <span style="display:flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; border-radius:3px; background:linear-gradient(180deg, #f59e0b, #d97706);"></span> Medium (50-80%)</span>
                    <span style="display:flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; border-radius:3px; background:linear-gradient(180deg, #3b82f6, #2563eb);"></span> Low (25-50%)</span>
                    <span style="display:flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; border-radius:3px; background:linear-gradient(180deg, #60a5fa, #3b82f6);"></span> Minimal (&lt;25%)</span>
                </div>
                <div style="font-size:10px; color:var(--fleet-muted);">Avg: <b style="color:var(--fleet-text);">${avgDaily}</b>/day | Total: <b style="color:var(--fleet-text);">${totalAlerts.toLocaleString()}</b></div>
            </div>
        </div>
    `;
    if (typeof lucide !== 'undefined') lucide.createIcons();
    window._lastAlertTrendData = daily;
}

function exportAlertTrend(format) {
    const daily = window._lastAlertTrendData;
    if (!daily || !daily.length) return;
    if (format === 'csv') {
        let csv = 'Date,Day,Alerts\n';
        daily.forEach(d => {
            const day = new Date(d.date).toLocaleDateString('en-US', { weekday: 'long' });
            csv += `${d.date},${day},${d.count}\n`;
        });
        const blob = new Blob([csv], { type: 'text/csv' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'alert_trend.csv';
        a.click();
    } else if (format === 'copy') {
        const text = daily.map(d => {
            const day = new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', weekday: 'short' });
            return `${day}: ${d.count} alerts`;
        }).join('\n');
        navigator.clipboard.writeText(`Alert Trend (Last ${daily.length} Days)\n${'─'.repeat(30)}\n${text}`).then(() => {
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed; bottom:24px; right:24px; padding:12px 20px; border-radius:10px; background:rgba(34,197,94,0.95); color:#fff; font-size:13px; font-weight:600; z-index:99999; box-shadow:0 4px 20px rgba(0,0,0,0.2);';
            toast.textContent = 'Trend data copied!';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2000);
        });
    }
}

async function loadAlertsPage() {
    const type = document.getElementById('alerts-page-type')?.value || '';
    const severity = document.getElementById('alerts-page-severity')?.value || '';
    const dateFrom = document.getElementById('alerts-page-date-from')?.value || '';
    const dateTo = document.getElementById('alerts-page-date-to')?.value || '';
    const vehicle = document.getElementById('alerts-page-vehicle')?.value || '';
    const isRead = document.getElementById('alerts-page-read')?.value || '';

    const params = new URLSearchParams();
    if (type) params.set('alert_type', type);
    if (severity) params.set('severity', severity);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    if (vehicle) params.set('vehicle', vehicle);
    if (isRead !== '') params.set('is_read', isRead);
    params.set('limit', _alertsPageLimit);
    params.set('offset', _alertsPageOffset);

    try {
        const res = await fetch(`/api/fleet/fdb/alerts?${params}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        renderAlertsPageStats(data.total, data.unread);
        renderAlertsPageTable(data.alerts);
        renderAlertsPagePagination(data.total);
        updateAlertBellBadge(data.unread);
        loadAlertsSummary();

        const title = document.getElementById('alerts-page-title');
        if (title) {
            let filterText = [];
            if (type) filterText.push(type.replace(/_/g, ' '));
            if (severity) filterText.push(severity);
            if (dateFrom || dateTo) filterText.push(`${dateFrom || 'start'} to ${dateTo || 'now'}`);
            title.textContent = filterText.length ? `Alerts: ${filterText.join(' | ')}` : 'All Alerts';
        }
    } catch (e) {
        console.error('Alerts page load error:', e);
        document.getElementById('alerts-page-body').innerHTML = '<tr><td colspan="10" style="padding:40px; text-align:center; color:var(--brand-danger);">Failed to load alerts</td></tr>';
    }
}

function renderAlertsPageStats(total, unread) {
    const el = document.getElementById('alerts-page-stats');
    if (!el) return;
    el.innerHTML = `
        <div class="fleet-kpi-card" style="background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:16px; padding:20px;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <div style="width:40px; height:40px; border-radius:12px; background:rgba(59,130,246,0.12); display:flex; align-items:center; justify-content:center;">
                    <i data-lucide="bell" style="width:20px; height:20px; color:#3b82f6;"></i>
                </div>
                <span style="font-size:12px; color:var(--fleet-muted); text-transform:uppercase; font-weight:700;">Total</span>
            </div>
            <div style="font-size:28px; font-weight:800; color:var(--fleet-text);">${total}</div>
        </div>
        <div class="fleet-kpi-card" style="background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:16px; padding:20px;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <div style="width:40px; height:40px; border-radius:12px; background:rgba(239,68,68,0.12); display:flex; align-items:center; justify-content:center;">
                    <i data-lucide="alert-circle" style="width:20px; height:20px; color:#ef4444;"></i>
                </div>
                <span style="font-size:12px; color:var(--fleet-muted); text-transform:uppercase; font-weight:700;">Unread</span>
            </div>
            <div style="font-size:28px; font-weight:800; color:#ef4444;">${unread}</div>
        </div>
        <div class="fleet-kpi-card" style="background:var(--fleet-card-bg); border:1px solid var(--fleet-border); border-radius:16px; padding:20px;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <div style="width:40px; height:40px; border-radius:12px; background:rgba(245,158,11,0.12); display:flex; align-items:center; justify-content:center;">
                    <i data-lucide="alert-triangle" style="width:20px; height:20px; color:#f59e0b;"></i>
                </div>
                <span style="font-size:12px; color:var(--fleet-muted); text-transform:uppercase; font-weight:700;">Read</span>
            </div>
            <div style="font-size:28px; font-weight:800; color:#f59e0b;">${Math.max(0, total - unread)}</div>
        </div>
    `;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function renderAlertsPageTable(alerts) {
    const tbody = document.getElementById('alerts-page-body');
    if (!tbody) return;
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="padding:60px; text-align:center; color:var(--fleet-muted);"><i data-lucide="bell-off" style="width:48px; height:48px; margin-bottom:12px; opacity:0.3;"></i><br>No alerts found</td></tr>';
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return;
    }

    const sevIcons = { critical: 'alert-circle', warning: 'alert-triangle', info: 'info' };
    const sevColors = { critical: '#ef4444', warning: '#f59e0b', info: '#3b82f6' };
    const sevBg = { critical: 'rgba(239,68,68,0.12)', warning: 'rgba(245,158,11,0.12)', info: 'rgba(59,130,246,0.12)' };
    const typeLabels = {
        'hard_acceleration': 'Hard Acceleration', 'hard_braking': 'Hard Braking', 'hard_cornering': 'Hard Cornering',
        'overspeed': 'Overspeed', 'speed_alert': 'Speed Alert', 'device_moving': 'Moving', 'device_stopped': 'Stopped',
        'device_online': 'Online', 'device_offline': 'Offline', 'ignition_on': 'Ignition On', 'ignition_off': 'Ignition Off',
        'driver_changed': 'Driver Changed', 'jamming': 'GPS Jamming', 'fatigue_driving': 'Fatigue Driving',
        'accident': 'Accident', 'low_battery': 'Low Battery', 'power_off': 'Power Off', 'fault': 'Device Fault',
        'excessive_idle': 'Excessive Idle', 'idle_alert': 'Idle Alert', 'maintenance': 'Maintenance', 'imei_missing': 'IMEI Missing',
        'geofence_enter': 'Geofence Enter', 'geofence_exit': 'Geofence Exit', 'custom_alert': 'Custom Alert'
    };

    tbody.innerHTML = alerts.map(a => {
        const icon = sevIcons[a.severity] || 'bell';
        const color = sevColors[a.severity] || '#6b7280';
        const bg = sevBg[a.severity] || 'rgba(107,114,128,0.12)';
        const time = new Date(a.created_at).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' });
        const readStyle = a.is_read ? 'opacity:0.55;' : '';
        const label = typeLabels[a.alert_type] || a.alert_type.replace(/_/g, ' ');
        const ackBtn = a.is_acknowledged ? `<span style="padding:3px 8px; border-radius:6px; background:rgba(34,197,94,0.12); color:#22c55e; font-size:10px; font-weight:700;">ACK</span>` : `<button onclick="event.stopPropagation(); acknowledgeAlert(${a.id}); loadAlertsPage();" style="padding:4px 10px; border-radius:6px; border:1px solid rgba(34,197,94,0.3); background:rgba(34,197,94,0.08); color:#22c55e; font-size:10px; font-weight:700; cursor:pointer;">Acknowledge</button>`;
        const actionTd = `<select onclick="event.stopPropagation()" onchange="setAlertAction(${a.id}, this.value); loadAlertsPage(); this.value=''" style="padding:4px 8px; border-radius:6px; border:1px solid var(--fleet-border); background:var(--fleet-card-bg); color:var(--fleet-text); font-size:10px; cursor:pointer;">
            <option value="">${a.action_taken ? a.action_taken.charAt(0).toUpperCase() + a.action_taken.slice(1) : 'Action...'}</option>
            <option value="escalated">Escalate</option>
            <option value="dismissed">Dismiss</option>
            <option value="assigned">Assign</option>
            <option value="resolved">Resolve</option>
        </select>`;
        const shareBtns = `<div style="display:flex; gap:4px; align-items:center;">
            <button onclick="event.stopPropagation(); shareAlertEmail('${_escHtml(a.title)}', '${_escHtml(a.vehicle)}', '${_escHtml(a.message || '')}', '${a.severity}')" title="Email" style="padding:4px 6px; border-radius:6px; border:1px solid rgba(59,130,246,0.3); background:rgba(59,130,246,0.08); color:#3b82f6; cursor:pointer;"><i data-lucide="mail" style="width:12px; height:12px;"></i></button>
            <button onclick="event.stopPropagation(); shareAlertWhatsApp('${_escHtml(a.title)}', '${_escHtml(a.vehicle)}', '${_escHtml(a.message || '')}', '${a.severity}')" title="WhatsApp" style="padding:4px 6px; border-radius:6px; border:1px solid rgba(37,211,102,0.3); background:rgba(37,211,102,0.08); color:#25d366; cursor:pointer;"><i data-lucide="message-circle" style="width:12px; height:12px;"></i></button>
            <button onclick="event.stopPropagation(); copyAlertLink(${a.id}, '${_escHtml(a.title)}', '${_escHtml(a.vehicle)}', '${_escHtml(a.message || '')}')" title="Copy" style="padding:4px 6px; border-radius:6px; border:1px solid rgba(168,85,247,0.3); background:rgba(168,85,247,0.08); color:#a855f7; cursor:pointer;"><i data-lucide="copy" style="width:12px; height:12px;"></i></button>
            ${a.alert_type === 'custom_alert' ? `<button onclick="event.stopPropagation(); deleteCustomAlert(${a.id}, '${_escHtml(a.title)}')" title="Delete custom alert" style="padding:4px 8px; border-radius:6px; border:1px solid rgba(239,68,68,0.5); background:rgba(239,68,68,0.15); color:#ef4444; cursor:pointer; font-size:10px; font-weight:800;"><i data-lucide="trash-2" style="width:11px; height:11px;"></i> Delete</button>` : `<button onclick="event.stopPropagation(); dismissAlert(${a.id})" title="Dismiss" style="padding:4px 6px; border-radius:6px; border:1px solid rgba(239,68,68,0.3); background:rgba(239,68,68,0.08); color:#ef4444; cursor:pointer;"><i data-lucide="x" style="width:12px; height:12px;"></i></button>`}
        </div>`;
        return `<tr style="${readStyle} border-bottom:1px solid var(--fleet-border); cursor:pointer; transition:background 0.15s;" onmouseover="this.style.background='var(--fleet-hover,rgba(59,130,246,0.04))'" onmouseout="this.style.background=''" onclick="markAlertRead(${a.id}); loadAlertsPage();">
            <td style="padding:10px 16px;"><i data-lucide="${icon}" style="width:18px; height:18px; color:${color};"></i></td>
            <td style="padding:10px 16px; font-weight:700; font-size:13px; white-space:nowrap;">${_escHtml(a.vehicle)}</td>
            <td style="padding:10px 16px;"><span style="padding:3px 10px; border-radius:6px; background:${bg}; color:${color}; font-size:11px; font-weight:700; white-space:nowrap;">${label}</span></td>
            <td style="padding:10px 16px;"><span class="alert-severity-badge ${a.severity}" style="text-transform:capitalize;">${a.severity}</span></td>
            <td style="padding:10px 16px; font-weight:600; font-size:13px; white-space:nowrap;">${_escHtml(a.title)}</td>
            <td style="padding:10px 16px; font-size:12px; color:var(--fleet-muted); max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${_escHtml(a.message || '')}</td>
            <td style="padding:10px 16px; font-size:12px; color:var(--fleet-muted); white-space:nowrap;">${time}</td>
            <td style="padding:10px 16px; white-space:nowrap;" onclick="event.stopPropagation()">${ackBtn}</td>
            <td style="padding:10px 16px; white-space:nowrap;" onclick="event.stopPropagation()">${actionTd}</td>
            <td style="padding:10px 16px; white-space:nowrap;" onclick="event.stopPropagation()">${shareBtns}</td>
        </tr>`;
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function renderAlertsPagePagination(total) {
    const el = document.getElementById('alerts-page-pagination');
    if (!el) return;
    const totalPages = Math.ceil(total / _alertsPageLimit);
    const currentPage = Math.floor(_alertsPageOffset / _alertsPageLimit) + 1;
    el.innerHTML = `
        <span style="font-size:12px; color:var(--fleet-muted);">Showing ${_alertsPageOffset + 1}-${Math.min(_alertsPageOffset + _alertsPageLimit, total)} of ${total}</span>
        <div style="display:flex; gap:8px;">
            <button class="glass-btn secondary" style="padding:6px 14px; font-size:12px;" ${currentPage <= 1 ? 'disabled' : ''} onclick="_alertsPageOffset = Math.max(0, _alertsPageOffset - _alertsPageLimit); loadAlertsPage();">Previous</button>
            <span style="padding:6px 14px; font-size:12px; color:var(--fleet-muted);">Page ${currentPage} of ${totalPages}</span>
            <button class="glass-btn secondary" style="padding:6px 14px; font-size:12px;" ${currentPage >= totalPages ? 'disabled' : ''} onclick="_alertsPageOffset += _alertsPageLimit; loadAlertsPage();">Next</button>
        </div>
    `;
}

// ============================================================================
// ALERT PREFERENCES FUNCTIONS
// ============================================================================
function closeAlertPreferences() {
    const modal = document.getElementById('alert-preferences-modal');
    if (modal) modal.classList.add('hidden-view');
}

function filterAlertTypes() {
    const search = (document.getElementById('alert-type-search')?.value || '').toLowerCase();
    const grid = document.getElementById('alert-types-selection-grid');
    if (!grid) return;
    grid.querySelectorAll('.alert-type-item').forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(search) ? '' : 'none';
    });
}

function selectAllAlerts(select) {
    const grid = document.getElementById('alert-types-selection-grid');
    if (!grid) return;
    grid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.checked = select;
    });
}

async function saveAlertPreferences() {
    const grid = document.getElementById('alert-types-selection-grid');
    if (!grid) return;
    const prefs = {};
    grid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        prefs[cb.dataset.type] = cb.checked;
    });
    try {
        const res = await fetch('/api/fleet/fdb/alerts/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify({ preferences: prefs })
        });
        if (res.ok) {
            closeAlertPreferences();
        }
    } catch (e) {
        console.error('Failed to save alert preferences:', e);
    }
}

// ── Driver Intelligence ──────────────────────────────────────────────────────
let driverViewInitialized = false;
let driverCurrentPeriod = 30;
let driverLeaderboardData = [];

function initDriverView() {
    if (!driverViewInitialized) {
        driverViewInitialized = true;
        loadDriverSummaryStats();
        loadDriverLeaderboard(30);
    }
    if (selectedVehicle) {
        const input = document.getElementById('driver-vehicle-search');
        if (input) input.value = selectedVehicle.name || selectedVehicle.id;
        loadDriverAnalytics(selectedVehicle.id);
    }
}

let _driverSearchDebounce = null;

function searchDriverVehicles(query) {
    const container = document.getElementById('driver-search-results');
    if (!container) return;
    clearTimeout(_driverSearchDebounce);
    _driverSearchDebounce = setTimeout(() => {
        fetch(`/api/analytics/driver/search?q=${encodeURIComponent(query || '')}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
            .then(r => r.ok ? r.json() : [])
            .then(devices => {
                if (!devices || !devices.length) {
                    container.innerHTML = '<div style="padding:12px; color:#94a3b8; font-size:0.8rem;">No vehicles found</div>';
                    container.style.display = 'block';
                    return;
                }
                container.innerHTML = devices.map(d => {
                    const statusColor = d.status === 'online' ? '#10b981' : d.status === 'offline' ? '#ef4444' : '#94a3b8';
                    const srcBadge = d.source === 'traccar'
                        ? '<span style="font-size:0.6rem; padding:1px 5px; border-radius:4px; background:rgba(99,102,241,0.1); color:#6366f1; font-weight:600;">GPS</span>'
                        : '<span style="font-size:0.6rem; padding:1px 5px; border-radius:4px; background:rgba(245,158,11,0.1); color:#f59e0b; font-weight:600;">FLEET</span>';
                    const onclick = d.id
                        ? `selectDriverVehicle(${d.id}, '${(d.name||'').replace(/'/g,"\\'")}', 'traccar')`
                        : `selectDriverVehicle(null, '${(d.name||'').replace(/'/g,"\\'")}', 'fleet_alerts')`;
                    return `<div class="driver-search-item" onclick="${onclick}" style="padding:8px 12px; cursor:pointer; border-bottom:1px solid #f1f5f9; display:flex; align-items:center; gap:8px; transition:0.15s;" onmouseover="this.style.background='#f0f4ff'" onmouseout="this.style.background=''">
                        <span style="width:8px; height:8px; border-radius:50%; background:${statusColor}; flex-shrink:0;"></span>
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:600; font-size:0.82rem; color:#1e293b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${d.name || d.id}</div>
                            <div style="font-size:0.7rem; color:#94a3b8;">${d.id ? 'ID: ' + d.id : 'Fleet vehicle'}</div>
                        </div>
                        ${srcBadge}
                    </div>`;
                }).join('');
                container.style.display = 'block';
            })
            .catch(() => { container.style.display = 'none'; });
    }, 200);
}

function selectDriverVehicle(deviceId, name, source) {
    const input = document.getElementById('driver-vehicle-search');
    const container = document.getElementById('driver-search-results');
    if (input) input.value = name || '';
    if (container) container.style.display = 'none';
    if (source === 'fleet_alerts' || !deviceId) {
        loadDriverAnalyticsByName(name);
    } else {
        loadDriverAnalytics(deviceId);
    }
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('#driver-search-container')) {
        const c = document.getElementById('driver-search-results');
        if (c) c.style.display = 'none';
    }
    if (!e.target.closest('#compare-search-a-container')) {
        const c = document.getElementById('compare-results-a');
        if (c) c.style.display = 'none';
    }
    if (!e.target.closest('#compare-search-b-container')) {
        const c = document.getElementById('compare-results-b');
        if (c) c.style.display = 'none';
    }
});

function changeDriverPeriod(days, btn) {
    driverCurrentPeriod = days;
    document.querySelectorAll('.driver-period-btn').forEach(b => {
        b.classList.remove('active');
        b.style.background = '#ffffff';
        b.style.color = '#94a3b8';
        b.style.borderColor = '#dbe3ee';
    });
    btn.classList.add('active');
    btn.style.background = 'linear-gradient(135deg,#818cf8,#6366f1)';
    btn.style.color = '#ffffff';
    btn.style.borderColor = 'transparent';
    loadDriverLeaderboard(days);
}

function loadDriverSummaryStats() {
    fetch('/api/analytics/driver/summary/stats', { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.ok ? r.json() : {})
        .then(d => {
            setTextSafe('drv-total-drivers', d.total_drivers || 0);
            setTextSafe('drv-avg-score', d.avg_eco_score || 100);
            setTextSafe('drv-total-events', (d.total_events_30d || 0).toLocaleString());
            setTextSafe('drv-brakes-30d', (d.harsh_braking_30d || 0).toLocaleString());
            setTextSafe('drv-safe-count', d.safe_drivers_count || 0);
        })
        .catch(() => {});
}

function loadDriverLeaderboard(days) {
    const tbody = document.getElementById('driver-leaderboard-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:24px;color:#94a3b8;">Loading leaderboard...</td></tr>';

    fetch(`/api/analytics/driver/leaderboard?days=${days}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.ok ? r.json() : [])
        .then(data => {
            driverLeaderboardData = data || [];
            if (!driverLeaderboardData.length) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:24px;color:#94a3b8;">No driver data available</td></tr>';
                return;
            }
            tbody.innerHTML = driverLeaderboardData.map(d => {
                const score = d.score || 0;
                const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
                const scoreBg = score >= 80 ? 'rgba(16,185,129,0.08)' : score >= 60 ? 'rgba(245,158,11,0.08)' : 'rgba(239,68,68,0.08)';
                const rankMedal = d.rank <= 3 ? ['🥇','🥈','🥉'][d.rank - 1] : `#${d.rank}`;
                const perfWidth = Math.min(100, score);
                return `<tr style="border-bottom:1px solid #f1f5f9; cursor:pointer; transition:0.15s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background=''" onclick="loadDriverAnalyticsByVehicle('${(d.vehicle||'').replace(/'/g,"\\'")}')">
                    <td style="padding:10px 14px; font-weight:700; font-size:0.85rem;">${rankMedal}</td>
                    <td style="padding:10px 14px; font-weight:600; color:#1e293b; font-size:0.82rem;">${d.name || 'Unknown'}</td>
                    <td style="padding:10px 14px; color:#64748b; font-size:0.78rem;">${d.vehicle || '-'}</td>
                    <td style="padding:10px 14px;"><span style="display:inline-block; padding:3px 10px; border-radius:8px; background:${scoreBg}; color:${scoreColor}; font-weight:800; font-size:0.82rem;">${score}</span></td>
                    <td style="padding:10px 14px; color:#ef4444; font-weight:600; font-size:0.8rem;">${d.brake || 0}</td>
                    <td style="padding:10px 14px; color:#f59e0b; font-weight:600; font-size:0.8rem;">${d.accel || 0}</td>
                    <td style="padding:10px 14px; color:#f97316; font-weight:600; font-size:0.8rem;">${d.corner || 0}</td>
                    <td style="padding:10px 14px; color:#64748b; font-size:0.8rem;">${d.trips || 0}</td>
                    <td style="padding:10px 14px; width:120px;">
                        <div style="height:6px; background:#f1f5f9; border-radius:3px; overflow:hidden;">
                            <div style="width:${perfWidth}%; height:100%; background:${scoreColor}; border-radius:3px;"></div>
                        </div>
                    </td>
                </tr>`;
            }).join('');
        })
        .catch(() => {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:24px;color:#94a3b8;">Failed to load leaderboard</td></tr>';
        });
}

function loadDriverAnalyticsByVehicle(vehicleName) {
    if (!vehicleName) return;
    const input = document.getElementById('driver-vehicle-search');
    if (input) input.value = vehicleName;
    fetch(`/api/analytics/driver/search?q=${encodeURIComponent(vehicleName)}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.ok ? r.json() : [])
        .then(results => {
            const exact = results.find(d => d.name === vehicleName);
            if (exact) {
                if (exact.id) {
                    loadDriverAnalytics(exact.id);
                } else {
                    loadDriverAnalyticsByName(vehicleName);
                }
            } else if (results.length > 0) {
                const first = results[0];
                if (first.id) {
                    loadDriverAnalytics(first.id);
                } else {
                    loadDriverAnalyticsByName(vehicleName);
                }
            } else {
                loadDriverAnalyticsByName(vehicleName);
            }
        })
        .catch(() => {
            loadDriverAnalyticsByName(vehicleName);
        });
}

function loadDriverAnalytics(deviceId) {
    if (!deviceId) return;

    fetch(`/api/analytics/driver/${deviceId}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data || data.error) {
                setTextSafe('intel-driver-name', 'No Driver Data');
                setTextSafe('intel-vehicle-name', data?.error || 'No driver assigned');
                setTextSafe('intel-eco-score', '--');
                const bar = document.getElementById('intel-score-bar');
                if (bar) { bar.style.width = '0%'; bar.style.background = '#e2e8f0'; }
                const avatar = document.getElementById('intel-driver-avatar');
                if (avatar) avatar.textContent = '?';
                return;
            }

            setTextSafe('intel-driver-name', data.driver_name || 'Unknown');
            setTextSafe('intel-vehicle-name', data.vehicle_name || '');
            setTextSafe('intel-driver-id', data.driver_id || '-');
            setTextSafe('intel-last-activity', data.last_activity ? new Date(data.last_activity).toLocaleDateString('en', { year:'numeric', month:'short', day:'numeric' }) : '-');
            setTextSafe('intel-eco-score', data.eco_score);

            const scoreColor = data.eco_score >= 80 ? '#10b981' : data.eco_score >= 60 ? '#f59e0b' : '#ef4444';
            const scoreEl = document.getElementById('intel-eco-score');
            if (scoreEl) scoreEl.style.color = scoreColor;

            const bar = document.getElementById('intel-score-bar');
            if (bar) {
                bar.style.width = data.eco_score + '%';
                bar.style.background = scoreColor;
            }

            const avatar = document.getElementById('intel-driver-avatar');
            if (avatar) {
                const name = data.driver_name || 'D';
                avatar.textContent = name.charAt(0).toUpperCase();
            }

            const badge = document.getElementById('intel-assignment-badge');
            if (badge) badge.style.display = data.auto_assigned ? 'inline-block' : 'none';

            const stats = data.stats || {};
            setTextSafe('stat-braking-total', stats.harsh_braking?.total || 0);
            setTextSafe('stat-braking-penalized', stats.harsh_braking?.penalized || 0);
            setTextSafe('stat-braking-grace', stats.harsh_braking?.grace_exempted || 0);
            setTextSafe('stat-acceleration', stats.harsh_acceleration || 0);
            setTextSafe('stat-cornering', stats.harsh_cornering || 0);
            setTextSafe('stat-idle-penalty', stats.idle_penalty || 0);
            setTextSafe('stat-idle-mins', (stats.idle_minutes || 0) + ' min');
        })
        .catch(() => {});
}

function loadDriverAnalyticsByName(vehicleName) {
    if (!vehicleName) return;
    fetch(`/api/analytics/driver/by-name/${encodeURIComponent(vehicleName)}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data || data.error) {
                setTextSafe('intel-driver-name', 'No Driver Data');
                setTextSafe('intel-vehicle-name', data?.error || 'No data for this vehicle');
                setTextSafe('intel-eco-score', '--');
                const bar = document.getElementById('intel-score-bar');
                if (bar) { bar.style.width = '0%'; bar.style.background = '#e2e8f0'; }
                const avatar = document.getElementById('intel-driver-avatar');
                if (avatar) avatar.textContent = '?';
                setTextSafe('intel-driver-id', '-');
                setTextSafe('intel-last-activity', '-');
                setTextSafe('stat-braking-total', 0);
                setTextSafe('stat-braking-penalized', 0);
                setTextSafe('stat-braking-grace', 0);
                setTextSafe('stat-acceleration', 0);
                setTextSafe('stat-cornering', 0);
                setTextSafe('stat-idle-penalty', 0);
                setTextSafe('stat-idle-mins', '0 min');
                return;
            }

            setTextSafe('intel-driver-name', data.driver_name || vehicleName);
            setTextSafe('intel-vehicle-name', data.vehicle_name || '');
            setTextSafe('intel-driver-id', data.driver_id || '-');
            setTextSafe('intel-last-activity', data.last_activity ? new Date(data.last_activity).toLocaleDateString('en', { year:'numeric', month:'short', day:'numeric' }) : '-');
            setTextSafe('intel-eco-score', data.eco_score);

            const scoreColor = data.eco_score >= 80 ? '#10b981' : data.eco_score >= 60 ? '#f59e0b' : '#ef4444';
            const scoreEl = document.getElementById('intel-eco-score');
            if (scoreEl) scoreEl.style.color = scoreColor;

            const bar = document.getElementById('intel-score-bar');
            if (bar) { bar.style.width = data.eco_score + '%'; bar.style.background = scoreColor; }

            const avatar = document.getElementById('intel-driver-avatar');
            if (avatar) { const n = data.driver_name || 'D'; avatar.textContent = n.charAt(0).toUpperCase(); }

            const stats = data.stats || {};
            setTextSafe('stat-braking-total', stats.harsh_braking?.total || 0);
            setTextSafe('stat-braking-penalized', stats.harsh_braking?.penalized || 0);
            setTextSafe('stat-braking-grace', stats.harsh_braking?.grace_exempted || 0);
            setTextSafe('stat-acceleration', stats.harsh_acceleration || 0);
            setTextSafe('stat-cornering', stats.harsh_cornering || 0);
            setTextSafe('stat-idle-penalty', stats.idle_penalty || 0);
            setTextSafe('stat-idle-mins', (stats.idle_minutes || 0) + ' min');
        })
        .catch(() => {});
}

function exportDriverLeaderboard() {
    if (!driverLeaderboardData.length) { showToast('No data to export', 'warning'); return; }
    let csv = 'Rank,Driver Name,Vehicle,Eco Score,Braking,Acceleration,Cornering,Trips\n';
    driverLeaderboardData.forEach(d => {
        csv += `${d.rank},"${d.name || ''}","${d.vehicle || ''}",${d.score},${d.brake||0},${d.accel||0},${d.corner||0},${d.trips||0}\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `driver-leaderboard-${new Date().toISOString().slice(0,10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
    showToast('Leaderboard exported!', 'success');
}

let _compareSearchDebounce = { a: null, b: null };
let _compareSelectedDevice = { a: null, b: null };

function openDriverCompareModal() {
    const section = document.getElementById('driver-compare-section');
    if (section) section.style.display = 'block';
    const inputA = document.getElementById('compare-search-a');
    if (inputA && !_compareSelectedDevice.a) {
        inputA.value = '';
        inputA.focus();
    }
}

function searchCompareVehicle(slot, query) {
    const container = document.getElementById(`compare-results-${slot}`);
    if (!container) return;
    clearTimeout(_compareSearchDebounce[slot]);
    _compareSearchDebounce[slot] = setTimeout(() => {
        fetch(`/api/analytics/driver/search?q=${encodeURIComponent(query || '')}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
            .then(r => r.ok ? r.json() : [])
            .then(devices => {
                if (!devices || !devices.length) {
                    container.innerHTML = '<div style="padding:12px; color:#94a3b8; font-size:0.8rem;">No vehicles found</div>';
                    container.style.display = 'block';
                    return;
                }
                container.innerHTML = devices.map(d => {
                    const statusColor = d.status === 'online' ? '#10b981' : d.status === 'offline' ? '#ef4444' : '#94a3b8';
                    const srcBadge = d.source === 'traccar'
                        ? '<span style="font-size:0.6rem; padding:1px 5px; border-radius:4px; background:rgba(99,102,241,0.1); color:#6366f1; font-weight:600;">GPS</span>'
                        : '<span style="font-size:0.6rem; padding:1px 5px; border-radius:4px; background:rgba(245,158,11,0.1); color:#f59e0b; font-weight:600;">FLEET</span>';
                    const onclick = d.id
                        ? `selectCompareVehicle('${slot}', ${d.id}, '${(d.name||'').replace(/'/g,"\\'")}', 'traccar')`
                        : `selectCompareVehicle('${slot}', null, '${(d.name||'').replace(/'/g,"\\'")}', 'fleet_alerts')`;
                    return `<div onclick="${onclick}" style="padding:8px 12px; cursor:pointer; border-bottom:1px solid #f1f5f9; display:flex; align-items:center; gap:8px; transition:0.15s;" onmouseover="this.style.background='#f0f4ff'" onmouseout="this.style.background=''">
                        <span style="width:8px; height:8px; border-radius:50%; background:${statusColor}; flex-shrink:0;"></span>
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:600; font-size:0.82rem; color:#1e293b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${d.name || d.id}</div>
                            <div style="font-size:0.7rem; color:#94a3b8;">${d.id ? 'ID: ' + d.id : 'Fleet vehicle'}</div>
                        </div>
                        ${srcBadge}
                    </div>`;
                }).join('');
                container.style.display = 'block';
            })
            .catch(() => { container.style.display = 'none'; });
    }, 200);
}

function selectCompareVehicle(slot, deviceId, name, source) {
    const input = document.getElementById(`compare-search-${slot}`);
    const container = document.getElementById(`compare-results-${slot}`);
    if (input) input.value = name || '';
    if (container) container.style.display = 'none';
    _compareSelectedDevice[slot] = deviceId;
    if (source === 'fleet_alerts' || !deviceId) {
        loadCompareDriverByName(slot, name);
    } else {
        loadCompareDriver(slot, deviceId);
    }
}

function loadCompareDriver(slot, deviceId) {
    if (!deviceId) return;
    const container = document.getElementById(`compare-driver-${slot}`);
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px;">Loading...</div>';

    fetch(`/api/analytics/driver/${deviceId}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data || data.error) {
                container.innerHTML = `<div style="text-align:center;color:#94a3b8;padding:30px;">${data?.error || 'No data'}</div>`;
                return;
            }
            const score = data.eco_score || 0;
            const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
            const stats = data.stats || {};
            container.innerHTML = `
                <div style="text-align:center;margin-bottom:16px;">
                    <div style="width:50px;height:50px;border-radius:50%;background:linear-gradient(135deg,${scoreColor},${scoreColor}88);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:1.2rem;">${(data.driver_name||'D').charAt(0).toUpperCase()}</div>
                    <div style="font-weight:700;font-size:0.95rem;margin-top:8px;">${data.driver_name || 'Unknown'}</div>
                    <div style="color:#64748b;font-size:0.75rem;">${data.vehicle_name || ''}</div>
                </div>
                <div style="text-align:center;margin-bottom:16px;">
                    <div style="font-size:2rem;font-weight:800;color:${scoreColor};">${score}</div>
                    <div style="font-size:0.72rem;color:#94a3b8;">Eco Score</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.75rem;">
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#ef4444;">${stats.harsh_braking?.total || 0}</div>
                        <div style="color:#94a3b8;">Braking</div>
                    </div>
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#f59e0b;">${stats.harsh_acceleration || 0}</div>
                        <div style="color:#94a3b8;">Accel</div>
                    </div>
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#f97316;">${stats.harsh_cornering || 0}</div>
                        <div style="color:#94a3b8;">Corner</div>
                    </div>
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#6366f1;">${stats.idle_minutes || 0}m</div>
                        <div style="color:#94a3b8;">Idle</div>
                    </div>
                </div>`;
        })
        .catch(() => {
            container.innerHTML = '<div style="text-align:center;color:#ef4444;padding:30px;">Failed to load</div>';
        });
}

function loadCompareDriverByName(slot, vehicleName) {
    if (!vehicleName) return;
    const container = document.getElementById(`compare-driver-${slot}`);
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px;">Loading...</div>';

    fetch(`/api/analytics/driver/by-name/${encodeURIComponent(vehicleName)}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data || data.error) {
                container.innerHTML = `<div style="text-align:center;color:#94a3b8;padding:30px;">${data?.error || 'No data'}</div>`;
                return;
            }
            const score = data.eco_score || 0;
            const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
            const stats = data.stats || {};
            container.innerHTML = `
                <div style="text-align:center;margin-bottom:16px;">
                    <div style="width:50px;height:50px;border-radius:50%;background:linear-gradient(135deg,${scoreColor},${scoreColor}88);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:1.2rem;">${(data.driver_name||'D').charAt(0).toUpperCase()}</div>
                    <div style="font-weight:700;font-size:0.95rem;margin-top:8px;">${data.driver_name || 'Unknown'}</div>
                    <div style="color:#64748b;font-size:0.75rem;">${data.vehicle_name || ''}</div>
                </div>
                <div style="text-align:center;margin-bottom:16px;">
                    <div style="font-size:2rem;font-weight:800;color:${scoreColor};">${score}</div>
                    <div style="font-size:0.72rem;color:#94a3b8;">Eco Score</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.75rem;">
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#ef4444;">${stats.harsh_braking?.total || 0}</div>
                        <div style="color:#94a3b8;">Braking</div>
                    </div>
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#f59e0b;">${stats.harsh_acceleration || 0}</div>
                        <div style="color:#94a3b8;">Accel</div>
                    </div>
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#f97316;">${stats.harsh_cornering || 0}</div>
                        <div style="color:#94a3b8;">Corner</div>
                    </div>
                    <div style="padding:8px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;text-align:center;">
                        <div style="font-weight:700;color:#6366f1;">${stats.idle_minutes || 0}m</div>
                        <div style="color:#94a3b8;">Idle</div>
                    </div>
                </div>`;
        })
        .catch(() => {
            container.innerHTML = '<div style="text-align:center;color:#ef4444;padding:30px;">Failed to load</div>';
        });
}

// ============================================================================
// MONTHLY MIS REPORT
// ============================================================================
let _monthlyMISData = null;
let _monthlyMISSort = { key: 'total_km', dir: 'desc' };

function openMonthlyMIS() {
    const modal = document.getElementById('monthly-mis-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    const input = document.getElementById('monthly-mis-month');
    if (input) {
        const now = new Date();
        const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        input.value = prev.getFullYear() + '-' + String(prev.getMonth() + 1).padStart(2, '0');
    }
    loadMISDays();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function loadMISDays() {
    const input = document.getElementById('monthly-mis-month');
    const daySelect = document.getElementById('monthly-mis-day');
    const month = input ? input.value : '';
    if (!month || !daySelect) return;

    daySelect.innerHTML = '<option value="">Loading...</option>';

    try {
        const res = await fetch(`/api/fleet/fdb/monthly-mis-days?month=${month}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();
        const days = data.days || [];

        let html = '<option value="">All Days (Month View)</option>';
        days.forEach(d => {
            const dt = new Date(d.date);
            const label = `${dt.getDate()} ${dt.toLocaleString('en', { month: 'short' })} — ${d.vehicles} veh, ${d.total_km.toLocaleString()} km`;
            html += `<option value="${d.date}">${label}</option>`;
        });
        daySelect.innerHTML = html;
    } catch (e) {
        daySelect.innerHTML = '<option value="">All Days</option>';
    }

    generateMonthlyMIS();
}

function closeMonthlyMIS() {
    const modal = document.getElementById('monthly-mis-modal');
    if (modal) modal.style.display = 'none';
}

async function generateMonthlyMIS() {
    const input = document.getElementById('monthly-mis-month');
    const daySelect = document.getElementById('monthly-mis-day');
    const month = input ? input.value : '';
    const day = daySelect ? daySelect.value : '';
    if (!month) return;

    const summaryEl = document.getElementById('monthly-mis-summary');
    const tbody = document.getElementById('monthly-mis-veh-body');
    const vendorEl = document.getElementById('monthly-mis-vendor-bars');
    const trendCanvas = document.getElementById('monthly-mis-trend-chart');
    
    if (summaryEl) summaryEl.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--fleet-text-sub);"><div style="display:inline-block; width:24px; height:24px; border:3px solid var(--fleet-border); border-top-color:var(--brand-primary); border-radius:50%; animation:spin 0.8s linear infinite; margin-bottom:12px;"></div><div>Loading report...</div></div>';
    if (tbody) tbody.innerHTML = '';
    if (vendorEl) vendorEl.innerHTML = '';
    if (trendCanvas) { const ctx = trendCanvas.getContext('2d'); ctx.clearRect(0, 0, trendCanvas.width, trendCanvas.height); }

    const dayParam = day ? `&day=${day}` : '';

    try {
        let res = await fetch(`/api/fleet/fdb/monthly-mis?month=${month}${dayParam}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        let data = await res.json();

        if (data.summary && data.summary.total_vehicles === 0) {
            if (summaryEl) summaryEl.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--fleet-text-sub);">No GPS data for this period. Starting auto-generation...</div>';
            const genRes = await fetch(`/api/fleet/fdb/gps-mis-generate?month=${month}`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            const genData = await genRes.json();
            if (genData.status === 'started' || genData.status === 'already_running') {
                let attempts = 0;
                const maxAttempts = 60;
                const pollInterval = 10000;
                const poll = async () => {
                    attempts++;
                    if (attempts > maxAttempts || !summaryEl) return;
                    if (summaryEl) summaryEl.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--fleet-text-sub);"><div style="display:inline-block; width:24px; height:24px; border:3px solid var(--fleet-border); border-top-color:var(--brand-primary); border-radius:50%; animation:spin 0.8s linear infinite; margin-bottom:12px;"></div><div>Generating GPS MIS for ${month}... (attempt ${attempts}/${maxAttempts})</div></div>`;
                    try {
                        const statusRes = await fetch(`/api/fleet/fdb/gps-mis-status?month=${month}`, {
                            headers: { 'Authorization': `Bearer ${authToken}` }
                        });
                        const statusData = await statusRes.json();
                        if (statusData.generation_status === 'done') {
                            res = await fetch(`/api/fleet/fdb/monthly-mis?month=${month}${dayParam}`, {
                                headers: { 'Authorization': `Bearer ${authToken}` }
                            });
                            data = await res.json();
                            if (data.summary && data.summary.total_vehicles > 0) {
                                _monthlyMISData = data;
                                const subEl2 = document.getElementById('monthly-mis-subtitle');
                                if (subEl2) subEl2.textContent = day ? `Fleet performance for ${day}` : 'Complete fleet performance for selected month';
                                renderMonthlyMISSummary(data.summary);
                                renderMonthlyMISTrend(data.trend, day);
                                renderMonthlyMISVendors(data.vendors);
                                renderMonthlyMISVehicleTable(data.vehicles);
                                return;
                            }
                        }
                        if (statusData.generation_status === 'error') {
                            if (summaryEl) summaryEl.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--brand-danger);">Generation error. Please try again.</div>';
                            return;
                        }
                    } catch (e) {}
                    setTimeout(poll, pollInterval);
                };
                poll();
                return;
            }
        }

        _monthlyMISData = data;
        const subEl = document.getElementById('monthly-mis-subtitle');
        if (subEl) subEl.textContent = day ? `Fleet performance for ${day}` : 'Complete fleet performance for selected month';
        renderMonthlyMISSummary(data.summary);
        renderMonthlyMISTrend(data.trend, day);
        renderMonthlyMISVendors(data.vendors);
        renderMonthlyMISVehicleTable(data.vehicles);
    } catch (err) {
        console.error('Monthly MIS error:', err);
        if (summaryEl) summaryEl.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--brand-danger);">Error: ${err.message}</div>`;
    }
}

function renderMonthlyMISSummary(s) {
    const el = document.getElementById('monthly-mis-summary');
    if (!el) return;
    const fmt = (n) => n >= 1000 ? n.toLocaleString('en-US', { maximumFractionDigits: 0 }) : n.toFixed(n % 1 === 0 ? 0 : 1);
    el.innerHTML = `
        <div style="background:linear-gradient(135deg,rgba(99,102,241,0.1),rgba(139,92,246,0.06)); border:1px solid rgba(99,102,241,0.25); border-radius:12px; padding:16px;">
            <div style="font-size:11px; color:var(--fleet-text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Vehicles</div>
            <div style="font-size:26px; font-weight:800; color:var(--brand-primary); margin:4px 0;">${fmt(s.total_vehicles)}</div>
            <div style="font-size:11px; color:var(--fleet-text-sub);">reporting vehicles</div>
        </div>
        <div style="background:linear-gradient(135deg,rgba(34,197,94,0.1),rgba(16,185,129,0.06)); border:1px solid rgba(34,197,94,0.25); border-radius:12px; padding:16px;">
            <div style="font-size:11px; color:var(--fleet-text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Total KM</div>
            <div style="font-size:26px; font-weight:800; color:var(--brand-success); margin:4px 0;">${fmt(s.total_km)}</div>
            <div style="font-size:11px; color:var(--fleet-text-sub);">Peak: ${fmt(s.on_peak_km)} | Off: ${fmt(s.off_peak_km)}</div>
        </div>
        <div style="background:linear-gradient(135deg,rgba(217,119,6,0.1),rgba(245,158,11,0.06)); border:1px solid rgba(217,119,6,0.25); border-radius:12px; padding:16px;">
            <div style="font-size:11px; color:var(--fleet-text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Fuel Efficiency</div>
            <div style="font-size:26px; font-weight:800; color:var(--brand-warning); margin:4px 0;">${s.actual_kmpl.toFixed(1)} <span style="font-size:13px; font-weight:600;">km/L</span></div>
            <div style="font-size:11px; color:var(--fleet-text-sub);">Benchmark: ${s.avg_benchmark.toFixed(1)} | Consumed: ${fmt(s.fuel_consumed)}L</div>
        </div>
        <div style="background:linear-gradient(135deg,rgba(220,38,38,0.1),rgba(239,68,68,0.06)); border:1px solid rgba(220,38,38,0.25); border-radius:12px; padding:16px;">
            <div style="font-size:11px; color:var(--fleet-text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Safety Events</div>
            <div style="font-size:26px; font-weight:800; color:var(--brand-danger); margin:4px 0;">${fmt(s.total_harsh_braking + s.total_speed_violation)}</div>
            <div style="font-size:11px; color:var(--fleet-text-sub);">Braking: ${fmt(s.total_harsh_braking)} | Speed: ${fmt(s.total_speed_violation)}</div>
        </div>
    `;
}

function renderMonthlyMISTrend(trend, selectedDay) {
    const canvas = document.getElementById('monthly-mis-trend-chart');
    if (!canvas || !trend || trend.length === 0) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.parentElement.clientWidth - 36;
    canvas.width = W;
    canvas.height = 200;
    ctx.clearRect(0, 0, W, 200);

    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
    const labelColor = isDark ? '#94a3b8' : '#6b7280';
    const barColor1 = isDark ? '#818cf8' : '#6366f1';
    const barColor2 = isDark ? '#a78bfa' : '#8b5cf6';

    const pad = { top: 20, right: 20, bottom: 40, left: 60 };
    const chartW = W - pad.left - pad.right;
    const chartH = 200 - pad.top - pad.bottom;
    const maxKM = Math.max(...trend.map(t => t.total_km), 1);

    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = pad.top + (chartH / 4) * i;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
        ctx.fillStyle = labelColor; ctx.font = '10px sans-serif'; ctx.textAlign = 'right';
        ctx.fillText(Math.round(maxKM * (1 - i / 4)).toLocaleString(), pad.left - 8, y + 3);
    }

    const barW = Math.max(4, (chartW / trend.length) - 2);
    trend.forEach((t, i) => {
        const x = pad.left + (chartW / trend.length) * i + 1;
        const barH = (t.total_km / maxKM) * chartH;
        const isSelected = selectedDay && t.date === selectedDay;
        const grad = ctx.createLinearGradient(x, pad.top + chartH - barH, x, pad.top + chartH);
        if (isSelected) {
            grad.addColorStop(0, '#f59e0b');
            grad.addColorStop(1, '#d97706');
        } else {
            grad.addColorStop(0, barColor1);
            grad.addColorStop(1, barColor2);
        }
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(x, pad.top + chartH - barH, barW, barH, [3, 3, 0, 0]);
        ctx.fill();

        if (i % Math.ceil(trend.length / 10) === 0) {
            ctx.save();
            ctx.fillStyle = labelColor; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
            const d = new Date(t.date);
            ctx.fillText(`${d.getDate()}/${d.getMonth() + 1}`, x + barW / 2, 200 - pad.bottom + 14);
            ctx.restore();
        }
    });

    ctx.fillStyle = labelColor; ctx.font = '10px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Day', W / 2, 200 - 4);
}

function renderMonthlyMISVendors(vendors) {
    const el = document.getElementById('monthly-mis-vendor-bars');
    if (!el || !vendors || vendors.length === 0) return;
    const maxKM = Math.max(...vendors.map(v => v.total_km), 1);
    el.innerHTML = vendors.map(v => {
        const pct = (v.total_km / maxKM * 100).toFixed(0);
        return `
            <div style="margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:3px;">
                    <span style="color:var(--fleet-text-main); font-weight:600; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${v.vendor}">${v.vendor}</span>
                    <span style="color:var(--fleet-text-sub);">${v.total_km.toLocaleString()} km | ${v.actual_kmpl.toFixed(1)} km/L</span>
                </div>
                <div style="height:8px; background:var(--fleet-border); border-radius:4px; overflow:hidden;">
                    <div style="height:100%; width:${pct}%; background:var(--brand-primary); border-radius:4px; transition:width 0.6s;"></div>
                </div>
            </div>
        `;
    }).join('');
}

function renderMonthlyMISVehicleTable(vehicles) {
    const tbody = document.getElementById('monthly-mis-veh-body');
    const countEl = document.getElementById('monthly-mis-veh-count');
    if (!tbody) return;

    const sorted = [...vehicles].sort((a, b) => {
        const key = _monthlyMISSort.key;
        const aVal = typeof a[key] === 'string' ? a[key] : (a[key] || 0);
        const bVal = typeof b[key] === 'string' ? b[key] : (b[key] || 0);
        if (typeof aVal === 'string') return _monthlyMISSort.dir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        return _monthlyMISSort.dir === 'asc' ? aVal - bVal : bVal - aVal;
    });

    if (countEl) countEl.textContent = `${vehicles.length} vehicles`;

    // Render first 50 immediately, rest in chunks
    const renderRow = (v) => {
        const kmColor = v.actual_kmpl > v.benchmark && v.benchmark > 0 ? 'var(--brand-success)' : v.actual_kmpl > 0 ? 'var(--brand-warning)' : 'var(--fleet-text-muted)';
        const brakingColor = v.harsh_braking > 0 ? 'var(--brand-danger)' : 'var(--fleet-text-sub)';
        const speedColor = v.speed_violation > 0 ? 'var(--brand-danger)' : 'var(--fleet-text-sub)';
        return `<tr style="border-bottom:1px solid var(--fleet-border); transition:background 0.15s;" onmouseenter="this.style.background='rgba(99,102,241,0.04)'" onmouseleave="this.style.background='transparent'">
            <td style="padding:10px 14px; font-size:12px; font-weight:700; color:var(--fleet-text-main); cursor:pointer;" onclick="closeMonthlyMIS(); openVehicleMIS('${v.vehicle}')">${v.vehicle}</td>
            <td style="padding:10px 14px; font-size:11px; color:var(--fleet-text-sub);">${v.vendor || '--'}</td>
            <td style="padding:10px 14px; font-size:11px; color:var(--fleet-text-sub);">${v.category || '--'}</td>
            <td style="padding:10px 14px; font-size:11px; color:var(--fleet-text-sub);">${v.fleet_group || '--'}</td>
            <td style="padding:10px 14px; font-size:12px; color:var(--fleet-text-main);">${v.reporting_days}</td>
            <td style="padding:10px 14px; font-size:12px; font-weight:700; color:var(--fleet-text-main);">${v.total_km.toLocaleString()}</td>
            <td style="padding:10px 14px; font-size:11px; color:var(--fleet-text-sub);">${v.on_peak_km.toLocaleString()}</td>
            <td style="padding:10px 14px; font-size:11px; color:var(--fleet-text-sub);">${v.off_peak_km.toLocaleString()}</td>
            <td style="padding:10px 14px; font-size:12px; color:var(--fleet-text-main);">${v.fuel_consumed.toLocaleString()}</td>
            <td style="padding:10px 14px; font-size:13px; font-weight:800; color:${kmColor};">${v.actual_kmpl.toFixed(1)}</td>
            <td style="padding:10px 14px; font-size:11px; color:var(--fleet-text-sub);">${v.benchmark.toFixed(1)}</td>
            <td style="padding:10px 14px; font-size:11px; color:var(--fleet-text-sub);">${v.avg_daily_km.toFixed(0)}</td>
            <td style="padding:10px 14px; font-size:11px; color:${brakingColor};">${v.harsh_braking}</td>
            <td style="padding:10px 14px; font-size:11px; color:${speedColor};">${v.speed_violation}</td>
        </tr>`;
    };

    const BATCH = 50;
    tbody.innerHTML = sorted.slice(0, BATCH).map(renderRow).join('');
    let idx = BATCH;
    const addBatch = () => {
        if (idx >= sorted.length) return;
        const frag = sorted.slice(idx, idx + BATCH).map(renderRow).join('');
        tbody.insertAdjacentHTML('beforeend', frag);
        idx += BATCH;
        if (idx < sorted.length) requestAnimationFrame(addBatch);
    };
    if (idx < sorted.length) requestAnimationFrame(addBatch);
}

function sortMonthlyMIS(key) {
    if (_monthlyMISSort.key === key) {
        _monthlyMISSort.dir = _monthlyMISSort.dir === 'asc' ? 'desc' : 'asc';
    } else {
        _monthlyMISSort.key = key;
        _monthlyMISSort.dir = 'desc';
    }
    if (_monthlyMISData) renderMonthlyMISVehicleTable(_monthlyMISData.vehicles);
}

function exportMonthlyMISCSV() {
    const input = document.getElementById('monthly-mis-month');
    const daySelect = document.getElementById('monthly-mis-day');
    const month = input ? input.value : '';
    const day = daySelect ? daySelect.value : '';
    if (!month) return;
    const dayParam = day ? `&day=${day}` : '';
    fetch(`/api/fleet/fdb/monthly-mis-export?month=${month}${dayParam}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    }).then(r => r.blob()).then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = day ? `MIS_${day}.csv` : `Monthly_MIS_${month}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }).catch(err => console.error('CSV export error:', err));
}

function toggleMatrixCollapse(e) {
    if (e) {
        // Prevent click events if clicking buttons inside header, though right now we handle it on the header level
        const target = e.target;
        if (target.closest('button') && target.closest('button').id !== 'matrix-collapse-btn') {
            return;
        }
    }
    const container = document.getElementById('matrix-collapse-container');
    const icon = document.getElementById('matrix-collapse-icon');
    if (!container) return;

    const isCollapsed = container.classList.toggle('collapsed');
    
    if (isCollapsed) {
        container.style.maxHeight = '0px';
        container.style.opacity = '0';
        if (icon) {
            icon.style.transform = 'rotate(180deg)';
        }
    } else {
        container.style.maxHeight = '2000px';
        container.style.opacity = '1';
        if (icon) {
            icon.style.transform = 'rotate(0deg)';
        }
    }
}

/* ====================================================================
   VOICE INPUT FEATURE — Web Speech API (GPT-style)
   Works 100% client-side. No backend changes needed.
   Supported: Chrome, Edge, Samsung Internet (webkit prefix fallback)
   ==================================================================== */

(function initVoiceInput() {
    var recognition    = null;
    var isListening    = false;
    var finalTranscript = '';
    var silenceTimer   = null;
    var SILENCE_MS     = 2200;

    function getVoiceBtn() { return document.getElementById('voice-input-btn'); }
    function getInputEl()  { return document.getElementById('user-input'); }

    function setVoiceBtnState(state) {
        var btn = getVoiceBtn();
        if (!btn) return;
        btn.classList.remove('voice-idle', 'voice-listening', 'voice-processing');
        btn.classList.add('voice-' + state);
        var icon = (state === 'listening') ? 'mic-off' : 'mic';
        btn.innerHTML = '<i data-lucide="' + icon + '"></i>';
        btn.title = (state === 'listening') ? 'Listening... click to stop' : 'Voice Input';
        try { if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [btn] }); } catch(e) {}
    }

    function toast(msg, type) {
        if (typeof showNotification === 'function') showNotification(msg, type || 'info');
    }

    function clearSilence() { if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; } }
    function resetSilence() {
        clearSilence();
        silenceTimer = setTimeout(function() { if (isListening) stopListening(true); }, SILENCE_MS);
    }

    function buildRecognition() {
        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) return null;
        var r = new SR();
        r.continuous     = true;
        r.interimResults = true;
        r.lang           = 'en-US';

        r.onstart = function() {
            isListening = true;
            finalTranscript = '';
            setVoiceBtnState('listening');
            resetSilence();
        };

        r.onresult = function(ev) {
            resetSilence();
            var interim = '';
            for (var i = ev.resultIndex; i < ev.results.length; i++) {
                if (ev.results[i].isFinal) finalTranscript += ev.results[i][0].transcript + ' ';
                else interim += ev.results[i][0].transcript;
            }
            var inp = getInputEl();
            if (inp) {
                inp.value = (finalTranscript + interim).trim();
                inp.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };

        r.onspeechend = function() { resetSilence(); };

        r.onerror = function(e) {
            clearSilence();
            isListening = false;
            setVoiceBtnState('idle');
            if (e.error === 'not-allowed' || e.error === 'permission-denied') {
                toast('Microphone access denied. Allow mic in browser settings.', 'error');
            } else if (e.error === 'no-speech') {
                toast('No speech detected. Try again.', 'info');
            } else if (e.error !== 'aborted') {
                toast('Voice error: ' + e.error, 'error');
            }
        };

        r.onend = function() {
            clearSilence();
            if (isListening) { isListening = false; setVoiceBtnState('idle'); }
        };

        return r;
    }

    function startListening() {
        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            toast('Voice input not supported. Use Chrome or Edge browser.', 'error');
            return;
        }
        // Web Speech API requires secure context (HTTPS or localhost)
        if (!window.isSecureContext) {
            toast('Voice needs HTTPS or localhost. Open via https:// or localhost:8000', 'error');
            return;
        }
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function() {
                recognition = buildRecognition();
                if (recognition) { try { recognition.start(); } catch(e) { console.warn('[Voice]', e); } }
            })
            .catch(function(err) {
                var msg = (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')
                    ? 'Microphone permission denied. Allow mic in browser settings.'
                    : 'Cannot access microphone: ' + err.message;
                toast(msg, 'error');
            });
    }

    function stopListening(autoSend) {
        clearSilence();
        isListening = false;
        if (recognition) { try { recognition.stop(); } catch(e) {} }
        setVoiceBtnState('idle');
        if (autoSend) {
            var inp = getInputEl();
            var text = inp ? inp.value.trim() : '';
            if (text) setTimeout(function() { if (typeof sendMessage === 'function') sendMessage(); }, 300);
        }
    }

    window.toggleVoiceInput = function() {
        if (isListening) stopListening(false);
        else startListening();
    };

    var closeChatBtn2 = document.getElementById('close-chat-panel');
    if (closeChatBtn2) {
        closeChatBtn2.addEventListener('click', function() {
            if (isListening) stopListening(false);
        });
    }

    var _origNewChat = window.startNewChat;
    if (typeof _origNewChat === 'function') {
        window.startNewChat = function() {
            if (isListening) stopListening(false);
            return _origNewChat.apply(this, arguments);
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { setVoiceBtnState('idle'); });
    } else {
        setVoiceBtnState('idle');
    }
})();

// ============================================================
// WORKSHOP MANAGEMENT MODULE
// ============================================================

let workshopTabState = 'jobs';
let workshopDashboardData = {};

const WS_STATUSES = ['pending','assigned','vehicle_arrived','inspection','in_progress','waiting_parts','paused','quality_check','approved','completed','cancelled'];
const WS_TRANSITIONS = { pending:['assigned','cancelled'], assigned:['vehicle_arrived','cancelled'], vehicle_arrived:['inspection','cancelled'], inspection:['in_progress','cancelled'], in_progress:['waiting_parts','paused','quality_check','cancelled'], waiting_parts:['in_progress','cancelled'], paused:['in_progress','cancelled'], quality_check:['in_progress','approved','cancelled'], approved:['completed','cancelled'], completed:[], cancelled:[] };
const WS_DEFAULT_CHECKLIST = ['Engine Oil Changed','Oil Filter Installed','Air Filter Checked','Leak Inspection','Road Test','Cleaning','Supervisor Approval'];

function initWorkshop() { loadWorkshopDashboard(); }

async function loadWorkshopDashboard() {
    try {
        const res = await fetch('/api/maintenance/workshop/dashboard', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed to load workshop dashboard');
        workshopDashboardData = await res.json();
        renderWorkshopKPI(workshopDashboardData.kpis || {});
        switchWorkshopTab(workshopTabState);
    } catch (e) { console.error('Workshop dashboard error:', e); }
}

function renderWorkshopKPI(kpis) {
    const c = document.getElementById('workshop-kpi-cards');
    if (!c) return;
    const items = [
        { label: 'Active Jobs', value: kpis.active_jobs || 0, icon: 'clipboard-list', color: '#3b82f6' },
        { label: 'Pending Jobs', value: kpis.pending_jobs || 0, icon: 'clock', color: '#f59e0b' },
        { label: 'Completed', value: kpis.completed_jobs || 0, icon: 'check-circle', color: '#10b981' },
        { label: 'Overdue', value: kpis.overdue_jobs || 0, icon: 'alert-triangle', color: '#ef4444' },
        { label: 'In Workshop', value: kpis.vehicles_in_workshop || 0, icon: 'warehouse', color: '#8b5cf6' },
        { label: 'Avg Repair Time', value: (kpis.avg_repair_hours || 0) + 'h', icon: 'timer', color: '#06b6d4' },
        { label: 'Total Cost', value: kpis.total_maintenance_cost ? formatPKR(kpis.total_maintenance_cost, true) : 'Rs. 0', icon: 'banknote', color: '#14b8a6' },
    ];
    c.innerHTML = items.map(i => `<div class="premium-card mini-stat" style="padding:16px; text-align:center;"><div style="display:flex; align-items:center; justify-content:center; gap:8px; margin-bottom:8px;"><i data-lucide="${i.icon}" style="width:18px; color:${i.color};"></i><span class="card-label" style="font-size:0.75rem; color:var(--text-dim); text-transform:uppercase; font-weight:600;">${i.label}</span></div><div class="card-value" style="font-size:1.6rem; font-weight:800; color:${i.color};">${i.value}</div></div>`).join('');
    safeCreateIcons();
}

function switchWorkshopTab(tab) {
    workshopTabState = tab;
    document.querySelectorAll('.workshop-tab-btn').forEach(b => { b.classList.remove('active'); b.style.background = 'transparent'; b.style.color = 'var(--text-secondary)'; });
    const btn = document.querySelector(`.workshop-tab-btn[data-wstab="${tab}"]`);
    if (btn) { btn.classList.add('active'); btn.style.background = 'var(--brand-primary)'; btn.style.color = '#fff'; }
    if (tab === 'jobs') renderWorkshopJobs();
    else if (tab === 'technicians') renderWorkshopTechnicians();
    else if (tab === 'inventory') renderInventoryTab();
}

async function renderWorkshopJobs() {
    const tc = document.getElementById('workshop-tab-content');
    if (!tc) return;
    try {
        const res = await fetch('/api/maintenance/workshop/jobs?page_size=200', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed to load jobs');
        const data = await res.json();
        const jobs = data.items || [];
        let html = `<div style="display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap;">
            <input type="text" id="ws-job-search" placeholder="Search jobs..." onkeyup="filterWorkshopJobs()" style="flex:1; min-width:200px; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/>
            <select id="ws-job-status-filter" onchange="filterWorkshopJobs()" style="padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                <option value="">All Status</option>
                ${WS_STATUSES.map(s => `<option value="${s}">${s.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</option>`).join('')}
            </select>
            <select id="ws-job-priority-filter" onchange="filterWorkshopJobs()" style="padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                <option value="">All Priority</option>
                <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
            </select>
            <button onclick="openWorkshopJobModal()" class="glass-btn primary" style="padding:10px 20px; border:none; cursor:pointer; border-radius:8px; font-weight:600; color:#fff;">+ New Job</button>
        </div>`;
        html += `<table class="modern-table" style="width:100%;"><thead><tr><th>Job #</th><th>Vehicle</th><th>Type</th><th>Priority</th><th>Technician</th><th>Status</th><th>Due Date</th><th>Cost</th><th>Actions</th></tr></thead><tbody id="ws-jobs-tbody">`;
        jobs.forEach(j => {
            html += `<tr data-status="${j.status}" data-priority="${j.priority}" data-search="${(j.job_number+' '+(j.device_name||'')+' '+(j.type_name||'')).toLowerCase()}">
                <td><strong>${j.job_number}</strong></td><td>${j.device_name||'N/A'}</td><td>${j.type_name||'N/A'}</td>
                <td>${wsPriorityBadge(j.priority)}</td><td>${j.technician_name||'<span style="color:var(--text-dim)">Unassigned</span>'}</td>
                <td>${wsStatusBadge(j.status)}</td><td>${j.due_date?new Date(j.due_date).toLocaleDateString():'-'}</td>
                <td>${j.total_cost?formatPKR(j.total_cost,true):(j.estimated_cost?'~'+formatPKR(j.estimated_cost,true):'-')}</td>
                <td><button onclick="openWorkshopJobDetail(${j.id})" class="glass-btn" style="padding:4px 10px; font-size:0.75rem; border:none; cursor:pointer; border-radius:6px; background:var(--brand-primary); color:#fff;">View</button>
                ${j.status!=='completed'&&j.status!=='cancelled'?`<button onclick="quickUpdateJobStatus(${j.id},'${j.status}')" class="glass-btn" style="padding:4px 10px; font-size:0.75rem; border:none; cursor:pointer; border-radius:6px; background:#f59e0b; color:#fff; margin-left:4px;">Advance</button>`:''}</td></tr>`;
        });
        html += '</tbody></table>';
        html += `<div style="margin-top:12px; color:var(--text-dim); font-size:0.8rem;">Showing ${jobs.length} jobs</div>`;
        tc.innerHTML = html;
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading jobs</div>'; }
}

function filterWorkshopJobs() {
    const search = (document.getElementById('ws-job-search')?.value||'').toLowerCase();
    const status = document.getElementById('ws-job-status-filter')?.value||'';
    const priority = document.getElementById('ws-job-priority-filter')?.value||'';
    document.querySelectorAll('#ws-jobs-tbody tr').forEach(row => {
        row.style.display = (!search||(row.dataset.search||'').includes(search))&&(!status||row.dataset.status===status)&&(!priority||row.dataset.priority===priority)?'':'none';
    });
}

function wsStatusBadge(status) {
    const colors = { pending:'#f59e0b', assigned:'#3b82f6', vehicle_arrived:'#8b5cf6', inspection:'#a855f7', in_progress:'#8b5cf6', waiting_parts:'#f97316', paused:'#ef4444', quality_check:'#06b6d4', approved:'#10b981', completed:'#10b981', cancelled:'#6b7280' };
    const labels = { pending:'Pending', assigned:'Assigned', vehicle_arrived:'Vehicle Arrived', inspection:'Inspection', in_progress:'In Progress', waiting_parts:'Waiting Parts', paused:'Paused', quality_check:'Quality Check', approved:'Approved', completed:'Completed', cancelled:'Cancelled' };
    const c = colors[status]||'#6b7280';
    return `<span style="display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:600; background:${c}22; color:${c}; border:1px solid ${c}44;">${labels[status]||status}</span>`;
}

function wsPriorityBadge(priority) {
    const colors = { critical:'#ef4444', high:'#f97316', medium:'#f59e0b', low:'#10b981' };
    const c = colors[priority]||'#6b7280';
    return `<span style="display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:600; background:${c}22; color:${c};">${(priority||'medium').charAt(0).toUpperCase()+(priority||'medium').slice(1)}</span>`;
}

function wsStatusFlow(status) {
    const flow = ['pending','assigned','vehicle_arrived','inspection','in_progress','paused','quality_check','approved','completed'];
    const icons = { pending:'circle', assigned:'user', vehicle_arrived:'truck', inspection:'search', in_progress:'wrench', paused:'pause-circle', quality_check:'check-square', approved:'thumbs-up', completed:'check-circle' };
    const idx = flow.indexOf(status);
    return flow.map((s,i) => {
        const done = i < idx;
        const current = i === idx;
        const colors = { pending:'#f59e0b', assigned:'#3b82f6', vehicle_arrived:'#8b5cf6', inspection:'#a855f7', in_progress:'#8b5cf6', paused:'#ef4444', quality_check:'#06b6d4', approved:'#10b981', completed:'#10b981' };
        const c = done?'#10b981':(current?colors[s]:'#d1d5db');
        return `<div style="display:flex; align-items:center; gap:6px;" title="${s}"><div style="width:24px; height:24px; border-radius:50%; background:${c}; color:#fff; display:flex; align-items:center; justify-content:center; font-size:0.65rem; font-weight:700; flex-shrink:0;">${done?'&#10003;':(i+1)}</div><span style="font-size:0.72rem; color:${c}; font-weight:${current?'700':'400'}; white-space:nowrap;">${s.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</span></div>`;
    }).join('<div style="width:14px; height:2px; background:#d1d5db; flex-shrink:0;"></div>');
}

async function openWorkshopJobDetail(jobId) {
    const modal = document.getElementById('workshop-job-detail-modal');
    const content = document.getElementById('workshop-job-detail-content');
    const titleEl = document.getElementById('ws-detail-title');
    if (!modal||!content) return;
    modal.style.display = 'flex';
    content.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const res = await fetch(`/api/maintenance/workshop/jobs/${jobId}`, { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed to load job');
        const job = await res.json();
        titleEl.textContent = `Job ${job.job_number}`;

        let html = `<div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">
            <div class="premium-card" style="padding:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px; color:var(--text-primary);">Job Information</h4>
                <div style="display:grid; gap:8px; font-size:0.82rem;">
                    <div><span style="color:var(--text-dim);">Status:</span> ${wsStatusBadge(job.status)}</div>
                    <div><span style="color:var(--text-dim);">Priority:</span> ${wsPriorityBadge(job.priority)}</div>
                    <div><span style="color:var(--text-dim);">Vehicle:</span> ${job.device_name||'N/A'} (ID: ${job.device_id})</div>
                    <div><span style="color:var(--text-dim);">Type:</span> ${job.type_name||'N/A'}</div>
                    <div><span style="color:var(--text-dim);">Template:</span> ${job.template_name||'N/A'}</div>
                    <div><span style="color:var(--text-dim);">Technician:</span> ${job.technician_name||'Unassigned'}</div>
                    <div><span style="color:var(--text-dim);">Odometer:</span> ${job.current_odometer||0} km</div>
                    <div><span style="color:var(--text-dim);">Due Reason:</span> ${job.due_reason||'N/A'}</div>
                </div>
            </div>
            <div class="premium-card" style="padding:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px; color:var(--text-primary);">Cost Breakdown (PKR)</h4>
                <div style="display:grid; gap:8px; font-size:0.82rem;">
                    <div><span style="color:var(--text-dim);">Labour Cost:</span> ${job.labour_cost?formatPKR(job.labour_cost,true):'Rs. 0'}</div>
                    <div><span style="color:var(--text-dim);">Parts Cost:</span> ${job.parts_cost?formatPKR(job.parts_cost,true):'Rs. 0'}</div>
                    <div><span style="color:var(--text-dim);">Misc Cost:</span> ${job.misc_cost?formatPKR(job.misc_cost,true):'Rs. 0'}</div>
                    <div style="border-top:1px solid var(--border-light); padding-top:6px; font-weight:700;"><span style="color:var(--text-dim);">Total Cost:</span> ${job.total_cost?formatPKR(job.total_cost,true):'Rs. 0'}</div>
                    <div><span style="color:var(--text-dim);">Est. Cost:</span> ${job.estimated_cost?formatPKR(job.estimated_cost,true):'-'}</div>
                    <div><span style="color:var(--text-dim);">Labour Hours:</span> ${job.labour_hours||0}h</div>
                </div>
            </div>
        </div>`;

        html += `<div class="premium-card" style="padding:16px; margin-bottom:16px;">
            <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px; color:var(--text-primary);">Status Flow</h4>
            <div style="display:flex; align-items:center; gap:0; flex-wrap:wrap; overflow-x:auto;">${wsStatusFlow(job.status)}</div>
        </div>`;

        if (job.maintenance_history && job.maintenance_history.length > 0) {
            html += `<div class="premium-card" style="padding:16px; margin-bottom:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px; color:var(--text-primary);">Previous Maintenance History</h4>
                <table class="modern-table" style="width:100%;"><thead><tr><th>Date</th><th>Odometer</th><th>Type</th><th>Technician</th><th>Cost</th></tr></thead><tbody>`;
            job.maintenance_history.forEach(h => {
                html += `<tr><td>${h.service_date?new Date(h.service_date).toLocaleDateString():'-'}</td><td>${h.service_value||0} km</td><td>${h.service_type||'-'}</td><td>${h.technician||'-'}</td><td>${h.cost?formatPKR(h.cost,true):'-'}</td></tr>`;
            });
            html += '</tbody></table></div>';
        }

        if (job.timeline && job.timeline.length > 0) {
            html += `<div class="premium-card" style="padding:16px; margin-bottom:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px; color:var(--text-primary);">Timeline</h4>
                <div style="display:flex; flex-direction:column; gap:10px;">`;
            const tlIcons = { job_created:'plus-circle', assigned:'user-plus', vehicle_arrived:'truck', inspection_started:'search', maintenance_started:'wrench', paused:'pause-circle', resumed:'play-circle', quality_check:'check-square', approved:'thumbs-up', completed:'check-circle', cancelled:'x-circle', attachment_added:'paperclip', note:'message-circle', status_change:'arrow-right-circle' };
            job.timeline.forEach(n => {
                const icon = tlIcons[n.note_type]||'clock';
                const color = n.note_type==='completed'||n.note_type==='approved'?'#10b981':n.note_type==='cancelled'?'#ef4444':'var(--brand-primary)';
                html += `<div style="display:flex; gap:10px; align-items:flex-start;">
                    <div style="width:28px; height:28px; border-radius:50%; background:${color}22; display:flex; align-items:center; justify-content:center; flex-shrink:0;"><i data-lucide="${icon}" style="width:14px; color:${color};"></i></div>
                    <div><div style="font-size:0.82rem; font-weight:600;">${n.content}</div><div style="font-size:0.72rem; color:var(--text-dim);">${n.author||''} &middot; ${n.created_at?new Date(n.created_at).toLocaleString():''}</div></div>
                </div>`;
            });
            html += '</div></div>';
        }

        if (job.quality_checklist && job.quality_checklist.length > 0) {
            html += `<div class="premium-card" style="padding:16px; margin-bottom:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px; color:var(--text-primary);">QC Checklist ${job.quality_check_passed?'<span style="color:#10b981;">PASSED</span>':'<span style="color:#ef4444;">FAILED</span>'}</h4>
                <div style="display:grid; gap:6px;">`;
            job.quality_checklist.forEach(c => {
                const icon = c.passed?'check-circle':'x-circle';
                const color = c.passed?'#10b981':'#ef4444';
                html += `<div style="display:flex; align-items:center; gap:8px; font-size:0.82rem;"><i data-lucide="${icon}" style="width:14px; color:${color};"></i><span>${c.item}</span>${c.remarks?`<span style="color:var(--text-dim); font-size:0.75rem;">— ${c.remarks}</span>`:''}</div>`;
            });
            html += '</div></div>';
        }

        if (job.attachments && job.attachments.length > 0) {
            html += `<div class="premium-card" style="padding:16px; margin-bottom:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px; color:var(--text-primary);">Attachments (${job.attachments.length})</h4>
                <div style="display:grid; gap:6px;">`;
            job.attachments.forEach(a => {
                const icon = a.file_type==='before_photo'||a.file_type==='after_photo'?'image':a.file_type==='invoice'?'receipt':'file';
                html += `<div style="display:flex; align-items:center; gap:8px; font-size:0.82rem;"><i data-lucide="${icon}" style="width:14px; color:var(--brand-primary);"></i><span>${a.original_name}</span><span style="color:var(--text-dim); font-size:0.72rem;">(${a.file_type||'document'})</span></div>`;
            });
            html += '</div></div>';
        }

        if (job.status !== 'completed' && job.status !== 'cancelled') {
            const transitions = job.valid_transitions || WS_TRANSITIONS[job.status] || [];
            html += `<div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:8px;">`;
            transitions.forEach(t => {
                const label = t.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase());
                let color = 'var(--brand-primary)';
                if (t==='cancelled') color='#ef4444';
                else if (t==='quality_check') color='#06b6d4';
                else if (t==='approved') color='#10b981';
                else if (t==='paused') color='#ef4444';
                else if (t==='inspection') color='#a855f7';
                html += `<button onclick="transitionWorkshopJob(${job.id},'${t}')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; background:${color}; color:#fff; font-size:0.82rem; font-weight:600;">${label}</button>`;
            });
            html += `<button onclick="openWorkshopJobEditModal(${job.id})" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px;">Edit Job</button>`;
            html += `<button onclick="openQualityCheckModal(${job.id})" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; background:#06b6d4; color:#fff;">QC Checklist</button>`;
            html += `<button onclick="cancelWorkshopJob(${job.id})" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; background:#ef4444; color:#fff;">Cancel</button>`;
            html += `</div>`;
        }
        content.innerHTML = html;
        safeCreateIcons();
    } catch (e) { content.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading job details</div>'; }
}

function closeWorkshopJobDetail() { const m = document.getElementById('workshop-job-detail-modal'); if(m) m.style.display='none'; }

const wsNextStatus = { pending:'assigned', assigned:'vehicle_arrived', vehicle_arrived:'inspection', inspection:'in_progress', in_progress:'quality_check', waiting_parts:'in_progress', paused:'in_progress', quality_check:'approved', approved:'completed' };

async function quickUpdateJobStatus(jobId, currentStatus) { await transitionWorkshopJob(jobId, wsNextStatus[currentStatus]); }

async function transitionWorkshopJob(jobId, newStatus) {
    if (!newStatus) return;
    if (newStatus === 'cancelled') { await cancelWorkshopJob(jobId); return; }
    try {
        const res = await fetch(`/api/maintenance/workshop/jobs/${jobId}/transition`, {
            method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'},
            body: JSON.stringify({status: newStatus})
        });
        if (!res.ok) { const e = await res.json(); alert(e.detail||'Failed to transition'); return; }
        loadWorkshopDashboard();
        if (document.getElementById('workshop-job-detail-modal')?.style.display==='flex') openWorkshopJobDetail(jobId);
    } catch(e) { alert('Error transitioning job'); }
}

async function approveWorkshopJob(jobId) {
    try {
        const res = await fetch(`/api/maintenance/workshop/jobs/${jobId}/approve`, {
            method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'},
            body: JSON.stringify({})
        });
        if (!res.ok) { const e = await res.json(); alert(e.detail||'Failed to approve'); return; }
        loadWorkshopDashboard();
        if (document.getElementById('workshop-job-detail-modal')?.style.display==='flex') openWorkshopJobDetail(jobId);
    } catch(e) { alert('Error approving job'); }
}

async function cancelWorkshopJob(jobId) {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    try {
        await fetch(`/api/maintenance/workshop/jobs/${jobId}/cancel`, {
            method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'},
            body: JSON.stringify({reason:'Cancelled by user'})
        });
        closeWorkshopJobDetail();
        loadWorkshopDashboard();
    } catch(e) {}
}

function openQualityCheckModal(jobId) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10001; display:flex; align-items:center; justify-content:center;';
    let checklistHtml = WS_DEFAULT_CHECKLIST.map((item, idx) => `
        <label style="display:flex; align-items:center; gap:10px; padding:8px 12px; border-radius:8px; border:1px solid var(--border-light); cursor:pointer; font-size:0.85rem;">
            <input type="checkbox" id="qc-item-${idx}" style="width:18px; height:18px; accent-color:var(--brand-primary);" />
            <span>${item}</span>
        </label>
    `).join('');
    modal.innerHTML = `<div class="premium-card" style="width:520px; max-width:90vw; max-height:85vh; overflow-y:auto; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.1rem; font-weight:700;">Quality Check Checklist</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
        </div>
        <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:16px;">${checklistHtml}</div>
        <div style="display:flex; flex-direction:column; gap:12px;">
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Inspection Notes</label><textarea id="qc-notes" rows="3" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; resize:vertical;"></textarea></div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Supervisor Name</label><input type="text" id="qc-supervisor" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
        </div>
        <div style="display:flex; gap:10px; margin-top:20px;">
            <button onclick="submitQualityCheck(${jobId})" style="flex:1; padding:10px; border-radius:8px; border:none; background:#10b981; color:#fff; cursor:pointer; font-weight:600;">Submit Checklist</button>
            <button onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
        </div>
    </div>`;
    document.body.appendChild(modal);
}

async function submitQualityCheck(jobId) {
    const notes = document.getElementById('qc-notes')?.value||'';
    const supervisor = document.getElementById('qc-supervisor')?.value||'Supervisor';
    const checklist = WS_DEFAULT_CHECKLIST.map((item, idx) => ({
        item, passed: document.getElementById(`qc-item-${idx}`)?.checked||false, remarks:''
    }));
    try {
        const res = await fetch(`/api/maintenance/workshop/jobs/${jobId}/quality-check`, {
            method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'},
            body: JSON.stringify({checklist, notes, checked_by_name: supervisor})
        });
        document.querySelector('.modal-overlay.active')?.remove();
        openWorkshopJobDetail(jobId);
    } catch(e) {}
}

function openWorkshopJobModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center;';
    modal.innerHTML = `<div class="premium-card" style="width:600px; max-width:90vw; max-height:85vh; overflow-y:auto; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.1rem; font-weight:700;">Create Workshop Job</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
        </div>
        <form onsubmit="submitWorkshopJob(event)" style="display:flex; flex-direction:column; gap:14px;">
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Vehicle *</label><select id="ws-job-vehicle" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"></select></div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Title *</label><input type="text" id="ws-job-title" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Priority</label><select id="ws-job-priority" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option><option value="critical">Critical</option></select></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Due Date</label><input type="date" id="ws-job-due-date" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            </div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Description</label><textarea id="ws-job-desc" rows="2" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; resize:vertical;"></textarea></div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Due Reason</label><input type="text" id="ws-job-reason" placeholder="e.g. Oil change overdue by 500km" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div style="display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">Create Job</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
    loadVehiclesForSelect('ws-job-vehicle');
}

async function loadVehiclesForSelect(selectId) {
    try {
        const res = await fetch('/api/v1/vehicles/live?limit=500', { headers: authHeaders() });
        const vehicles = await res.json();
        const sel = document.getElementById(selectId);
        if (!sel) return;
        sel.innerHTML = '<option value="">-- Select Vehicle --</option>';
        (Array.isArray(vehicles)?vehicles:[]).forEach(v => { sel.innerHTML += `<option value="${v.id}">${v.name||v.id}</option>`; });
    } catch(e) {}
}

async function submitWorkshopJob(e) {
    e.preventDefault();
    const data = {
        device_id: parseInt(document.getElementById('ws-job-vehicle').value),
        title: document.getElementById('ws-job-title').value,
        priority: document.getElementById('ws-job-priority').value,
        due_date: document.getElementById('ws-job-due-date').value||null,
        description: document.getElementById('ws-job-desc').value,
        due_reason: document.getElementById('ws-job-reason').value,
    };
    if (!data.device_id) { alert('Please select a vehicle'); return; }
    await fetch('/api/maintenance/workshop/jobs', {
        method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify(data)
    });
    document.querySelector('.modal-overlay.active')?.remove();
    loadWorkshopDashboard();
}

function openWorkshopJobEditModal(jobId) {
    fetch(`/api/maintenance/workshop/jobs/${jobId}`, { headers: authHeaders() })
        .then(r => r.json()).then(job => {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay active';
            modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10001; display:flex; align-items:center; justify-content:center;';
            modal.innerHTML = `<div class="premium-card" style="width:560px; max-width:90vw; padding:32px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                    <h3 style="font-size:1.1rem; font-weight:700;">Edit Job ${job.job_number}</h3>
                    <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
                </div>
                <form onsubmit="submitWorkshopJobEdit(event, ${jobId})" style="display:flex; flex-direction:column; gap:14px;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Priority</label><select id="ws-edit-priority" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                            ${['low','medium','high','critical'].map(p=>`<option value="${p}" ${job.priority===p?'selected':''}>${p.charAt(0).toUpperCase()+p.slice(1)}</option>`).join('')}
                        </select></div>
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Due Date</label><input type="date" id="ws-edit-due-date" value="${job.due_date?job.due_date.split('T')[0]:''}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                    </div>
                    <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Labour Hours</label><input type="number" id="ws-edit-hours" step="0.5" value="${job.labour_hours||0}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Labour Cost (PKR)</label><input type="number" id="ws-edit-labour-cost" step="0.01" value="${job.labour_cost||0}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Parts Cost (PKR)</label><input type="number" id="ws-edit-parts-cost" step="0.01" value="${job.parts_cost||0}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Misc Cost (PKR)</label><input type="number" id="ws-edit-misc-cost" step="0.01" value="${job.misc_cost||0}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                    </div>
                    <div style="background:var(--fleet-bg); padding:10px 14px; border-radius:8px; font-size:0.85rem; font-weight:600; color:var(--brand-primary);">Total Cost: <span id="ws-edit-total-preview">${formatPKR((job.labour_cost||0)+(job.parts_cost||0)+(job.misc_cost||0), true)}</span></div>
                    <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Notes</label><textarea id="ws-edit-notes" rows="2" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; resize:vertical;">${job.notes||''}</textarea></div>
                    <div style="display:flex; gap:10px; margin-top:8px;">
                        <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                        <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">Save</button>
                    </div>
                </form>
            </div>`;
            document.body.appendChild(modal);
            ['ws-edit-labour-cost','ws-edit-parts-cost','ws-edit-misc-cost'].forEach(id => {
                document.getElementById(id)?.addEventListener('input', () => {
                    const l = parseFloat(document.getElementById('ws-edit-labour-cost')?.value)||0;
                    const p = parseFloat(document.getElementById('ws-edit-parts-cost')?.value)||0;
                    const m = parseFloat(document.getElementById('ws-edit-misc-cost')?.value)||0;
                    document.getElementById('ws-edit-total-preview').textContent = formatPKR(l+p+m, true);
                });
            });
        });
}

async function submitWorkshopJobEdit(e, jobId) {
    e.preventDefault();
    const data = {
        priority: document.getElementById('ws-edit-priority').value,
        due_date: document.getElementById('ws-edit-due-date').value||null,
        labour_hours: parseFloat(document.getElementById('ws-edit-hours').value)||0,
        labour_cost: parseFloat(document.getElementById('ws-edit-labour-cost').value)||0,
        parts_cost: parseFloat(document.getElementById('ws-edit-parts-cost').value)||0,
        misc_cost: parseFloat(document.getElementById('ws-edit-misc-cost')?.value)||0,
        notes: document.getElementById('ws-edit-notes').value,
    };
    await fetch(`/api/maintenance/workshop/jobs/${jobId}`, {
        method:'PUT', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify(data)
    });
    document.querySelector('.modal-overlay.active')?.remove();
    openWorkshopJobDetail(jobId);
    loadWorkshopDashboard();
}

// ==================== TECHNICIANS ====================

async function renderWorkshopTechnicians() {
    const tc = document.getElementById('workshop-tab-content');
    if (!tc) return;
    try {
        const res = await fetch('/api/maintenance/workshop/technicians?page_size=200', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed to load technicians');
        const data = await res.json();
        const techs = data.items || [];
        let html = `<div style="display:flex; gap:10px; margin-bottom:16px; align-items:center;">
            <input type="text" id="ws-tech-search" placeholder="Search technicians..." onkeyup="filterWorkshopTechs()" style="flex:1; min-width:200px; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/>
            <button onclick="openTechnicianModal()" class="glass-btn primary" style="padding:10px 20px; border:none; cursor:pointer; border-radius:8px; font-weight:600; color:#fff;">+ Add Technician</button>
        </div>`;
        html += `<table class="modern-table" style="width:100%;"><thead><tr><th>Name</th><th>Employee ID</th><th>Phone</th><th>Skills</th><th>Status</th><th>Active Jobs</th><th>Workload</th><th>Completed</th><th>Actions</th></tr></thead><tbody id="ws-techs-tbody">`;
        techs.forEach(t => {
            const statusColor = t.status==='available'?'#10b981':t.status==='busy'?'#f59e0b':'#6b7280';
            const maxWl = t.max_workload||3;
            const wlPct = t.workload_percent||0;
            const wlColor = wlPct>=100?'#ef4444':wlPct>=60?'#f59e0b':'#10b981';
            html += `<tr data-search="${(t.name+' '+t.employee_id).toLowerCase()}">
                <td><strong>${t.name}</strong></td><td>${t.employee_id}</td><td>${t.phone||'-'}</td>
                <td>${(t.skills||[]).map(s=>`<span style="display:inline-block; padding:2px 8px; border-radius:8px; font-size:0.7rem; background:#3b82f622; color:#3b82f6; margin:1px;">${s}</span>`).join(' ')||'-'}</td>
                <td><span style="display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:600; background:${statusColor}22; color:${statusColor};">${t.status.charAt(0).toUpperCase()+t.status.slice(1)}</span></td>
                <td>${t.active_jobs||0}</td>
                <td><div style="display:flex; align-items:center; gap:6px;"><div style="width:60px; height:6px; border-radius:3px; background:#d1d5db; overflow:hidden;"><div style="width:${Math.min(wlPct,100)}%; height:100%; background:${wlColor}; border-radius:3px;"></div></div><span style="font-size:0.72rem; color:var(--text-dim);">${t.active_jobs||0}/${maxWl}</span></div></td>
                <td>${t.completed_jobs||0}</td>
                <td>
                    <button onclick="openEditTechnicianModal(${t.id})" class="glass-btn" style="padding:4px 10px; font-size:0.75rem; border:none; cursor:pointer; border-radius:6px;">Edit</button>
                    <button onclick="deleteTechnician(${t.id})" class="glass-btn" style="padding:4px 10px; font-size:0.75rem; border:none; cursor:pointer; border-radius:6px; background:#ef4444; color:#fff; margin-left:4px;">Delete</button>
                </td></tr>`;
        });
        html += '</tbody></table>';
        html += `<div style="margin-top:12px; color:var(--text-dim); font-size:0.8rem;">Showing ${techs.length} technicians</div>`;
        tc.innerHTML = html;
        safeCreateIcons();
    } catch(e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading technicians</div>'; }
}

function filterWorkshopTechs() {
    const search = (document.getElementById('ws-tech-search')?.value||'').toLowerCase();
    document.querySelectorAll('#ws-techs-tbody tr').forEach(row => { row.style.display = !search||(row.dataset.search||'').includes(search)?'':'none'; });
}

function openTechnicianModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center;';
    modal.innerHTML = `<div class="premium-card" style="width:500px; max-width:90vw; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.1rem; font-weight:700;">Add Technician</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
        </div>
        <form onsubmit="submitTechnician(event)" style="display:flex; flex-direction:column; gap:14px;">
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Name *</label><input type="text" id="tech-name" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Employee ID *</label><input type="text" id="tech-eid" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Phone</label><input type="text" id="tech-phone" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            </div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Max Workload (concurrent jobs)</label><input type="number" id="tech-max-workload" min="1" max="10" value="3" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Skills (comma-separated)</label><input type="text" id="tech-skills" placeholder="oil_change, brake_service, electrical" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div style="display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">Create</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
}

async function submitTechnician(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('tech-name').value,
        employee_id: document.getElementById('tech-eid').value,
        phone: document.getElementById('tech-phone').value,
        max_workload: parseInt(document.getElementById('tech-max-workload').value)||3,
        skills: (document.getElementById('tech-skills').value||'').split(',').map(s=>s.trim()).filter(Boolean),
    };
    const res = await fetch('/api/maintenance/workshop/technicians', {
        method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify(data)
    });
    if (!res.ok) { const err = await res.json(); alert(err.detail||'Error creating technician'); return; }
    document.querySelector('.modal-overlay.active')?.remove();
    renderWorkshopTechnicians();
}

async function openEditTechnicianModal(techId) {
    const res = await fetch('/api/maintenance/workshop/technicians?page_size=200', { headers: authHeaders() });
    const data = await res.json();
    const tech = (data.items||[]).find(t=>t.id===techId);
    if (!tech) return;
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center;';
    modal.innerHTML = `<div class="premium-card" style="width:500px; max-width:90vw; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.1rem; font-weight:700;">Edit Technician</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
        </div>
        <form onsubmit="submitEditTechnician(event, ${techId})" style="display:flex; flex-direction:column; gap:14px;">
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Name</label><input type="text" id="tech-edit-name" value="${tech.name}" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Phone</label><input type="text" id="tech-edit-phone" value="${tech.phone||''}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Status</label><select id="tech-edit-status" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                    <option value="available" ${tech.status==='available'?'selected':''}>Available</option>
                    <option value="busy" ${tech.status==='busy'?'selected':''}>Busy</option>
                    <option value="off_duty" ${tech.status==='off_duty'?'selected':''}>Off Duty</option>
                </select></div>
            </div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Max Workload</label><input type="number" id="tech-edit-max-workload" min="1" max="10" value="${tech.max_workload||3}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Skills (comma-separated)</label><input type="text" id="tech-edit-skills" value="${(tech.skills||[]).join(', ')}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div style="display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">Save</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
}

async function submitEditTechnician(e, techId) {
    e.preventDefault();
    const data = {
        name: document.getElementById('tech-edit-name').value,
        phone: document.getElementById('tech-edit-phone').value,
        status: document.getElementById('tech-edit-status').value,
        max_workload: parseInt(document.getElementById('tech-edit-max-workload').value)||3,
        skills: (document.getElementById('tech-edit-skills').value||'').split(',').map(s=>s.trim()).filter(Boolean),
    };
    await fetch(`/api/maintenance/workshop/technicians/${techId}`, {
        method:'PUT', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify(data)
    });
    document.querySelector('.modal-overlay.active')?.remove();
    renderWorkshopTechnicians();
}

async function deleteTechnician(techId) {
    if (!confirm('Delete this technician?')) return;
    await fetch(`/api/maintenance/workshop/technicians/${techId}`, { method:'DELETE', headers: authHeaders() });
    renderWorkshopTechnicians();
}

// ==================== INVENTORY & SPARE PARTS MODULE ====================
const INV_CATEGORIES = ['engine','brakes','electrical','filters','fluids','body','tyres','tools','other'];
const INV_UNITS = ['pcs','litres','kg','metres','sets','bottles','cans','boxes'];
const INV_MOVEMENT_TYPES = ['stock_in','stock_out','adjustment','transfer','return','scrap'];


// ==================== INVENTORY DASHBOARD ====================

async function renderInventoryTab() {
    const tc = document.getElementById('workshop-tab-content');
    if (!tc) return;
    try {
        const [dashRes, partsRes] = await Promise.all([
            fetch('/api/maintenance/inventory/dashboard', { headers: authHeaders() }),
            fetch('/api/maintenance/inventory/parts?page_size=200', { headers: authHeaders() })
        ]);
        const dash = dashRes.ok ? await dashRes.json() : { kpis: {}, alerts: [] };
        const partsData = partsRes.ok ? await partsRes.json() : { items: [], total: 0 };
        const kpis = dash.kpis || {};
        const alerts = dash.alerts || [];

        let html = `<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:20px;">`;
        const kpiItems = [
            { label: 'Total Parts', value: kpis.total_parts || 0, icon: 'package', color: '#3b82f6' },
            { label: 'Available Stock', value: kpis.available_stock || 0, icon: 'box', color: '#10b981' },
            { label: 'Low Stock', value: kpis.low_stock_items || 0, icon: 'alert-triangle', color: '#f59e0b' },
            { label: 'Out of Stock', value: kpis.out_of_stock || 0, icon: 'x-circle', color: '#ef4444' },
            { label: 'Inventory Value', value: formatPKR(kpis.total_inventory_value || 0, true), icon: 'banknote', color: '#8b5cf6' },
            { label: 'Issued Today', value: kpis.parts_issued_today || 0, icon: 'arrow-up-right', color: '#06b6d4' },
            { label: 'Returned Today', value: kpis.parts_returned_today || 0, icon: 'arrow-down-left', color: '#14b8a6' },
            { label: 'Pending Reorder', value: kpis.pending_purchase_items || 0, icon: 'shopping-cart', color: '#f97316' },
        ];
        html += kpiItems.map(i => `<div class="premium-card mini-stat" style="padding:14px; text-align:center;"><div style="display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:6px;"><i data-lucide="${i.icon}" style="width:16px; color:${i.color};"></i><span style="font-size:0.72rem; color:var(--text-dim); text-transform:uppercase; font-weight:600;">${i.label}</span></div><div style="font-size:1.4rem; font-weight:800; color:${i.color};">${i.value}</div></div>`).join('');
        html += `</div>`;

        if (alerts.length > 0) {
            html += `<div class="premium-card" style="padding:16px; margin-bottom:16px; border-left:4px solid #ef4444;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:10px; color:var(--text-primary);">Stock Alerts (${alerts.length})</h4>
                <div style="display:grid; gap:6px;">`;
            alerts.forEach(a => {
                const color = a.severity === 'critical' ? '#ef4444' : '#f59e0b';
                html += `<div style="display:flex; align-items:center; gap:8px; font-size:0.82rem; padding:6px 10px; border-radius:6px; background:${color}11;"><i data-lucide="${a.type === 'out_of_stock' ? 'x-circle' : a.type === 'expired' ? 'clock' : 'alert-triangle'}" style="width:14px; color:${color};"></i><span>${a.message}</span></div>`;
            });
            html += `</div></div>`;
        }

        html += `<div style="display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap; align-items:center;">
            <input type="text" id="inv-search" placeholder="Search parts..." onkeyup="filterInventory()" style="flex:1; min-width:200px; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/>
            <select id="inv-cat-filter" onchange="filterInventory()" style="padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                <option value="">All Categories</option>
                ${INV_CATEGORIES.map(c => `<option value="${c}">${c.charAt(0).toUpperCase()+c.slice(1)}</option>`).join('')}
            </select>
            <select id="inv-status-filter" onchange="filterInventory()" style="padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                <option value="">All Stock Status</option>
                <option value="in_stock">In Stock</option><option value="low_stock">Low Stock</option><option value="out_of_stock">Out of Stock</option><option value="overstocked">Overstocked</option>
            </select>
            <button onclick="openCreatePartModal()" class="glass-btn primary" style="padding:10px 16px; border:none; cursor:pointer; border-radius:8px; font-weight:600; color:#fff;">+ Add Part</button>
        </div>`;

        const parts = partsData.items || [];
        html += `<table class="modern-table" style="width:100%;"><thead><tr>
            <th>Part #</th><th>Name</th><th>Category</th><th>Brand</th><th>Qty</th><th>Min</th><th>Unit Cost</th><th>Total Value</th><th>Location</th><th>Status</th><th>Actions</th>
        </tr></thead><tbody id="inv-parts-tbody">`;
        parts.forEach(p => {
            const st = p.stock_status;
            const stColor = st === 'in_stock' ? '#10b981' : st === 'low_stock' ? '#f59e0b' : st === 'out_of_stock' ? '#ef4444' : '#8b5cf6';
            const stLabel = st === 'in_stock' ? 'In Stock' : st === 'low_stock' ? 'Low' : st === 'out_of_stock' ? 'Out' : 'Over';
            html += `<tr data-category="${p.category||''}" data-stock="${st}" data-search="${(p.part_number+' '+p.name+' '+(p.brand||'')+' '+(p.supplier||'')).toLowerCase()}">
                <td><strong>${p.part_number}</strong></td><td>${p.name}</td><td>${(p.category||'-').charAt(0).toUpperCase()+(p.category||'').slice(1)}</td>
                <td>${p.brand||'-'}</td>
                <td style="font-weight:700; color:${stColor};">${p.current_quantity} ${p.unit}</td>
                <td>${p.minimum_stock}</td>
                <td>${formatPKR(p.unit_cost, true)}</td>
                <td>${formatPKR(p.total_value, true)}</td>
                <td>${p.storage_location||'-'}</td>
                <td><span style="display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.72rem; font-weight:600; background:${stColor}22; color:${stColor};">${stLabel}</span></td>
                <td>
                    <button onclick="openPartDetail(${p.id})" class="glass-btn" style="padding:4px 8px; font-size:0.72rem; border:none; cursor:pointer; border-radius:6px; background:var(--brand-primary); color:#fff;">View</button>
                    <button onclick="openStockMovementModal(${p.id},'${p.name}','${p.unit}',${p.current_quantity})" class="glass-btn" style="padding:4px 8px; font-size:0.72rem; border:none; cursor:pointer; border-radius:6px; background:#10b981; color:#fff; margin-left:3px;">Move</button>
                </td></tr>`;
        });
        html += '</tbody></table>';
        html += `<div style="margin-top:12px; color:var(--text-dim); font-size:0.8rem;">Showing ${parts.length} parts</div>`;
        tc.innerHTML = html;
        safeCreateIcons();
    } catch (e) {
        tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading inventory</div>';
    }
}

function filterInventory() {
    const search = (document.getElementById('inv-search')?.value||'').toLowerCase();
    const cat = document.getElementById('inv-cat-filter')?.value||'';
    const status = document.getElementById('inv-status-filter')?.value||'';
    document.querySelectorAll('#inv-parts-tbody tr').forEach(row => {
        row.style.display = (!search||(row.dataset.search||'').includes(search))&&(!cat||row.dataset.category===cat)&&(!status||row.dataset.stock===status)?'':'none';
    });
}

// ==================== PART DETAIL ====================

async function openPartDetail(partId) {
    const modal = document.getElementById('workshop-job-detail-modal');
    const content = document.getElementById('workshop-job-detail-content');
    const titleEl = document.getElementById('ws-detail-title');
    if (!modal||!content) return;
    modal.style.display = 'flex';
    content.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const res = await fetch(`/api/maintenance/inventory/parts/${partId}`, { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed to load part');
        const p = await res.json();
        titleEl.textContent = `${p.part_number} — ${p.name}`;

        const stColor = p.stock_status === 'in_stock' ? '#10b981' : p.stock_status === 'low_stock' ? '#f59e0b' : p.stock_status === 'out_of_stock' ? '#ef4444' : '#8b5cf6';
        let html = `<div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px;">
            <div class="premium-card" style="padding:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px;">Part Information</h4>
                <div style="display:grid; gap:8px; font-size:0.82rem;">
                    <div><span style="color:var(--text-dim);">Part Number:</span> <strong>${p.part_number}</strong></div>
                    <div><span style="color:var(--text-dim);">Name:</span> ${p.name}</div>
                    <div><span style="color:var(--text-dim);">Category:</span> ${(p.category||'-').charAt(0).toUpperCase()+(p.category||'').slice(1)}</div>
                    <div><span style="color:var(--text-dim);">Brand:</span> ${p.brand||'-'}</div>
                    <div><span style="color:var(--text-dim);">Vehicle Type:</span> ${p.compatible_vehicle_category||'All'}</div>
                    <div><span style="color:var(--text-dim);">Unit:</span> ${p.unit}</div>
                    <div><span style="color:var(--text-dim);">Supplier:</span> ${p.supplier||'-'}</div>
                    <div><span style="color:var(--text-dim);">Location:</span> ${p.storage_location||'-'}</div>
                </div>
            </div>
            <div class="premium-card" style="padding:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px;">Stock & Cost</h4>
                <div style="display:grid; gap:8px; font-size:0.82rem;">
                    <div><span style="color:var(--text-dim);">Current Stock:</span> <strong style="color:${stColor};">${p.current_quantity} ${p.unit}</strong></div>
                    <div><span style="color:var(--text-dim);">Minimum:</span> ${p.minimum_stock} ${p.unit}</div>
                    <div><span style="color:var(--text-dim);">Maximum:</span> ${p.maximum_stock} ${p.unit}</div>
                    <div><span style="color:var(--text-dim);">Unit Cost:</span> ${formatPKR(p.unit_cost, true)}</div>
                    <div style="border-top:1px solid var(--border-light); padding-top:6px; font-weight:700;"><span style="color:var(--text-dim);">Total Value:</span> ${formatPKR(p.total_value, true)}</div>
                    <div><span style="color:var(--text-dim);">Status:</span> <span style="color:${stColor}; font-weight:600;">${p.stock_status.replace(/_/g,' ').toUpperCase()}</span></div>
                    ${p.expiry_date ? `<div><span style="color:var(--text-dim);">Expiry:</span> ${new Date(p.expiry_date).toLocaleDateString()}</div>` : ''}
                </div>
            </div>
        </div>`;

        if (p.recent_movements && p.recent_movements.length > 0) {
            html += `<div class="premium-card" style="padding:16px; margin-bottom:16px;">
                <h4 style="font-size:0.85rem; font-weight:700; margin-bottom:12px;">Recent Movements</h4>
                <table class="modern-table" style="width:100%;"><thead><tr><th>Date</th><th>Type</th><th>Qty</th><th>Before</th><th>After</th><th>Cost</th><th>Reason</th><th>User</th></tr></thead><tbody>`;
            p.recent_movements.forEach(m => {
                const typeColors = { stock_in:'#10b981', stock_out:'#ef4444', adjustment:'#f59e0b', transfer:'#3b82f6', return:'#14b8a6', scrap:'#6b7280' };
                const c = typeColors[m.movement_type]||'#6b7280';
                html += `<tr>
                    <td>${m.created_at?new Date(m.created_at).toLocaleDateString():'-'}</td>
                    <td><span style="color:${c}; font-weight:600;">${m.movement_type.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</span></td>
                    <td style="font-weight:700; color:${m.quantity>0?'#10b981':'#ef4444'};">${m.quantity>0?'+':''}${m.quantity}</td>
                    <td>${m.stock_before}</td><td>${m.stock_after}</td>
                    <td>${m.total_cost?formatPKR(m.total_cost,true):'-'}</td>
                    <td>${m.reason||'-'}</td><td>${m.performed_by||'-'}</td></tr>`;
            });
            html += '</tbody></table></div>';
        }

        html += `<div style="display:flex; gap:10px; flex-wrap:wrap;">
            <button onclick="openStockMovementModal(${p.id},'${p.name}','${p.unit}',${p.current_quantity})" class="glass-btn primary" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-weight:600; color:#fff;">Record Movement</button>
            <button onclick="openEditPartModal(${p.id})" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px;">Edit Part</button>
            <button onclick="deletePart(${p.id})" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; background:#ef4444; color:#fff;">Deactivate</button>
        </div>`;

        content.innerHTML = html;
        safeCreateIcons();
    } catch (e) {
        content.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading part details</div>';
    }
}

// ==================== CREATE PART ====================

function openCreatePartModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center;';
    modal.innerHTML = `<div class="premium-card" style="width:600px; max-width:90vw; max-height:85vh; overflow-y:auto; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.1rem; font-weight:700;">Add Spare Part</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
        </div>
        <form onsubmit="submitCreatePart(event)" style="display:flex; flex-direction:column; gap:12px;">
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Part Number *</label><input type="text" id="inv-pn" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Name *</label><input type="text" id="inv-name" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Category</label><select id="inv-cat" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                    ${INV_CATEGORIES.map(c => `<option value="${c}">${c.charAt(0).toUpperCase()+c.slice(1)}</option>`).join('')}
                </select></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Unit</label><select id="inv-unit" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                    ${INV_UNITS.map(u => `<option value="${u}">${u}</option>`).join('')}
                </select></div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Brand</label><input type="text" id="inv-brand" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Vehicle Category</label><select id="inv-vcat" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                    <option value="all">All</option><option value="truck">Truck</option><option value="bus">Bus</option><option value="car">Car</option><option value="generator">Generator</option>
                </select></div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Initial Qty</label><input type="number" id="inv-qty" min="0" value="0" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Min Stock</label><input type="number" id="inv-min" min="0" value="5" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Max Stock</label><input type="number" id="inv-max" min="1" value="100" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Unit Cost (PKR)</label><input type="number" id="inv-cost" min="0" step="0.01" value="0" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Supplier</label><input type="text" id="inv-supplier" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            </div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Storage Location</label><input type="text" id="inv-location" placeholder="e.g. Warehouse A, Shelf B3" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Description</label><textarea id="inv-desc" rows="2" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; resize:vertical;"></textarea></div>
            <div style="display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">Create Part</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
}

async function submitCreatePart(e) {
    e.preventDefault();
    const data = {
        part_number: document.getElementById('inv-pn').value,
        name: document.getElementById('inv-name').value,
        category: document.getElementById('inv-cat').value,
        unit: document.getElementById('inv-unit').value,
        brand: document.getElementById('inv-brand').value,
        compatible_vehicle_category: document.getElementById('inv-vcat').value,
        current_quantity: parseFloat(document.getElementById('inv-qty').value)||0,
        minimum_stock: parseFloat(document.getElementById('inv-min').value)||0,
        maximum_stock: parseFloat(document.getElementById('inv-max').value)||100,
        unit_cost: parseFloat(document.getElementById('inv-cost').value)||0,
        supplier: document.getElementById('inv-supplier').value,
        storage_location: document.getElementById('inv-location').value,
        description: document.getElementById('inv-desc').value,
    };
    const res = await fetch('/api/maintenance/inventory/parts', {
        method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify(data)
    });
    if (!res.ok) { const err = await res.json(); alert(err.detail||'Error creating part'); return; }
    document.querySelector('.modal-overlay.active')?.remove();
    renderInventoryTab();
}

// ==================== STOCK MOVEMENT ====================

function openStockMovementModal(partId, partName, unit, currentQty) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10001; display:flex; align-items:center; justify-content:center;';
    modal.innerHTML = `<div class="premium-card" style="width:480px; max-width:90vw; padding:32px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="font-size:1.1rem; font-weight:700;">Stock Movement — ${partName}</h3>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
        </div>
        <div style="font-size:0.82rem; color:var(--text-dim); margin-bottom:16px;">Current stock: <strong>${currentQty} ${unit}</strong></div>
        <form onsubmit="submitStockMovement(event, ${partId})" style="display:flex; flex-direction:column; gap:14px;">
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Movement Type *</label><select id="mov-type" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                <option value="stock_in">Stock In</option><option value="stock_out">Stock Out</option><option value="adjustment">Adjustment</option>
                <option value="transfer">Transfer</option><option value="return">Return</option><option value="scrap">Scrap</option>
            </select></div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Quantity *</label><input type="number" id="mov-qty" min="0.01" step="0.01" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Unit Cost (PKR)</label><input type="number" id="mov-cost" step="0.01" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            </div>
            <div id="mov-to-loc-div" style="display:none;"><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">To Location</label><input type="text" id="mov-to-loc" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Reason</label><input type="text" id="mov-reason" placeholder="e.g. Workshop issue, Purchase restock" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
            <div style="display:flex; gap:10px; margin-top:8px;">
                <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">Submit</button>
            </div>
        </form>
    </div>`;
    document.body.appendChild(modal);
    document.getElementById('mov-type').addEventListener('change', function() {
        document.getElementById('mov-to-loc-div').style.display = this.value === 'transfer' ? '' : 'none';
    });
}

async function submitStockMovement(e, partId) {
    e.preventDefault();
    const type = document.getElementById('mov-type').value;
    const qty = parseFloat(document.getElementById('mov-qty').value)||0;
    const cost = parseFloat(document.getElementById('mov-cost').value)||0;
    const reason = document.getElementById('mov-reason').value;
    const toLoc = document.getElementById('mov-to-loc')?.value||'';

    let endpoint = `/api/maintenance/inventory/parts/${partId}/${type.replace('_','-')}`;
    let body = { quantity: qty, reason: reason };
    if (type === 'stock_in') body.unit_cost = cost;
    if (type === 'adjustment') { body.new_quantity = qty; }
    if (type === 'transfer') body.to_location = toLoc;

    const res = await fetch(endpoint, {
        method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    if (!res.ok) { const err = await res.json(); alert(err.detail||'Error recording movement'); return; }
    document.querySelector('.modal-overlay.active')?.remove();
    renderInventoryTab();
}

// ==================== EDIT PART ====================

function openEditPartModal(partId) {
    fetch(`/api/maintenance/inventory/parts/${partId}`, { headers: authHeaders() })
        .then(r => r.json()).then(p => {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay active';
            modal.style.cssText = 'position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:10001; display:flex; align-items:center; justify-content:center;';
            modal.innerHTML = `<div class="premium-card" style="width:560px; max-width:90vw; padding:32px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                    <h3 style="font-size:1.1rem; font-weight:700;">Edit ${p.part_number}</h3>
                    <button onclick="this.closest('.modal-overlay').remove()" style="background:none; border:none; font-size:1.2rem; cursor:pointer; color:var(--text-secondary);">&times;</button>
                </div>
                <form onsubmit="submitEditPart(event, ${partId})" style="display:flex; flex-direction:column; gap:12px;">
                    <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Name</label><input type="text" id="ep-name" value="${p.name}" required style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Category</label><select id="ep-cat" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;">
                            ${INV_CATEGORIES.map(c => `<option value="${c}" ${p.category===c?'selected':''}>${c.charAt(0).toUpperCase()+c.slice(1)}</option>`).join('')}
                        </select></div>
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Brand</label><input type="text" id="ep-brand" value="${p.brand||''}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Min Stock</label><input type="number" id="ep-min" min="0" value="${p.minimum_stock}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Max Stock</label><input type="number" id="ep-max" min="1" value="${p.maximum_stock}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Unit Cost (PKR)</label><input type="number" id="ep-cost" step="0.01" value="${p.unit_cost}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Supplier</label><input type="text" id="ep-supplier" value="${p.supplier||''}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                        <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Location</label><input type="text" id="ep-location" value="${p.storage_location||''}" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem;"/></div>
                    </div>
                    <div><label style="font-size:0.78rem; font-weight:600; color:var(--text-secondary);">Description</label><textarea id="ep-desc" rows="2" style="width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border-light); background:var(--fleet-bg); color:var(--text-primary); font-size:0.85rem; resize:vertical;">${p.description||''}</textarea></div>
                    <div style="display:flex; gap:10px; margin-top:8px;">
                        <button type="button" onclick="this.closest('.modal-overlay').remove()" style="flex:1; padding:10px; border-radius:8px; border:1px solid var(--border-light); background:#fff; color:var(--text-secondary); cursor:pointer; font-weight:600;">Cancel</button>
                        <button type="submit" style="flex:1; padding:10px; border-radius:8px; border:none; background:var(--brand-primary); color:#fff; cursor:pointer; font-weight:600;">Save</button>
                    </div>
                </form>
            </div>`;
            document.body.appendChild(modal);
        });
}

async function submitEditPart(e, partId) {
    e.preventDefault();
    const data = {
        name: document.getElementById('ep-name').value,
        category: document.getElementById('ep-cat').value,
        brand: document.getElementById('ep-brand').value,
        minimum_stock: parseFloat(document.getElementById('ep-min').value)||0,
        maximum_stock: parseFloat(document.getElementById('ep-max').value)||100,
        unit_cost: parseFloat(document.getElementById('ep-cost').value)||0,
        supplier: document.getElementById('ep-supplier').value,
        storage_location: document.getElementById('ep-location').value,
        description: document.getElementById('ep-desc').value,
    };
    const res = await fetch(`/api/maintenance/inventory/parts/${partId}`, {
        method:'PUT', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify(data)
    });
    if (!res.ok) { const err = await res.json(); alert(err.detail||'Error updating part'); return; }
    document.querySelector('.modal-overlay.active')?.remove();
    openPartDetail(partId);
}

// ==================== DELETE PART ====================

async function deletePart(partId) {
    if (!confirm('Deactivate this part?')) return;
    const res = await fetch(`/api/maintenance/inventory/parts/${partId}`, { method:'DELETE', headers: authHeaders() });
    if (!res.ok) { alert('Error deactivating part'); return; }
    document.getElementById('workshop-job-detail-modal').style.display = 'none';
    renderInventoryTab();
}

// ==================== REPORTS & ANALYTICS MODULE ====================

let reportsChartInstances = {};

function openReportsView() {
    switchView('reports');
    setTimeout(loadReportsDashboard, 200);
}

async function loadReportsDashboard() {
    try {
        const res = await fetch('/api/maintenance/reports/dashboard', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed to load reports');
        const kpis = await res.json();
        renderReportsKPIs(kpis);
        switchReportsTab('overview');
    } catch (e) { console.error('Reports dashboard error:', e); }
}

function renderReportsKPIs(k) {
    const c = document.getElementById('reports-kpi-cards');
    if (!c) return;
    const items = [
        { label: 'Total Maint. Cost', value: formatPKR(k.total_maintenance_cost || 0, true), icon: 'banknote', color: '#3b82f6' },
        { label: 'Monthly Cost', value: formatPKR(k.monthly_maintenance_cost || 0, true), icon: 'calendar', color: '#8b5cf6' },
        { label: 'Total Jobs', value: k.total_workshop_jobs || 0, icon: 'clipboard-list', color: '#06b6d4' },
        { label: 'Completed', value: k.completed_jobs || 0, icon: 'check-circle', color: '#10b981' },
        { label: 'Pending', value: k.pending_jobs || 0, icon: 'clock', color: '#f59e0b' },
        { label: 'Overdue', value: k.overdue_vehicles || 0, icon: 'alert-triangle', color: '#ef4444' },
        { label: 'Fleet Health', value: (k.fleet_health_score || 0) + '%', icon: 'heart-pulse', color: '#14b8a6' },
        { label: 'Inventory Value', value: formatPKR(k.inventory_value || 0, true), icon: 'package', color: '#f97316' },
        { label: 'Parts Consumed', value: k.parts_consumed || 0, icon: 'arrow-up-right', color: '#ec4899' },
        { label: 'Avg Repair Time', value: (k.average_repair_time_hours || 0) + 'h', icon: 'timer', color: '#06b6d4' },
    ];
    if (k.top_maintenance_vehicle) {
        items.push({ label: 'Top Maint. Vehicle', value: k.top_maintenance_vehicle.name || 'N/A', icon: 'truck', color: '#ef4444' });
    }
    c.innerHTML = items.map(i => `<div class="premium-card mini-stat" style="padding:12px; text-align:center;"><div style="display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:4px;"><i data-lucide="${i.icon}" style="width:16px; color:${i.color};"></i><span style="font-size:0.7rem; color:var(--text-dim); text-transform:uppercase; font-weight:600;">${i.label}</span></div><div style="font-size:1.2rem; font-weight:800; color:${i.color};">${i.value}</div></div>`).join('');
    safeCreateIcons();
}

function switchReportsTab(tab) {
    document.querySelectorAll('.reports-tab-btn').forEach(b => { b.classList.remove('active'); b.style.background = 'transparent'; b.style.color = 'var(--text-secondary)'; });
    const btn = document.querySelector(`.reports-tab-btn[data-rptab="${tab}"]`);
    if (btn) { btn.classList.add('active'); btn.style.background = 'var(--brand-primary)'; btn.style.color = '#fff'; }
    Object.values(reportsChartInstances).forEach(c => { try { c.destroy(); } catch(e){} });
    reportsChartInstances = {};
    if (tab === 'overview') loadReportsOverview();
    else if (tab === 'cost') loadCostReports();
    else if (tab === 'workshop') loadWorkshopReports();
    else if (tab === 'technicians') loadTechnicianReports();
    else if (tab === 'inventory') loadInventoryReports();
    else if (tab === 'vehicles') loadVehicleReports();
    else if (tab === 'monthly') loadMonthlyYearlyReports();
}

// ==================== OVERVIEW ====================

async function loadReportsOverview() {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    tc.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const [costRes, statusRes] = await Promise.all([
            fetch('/api/maintenance/reports/charts/cost-trend?months=12', { headers: authHeaders() }),
            fetch('/api/maintenance/reports/charts/status-distribution', { headers: authHeaders() })
        ]);
        const costData = costRes.ok ? await costRes.json() : { labels: [], costs: [], counts: [] };
        const statusData = statusRes.ok ? await statusRes.json() : { labels: [], values: [] };

        let html = `<div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px;">
            <div class="premium-card" style="padding:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Maintenance Cost Trend (12 Months)</h4><div style="position:relative; height:280px;"><canvas id="rptCostTrend"></canvas></div></div>
            <div class="premium-card" style="padding:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Job Status Distribution</h4><div style="position:relative; height:280px;"><canvas id="rptStatusDist"></canvas></div></div>
        </div>`;
        html += `<div style="display:flex; gap:10px; margin-bottom:16px;">
            <button onclick="exportReportCSV('overview')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Export CSV</button>
            <button onclick="window.print()" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Print</button>
        </div>`;
        tc.innerHTML = html;

        if (costData.labels.length > 0) {
            const ctx1 = document.getElementById('rptCostTrend');
            if (ctx1) reportsChartInstances.costTrend = new Chart(ctx1, {
                type: 'line', data: { labels: costData.labels, datasets: [{ label: 'Cost (PKR)', data: costData.costs, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.3 }, { label: 'Jobs', data: costData.counts, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.1)', fill: false, tension: 0.3, yAxisID: 'y1' }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } }, scales: { y: { position: 'left', ticks: { callback: v => 'Rs.' + (v/1000).toFixed(0) + 'k' } }, y1: { position: 'right', grid: { drawOnChartArea: false } } } }
            });
        }
        if (statusData.labels.length > 0) {
            const ctx2 = document.getElementById('rptStatusDist');
            if (ctx2) {
                const colors = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#f97316','#14b8a6','#6b7280','#a855f7'];
                reportsChartInstances.statusDist = new Chart(ctx2, {
                    type: 'doughnut', data: { labels: statusData.labels, datasets: [{ data: statusData.values, backgroundColor: colors.slice(0, statusData.labels.length) }] },
                    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { font: { size: 11 } } } } }
                });
            }
        }
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading overview</div>'; }
}

// ==================== COST ANALYSIS ====================

async function loadCostReports() {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    tc.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const res = await fetch('/api/maintenance/reports/cost-analytics?days=365', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();

        let html = `<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px;">
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim); text-transform:uppercase;">Labour Cost</div><div style="font-size:1.3rem; font-weight:800; color:#3b82f6;">${formatPKR(data.total_labour_cost, true)}</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim); text-transform:uppercase;">Parts Cost</div><div style="font-size:1.3rem; font-weight:800; color:#10b981;">${formatPKR(data.total_parts_cost, true)}</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim); text-transform:uppercase;">Misc Cost</div><div style="font-size:1.3rem; font-weight:800; color:#f59e0b;">${formatPKR(data.total_misc_cost, true)}</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim); text-transform:uppercase;">Maintenance Cost</div><div style="font-size:1.3rem; font-weight:800; color:#8b5cf6;">${formatPKR(data.total_maintenance_cost, true)}</div></div>
        </div>`;
        html += `<div style="display:grid; grid-template-columns:2fr 1fr; gap:20px; margin-bottom:20px;">
            <div class="premium-card" style="padding:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Monthly Cost Trend</h4><div style="position:relative; height:280px;"><canvas id="rptCostMonthly"></canvas></div></div>
            <div class="premium-card" style="padding:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Cost Breakdown</h4><div style="position:relative; height:280px;"><canvas id="rptCostPie"></canvas></div></div>
        </div>`;
        if (data.vehicle_costs && data.vehicle_costs.length > 0) {
            html += `<div class="premium-card" style="padding:20px; margin-bottom:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Top Vehicles by Cost</h4><table class="modern-table" style="width:100%;"><thead><tr><th>Vehicle</th><th>Jobs</th><th>Total Cost (PKR)</th></tr></thead><tbody>`;
            data.vehicle_costs.forEach(v => { html += `<tr><td>${v.device_name}</td><td>${v.jobs}</td><td>${formatPKR(v.total_cost, true)}</td></tr>`; });
            html += '</tbody></table></div>';
        }
        html += `<div style="display:flex; gap:10px;"><button onclick="exportReportCSV('cost')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Export CSV</button></div>`;
        tc.innerHTML = html;

        if (data.monthly_trend && data.monthly_trend.length > 0) {
            const ctx = document.getElementById('rptCostMonthly');
            if (ctx) reportsChartInstances.costMonthly = new Chart(ctx, {
                type: 'bar', data: { labels: data.monthly_trend.map(m => m.month), datasets: [
                    { label: 'Labour', data: data.monthly_trend.map(m => m.labour), backgroundColor: '#3b82f6' },
                    { label: 'Parts', data: data.monthly_trend.map(m => m.parts), backgroundColor: '#10b981' },
                    { label: 'Misc', data: data.monthly_trend.map(m => m.misc), backgroundColor: '#f59e0b' }
                ]}, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } }, scales: { x: { stacked: true }, y: { stacked: true, ticks: { callback: v => 'Rs.' + (v/1000).toFixed(0) + 'k' } } } }
            });
        }
        const pieCtx = document.getElementById('rptCostPie');
        if (pieCtx) reportsChartInstances.costPie = new Chart(pieCtx, {
            type: 'doughnut', data: { labels: ['Labour', 'Parts', 'Misc', 'Maintenance'], datasets: [{ data: [data.total_labour_cost, data.total_parts_cost, data.total_misc_cost, data.total_maintenance_cost], backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'] }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
        });
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading cost reports</div>'; }
}

// ==================== WORKSHOP REPORTS ====================

async function loadWorkshopReports() {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    tc.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const res = await fetch('/api/maintenance/reports/workshop-performance?days=90', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();

        let html = `<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:20px;">
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">TOTAL JOBS</div><div style="font-size:1.3rem; font-weight:800; color:#3b82f6;">${data.total_jobs}</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">COMPLETED</div><div style="font-size:1.3rem; font-weight:800; color:#10b981;">${data.completed}</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">IN PROGRESS</div><div style="font-size:1.3rem; font-weight:800; color:#f59e0b;">${data.in_progress}</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">AVG REPAIR HOURS</div><div style="font-size:1.3rem; font-weight:800; color:#06b6d4;">${data.avg_repair_hours}h</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">TOTAL COST</div><div style="font-size:1.3rem; font-weight:800; color:#8b5cf6;">${formatPKR(data.total_cost, true)}</div></div>
            <div class="premium-card" style="padding:14px; text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">AVG COST/JOB</div><div style="font-size:1.3rem; font-weight:800; color:#ec4899;">${formatPKR(data.avg_cost, true)}</div></div>
        </div>`;
        html += `<div class="premium-card" style="padding:20px; margin-bottom:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Monthly Job Trend</h4><div style="position:relative; height:250px;"><canvas id="rptJobTrend"></canvas></div></div>`;
        if (data.status_counts) {
            html += `<div class="premium-card" style="padding:20px; margin-bottom:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Status Breakdown</h4><div style="display:flex; flex-wrap:wrap; gap:8px;">`;
            Object.entries(data.status_counts).forEach(([s, c]) => {
                if (c > 0) html += `<div style="padding:6px 14px; border-radius:8px; background:var(--brand-primary)11; font-size:0.82rem;"><strong>${c}</strong> ${s.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>`;
            });
            html += '</div></div>';
        }
        html += `<div style="display:flex; gap:10px;"><button onclick="exportReportCSV('workshop')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Export CSV</button></div>`;
        tc.innerHTML = html;

        if (data.monthly_trend && data.monthly_trend.length > 0) {
            const ctx = document.getElementById('rptJobTrend');
            if (ctx) reportsChartInstances.jobTrend = new Chart(ctx, {
                type: 'bar', data: { labels: data.monthly_trend.map(m => m.month), datasets: [{ label: 'Jobs', data: data.monthly_trend.map(m => m.count), backgroundColor: '#3b82f6', borderRadius: 4 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });
        }
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading workshop reports</div>'; }
}

// ==================== TECHNICIAN REPORTS ====================

async function loadTechnicianReports() {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    tc.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const res = await fetch('/api/maintenance/reports/technician-performance', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed');
        const techs = await res.json();
        if (techs.length === 0) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">No Data Available</div>'; return; }

        let html = `<div class="premium-card" style="padding:20px; margin-bottom:20px;">
            <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Technician Performance</h4>
            <table class="modern-table" style="width:100%;"><thead><tr><th>Name</th><th>Employee ID</th><th>Completed</th><th>Active</th><th>Avg Time</th><th>Approval Rate</th><th>Total Cost</th></tr></thead><tbody>`;
        techs.forEach(t => {
            html += `<tr><td><strong>${t.name}</strong></td><td>${t.employee_id}</td><td>${t.completed_jobs}</td><td>${t.active_jobs}</td><td>${t.avg_completion_hours}h</td><td>${t.approval_rate}%</td><td>${formatPKR(t.total_cost, true)}</td></tr>`;
        });
        html += '</tbody></table></div>';
        html += `<div class="premium-card" style="padding:20px; margin-bottom:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Jobs by Technician</h4><div style="position:relative; height:280px;"><canvas id="rptTechJobs"></canvas></div></div>`;
        html += `<div style="display:flex; gap:10px;"><button onclick="exportReportCSV('technicians')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Export CSV</button></div>`;
        tc.innerHTML = html;

        const ctx = document.getElementById('rptTechJobs');
        if (ctx) reportsChartInstances.techJobs = new Chart(ctx, {
            type: 'bar', data: { labels: techs.map(t => t.name), datasets: [{ label: 'Completed', data: techs.map(t => t.completed_jobs), backgroundColor: '#10b981', borderRadius: 4 }, { label: 'Active', data: techs.map(t => t.active_jobs), backgroundColor: '#f59e0b', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true } } }
        });
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading technician reports</div>'; }
}

// ==================== INVENTORY REPORTS ====================

async function loadInventoryReports() {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    tc.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const [invRes, lowRes, catRes] = await Promise.all([
            fetch('/api/maintenance/reports/inventory-analytics', { headers: authHeaders() }),
            fetch('/api/maintenance/reports/low-stock', { headers: authHeaders() }),
            fetch('/api/maintenance/reports/charts/inventory-by-category', { headers: authHeaders() })
        ]);
        const inv = invRes.ok ? await invRes.json() : {};
        const low = lowRes.ok ? await lowRes.json() : [];
        const cat = catRes.ok ? await catRes.json() : { labels: [], values: [] };

        let html = '';
        if (cat.labels.length > 0) {
            html += `<div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px;">
                <div class="premium-card" style="padding:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Inventory Value by Category</h4><div style="position:relative; height:280px;"><canvas id="rptInvCat"></canvas></div></div>
                <div class="premium-card" style="padding:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Most Used Parts</h4><div style="position:relative; height:280px;"><canvas id="rptMostUsed"></canvas></div></div>
            </div>`;
        }
        if (low.length > 0) {
            html += `<div class="premium-card" style="padding:20px; margin-bottom:20px; border-left:4px solid #ef4444;">
                <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Low Stock Items (${low.length})</h4>
                <table class="modern-table" style="width:100%;"><thead><tr><th>Part #</th><th>Name</th><th>Current</th><th>Minimum</th><th>Deficit</th><th>Reorder Cost</th><th>Status</th></tr></thead><tbody>`;
            low.forEach(l => {
                const sc = l.status === 'OUT_OF_STOCK' ? '#ef4444' : '#f59e0b';
                html += `<tr><td>${l.part_number}</td><td>${l.name}</td><td>${l.current_stock}</td><td>${l.minimum_stock}</td><td>${l.deficit}</td><td>${formatPKR(l.reorder_cost, true)}</td><td><span style="color:${sc}; font-weight:600;">${l.status.replace(/_/g, ' ')}</span></td></tr>`;
            });
            html += '</tbody></table></div>';
        }
        html += `<div style="display:flex; gap:10px;"><button onclick="exportReportCSV('inventory')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Export CSV</button></div>`;
        tc.innerHTML = html;

        if (cat.labels.length > 0) {
            const ctx1 = document.getElementById('rptInvCat');
            if (ctx1) {
                const colors = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#f97316','#14b8a6'];
                reportsChartInstances.invCat = new Chart(ctx1, {
                    type: 'pie', data: { labels: cat.labels, datasets: [{ data: cat.values, backgroundColor: colors.slice(0, cat.labels.length) }] },
                    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
                });
            }
        }
        if (inv.most_used_parts && inv.most_used_parts.length > 0) {
            const ctx2 = document.getElementById('rptMostUsed');
            if (ctx2) reportsChartInstances.mostUsed = new Chart(ctx2, {
                type: 'bar', data: { labels: inv.most_used_parts.map(p => p.part_name), datasets: [{ label: 'Usage Count', data: inv.most_used_parts.map(p => p.usage_count), backgroundColor: '#3b82f6', borderRadius: 4 }] },
                options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
            });
        }
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading inventory reports</div>'; }
}

// ==================== VEHICLE REPORTS ====================

async function loadVehicleReports() {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    tc.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const res = await fetch('/api/maintenance/reports/vehicle-downtime?days=90', { headers: authHeaders() });
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();

        if (data.length === 0) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">No Data Available</div>'; return; }

        let html = `<div class="premium-card" style="padding:20px; margin-bottom:20px;">
            <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Vehicle Downtime Report (Last 90 Days)</h4>
            <table class="modern-table" style="width:100%;"><thead><tr><th>Vehicle</th><th>Visits</th><th>Total Hours</th><th>Total Cost (PKR)</th><th>First Visit</th><th>Last Visit</th></tr></thead><tbody>`;
        data.forEach(v => {
            html += `<tr><td><strong>${v.device_name}</strong></td><td>${v.visit_count}</td><td>${v.total_hours}h</td><td>${formatPKR(v.total_cost, true)}</td><td>${v.first_visit ? new Date(v.first_visit).toLocaleDateString() : '-'}</td><td>${v.last_visit ? new Date(v.last_visit).toLocaleDateString() : '-'}</td></tr>`;
        });
        html += '</tbody></table></div>';
        html += `<div class="premium-card" style="padding:20px; margin-bottom:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">Vehicle Downtime Hours</h4><div style="position:relative; height:280px;"><canvas id="rptDownTime"></canvas></div></div>`;
        html += `<div style="display:flex; gap:10px;"><button onclick="exportReportCSV('vehicles')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Export CSV</button></div>`;
        tc.innerHTML = html;

        const ctx = document.getElementById('rptDownTime');
        if (ctx) reportsChartInstances.downTime = new Chart(ctx, {
            type: 'bar', data: { labels: data.map(v => v.device_name), datasets: [{ label: 'Hours', data: data.map(v => v.total_hours), backgroundColor: '#ef4444', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading vehicle reports</div>'; }
}

// ==================== MONTHLY / YEARLY ====================

async function loadMonthlyYearlyReports() {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    tc.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">Loading...</div>';
    try {
        const now = new Date();
        const [monthRes, yearRes] = await Promise.all([
            fetch(`/api/maintenance/reports/monthly?year=${now.getFullYear()}&month=${now.getMonth()+1}`, { headers: authHeaders() }),
            fetch(`/api/maintenance/reports/yearly?year=${now.getFullYear()}`, { headers: authHeaders() })
        ]);
        const month = monthRes.ok ? await monthRes.json() : {};
        const year = yearRes.ok ? await yearRes.json() : {};

        let html = `<div class="premium-card" style="padding:20px; margin-bottom:20px;">
            <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">${month.month_name || ''} ${month.year || now.getFullYear()} Summary</h4>
            <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px;">
                <div style="text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">JOBS CREATED</div><div style="font-size:1.2rem; font-weight:800; color:#3b82f6;">${month.jobs_created || 0}</div></div>
                <div style="text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">JOBS COMPLETED</div><div style="font-size:1.2rem; font-weight:800; color:#10b981;">${month.jobs_completed || 0}</div></div>
                <div style="text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">TOTAL COST</div><div style="font-size:1.2rem; font-weight:800; color:#8b5cf6;">${formatPKR(month.total_cost || 0, true)}</div></div>
                <div style="text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">WORKSHOP COST</div><div style="font-size:1.2rem; font-weight:800; color:#f59e0b;">${formatPKR(month.workshop_cost || 0, true)}</div></div>
                <div style="text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">MAINT. SERVICES</div><div style="font-size:1.2rem; font-weight:800; color:#06b6d4;">${month.maintenance_services || 0}</div></div>
                <div style="text-align:center;"><div style="font-size:0.72rem; color:var(--text-dim);">PARTS CONSUMED</div><div style="font-size:1.2rem; font-weight:800; color:#ec4899;">${month.parts_consumed || 0}</div></div>
            </div>
        </div>`;
        if (year.monthly_data && year.monthly_data.length > 0) {
            html += `<div class="premium-card" style="padding:20px; margin-bottom:20px;">
                <h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">${year.year} Yearly Overview — Total: ${formatPKR(year.total_cost, true)}</h4>
                <table class="modern-table" style="width:100%;"><thead><tr><th>Month</th><th>Jobs</th><th>Cost (PKR)</th></tr></thead><tbody>`;
            year.monthly_data.forEach(m => { html += `<tr><td>${m.month_name}</td><td>${m.jobs}</td><td>${formatPKR(m.cost, true)}</td></tr>`; });
            html += '</tbody></table></div>';
            html += `<div class="premium-card" style="padding:20px; margin-bottom:20px;"><h4 style="font-size:0.9rem; font-weight:700; margin-bottom:12px;">${year.year} Monthly Costs</h4><div style="position:relative; height:280px;"><canvas id="rptYearCost"></canvas></div></div>`;
        }
        html += `<div style="display:flex; gap:10px;"><button onclick="exportReportCSV('monthly')" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Export CSV</button><button onclick="window.print()" class="glass-btn" style="padding:8px 16px; border:none; cursor:pointer; border-radius:8px; font-size:0.82rem;">Print</button></div>`;
        tc.innerHTML = html;

        if (year.monthly_data && year.monthly_data.length > 0) {
            const ctx = document.getElementById('rptYearCost');
            if (ctx) reportsChartInstances.yearCost = new Chart(ctx, {
                type: 'line', data: { labels: year.monthly_data.map(m => m.month_name), datasets: [{ label: 'Cost (PKR)', data: year.monthly_data.map(m => m.cost), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.3 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { ticks: { callback: v => 'Rs.' + (v/1000).toFixed(0) + 'k' } } } }
            });
        }
    } catch (e) { tc.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-dim);">Error loading monthly/yearly reports</div>'; }
}

// ==================== EXPORT ====================

function exportReportCSV(type) {
    const tc = document.getElementById('reports-tab-content');
    if (!tc) return;
    const table = tc.querySelector('table');
    if (!table) { alert('No data table to export'); return; }
    let csv = '';
    table.querySelectorAll('tr').forEach(row => {
        const cols = [];
        row.querySelectorAll('th, td').forEach(cell => { cols.push('"' + cell.textContent.trim().replace(/"/g, '""') + '"'); });
        csv += cols.join(',') + '\n';
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `report_${type}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click(); URL.revokeObjectURL(url);
}
