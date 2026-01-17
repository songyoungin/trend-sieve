"""설정 관리 모듈."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    gemini_api_key: str = Field(description="Gemini API 키")
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="사용할 Gemini 모델",
    )

    interests: list[str] = Field(
        default=[
            "AI Agent",
            "LLM",
            "RAG",
            "Vector DB",
            "Embedding",
            "GPT",
            "Claude",
            "Langchain",
            "LlamaIndex",
            "Ollama",
            "Fine-tuning",
            "Prompt Engineering",
            "AI Assistant",
            "Machine Learning",
            "Deep Learning",
            "Transformer",
        ],
        description="관심 키워드 목록",
    )

    relevance_threshold: int = Field(
        default=6,
        ge=1,
        le=10,
        description="관련성 점수 임계값 (1-10)",
    )

    # Supabase
    supabase_url: str | None = Field(default=None, description="Supabase URL")
    supabase_key: str | None = Field(default=None, description="Supabase anon key")

    # Slack
    slack_webhook_url: str | None = Field(default=None, description="Slack Webhook URL")


settings = Settings()
