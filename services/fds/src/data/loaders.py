"""
데이터 로더 모듈

사기 탐지에 필요한 정적 데이터를 로드합니다.
- 테스트 카드 번호 리스트
- 화물 전달 업체 주소 리스트
- 일회용 이메일 도메인 리스트
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from functools import lru_cache


class DataLoader:
    """정적 데이터 로더"""

    def __init__(self, data_dir: Path = None):
        """
        Args:
            data_dir: 데이터 디렉토리 경로 (기본값: src/data/)
        """
        if data_dir is None:
            data_dir = Path(__file__).parent
        self.data_dir = data_dir

    @lru_cache(maxsize=1)
    def load_test_cards(self) -> List[str]:
        """
        테스트 카드 번호 리스트 로드

        Returns:
            List[str]: 테스트 카드 번호 리스트

        Example:
            >>> loader = DataLoader()
            >>> test_cards = loader.load_test_cards()
            >>> print(len(test_cards))
            20
        """
        file_path = self.data_dir / "test_cards.json"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("test_cards", [])
        except FileNotFoundError:
            print(f"[WARNING] Test cards file not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in test cards file: {e}")
            return []

    @lru_cache(maxsize=1)
    def load_freight_forwarders(self) -> List[Dict[str, Any]]:
        """
        화물 전달 업체 리스트 로드

        Returns:
            List[Dict[str, Any]]: 화물 전달 업체 정보 리스트

        Example:
            >>> loader = DataLoader()
            >>> forwarders = loader.load_freight_forwarders()
            >>> print(len(forwarders))
            10
        """
        file_path = self.data_dir / "freight_forwarders.json"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("freight_forwarders", [])
        except FileNotFoundError:
            print(f"[WARNING] Freight forwarders file not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in freight forwarders file: {e}")
            return []

    @lru_cache(maxsize=1)
    def load_disposable_email_domains(self) -> List[str]:
        """
        일회용 이메일 도메인 리스트 로드

        Returns:
            List[str]: 일회용 이메일 도메인 리스트

        Example:
            >>> loader = DataLoader()
            >>> domains = loader.load_disposable_email_domains()
            >>> print(len(domains))
            98
        """
        file_path = self.data_dir / "disposable_emails.json"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("disposable_email_domains", [])
        except FileNotFoundError:
            print(f"[WARNING] Disposable emails file not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in disposable emails file: {e}")
            return []

    def reload(self):
        """캐시를 클리어하고 데이터 재로드"""
        self.load_test_cards.cache_clear()
        self.load_freight_forwarders.cache_clear()
        self.load_disposable_email_domains.cache_clear()


# 글로벌 인스턴스
_loader = DataLoader()


def get_test_cards() -> List[str]:
    """테스트 카드 리스트 반환 (편의 함수)"""
    return _loader.load_test_cards()


def get_freight_forwarders() -> List[Dict[str, Any]]:
    """화물 전달 업체 리스트 반환 (편의 함수)"""
    return _loader.load_freight_forwarders()


def get_disposable_email_domains() -> List[str]:
    """일회용 이메일 도메인 리스트 반환 (편의 함수)"""
    return _loader.load_disposable_email_domains()


def reload_all_data():
    """모든 데이터 재로드 (편의 함수)"""
    _loader.reload()
