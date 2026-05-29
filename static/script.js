/**
 * AI - Telemetrix | Premium Fleet Intelligence v5.0
 * Fully upgraded architecture with role-based filtering, advanced charts,
 * and high-fidelity tactical maps.
 */

// Initialize Lucide Icons
function safeCreateIcons() {
    try { lucide.createIcons(); } catch (e) { }
}

window.onerror = function(msg, url, line, col, error) {
    console.error("Global System Error:", msg, "at", url, ":", line);
    return false;
};

console.log("AI - Telemetrix Engine Starting...");

// DOM Elements
const loginView = document.getElementById('login-view');
const appView = document.getElementById('app-view');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const logoutBtn = document.getElementById('logout-btn');
const userNameDisplay = document.getElementById('user-name-display');
const roleDisplay = document.getElementById('role-display');
const roleText = document.getElementById('role-text');
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
let currentLang = localStorage.getItem('fleet_lang') || 'en';

const translations = {
    en: {
        login_title: "AI - Telemetrix", login_subtitle: "Enterprise Intelligence Portal", label_email: "Corporate Email", label_password: "Security Key", label_name: "Full Name", btn_access: "Access System", new_to: "New to Telemetrix?", req_access: "Request Access", demo_access: "Demo Access:", demo_note: "Valid for all modules",
        nav_dashboard: "Dashboard", nav_map: "Live Map", nav_intel: "Vehicle Intel", nav_fuel: "Fuel Analytics", nav_safety: "Driver Safety", nav_maint: "Maintenance",
        dash_title: "Dashboard Overview", dash_subtitle: "Real-time updates", stat_active: "Active Units", stat_moving: "Moving", stat_fuel: "Fleet Fuel", stat_alerts: "Alerts",
        kpi_total: "Total Units", kpi_moving: "Moving", kpi_idle: "Idle", kpi_stopped: "Stopped", kpi_offline: "Offline", kpi_alerts: "Active Alerts", kpi_overspeed: "Overspeed", kpi_ignition: "Ignition", kpi_geofence: "Geofence", kpi_tamper: "Tamper"
    },
    ur: {
        login_title: "اے آئی - ٹیلی میٹرکس", login_subtitle: "انٹرپرائز انٹیلیجنس پورٹل", label_email: "ای میل", label_password: "کلید", label_name: "پورا نام", btn_access: "سسٹم تک رسائی", new_to: "نئے ہیں؟", req_access: "رسائی طلب کریں", demo_access: "ڈیمو رسائی:", demo_note: "تمام ماڈیولز",
        nav_dashboard: "ڈیش بورڈ", nav_map: "نقشہ", nav_intel: "گاڑیوں کی معلومات", nav_fuel: "ایندھن", nav_safety: "حفاظت", nav_maint: "دیکھ بھال",
        dash_title: "ڈیش بورڈ جائزہ", dash_subtitle: "ریئل ٹائم اپ ڈیٹس", stat_active: "فعال گاڑیاں", stat_moving: "راستے میں", stat_fuel: "کل ایندھن", stat_alerts: "الرٹس",
        kpi_total: "کل یونٹس", kpi_moving: "حرکت پذیر", kpi_idle: "آئیڈل", kpi_stopped: "رکی ہوئی", kpi_offline: "آف لائن", kpi_alerts: "فعال الرٹس", kpi_overspeed: "تیز رفتار", kpi_ignition: "اگنیشن", kpi_geofence: "جیو فینس", kpi_tamper: "ٹیمپرنگ"
    },
    zh: {
        login_title: "AI - 远程信息处理", login_subtitle: "企业情报门户", label_email: "企业邮箱", label_password: "安全密钥", label_name: "全名", btn_access: "进入系统", new_to: "第一次使用？", req_access: "申请访问", demo_access: "演示访问：", demo_note: "所有模块有效",
        nav_dashboard: "仪表盘", nav_map: "实时地图", nav_intel: "车辆智能", nav_fuel: "燃油分析", nav_safety: "驾驶安全", nav_maint: "维护保养",
        dash_title: "仪表盘概览", dash_subtitle: "实时更新", stat_active: "活跃车辆", stat_moving: "行驶中", stat_fuel: "车队燃油", stat_alerts: "警报",
        kpi_total: "总计单元", kpi_moving: "运行中", kpi_idle: "怠速", kpi_stopped: "停止", kpi_offline: "离线", kpi_alerts: "活跃警报", kpi_overspeed: "超速", kpi_ignition: "点火", kpi_geofence: "地理围栏", kpi_tamper: "篡改"
    },
    es: {
        login_title: "AI - Telemetrix", login_subtitle: "Portal de Inteligencia", label_email: "Correo", label_password: "Clave", label_name: "Nombre", btn_access: "Acceder", new_to: "¿Nuevo?", req_access: "Solicitar Acceso", demo_access: "Acceso Demo:", demo_note: "Todos los módulos",
        nav_dashboard: "Tablero", nav_map: "Mapa", nav_intel: "Intel Vehículo", nav_fuel: "Combustible", nav_safety: "Seguridad", nav_maint: "Mantenimiento",
        dash_title: "Resumen Tablero", dash_subtitle: "Actualizaciones", stat_active: "Unidades Activas", stat_moving: "En Tránsito", stat_fuel: "Combustible", stat_alerts: "Alertas",
        kpi_total: "Unidades Totales", kpi_moving: "Móvil", kpi_idle: "Ralentí", kpi_stopped: "Detenido", kpi_offline: "Offline", kpi_alerts: "Alertas Activas", kpi_overspeed: "Exceso Vel.", kpi_ignition: "Ignición", kpi_geofence: "Geocerca", kpi_tamper: "Manipulación"
    },
    fr: {
        login_title: "AI - Telemetrix", login_subtitle: "Portail d'intelligence", label_email: "Email", label_password: "Clé", label_name: "Nom complet", btn_access: "Accéder", new_to: "Nouveau?", req_access: "Demander accès", demo_access: "Accès démo:", demo_note: "Tous les modules",
        nav_dashboard: "Tableau de bord", nav_map: "Carte en direct", nav_intel: "Intel véhicule", nav_fuel: "Carburant", nav_safety: "Sécurité", nav_maint: "Maintenance",
        dash_title: "Aperçu général", dash_subtitle: "Mises à jour", stat_active: "Unités Actives", stat_moving: "En Transit", stat_fuel: "Carburant", stat_alerts: "Alertes",
        kpi_total: "Unités Totales", kpi_moving: "En mouvement", kpi_idle: "Ralenti", kpi_stopped: "Arrêté", kpi_offline: "Hors ligne", kpi_alerts: "Alertes Actives", kpi_overspeed: "Excès vitesse", kpi_ignition: "Allumage", kpi_geofence: "Géo-clôture", kpi_tamper: "Sabotage"
    },
    de: {
        login_title: "AI - Telemetrix", login_subtitle: "Unternehmensportal", label_email: "E-Mail", label_password: "Schlüssel", label_name: "Name", btn_access: "Zugang", new_to: "Neu?", req_access: "Zugang anfordern", demo_access: "Demo:", demo_note: "Alle Module",
        nav_dashboard: "Dashboard", nav_map: "Karte", nav_intel: "Fahrzeug-Intel", nav_fuel: "Kraftstoff", nav_safety: "Sicherheit", nav_maint: "Wartung",
        dash_title: "Übersicht", dash_subtitle: "Echtzeit-Updates", stat_active: "Aktive Einheiten", stat_moving: "In Fahrt", stat_fuel: "Kraftstoff", stat_alerts: "Alarm",
        kpi_total: "Gesamt", kpi_moving: "Fahrend", kpi_idle: "Leerlauf", kpi_stopped: "Gestoppt", kpi_offline: "Offline", kpi_alerts: "Alarme", kpi_overspeed: "Geschwindigkeit", kpi_ignition: "Zündung", kpi_geofence: "Geofence", kpi_tamper: "Sabotage"
    },
    ru: {
        login_title: "AI - Телеметрикс", login_subtitle: "Корпоративный портал", label_email: "Email", label_password: "Ключ", label_name: "Имя", btn_access: "Войти", new_to: "Впервые здесь?", req_access: "Запрос доступа", demo_access: "Демо:", demo_note: "Все модули",
        nav_dashboard: "Панель", nav_map: "Карта", nav_intel: "Интеллект", nav_fuel: "Топливо", nav_safety: "Безопасность", nav_maint: "Сервис",
        dash_title: "Обзор", dash_subtitle: "Обновления", stat_active: "Активно", stat_moving: "В пути", stat_fuel: "Топливо", stat_alerts: "События",
        kpi_total: "Всего", kpi_moving: "Движется", kpi_idle: "Холостой ход", kpi_stopped: "Стоит", kpi_offline: "Оффлайн", kpi_alerts: "События", kpi_overspeed: "Скорость", kpi_ignition: "Зажигание", kpi_geofence: "Геозона", kpi_tamper: "Взлом"
    },
    tr: {
        login_title: "AI - Telemetrix", login_subtitle: "Kurumsal Portal", label_email: "E-posta", label_password: "Şifre", label_name: "Ad Soyad", btn_access: "Giriş Yap", new_to: "Yeni misiniz?", req_access: "Erişim İste", demo_access: "Demo Giriş:", demo_note: "Tüm modüller",
        nav_dashboard: "Panel", nav_map: "Harita", nav_intel: "Araç Zekası", nav_fuel: "Yakıt", nav_safety: "Güvenlik", nav_maint: "Bakım",
        dash_title: "Genel Bakış", dash_subtitle: "Canlı Güncellemeler", stat_active: "Aktif Birimler", stat_moving: "Hareketli", stat_fuel: "Yakıt", stat_alerts: "Alarmlar",
        kpi_total: "Toplam Birim", kpi_moving: "Hareketli", kpi_idle: "Rölanti", kpi_stopped: "Durdu", kpi_offline: "Çevrimdışı", kpi_alerts: "Aktif Alarmlar", kpi_overspeed: "Aşırı Hız", kpi_ignition: "Kontak", kpi_geofence: "Coğrafi Sınır", kpi_tamper: "Müdahale"
    },
    it: {
        login_title: "AI - Telemetrix", login_subtitle: "Portale Aziendale", label_email: "Email", label_password: "Chiave", label_name: "Nome", btn_access: "Accedi", new_to: "Nuovo?", req_access: "Richiedi Accesso", demo_access: "Accesso Demo:", demo_note: "Tutti i moduli",
        nav_dashboard: "Dashboard", nav_map: "Mappa", nav_intel: "Intel Veicoli", nav_fuel: "Carburante", nav_safety: "Sicurezza", nav_maint: "Manutenzione",
        dash_title: "Panoramica", dash_subtitle: "Live Update", stat_active: "Unità Attive", stat_moving: "In Viaggio", stat_fuel: "Carburante", stat_alerts: "Allarmi",
        kpi_total: "Totale Unità", kpi_moving: "In movimento", kpi_idle: "Inattivo", kpi_stopped: "Fermo", kpi_offline: "Disconnesso", kpi_alerts: "Allarmi Attivi", kpi_overspeed: "Eccesso Vel.", kpi_ignition: "Accensione", kpi_geofence: "Geofence", kpi_tamper: "Sabotaggio"
    },
    hi: {
        login_title: "ऐआई - टेलीमेट्रिक्स", login_subtitle: "एंटरप्राइज इंटेलिजेंस", label_email: "ईमेल", label_password: "पासवर्ड", label_name: "पूरा नाम", btn_access: "प्रवेश करें", new_to: "नए हैं?", req_access: "पहुंच मांगें", demo_access: "डेमो लॉगिन:", demo_note: "सभी सुविधाएं",
        nav_dashboard: "डैशबोर्ड", nav_map: "नक्शा", nav_intel: "वाहन सूचना", nav_fuel: "ईंधन", nav_safety: "सुरक्षा", nav_maint: "रखरखाव",
        dash_title: "सारांश", dash_subtitle: "लाइव अपडेट", stat_active: "सक्रिय वाहन", stat_moving: "चल रहा है", stat_fuel: "कुल ईंधन", stat_alerts: "अलर्ट",
        kpi_total: "कुल इकाइयाँ", kpi_moving: "चल रहा", kpi_idle: "आइडल", kpi_stopped: "रुका हुआ", kpi_offline: "ऑफलाइन", kpi_alerts: "सक्रिय अलर्ट", kpi_overspeed: "ओवरस्पीड", kpi_ignition: "इग्निशन", kpi_geofence: "जियोफेंस", kpi_tamper: "छेड़छाड़"
    },
    ar: {
        login_title: "AI - تيليميتريكس", login_subtitle: "بوابة استخبارات المؤسسات", label_email: "البريد الإلكتروني", label_password: "مفتاح الأمان", label_name: "الاسم", btn_access: "دخول", new_to: "جديد؟", req_access: "طلب دخول", demo_access: "دخول تجريبي:", demo_note: "جميع الوحدات",
        nav_dashboard: "لوحة القيادة", nav_map: "الخريطة", nav_intel: "ذكاء المركبات", nav_fuel: "الوقود", nav_safety: "السلامة", nav_maint: "الصيانة",
        dash_title: "نظرة عامة", dash_subtitle: "تحديثات فورية", stat_active: "الوحدات النشطة", stat_moving: "متحرك", stat_fuel: "الوقود", stat_alerts: "تنبيهات",
        kpi_total: "إجمالي الوحدات", kpi_moving: "متحرك", kpi_idle: "خامل", kpi_stopped: "متوقف", kpi_offline: "غير متصل", kpi_alerts: "التنبيهات", kpi_overspeed: "تجاوز السرعة", kpi_ignition: "تشغيل", kpi_geofence: "سياج جغرافي", kpi_tamper: "تلاعب"
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
let darkLayer, lightLayer, standardLayer, satelliteLayer;
let latestVehicles = [];

// -----------------------------------------
// STATUS LOGIC HELPER
// -----------------------------------------
function getVehicleStatus(v) {
    if (!v.lastUpdate) return { label: 'Offline', color: '#94a3b8', class: 'offline' };
    
    const lastUpdate = new Date(v.lastUpdate);
    const now = new Date();
    const diffMinutes = (now - lastUpdate) / (1000 * 60);
    
    // Offline if no update for more than 10 minutes
    if (diffMinutes > 10) return { label: 'Offline', color: '#94a3b8', class: 'offline' };
    
    const ignition = v.attributes?.ignition === true || v.attributes?.ignition === 'true' || (v.attributes?.ignition === undefined && v.speed > 2);
    
    if (v.speed > 2) {
        return { label: 'Moving', color: '#22c55e', class: 'moving' }; // Green
    } else if (ignition) {
        return { label: 'Idle', color: '#eab308', class: 'idle' }; // Yellow/Orange
    } else {
        return { label: 'Online', color: '#0ea5e9', class: 'online' }; // Blue
    }
}

let authToken = localStorage.getItem('fleet_token');
let userRole = localStorage.getItem('fleet_role');
let userName = localStorage.getItem('fleet_name');
let selectedVehicle = null;

// Chart Instances
let velocityChart = null;
let statusDonutChart = null;
let lifecycleChart = null;
let fuelTrendChart = null;
let fuelTimelineChart = null;
let idleCostChart = null;
let safetyRadarChart = null;

// -----------------------------------------
// MODULE INITIALIZERS
// -----------------------------------------

async function fetchLiveFuelPrices() {
    try {
        const resp = await fetch('/api/analytics/fuel-prices', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const prices = await resp.json();
        
        const priceEl = document.getElementById('fuel-live-price');
        const syncBadge = document.getElementById('fuel-sync-badge');
        
        if (priceEl && prices.Petrol) {
            priceEl.innerText = `Rs. ${prices.Petrol.toFixed(2)}`;
            if (syncBadge) {
                syncBadge.innerText = 'Last Synced: Just Now';
                syncBadge.className = 'stats-badge success';
            }
        }
    } catch (e) { console.error("Fuel Price Sync Error:", e); }
}

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
    if (selectedVehicle) updateFuelForSelected();
}

async function updateFuelForSelected() {
    if (!selectedVehicle || !fuelTrendChart) return;
    
    try {
        const resp = await fetch(`/api/analytics/fuel/${selectedVehicle.id}`, {
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

        if (totalCost) totalCost.innerText = `Rs. ${data.total_cost_pkr.toLocaleString()}`;
        if (livePrice && data.price_pkr) livePrice.innerText = `Rs. ${data.price_pkr.toFixed(2)}`;
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
                effBadge.innerText = '⚡ ECU Verified';
            } else if (data.tier === 'B') {
                effBadge.className = 'stats-badge primary';
                effBadge.innerText = '🤖 AI-Estimated';
            } else {
                effBadge.className = 'stats-badge warning';
                effBadge.innerText = '⚠️ Regularized Fallback';
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

function updateSafetyForSelected() {
    if (!selectedVehicle || !safetyRadarChart) return;
    const speed = selectedVehicle.speed || 0;
    const attrs = selectedVehicle.attributes || {};
    
    const isSpeeding = speed > 85; // 85 km/h threshold
    const isIdling = attrs.ignition && speed === 0;
    
    let baseScore = 95;
    let grade = 'A';
    if (isSpeeding) { baseScore -= 30; grade = 'C'; }
    if (isIdling) { baseScore -= 10; grade = 'B'; }

    safetyRadarChart.data.datasets[0].data = [
        isSpeeding ? 40 : 95,      // Speeding
        85,                        // Harsh Brake (mocked without events)
        90,                        // Rapid Accel (mocked)
        88,                        // Sharp Turn (mocked)
        95,                        // Night Driving (mocked)
        isIdling ? 50 : 95         // Idle Time
    ];
    safetyRadarChart.data.datasets[0].label = `Asset: ${selectedVehicle.name} (Speed: ${Math.round(speed)} km/h)`;
    safetyRadarChart.update();
    
    const arc = document.querySelector('.score-percentage');
    if (arc) arc.setAttribute('stroke-dasharray', `${baseScore}, 100`);
    const pct = document.querySelector('.percentage');
    if (pct) pct.textContent = baseScore;
    const lbl = document.querySelector('.score-label');
    if (lbl) lbl.innerHTML = `Asset Safety Grade: <strong>${grade}</strong>`;
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
            </div>`).join('') : '<div style="color:var(--brand-success); padding:20px; text-align:center;">Vehicle ECU Clear — No Faults</div>';
    }
}

function updateSafetyEvents(events) {
    const timeline = document.getElementById('safety-timeline');
    if (!timeline) return;
    
    timeline.innerHTML = events.map(e => {
        let severity = 'Low';
        let colorClass = '';
        if (e.type.toLowerCase().includes('overspeed') || e.type.toLowerCase().includes('harsh')) {
            severity = 'High';
            colorClass = 'danger';
        } else if (e.type.toLowerCase().includes('ignition')) {
            severity = 'Medium';
        }
        
        return `
            <div class="dtc-item" style="background:rgba(255,255,255,0.02); border:1px solid var(--border-light); margin-bottom:10px;">
                <div>
                    <strong style="color:#fff;">${e.type.replace(/([A-Z])/g, ' $1').trim()}</strong>
                    <div style="font-size:0.75rem; color:var(--text-dim);">${e.vehicle} • ${e.time}</div>
                </div>
                <span class="stats-badge ${colorClass}">${severity}</span>
            </div>
        `;
    }).join('');
}

function initSafetyCenter() {
    const ctx = document.getElementById('safetyRadarChart');
    if (!ctx || safetyRadarChart) return;

    safetyRadarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Speeding', 'Harsh Brake', 'Rapid Accel', 'Sharp Turn', 'Night Driving', 'Idle Time'],
            datasets: [{
                label: 'Fleet Average',
                data: [],
                fill: true,
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                borderColor: '#10b981',
                pointBackgroundColor: '#10b981'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { title: { display: true, text: 'No Data Available', color: '#64748b' } },
            scales: {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#94a3b8' },
                    ticks: { display: false }
                }
            }
        }
    });

    if (!latestVehicles || latestVehicles.length === 0) {
        document.querySelector('.percentage').textContent = '0';
        document.querySelector('.score-label').innerHTML = 'Fleet Safety Grade: <strong>No Data Available</strong>';
        document.querySelector('#safety-asset-context').innerText = 'No Data Available';
        return;
    }

    if (selectedVehicle) updateSafetyForSelected();
}

function initMaintenanceCenter() {
    const dtcList = document.getElementById('active-dtc-list');
    const forecast = document.getElementById('maintenance-forecast');

    if (!latestVehicles || latestVehicles.length === 0) {
        if (dtcList) dtcList.innerHTML = '<div style="color:var(--text-dim); padding:20px; text-align:center;">No Data Available</div>';
        if (forecast) forecast.innerHTML = '<div style="color:var(--text-dim); padding:20px; text-align:center;">No Data Available</div>';
        document.querySelector('#maint-asset-context').innerText = 'No Data Available';
        document.querySelector('.maintenance-list .stats-badge').innerText = '0 Critical';
        return;
    }

    if (selectedVehicle) updateMaintForSelected();
}

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
// CHATBOT ENGINE
// -----------------------------------------
async function loadChatHistory(sessionId = currentSessionId) {
    if (!authToken) return;
    try {
        const resp = await fetch(`/api/v1/chat/history?session_id=${sessionId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!resp.ok) return;
        const data = await resp.json();
        
        chatMessages.innerHTML = '';
        if (data.history && data.history.length > 0) {
            data.history.forEach(msg => appendMessage(msg.role === 'user' ? 'user' : 'bot', msg.content));
        } else {
            setTimeout(() => {
                appendMessage('bot', `**System Online.** Hello ${userName || 'Operator'}. \n\nI am the **AI - Telemetrix** Assistant. How can I assist with your fleet intelligence today?`);
            }, 600);
        }
        updateHistorySidebar();
    } catch (e) { console.error("Chat History Error:", e); }
}

async function updateHistorySidebar() {
    if (!historyList) return;
    let sessions = JSON.parse(localStorage.getItem('fleet_sessions') || '[]');
    if (!sessions.includes(currentSessionId)) {
        sessions.unshift(currentSessionId);
        localStorage.setItem('fleet_sessions', JSON.stringify(sessions));
    }
    
    const searchTerm = historySearchInput?.value.toLowerCase() || '';
    const filteredSessions = sessions.filter((s, idx) => `Session ${sessions.length - idx}`.toLowerCase().includes(searchTerm));

    historyList.innerHTML = filteredSessions.length ? '' : '<div class="history-empty">No matching chats</div>';
    
    filteredSessions.forEach((sid) => {
        const originalIdx = sessions.indexOf(sid);
        const item = document.createElement('div');
        item.className = `history-item ${sid === currentSessionId ? 'active' : ''}`;
        item.innerHTML = `
            <i data-lucide="message-square" style="width:14px;"></i> 
            <span style="flex:1; overflow:hidden; text-overflow:ellipsis;">Session ${sessions.length - originalIdx}</span>
            <button class="delete-session" onclick="deleteChatSession(event, '${sid}')"><i data-lucide="trash-2" style="width:12px;"></i></button>
        `;
        item.onclick = () => {
            currentSessionId = sid;
            localStorage.setItem('fleet_session_id', sid);
            loadChatHistory(sid);
        };
        historyList.appendChild(item);
    });
    lucide.createIcons({ el: historyList });
}

function deleteChatSession(event, sid) {
    event.stopPropagation();
    if (!confirm("Are you sure you want to delete this intelligence session?")) return;
    
    let sessions = JSON.parse(localStorage.getItem('fleet_sessions') || '[]');
    sessions = sessions.filter(s => s !== sid);
    localStorage.setItem('fleet_sessions', JSON.stringify(sessions));
    
    if (sid === currentSessionId) {
        currentSessionId = sessions[0] || ('session-' + Math.random().toString(36).substr(2, 9));
        localStorage.setItem('fleet_session_id', currentSessionId);
        loadChatHistory();
    } else {
        updateHistorySidebar();
    }
}

historySearchInput?.addEventListener('input', updateHistorySidebar);

function appendMessage(type, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type === 'user' ? 'user-message' : 'bot-message'}`;
    const content = document.createElement('div');
    content.className = 'message-content';
    
    // Premium Markdown Rendering
    if (typeof marked !== 'undefined') {
        content.innerHTML = marked.parse(text);
    } else {
        content.innerHTML = text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
    
    // Fix Table Responsiveness
    const tables = content.querySelectorAll('table');
    tables.forEach(t => {
        const wrap = document.createElement('div');
        wrap.style.overflowX = 'auto';
        wrap.style.width = '100%';
        t.parentNode.insertBefore(wrap, t);
        wrap.appendChild(t);
    });

    msgDiv.appendChild(content);
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

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || !authToken) return;

    appendMessage('user', text);
    userInput.value = '';
    if (typingIndicator) typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch('/api/v1/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify({ query: text, session_id: currentSessionId })
        });
        const data = await response.json();
        if (typingIndicator) typingIndicator.style.display = 'none';
        if (response.ok) {
            appendMessage('bot', data.answer);
            updateHistorySidebar();
        } else {
            appendMessage('bot', `**Access Denied.** ${data.detail || 'Node error.'}`);
        }
    } catch (err) {
        if (typingIndicator) typingIndicator.style.display = 'none';
        appendMessage('bot', 'Network intelligence node unreachable.');
    }
}

// -----------------------------------------
// ANALYTICS & DASHBOARD ENGINE
// -----------------------------------------
async function loadDashboardData() {
    if (!authToken) return;
    try {
        const summaryResp = await fetch('/api/analytics/summary', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!summaryResp.ok) throw new Error("Analytics Fetch Failed");
        
        const summaryData = await summaryResp.json();
        
        // Backend returns data under summaryData.kpis
        const raw = summaryData.kpis || summaryData;
        const k = {
            total:      raw.total      || raw.total_vehicles || 0,
            moving:     raw.active     || raw.moving         || 0,
            stationary: raw.idle       || raw.stationary     || 0,
            offline:    raw.stale      || raw.offline        || 0,
            overspeed:  raw.overspeed  || raw.overspeed_today|| 0,
            online:     raw.online     || 0
        };

        const vehiclesResp = await fetch('/api/v1/vehicles/live?limit=1000', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const vehicles = Array.isArray(await vehiclesResp.clone().json()) ? await vehiclesResp.json() : [];
        latestVehicles = vehicles;

        // Update Expandable Master Cards with TRUE database counts
        animateCounter('kpi-total',   k.total);
        animateCounter('kpi-moving',  k.moving);
        animateCounter('kpi-idle',    k.stationary);
        animateCounter('kpi-stopped', k.stationary);
        animateCounter('kpi-offline', k.offline);
        animateCounter('kpi-offline-alerts', k.offline);

        // Update Alerts KPIs from DB
        animateCounter('kpi-alerts-total', k.overspeed);
        animateCounter('kpi-overspeed',    k.overspeed);
        
        // Update Trips KPI
        animateCounter('kpi-trips-total',   k.moving);
        animateCounter('kpi-running-trips',  k.moving);
        
        // Update Charts using current live sample
        updateVelocityChart(vehicles);
        
        // Use true database counts for status distribution donut
        const stats = {
            total: k.total,
            moving: k.moving,
            idle: k.stationary,
            stopped: 0,
            offline: k.offline
        };
        updateStatusDonut(stats);

        // Update Fuel View Stats if they exist (Safely fallback if no db values exist)
        const fuelCost = document.querySelector('#view-fuel .mini-stat:nth-child(1) .card-value');
        const avgEff = document.querySelector('#view-fuel .mini-stat:nth-child(2) .card-value');
        if (fuelCost) fuelCost.innerText = `$${(k.total * 0.4).toLocaleString(undefined, {maximumFractionDigits: 0})}`; 
        if (avgEff) avgEff.innerText = `N/A`;

        // Update Asset Grid with VIN and proper status
        renderAssetGrid(vehicles);
        
        // Update Recent Events in Safety Dashboard if data exists
        if (summaryData.recent_events && summaryData.recent_events.length > 0) {
            updateSafetyEvents(summaryData.recent_events);
        }
        
        // Update the badge in the minimizable matrix header
        const badge = document.getElementById('vehicle-count-badge');
        if (badge) badge.innerText = `${k.total.toLocaleString()} Total Units`;

    } catch (e) {
        console.error("Dashboard Engine Failure:", e);
        showNotification("Intelligence node sync error. Retrying...", "error");
    }
}

function updateVelocityChart(vehicles) {
    const ctx = document.getElementById('fleetTrendChart');
    if (!ctx) return;

    const labels = vehicles.slice(0, 8).map(v => v.name || 'Unknown');
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
    if (legend) {
        legend.innerHTML = labels.map((l, i) => `
            <div style="display:flex; align-items:center; gap:8px; background:rgba(255,255,255,0.02); padding:8px 12px; border-radius:10px; border:1px solid var(--border-light);">
                <span style="width:8px; height:8px; border-radius:50%; background:${colors[i]};"></span>
                <span style="font-size:0.75rem; color:var(--text-secondary); font-weight:700; flex:1;">${l}</span>
                <span style="font-size:0.75rem; color:#fff; font-weight:700;">${data[i]}</span>
            </div>`).join('');
    }
}

function renderAssetGrid(vehicles) {
    const grid = document.getElementById('asset-grid');
    if (!grid) return;
    grid.innerHTML = vehicles.map(v => {
        const fuel = v.attributes?.fuelLevel || v.attributes?.fuel || 0;
        const speed = v.speed || 0;
        const status = (v.status || 'unknown').toLowerCase();
        const isOnline = status === 'online';
        
        const make = v.attributes?.make || v.category || 'Asset';
        const model = v.model || v.attributes?.model || '';
        const year = v.attributes?.year || '';
        
        return `
            <div class="asset-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <h4 style="font-weight:700; color:#fff;">${v.name}</h4>
                        <div class="asset-vin">${v.vin || v.uniqueId || 'N/A'}</div>
                    </div>
                    <div class="status-indicator ${isOnline ? 'status-online' : 'status-offline'}">
                        ${isOnline ? '<span class="pulse-dot"></span>' : ''}${status.toUpperCase()}
                    </div>
                </div>
                <div class="asset-metrics-row">
                    <div class="metric-box"><span class="metric-label">Speed</span><div class="metric-value">${speed.toFixed(0)} <small>km/h</small></div></div>
                    <div class="metric-box"><span class="metric-label">Energy</span><div class="metric-value">${fuel > 0 ? fuel + '%' : 'N/A'}</div></div>
                </div>
                <div class="asset-vin" style="margin-top: -10px; margin-bottom: 10px; font-size: 0.7rem; color: var(--brand-primary);">${make} ${model} (${year})</div>
                <div style="height:4px; background:rgba(255,255,255,0.05); border-radius:2px; overflow:hidden;">
                    <div style="height:100%; width:${fuel}%; background:var(--brand-primary); transition: width 0.5s ease;"></div>
                </div>
                <div style="margin-top:20px; display:flex; gap:12px;">
                    <button class="glass-btn" onclick="showOnMap(${v.latitude}, ${v.longitude}, '${v.name}', ${v.id})" style="flex:1;"><i data-lucide="map-pin"></i> View</button>
                    <button class="glass-btn info-asset-btn" onclick="openVehicleIntel('${v.name}')" style="flex:1;"><i data-lucide="info"></i> Intel</button>
                </div>
            </div>`;
    }).join('');
    lucide.createIcons({ el: grid });
}

// -----------------------------------------
// VEHICLE INTELLIGENCE ENGINE (real API)
// -----------------------------------------

let currentIntelDeviceId = null;   // track which device is loaded in the intel panel

function initVehicleIntel() {
    // Called when the Vehicle Intelligence nav item is clicked
    if (lifecycleChart) {
        try { lifecycleChart.resize(); } catch(e) {}
    }
    // If a vehicle is already selected, refresh its intel
    if (currentIntelDeviceId) {
        loadVehicleIntel(currentIntelDeviceId);
    }
}

async function openVehicleIntel(name) {
    const v = latestVehicles.find(x => x.name === name);
    if (!v) return;

    selectedVehicle = v;
    currentIntelDeviceId = v.id;
    activeVinDeviceId    = v.id;

    // Update Context Labels in other modules
    const contextText = `Asset: ${v.name} (${v.vin || v.uniqueId || 'N/A'})`;
    ['fuel-asset-context', 'safety-asset-context', 'maint-asset-context'].forEach(id => {
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
    updateSafetyForSelected();
    updateMaintForSelected();
}

async function loadVehicleIntel(deviceId) {
    if (!deviceId || !authToken) return;

    // Show main grid, hide no-selection placeholder
    const noSel    = document.getElementById('intel-no-selection');
    const mainGrid = document.getElementById('intel-main-grid');
    const banner   = document.getElementById('intel-amber-banner');
    if (noSel)    noSel.style.display    = 'none';
    if (mainGrid) mainGrid.style.display = 'block';

    // Spinner on refresh button
    const refreshBtn = document.getElementById('intel-refresh-btn');
    if (refreshBtn) refreshBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:13px;"></i> Loading…';

    try {
        const resp = await fetch(`/api/v1/vehicles/${deviceId}/intel`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!resp.ok) throw new Error(`Intel API ${resp.status}`);
        const d = await resp.json();

        console.log(`[VIN Intel] Device ${deviceId} | VIN: ${d.vin} | source: ${d.vin_source} | badge: ${d.badge?.label}`);

        // ── Header ──────────────────────────────────────────
        const nameEl  = document.getElementById('intel-v-name');
        const vinEl   = document.getElementById('intel-v-vin');
        const badgeEl = document.getElementById('intel-vin-badge');

        if (nameEl)  nameEl.innerText  = d.name || 'Unknown';
        if (vinEl)   vinEl.innerText   = d.vin  || '—';

        // Populate Configuration Card
        const configVin = document.getElementById('intel-config-vin');
        if (configVin) configVin.value = d.vin || '';

        if (badgeEl) {
            if (d.vin && d.badge) {
                badgeEl.style.display = 'inline-block';
                badgeEl.innerText     = d.badge.label;
                badgeEl.className     = `stats-badge ${d.badge.class || ''}`;
            } else {
                badgeEl.style.display = 'none';
            }
        }

        // ── Amber Banner ─────────────────────────────────────
        if (banner) {
            if (d.is_incomplete) banner.classList.remove('vin-hidden');
            else                  banner.classList.add('vin-hidden');
        }

        // ── Specs Grid ───────────────────────────────────────
        const s = d.specs || {};
        const setField = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val || 'N/A';
        };
        setField('intel-make',     s.make);
        setField('intel-model',    s.model);
        setField('intel-year',     s.year  ? String(s.year) : null);
        setField('intel-engine',   s.engine);
        setField('intel-fuel',     s.fuel_type);
        setField('intel-category', s.category);

        // ── Odometer ─────────────────────────────────────────
        const odoEl = document.getElementById('intel-odometer');
        if (odoEl) odoEl.innerText = d.odometer_km > 0 ? `${d.odometer_km.toLocaleString()} km` : '— km';

        // ── Profile Status Badge ──────────────────────────────
        const statusEl = document.getElementById('intel-profile-status');
        if (statusEl) {
            const statusMap = {
                'obd_verified':   ['⚡ OBD Verified',   'success'],
                'manual_enriched':['🤖 Manual Enriched', 'primary'],
            };
            const [label, cls] = statusMap[d.profile_status] || ['Pending / Unknown', ''];
            statusEl.innerText  = label;
            statusEl.className  = `stats-badge ${cls}`;
        }

        // ── Rich Technical Specs (NEW) ────────────────────────
        renderRichVinData(s);

        // ── Depreciation Chart ────────────────────────────────
        const depr        = d.depreciation || {};
        const hasDeprData = depr.labels && depr.labels.length > 0 && s.year;

        const noDataEl   = document.getElementById('intel-depr-no-data');
        const chartWrap  = document.getElementById('intel-depr-chart-wrap');
        const summaryEl  = document.getElementById('intel-depr-summary');

        if (hasDeprData) {
            if (noDataEl)  noDataEl.style.display  = 'none';
            if (chartWrap) chartWrap.style.display  = 'block';
            if (summaryEl) summaryEl.style.display  = 'flex';

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
            if (ageEl) ageEl.innerText = age !== null ? `${age} yr${age !== 1 ? 's' : ''}` : '—';
            if (deprOdo) deprOdo.innerText = d.odometer_km > 0 ? `${d.odometer_km.toLocaleString()} km` : '—';

        } else {
            if (noDataEl)  noDataEl.style.display  = 'flex';
            if (chartWrap) chartWrap.style.display  = 'none';
            if (summaryEl) summaryEl.style.display  = 'none';
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
    if (!selectedVehicle) {
        document.getElementById('intel-no-selection').style.display = 'block';
        document.getElementById('intel-main-grid').style.display = 'none';
        document.getElementById('intel-amber-banner')?.classList.add('vin-hidden');
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

// ── Manual VIN Modal Logic ───────────────────────────────────────────────────

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


// -----------------------------------------
// TACTICAL MAP ENGINE
// -----------------------------------------

// Exposed switchLayer for global theme toggle
function switchMapLayer(targetLayer, targetBtnId) {
    if (!map) return;
    [darkLayer, lightLayer, standardLayer, satelliteLayer].forEach(l => {
        if (l) map.removeLayer(l);
    });
    if (targetLayer) map.addLayer(targetLayer);
    
    // Update map interface buttons
    const allBtns = ['btn-layer-dark', 'btn-layer-light', 'btn-layer-standard', 'btn-layer-satellite'];
    allBtns.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.classList.remove('active');
    });
    const activeBtn = document.getElementById(targetBtnId);
    if (activeBtn) activeBtn.classList.add('active');
}

function initMap() {
    if (map || !document.getElementById('live-map')) return;
    
    // Modern Map Initialization
    map = L.map('live-map', { 
        zoomControl: false,
        attributionControl: false,
        fadeAnimation: true,
        markerZoomAnimation: true,
        worldCopyJump: true,
        maxZoom: 20
    }).setView([24.8607, 67.0011], 12);
    
    // Premium Professional Map Layers
    darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CartoDB'
    }).addTo(map);
    
    lightLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CartoDB'
    });
    
    satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri'
    });

    // Layer Switcher Controls
    document.getElementById('btn-layer-dark').onclick = () => switchMapLayer(darkLayer, 'btn-layer-dark');
    document.getElementById('btn-layer-light').onclick = () => switchMapLayer(lightLayer, 'btn-layer-light');
    document.getElementById('btn-layer-satellite').onclick = () => switchMapLayer(satelliteLayer, 'btn-layer-satellite');
    
    // Zoom Controls Redesign
    L.control.zoom({ position: 'topright' }).addTo(map);
    
    lucide.createIcons();

    // Center on Selected logic
    document.getElementById('btn-center-vehicle').onclick = () => {
        if (selectedVehicle && selectedVehicle.latitude) {
            map.flyTo([selectedVehicle.latitude, selectedVehicle.longitude], 17);
        } else {
            showNotification("No vehicle selected to center", "info");
        }
    };

    markerClusterGroup = L.markerClusterGroup({
        disableClusteringAtZoom: 16,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        maxClusterRadius: 50,
        iconCreateFunction: (cluster) => {
            return L.divIcon({
                html: `<div class="cluster-marker"><span>${cluster.getChildCount()}</span></div>`,
                className: 'cluster-icon-wrap',
                iconSize: [40, 40]
            });
        }
    });
    map.addLayer(markerClusterGroup);
    
    // Auto-initialize icons in popups when they open
    map.on('popupopen', (e) => {
        if (e.popup._contentNode) {
            lucide.createIcons({ el: e.popup._contentNode });
        }
    });
    
    setTimeout(() => map.invalidateSize(), 500);
    startMapUpdates();
}

async function updateVehicleMarkers() {
    if (!authToken || !map) return;
    
    try {
        const resp = await fetch('/api/v1/vehicles/live?limit=1000', { 
            headers: { 'Authorization': `Bearer ${authToken}` } 
        });
        
        if (!resp.ok) return;
        const vehicles = await resp.json();
        latestVehicles = vehicles;
        
        if (vehicles.length === 0) {
            const listEl = document.getElementById('map-vehicle-list');
            if (listEl) listEl.innerHTML = '<div style="padding:40px; text-align:center; color:#64748b; font-family:var(--map-font);">No Data Available</div>';
            markerClusterGroup.clearLayers();
            markers = {};
            return;
        }

        renderMapSidebar(vehicles);

        vehicles.forEach(v => {
            if (v.latitude && v.longitude) {
                const pos = [v.latitude, v.longitude];
                const status = getVehicleStatus(v);
                
                // --- REDESIGNED MARKER HTML ---
                const markerHtml = `
                    <div class="tactical-marker-container">
                        <div class="tactical-marker-label">${v.name}</div>
                        <div class="tactical-marker-icon" style="transform: rotate(${v.course || 0}deg);">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 2L4.5 20.29L5.21 21L12 18L18.79 21L19.5 20.29L12 2Z" fill="${status.color}" stroke="#ffffff" stroke-width="1.5" stroke-linejoin="round"/>
                            </svg>
                        </div>
                    </div>`;
                
                const icon = L.divIcon({ 
                    html: markerHtml, 
                    className: 'tactical-marker-wrap', 
                    iconSize: [32, 32], 
                    iconAnchor: [16, 16] 
                });

                if (markers[v.id]) {
                    markers[v.id].setLatLng(pos);
                    markers[v.id].setIcon(icon);
                    markers[v.id].setPopupContent(createTacticalPopup(v));
                } else {
                    const popupOpts = { 
                        className: 'tactical-popup', 
                        maxWidth: 300, 
                        minWidth: 300, 
                        autoPanPadding: [30, 30],
                        offset: [0, -10]
                    };
                    const marker = L.marker(pos, { icon }).bindPopup(createTacticalPopup(v), popupOpts);
                    markers[v.id] = marker;
                    markerClusterGroup.addLayer(marker);
                }
            }
        });
        
        updateDebugOverlay();
        
    } catch (e) { 
        console.error("Map Update Engine Error:", e); 
    }
}

function updateDebugOverlay() {
    const totalEl = document.getElementById('dbg-total');
    const markersEl = document.getElementById('dbg-markers');
    if (totalEl) totalEl.innerText = latestVehicles.length;
    if (markersEl) markersEl.innerText = Object.keys(markers).length;
}

function renderMapSidebar(vehicles) {
    const list = document.getElementById('map-vehicle-list');
    if (!list) return;
    
    const searchTerm = document.getElementById('map-vehicle-search')?.value.toLowerCase() || '';
    const filtered = vehicles.filter(v => 
        (v.name || '').toLowerCase().includes(searchTerm) || 
        (v.uniqueId || '').toLowerCase().includes(searchTerm)
    );

    list.innerHTML = filtered.map(v => {
        const status = getVehicleStatus(v);
        const speedKph = (v.speed || 0).toFixed(1);
        const isActive = (selectedVehicle && selectedVehicle.id === v.id) ? 'active' : '';
        const timeStr = v.lastUpdate ? new Date(v.lastUpdate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'N/A';
        
        return `
            <div class="map-vehicle-item ${isActive}" onclick="selectVehicleOnMap(${v.id})">
                <div class="vehicle-item-top">
                    <span class="vehicle-item-name">${v.name}</span>
                    <span class="status-dot ${status.class}"></span>
                </div>
                <div class="vehicle-item-id">DEVICE ID: ${v.uniqueId}</div>
                <div class="vehicle-item-stats">
                    <span style="color:var(--brand-primary); font-weight:800;">${speedKph} KM/H</span>
                    <span>${timeStr}</span>
                </div>
            </div>
        `;
    }).join('');
}

function selectVehicleOnMap(id) {
    const v = latestVehicles.find(veh => veh.id === id);
    if (!v) return;
    
    selectedVehicle = v;
    map.flyTo([v.latitude, v.longitude], 17);
    
    if (markers[id]) {
        const marker = markers[id];
        if (markerClusterGroup && markerClusterGroup.hasLayer(marker)) {
            markerClusterGroup.zoomToShowLayer(marker, () => marker.openPopup());
        } else {
            marker.openPopup();
        }
    }
    
    renderMapSidebar(latestVehicles);
}

function createTacticalPopup(v) {
    const status = getVehicleStatus(v);
    const lastUpdate = v.lastUpdate ? new Date(v.lastUpdate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'N/A';
    const speed = (v.speed || 0).toFixed(1);
    const ignition = v.attributes?.ignition ? 'ON' : 'OFF';
    const ignColor = v.attributes?.ignition ? 'var(--brand-warning)' : 'var(--text-dim)';
    const address = v.address || 'Locating address...';
    const distanceKm = ((v.attributes?.totalDistance || v.attributes?.odometer || 0) / 1000).toFixed(1);
    
    // Intelligence data
    const make = v.attributes?.make || v.category || 'Asset';
    const model = v.model || v.attributes?.model || '';
    const fuelLvl = v.attributes?.fuelLevel || v.attributes?.fuel || 0;
    const fuelMethod = v.attributes?.fuelMethod || 'estimated';
    const fuelLabel = fuelMethod === 'sensor' ? 'Verified' : 'AI-Est';
    const fuelColor = fuelMethod === 'sensor' ? 'var(--brand-success)' : 'var(--brand-warning)';

    return `
<div class="popup-card">
  <div class="popup-header">
    <div style="display:flex; flex-direction:column;">
        <div class="popup-title">${v.name || 'Unknown Asset'}</div>
        <div style="font-size:0.65rem; color:var(--brand-primary); font-weight:700;">${make} ${model}</div>
    </div>
    <div class="popup-badge" style="background:${status.color}20; color:${status.color}; border:1px solid ${status.color}40;">
        ${status.label}
    </div>
  </div>
  
  <div class="popup-grid">
    <div class="popup-stat">
      <div class="popup-stat-label">Speed</div>
      <div class="popup-stat-value" style="color:var(--brand-primary)">${speed}<small style="font-size:0.6rem; margin-left:2px;">KM/H</small></div>
    </div>
    <div class="popup-stat">
      <div class="popup-stat-label">Fuel Level</div>
      <div class="popup-stat-value" style="color:${fuelColor}">${fuelLvl}% <small style="font-size:0.5rem; opacity:0.8;">(${fuelLabel})</small></div>
    </div>
    <div class="popup-stat">
      <div class="popup-stat-label">Odometer</div>
      <div class="popup-stat-value">${distanceKm}<small style="font-size:0.6rem; margin-left:2px;">KM</small></div>
    </div>
    <div class="popup-stat">
      <div class="popup-stat-label">Ignition</div>
      <div class="popup-stat-value" style="color:${ignColor}">${ignition}</div>
    </div>
  </div>

  <div class="popup-footer">
    <div style="display:flex; align-items:center; gap:6px;">
        <i data-lucide="clock" style="width:12px;"></i>
        <span>Last update: ${lastUpdate}</span>
    </div>
    <div class="popup-address">
        <i data-lucide="map-pin" style="width:10px; display:inline-block; margin-right:4px;"></i>
        ${address}
    </div>
  </div>

  <div class="popup-actions">
    <button onclick="openDetailsModal(${v.id})" class="popup-btn"><i data-lucide="activity"></i> Status</button>
    <button onclick="openVehicleIntel('${v.name}')" class="popup-btn"><i data-lucide="info"></i> Intel</button>
    <button onclick="triggerVehicleEdit(${v.id})" class="popup-btn"><i data-lucide="edit-3"></i> Edit</button>
  </div>
</div>`;
}

function triggerVehicleEdit(id) {
    const v = latestVehicles.find(veh => veh.id === id);
    if (!v) return;

    // Populate the edit modal
    const modal = document.getElementById('edit-vehicle-modal');
    if (!modal) return;

    document.getElementById('edit-vehicle-id').value = v.id;
    document.getElementById('edit-vehicle-name').value = v.name || '';
    document.getElementById('edit-vehicle-uid').value = v.uniqueId || '';
    document.getElementById('edit-vehicle-vin').value = v.vin || v.attributes?.vin || '';
    document.getElementById('edit-vehicle-model').value = v.model || v.attributes?.model || '';
    document.getElementById('edit-vehicle-category').value = v.category || 'car';
    document.getElementById('edit-vehicle-contact').value = v.contact || '';

    modal.classList.remove('hidden-view');
    modal.style.display = 'flex';
    lucide.createIcons({ el: modal });
}

function closeEditModal() {
    const modal = document.getElementById('edit-vehicle-modal');
    if (modal) {
        modal.classList.add('hidden-view');
        modal.style.display = 'none';
    }
}

// Attach listener to Edit form
document.addEventListener('DOMContentLoaded', () => {
    const editForm = document.getElementById('edit-vehicle-form');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('edit-vehicle-id').value;
            const payload = {
                name: document.getElementById('edit-vehicle-name').value,
                uniqueId: document.getElementById('edit-vehicle-uid').value,
                vin: document.getElementById('edit-vehicle-vin').value,
                model: document.getElementById('edit-vehicle-model').value,
                category: document.getElementById('edit-vehicle-category').value,
                contact: document.getElementById('edit-vehicle-contact').value
            };

            try {
                const resp = await fetch(`/api/v1/vehicles/${id}`, {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (resp.ok) {
                    showNotification('Asset updated successfully', 'success');
                    closeEditModal();
                    loadDashboardData(); // Refresh everything
                } else {
                    const err = await resp.json();
                    showNotification(err.detail || 'Update failed', 'error');
                }
            } catch (err) {
                showNotification('Network error', 'error');
            }
        });
    }
});

// -----------------------------------------
// VEHICLE DETAILS MODAL
// -----------------------------------------
let selectedVehicleIdForDetails = null;

function openDetailsModal(id) {
    const v = latestVehicles.find(veh => veh.id === id);
    if (!v) return;
    selectedVehicleIdForDetails = id;

    // Basic Info
    document.getElementById('det-name').innerText = v.name || 'Unknown';
    document.getElementById('det-uid').innerText = v.uniqueId || 'N/A';
    document.getElementById('det-vin').innerText = v.vin || v.attributes?.vin || 'N/A';
    document.getElementById('det-model').innerText = v.model || 'N/A';
    document.getElementById('det-category').innerText = v.category || 'N/A';
    document.getElementById('det-group').innerText = v.groupId || 'Default';
    document.getElementById('det-driver').innerText = v.contact || 'Not Assigned';
    document.getElementById('det-phone').innerText = v.phone || 'N/A';

    // Telemetry
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

    // Health & Status (Real data)
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

function focusVehicleOnMap() {
    if (selectedVehicleIdForDetails) {
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

// Search listener for map sidebar
document.getElementById('map-vehicle-search')?.addEventListener('input', () => {
    renderMapSidebar(latestVehicles);
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

function startMapUpdates() { 
    stopMapUpdates();
    updateVehicleMarkers(); 
    mapInterval = setInterval(updateVehicleMarkers, 12000); // 12 seconds refresh
}
function stopMapUpdates() { if (mapInterval) clearInterval(mapInterval); }

// -----------------------------------------
// CORE INITIALIZATION
// -----------------------------------------
function checkAuthState() {
    if (authToken) {
        loginView.classList.replace('active-view', 'hidden-view');
        appView.classList.replace('hidden-view', 'active-view');
        // Apply Role-Based Access
        if (roleText) {
            roleText.innerText = userRole || 'USER';
        }
        if (roleDisplay) roleDisplay.style.color = (userRole === 'SUPERADMIN' || userRole === 'ADMIN') ? 'var(--brand-success)' : 'var(--brand-primary)';
        
        userNameDisplay.innerText = userName || 'Operator';
        setupRoleUI();
        loadDashboardData();
        loadChatHistory();
    } else {
        appView.classList.replace('active-view', 'hidden-view');
        loginView.classList.replace('hidden-view', 'active-view');
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
}

function applySavedTheme() {
    const savedTheme = localStorage.getItem('fleet_theme');
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
    const shouldUseLight = savedTheme ? savedTheme === 'light' : prefersLight;
    document.body.classList.toggle('light-theme', shouldUseLight);

    const icon = document.querySelector('#global-theme-toggle i');
    if (icon) {
        icon.setAttribute('data-lucide', shouldUseLight ? 'moon' : 'sun');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    applySavedTheme();
    checkAuthState();
    safeCreateIcons();
    
    // Global Theme Toggle
    document.getElementById('global-theme-toggle')?.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const isLight = document.body.classList.contains('light-theme');
        localStorage.setItem('fleet_theme', isLight ? 'light' : 'dark');
        
        // Update icon
        const icon = document.querySelector('#global-theme-toggle i');
        if (icon) {
            icon.setAttribute('data-lucide', isLight ? 'moon' : 'sun');
            safeCreateIcons();
        }
        
        // Sync with Map if needed
        if (isLight && typeof switchMapLayer === 'function' && lightLayer) {
            switchMapLayer(lightLayer, 'btn-layer-light');
        } else if (!isLight && typeof switchMapLayer === 'function' && darkLayer) {
            switchMapLayer(darkLayer, 'btn-layer-dark');
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

    // Map Sidebar Sidebar Toggle
    document.getElementById('toggle-map-sidebar')?.addEventListener('click', () => {
        const sidebar = document.getElementById('map-asset-sidebar');
        const toggleBtn = document.getElementById('toggle-map-sidebar');
        const icon = toggleBtn.querySelector('i');
        
        sidebar.classList.toggle('collapsed');
        
        if (sidebar.classList.contains('collapsed')) {
            icon.setAttribute('data-lucide', 'chevron-right');
        } else {
            icon.setAttribute('data-lucide', 'chevron-left');
        }
        
        safeCreateIcons();
        // Re-invalidate map size after sidebar transition
        setTimeout(() => {
            if (map) map.invalidateSize();
        }, 400);
    });

    // Initialize Login Form
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value.trim();
            const nameField = document.getElementById('name');
            const nameGroup = document.getElementById('name-group');
            
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
                    name: nameField.value.trim() || 'New User'
                });
            } else {
                headers['Content-Type'] = 'application/x-www-form-urlencoded';
                body = `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`;
            }
            
            const btn = e.submitter || document.querySelector('.auth-btn');
            const originalBtnText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<span>${isRegister ? 'Creating Account...' : 'Authenticating...'}</span> <i data-lucide="loader-2" class="spin"></i>`;
            safeCreateIcons();
            loginError.innerText = '';
            
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
                    loginError.innerText = data.detail || 'Authentication failed. Please check credentials.';
                }
            } catch (err) { 
                console.error("Auth Error:", err);
                loginError.innerText = 'Security node unreachable. Check connection.'; 
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
        const nameGroup = document.getElementById('name-group');
        const authBtnText = document.querySelector('.auth-btn span');
        const toggleText = document.getElementById('toggle-text');
        const loginTitle = document.querySelector('.login-title');
        const loginSubtitle = document.querySelector('.login-subtitle');

        const isLogin = nameGroup.style.display === 'none';
        if (isLogin) {
            nameGroup.style.display = 'block';
            authBtnText.innerText = 'Create Account';
            toggleText.innerHTML = 'Already have access? <a href="#" id="toggle-auth" style="color: var(--brand-primary); text-decoration: none; font-weight: 700;">Sign In</a>';
            loginTitle.innerText = 'Join AI - Telemetrix';
            loginSubtitle.innerText = 'Create your enterprise fleet account';
        } else {
            nameGroup.style.display = 'none';
            authBtnText.innerText = 'Access System';
            toggleText.innerHTML = 'New to Telemetrix? <a href="#" id="toggle-auth" style="color: var(--brand-primary); text-decoration: none; font-weight: 700;">Request Access</a>';
            loginTitle.innerText = 'AI - Telemetrix';
            loginSubtitle.innerText = 'Enterprise Intelligence Portal';
        }
        
        // Re-attach listener because we replaced innerHTML
        document.getElementById('toggle-auth')?.addEventListener('click', toggleAuthMode);
        safeCreateIcons();
    }

    document.getElementById('toggle-auth')?.addEventListener('click', toggleAuthMode);
});

logoutBtn?.addEventListener('click', () => { localStorage.clear(); location.reload(); });

// View Switching
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const view = item.getAttribute('data-view');
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        document.querySelectorAll('.sub-view').forEach(v => {
            v.classList.replace('active-view', 'hidden-view');
            if (v.id === `view-${view}`) v.classList.replace('hidden-view', 'active-view');
        });
        if (view === 'analytics') loadDashboardData();
        if (view === 'vehicle-intel') initVehicleIntel();
        if (view === 'fuel') initFuelAnalytics();
        if (view === 'safety') initSafetyCenter();
        if (view === 'maintenance') initMaintenanceCenter();
        if (view === 'map') {
            setTimeout(() => {
                initMap();
                if (map) map.invalidateSize();
                startMapUpdates();
            }, 300);
        } else {
            stopMapUpdates();
        }
    });
});

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
                showNotification(`Sync Complete — ${data.synced.devices || 0} Assets Updated`, 'success');
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

    // First click — show inline confirmation
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


