"""소스 프로토콜 정의."""

from typing import Protocol

from trend_sieve.models import Repository


class Source(Protocol):
    """데이터 소스 프로토콜."""

    async def fetch(self) -> list[Repository]:
        """데이터를 가져온다."""
        ...
