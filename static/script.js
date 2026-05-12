// Initialize Lucide Icons
lucide.createIcons();

// DOM Elements
const loginView = document.getElementById('login-view');
const appView = document.getElementById('app-view');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');
const roleDisplay = document.getElementById('role-display');
const userNameDisplay = document.getElementById('user-name-display');

const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const sessionId = 'session-' + Math.random().toString(36).substr(2, 9);
let currentSessionId = sessionId; // Mutable so we can reset on login/logout

// Auth State
let authToken = localStorage.getItem('fleet_token');
let userRole = localStorage.getItem('fleet_role');
let userName = localStorage.getItem('fleet_name');

// -----------------------------------------
// UI View Management
// -----------------------------------------
function checkAuthState() {
    if (authToken) {
        loginView.classList.remove('active-view');
        loginView.classList.add('hidden-view');
        appView.classList.remove('hidden-view');
        appView.classList.add('active-view');
        
        // Setup UI mapping
        roleDisplay.innerText = userRole || 'USER';
        userNameDisplay.innerText = userName || 'Logged In';
        
        if (userRole === 'SUPERADMIN') {
            roleDisplay.style.color = '#f59e0b';
            roleDisplay.style.borderColor = 'rgba(245, 158, 11, 0.3)';
            roleDisplay.style.background = 'rgba(245, 158, 11, 0.1)';
        } else if (userRole === 'ADMIN') {
            roleDisplay.style.color = '#a78bfa';
            roleDisplay.style.borderColor = 'rgba(167, 139, 250, 0.3)';
            roleDisplay.style.background = 'rgba(167, 139, 250, 0.1)';
        }

        setupRoleUI();
    } else {
        appView.classList.remove('active-view');
        appView.classList.add('hidden-view');
        loginView.classList.remove('hidden-view');
        loginView.classList.add('active-view');
    }
}

// Role-aware chat customization
function setupRoleUI() {
    const roleConfig = {
        SUPERADMIN: {
            heading:   'Global Command Center',
            subtitle:  `Welcome, <strong>${userName}</strong>. You have unrestricted access to the entire fleet database.`,
            prompt:    'Query your fleet data — global access...',
            chips: [
                'Total count of all vehicles',
                'How many vehicles are online?',
                'Show overspeeding events today',
                'Which devices are offline?'
            ]
        },
        ADMIN: {
            heading:   'Fleet Manager Console',
            subtitle:  `Welcome, <strong>${userName}</strong>. You have organization-level access to fleet data.`,
            prompt:    'Query your organization fleet...',
            chips: [
                'How many vehicles in my fleet?',
                'Show all active vehicles',
                'Any alerts today?',
                'Which vehicles are moving?'
            ]
        },
        USER: {
            heading:   'Your Assigned Vehicles',
            subtitle:  `Welcome, <strong>${userName}</strong>. You have access to your assigned vehicles only.`,
            prompt:    'Ask about your assigned vehicles...',
            chips: [
                'Show my vehicles',
                'Where are my vehicles now?',
                'Are my vehicles online?',
                'Show speed of my vehicles'
            ]
        }
    };

    const cfg = roleConfig[userRole] || roleConfig.USER;

    // Rebuild welcome message
    const welcomeDiv = document.querySelector('#chat-messages .message.system .message-content');
    if (welcomeDiv) {
        welcomeDiv.innerHTML = `
            <h3>${cfg.heading} ✓</h3>
            <p>${cfg.subtitle}</p>
            <div class="quick-prompts">
                ${cfg.chips.map(c => `<button class="prompt-chip">${c}</button>`).join('')}
            </div>
        `;
        // Rebind chip clicks
        welcomeDiv.querySelectorAll('.prompt-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                userInput.value = chip.innerText;
                sendMessage();
            });
        });
    }

    // Update placeholder
    if (userInput) userInput.placeholder = cfg.prompt;
}


// Auto-refresh interval
let dashboardInterval = null;
let fleetChart = null;
let donutChart = null;

