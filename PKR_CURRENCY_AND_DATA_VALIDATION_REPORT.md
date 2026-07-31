# PKR Currency Replacement & Real-Data Architecture Validation Report

**Date:** July 29, 2026  
**Scope:** Workshop & Maintenance Modules  
**Status:** COMPLETE

---

## PART 1: PKR Currency Replacement

### Centralized Formatter Added

| File | Change |
|------|--------|
| `static/script.js:1041-1044` | New `formatPKR(amount, showDecimals)` helper function |

```javascript
function formatPKR(amount, showDecimals = false) {
    if (amount == null || isNaN(amount)) return 'Rs. 0';
    const num = Number(amount);
    if (showDecimals) return 'Rs. ' + num.toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return 'Rs. ' + num.toLocaleString('en-PK', { maximumFractionDigits: 0 });
}
```

### Files Updated

| # | File | Line(s) | Before | After |
|---|------|---------|--------|-------|
| 1 | `static/script.js` | 10977 | `'$' + j.actual_cost.toFixed(2)` | `formatPKR(j.actual_cost, true)` |
| 2 | `static/script.js` | 10977 | `'~$' + j.estimated_cost.toFixed(2)` | `'~' + formatPKR(j.estimated_cost, true)` |
| 3 | `static/script.js` | 11070 | `'$' + job.estimated_cost.toFixed(2)` | `formatPKR(job.estimated_cost, true)` |
| 4 | `static/script.js` | 11071 | `'$' + job.actual_cost.toFixed(2)` | `formatPKR(job.actual_cost, true)` |
| 5 | `static/script.js` | 11073 | `'$' + job.parts_cost.toFixed(2)` | `formatPKR(job.parts_cost, true)` |
| 6 | `static/script.js` | 11086 | `'$' + h.cost.toFixed(2)` | `formatPKR(h.cost, true)` |
| 7 | `static/script.js` | 11293 | `Labour Cost ($)` label | `Labour Cost (PKR)` |
| 8 | `static/script.js` | 11294 | `Parts Cost ($)` label | `Parts Cost (PKR)` |
| 9 | `static/index.html` | 1441 | `Cost (USD)` label | `Cost (PKR)` |

### Verification

- **0 remaining `$` currency references** in Workshop & Maintenance UI code
- **0 remaining `USD` references** in any HTML/JS files
- All cost fields now use `formatPKR()` or `Rs.` prefix consistently
- Existing `Rs.` formatting in Fuel module was already correct (no changes needed)

---

## PART 2: Real-Data Architecture Validation

### Audit Summary

| Category | Status | Details |
|----------|--------|---------|
| Mock Data | NONE FOUND | No fake/demo data in Workshop or Maintenance modules |
| Placeholder Data | NONE FOUND | No placeholder values in API responses |
| Hardcoded Schedule IDs | FIXED | Replaced `[1,2,3,4,5,6,7,8]` with API fetch |
| Duplicate Logic | NONE FOUND | Seed functions check for existing records before insert |
| Demo Account Bypass | EXISTS (Auth only) | `app/api/auth.py` demo accounts — not in scope |
| Default Fallback Values | ACCEPTABLE | `default_price=272.89` is a fallback, not mock data |

### Hardcoded Schedule IDs Fixed

| File | Line | Before | After |
|------|------|--------|-------|
| `static/script.js` | 2004-2017 | `const scheduleIds = [1, 2, 3, 4, 5, 6, 7, 8]` | Fetches from `/api/maintenance/planner/types` API |

### Data Source Verification — Every Dashboard Component

#### Workshop Dashboard (`GET /api/maintenance/workshop/dashboard`)

