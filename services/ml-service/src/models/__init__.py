"""
ML Service Models

ML 모델 메타데이터 및 사기 케이스 관리를 위한 데이터 모델
"""

from .ml_model import MLModel
from .fraud_case import FraudCase

__all__ = ["MLModel", "FraudCase"]
