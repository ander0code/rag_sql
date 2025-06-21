import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class PostgresSettings(BaseSettings):
    host: str = os.getenv("PG_HOST", "localhost")
    port: str = os.getenv("PG_PORT", "5432")
    db: str = os.getenv("PG_DB", "pws")
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "123456789")
    
    @property
    def db_uri(self) -> str:
        return f"host={self.host} port={self.port} dbname={self.db} user={self.user} password={self.password}"

class QdrantSettings(BaseSettings):
    url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection_name: str = "custom_db_schema"

class AISettings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = "deepseek-chat"
    openai_model: str = "gpt-4o-mini"
    temperature: float = 0.0

class LogSettings(BaseSettings):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class Settings(BaseSettings):
    """Configuración global del proyecto"""
    app_name: str = "RAG-SQL"
    debug: bool = True
    db: PostgresSettings = PostgresSettings()
    vector_db: QdrantSettings = QdrantSettings()
    ai: AISettings = AISettings()
    logs: LogSettings = LogSettings()

settings = Settings()