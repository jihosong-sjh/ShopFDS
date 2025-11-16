FROM ghcr.io/mlflow/mlflow:v2.9.2

# PostgreSQL 드라이버 설치
RUN pip install --no-cache-dir psycopg2-binary

# MLflow 실행
CMD ["mlflow", "server", \
     "--backend-store-uri", "${BACKEND_STORE_URI}", \
     "--default-artifact-root", "/mlflow/artifacts", \
     "--host", "0.0.0.0", \
     "--port", "5000"]
