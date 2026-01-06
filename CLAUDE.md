# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

trend-sieve는 GitHub Trending에서 저장소를 수집하고, Gemini AI로 관심 키워드(AI/LLM 관련) 기반 필터링 및 요약을 생성하는 CLI 도구입니다.

## Commands

```bash
# 의존성 설치
uv sync

# CLI 실행
uv run trend-sieve

# 린트/포맷/타입 검사 (pre-commit)
uv run pre-commit run --all-files
```

## Architecture

```
src/trend_sieve/
├── main.py          # CLI 엔트리포인트, 파이프라인 오케스트레이션
├── config.py        # pydantic-settings 기반 설정 (환경변수, 관심 키워드)
├── models.py        # Pydantic 모델 (Repository, FilteredRepository)
├── sources/         # 데이터 수집 계층
│   ├── base.py      # Source 프로토콜 정의
│   └── github.py    # GitHub Trending 스크래퍼 (httpx + selectolax)
└── filters/         # 필터링 계층
    └── gemini.py    # Gemini API로 관련성 평가 및 요약 생성
```

**파이프라인 흐름**: `GitHubTrendingSource.fetch()` → `GeminiFilter.filter()` → 콘솔 출력

## Environment Variables

`.env` 파일에 설정:
- `GEMINI_API_KEY`: Gemini API 키 (필수)
