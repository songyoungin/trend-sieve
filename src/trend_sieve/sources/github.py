"""GitHub Trending 스크래퍼."""

import httpx
from selectolax.parser import HTMLParser

from trend_sieve.models import Repository


class GitHubTrendingSource:
    """GitHub Trending 페이지에서 저장소를 수집한다."""

    BASE_URL = "https://github.com/trending"

    def __init__(
        self,
        since: str = "daily",
        language: str | None = None,
    ) -> None:
        """
        Args:
            since: 기간 필터 (daily, weekly, monthly)
            language: 언어 필터 (예: python, rust). None이면 전체.
        """
        self.since = since
        self.language = language

    def _build_url(self) -> str:
        """요청 URL을 생성한다."""
        url = self.BASE_URL
        if self.language:
            url = f"{url}/{self.language}"
        return f"{url}?since={self.since}"

    def _parse_number(self, text: str) -> int:
        """숫자 문자열을 파싱한다 (예: '1,234' -> 1234)."""
        cleaned = text.strip().replace(",", "")
        if not cleaned:
            return 0
        return int(cleaned)

    def _parse_stars_today(self, text: str) -> int:
        """오늘 스타 수를 파싱한다 (예: '123 stars today' -> 123)."""
        parts = text.strip().split()
        if parts:
            return self._parse_number(parts[0])
        return 0

    def _parse_repository(self, article: HTMLParser) -> Repository | None:
        """HTML article 요소에서 저장소 정보를 추출한다."""
        # 저장소 이름
        name_elem = article.css_first("h2 a")
        if not name_elem:
            return None

        href = name_elem.attributes.get("href", "")
        name = href.strip("/")
        url = f"https://github.com{href}"

        # 설명
        desc_elem = article.css_first("p")
        description = desc_elem.text(strip=True) if desc_elem else None

        # 언어
        lang_elem = article.css_first("[itemprop='programmingLanguage']")
        language = lang_elem.text(strip=True) if lang_elem else None

        # 스타 수
        stars = 0
        star_links = article.css("a[href$='/stargazers']")
        if star_links:
            stars = self._parse_number(star_links[0].text())

        # 포크 수
        forks = 0
        fork_links = article.css("a[href$='/forks']")
        if fork_links:
            forks = self._parse_number(fork_links[0].text())

        # 오늘 스타 수
        stars_today = 0
        stars_today_elem = article.css_first("span.d-inline-block.float-sm-right")
        if stars_today_elem:
            stars_today = self._parse_stars_today(stars_today_elem.text())

        return Repository(
            name=name,
            url=url,
            description=description,
            language=language,
            stars=stars,
            forks=forks,
            stars_today=stars_today,
        )

    async def fetch(self) -> list[Repository]:
        """GitHub Trending 페이지에서 저장소 목록을 가져온다."""
        url = self._build_url()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Accept-Language": "en-US,en;q=0.9"},
                follow_redirects=True,
            )
            response.raise_for_status()

        parser = HTMLParser(response.text)
        articles = parser.css("article.Box-row")

        repositories = []
        for article in articles:
            repo = self._parse_repository(article)
            if repo:
                repositories.append(repo)

        return repositories
