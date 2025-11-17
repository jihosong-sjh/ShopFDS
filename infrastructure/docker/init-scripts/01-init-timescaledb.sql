-- TimescaleDB 확장 활성화
-- Note: shared_preload_libraries='timescaledb' must be set in postgresql.conf (already configured in master.conf)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- PostGIS 확장 (IP geolocation 용도)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- UUID 생성 함수
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 데이터베이스 생성 확인
SELECT 'TimescaleDB extension installed successfully!' AS status;