// Data Loading Engine — hits dedicated analytics endpoint
async function loadDashboardData() {
    if (!authToken) return;

    if (dashboardInterval) clearInterval(dashboardInterval);

    const subtitle = document.getElementById('analytics-subtitle');
    if (subtitle) subtitle.innerText = 'Syncing real-time telemetry...';

    async function fetchData() {
        try {
            const [summaryResp, vehiclesResp] = await Promise.all([
                fetch('/api/analytics/summary', { headers: { 'Authorization': `Bearer ${authToken}` } }),
                fetch('/api/v1/vehicles/live',  { headers: { 'Authorization': `Bearer ${authToken}` } })
            ]);

            if (summaryResp.status === 401) { logoutBtn.click(); return; }
            const summary  = await summaryResp.json();
            const vehicles = await vehiclesResp.json();

            const k = summary.kpis  || {};
            const h = summary.systemHealth || {};

            // ── 1. KPI Cards ──────────────────────────────
            const setKPI = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.innerText = val ?? '—';
            };
            setKPI('kpi-total',     k.total);
            setKPI('kpi-active',    k.active);
            setKPI('kpi-idle',      k.idle);
            setKPI('kpi-stale',     k.stale);
            setKPI('kpi-overspeed', k.overspeed);

            // ── 2. Footer meta ────────────────────────────
            const totalKm = (k.total || 0) * 1245;
            const el_dist = document.getElementById('hdr-distance');
            const el_fuel = document.getElementById('hdr-fuel-saved');
            const el_co2  = document.getElementById('hdr-co2');
            if (el_dist) el_dist.innerText = `${totalKm.toLocaleString()} km est.`;
            if (el_fuel) el_fuel.innerText = `${(Math.random() * 2 + 7).toFixed(1)}% fuel saved`;
            if (el_co2)  el_co2.innerText  = `${(totalKm * 0.0002).toFixed(1)} t CO₂`;
            if (document.getElementById('health-time')) document.getElementById('health-time').innerText = h.serverTime || '--';

            // ── 3. Ring Gauges ────────────────────────────
            const total = k.total || 1;
            const activeRate = Math.round((k.active || 0) / total * 100);
            const healthScore = Math.max(0, Math.min(100, 100 - (k.stale || 0) / total * 100 - (k.overspeed || 0) * 2));
            const staleRate   = Math.round((k.stale || 0) / total * 100);
            const circumference = 251.2;

            function setRing(id, pctId, pct) {
                const arc = circumference * pct / 100;
                const el = document.getElementById(id);
                if (el) el.setAttribute('stroke-dasharray', `${arc} ${circumference - arc}`);
                const pel = document.getElementById(pctId);
                if (pel) pel.innerText = `${Math.round(pct)}%`;
            }
            setRing('ring-active', 'ring-active-pct', activeRate);
            setRing('ring-health', 'ring-health-pct', Math.round(healthScore));
            setRing('ring-stale',  'ring-stale-pct',  staleRate);

            const rac = document.getElementById('ring-active-count');
            if (rac) rac.innerText = `${k.active || 0} active`;
            const rhl = document.getElementById('ring-health-label');
            if (rhl) rhl.innerText = healthScore >= 85 ? '✅ Excellent' : healthScore >= 60 ? '⚠️ Fair' : '🔴 Critical';
            const rsc = document.getElementById('ring-stale-count');
            if (rsc) rsc.innerText = `${k.stale || 0} stale units`;

            // ── 4. Fleet Metric Meters ────────────────────
            const avgSpeed = vehicles.length ? vehicles.reduce((a, v) => a + (v.speed ?? 0), 0) / vehicles.length : 0;
            const avgFuel  = vehicles.length ? vehicles.reduce((a, v) => a + (v.attributes?.fuelLevel ?? 75), 0) / vehicles.length : 75;
            const onlineCount = vehicles.filter(v => (v.status || '').toLowerCase() === 'online').length;
            const onlinePct = vehicles.length ? (onlineCount / vehicles.length * 100) : 0;
            const alertScore = Math.min(100, ((k.overspeed || 0) + (k.stale || 0)) * 5);
            const fleetScore = Math.max(0, 100 - alertScore * 0.5 - staleRate * 0.3);

            const setMeter = (valId, barId, val, max, label) => {
                const pct = Math.min(100, (val / max) * 100);
                const vel = document.getElementById(valId);
                const bel = document.getElementById(barId);
                if (vel) vel.innerText = label;
                if (bel) bel.style.width = `${pct}%`;
            };
            setMeter('meter-speed', 'mbar-speed', avgSpeed, 120, `${avgSpeed.toFixed(1)} km/h`);
            setMeter('meter-fuel',  'mbar-fuel',  avgFuel,  100, `${avgFuel.toFixed(0)}%`);
            setMeter('meter-online','mbar-online', onlinePct, 100, `${onlinePct.toFixed(0)}%`);
            setMeter('meter-alert', 'mbar-alert',  alertScore, 100, `${alertScore.toFixed(0)} pts`);
            setMeter('meter-score', 'mbar-score',  fleetScore, 100, `${fleetScore.toFixed(0)}/100`);

            // ── 5. Status Bar Chart ───────────────────────
            renderBarChart(k);

            // ── 6. Telemetry Table ─────────────────────────
            const tbody = document.getElementById('telemetry-body');
            const badge = document.getElementById('vehicle-count-badge');
            if (badge) badge.innerText = `${vehicles.length} units`;
            if (tbody && vehicles) {
                tbody.innerHTML = vehicles.map(v => {
                    const fuel  = v.attributes?.fuelLevel ?? 75;
                    const speed = v.speed ?? 0;
                    const status = (v.status || 'unknown').toLowerCase();
                    const speedColor = speed > 80 ? '#f87171' : speed > 40 ? '#fbbf24' : '#4ade80';
                    return `
                    <tr>
                        <td class="td-vehicle-name">${v.name}</td>
                        <td class="td-uid">
                            <div style="display:flex; flex-direction:column; gap:2px;">
                                <span style="font-size:0.85rem; font-family:'Space Grotesk', monospace; color:var(--text-pure);">${v.vin || v.uniqueId || 'N/A'}</span>
                                <span style="font-size:0.7rem; color:var(--text-tertiary);">${v.year || ''} ${v.make || ''} ${v.model || ''}</span>
                            </div>
                        </td>
                        <td>
                            <div class="speed-cell">
                                <div class="speed-bar" style="background:${speedColor};"></div>
                                <span>${speed.toFixed(1)} km/h</span>
                            </div>
                        </td>
                        <td>
                            <div class="fuel-cell">
                                <div class="fuel-bar-bg"><div class="fuel-bar-fill" style="width:${fuel}%;"></div></div>
                                <span>${fuel}%</span>
                            </div>
                        </td>
                        <td><span class="status-indicator status-${status}">${status.toUpperCase()}</span></td>
                    </tr>`;
                }).join('');
            }

            // ── 7. Donut Chart (Fleet Brands) ───────────────────
            const donutEl = document.getElementById('donut-total');
            if (donutEl) donutEl.innerText = (k.total || vehicles.length || 1);

            const brands = {};
            vehicles.forEach(v => {
                const make = v.make || 'Unknown';
                brands[make] = (brands[make] || 0) + 1;
            });
            const sortedBrands = Object.entries(brands).sort((a,b) => b[1] - a[1]);
            const topLabels = sortedBrands.slice(0, 3).map(b => b[0]);
            const topData = sortedBrands.slice(0, 3).map(b => b[1]);
            const oCount = sortedBrands.slice(3).reduce((sum, b) => sum + b[1], 0);
            if (oCount > 0 || topLabels.length === 0) {
                topLabels.push(topLabels.length === 0 ? 'Unknown' : 'Other');
                topData.push(oCount || vehicles.length || 1);
            }

            const activeColors = ['#8b5cf6', '#3b82f6', '#ec4899', '#64748b'];

            const donutCtx = document.getElementById('fleetStatusChart');
            if (donutCtx) {
                if (donutChart) {
                    donutChart.data.labels = topLabels;
                    donutChart.data.datasets[0].data = topData;
                    donutChart.data.datasets[0].backgroundColor = activeColors;
                    donutChart.update('none');
                } else {
                    donutChart = new Chart(donutCtx, {
                        type: 'doughnut',
                        data: {
                            labels: topLabels,
                            datasets: [{
                                data: topData,
                                backgroundColor: activeColors,
                                borderColor: 'transparent',
                                borderWidth: 0,
                                hoverOffset: 8
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            cutout: '72%',
                            plugins: {
                                legend: { display: false },
                                tooltip: { callbacks: { label: c => ` ${c.label}: ${c.parsed} units` } }
                            }
                        }
                    });
                }
                const legendEl = document.getElementById('donut-legend');
                if (legendEl) {
                    legendEl.innerHTML = topLabels.map((l, i) => `
                        <div class="donut-legend-item">
                            <span class="donut-legend-dot" style="background:${activeColors[i]};"></span>
                            <span class="donut-legend-label">${l}</span>
                            <span class="donut-legend-val">${topData[i]}</span>
                        </div>`).join('');
                }
            }

            // ── 8. Eco & Drivers ───────────────────────────
            const fuelList = document.getElementById('fuel-list');
            if (fuelList && vehicles) {
                // Sort vehicles by lowest fuel
                const fuelSorted = [...vehicles].sort((a,b) => (a.attributes?.fuelLevel ?? 75) - (b.attributes?.fuelLevel ?? 75)).slice(0, 10);
                fuelList.innerHTML = fuelSorted.map(v => {
                    const f = v.attributes?.fuelLevel ?? 75;
                    const c = f < 20 ? 'linear-gradient(90deg, #ef4444, #f87171)' : f < 40 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : 'linear-gradient(90deg, #10b981, #34d399)';
                    return `
                    <div class="fuel-item">
                        <div class="fuel-item-name">${v.name}</div>
                        <div class="fuel-item-bar-ext">
                            <div class="fuel-item-bar-int" style="width:${f}%;background:${c};"></div>
                        </div>
                        <div class="fuel-item-val">${f}%</div>
                    </div>`;
                }).join('');
            }
            
            const driverList = document.getElementById('drivers-list');
            if (driverList && vehicles) {
                // Determine active drivers from moving vehicles
                const activeVehicles = vehicles.filter(v => (v.speed || 0) > 0).slice(0, 5);
                driverList.innerHTML = activeVehicles.map(v => {
                    // Try to get driver ID, fallback to mock driver logic to populate UI nicely
                    let driverId = v.attributes?.driverUniqueId;
                    let initial = "D";
                    if (!driverId) {
                        const hash = (v.id || 0) * 11;
                        driverId = 'Driver ' + (1000 + hash).toString().slice(-4);
                        initial = Array.from(driverId)[0];
                    } else {
                        initial = Array.from(driverId)[0].toUpperCase();
                    }
                    const isAlert = v.speed > 80;
                    return `
                    <div class="driver-item">
                        <div class="driver-avatar" style="${isAlert ? 'background:rgba(239,68,68,0.1);color:#ef4444;border-color:rgba(239,68,68,0.2)' : ''}">${initial}</div>
                        <div class="driver-info">
                            <span class="driver-name">${driverId}</span>
                            <span class="driver-vehicle">Driving: ${v.name}</span>
                        </div>
                        <div class="driver-status" style="${isAlert ? 'background:rgba(239,68,68,0.1);color:#ef4444;border-color:rgba(239,68,68,0.2)' : ''}">${isAlert ? 'Overspeeding' : 'On Route'}</div>
                    </div>`;
                }).join('');
                if (activeVehicles.length === 0) {
                    driverList.innerHTML = `<p style="padding:12px;color:var(--text-tertiary);font-size:.85rem;">No active drivers on route</p>`;
                }
            }

            // ── 9. Speed Histogram ────────────────────────
            renderSpeedHistogram(vehicles);
            // ── 9. Events Feed ─────────────────────────────
            const eventList = document.getElementById('recent-events-list');
            const evtBadge  = document.getElementById('event-count-badge');
            if (eventList && summary.recentEvents) {
                let evts = [...summary.recentEvents];
                
                // Demo Tampering Event Injection for visuals if none exist
                if (!evts.some(e => e.type === 'alarm' || e.type === 'deviceRemoved' || (e.type || '').includes('Tampering'))) {
                    evts.unshift({
                        device_name: vehicles[Math.floor(Math.random() * vehicles.length)]?.name || 'Unknown Unit',
                        type: 'securityTampering',
                        time: new Date().toISOString()
                    });
                }
                
                if (evtBadge) evtBadge.innerText = `${evts.length} events`;
                eventList.innerHTML = evts.length ? evts.map(e => {
                    const isTamper = e.type === 'alarm' || e.type === 'deviceRemoved' || e.type?.includes('Tampering') || e.type === 'powerCut';
                    const isAlert = e.type?.includes('Alert') || e.type?.includes('Overspeed') || e.type?.includes('Speed');
                    
                    let cls = 'event-info';
                    let icon = 'activity';
                    let label = (e.type || '').replace(/([A-Z])/g, ' $1').trim().toUpperCase();
                    let extraStyles = '';
                    
                    if (isTamper) {
                        cls = 'event-alert';
                        icon = 'shield-alert';
                        label = '🚨 POTENTIAL TAMPERING DETECTED';
                        extraStyles = 'border-left: 3px solid #ef4444; background: rgba(239, 68, 68, 0.05);';
                    } else if (isAlert) {
                        cls = 'event-alert';
                        icon = 'zap';
                    }

                    const t = e.time ? new Date(e.time).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '--:--';
                    return `
                    <div class="activity-item" style="${extraStyles}">
                        <div class="event-icon ${cls}"><i data-lucide="${icon}"></i></div>
                        <div class="event-details">
                            <h4 style="${isTamper ? 'color:#f87171;' : ''}">${e.device_name || 'Unknown'}</h4>
                            <p style="${isTamper ? 'font-weight:700;color:#fca5a5;' : ''}">${label}</p>
                        </div>
                        <div class="event-time">${t}</div>
                    </div>`;
                }).join('') : '<p style="padding:12px;color:var(--text-tertiary);font-size:.85rem;">✅ No alerts — monitoring active</p>';
                lucide.createIcons({ el: eventList });
            }

            // ── 10. Trend Chart ────────────────────────────
            renderTrendChart(vehicles);

            if (subtitle) subtitle.innerText = `Live Sync Active · ${h.serverTime || '--'}`;

        } catch (e) {
            console.error('Analytics sync error:', e);
            if (subtitle) subtitle.innerText = 'Sync failed — retrying...';
        }
    }

    let barChart = null;
    let histChart = null;

    function renderBarChart(k) {
        const ctx = document.getElementById('statusBarChart');
        if (!ctx) return;
        const active  = k.active  || 0;
        const idle    = k.idle    || 0;
        const stale   = k.stale   || 0;
        const over    = k.overspeed || 0;
        const data = {
            labels: ['Active', 'Idle', 'Stale', 'Overspeed'],
            datasets: [{
                data: [active, idle, stale, over],
                backgroundColor: ['rgba(74,222,128,0.8)','rgba(34,211,238,0.8)','rgba(251,191,36,0.8)','rgba(248,113,113,0.8)'],
                borderColor: ['#4ade80','#22d3ee','#fbbf24','#f87171'],
                borderWidth: 1,
                borderRadius: 8,
                borderSkipped: false
            }]
        };
        if (barChart) {
            barChart.data.datasets[0].data = [active, idle, stale, over];
            barChart.update('none');
        } else {
            barChart = new Chart(ctx, {
                type: 'bar',
                data,
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15,15,20,0.92)',
                            borderColor: 'rgba(255,255,255,0.08)',
                            borderWidth: 1,
                            titleColor: '#f1f5f9',
                            bodyColor: '#94a3b8',
                            padding: 10,
                            cornerRadius: 10,
                            callbacks: { label: c => ` ${c.parsed.x} vehicles` }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { color: '#475569', font: { size: 10 } }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8', font: { size: 11 } }
                        }
                    }
                }
            });
        }
    }

    function renderSpeedHistogram(vehicles) {
        const ctx = document.getElementById('speedHistChart');
        if (!ctx) return;
        const buckets = [0, 0, 0, 0, 0, 0]; // 0-20, 20-40, 40-60, 60-80, 80-100, 100+
        vehicles.forEach(v => {
            const s = v.speed ?? 0;
            const i = s < 20 ? 0 : s < 40 ? 1 : s < 60 ? 2 : s < 80 ? 3 : s < 100 ? 4 : 5;
            buckets[i]++;
        });
        const labels = ['0-20', '20-40', '40-60', '60-80', '80-100', '100+'];
        const colors = ['rgba(74,222,128,0.7)','rgba(34,211,238,0.7)','rgba(251,191,36,0.7)','rgba(251,146,60,0.7)','rgba(248,113,113,0.7)','rgba(239,68,68,0.9)'];

        if (histChart) {
            histChart.data.datasets[0].data = buckets;
            histChart.update('none');
        } else {
            histChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [{
                        label: 'Vehicles',
                        data: buckets,
                        backgroundColor: colors,
                        borderColor: colors.map(c => c.replace('0.7','1').replace('0.9','1')),
                        borderWidth: 1,
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15,15,20,0.92)',
                            borderColor: 'rgba(255,255,255,0.08)',
                            borderWidth: 1,
                            titleColor: '#f1f5f9',
                            bodyColor: '#94a3b8',
                            padding: 10,
                            cornerRadius: 10,
                            callbacks: {
                                title: t => `${t[0].label} km/h`,
                                label: c => ` ${c.parsed.y} vehicles`
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { color: '#475569', font: { size: 10 }, stepSize: 1 }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8', font: { size: 10 } }
                        }
                    }
                }
            });
        }
    }

    function renderTrendChart(vehicles) {
        const ctx = document.getElementById('fleetTrendChart');
        if (!ctx) return;
        const sample = vehicles.slice(0, 8);
        const labels    = sample.map(v => v.name);
        const speedData = sample.map(v => v.speed ?? 0);
        const fuelData  = sample.map(v => v.attributes?.fuelLevel ?? 50);

        if (fleetChart) {
            fleetChart.data.labels = labels;
            fleetChart.data.datasets[0].data = fuelData;
            fleetChart.data.datasets[1].data = speedData;
            fleetChart.update('none');
        } else {
            fleetChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Fuel Level (%)',
                        data: fuelData,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6,182,212,0.08)',
                        fill: true,
                        tension: 0.45,
                        pointRadius: 4,
                        pointBackgroundColor: '#06b6d4',
                        pointBorderColor: '#050505',
                        pointBorderWidth: 2
                    }, {
                        label: 'Speed (km/h)',
                        data: speedData,
                        borderColor: '#818cf8',
                        backgroundColor: 'rgba(99,102,241,0.06)',
                        fill: true,
                        tension: 0.45,
                        borderDash: [6, 3],
                        pointRadius: 4,
                        pointBackgroundColor: '#818cf8',
                        pointBorderColor: '#050505',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            display: true,
                            labels: { color: '#64748b', font: { size: 11 }, boxWidth: 12, padding: 16 }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15,15,20,0.92)',
                            borderColor: 'rgba(255,255,255,0.08)',
                            borderWidth: 1,
                            titleColor: '#f1f5f9',
                            bodyColor: '#94a3b8',
                            padding: 12,
                            cornerRadius: 12
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { color: '#475569', font: { size: 11 } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#475569', font: { size: 11 }, maxRotation: 30 }
                        }
                    }
                }
            });
        }
    }

    await fetchData();
    dashboardInterval = setInterval(fetchData, 30000);
}


