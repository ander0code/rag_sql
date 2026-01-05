# Scanner de schema: descubre tablas, columnas, ENUMs y relaciones de la DB

import json
import logging
from pathlib import Path
from typing import Optional
from core.services.sql_executor import QueryExecutor

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "schemas"


# Escanea la estructura de la base de datos PostgreSQL
class SchemaScanner:
    def __init__(self, db_uri: str):
        self.executor = QueryExecutor(db_uri)
        self.schemas_data = {}

    # Escanea todos los schemas o uno específico
    def scan(self, target_schema: Optional[str] = None) -> dict:
        schemas = self._get_user_schemas()

        if not schemas:
            logger.warning("No se encontraron schemas")
            return {}

        if len(schemas) == 1:
            target_schema = schemas[0]
            logger.info(f"DB con un solo schema: {target_schema}")

        if target_schema:
            if target_schema in schemas:
                self.schemas_data = {target_schema: self._scan_schema(target_schema)}
            else:
                logger.error(f"Schema '{target_schema}' no existe")
                return {}
        else:
            logger.info(f"Escaneando {len(schemas)} schemas: {schemas}")
            for s in schemas:
                self.schemas_data[s] = self._scan_schema(s)

        return self.schemas_data

    # Obtiene schemas del usuario (excluye system schemas)
    def _get_user_schemas(self) -> list:
        try:
            result = self.executor.execute("""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                AND schema_name NOT LIKE 'pg_%'
                ORDER BY schema_name
            """)
            return [r[0] for r in result.get("data", [])]
        except Exception as e:
            logger.error(f"Error al obtener schemas: {e}")
            return []

    # Escanea todas las tablas de un schema
    def _scan_schema(self, schema: str) -> list:
        tables = []

        result = self.executor.execute(f"""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
        """)

        for (table_name,) in result.get("data", []):
            table_info = self._scan_table(schema, table_name)
            if table_info:
                tables.append(table_info)

        logger.info(f"Schema '{schema}': {len(tables)} tablas")
        return tables

    # Escanea columnas, ENUMs, FKs y detecta datos sensibles
    def _scan_table(self, schema: str, table: str) -> dict:
        cols_result = self.executor.execute(f"""
            SELECT c.column_name, c.data_type, c.udt_name
            FROM information_schema.columns c
            WHERE c.table_schema = '{schema}' AND c.table_name = '{table}'
            ORDER BY c.ordinal_position
        """)

        columns = []
        enum_columns = {}
        sensitive_columns = []

        for r in cols_result.get("data", []):
            col_name, data_type, udt_name = r[0], r[1], r[2]

            if self._is_sensitive_column(col_name):
                sensitive_columns.append(col_name)

            if data_type == "USER-DEFINED":
                enum_values = self._get_enum_values(udt_name)
                columns.append(f"{col_name} (ENUM: {', '.join(enum_values[:5])})")
                enum_columns[col_name] = enum_values
            else:
                columns.append(f"{col_name} ({data_type.upper()})")

        fk_result = self.executor.execute(f"""
            SELECT kcu.column_name, ccu.table_name AS foreign_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu 
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND tc.table_schema = '{schema}' AND tc.table_name = '{table}'
        """)

        related = list(set(r[1] for r in fk_result.get("data", [])))

        is_sensitive_table = self._is_sensitive_table(table)

        return {
            "schema_text": f"Tabla '{table}' en schema {schema}. Columnas: {', '.join(columns[:5])}...",
            "metadata": {
                "table_name": table,
                "schema": schema,
                "columns": columns,
                "enum_columns": enum_columns,
                "related_tables": related,
                "sensitive_columns": sensitive_columns,
                "is_sensitive_table": is_sensitive_table,
            },
        }

    # Detecta columnas sensibles por su nombre
    def _is_sensitive_column(self, col_name: str) -> bool:
        col_lower = col_name.lower()

        sensitive_patterns = [
            "pass",
            "pwd",
            "password",
            "passwd",
            "secret",
            "private",
            "key",
            "token",
            "hash",
            "salt",
            "crypt",
            "api_key",
            "apikey",
            "access_token",
            "refresh_token",
            "credit",
            "card",
            "cvv",
            "ssn",
            "social",
            "auth",
            "credential",
            "bearer",
        ]

        return any(pattern in col_lower for pattern in sensitive_patterns)

    # Detecta tablas sensibles por su nombre
    def _is_sensitive_table(self, table_name: str) -> bool:
        table_lower = table_name.lower()

        sensitive_patterns = [
            "user",
            "usuario",
            "account",
            "cuenta",
            "auth",
            "login",
            "credential",
            "session",
            "token",
            "api_key",
            "secret",
            "password",
            "admin",
            "role",
            "permission",
            "privilege",
            "payment",
            "billing",
            "invoice",
            "subscription",
        ]

        return any(pattern in table_lower for pattern in sensitive_patterns)

    # Obtiene valores de un ENUM de PostgreSQL
    def _get_enum_values(self, enum_name: str) -> list:
        result = self.executor.execute(f"""
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = '{enum_name}'
            ORDER BY e.enumsortorder
        """)
        return [r[0] for r in result.get("data", [])]

    # Guarda los schemas descubiertos en JSON
    def save(self, filename: str = "discovered_schemas.json"):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / filename

        all_tables = []
        for schema, tables in self.schemas_data.items():
            all_tables.extend(tables)

        data = {
            "version": "auto-discovered",
            "schemas_found": list(self.schemas_data.keys()),
            "schemas": all_tables,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Guardado: {path} ({len(all_tables)} tablas)")
        return path

    # Retorna resumen de lo escaneado
    def get_info(self) -> dict:
        return {
            "schemas": list(self.schemas_data.keys()),
            "total_tables": sum(len(t) for t in self.schemas_data.values()),
            "single_schema": len(self.schemas_data) == 1,
        }
