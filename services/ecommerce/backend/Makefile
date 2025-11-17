# Makefile for Ecommerce Backend

# Python 인터프리터
PYTHON := python

# 환경 변수 파일
ENV_FILE := .env

# 기본 타겟
.DEFAULT_GOAL := help

# 도움말
help:
	@echo "사용 가능한 명령어:"
	@echo "  make install      - 의존성 설치"
	@echo "  make dev          - 개발 서버 실행"
	@echo "  make seed         - 시드 데이터 생성"
	@echo "  make migrate      - 데이터베이스 마이그레이션"
	@echo "  make test         - 테스트 실행"
	@echo "  make clean        - 캐시 파일 삭제"

# 의존성 설치
install:
	pip install -r requirements.txt

# 개발 서버 실행
dev:
	$(PYTHON) src/main.py

# 시드 데이터 생성
seed:
	@echo "[START] 시드 데이터 생성..."
	$(PYTHON) scripts/seed_data.py

# 데이터베이스 마이그레이션
migrate:
	alembic upgrade head

# 마이그레이션 생성
migration:
	@read -p "마이그레이션 이름: " name; \
	alembic revision --autogenerate -m "$$name"

# 테스트 실행
test:
	pytest tests/ -v

# 유닛 테스트만
test-unit:
	pytest tests/unit -v

# 통합 테스트만
test-integration:
	pytest tests/integration -v

# 캐시 파일 삭제
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# 코드 포맷팅
format:
	black src/
	ruff check src/ --fix

# 코드 검사
lint:
	black --check src/
	ruff check src/

.PHONY: help install dev seed migrate migration test test-unit test-integration clean format lint