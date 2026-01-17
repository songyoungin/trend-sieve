"""Gemini 기반 필터링 모듈."""

import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from trend_sieve.config import settings
from trend_sieve.models import CodeExample, FilteredRepository, Repository

logger = logging.getLogger(__name__)


class _QuickStartCode(BaseModel):
    """Quick Start 코드 스키마."""

    language: str = Field(default="", description="프로그래밍 언어")
    code: str = Field(default="", description="Quick Start 예제 코드 (10-15줄 이내)")


class _FilteredItem(BaseModel):
    """Gemini 응답용 스키마."""

    index: int = Field(description="저장소 번호 (1부터 시작)")
    relevance_score: int = Field(ge=1, le=10, description="관련성 점수 (1-10)")
    matched_interests: list[str] = Field(description="매칭된 관심 키워드")
    summary: str = Field(description="한국어 요약 (2-3문장)")
    quick_start: _QuickStartCode | None = Field(
        default=None,
        description="README에서 추출한 Quick Start 예제 코드 (있는 경우만)",
    )


class GeminiFilter:
    """Gemini를 사용하여 저장소를 필터링하고 요약한다."""

    def __init__(
        self,
        interests: list[str] | None = None,
        threshold: int | None = None,
    ) -> None:
        """
        Args:
            interests: 관심 키워드 목록. None이면 설정값 사용.
            threshold: 관련성 임계값 (1-10). None이면 설정값 사용.
        """
        self.interests = interests or settings.interests
        self.threshold = threshold or settings.relevance_threshold
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def _build_prompt(
        self,
        repositories: list[Repository],
        readmes: dict[str, str],
    ) -> str:
        """필터링 프롬프트를 생성한다."""
        repos_parts = []
        for i, repo in enumerate(repositories):
            readme_excerpt = readmes.get(repo.name, "")
            # README는 앞부분만 사용 (토큰 절약)
            if readme_excerpt and len(readme_excerpt) > 3000:
                readme_excerpt = readme_excerpt[:3000] + "\n[... truncated ...]"

            part = (
                f"### {i + 1}. {repo.name}\n"
                f"- URL: {repo.url}\n"
                f"- 설명: {repo.description or '없음'}\n"
                f"- 언어: {repo.language or '없음'}\n"
                f"- 스타: {repo.stars:,} (오늘 +{repo.stars_today:,})"
            )
            if readme_excerpt:
                part += f"\n- README:\n```\n{readme_excerpt}\n```"
            repos_parts.append(part)

        repos_text = "\n\n".join(repos_parts)
        interests_text = ", ".join(self.interests)

        return f"""당신은 기술 트렌드 분석가입니다. 아래 GitHub 저장소 목록을 분석하여 관심 키워드와 관련된 저장소만 필터링하세요.

## 관심 키워드
{interests_text}

## 저장소 목록
{repos_text}

## 작업
각 저장소에 대해:
1. 관심 키워드와의 관련성을 1-10점으로 평가하세요.
2. 관련성이 {self.threshold}점 이상인 저장소만 선택하세요.
3. 선택된 저장소에 대해 한국어로 2-3문장 요약을 작성하세요.
4. README가 있으면, 개발자가 바로 실행해볼 수 있는 Quick Start 예제 코드를 추출하세요.
   - 설치 명령어(pip install, npm install 등)는 제외
   - 실제 라이브러리 사용 코드만 선택
   - 10-15줄 이내로 핵심만 추출
   - 적절한 예제가 없으면 quick_start를 null로

관련 없는 저장소는 출력에서 제외하세요. 관련 저장소가 없으면 빈 배열을 반환하세요."""

    def _build_results(
        self,
        items: list[_FilteredItem],
        repositories: list[Repository],
        licenses: dict[str, str | None],
        open_source_set: set[str],
    ) -> list[FilteredRepository]:
        """응답 아이템을 FilteredRepository로 변환한다."""
        results = []
        for item in items:
            idx = item.index - 1
            if 0 <= idx < len(repositories):
                repo = repositories[idx]
                is_open_source = repo.name in open_source_set

                code_examples: list[CodeExample] = []
                if item.quick_start and item.quick_start.code and is_open_source:
                    code_examples.append(
                        CodeExample(
                            language=item.quick_start.language
                            or repo.language
                            or "text",
                            code=item.quick_start.code,
                        )
                    )

                results.append(
                    FilteredRepository(
                        repository=repo,
                        relevance_score=item.relevance_score,
                        summary=item.summary,
                        matched_interests=item.matched_interests,
                        license=licenses.get(repo.name),
                        is_open_source=is_open_source,
                        code_examples=code_examples,
                    )
                )
        return results

    async def filter(
        self,
        repositories: list[Repository],
        readmes: dict[str, str] | None = None,
        licenses: dict[str, str | None] | None = None,
        open_source_set: set[str] | None = None,
    ) -> list[FilteredRepository]:
        """저장소 목록을 필터링하고 요약한다."""
        if not repositories:
            return []

        readmes = readmes or {}
        licenses = licenses or {}
        open_source_set = open_source_set or set()

        prompt = self._build_prompt(repositories, readmes)

        response = await self.client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=list[_FilteredItem],
            ),
        )

        if not response.text:
            logger.warning("Gemini 응답이 비어있음")
            return []

        # Structured Output이므로 파싱된 결과를 바로 사용
        items = response.parsed
        if items is None:
            logger.warning("Gemini 응답 파싱 실패")
            return []

        return self._build_results(items, repositories, licenses, open_source_set)
