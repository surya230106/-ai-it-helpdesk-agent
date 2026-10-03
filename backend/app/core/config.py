from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI IT Helpdesk Agent"
    database_url: str = "postgresql+psycopg://helpdesk:helpdesk@db:5432/helpdesk"
    jwt_secret: str = "change-this-in-production"
    jwt_expire_minutes: int = 1440
    ai_mode: str = "local"
    ai_provider: str = "ollama"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: float = 45.0
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"
    openai_embedding_model: str = "text-embedding-3-small"
    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 10
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
