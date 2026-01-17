# 클라우드 모니터링 시스템 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** GitHub Trending + Hacker News를 매일 자동 수집하여 Supabase에 저장하고, 새 아이템을 Slack으로 알림

**Architecture:** GitHub Actions가 매일 09:00 KST에 트리거 → 두 소스에서 데이터 수집 → Gemini로 필터링/요약 → Supabase UPSERT → 새 아이템만 Slack 알림

**Tech Stack:** Python 3.13, httpx, supabase-py, typer, pydantic, GitHub Actions

---

## Task 1: Hacker News Source 추가

**Files:**
- Create: `src/trend_sieve/sources/hackernews.py`
- Create: `tests/sources/test_hackernews.py`
- Modify: `src/trend_sieve/sources/__init__.py`

### Step 1: 테스트 파일 구조 생성

```bash
mkdir -p tests/sources
touch tests/__init__.py tests/sources/__init__.py
```

### Step 2: 실패하는 테스트 작성

`tests/sources/test_hackernews.py`:

```python
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
```

### Step 3: 테스트 실패 확인

```bash
uv run pytest tests/sources/test_hackernews.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'trend_sieve.sources.hackernews'`

### Step 4: TrendItem 모델 추가

`src/trend_sieve/models.py`에 추가:

```python
class TrendItem(BaseModel):
    """통합 트렌드 아이템 (GitHub + HN 공통)."""

    source: str = Field(description="소스 ('github' | 'hackernews')")
    source_id: str = Field(description="소스별 고유 ID")
    title: str = Field(description="제목")
    url: str = Field(description="URL")
    description: str | None = Field(default=None, description="설명")
    metadata: dict = Field(default_factory=dict, description="소스별 메타데이터")

    # AI 분석 결과 (필터링 후 채워짐)
    relevance_score: int | None = Field(default=None, description="관련성 점수")
    summary: str | None = Field(default=None, description="요약")
    matched_interests: list[str] = Field(default_factory=list, description="매칭된 관심사")
    code_example: str | None = Field(default=None, description="예제 코드")

    # 라이선스 (GitHub만)
    license: str | None = Field(default=None, description="라이선스")
    is_open_source: bool = Field(default=False, description="오픈소스 여부")
```

### Step 5: HackerNewsSource 구현

`src/trend_sieve/sources/hackernews.py`:

```python
"""Hacker News 소스 모듈."""

import asyncio
import logging

import httpx

from trend_sieve.models import TrendItem

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsSource:
    """Hacker News에서 트렌드 아이템을 수집한다."""

    def __init__(self, timeout: float = 10.0) -> None:
        """
        Args:
            timeout: HTTP 요청 타임아웃 (초)
        """
        self.timeout = timeout

    async def _fetch_item(
        self, client: httpx.AsyncClient, item_id: int
    ) -> dict | None:
        """개별 아이템을 가져온다."""
        try:
            response = await client.get(f"{HN_API_BASE}/item/{item_id}.json")
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"Failed to fetch item {item_id}: {e}")
        return None

    async def fetch(self, limit: int = 30) -> list[TrendItem]:
        """Top Stories에서 아이템을 수집한다."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Top Stories ID 목록 가져오기
            response = await client.get(f"{HN_API_BASE}/topstories.json")
            if response.status_code != 200:
                logger.error("Failed to fetch top stories")
                return []

            story_ids: list[int] = response.json()[:limit]

            # 각 아이템 병렬 수집
            tasks = [self._fetch_item(client, sid) for sid in story_ids]
            items = await asyncio.gather(*tasks)

            results: list[TrendItem] = []
            for item in items:
                if not item or item.get("type") != "story":
                    continue

                # URL이 없는 경우 (Ask HN 등) HN 페이지 URL 사용
                url = item.get("url") or f"https://news.ycombinator.com/item?id={item['id']}"

                results.append(
                    TrendItem(
                        source="hackernews",
                        source_id=str(item["id"]),
                        title=item.get("title", ""),
                        url=url,
                        description=None,  # HN은 description이 없음
                        metadata={
                            "points": item.get("score", 0),
                            "comments": item.get("descendants", 0),
                            "author": item.get("by", ""),
                            "time": item.get("time", 0),
                        },
                    )
                )

            return results
```

