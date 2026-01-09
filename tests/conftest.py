# Configuración central de pytest y fixtures compartidos

import pytest
import os
import sys
from unittest.mock import Mock, MagicMock, patch

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# MARKERS PERSONALIZADOS

def pytest_configure(config):
    """Registrar markers personalizados"""
    config.addinivalue_line(
        "markers", "unit: Tests unitarios rápidos (sin servicios externos)"
    )
    config.addinivalue_line(
        "markers", "integration: Tests de integración (requieren Redis/DB)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests lentos (LLM real, etc.)"
    )


# FIXTURES DE MOCK PARA TESTS UNITARIOS

@pytest.fixture
def mock_llm():
    """Mock del LLM para evitar llamadas reales (costosas y lentas)"""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="SELECT id, nombre FROM usuarios LIMIT 100;")
    return mock


@pytest.fixture
def mock_deps():
    """Mock completo de AppDependencies para tests de API"""
    mock = MagicMock()
    mock.pipeline.get_info.return_value = {
        "total_tables": 5,
        "schemas": ["public"],
        "llm": "mock-llm",
    }
    mock.pipeline.run.return_value = ("Resultado mock", 100)
    mock.pipeline._scan_db.return_value = None
    mock.session_manager.create_session.return_value = "test-session-123"
    mock.session_manager.get_context_string.return_value = ""
    mock.session_manager.delete_session.return_value = True
    mock.rate_limiter.check.return_value = (True, 29)
    mock.sanitizer.sanitize_query.side_effect = lambda x: x
    mock.prompt_guard.check.return_value = (True, None)
    mock.topic_detector.check.return_value = (True, None)
    mock.output_validator.validate.return_value = (True, "Resultado mock")
    mock.audit_logger.log_query = Mock()
    mock.audit_logger.log_security_event = Mock()
    return mock


@pytest.fixture(scope="session")
def sample_schemas():
    """Schemas de ejemplo para tests"""
    return [
        {
            "metadata": {"table_name": "usuarios", "schema": "public"},
            "page_content": """
            CREATE TABLE public.usuarios (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100),
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            );
            """,
        },
        {
            "metadata": {"table_name": "productos", "schema": "public"},
            "page_content": """
            CREATE TABLE public.productos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100),
                precio DECIMAL(10,2),
                stock INTEGER DEFAULT 0
            );
            """,
        },
        {
            "metadata": {"table_name": "pedidos", "schema": "public"},
            "page_content": """
            CREATE TABLE public.pedidos (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id),
                total DECIMAL(10,2),
                estado VARCHAR(20) DEFAULT 'pendiente'
            );
            """,
        },
    ]


# FIXTURES DE INTEGRACIÓN (scope="session" para reusar conexiones)

@pytest.fixture(scope="session")
def redis_client():
    """Cliente Redis real - reutilizado en toda la sesión de tests"""
    try:
        from adapters.outbound.cache import get_redis_client
        client = get_redis_client()
        if client.is_connected():
            yield client
        else:
            pytest.skip("Redis no disponible")
    except Exception as e:
        pytest.skip(f"Redis no disponible: {e}")


@pytest.fixture(scope="session")
def db_connection():
    """Conexión a base de datos real - reutilizada en toda la sesión"""
    try:
        from config import settings
        from adapters.outbound.database import get_database_adapter
        
        # Obtener tipo y conexión desde settings
        db_type = settings.db.db_type
        connection_string = settings.db.db_uri
        
        adapter = get_database_adapter(db_type, connection_string)
        
        # Verificar que podemos conectar
        result = adapter.execute("SELECT 1 as test")
        if "error" not in result:
            yield adapter
        else:
            pytest.skip(f"DB no disponible: {result.get('error')}")
    except Exception as e:
        pytest.skip(f"DB no disponible: {e}")


@pytest.fixture(scope="session")
def schema_retriever(db_connection, sample_schemas):
    """SchemaRetriever con schemas reales o de ejemplo"""
    from core.services.schema.retriever import SchemaRetriever
    
    # Intentar usar schemas reales si la DB está conectada
    try:
        from adapters.outbound.database import get_database_adapter
        adapter = get_database_adapter()
        real_schemas = adapter.get_schema_documents()
        if real_schemas:
            return SchemaRetriever(MagicMock(), schemas=real_schemas)
    except Exception:
        # Si falla obtener schemas reales, usamos los de ejemplo
        pass
    
    # Fallback a schemas de ejemplo
    return SchemaRetriever(MagicMock(), schemas=sample_schemas)


# FIXTURES PARA TESTS DE API

@pytest.fixture
def api_client(mock_deps):
    """Cliente de API con dependencias mockeadas"""
    from fastapi.testclient import TestClient
    
    with patch("adapters.inbound.dependencies.AppDependencies") as MockDeps, \
         patch("adapters.inbound.routes.health.get_redis_client") as mock_redis, \
         patch("adapters.inbound.routes.admin.get_metrics") as mock_metrics, \
         patch("adapters.inbound.routes.query.get_metrics"):

        MockDeps.get_instance.return_value = mock_deps

        mock_redis_instance = MagicMock()
        mock_redis_instance.is_connected.return_value = True
        mock_redis.return_value = mock_redis_instance
        mock_metrics.return_value = MagicMock()

        from adapters.inbound.api import app
        yield TestClient(app)


# UTILIDADES PARA TESTS

@pytest.fixture
def clean_test_keys(redis_client):
    """Limpia claves de test en Redis después del test"""
    created_keys = []
    
    def register_key(key: str):
        created_keys.append(key)
        return key
    
    yield register_key
    
    # Cleanup - usar client (no _client)
    for key in created_keys:
        try:
            redis_client.client.delete(key)
        except Exception:
            # Ignorar errores de limpieza (no crítico)
            pass
