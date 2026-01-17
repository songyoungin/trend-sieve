"""Supabase 스토리지 테스트."""

import pytest

from trend_sieve.models import TrendItem
from trend_sieve.storage.supabase import SupabaseStorage


@pytest.fixture
def mock_item() -> TrendItem:
    """테스트용 TrendItem을 반환한다."""
    return TrendItem(
        source="github",
        source_id="test/repo",
        title="Test Repo",
        url="https://github.com/test/repo",
        description="Test description",
        relevance_score=8,
        summary="테스트 요약",
        matched_interests=["AI", "LLM"],
    )


class TestSupabaseStorage:
    """SupabaseStorage 테스트."""

    def test_init_without_credentials(self) -> None:
        """환경변수 없이 초기화하면 None 클라이언트를 가진다."""
        storage = SupabaseStorage(url=None, key=None)
        assert storage.client is None

    def test_is_configured(self) -> None:
        """is_configured가 올바르게 동작한다."""
        storage = SupabaseStorage(url=None, key=None)
        assert storage.is_configured is False
