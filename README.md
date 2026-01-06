# trend-sieve

GitHub Trending에서 저장소를 수집하고, AI로 관심 분야를 필터링하여 요약해주는 CLI 도구입니다.

## 주요 기능

- GitHub Trending 페이지에서 인기 저장소 자동 수집
- Gemini AI를 활용한 관심 키워드 기반 필터링
- 각 저장소에 대한 관련성 점수 및 한국어 요약 생성

## 요구사항

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- Gemini API 키

## 설치

```bash
# 저장소 클론
git clone https://github.com/your-username/trend-sieve.git
cd trend-sieve

# 의존성 설치
uv sync
```

## 설정

`.env` 파일을 생성하고 Gemini API 키를 설정합니다:

```bash
cp .env.example .env
```

```env
GEMINI_API_KEY=your-api-key-here
```

API 키는 [Google AI Studio](https://aistudio.google.com/app/apikey)에서 발급받을 수 있습니다.

## 사용법

```bash
uv run trend-sieve
```

### 출력 예시

```
============================================================
🔥 오늘의 AI/LLM 트렌드 저장소
============================================================

### 1. openai/gpt-4-turbo
⭐ 12,345 (+1,234 today)
📝 Python
🔗 https://github.com/openai/gpt-4-turbo
📊 관련성: 9/10
🏷️  키워드: LLM, GPT, AI Agent

GPT-4 Turbo 모델을 활용한 새로운 기능을 제공하는 저장소입니다...
------------------------------------------------------------
```

## 기본 관심 키워드

- AI Agent, LLM, RAG, Vector DB, Embedding
- GPT, Claude, Langchain, LlamaIndex, Ollama
- Fine-tuning, Prompt Engineering, AI Assistant
- Machine Learning, Deep Learning, Transformer

`config.py`에서 관심 키워드와 관련성 임계값을 수정할 수 있습니다.

## 라이선스

MIT
