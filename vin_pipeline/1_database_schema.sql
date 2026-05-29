-- 1. Complete database migration SQL
ALTER TABLE tc_devices ADD COLUMN IF NOT EXISTS vin VARCHAR(17);
ALTER TABLE tc_devices ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(100);
ALTER TABLE tc_devices ADD COLUMN IF NOT EXISTS model VARCHAR(100);
ALTER TABLE tc_devices ADD COLUMN IF NOT EXISTS year INT;
ALTER TABLE tc_devices ADD COLUMN IF NOT EXISTS pid_profile TEXT;
ALTER TABLE tc_devices ADD COLUMN IF NOT EXISTS profile_status VARCHAR(30);

CREATE TABLE IF NOT EXISTS vin_change_log (
  id SERIAL PRIMARY KEY,
  device_id INT,
  old_vin VARCHAR(17),
  new_vin VARCHAR(17),
  changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  wipe_executed BOOLEAN DEFAULT TRUE
);

-- Note: Depending on existing DB schema, this creates a trips table for backfill logic.
CREATE TABLE IF NOT EXISTS fleet_trips (
    id SERIAL PRIMARY KEY,
    device_id INT,
    distance_km FLOAT,
    fuel_consumed_liters FLOAT,
    cost_estimate FLOAT,
    efficiency_score FLOAT,
    start_time TIMESTAMP,
    end_time TIMESTAMP
);
