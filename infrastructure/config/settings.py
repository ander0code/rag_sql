"""Configuración del proyecto."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class PostgresSettings(BaseSettings):
    # Soporta URL completa o variables separadas
    database_url: str = os.getenv("DATABASE_URL", "")
    host: str = os.getenv("PG_HOST", "localhost")
    port: str = os.getenv("PG_PORT", "5432")
    db: str = os.getenv("PG_DB", "postgres")
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "")
    
    @property
    def db_uri(self) -> str:
        # Si hay DATABASE_URL, usarla directamente (convertir formato)
        if self.database_url:
            # postgresql://user:pass@host:port/db -> formato psycopg2
            url = self.database_url
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "")
                # Parsear: user:pass@host:port/db
                auth, rest = url.split("@")
                user, password = auth.split(":")
                host_port, db = rest.split("/")
                if ":" in host_port:
                    host, port = host_port.split(":")
                else:
                    host, port = host_port, "5432"
                return f"host={host} port={port} dbname={db} user={user} password={password}"
        
        return f"host={self.host} port={self.port} dbname={self.db} user={self.user} password={self.password}"


class AISettings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = "deepseek-chat"
    openai_model: str = "gpt-4o-mini"
    temperature: float = 0.0


class LogSettings(BaseSettings):
    level: str = "INFO"


class Settings(BaseSettings):
    app_name: str = "RAG-SQL"
    debug: bool = True
    db: PostgresSettings = PostgresSettings()
    ai: AISettings = AISettings()
    logs: LogSettings = LogSettings()


settings = Settings()
