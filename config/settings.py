import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

# Debug: verificar que el archivo .env existe
print(f"🔍 Buscando archivo .env en: {env_path}")
print(f"🔍 Archivo .env existe: {env_path.exists()}")

load_dotenv(env_path)

# Debug: verificar variables cargadas
print(f"🔍 DEEPSEEK_API_KEY desde .env: {os.getenv('DEEPSEEK_API_KEY', 'NO_ENCONTRADA')[:20]}...")
print(f"🔍 OPENAI_API_KEY desde .env: {os.getenv('OPENAI_API_KEY', 'NO_ENCONTRADA')[:20]}...")

class PostgresSettings(BaseSettings):
    # Nueva configuración para la base de datos de voluntarios
    host: str = os.getenv("PG_HOST", "localhost")
    port: str = os.getenv("PG_PORT", "5432")
    db: str = os.getenv("PG_DB", "voluntarios_db")
    user: str = os.getenv("PG_USER", "postgrest")
    password: str = os.getenv("PG_PASSWORD", "postgrest_password")
    # Removed default schema - will be passed per request
    
    @property
    def db_uri(self) -> str:
        return f"host={self.host} port={self.port} dbname={self.db} user={self.user} password={self.password}"
    
    @property
    def db_dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

class QdrantSettings(BaseSettings):
    # Mantener para compatibilidad pero ya no se usará
    url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection_name: str = "schemas_voluntarios"

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

# Debug final: verificar configuración cargada
print(f"🔍 Settings - Deepseek API Key: {settings.ai.deepseek_api_key[:20] if settings.ai.deepseek_api_key else 'VACÍA'}...")
print(f"🔍 Settings - OpenAI API Key: {settings.ai.openai_api_key[:20] if settings.ai.openai_api_key else 'VACÍA'}...")