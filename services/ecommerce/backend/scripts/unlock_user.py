"""
사용자 계정 잠금 해제 스크립트

로그인 실패로 잠긴 계정의 failed_login_attempts를 0으로 초기화합니다.
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from src.models.user import User
from src.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def unlock_user(email: str):
    """사용자 계정 잠금 해제"""
    async with AsyncSessionLocal() as session:
        # 사용자 조회
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if not user:
            print(f"[ERROR] 사용자를 찾을 수 없습니다: {email}")
            return False

        print(f"[INFO] 사용자 정보:")
        print(f"  - 이메일: {user.email}")
        print(f"  - 이름: {user.name}")
        print(f"  - 역할: {user.role}")
        print(f"  - 상태: {user.status}")
        print(f"  - 로그인 실패 횟수: {user.failed_login_attempts}")

        if user.failed_login_attempts == 0:
            print("[INFO] 계정이 잠겨있지 않습니다.")
            return True

        # 잠금 해제
        await session.execute(
            update(User)
            .where(User.email == email)
            .values(failed_login_attempts=0)
        )
        await session.commit()

        print(f"[SUCCESS] 계정 잠금 해제 완료: {email}")
        return True


async def unlock_all_users():
    """모든 사용자 계정 잠금 해제"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.failed_login_attempts > 0)
        )
        locked_users = result.scalars().all()

        if not locked_users:
            print("[INFO] 잠긴 계정이 없습니다.")
            return

        print(f"[INFO] {len(locked_users)}개 계정의 잠금을 해제합니다:")
        for user in locked_users:
            print(f"  - {user.email} (실패 횟수: {user.failed_login_attempts})")

        await session.execute(
            update(User)
            .where(User.failed_login_attempts > 0)
            .values(failed_login_attempts=0)
        )
        await session.commit()

        print(f"[SUCCESS] {len(locked_users)}개 계정 잠금 해제 완료")


async def main():
    """메인 실행 함수"""
    print("[START] 사용자 계정 잠금 해제 도구")

    if len(sys.argv) < 2:
        print("\n[사용법]")
        print("  python scripts/unlock_user.py <email>       # 특정 사용자 잠금 해제")
        print("  python scripts/unlock_user.py --all         # 모든 사용자 잠금 해제")
        print("\n[예시]")
        print("  python scripts/unlock_user.py customer3@example.com")
        print("  python scripts/unlock_user.py --all")
        return

    try:
        if sys.argv[1] == "--all":
            await unlock_all_users()
        else:
            email = sys.argv[1]
            await unlock_user(email)

    except Exception as e:
        print(f"[ERROR] 실행 실패: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
