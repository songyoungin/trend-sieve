"""Slack 알림 테스트."""

import pytest

from trend_sieve.models import TrendItem
from trend_sieve.notifiers.slack import SlackNotifier


@pytest.fixture
def notifier() -> SlackNotifier:
    """SlackNotifier 인스턴스를 반환한다."""
    return SlackNotifier(webhook_url=None)


@pytest.fixture
def sample_items() -> list[TrendItem]:
    """테스트용 아이템 목록을 반환한다."""
    return [
        TrendItem(
            source="github",
            source_id="openai/gpt",
            title="openai/gpt",
            url="https://github.com/openai/gpt",
            relevance_score=9,
            summary="GPT 모델 구현체",
            matched_interests=["LLM", "GPT"],
        ),
        TrendItem(
            source="hackernews",
            source_id="12345",
            title="Claude 4 Released",
            url="https://example.com/claude4",
            relevance_score=8,
            summary="Anthropic의 새 모델",
            matched_interests=["LLM"],
            metadata={"points": 500, "comments": 200},
        ),
    ]


class TestSlackNotifier:
    """SlackNotifier 테스트."""

    def test_is_configured_false_without_url(self, notifier: SlackNotifier) -> None:
        """webhook_url 없이는 is_configured가 False다."""
        assert notifier.is_configured is False

    def test_format_message(
        self, notifier: SlackNotifier, sample_items: list[TrendItem]
    ) -> None:
        """메시지 포맷이 올바르게 생성된다."""
        message = notifier._format_message(sample_items)
        assert "오늘의 AI 트렌드" in message
        assert "openai/gpt" in message
        assert "Claude 4 Released" in message