| KPI | Data Source | Query |
|-----|-------------|-------|
| Total Jobs | `workshop_jobs` table | `COUNT(*)` |
| Active Jobs | `workshop_jobs` table | `COUNT(*) WHERE status IN (...)` |
| Pending Jobs | `workshop_jobs` table | `COUNT(*) WHERE status='pending'` |
| Completed Jobs | `workshop_jobs` table | `COUNT(*) WHERE status='completed'` |
| Overdue Jobs | `workshop_jobs` table | `COUNT(*) WHERE status IN (...) AND due_date < NOW()` |
| Cancelled Jobs | `workshop_jobs` table | `COUNT(*) WHERE status='cancelled'` |
| Vehicles in Workshop | `workshop_jobs` table | `COUNT(*) WHERE status IN (...)` |
| Avg Repair Hours | `workshop_jobs` table | `AVG(labour_hours) WHERE status='completed'` |
| Total Technicians | `technicians` table | `COUNT(*) WHERE is_active=True` |
| Available Technicians | `technicians` table | `COUNT(*) WHERE is_active=True AND status='available'` |
| Busy Technicians | `technicians` table | `COUNT(*) WHERE is_active=True AND status='busy'` |
| Total Maintenance Cost | `workshop_jobs` table | `SUM(actual_cost) WHERE status='completed'` |

#### Maintenance Dashboard (`GET /api/maintenance/dashboard`)

| KPI | Data Source | Query |
|-----|-------------|-------|
| Dashboard data | `maintenance_logs`, `maintenance_schedules`, `workshops` tables | Real DB queries |
| Types summary | `maintenance_types` table | `COUNT(*)` with filters |
| Templates | `maintenance_templates` table | `SELECT *` with pagination |

#### Scheduler (`/api/maintenance/planner/scheduler/*`)

| Endpoint | Data Source |
|----------|-------------|
| `/summary` | Real DB queries on `vehicle_maintenance_plans`, `vehicle_plan_rule_overrides`, `maintenance_rules` |
| `/upcoming` | Real DB queries + Traccar API for odometer |
| `/overdue` | Real DB queries + Traccar API for odometer |
| `/calendar` | Real DB queries |
| `/activity` | Real DB queries from `rule_history` table |
| `/recalculate` | Traccar API + DB queries |

#### Vehicle Plans (`GET /api/maintenance/planner/vehicles-plans`)

| Field | Data Source |
|-------|-------------|
| Vehicle info | Traccar API (`/api/v1/vehicles/live`) |
| Plans | `vehicle_maintenance_plans` table |
| Overrides | `vehicle_plan_rule_overrides` table |
| Odometer | Traccar position attributes (`totalDistance`/`odometer`) |
| Due status | `calculate_fleet_due_status()` — real DB + Traccar |

#### Workshop Jobs

| Field | Data Source |
|-------|-------------|
| Job list | `workshop_jobs` table |
| Job detail | `workshop_jobs` + `tc_devices` + `maintenance_types` + `maintenance_templates` + `technicians` |
| Device name | Traccar API fallback (SQLite Device table empty) |
| Odometer | Traccar API positions |
| Notes | `job_notes` table |
| History | `maintenance_logs` table |

### Seed Data (Legitimate)

| Seed Function | Purpose | Duplicate Protection |
|---------------|---------|---------------------|
| `seed_default_types()` | Creates 21 maintenance types | Checks `COUNT(*)` before insert |
| `seed_default_templates()` | Creates default templates | Checks `COUNT(*)` before insert |
| `seed_default_rules()` | Creates 21 default rules | Checks `COUNT(*)` before insert |
| `seed_default_template_rules()` | Maps rules to templates | Checks existing links |

### Mock Data Status

| Module | Mock Data Found | Action |
|--------|----------------|--------|
| Workshop Dashboard | None | No action needed |
| Workshop Jobs | None | No action needed |
| Workshop Technicians | None | No action needed |
| Maintenance Dashboard | None | No action needed |
| Maintenance Types | None | No action needed |
| Maintenance Rules | None | No action needed |
| Maintenance Templates | None | No action needed |
| Vehicle Plans | None | No action needed |
| Scheduler | None | No action needed |
| Activity Feed | None | No action needed |

### Conclusion

All Workshop and Maintenance module data comes from real sources:
- **Traccar Database** (via REST API for vehicle data, positions, odometer)
- **planner.db SQLite** (for maintenance types, rules, templates, plans, overrides, logs, jobs, technicians)
- **No mock, placeholder, demo, or fake data** exists in these modules

Every dashboard KPI is calculated from real database queries.  
Every chart uses real database values.  
Every table displays real records.  
Every API response returns real data or indicates "No Data Available" where appropriate.