### Step 6: `__init__.py` 업데이트

`src/trend_sieve/sources/__init__.py`:

```python
"""데이터 소스 모듈."""

from trend_sieve.sources.github import GitHubTrendingSource
from trend_sieve.sources.hackernews import HackerNewsSource

__all__ = ["GitHubTrendingSource", "HackerNewsSource"]
```

### Step 7: 테스트 통과 확인

```bash
uv run pytest tests/sources/test_hackernews.py -v
```

Expected: PASS

### Step 8: 커밋

```bash
git add src/trend_sieve/sources/hackernews.py src/trend_sieve/sources/__init__.py src/trend_sieve/models.py tests/
git commit -m "feat(sources): Hacker News 소스 추가

- HackerNewsSource 클래스 구현
- HN Top Stories API 연동
- TrendItem 통합 모델 추가
- 테스트 코드 작성"
```

---

## Task 2: Supabase Storage 추가

**Files:**
- Create: `src/trend_sieve/storage/__init__.py`
- Create: `src/trend_sieve/storage/supabase.py`
- Create: `tests/storage/test_supabase.py`
- Modify: `src/trend_sieve/config.py`
- Modify: `pyproject.toml`

### Step 1: supabase 의존성 추가

```bash
uv add supabase
```

### Step 2: 환경변수 설정 추가

`src/trend_sieve/config.py` 수정:

```python
class Settings(BaseSettings):
    # ... 기존 필드 ...

    # Supabase
    supabase_url: str | None = Field(default=None, description="Supabase URL")
    supabase_key: str | None = Field(default=None, description="Supabase anon key")

    # Slack
    slack_webhook_url: str | None = Field(default=None, description="Slack Webhook URL")
```

### Step 3: 실패하는 테스트 작성

`tests/storage/test_supabase.py`:

```python
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
```

### Step 4: 테스트 실패 확인

```bash
mkdir -p tests/storage
touch tests/storage/__init__.py
uv run pytest tests/storage/test_supabase.py -v
```

Expected: FAIL - `ModuleNotFoundError`

### Step 5: SupabaseStorage 구현

`src/trend_sieve/storage/__init__.py`:

```python
"""스토리지 모듈."""

from trend_sieve.storage.supabase import SupabaseStorage

__all__ = ["SupabaseStorage"]
```

`src/trend_sieve/storage/supabase.py`:

```python
"""Supabase 스토리지 모듈."""

import logging
from datetime import datetime, timezone

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
        now = datetime.now(timezone.utc).isoformat()

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
    ) -> list[dict]:
        """최근 아이템을 조회한다."""
        if not self.client:
            return []

        response = (
            self.client.table("trend_items")
            .select("*")
            .order("first_seen_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
```

### Step 6: 테스트 통과 확인

```bash
uv run pytest tests/storage/test_supabase.py -v
```

Expected: PASS

### Step 7: 커밋

```bash
git add src/trend_sieve/storage/ src/trend_sieve/config.py tests/storage/ pyproject.toml uv.lock
git commit -m "feat(storage): Supabase 스토리지 추가

- SupabaseStorage 클래스 구현
- upsert_items로 새 아이템 판별
- 환경변수 설정 추가
- 테스트 코드 작성"
```

---

## Task 3: Slack Notifier 추가

**Files:**
- Create: `src/trend_sieve/notifiers/__init__.py`
- Create: `src/trend_sieve/notifiers/slack.py`
- Create: `tests/notifiers/test_slack.py`

### Step 1: 실패하는 테스트 작성

`tests/notifiers/test_slack.py`:

```python
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
```

### Step 2: 테스트 실패 확인

