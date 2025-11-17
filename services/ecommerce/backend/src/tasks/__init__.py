"""
Celery Tasks for Ecommerce Service

이 모듈은 비동기 작업을 처리하는 Celery 작업을 포함합니다.
"""

from celery import Celery
import os

# Celery 애플리케이션 인스턴스 생성
app = Celery("ecommerce_tasks")

# celeryconfig 모듈에서 설정 로드
app.config_from_object("celeryconfig")

# 작업 모듈 자동 검색
app.autodiscover_tasks(["src.tasks"])
