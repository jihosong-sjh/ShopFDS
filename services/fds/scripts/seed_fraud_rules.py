"""
사기 탐지 룰 초기 데이터 시드 스크립트

30개의 실전 사기 탐지 룰을 데이터베이스에 삽입합니다.

**실행 방법**:
    cd services/fds
    python scripts/seed_fraud_rules.py

**주의**:
    이미 룰이 존재하는 경우 건너뜁니다 (중복 방지).
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from sqlalchemy import select
from src.models import init_db, close_db, get_async_session_maker
from src.models.fraud_rule import FraudRule, RuleCategory


# === 30개 실전 룰 정의 ===

FRAUD_RULES = [
    # === Payment Rules (결제 관련 10개) ===
    {
        "rule_name": "P1: 테스트 카드 사용 감지",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "알려진 테스트 카드 번호를 사용한 거래를 차단합니다.",
        "rule_logic": {"type": "test_card_check", "action": "block"},
        "risk_score": 100,
        "priority": 100,
        "is_active": True,
    },
    {
        "rule_name": "P2: 카드 BIN 국가 불일치",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "카드 발급 국가와 청구 국가가 불일치하는 경우 탐지합니다.",
        "rule_logic": {"type": "bin_country_mismatch", "action": "manual_review"},
        "risk_score": 60,
        "priority": 85,
        "is_active": True,
    },
    {
        "rule_name": "P3: 고액 첫 거래",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "신규 사용자가 100만원 이상의 고액 거래를 시도하는 경우 차단합니다.",
        "rule_logic": {
            "type": "high_amount_first_transaction",
            "threshold": 1000000,
            "action": "block",
        },
        "risk_score": 80,
        "priority": 90,
        "is_active": True,
    },
    {
        "rule_name": "P4: 카드 Velocity Check",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "10분 내 동일 카드로 3회 이상 거래 시도 시 탐지합니다.",
        "rule_logic": {
            "type": "card_velocity",
            "window_seconds": 600,
            "max_transactions": 3,
            "action": "manual_review",
        },
        "risk_score": 70,
        "priority": 80,
        "is_active": True,
    },
    {
        "rule_name": "P5: 카드 번호 Brute Force",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "카드 번호 입력을 3회 이상 실패 후 성공하는 경우 차단합니다.",
        "rule_logic": {
            "type": "card_number_brute_force",
            "max_failures": 3,
            "action": "block",
        },
        "risk_score": 90,
        "priority": 95,
        "is_active": True,
    },
    {
        "rule_name": "P6: CVV Brute Force",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "CVV 입력을 3회 이상 실패 후 성공하는 경우 차단합니다.",
        "rule_logic": {"type": "cvv_brute_force", "max_failures": 3, "action": "block"},
        "risk_score": 95,
        "priority": 95,
        "is_active": True,
    },
    {
        "rule_name": "P7: 만료된 카드 사용",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "만료된 카드를 사용하는 경우 차단합니다.",
        "rule_logic": {"type": "expired_card", "action": "block"},
        "risk_score": 100,
        "priority": 100,
        "is_active": False,  # 결제 프로세서에서 이미 차단하므로 비활성화
    },
    {
        "rule_name": "P8: 정확한 반올림 금액",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "5만원, 10만원 등 정확히 나누어 떨어지는 금액으로 거래 시 자동화 의심.",
        "rule_logic": {
            "type": "round_number_amount",
            "modulo": 10000,
            "min_amount": 50000,
            "action": "warning",
        },
        "risk_score": 40,
        "priority": 30,
        "is_active": True,
    },
    {
        "rule_name": "P9: 비정상적으로 높은 금액",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "300만원 이상의 비정상적으로 높은 금액의 거래를 탐지합니다.",
        "rule_logic": {
            "type": "abnormally_high_amount",
            "threshold": 3000000,
            "action": "manual_review",
        },
        "risk_score": 75,
        "priority": 70,
        "is_active": True,
    },
    {
        "rule_name": "P10: 사기 BIN 리스트",
        "rule_category": RuleCategory.PAYMENT,
        "rule_description": "알려진 사기 BIN 리스트에 포함된 카드를 차단합니다.",
        "rule_logic": {"type": "fraud_bin_list", "action": "block"},
        "risk_score": 100,
        "priority": 100,
        "is_active": True,
    },
    # === Account Rules (계정 탈취 관련 10개) ===
    {
        "rule_name": "A1: 비밀번호 Brute Force",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "1분 내 비밀번호를 5회 이상 실패한 경우 차단합니다.",
        "rule_logic": {
            "type": "password_brute_force",
            "window_seconds": 60,
            "max_failures": 5,
            "action": "block",
        },
        "risk_score": 100,
        "priority": 100,
        "is_active": True,
    },
    {
        "rule_name": "A2: 세션 하이재킹",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "10분 이내에 IP 주소가 급격히 변경된 경우 탐지합니다.",
        "rule_logic": {
            "type": "session_hijacking",
            "window_seconds": 600,
            "action": "manual_review",
        },
        "risk_score": 85,
        "priority": 90,
        "is_active": True,
    },
    {
        "rule_name": "A3: 로그인 후 즉시 결제",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "로그인 후 30초 이내에 결제를 시도하는 경우 탐지합니다.",
        "rule_logic": {
            "type": "rapid_checkout",
            "window_seconds": 30,
            "action": "manual_review",
        },
        "risk_score": 65,
        "priority": 60,
        "is_active": True,
    },
    {
        "rule_name": "A4: 동일 IP 다중 계정",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "1시간 내 동일 IP에서 5명 이상의 계정이 사용되는 경우 탐지합니다.",
        "rule_logic": {
            "type": "multiple_accounts_same_ip",
            "window_seconds": 3600,
            "max_users": 5,
            "action": "manual_review",
        },
        "risk_score": 70,
        "priority": 70,
        "is_active": True,
    },
    {
        "rule_name": "A5: 디바이스 ID 불일치",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "알 수 없는 디바이스에서 로그인하는 경우 탐지합니다.",
        "rule_logic": {"type": "device_mismatch", "action": "manual_review"},
        "risk_score": 50,
        "priority": 50,
        "is_active": True,
    },
    {
        "rule_name": "A6: User-Agent 변조",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "User-Agent에 봇/크롤러 패턴이 감지되는 경우 탐지합니다.",
        "rule_logic": {
            "type": "user_agent_spoofing",
            "suspicious_patterns": [
                "bot",
                "crawler",
                "spider",
                "curl",
                "wget",
                "python-requests",
            ],
            "action": "manual_review",
        },
        "risk_score": 60,
        "priority": 55,
        "is_active": True,
    },
    {
        "rule_name": "A7: 신규 계정 즉시 결제",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "계정 생성 후 10분 이내에 결제를 시도하는 경우 탐지합니다.",
        "rule_logic": {
            "type": "new_account_immediate_purchase",
            "window_seconds": 600,
            "action": "manual_review",
        },
        "risk_score": 75,
        "priority": 75,
        "is_active": True,
    },
    {
        "rule_name": "A8: 해외 IP 로그인",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "해외 IP에서 로그인하는 경우 탐지합니다.",
        "rule_logic": {
            "type": "foreign_ip_login",
            "allowed_countries": ["KR"],
            "action": "manual_review",
        },
        "risk_score": 55,
        "priority": 50,
        "is_active": True,
    },
    {
        "rule_name": "A9: 패스워드 변경 후 결제",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "패스워드 변경 후 30분 이내에 결제를 시도하는 경우 탐지합니다.",
        "rule_logic": {
            "type": "password_change_then_purchase",
            "window_seconds": 1800,
            "action": "manual_review",
        },
        "risk_score": 70,
        "priority": 65,
        "is_active": True,
    },
    {
        "rule_name": "A10: 로그인 실패 후 성공",
        "rule_category": RuleCategory.ACCOUNT,
        "rule_description": "로그인을 3회 이상 실패 후 성공하는 경우 차단합니다.",
        "rule_logic": {
            "type": "multiple_failed_logins",
            "max_failures": 3,
            "action": "block",
        },
        "risk_score": 80,
        "priority": 85,
        "is_active": True,
    },
    # === Shipping Rules (배송지 사기 관련 10개) ===
    {
        "rule_name": "S1: 화물 전달 업체 주소",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "화물 전달 업체 주소로 배송하는 경우 차단합니다.",
        "rule_logic": {"type": "freight_forwarder", "action": "block"},
        "risk_score": 85,
        "priority": 90,
        "is_active": True,
    },
    {
        "rule_name": "S2: 일회용 이메일 사용",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "일회용 이메일 도메인을 사용하는 경우 차단합니다.",
        "rule_logic": {"type": "disposable_email", "action": "block"},
        "risk_score": 90,
        "priority": 95,
        "is_active": True,
    },
    {
        "rule_name": "S3: 배송 국가-IP 불일치",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "배송 국가와 IP 국가가 불일치하는 경우 탐지합니다.",
        "rule_logic": {"type": "shipping_ip_mismatch", "action": "manual_review"},
        "risk_score": 60,
        "priority": 65,
        "is_active": True,
    },
    {
        "rule_name": "S4: PO Box 배송지",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "PO Box(사서함)로 배송하는 경우 탐지합니다.",
        "rule_logic": {"type": "po_box", "action": "manual_review"},
        "risk_score": 70,
        "priority": 70,
        "is_active": True,
    },
    {
        "rule_name": "S5: 불완전한 주소",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "주소가 15자 미만으로 불완전한 경우 탐지합니다.",
        "rule_logic": {
            "type": "incomplete_address",
            "min_length": 15,
            "action": "manual_review",
        },
        "risk_score": 50,
        "priority": 40,
        "is_active": True,
    },
    {
        "rule_name": "S6: 동일 배송지 다중 계정",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "24시간 내 동일 배송지로 3명 이상이 주문하는 경우 탐지합니다.",
        "rule_logic": {
            "type": "multiple_accounts_same_shipping",
            "window_seconds": 86400,
            "max_users": 3,
            "action": "manual_review",
        },
        "risk_score": 80,
        "priority": 75,
        "is_active": True,
    },
    {
        "rule_name": "S7: 동일 카드 다중 배송지",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "24시간 내 동일 카드로 3개 이상 배송지로 주문하는 경우 탐지합니다.",
        "rule_logic": {
            "type": "multiple_shipping_same_card",
            "window_seconds": 86400,
            "max_addresses": 3,
            "action": "manual_review",
        },
        "risk_score": 75,
        "priority": 70,
        "is_active": True,
    },
    {
        "rule_name": "S8: 사기 주소 리스트",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "알려진 사기 주소 리스트에 포함된 경우 차단합니다.",
        "rule_logic": {"type": "fraud_address_list", "action": "block"},
        "risk_score": 100,
        "priority": 100,
        "is_active": True,
    },
    {
        "rule_name": "S9: 배송지-청구지 불일치",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "배송 국가와 청구 국가가 불일치하는 경우 탐지합니다.",
        "rule_logic": {"type": "shipping_billing_mismatch", "action": "manual_review"},
        "risk_score": 55,
        "priority": 55,
        "is_active": True,
    },
    {
        "rule_name": "S10: 고위험 국가 배송",
        "rule_category": RuleCategory.SHIPPING,
        "rule_description": "고위험 국가(NG, GH, PK 등)로 배송하는 경우 탐지합니다.",
        "rule_logic": {
            "type": "high_risk_country",
            "high_risk_countries": ["NG", "GH", "PK", "ID", "VN"],
            "action": "manual_review",
        },
        "risk_score": 65,
        "priority": 60,
        "is_active": True,
    },
]


async def seed_fraud_rules():
    """사기 탐지 룰 초기 데이터 삽입"""
    print("[INFO] Starting fraud rules seed script...")

    # 데이터베이스 초기화
    await init_db()

    # 세션 생성
    SessionLocal = get_async_session_maker()
    async with SessionLocal() as db:
        inserted_count = 0
        skipped_count = 0

        for rule_data in FRAUD_RULES:
            # 동일 이름의 룰이 이미 존재하는지 확인
            query = select(FraudRule).where(
                FraudRule.rule_name == rule_data["rule_name"]
            )
            result = await db.execute(query)
            existing_rule = result.scalar_one_or_none()

            if existing_rule:
                print(f"[SKIP] Rule already exists: {rule_data['rule_name']}")
                skipped_count += 1
                continue

            # 새 룰 생성
            rule = FraudRule(**rule_data)
            db.add(rule)
            inserted_count += 1
            print(
                f"[OK] Inserted: {rule_data['rule_name']} (priority={rule_data['priority']}, risk_score={rule_data['risk_score']})"
            )

        # 커밋
        await db.commit()

    # 데이터베이스 종료
    await close_db()

    print("\n[SUMMARY]")
    print(f"  Inserted: {inserted_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total: {len(FRAUD_RULES)}")
    print("\n[DONE] Seed script completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_fraud_rules())
