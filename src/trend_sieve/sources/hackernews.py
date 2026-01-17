"""Hacker News 소스 모듈."""

import asyncio
import logging
from typing import Any

import httpx

from trend_sieve.models import TrendItem

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsSource:
    """Hacker News에서 트렌드 아이템을 수집한다."""

    def __init__(self, timeout: float = 10.0) -> None:
        """HackerNewsSource 인스턴스를 초기화한다.

        Args:
            timeout: HTTP 요청 타임아웃 (초)
        """
        self.timeout = timeout

    async def _fetch_item(
        self, client: httpx.AsyncClient, item_id: int
    ) -> dict[str, Any] | None:
        """개별 아이템을 가져온다.

        Args:
            client: HTTP 클라이언트
            item_id: Hacker News 아이템 ID

        Returns:
            아이템 데이터 딕셔너리 또는 None
        """
        try:
            response = await client.get(f"{HN_API_BASE}/item/{item_id}.json")
            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                return data
        except httpx.RequestError as e:
            logger.warning(f"Failed to fetch item {item_id}: {e}")
        return None

    async def fetch(self, limit: int = 30) -> list[TrendItem]:
        """Top Stories에서 아이템을 수집한다.

        Args:
            limit: 수집할 최대 아이템 수

        Returns:
            TrendItem 리스트
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{HN_API_BASE}/topstories.json")
            if response.status_code != 200:
                logger.error("Failed to fetch top stories")
                return []

            story_ids: list[int] = response.json()[:limit]
            tasks = [self._fetch_item(client, sid) for sid in story_ids]
            items = await asyncio.gather(*tasks)

            results: list[TrendItem] = []
            for item in items:
                if not item or item.get("type") != "story":
                    continue

                url = (
                    item.get("url")
                    or f"https://news.ycombinator.com/item?id={item['id']}"
                )

                results.append(
                    TrendItem(
                        source="hackernews",
                        source_id=str(item["id"]),
                        title=item.get("title", ""),
                        url=url,
                        description=None,
                        metadata={
                            "points": item.get("score", 0),
                            "comments": item.get("descendants", 0),
                            "author": item.get("by", ""),
                            "time": item.get("time", 0),
                        },
                    )
                )

            return results
