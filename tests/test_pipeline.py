# Tests unitarios de componentes del pipeline
# Ejecutar con: pytest tests/test_pipeline.py -v

import pytest
from unittest.mock import Mock


# =============================================================================
# TESTS DE VALIDACIÓN SQL
# =============================================================================

@pytest.mark.unit
class TestValidator:
    """Tests para validación de SQL seguro"""

    def test_rejects_delete(self):
        from core.services.security import is_safe_sql
        assert not is_safe_sql("DELETE FROM users")

    def test_rejects_drop(self):
        from core.services.security import is_safe_sql
        assert not is_safe_sql("DROP TABLE users")

    def test_accepts_select(self):
        from core.services.security import is_safe_sql
        assert is_safe_sql("SELECT * FROM users")

    def test_rejects_update(self):
        from core.services.security import is_safe_sql
        assert not is_safe_sql("UPDATE users SET name = 'test'")

    def test_rejects_insert(self):
        from core.services.security import is_safe_sql
        assert not is_safe_sql("INSERT INTO users VALUES (1, 'test')")

    def test_rejects_truncate(self):
        from core.services.security import is_safe_sql
        assert not is_safe_sql("TRUNCATE TABLE users")

    def test_rejects_alter(self):
        from core.services.security import is_safe_sql
        assert not is_safe_sql("ALTER TABLE users ADD COLUMN hack VARCHAR(100)")

    def test_accepts_select_with_join(self):
        from core.services.security import is_safe_sql
        sql = "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        assert is_safe_sql(sql)

    def test_accepts_select_with_subquery(self):
        from core.services.security import is_safe_sql
        sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"
        assert is_safe_sql(sql)


# =============================================================================
# TESTS DE SCHEMA RETRIEVER
# =============================================================================

@pytest.mark.unit
class TestSchemaRetriever:
    """Tests para el recuperador de schemas"""

    def test_empty_init(self):
        from core.services.schema.retriever import SchemaRetriever
        r = SchemaRetriever(Mock(), schemas=[])
        assert r.schemas == []

    def test_with_schemas(self, sample_schemas):
        from core.services.schema.retriever import SchemaRetriever
        r = SchemaRetriever(Mock(), schemas=sample_schemas)
        assert len(r.schemas) == 3

    def test_get_by_name_found(self, sample_schemas):
        from core.services.schema.retriever import SchemaRetriever
        r = SchemaRetriever(Mock(), schemas=sample_schemas)
        result = r.get_by_name("usuarios")
        assert result is not None
        assert result["metadata"]["table_name"] == "usuarios"

    def test_get_by_name_not_found(self, sample_schemas):
        from core.services.schema.retriever import SchemaRetriever
        r = SchemaRetriever(Mock(), schemas=sample_schemas)
        assert r.get_by_name("noexiste") is None

    def test_get_available_schemas(self, sample_schemas):
        from core.services.schema.retriever import SchemaRetriever
        r = SchemaRetriever(Mock(), schemas=sample_schemas)
        schemas = r.get_available_schemas()
        assert "public" in schemas

    def test_get_all_table_names(self, sample_schemas):
        from core.services.schema.retriever import SchemaRetriever
        r = SchemaRetriever(Mock(), schemas=sample_schemas)
        tables = [s["metadata"]["table_name"] for s in r.schemas]
        assert "usuarios" in tables
        assert "productos" in tables
        assert "pedidos" in tables


# =============================================================================
# TESTS DE SQL GENERATOR
# =============================================================================

@pytest.mark.unit
class TestSQLGenerator:
    """Tests para el generador de SQL"""

    def test_clean_removes_markdown(self, sample_schemas):
        from core.services.sql.generator import SQLGenerator
        gen = SQLGenerator(Mock())
        raw = "```sql\nSELECT * FROM usuarios;\n```"
        result = gen._clean(raw, sample_schemas, "public")
        assert "SELECT" in result
        assert "```" not in result

    def test_clean_adds_limit(self, sample_schemas):
        from core.services.sql.generator import SQLGenerator
        gen = SQLGenerator(Mock())
        raw = "SELECT * FROM usuarios"
        result = gen._clean(raw, sample_schemas, "public")
        assert "LIMIT" in result

    def test_clean_preserves_existing_limit(self, sample_schemas):
        from core.services.sql.generator import SQLGenerator
        gen = SQLGenerator(Mock())
        raw = "SELECT * FROM usuarios LIMIT 10"
        result = gen._clean(raw, sample_schemas, "public")
        assert "LIMIT 10" in result
        # No debería tener doble LIMIT
        assert result.count("LIMIT") == 1

    def test_clean_handles_semicolon(self, sample_schemas):
        from core.services.sql.generator import SQLGenerator
        gen = SQLGenerator(Mock())
        raw = "SELECT * FROM usuarios;"
        result = gen._clean(raw, sample_schemas, "public")
        # Debería manejar el punto y coma correctamente
        assert "SELECT" in result


# =============================================================================
# TESTS DE INPUT SANITIZER
# =============================================================================

@pytest.mark.unit
class TestInputSanitizer:
    """Tests para sanitización de input"""

    def test_sanitizer_exists(self):
        from core.services.security import InputSanitizer
        sanitizer = InputSanitizer()
        assert sanitizer is not None

    def test_sanitizer_handles_normal_input(self):
        from core.services.security import InputSanitizer
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_query("¿Cuántos usuarios hay?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_sanitizer_handles_special_chars(self):
        from core.services.security import InputSanitizer
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_query("test <script>alert('xss')</script>")
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
