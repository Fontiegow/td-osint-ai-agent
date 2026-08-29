from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Tehran OSINT Agent"
    ENVIRONMENT: str = "development"

    # Milestone 1 Settings
    POSTGRES_USER: str = "osint_user"
    POSTGRES_PASSWORD: str = "osint_password"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "osint_db"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    QDRANT_HOST: str = "localhost"

    # LLM Settings (Milestone 2)
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "llama3.2:3b"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_API_KEY: str = "not-needed-for-local"
    LLM_TIMEOUT: float = 60.0
    LLM_MAX_RETRIES: int = 3
    LLM_TEMPERATURE: float = 0.7

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=False,
    )


settings = Settings()