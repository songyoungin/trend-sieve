"""CLI 엔트리포인트."""

import asyncio
import logging
import sys

from trend_sieve.filters import GeminiFilter
from trend_sieve.sources import GitHubTrendingSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run() -> None:
    """메인 파이프라인을 실행한다."""
    # 1. GitHub Trending에서 저장소 수집
    logger.info("GitHub Trending 데이터 수집 중...")
    source = GitHubTrendingSource(since="daily")
    repositories = await source.fetch()
    logger.info("수집된 저장소: %d개", len(repositories))

    if not repositories:
        logger.warning("수집된 저장소가 없습니다.")
        return

    # 2. Gemini로 필터링 및 요약
    logger.info("AI 필터링 및 요약 중...")
    gemini_filter = GeminiFilter()
    filtered = await gemini_filter.filter(repositories)
    logger.info("필터링된 저장소: %d개", len(filtered))

    # 3. 결과 출력
    if not filtered:
        print("\n관심 키워드와 관련된 저장소가 없습니다.")
        return

    print("\n" + "=" * 60)
    print("🔥 오늘의 AI/LLM 트렌드 저장소")
    print("=" * 60)

    for i, item in enumerate(filtered, 1):
        repo = item.repository
        print(f"\n### {i}. {repo.name}")
        print(f"⭐ {repo.stars:,} (+{repo.stars_today:,} today)")
        if repo.language:
            print(f"📝 {repo.language}")
        print(f"🔗 {repo.url}")
        print(f"📊 관련성: {item.relevance_score}/10")
        print(f"🏷️  키워드: {', '.join(item.matched_interests)}")
        print(f"\n{item.summary}")
        print("-" * 60)


def main() -> None:
    """CLI 엔트리포인트."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n중단됨")
        sys.exit(0)
    except Exception as e:
        logger.exception("오류 발생: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