```bash
mkdir -p tests/notifiers
touch tests/notifiers/__init__.py
uv run pytest tests/notifiers/test_slack.py -v
```

Expected: FAIL - `ModuleNotFoundError`

### Step 3: SlackNotifier 구현

`src/trend_sieve/notifiers/__init__.py`:

```python
"""알림 모듈."""

from trend_sieve.notifiers.slack import SlackNotifier

__all__ = ["SlackNotifier"]
```

`src/trend_sieve/notifiers/slack.py`:

```python
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
                score = f":star: {item.relevance_score}/10" if item.relevance_score else ""
                lines.append(f"• <{item.url}|{item.title}> - {item.summary or ''} {score}")
            lines.append("")

        if hn_items:
            lines.append("*:newspaper: Hacker News*")
            for item in hn_items[:5]:  # 최대 5개
                score = f":star: {item.relevance_score}/10" if item.relevance_score else ""
                points = item.metadata.get("points", 0)
                lines.append(
                    f"• <{item.url}|{item.title}> ({points} points) - {item.summary or ''} {score}"
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
```

### Step 4: 테스트 통과 확인

```bash
uv run pytest tests/notifiers/test_slack.py -v
```

Expected: PASS

### Step 5: 커밋

```bash
git add src/trend_sieve/notifiers/ tests/notifiers/
git commit -m "feat(notifiers): Slack 알림 추가

- SlackNotifier 클래스 구현
- Incoming Webhook으로 메시지 전송
- GitHub/HN 소스별 포맷팅
- 테스트 코드 작성"
```

---

## Task 4: Scheduler 엔트리포인트 추가

**Files:**
- Create: `src/trend_sieve/scheduler.py`
- Modify: `pyproject.toml` (scripts 추가)

### Step 1: scheduler.py 구현

`src/trend_sieve/scheduler.py`:

```python
"""스케줄러 엔트리포인트 (GitHub Actions용)."""

import asyncio
import logging

from trend_sieve.config import settings
from trend_sieve.enrichers import ReadmeEnricher
from trend_sieve.filters import GeminiFilter
from trend_sieve.models import TrendItem
from trend_sieve.notifiers import SlackNotifier
from trend_sieve.sources import GitHubTrendingSource, HackerNewsSource
from trend_sieve.storage import SupabaseStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _convert_github_to_trend_item(
    filtered_repo,
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
        code_example=filtered_repo.code_examples[0].code if filtered_repo.code_examples else None,
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
```

### Step 2: pyproject.toml에 스크립트 추가

`pyproject.toml` 수정 - `[project.scripts]` 섹션에 추가:

```toml
[project.scripts]
trend-sieve = "trend_sieve.main:app"
trend-sieve-scheduler = "trend_sieve.scheduler:main"
```

### Step 3: 로컬 테스트

```bash
uv run trend-sieve-scheduler
```

Expected: GitHub + HN 수집 로그 출력 (Supabase/Slack 미설정 경고)

### Step 4: 커밋

```bash
git add src/trend_sieve/scheduler.py pyproject.toml
git commit -m "feat(scheduler): GitHub Actions용 스케줄러 추가

- run() 함수로 전체 파이프라인 실행
- GitHub + HN 수집 → 필터링 → 저장 → 알림
- trend-sieve-scheduler CLI 명령어 추가"
```

---

## Task 5: GitHub Actions 워크플로우 추가

**Files:**
- Create: `.github/workflows/daily-trend.yml`

### Step 1: 워크플로우 파일 생성

`.github/workflows/daily-trend.yml`:

```yaml
name: Daily Trend Sieve

on:
  schedule:
    # UTC 00:00 = KST 09:00
    - cron: '0 0 * * *'
  workflow_dispatch:  # 수동 실행

jobs:
  collect:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync

      - name: Run scheduler
        run: uv run trend-sieve-scheduler
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Step 2: 커밋

```bash
mkdir -p .github/workflows
git add .github/workflows/daily-trend.yml
git commit -m "ci: GitHub Actions 일일 스케줄 워크플로우 추가

