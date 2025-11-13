"""
FDS 평가 API 통합 테스트

정상 거래 시나리오를 테스트합니다 (T050).
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timezone
from uuid import uuid4


def test_normal_transaction_should_be_approved():
    """
    테스트 시나리오: 정상 거래 - 자동 승인

    조건:
    - 거래 금액: 50,000원 (정상 범위)
    - 디바이스: desktop (정상)
    - IP: 정상 IP

    기대 결과:
    - risk_score: 0-30점
    - risk_level: "low"
    - decision: "approve"
    - evaluation_time_ms: 100ms 이내
    """
    # 테스트 데이터
    request_data = {
        "transaction_id": str(uuid4()),
        "user_id": str(uuid4()),
        "order_id": str(uuid4()),
        "amount": 50000.00,
        "currency": "KRW",
        "ip_address": "211.234.56.78",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
        "device_fingerprint": {
            "device_type": "desktop",
            "os": "Windows 10",
            "browser": "Chrome 120.0"
        },
        "shipping_info": {
            "name": "홍길동",
            "address": "서울특별시 강남구 테헤란로 123",
            "phone": "010-1234-5678"
        },
        "payment_info": {
            "method": "credit_card",
            "card_bin": "541234",
            "card_last_four": "5678"
        },
        "session_context": None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # FDS API 호출 (직접 테스트)
    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app) as client:
        headers = {
            "X-Service-Token": "dev-service-token-12345"
        }

        response = client.post(
            "/internal/fds/evaluate",
            json=request_data,
            headers=headers
        )

        # 검증
        assert response.status_code == 200

        result = response.json()

        # 위험 점수 확인
        assert 0 <= result["risk_score"] <= 30, f"예상 위험 점수: 0-30, 실제: {result['risk_score']}"

        # 위험 수준 확인
        assert result["risk_level"] == "low", f"예상 위험 수준: low, 실제: {result['risk_level']}"

        # 의사결정 확인
        assert result["decision"] == "approve", f"예상 결정: approve, 실제: {result['decision']}"

        # 평가 시간 확인 (100ms 이내)
        eval_time = result["evaluation_metadata"]["evaluation_time_ms"]
        assert eval_time < 100, f"예상 평가 시간: <100ms, 실제: {eval_time}ms"

        # 권장 조치 확인
        assert result["recommended_action"]["action"] == "approve"
        assert result["recommended_action"]["additional_auth_required"] is False

        print("[PASS] 정상 거래 자동 승인 테스트 통과")
        print(f"  - 위험 점수: {result['risk_score']}")
        print(f"  - 평가 시간: {eval_time}ms")


def test_high_amount_transaction_should_be_low_risk():
    """
    테스트 시나리오: 고액 거래 (100만원 이상) - 약간의 위험 점수

    조건:
    - 거래 금액: 1,500,000원 (고액)
    - 디바이스: desktop (정상)

    기대 결과:
    - risk_score: 0-30점 (여전히 자동 승인 범위)
    - risk_level: "low"
    - decision: "approve"
    """
    request_data = {
        "transaction_id": str(uuid4()),
        "user_id": str(uuid4()),
        "order_id": str(uuid4()),
        "amount": 1500000.00,
        "currency": "KRW",
        "ip_address": "211.234.56.78",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
        "device_fingerprint": {
            "device_type": "desktop",
            "os": None,
            "browser": None
        },
        "shipping_info": {
            "name": "홍길동",
            "address": "서울특별시 강남구 테헤란로 123",
            "phone": "010-1234-5678"
        },
        "payment_info": {
            "method": "credit_card",
            "card_bin": "541234",
            "card_last_four": "5678"
        },
        "session_context": None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app) as client:
        headers = {"X-Service-Token": "dev-service-token-12345"}

        response = client.post(
            "/internal/fds/evaluate",
            json=request_data,
            headers=headers
        )

        assert response.status_code == 200

        result = response.json()

        # 고액 거래는 약간의 위험 점수 추가 (15점)
        assert result["risk_score"] > 10, "고액 거래는 기본 점수보다 높아야 함"
        assert result["risk_score"] <= 30, "여전히 자동 승인 범위 내여야 함"

        # 여전히 자동 승인
        assert result["risk_level"] == "low"
        assert result["decision"] == "approve"

        print("[PASS] 고액 거래 자동 승인 테스트 통과")
        print(f"  - 위험 점수: {result['risk_score']}")


def test_unknown_device_should_be_low_risk():
    """
    테스트 시나리오: 알 수 없는 디바이스 - 약간의 위험 점수

    조건:
    - 거래 금액: 50,000원 (정상 범위)
    - 디바이스: unknown (식별 불가)

    기대 결과:
    - risk_score: 0-30점 (자동 승인 범위)
    - risk_level: "low"
    - decision: "approve"
    """
    request_data = {
        "transaction_id": str(uuid4()),
        "user_id": str(uuid4()),
        "order_id": str(uuid4()),
        "amount": 50000.00,
        "currency": "KRW",
        "ip_address": "211.234.56.78",
        "user_agent": "UnknownBot/1.0",
        "device_fingerprint": {
            "device_type": "unknown",
            "os": None,
            "browser": None
        },
        "shipping_info": {
            "name": "홍길동",
            "address": "서울특별시 강남구 테헤란로 123",
            "phone": "010-1234-5678"
        },
        "payment_info": {
            "method": "credit_card",
            "card_bin": "541234",
            "card_last_four": "5678"
        },
        "session_context": None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app) as client:
        headers = {"X-Service-Token": "dev-service-token-12345"}

        response = client.post(
            "/internal/fds/evaluate",
            json=request_data,
            headers=headers
        )

        assert response.status_code == 200

        result = response.json()

        # 알 수 없는 디바이스는 약간의 위험 점수 추가
        assert result["risk_score"] > 0
        assert result["risk_score"] <= 30

        # 여전히 자동 승인
        assert result["risk_level"] == "low"
        assert result["decision"] == "approve"

        print("[PASS] 알 수 없는 디바이스 자동 승인 테스트 통과")
        print(f"  - 위험 점수: {result['risk_score']}")


if __name__ == "__main__":
    print("=" * 60)
    print("FDS 정상 거래 시나리오 검증 (T050)")
    print("=" * 60)
    print()

    test_normal_transaction_should_be_approved()
    print()
    test_high_amount_transaction_should_be_low_risk()
    print()
    test_unknown_device_should_be_low_risk()
    print()

    print("=" * 60)
    print("[SUCCESS] 모든 테스트 통과!")
    print("=" * 60)
