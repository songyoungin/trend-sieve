"""Gemini 기반 필터링 모듈."""

import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from trend_sieve.config import settings
from trend_sieve.models import FilteredRepository, Repository

logger = logging.getLogger(__name__)


class _FilteredItem(BaseModel):
    """Gemini 응답용 스키마."""

    index: int = Field(description="저장소 번호 (1부터 시작)")
    relevance_score: int = Field(ge=1, le=10, description="관련성 점수 (1-10)")
    matched_interests: list[str] = Field(description="매칭된 관심 키워드")
    summary: str = Field(description="한국어 요약 (2-3문장)")


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

    def _build_prompt(self, repositories: list[Repository]) -> str:
        """필터링 프롬프트를 생성한다."""
        repos_text = "\n\n".join(
            f"### {i + 1}. {repo.name}\n"
            f"- URL: {repo.url}\n"
            f"- 설명: {repo.description or '없음'}\n"
            f"- 언어: {repo.language or '없음'}\n"
            f"- 스타: {repo.stars:,} (오늘 +{repo.stars_today:,})"
            for i, repo in enumerate(repositories)
        )

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

관련 없는 저장소는 출력에서 제외하세요. 관련 저장소가 없으면 빈 배열을 반환하세요."""

    def _build_results(
        self,
        items: list[_FilteredItem],
        repositories: list[Repository],
    ) -> list[FilteredRepository]:
        """응답 아이템을 FilteredRepository로 변환한다."""
        results = []
        for item in items:
            idx = item.index - 1
            if 0 <= idx < len(repositories):
                results.append(
                    FilteredRepository(
                        repository=repositories[idx],
                        relevance_score=item.relevance_score,
                        summary=item.summary,
                        matched_interests=item.matched_interests,
                    )
                )
        return results

    async def filter(
        self,
        repositories: list[Repository],
    ) -> list[FilteredRepository]:
        """저장소 목록을 필터링하고 요약한다."""
        if not repositories:
            return []

        prompt = self._build_prompt(repositories)

        response = await self.client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,
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

        return self._build_results(items, repositories)