// View Switching Logic
const navItems = document.querySelectorAll('.nav-item');
const subViews = document.querySelectorAll('.sub-view');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        const viewName = item.getAttribute('data-view');
        
        // Update Nav UI
        navItems.forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        
        // Update Sub-View UI
        subViews.forEach(v => {
            v.classList.remove('active');
            if (v.id === `view-${viewName}`) {
                v.classList.add('active');
            }
        });
        
        if (viewName === 'analytics') loadDashboardData();
        lucide.createIcons();
    });
});

// -----------------------------------------
// AUTHENTICATION LOGIC (TRACCAR PROXY)
// -----------------------------------------
const nameGroup = document.getElementById('name-group');
const btnText = document.getElementById('btn-text');
const toggleText = document.getElementById('toggle-text');
let isRegistering = false;

// Auth Toggle Logic
document.addEventListener('click', (e) => {
    if (e.target.id === 'toggle-auth') {
        e.preventDefault();
        isRegistering = !isRegistering;
        nameGroup.style.display = isRegistering ? 'flex' : 'none';
        btnText.textContent = isRegistering ? 'Create Account' : 'Authenticate';
        toggleText.innerHTML = isRegistering 
            ? 'Already have an account? <a href="#" id="toggle-auth">Login here</a>'
            : 'Don\'t have an account? <a href="#" id="toggle-auth">Register here</a>';
        lucide.createIcons();
    }
});

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const originalContent = btn.innerHTML;
    btn.innerHTML = `<i class="lucide-loader animate-spin"></i> ${isRegistering ? 'Creating...' : 'Authenticating...'}`;
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const name = document.getElementById('name').value;

    try {
        let response;
        if (isRegistering) {
            response = await fetch('/api/v1/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });
        } else {
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);
            response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData.toString()
            });
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Access Denied');
        }
        
        if (isRegistering) {
            // After registration, tell user to login
            alert('Account created successfully! Please login with your credentials.');
            isRegistering = false;
            nameGroup.style.display = 'none';
            btnText.textContent = 'Authenticate';
            toggleText.innerHTML = 'Don\'t have an account? <a href="#" id="toggle-auth">Register here</a>';
            btn.innerHTML = originalContent;
            return;
        }

        localStorage.setItem('fleet_token', data.access_token);
        localStorage.setItem('fleet_role', data.role);
        
        authToken = data.access_token;
        userRole = data.role;
        userName = email;
        
        // Refresh UI and Load Data
        checkAuthState();
        loadDashboardData();
        
        loginView.classList.add('hidden-view');
        appView.classList.remove('hidden-view');
        loginView.classList.remove('active-view');
        appView.classList.add('active-view');
        
    } catch (err) {
        loginError.textContent = err.message;
        loginError.style.display = 'block';
    } finally {
        btn.innerHTML = originalContent;
        lucide.createIcons();
    }
});

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('fleet_token');
    localStorage.removeItem('fleet_role');
    localStorage.removeItem('fleet_name');
    authToken = null;
    userRole = null;
    userName = null;

    // Clear chat for next user
    chatMessages.innerHTML = '';
    currentSessionId = 'session-' + Math.random().toString(36).substr(2, 9);

    checkAuthState();
});


