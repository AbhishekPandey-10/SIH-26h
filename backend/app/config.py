"""
Application Configuration Settings
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/medikiosk"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/medikiosk"
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_DB_PATH: str = "./medikiosk_dev.db"

    # Gemini LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Bhashini Indic Speech Services
    BHASHINI_USER_ID: str = ""
    BHASHINI_API_KEY: str = ""
    BHASHINI_INFERENCE_KEY: str = ""
    BHASHINI_PIPELINE_ENDPOINT: str = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    # Kiosk Configuration
    KIOSK_ID: str = "KIOSK-AIIMS-DELHI-OPD-01"
    DEFAULT_LANGUAGE: str = "hi"
    IDLE_TIMEOUT_SECONDS: int = 180

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
