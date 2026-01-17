"""Hacker News 소스 테스트."""

import pytest

from trend_sieve.sources.hackernews import HackerNewsSource


@pytest.fixture
def source() -> HackerNewsSource:
    """HackerNewsSource 인스턴스를 반환한다."""
    return HackerNewsSource()


class TestHackerNewsSource:
    """HackerNewsSource 테스트."""

    @pytest.mark.asyncio
    async def test_fetch_returns_list(self, source: HackerNewsSource) -> None:
        """fetch()가 리스트를 반환하는지 확인한다."""
        items = await source.fetch(limit=5)
        assert isinstance(items, list)
        assert len(items) <= 5

    @pytest.mark.asyncio
    async def test_fetch_item_has_required_fields(
        self, source: HackerNewsSource
    ) -> None:
        """각 아이템이 필수 필드를 가지는지 확인한다."""
        items = await source.fetch(limit=1)
        if items:
            item = items[0]
            assert item.source == "hackernews"
            assert item.source_id
            assert item.title
            assert item.url
