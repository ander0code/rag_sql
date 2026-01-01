import pytest
from unittest.mock import Mock


class TestValidator:
    def test_rejects_delete(self):
        from core.execution.validator import is_safe_sql
        assert not is_safe_sql("DELETE FROM users")
    
    def test_rejects_drop(self):
        from core.execution.validator import is_safe_sql
        assert not is_safe_sql("DROP TABLE users")
    
    def test_accepts_select(self):
        from core.execution.validator import is_safe_sql
        assert is_safe_sql("SELECT * FROM users")


class TestSchemaRetriever:
    def test_empty_init(self):
        from core.retrieval.schema_retriever import SchemaRetriever
        r = SchemaRetriever(Mock(), schemas=[])
        assert r.schemas == []
    
    def test_with_schemas(self):
        from core.retrieval.schema_retriever import SchemaRetriever
        fake_schemas = [{"metadata": {"table_name": "productos", "schema": "public"}}]
        r = SchemaRetriever(Mock(), schemas=fake_schemas)
        assert len(r.schemas) == 1
    
    def test_get_by_name(self):
        from core.retrieval.schema_retriever import SchemaRetriever
        fake_schemas = [{"metadata": {"table_name": "productos", "schema": "public"}}]
        r = SchemaRetriever(Mock(), schemas=fake_schemas)
        assert r.get_by_name("productos") is not None
        assert r.get_by_name("noexiste") is None


class TestSQLGenerator:
    def test_clean_markdown(self):
        from core.generation.sql_generator import SQLGenerator
        gen = SQLGenerator(Mock())
        result = gen._clean("```sql\nSELECT * FROM t;\n```", "public", set(), set())
        assert "SELECT" in result
        assert "```" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
