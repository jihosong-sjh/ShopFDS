"""
사용자 비밀번호 재설정 스크립트

지정한 사용자의 비밀번호를 새로운 비밀번호로 업데이트합니다.
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from src.models.user import User
from src.utils.security import hash_password
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


async def reset_password(email: str, new_password: str):
    """사용자 비밀번호 재설정"""
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

        # 비밀번호 해싱
        hashed_password = hash_password(new_password)

        print(f"[INFO] 비밀번호를 '{new_password}'로 변경합니다...")

        # 비밀번호 업데이트 및 로그인 실패 횟수 초기화
        await session.execute(
            update(User)
            .where(User.email == email)
            .values(
                password_hash=hashed_password,
                failed_login_attempts=0
            )
        )
        await session.commit()

        print(f"[SUCCESS] 비밀번호 재설정 완료: {email}")
        return True


async def reset_all_test_users():
    """모든 테스트 사용자의 비밀번호를 기본값으로 재설정"""
    test_users = [
        ("customer1@example.com", "password123"),
        ("customer2@example.com", "password123"),
        ("customer3@example.com", "password123"),
        ("admin@shopfds.com", "admin123"),
        ("security@shopfds.com", "security123"),
    ]

    print(f"[INFO] {len(test_users)}개 테스트 계정의 비밀번호를 재설정합니다...")

    for email, password in test_users:
        await reset_password(email, password)
        print()

    print("[SUCCESS] 모든 테스트 계정 비밀번호 재설정 완료")


async def main():
    """메인 실행 함수"""
    print("[START] 비밀번호 재설정 도구")

    if len(sys.argv) < 2:
        print("\n[사용법]")
        print("  python scripts/reset_password.py <email> <password>  # 특정 사용자 비밀번호 재설정")
        print("  python scripts/reset_password.py --all               # 모든 테스트 사용자 재설정")
        print("\n[예시]")
        print("  python scripts/reset_password.py customer3@example.com password123")
        print("  python scripts/reset_password.py --all")
        return

    try:
        if sys.argv[1] == "--all":
            await reset_all_test_users()
        else:
            if len(sys.argv) < 3:
                print("[ERROR] 비밀번호를 입력해주세요.")
                print("사용법: python scripts/reset_password.py <email> <password>")
                return

            email = sys.argv[1]
            password = sys.argv[2]
            await reset_password(email, password)

    except Exception as e:
        print(f"[ERROR] 실행 실패: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
