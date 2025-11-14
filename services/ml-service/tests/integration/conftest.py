"""
ML Service 통합 테스트 설정

공통 fixture 및 테스트 환경 설정
"""

import os
import sys
from pathlib import Path

import pytest

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 테스트 환경 변수 설정
os.environ["TESTING"] = "1"
os.environ["LOG_LEVEL"] = "WARNING"

# pytest 설정
def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers",
        "integration: 통합 테스트 (데이터베이스, 외부 서비스 등)"
    )
    config.addinivalue_line(
        "markers",
        "slow: 느린 테스트 (ML 학습 등)"
    )
