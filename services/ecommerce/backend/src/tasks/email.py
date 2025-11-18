"""
Email Tasks for Ecommerce Service

이 모듈은 이메일 발송을 위한 Celery 비동기 작업을 포함합니다.
"""

from src.tasks import app
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    name="src.tasks.email.send_order_confirmation_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_order_confirmation_email(
    self, order_id: str, user_email: str, order_details: Dict[str, Any]
):
    """
    주문 확인 이메일 발송

    Args:
        self: Celery 작업 인스턴스 (bind=True로 자동 전달)
        order_id: 주문 ID
        user_email: 사용자 이메일
        order_details: 주문 상세 정보 (items, total_amount, shipping_address 등)

    Returns:
        Dict[str, Any]: 발송 결과 (success, message, timestamp)
    """
    try:
        logger.info(
            f"[Celery] Sending order confirmation email to {user_email} for order {order_id}"
        )

        # 실제 이메일 발송 로직 (예: SendGrid, AWS SES, SMTP 등)
        # 여기서는 플레이스홀더로 대체
        _email_content = _generate_order_confirmation_email(order_id, order_details)

        # TODO: 실제 이메일 발송 구현
        # send_email_via_smtp(user_email, "주문 확인", _email_content)

        logger.info(f"[SUCCESS] Order confirmation email sent to {user_email}")

        return {
            "success": True,
            "message": f"Order confirmation email sent to {user_email}",
            "order_id": order_id,
            "timestamp": self.request.id,
        }

    except Exception as exc:
        logger.error(f"[FAIL] Failed to send order confirmation email: {exc}")

        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.warning(
                f"[RETRY] Retrying email send (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

        # 최대 재시도 횟수 초과 시 실패 처리
        return {
            "success": False,
            "message": f"Failed to send email after {self.max_retries} retries",
            "error": str(exc),
        }


@app.task(
    bind=True,
    name="src.tasks.email.send_password_reset_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_password_reset_email(self, user_email: str, reset_token: str):
    """
    비밀번호 재설정 이메일 발송

    Args:
        self: Celery 작업 인스턴스
        user_email: 사용자 이메일
        reset_token: 비밀번호 재설정 토큰

    Returns:
        Dict[str, Any]: 발송 결과
    """
    try:
        logger.info(f"[Celery] Sending password reset email to {user_email}")

        # 비밀번호 재설정 이메일 내용 생성
        _email_content = _generate_password_reset_email(reset_token)

        # TODO: 실제 이메일 발송 구현
        # send_email_via_smtp(user_email, "비밀번호 재설정", _email_content)

        logger.info(f"[SUCCESS] Password reset email sent to {user_email}")

        return {
            "success": True,
            "message": f"Password reset email sent to {user_email}",
            "timestamp": self.request.id,
        }

    except Exception as exc:
        logger.error(f"[FAIL] Failed to send password reset email: {exc}")

        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.warning(
                f"[RETRY] Retrying password reset email (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

        return {
            "success": False,
            "message": f"Failed to send email after {self.max_retries} retries",
            "error": str(exc),
        }


def _generate_order_confirmation_email(
    order_id: str, order_details: Dict[str, Any]
) -> str:
    """주문 확인 이메일 HTML 내용 생성"""
    return f"""
    <html>
    <body>
        <h1>주문이 완료되었습니다!</h1>
        <p>주문 번호: {order_id}</p>
        <p>총 금액: {order_details.get('total_amount', 0):,}원</p>
        <p>배송지: {order_details.get('shipping_address', 'N/A')}</p>
        <h3>주문 상품:</h3>
        <ul>
            {''.join([f"<li>{item['name']} x {item['quantity']}</li>" for item in order_details.get('items', [])])}
        </ul>
        <p>감사합니다.</p>
    </body>
    </html>
    """


def _generate_password_reset_email(reset_token: str) -> str:
    """비밀번호 재설정 이메일 HTML 내용 생성"""
    reset_url = f"http://localhost:3000/reset-password?token={reset_token}"
    return f"""
    <html>
    <body>
        <h1>비밀번호 재설정 요청</h1>
        <p>아래 링크를 클릭하여 비밀번호를 재설정하세요:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>이 링크는 24시간 동안 유효합니다.</p>
        <p>요청하지 않으셨다면 이 이메일을 무시하세요.</p>
    </body>
    </html>
    """