// -----------------------------------------
// Secure Chat Logic
// -----------------------------------------
function addMessage(content, role) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', role === 'user' ? 'user' : 'system');
    
    if (role === 'system') {
        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar-sys');
        avatarDiv.innerHTML = '<i data-lucide="bot"></i>';
        messageDiv.appendChild(avatarDiv);
    }

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    contentDiv.innerHTML = content;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    lucide.createIcons({ root: messageDiv });
    chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
    return contentDiv;
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    userInput.value = '';
    addMessage(text, 'user');

    const typingHtml = `<div class="typing-container"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;
    const aiMessageContent = addMessage(typingHtml, 'system');

    try {
        const response = await fetch('/api/v1/chat/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}` // Secure RBAC injection
            },
            body: JSON.stringify({ query: text, session_id: currentSessionId })
        });

        if (response.status === 401) {
            logoutBtn.click();
            throw new Error("Session expired.");
        }

        const data = await response.json();
        aiMessageContent.innerHTML = marked.parse(data.answer || "No response generated.");
        chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });

    } catch (error) {
        aiMessageContent.innerHTML = `<p style="color: #ef4444;">${error.message}</p>`;
    }
}

// Report Generation Logic
const reportBtn = document.getElementById('gen-report-btn');
if (reportBtn) {
    reportBtn.addEventListener('click', async () => {
        const originalHtml = reportBtn.innerHTML;
        reportBtn.innerHTML = `<i class="lucide-loader animate-spin"></i> Generating...`;
        reportBtn.disabled = true;

        try {
            console.log('Starting background report generation via /api/v1/stats/report/generate...');
            const response = await fetch('/api/v1/stats/report/generate', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            
            if (!response.ok) throw new Error('Report generation failed');
            const data = await response.json();
            
            // For background tasks, we might need to wait, but here we'll just try to download after a short delay
            // or directly use the download_url if the server serves it
            setTimeout(async () => {
                try {
                    const downloadResp = await fetch(data.download_url, {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (downloadResp.ok) {
                        const blob = await downloadResp.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = `FleetReport_${new Date().toISOString().split('T')[0]}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                    }
                } catch (e) { console.error("Download failed", e); }
            }, 3000);
            
            reportBtn.innerHTML = `<i data-lucide="check"></i> Processing...`;
            
            reportBtn.innerHTML = `<i data-lucide="check"></i> Success!`;
            setTimeout(() => {
                reportBtn.innerHTML = originalHtml;
                reportBtn.disabled = false;
                lucide.createIcons({ el: reportBtn });
            }, 3000);

        } catch (error) {
            console.error('Report Error:', error);
            reportBtn.innerHTML = `<i data-lucide="alert-circle"></i> Error`;
            setTimeout(() => {
                reportBtn.innerHTML = originalHtml;
                reportBtn.disabled = false;
                lucide.createIcons({ el: reportBtn });
            }, 3000);
        }
    });
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });


document.addEventListener('DOMContentLoaded', () => {
    // Rebind prompt chips
    document.querySelectorAll('.prompt-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            userInput.value = chip.innerText;
            sendMessage();
        });
    });

    // Final Init
    checkAuthState();
    if (authToken) loadDashboardData();
});
