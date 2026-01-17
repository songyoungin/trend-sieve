"""Supabase 스토리지 모듈."""

import logging
from datetime import UTC, datetime, timedelta

from supabase import Client, create_client

from trend_sieve.models import TrendItem

logger = logging.getLogger(__name__)


class SupabaseStorage:
    """Supabase에 트렌드 아이템을 저장한다."""

    def __init__(self, url: str | None, key: str | None) -> None:
        """
        Args:
            url: Supabase 프로젝트 URL
            key: Supabase anon key
        """
        self.client: Client | None = None
        if url and key:
            self.client = create_client(url, key)

    @property
    def is_configured(self) -> bool:
        """Supabase가 설정되었는지 확인한다."""
        return self.client is not None

    async def upsert_items(self, items: list[TrendItem]) -> list[TrendItem]:
        """아이템을 저장하고 새로 추가된 아이템을 반환한다."""
        if not self.client or not items:
            return []

        new_items: list[TrendItem] = []
        now = datetime.now(UTC).isoformat()

        for item in items:
            # 기존 아이템 확인
            existing = (
                self.client.table("trend_items")
                .select("id, first_seen_at")
                .eq("source", item.source)
                .eq("source_id", item.source_id)
                .execute()
            )

            data = {
                "source": item.source,
                "source_id": item.source_id,
                "title": item.title,
                "url": item.url,
                "description": item.description,
                "metadata": item.metadata,
                "relevance_score": item.relevance_score,
                "summary": item.summary,
                "matched_interests": item.matched_interests,
                "code_example": item.code_example,
                "license": item.license,
                "is_open_source": item.is_open_source,
                "last_seen_at": now,
            }

            if existing.data:
                # 기존 아이템 업데이트
                self.client.table("trend_items").update(data).eq(
                    "id", existing.data[0]["id"]
                ).execute()
            else:
                # 새 아이템 삽입
                data["first_seen_at"] = now
                self.client.table("trend_items").insert(data).execute()
                new_items.append(item)
                logger.info(f"New item: {item.source}/{item.source_id}")

        return new_items

    async def get_recent_items(
        self, days: int = 7, limit: int = 100
    ) -> list[dict[str, object]]:
        """최근 아이템을 조회한다.

        Args:
            days: 조회할 기간 (일 단위)
            limit: 최대 조회 개수
        """
        if not self.client:
            return []

        # days 일 이내의 아이템만 조회
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        response = (
            self.client.table("trend_items")
            .select("*")
            .gte("first_seen_at", since)
            .order("first_seen_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
