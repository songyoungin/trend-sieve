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


class CodeExample(BaseModel):
    """코드 예제."""

    language: str = Field(description="프로그래밍 언어")
    code: str = Field(description="코드 내용")


class FilteredRepository(BaseModel):
    """필터링된 저장소 정보 (요약 포함)."""

    repository: Repository = Field(description="원본 저장소 정보")
    relevance_score: int = Field(ge=1, le=10, description="관련성 점수 (1-10)")
    summary: str = Field(description="AI 생성 요약")
    matched_interests: list[str] = Field(
        default_factory=list,
        description="매칭된 관심 키워드",
    )
    license: str | None = Field(default=None, description="라이선스 SPDX ID")
    is_open_source: bool = Field(default=False, description="오픈소스 여부")
    code_examples: list[CodeExample] = Field(
        default_factory=list,
        description="README에서 추출한 예제 코드",
    )


class TrendItem(BaseModel):
    """통합 트렌드 아이템 (GitHub + HN 공통)."""

    source: str = Field(description="소스 ('github' | 'hackernews')")
    source_id: str = Field(description="소스별 고유 ID")
    title: str = Field(description="제목")
    url: str = Field(description="URL")
    description: str | None = Field(default=None, description="설명")
    metadata: dict[str, int | str] = Field(
        default_factory=dict, description="소스별 메타데이터"
    )

    # AI 분석 결과 (필터링 후 채워짐)
    relevance_score: int | None = Field(default=None, description="관련성 점수")
    summary: str | None = Field(default=None, description="요약")
    matched_interests: list[str] = Field(
        default_factory=list, description="매칭된 관심사"
    )
    code_example: str | None = Field(default=None, description="예제 코드")

    # 라이선스 (GitHub만)
    license: str | None = Field(default=None, description="라이선스")
    is_open_source: bool = Field(default=False, description="오픈소스 여부")
