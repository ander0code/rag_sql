# Configuración centralizada usando Pydantic Settings

import os
from pathlib import Path
from typing import Optional
from enum import Enum
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"


# Configuración de base de datos multi-tipo
class DatabaseSettings(BaseSettings):
    db_type: str = os.getenv("DB_TYPE", "postgresql")

    host: str = os.getenv("DB_HOST", "localhost")
    port: str = os.getenv("DB_PORT", "5432")
    database: str = os.getenv("DB_NAME", "postgres")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")

    ssl_mode: str = os.getenv("DB_SSL_MODE", "disable")
    ssl_cert: Optional[str] = os.getenv("DB_SSL_CERT", None)
    ssl_key: Optional[str] = os.getenv("DB_SSL_KEY", None)
    ssl_ca: Optional[str] = os.getenv("DB_SSL_CA", None)

    database_url: str = os.getenv("DATABASE_URL", "")

    @property
    def db_uri(self) -> str:
        if self.database_url:
            return self._parse_database_url()

        if self.db_type == "postgresql":
            return self._postgresql_uri()
        elif self.db_type == "mysql":
            return self._mysql_uri()
        elif self.db_type == "sqlserver":
            return self._sqlserver_uri()
        elif self.db_type == "sqlite":
            return self._sqlite_uri()
        else:
            return self._postgresql_uri()

    def _postgresql_uri(self) -> str:
        uri = f"host={self.host} port={self.port} dbname={self.database} user={self.user} password={self.password}"
        if self.ssl_mode != "disable":
            uri += f" sslmode={self.ssl_mode}"
            if self.ssl_cert:
                uri += f" sslcert={self.ssl_cert}"
            if self.ssl_key:
                uri += f" sslkey={self.ssl_key}"
            if self.ssl_ca:
                uri += f" sslrootcert={self.ssl_ca}"
        return uri

    def _mysql_uri(self) -> str:
        ssl_config = ""
        if self.ssl_mode != "disable":
            ssl_config = f"&ssl_mode={self.ssl_mode}"
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset=utf8mb4{ssl_config}"

    def _sqlserver_uri(self) -> str:
        driver = "ODBC Driver 17 for SQL Server"
        encrypt = "yes" if self.ssl_mode != "disable" else "no"
        return f"mssql+pyodbc://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?driver={driver}&Encrypt={encrypt}"

    def _sqlite_uri(self) -> str:
        return f"sqlite:///{self.database}"

    def _parse_database_url(self) -> str:
        url = self.database_url

        if url.startswith("postgresql://") or url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://")
            url = url.replace("postgresql://", "")
            auth, rest = url.split("@")
            user, password = auth.split(":")
            host_port, db = rest.split("/")
            if ":" in host_port:
                host, port = host_port.split(":")
            else:
                host, port = host_port, "5432"

            uri = f"host={host} port={port} dbname={db} user={user} password={password}"
            if self.ssl_mode != "disable":
                uri += f" sslmode={self.ssl_mode}"
            return uri

        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+pymysql://")

        return url


# Configuración de APIs de LLM
class AISettings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = "deepseek-chat"
    openai_model: str = "gpt-4o-mini"
    temperature: float = 0.0


class LogSettings(BaseSettings):
    level: str = "INFO"


# Configuración principal de la aplicación
class Settings(BaseSettings):
    app_name: str = "RAG-SQL"
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    session_ttl: int = int(os.getenv("SESSION_TTL", "1800"))
    max_history: int = int(os.getenv("MAX_HISTORY", "10"))

    db: DatabaseSettings = DatabaseSettings()
    ai: AISettings = AISettings()
    logs: LogSettings = LogSettings()


settings = Settings()
