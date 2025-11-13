-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- PostGIS 확장 (IP geolocation 용도)
CREATE EXTENSION IF NOT EXISTS postgis;

-- UUID 생성 함수
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 성능 개선을 위한 설정
ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- 데이터베이스 생성 확인
SELECT 'TimescaleDB extension installed successfully!' AS status;
