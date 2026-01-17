"""스케줄러 엔트리포인트 (GitHub Actions용)."""

import asyncio
import logging

from trend_sieve.config import settings
from trend_sieve.enrichers import ReadmeEnricher
from trend_sieve.filters import GeminiFilter
from trend_sieve.models import FilteredRepository, TrendItem
from trend_sieve.notifiers import SlackNotifier
from trend_sieve.sources import GitHubTrendingSource, HackerNewsSource
from trend_sieve.storage import SupabaseStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _convert_github_to_trend_item(
    filtered_repo: FilteredRepository,
) -> TrendItem:
    """FilteredRepository를 TrendItem으로 변환한다."""
    repo = filtered_repo.repository
    return TrendItem(
        source="github",
        source_id=repo.name,
        title=repo.name,
        url=repo.url,
        description=repo.description,
        metadata={
            "stars": repo.stars,
            "stars_today": repo.stars_today,
            "language": repo.language,
            "forks": repo.forks,
        },
        relevance_score=filtered_repo.relevance_score,
        summary=filtered_repo.summary,
        matched_interests=filtered_repo.matched_interests,
        code_example=filtered_repo.code_examples[0].code
        if filtered_repo.code_examples
        else None,
        license=filtered_repo.license,
        is_open_source=filtered_repo.is_open_source,
    )


async def run() -> None:
    """스케줄러 메인 로직."""
    logger.info("Starting trend-sieve scheduler")

    # 1. GitHub Trending 수집
    logger.info("Fetching GitHub Trending...")
    github_source = GitHubTrendingSource()
    github_repos = await github_source.fetch()
    logger.info(f"Fetched {len(github_repos)} GitHub repos")

    # 2. README/라이선스 수집
    logger.info("Enriching with README and license...")
    enricher = ReadmeEnricher()
    repo_names = [repo.name for repo in github_repos]
    enrichments = await enricher.fetch_metadata_many(repo_names)

    readmes = {name: e["readme"] for name, e in enrichments.items() if e["readme"]}
    licenses = {name: e["license"] for name, e in enrichments.items()}
    open_source_set = {name for name, e in enrichments.items() if e["is_open_source"]}

    # 3. GitHub 필터링
    logger.info("Filtering GitHub repos with Gemini...")
    gemini_filter = GeminiFilter()
    filtered_github = await gemini_filter.filter(
        github_repos,
        readmes=readmes,
        licenses=licenses,
        open_source_set=open_source_set,
    )
    logger.info(f"Filtered to {len(filtered_github)} relevant GitHub repos")

    # GitHub 결과를 TrendItem으로 변환
    github_items = [_convert_github_to_trend_item(r) for r in filtered_github]

    # 4. Hacker News 수집
    logger.info("Fetching Hacker News...")
    hn_source = HackerNewsSource()
    hn_items = await hn_source.fetch(limit=50)
    logger.info(f"Fetched {len(hn_items)} HN items")

    # 5. HN 필터링 (Gemini)
    # HN 아이템을 필터링하기 위해 간단한 프롬프트 사용
    logger.info("Filtering HN items with Gemini...")
    # TODO: HN 전용 필터 구현 (현재는 GitHub 로직 재사용 불가)
    # 임시로 모든 HN 아이템 포함 (추후 개선)

    # 6. 모든 아이템 통합
    all_items = github_items + hn_items[:10]  # HN은 상위 10개만
    logger.info(f"Total items to save: {len(all_items)}")

    # 7. Supabase 저장
    storage = SupabaseStorage(
        url=settings.supabase_url,
        key=settings.supabase_key,
    )

    if storage.is_configured:
        logger.info("Saving to Supabase...")
        new_items = await storage.upsert_items(all_items)
        logger.info(f"New items: {len(new_items)}")
    else:
        logger.warning("Supabase not configured, skipping storage")
        new_items = all_items  # 테스트용

    # 8. Slack 알림
    notifier = SlackNotifier(webhook_url=settings.slack_webhook_url)

    if notifier.is_configured and new_items:
        logger.info("Sending Slack notification...")
        await notifier.send(new_items)
    else:
        if not notifier.is_configured:
            logger.warning("Slack not configured, skipping notification")
        if not new_items:
            logger.info("No new items to notify")

    logger.info("Scheduler completed")


def main() -> None:
    """CLI 엔트리포인트."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
