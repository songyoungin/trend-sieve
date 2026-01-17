"""Slack 알림 모듈."""

import logging

import httpx

from trend_sieve.models import TrendItem

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slack으로 알림을 전송한다."""

    def __init__(self, webhook_url: str | None) -> None:
        """
        Args:
            webhook_url: Slack Incoming Webhook URL
        """
        self.webhook_url = webhook_url

    @property
    def is_configured(self) -> bool:
        """Slack이 설정되었는지 확인한다."""
        return self.webhook_url is not None

    def _format_message(self, items: list[TrendItem]) -> str:
        """알림 메시지를 포맷한다."""
        github_items = [i for i in items if i.source == "github"]
        hn_items = [i for i in items if i.source == "hackernews"]

        lines = [f":fire: *오늘의 AI 트렌드* ({len(items)}건)\n"]

        if github_items:
            lines.append("*:package: GitHub*")
            for item in github_items[:5]:  # 최대 5개
                score = (
                    f":star: {item.relevance_score}/10" if item.relevance_score else ""
                )
                lines.append(
                    f"• <{item.url}|{item.title}> - {item.summary or ''} {score}"
                )
            lines.append("")

        if hn_items:
            lines.append("*:newspaper: Hacker News*")
            for item in hn_items[:5]:  # 최대 5개
                score = (
                    f":star: {item.relevance_score}/10" if item.relevance_score else ""
                )
                points = item.metadata.get("points", 0)
                lines.append(
                    f"• <{item.url}|{item.title}> ({points} points) "
                    f"- {item.summary or ''} {score}"
                )

        return "\n".join(lines)

    async def send(self, items: list[TrendItem]) -> bool:
        """새 아이템 알림을 전송한다."""
        if not self.webhook_url or not items:
            return False

        message = self._format_message(items)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.webhook_url,
                    json={"text": message},
                )
                if response.status_code == 200:
                    logger.info(f"Slack notification sent: {len(items)} items")
                    return True
                else:
                    logger.error(f"Slack API error: {response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"Slack request failed: {e}")

        return False
