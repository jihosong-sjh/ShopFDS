"""
Performance 테스트 플레이스홀더

실제 성능 테스트가 구현될 때까지 임시로 사용하는 플레이스홀더입니다.
"""

import pytest


def test_placeholder(benchmark):
    """플레이스홀더 벤치마크 테스트"""

    def dummy_operation():
        """간단한 더미 작업"""
        return sum(range(100))

    result = benchmark(dummy_operation)
    assert result == 4950
