FROM ghcr.io/mlflow/mlflow:v2.9.2

# PostgreSQL 드라이버 및 필요 패키지 설치
RUN pip install --no-cache-dir \
    psycopg2-binary \
    sqlalchemy \
    alembic

# 엔트리포인트 스크립트 생성
RUN echo '#!/bin/bash\n\
echo "Waiting for PostgreSQL to be ready..."\n\
sleep 10\n\
echo "Starting MLflow server..."\n\
exec mlflow server \\\n\
     --backend-store-uri "$BACKEND_STORE_URI" \\\n\
     --default-artifact-root "$ARTIFACT_ROOT" \\\n\
     --host 0.0.0.0 \\\n\
     --port 5000' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
