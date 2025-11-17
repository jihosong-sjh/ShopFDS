-- MLflow 전용 데이터베이스 생성
CREATE DATABASE mlflow;

-- mlflow 데이터베이스에 권한 부여
\c mlflow;

-- MLflow가 필요로 하는 기본 권한 설정
GRANT ALL PRIVILEGES ON DATABASE mlflow TO shopfds;
GRANT CREATE ON SCHEMA public TO shopfds;