- 매일 09:00 KST 자동 실행
- 수동 실행(workflow_dispatch) 지원
- 환경변수는 GitHub Secrets에서 주입"
```

---

## Task 6: Supabase 테이블 생성 SQL

**Files:**
- Create: `docs/supabase-schema.sql`

### Step 1: SQL 파일 생성

`docs/supabase-schema.sql`:

```sql
-- trend_items 테이블 생성
CREATE TABLE trend_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT,

  metadata JSONB DEFAULT '{}',

  relevance_score INT,
  summary TEXT,
  matched_interests TEXT[],
  code_example TEXT,

  license TEXT,
  is_open_source BOOLEAN DEFAULT false,

  first_seen_at TIMESTAMPTZ DEFAULT now(),
  last_seen_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(source, source_id)
);

-- 인덱스 생성
CREATE INDEX idx_trend_items_source ON trend_items(source);
CREATE INDEX idx_trend_items_first_seen ON trend_items(first_seen_at DESC);
CREATE INDEX idx_trend_items_relevance ON trend_items(relevance_score DESC);
CREATE INDEX idx_trend_items_source_id ON trend_items(source, source_id);

-- RLS (Row Level Security) 활성화
ALTER TABLE trend_items ENABLE ROW LEVEL SECURITY;

-- 공개 읽기 정책 (대시보드용)
CREATE POLICY "Public read access" ON trend_items
  FOR SELECT USING (true);

-- Service role만 쓰기 가능
CREATE POLICY "Service role write access" ON trend_items
  FOR ALL USING (auth.role() = 'service_role');
```

### Step 2: 커밋

```bash
git add docs/supabase-schema.sql
git commit -m "docs: Supabase 스키마 SQL 추가

- trend_items 테이블 정의
- 인덱스 및 RLS 정책 포함"
```

---

## Task 7: README 업데이트

**Files:**
- Modify: `README.md`

### Step 1: README에 클라우드 모니터링 섹션 추가

`README.md`에 다음 섹션 추가:

```markdown
## 클라우드 모니터링 (선택)

GitHub Actions를 통해 매일 자동으로 트렌드를 수집하고 Slack으로 알림받을 수 있습니다.

### 설정

1. **Supabase 프로젝트 생성**
   - [Supabase](https://supabase.com)에서 새 프로젝트 생성
   - `docs/supabase-schema.sql` 실행하여 테이블 생성

2. **Slack Webhook 생성**
   - [Slack API](https://api.slack.com/apps)에서 앱 생성
   - Incoming Webhooks 활성화 후 URL 복사

3. **GitHub Secrets 설정**
   - `GEMINI_API_KEY`: Gemini API 키
   - `SUPABASE_URL`: Supabase 프로젝트 URL
   - `SUPABASE_KEY`: Supabase anon key
   - `SLACK_WEBHOOK_URL`: Slack Webhook URL

4. **수동 실행 테스트**
   - Actions 탭 → "Daily Trend Sieve" → "Run workflow"

### 데이터 소스

| 소스 | 설명 |
|------|------|
| GitHub Trending | 일간 인기 저장소 |
| Hacker News | Top Stories |
```

### Step 2: 커밋

```bash
git add README.md
git commit -m "docs: 클라우드 모니터링 설정 가이드 추가"
```

---

## 완료 체크리스트

- [ ] Task 1: Hacker News Source
- [ ] Task 2: Supabase Storage
- [ ] Task 3: Slack Notifier
- [ ] Task 4: Scheduler 엔트리포인트
- [ ] Task 5: GitHub Actions 워크플로우
- [ ] Task 6: Supabase 스키마 SQL
- [ ] Task 7: README 업데이트

## 설정 필요 항목

1. Supabase 프로젝트 생성 및 테이블 생성
2. Slack Incoming Webhook 생성
3. GitHub Secrets 설정
4. (선택) 웹 대시보드 구축
