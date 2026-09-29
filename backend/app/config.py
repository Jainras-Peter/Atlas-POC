from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Which LLM backend to use: "groq" | "gemini"
    active_provider: str = "groq"
    # Model id for the active provider (overrides provider-specific defaults)
    active_model: str = ""

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "ai_poc"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def provider(self) -> str:
        return (self.active_provider or "groq").strip().lower()

    @property
    def model_name(self) -> str:
        if self.active_model and self.active_model.strip():
            return self.active_model.strip()
        if self.provider == "gemini":
            return self.gemini_model
        return self.groq_model


settings = Settings()
