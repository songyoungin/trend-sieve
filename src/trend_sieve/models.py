"""데이터 모델 정의."""

from pydantic import BaseModel, Field


class Repository(BaseModel):
    """GitHub 저장소 정보."""

    name: str = Field(description="저장소 전체 이름 (owner/repo)")
    url: str = Field(description="저장소 URL")
    description: str | None = Field(default=None, description="저장소 설명")
    language: str | None = Field(default=None, description="주 프로그래밍 언어")
    stars: int = Field(default=0, description="총 스타 수")
    stars_today: int = Field(default=0, description="오늘 추가된 스타 수")
    forks: int = Field(default=0, description="포크 수")


class FilteredRepository(BaseModel):
    """필터링된 저장소 정보 (요약 포함)."""

    repository: Repository = Field(description="원본 저장소 정보")
    relevance_score: int = Field(ge=1, le=10, description="관련성 점수 (1-10)")
    summary: str = Field(description="AI 생성 요약")
    matched_interests: list[str] = Field(
        default_factory=list,
        description="매칭된 관심 키워드",
    )
