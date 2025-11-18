"""
사기 탐지 룰 엔진 (Fraud Rule Engine)

실전 사기 패턴 30개 룰을 적용하여 명백한 사기 패턴을 자동 차단합니다.

**룰 카테고리**:
- Payment (결제): 테스트 카드, BIN 불일치, 금액 이상 등 10개
- Account (계정): 비밀번호 실패, 세션 하이재킹, 계정 탈취 등 10개
- Shipping (배송지): 화물 전달 주소, 일회용 이메일, 배송지 사기 등 10개

**처리 우선순위**:
1. BLOCK (차단): 100점, 즉시 거래 차단
2. MANUAL_REVIEW (수동 검토): 50-80점, 검토 큐 추가
3. WARNING (경고): 30-50점, 위험 점수만 증가
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import re
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as aioredis

from ..models.fraud_rule import RuleCategory
from ..models.rule_execution import RuleExecution


class RuleAction:
    """룰 액션 정의"""

    BLOCK = "block"  # 즉시 차단
    MANUAL_REVIEW = "manual_review"  # 수동 검토 필요
    WARNING = "warning"  # 경고만 표시


class RuleResult:
    """룰 실행 결과"""

    def __init__(
        self,
        rule_id: UUID,
        rule_name: str,
        rule_category: RuleCategory,
        matched: bool,
        risk_score: int,
        action: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_category = rule_category
        self.matched = matched
        self.risk_score = risk_score
        self.action = action
        self.description = description
        self.metadata = metadata or {}


class TransactionData:
    """거래 데이터 (룰 평가용)"""

    def __init__(
        self,
        transaction_id: UUID,
        user_id: UUID,
        user_email: str,
        card_number: str,
        card_bin: str,
        card_last4: str,
        amount: Decimal,
        currency: str,
        ip_address: str,
        user_agent: str,
        shipping_address: str,
        shipping_city: str,
        shipping_country: str,
        billing_country: str,
        device_id: Optional[str] = None,
        session_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.user_email = user_email
        self.card_number = card_number
        self.card_bin = card_bin
        self.card_last4 = card_last4
        self.amount = amount
        self.currency = currency
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.shipping_address = shipping_address
        self.shipping_city = shipping_city
        self.shipping_country = shipping_country
        self.billing_country = billing_country
        self.device_id = device_id
        self.session_id = session_id
        self.created_at = created_at or datetime.utcnow()


class FraudRuleEngine:
    """
    실전 사기 탐지 룰 엔진

    30개 룰을 우선순위에 따라 실행하여 사기 패턴을 탐지합니다.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: aioredis.Redis,
        test_cards: List[str],
        freight_forwarders: List[Dict[str, Any]],
        disposable_email_domains: List[str],
    ):
        """
        Args:
            db: 데이터베이스 세션
            redis: Redis 클라이언트
            test_cards: 테스트 카드 번호 리스트
            freight_forwarders: 화물 전달 업체 주소 리스트
            disposable_email_domains: 일회용 이메일 도메인 리스트
        """
        self.db = db
        self.redis = redis
        self.test_cards = set(test_cards)
        self.freight_forwarders = freight_forwarders
        self.disposable_email_domains = set(disposable_email_domains)

    async def evaluate(
        self, transaction: TransactionData
    ) -> Tuple[List[RuleResult], int, str]:
        """
        거래를 평가하여 사기 패턴 탐지

        Args:
            transaction: 거래 데이터

        Returns:
            Tuple[List[RuleResult], int, str]:
                - 매칭된 룰 결과 리스트
                - 총 위험 점수
                - 최종 액션 (block/manual_review/allow)
        """
        results: List[RuleResult] = []

        # === Payment Rules (결제 관련 룰 10개) ===
        results.extend(await self._evaluate_payment_rules(transaction))

        # === Account Rules (계정 탈취 관련 룰 10개) ===
        results.extend(await self._evaluate_account_rules(transaction))

        # === Shipping Rules (배송지 사기 관련 룰 10개) ===
        results.extend(await self._evaluate_shipping_rules(transaction))

        # 총 위험 점수 계산
        total_risk_score = sum(r.risk_score for r in results if r.matched)

        # 최종 액션 결정 (우선순위: BLOCK > MANUAL_REVIEW > WARNING)
        final_action = "allow"
        for result in results:
            if result.matched and result.action == RuleAction.BLOCK:
                final_action = "block"
                break
            elif result.matched and result.action == RuleAction.MANUAL_REVIEW:
                final_action = "manual_review"

        return results, total_risk_score, final_action

    # ========================================================================
    # Payment Rules (결제 관련 룰 10개)
    # ========================================================================

    async def _evaluate_payment_rules(self, tx: TransactionData) -> List[RuleResult]:
        """결제 관련 룰 10개 평가"""
        results = []

        # P1. 테스트 카드 사용 감지
        results.append(await self._rule_test_card(tx))

        # P2. 카드 BIN과 국가 불일치
        results.append(await self._rule_bin_country_mismatch(tx))

        # P3. 고액 첫 거래 (신규 사용자가 100만원 이상)
        results.append(await self._rule_high_amount_first_transaction(tx))

        # P4. 짧은 시간 내 동일 카드 반복 사용 (10분 내 3회)
        results.append(await self._rule_card_velocity(tx))

        # P5. 카드 번호 입력 여러 번 실패 후 성공
        results.append(await self._rule_card_number_brute_force(tx))

        # P6. CVV 여러 번 실패 후 성공
        results.append(await self._rule_cvv_brute_force(tx))

        # P7. 만료된 카드 사용
        results.append(await self._rule_expired_card(tx))

        # P8. 금액이 정확히 반올림된 값 (5000원, 10000원 등 - 자동화 의심)
        results.append(await self._rule_round_number_amount(tx))

        # P9. 비정상적으로 높은 금액 (300만원 이상)
        results.append(await self._rule_abnormally_high_amount(tx))

        # P10. BIN이 알려진 사기 BIN 리스트에 포함
        results.append(await self._rule_fraud_bin_list(tx))

        return results

    async def _rule_test_card(self, tx: TransactionData) -> RuleResult:
        """P1. 테스트 카드 사용 감지 (100% 차단)"""
        rule_name = "P1: 테스트 카드 사용"
        matched = tx.card_number in self.test_cards

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000001"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=100 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"테스트 카드 사용 감지: {tx.card_last4}" if matched else "정상",
            metadata={"card_last4": tx.card_last4} if matched else {},
        )

    async def _rule_bin_country_mismatch(self, tx: TransactionData) -> RuleResult:
        """P2. 카드 BIN과 청구 국가 불일치"""
        rule_name = "P2: 카드 BIN 국가 불일치"

        # BIN으로 카드 발급 국가 조회 (간단한 예시)
        bin_country = await self._get_bin_country(tx.card_bin)
        matched = bin_country and bin_country != tx.billing_country

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000002"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=60 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"카드 발급 국가({bin_country})와 청구 국가({tx.billing_country}) 불일치"
            if matched
            else "정상",
            metadata={"bin_country": bin_country, "billing_country": tx.billing_country}
            if matched
            else {},
        )

    async def _rule_high_amount_first_transaction(
        self, tx: TransactionData
    ) -> RuleResult:
        """P3. 고액 첫 거래 (신규 사용자가 100만원 이상)"""
        rule_name = "P3: 고액 첫 거래"

        # 사용자의 이전 거래 수 조회
        transaction_count = await self._get_user_transaction_count(tx.user_id)
        is_first_transaction = transaction_count == 0
        is_high_amount = tx.amount >= Decimal("1000000")

        matched = is_first_transaction and is_high_amount

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000003"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=80 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"신규 사용자의 첫 거래가 고액({tx.amount:,.0f}원)" if matched else "정상",
            metadata={
                "amount": float(tx.amount),
                "transaction_count": transaction_count,
            }
            if matched
            else {},
        )

    async def _rule_card_velocity(self, tx: TransactionData) -> RuleResult:
        """P4. 짧은 시간 내 동일 카드 반복 사용 (10분 내 3회)"""
        rule_name = "P4: 카드 Velocity Check"

        redis_key = f"card_velocity:{tx.card_last4}"
        count = await self.redis.incr(redis_key)

        if count == 1:
            await self.redis.expire(redis_key, 600)  # 10분 TTL

        matched = count > 3

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000004"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=70 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"10분 내 동일 카드({tx.card_last4}) {count}회 사용"
            if matched
            else "정상",
            metadata={"card_last4": tx.card_last4, "count": count} if matched else {},
        )

    async def _rule_card_number_brute_force(self, tx: TransactionData) -> RuleResult:
        """P5. 카드 번호 입력 여러 번 실패 후 성공"""
        rule_name = "P5: 카드 번호 Brute Force"

        redis_key = f"card_failures:{tx.user_id}"
        failure_count = await self.redis.get(redis_key)
        failure_count = int(failure_count) if failure_count else 0

        matched = failure_count >= 3

        # 성공 시 카운터 리셋
        if matched:
            await self.redis.delete(redis_key)

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000005"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=90 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"카드 번호 {failure_count}회 실패 후 성공" if matched else "정상",
            metadata={"failure_count": failure_count} if matched else {},
        )

    async def _rule_cvv_brute_force(self, tx: TransactionData) -> RuleResult:
        """P6. CVV 여러 번 실패 후 성공"""
        rule_name = "P6: CVV Brute Force"

        redis_key = f"cvv_failures:{tx.card_last4}"
        failure_count = await self.redis.get(redis_key)
        failure_count = int(failure_count) if failure_count else 0

        matched = failure_count >= 3

        if matched:
            await self.redis.delete(redis_key)

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000006"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=95 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"CVV {failure_count}회 실패 후 성공" if matched else "정상",
            metadata={"failure_count": failure_count} if matched else {},
        )

    async def _rule_expired_card(self, tx: TransactionData) -> RuleResult:
        """P7. 만료된 카드 사용"""
        rule_name = "P7: 만료된 카드 사용"

        # 이 로직은 결제 프로세서에서 이미 차단하지만, 이중 확인
        # metadata에 card_expiry가 있다고 가정
        matched = False  # 실제로는 tx.metadata에서 확인

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000007"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=100 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description="만료된 카드 사용" if matched else "정상",
            metadata={} if matched else {},
        )

    async def _rule_round_number_amount(self, tx: TransactionData) -> RuleResult:
        """P8. 금액이 정확히 반올림된 값 (5000원, 10000원 등 - 자동화 의심)"""
        rule_name = "P8: 정확한 반올림 금액"

        # 5000, 10000, 50000, 100000, ... 등 정확히 나누어 떨어지는 금액
        matched = tx.amount % 10000 == 0 and tx.amount >= 50000

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000008"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=40 if matched else 0,
            action=RuleAction.WARNING,
            description=f"정확한 반올림 금액({tx.amount:,.0f}원) - 자동화 의심" if matched else "정상",
            metadata={"amount": float(tx.amount)} if matched else {},
        )

    async def _rule_abnormally_high_amount(self, tx: TransactionData) -> RuleResult:
        """P9. 비정상적으로 높은 금액 (300만원 이상)"""
        rule_name = "P9: 비정상적으로 높은 금액"

        matched = tx.amount >= Decimal("3000000")

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000009"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=75 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"비정상적으로 높은 금액({tx.amount:,.0f}원)" if matched else "정상",
            metadata={"amount": float(tx.amount)} if matched else {},
        )

    async def _rule_fraud_bin_list(self, tx: TransactionData) -> RuleResult:
        """P10. BIN이 알려진 사기 BIN 리스트에 포함"""
        rule_name = "P10: 사기 BIN 리스트"

        # Redis에 사기 BIN 리스트 저장 (예시)
        matched = await self.redis.sismember("fraud_bins", tx.card_bin)

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000010"),
            rule_name=rule_name,
            rule_category=RuleCategory.PAYMENT,
            matched=matched,
            risk_score=100 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"사기 BIN({tx.card_bin}) 탐지" if matched else "정상",
            metadata={"card_bin": tx.card_bin} if matched else {},
        )

    # ========================================================================
    # Account Rules (계정 탈취 관련 룰 10개)
    # ========================================================================

    async def _evaluate_account_rules(self, tx: TransactionData) -> List[RuleResult]:
        """계정 탈취 관련 룰 10개 평가"""
        results = []

        # A1. 1분 내 비밀번호 5회 실패
        results.append(await self._rule_password_brute_force(tx))

        # A2. 세션 하이재킹 (IP 주소 급격한 변경)
        results.append(await self._rule_session_hijacking(tx))

        # A3. 로그인 후 즉시 결제 (30초 이내)
        results.append(await self._rule_rapid_checkout(tx))

        # A4. 여러 계정에서 동일 IP 사용
        results.append(await self._rule_multiple_accounts_same_ip(tx))

        # A5. 디바이스 ID 불일치 (기존 디바이스와 다름)
        results.append(await self._rule_device_mismatch(tx))

        # A6. User-Agent 변조 감지
        results.append(await self._rule_user_agent_spoofing(tx))

        # A7. 계정 생성 직후 결제 (10분 이내)
        results.append(await self._rule_new_account_immediate_purchase(tx))

        # A8. 비정상적인 로그인 위치 (해외 IP)
        results.append(await self._rule_foreign_ip_login(tx))

        # A9. 패스워드 변경 직후 결제
        results.append(await self._rule_password_change_then_purchase(tx))

        # A10. 다수의 실패한 로그인 후 성공
        results.append(await self._rule_multiple_failed_logins(tx))

        return results

    async def _rule_password_brute_force(self, tx: TransactionData) -> RuleResult:
        """A1. 1분 내 비밀번호 5회 실패"""
        rule_name = "A1: 비밀번호 Brute Force"

        redis_key = f"password_failures:{tx.user_id}"
        failure_count = await self.redis.get(redis_key)
        failure_count = int(failure_count) if failure_count else 0

        matched = failure_count >= 5

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000011"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=100 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"1분 내 비밀번호 {failure_count}회 실패" if matched else "정상",
            metadata={"failure_count": failure_count} if matched else {},
        )

    async def _rule_session_hijacking(self, tx: TransactionData) -> RuleResult:
        """A2. 세션 하이재킹 (IP 주소 급격한 변경)"""
        rule_name = "A2: 세션 하이재킹"

        # 마지막 IP와 현재 IP 비교
        redis_key = f"last_ip:{tx.user_id}"
        last_ip = await self.redis.get(redis_key)
        last_ip = last_ip.decode() if last_ip else None

        matched = False
        if last_ip and last_ip != tx.ip_address:
            # 10분 이내에 IP가 변경되었는지 확인
            redis_key_time = f"last_ip_time:{tx.user_id}"
            last_time = await self.redis.get(redis_key_time)
            if last_time:
                last_time = float(last_time.decode())
                time_diff = datetime.utcnow().timestamp() - last_time
                matched = time_diff < 600  # 10분 이내

        # IP 업데이트
        await self.redis.set(redis_key, tx.ip_address)
        await self.redis.set(
            f"last_ip_time:{tx.user_id}", datetime.utcnow().timestamp()
        )

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000012"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=85 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"IP 주소 급격한 변경: {last_ip} -> {tx.ip_address}"
            if matched
            else "정상",
            metadata={"last_ip": last_ip, "current_ip": tx.ip_address}
            if matched
            else {},
        )

    async def _rule_rapid_checkout(self, tx: TransactionData) -> RuleResult:
        """A3. 로그인 후 즉시 결제 (30초 이내)"""
        rule_name = "A3: 로그인 후 즉시 결제"

        redis_key = f"login_time:{tx.user_id}"
        login_time = await self.redis.get(redis_key)

        matched = False
        if login_time:
            login_time = float(login_time.decode())
            time_diff = datetime.utcnow().timestamp() - login_time
            matched = time_diff < 30  # 30초 이내

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000013"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=65 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"로그인 후 {time_diff:.0f}초 만에 결제" if matched else "정상",
            metadata={"time_diff_seconds": time_diff} if matched else {},
        )

    async def _rule_multiple_accounts_same_ip(self, tx: TransactionData) -> RuleResult:
        """A4. 여러 계정에서 동일 IP 사용"""
        rule_name = "A4: 동일 IP 다중 계정"

        redis_key = f"ip_users:{tx.ip_address}"
        await self.redis.sadd(redis_key, str(tx.user_id))
        await self.redis.expire(redis_key, 3600)  # 1시간 TTL

        user_count = await self.redis.scard(redis_key)
        matched = user_count > 5  # 1시간 내 동일 IP에서 5명 이상

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000014"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=70 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"동일 IP({tx.ip_address})에서 {user_count}명 사용"
            if matched
            else "정상",
            metadata={"ip_address": tx.ip_address, "user_count": user_count}
            if matched
            else {},
        )

    async def _rule_device_mismatch(self, tx: TransactionData) -> RuleResult:
        """A5. 디바이스 ID 불일치"""
        rule_name = "A5: 디바이스 ID 불일치"

        if not tx.device_id:
            return RuleResult(
                rule_id=UUID("00000000-0000-0000-0000-000000000015"),
                rule_name=rule_name,
                rule_category=RuleCategory.ACCOUNT,
                matched=False,
                risk_score=0,
                action=RuleAction.WARNING,
                description="정상",
                metadata={},
            )

        redis_key = f"known_devices:{tx.user_id}"
        is_known = await self.redis.sismember(redis_key, tx.device_id)

        matched = not is_known

        # 새 디바이스 등록
        if not is_known:
            await self.redis.sadd(redis_key, tx.device_id)

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000015"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=50 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"알 수 없는 디바이스({tx.device_id[:8]}...)" if matched else "정상",
            metadata={"device_id": tx.device_id} if matched else {},
        )

    async def _rule_user_agent_spoofing(self, tx: TransactionData) -> RuleResult:
        """A6. User-Agent 변조 감지"""
        rule_name = "A6: User-Agent 변조"

        # 간단한 휴리스틱: 알려진 봇 User-Agent 또는 비정상적인 패턴
        suspicious_patterns = [
            "bot",
            "crawler",
            "spider",
            "curl",
            "wget",
            "python-requests",
        ]
        matched = any(
            pattern in tx.user_agent.lower() for pattern in suspicious_patterns
        )

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000016"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=60 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"User-Agent 변조 의심: {tx.user_agent}" if matched else "정상",
            metadata={"user_agent": tx.user_agent} if matched else {},
        )

    async def _rule_new_account_immediate_purchase(
        self, tx: TransactionData
    ) -> RuleResult:
        """A7. 계정 생성 직후 결제 (10분 이내)"""
        rule_name = "A7: 신규 계정 즉시 결제"

        # 계정 생성 시간 조회 (데이터베이스 또는 Redis)
        redis_key = f"account_created_at:{tx.user_id}"
        created_at = await self.redis.get(redis_key)

        matched = False
        if created_at:
            created_at = float(created_at.decode())
            time_diff = datetime.utcnow().timestamp() - created_at
            matched = time_diff < 600  # 10분 이내

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000017"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=75 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"계정 생성 {time_diff/60:.0f}분 후 결제" if matched else "정상",
            metadata={"time_diff_minutes": time_diff / 60} if matched else {},
        )

    async def _rule_foreign_ip_login(self, tx: TransactionData) -> RuleResult:
        """A8. 비정상적인 로그인 위치 (해외 IP)"""
        rule_name = "A8: 해외 IP 로그인"

        # GeoIP로 국가 확인 (간단한 예시)
        ip_country = await self._get_ip_country(tx.ip_address)
        matched = ip_country and ip_country != "KR"  # 한국이 아닌 경우

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000018"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=55 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"해외 IP({ip_country}) 로그인" if matched else "정상",
            metadata={"ip_country": ip_country} if matched else {},
        )

    async def _rule_password_change_then_purchase(
        self, tx: TransactionData
    ) -> RuleResult:
        """A9. 패스워드 변경 직후 결제"""
        rule_name = "A9: 패스워드 변경 후 결제"

        redis_key = f"password_changed_at:{tx.user_id}"
        changed_at = await self.redis.get(redis_key)

        matched = False
        if changed_at:
            changed_at = float(changed_at.decode())
            time_diff = datetime.utcnow().timestamp() - changed_at
            matched = time_diff < 1800  # 30분 이내

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000019"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=70 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"패스워드 변경 {time_diff/60:.0f}분 후 결제" if matched else "정상",
            metadata={"time_diff_minutes": time_diff / 60} if matched else {},
        )

    async def _rule_multiple_failed_logins(self, tx: TransactionData) -> RuleResult:
        """A10. 다수의 실패한 로그인 후 성공"""
        rule_name = "A10: 로그인 실패 후 성공"

        redis_key = f"login_failures:{tx.user_id}"
        failure_count = await self.redis.get(redis_key)
        failure_count = int(failure_count) if failure_count else 0

        matched = failure_count >= 3

        # 성공 시 카운터 리셋
        if matched:
            await self.redis.delete(redis_key)

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000020"),
            rule_name=rule_name,
            rule_category=RuleCategory.ACCOUNT,
            matched=matched,
            risk_score=80 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"로그인 {failure_count}회 실패 후 성공" if matched else "정상",
            metadata={"failure_count": failure_count} if matched else {},
        )

    # ========================================================================
    # Shipping Rules (배송지 사기 관련 룰 10개)
    # ========================================================================

    async def _evaluate_shipping_rules(self, tx: TransactionData) -> List[RuleResult]:
        """배송지 사기 관련 룰 10개 평가"""
        results = []

        # S1. 화물 전달 업체 주소 (Freight Forwarder)
        results.append(await self._rule_freight_forwarder(tx))

        # S2. 일회용 이메일 도메인 사용
        results.append(await self._rule_disposable_email(tx))

        # S3. 배송 국가와 IP 국가 불일치
        results.append(await self._rule_shipping_ip_mismatch(tx))

        # S4. 배송지가 PO Box (사서함)
        results.append(await self._rule_po_box(tx))

        # S5. 배송지 주소가 불완전 (짧음)
        results.append(await self._rule_incomplete_address(tx))

        # S6. 동일 배송지로 여러 계정 주문
        results.append(await self._rule_multiple_accounts_same_shipping(tx))

        # S7. 동일 카드로 여러 배송지 주문
        results.append(await self._rule_multiple_shipping_same_card(tx))

        # S8. 배송지가 알려진 사기 주소 리스트에 포함
        results.append(await self._rule_fraud_address_list(tx))

        # S9. 배송지와 청구지 국가 불일치
        results.append(await self._rule_shipping_billing_mismatch(tx))

        # S10. 배송지가 고위험 국가
        results.append(await self._rule_high_risk_country(tx))

        return results

    async def _rule_freight_forwarder(self, tx: TransactionData) -> RuleResult:
        """S1. 화물 전달 업체 주소"""
        rule_name = "S1: 화물 전달 업체 주소"

        # 화물 전달 업체 리스트와 매칭
        matched = any(
            ff["address"].lower() in tx.shipping_address.lower()
            for ff in self.freight_forwarders
        )

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000021"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=85 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"화물 전달 업체 주소 탐지: {tx.shipping_address}" if matched else "정상",
            metadata={"shipping_address": tx.shipping_address} if matched else {},
        )

    async def _rule_disposable_email(self, tx: TransactionData) -> RuleResult:
        """S2. 일회용 이메일 도메인 사용"""
        rule_name = "S2: 일회용 이메일 사용"

        # 이메일 도메인 추출
        email_domain = tx.user_email.split("@")[-1].lower()
        matched = email_domain in self.disposable_email_domains

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000022"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=90 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"일회용 이메일 도메인 사용: {email_domain}" if matched else "정상",
            metadata={"email_domain": email_domain} if matched else {},
        )

    async def _rule_shipping_ip_mismatch(self, tx: TransactionData) -> RuleResult:
        """S3. 배송 국가와 IP 국가 불일치"""
        rule_name = "S3: 배송 국가-IP 불일치"

        ip_country = await self._get_ip_country(tx.ip_address)
        matched = ip_country and ip_country != tx.shipping_country

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000023"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=60 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"배송 국가({tx.shipping_country})와 IP 국가({ip_country}) 불일치"
            if matched
            else "정상",
            metadata={"shipping_country": tx.shipping_country, "ip_country": ip_country}
            if matched
            else {},
        )

    async def _rule_po_box(self, tx: TransactionData) -> RuleResult:
        """S4. 배송지가 PO Box (사서함)"""
        rule_name = "S4: PO Box 배송지"

        # PO Box 패턴 검색
        po_box_pattern = r"(p\.?\s*o\.?\s*box|post\s*office\s*box)"
        matched = bool(re.search(po_box_pattern, tx.shipping_address, re.IGNORECASE))

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000024"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=70 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"PO Box 배송지: {tx.shipping_address}" if matched else "정상",
            metadata={"shipping_address": tx.shipping_address} if matched else {},
        )

    async def _rule_incomplete_address(self, tx: TransactionData) -> RuleResult:
        """S5. 배송지 주소가 불완전 (짧음)"""
        rule_name = "S5: 불완전한 주소"

        # 주소 길이가 너무 짧으면 의심
        matched = len(tx.shipping_address) < 15

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000025"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=50 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"불완전한 주소({len(tx.shipping_address)}자): {tx.shipping_address}"
            if matched
            else "정상",
            metadata={"address_length": len(tx.shipping_address)} if matched else {},
        )

    async def _rule_multiple_accounts_same_shipping(
        self, tx: TransactionData
    ) -> RuleResult:
        """S6. 동일 배송지로 여러 계정 주문"""
        rule_name = "S6: 동일 배송지 다중 계정"

        # 배송지 해시 생성
        shipping_hash = hashlib.md5(tx.shipping_address.lower().encode()).hexdigest()
        redis_key = f"shipping_users:{shipping_hash}"

        await self.redis.sadd(redis_key, str(tx.user_id))
        await self.redis.expire(redis_key, 86400)  # 24시간 TTL

        user_count = await self.redis.scard(redis_key)
        matched = user_count > 3  # 24시간 내 동일 배송지로 3명 이상

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000026"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=80 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"동일 배송지로 {user_count}명 주문" if matched else "정상",
            metadata={"shipping_address": tx.shipping_address, "user_count": user_count}
            if matched
            else {},
        )

    async def _rule_multiple_shipping_same_card(
        self, tx: TransactionData
    ) -> RuleResult:
        """S7. 동일 카드로 여러 배송지 주문"""
        rule_name = "S7: 동일 카드 다중 배송지"

        shipping_hash = hashlib.md5(tx.shipping_address.lower().encode()).hexdigest()
        redis_key = f"card_shipping:{tx.card_last4}"

        await self.redis.sadd(redis_key, shipping_hash)
        await self.redis.expire(redis_key, 86400)  # 24시간 TTL

        shipping_count = await self.redis.scard(redis_key)
        matched = shipping_count > 3  # 24시간 내 동일 카드로 3개 이상 배송지

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000027"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=75 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"동일 카드({tx.card_last4})로 {shipping_count}개 배송지 주문"
            if matched
            else "정상",
            metadata={"card_last4": tx.card_last4, "shipping_count": shipping_count}
            if matched
            else {},
        )

    async def _rule_fraud_address_list(self, tx: TransactionData) -> RuleResult:
        """S8. 배송지가 알려진 사기 주소 리스트에 포함"""
        rule_name = "S8: 사기 주소 리스트"

        # Redis에 사기 주소 해시 저장
        shipping_hash = hashlib.md5(tx.shipping_address.lower().encode()).hexdigest()
        matched = await self.redis.sismember("fraud_addresses", shipping_hash)

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000028"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=100 if matched else 0,
            action=RuleAction.BLOCK if matched else RuleAction.WARNING,
            description=f"사기 주소 탐지: {tx.shipping_address}" if matched else "정상",
            metadata={"shipping_address": tx.shipping_address} if matched else {},
        )

    async def _rule_shipping_billing_mismatch(self, tx: TransactionData) -> RuleResult:
        """S9. 배송지와 청구지 국가 불일치"""
        rule_name = "S9: 배송지-청구지 불일치"

        matched = tx.shipping_country != tx.billing_country

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000029"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=55 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"배송 국가({tx.shipping_country})와 청구 국가({tx.billing_country}) 불일치"
            if matched
            else "정상",
            metadata={
                "shipping_country": tx.shipping_country,
                "billing_country": tx.billing_country,
            }
            if matched
            else {},
        )

    async def _rule_high_risk_country(self, tx: TransactionData) -> RuleResult:
        """S10. 배송지가 고위험 국가"""
        rule_name = "S10: 고위험 국가 배송"

        # 고위험 국가 리스트 (예시)
        high_risk_countries = {"NG", "GH", "PK", "ID", "VN"}  # ISO 2자 코드
        matched = tx.shipping_country in high_risk_countries

        return RuleResult(
            rule_id=UUID("00000000-0000-0000-0000-000000000030"),
            rule_name=rule_name,
            rule_category=RuleCategory.SHIPPING,
            matched=matched,
            risk_score=65 if matched else 0,
            action=RuleAction.MANUAL_REVIEW if matched else RuleAction.WARNING,
            description=f"고위험 국가 배송: {tx.shipping_country}" if matched else "정상",
            metadata={"shipping_country": tx.shipping_country} if matched else {},
        )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _get_bin_country(self, card_bin: str) -> Optional[str]:
        """카드 BIN으로 발급 국가 조회 (Mock)"""
        # 실제로는 BIN Database API 호출
        bin_country_map = {
            "123456": "US",
            "411111": "US",  # 테스트 카드
            "543210": "KR",
        }
        return bin_country_map.get(card_bin, "KR")

    async def _get_ip_country(self, ip_address: str) -> Optional[str]:
        """IP 주소로 국가 조회 (Mock)"""
        # 실제로는 MaxMind GeoIP2 또는 외부 API 호출
        if ip_address.startswith("127.") or ip_address.startswith("192.168."):
            return "KR"  # 로컬 IP는 한국으로 가정
        return "US"  # Mock

    async def _get_user_transaction_count(self, user_id: UUID) -> int:
        """사용자의 이전 거래 수 조회"""
        # Redis 캐시 확인
        redis_key = f"user_tx_count:{user_id}"
        count = await self.redis.get(redis_key)

        if count:
            return int(count.decode())

        # 데이터베이스 조회 (여기서는 0 반환 - Mock)
        return 0

    async def save_rule_executions(
        self, transaction_id: UUID, results: List[RuleResult]
    ) -> List[RuleExecution]:
        """룰 실행 결과를 데이터베이스에 저장"""
        executions = []

        for result in results:
            if result.matched:  # 매칭된 룰만 저장
                execution = RuleExecution(
                    transaction_id=transaction_id,
                    rule_id=result.rule_id,
                    matched=True,
                    metadata={
                        "rule_name": result.rule_name,
                        "rule_category": result.rule_category.value,
                        "risk_score": result.risk_score,
                        "action": result.action,
                        "description": result.description,
                        **result.metadata,
                    },
                )
                self.db.add(execution)
                executions.append(execution)

        await self.db.flush()
        return executions
