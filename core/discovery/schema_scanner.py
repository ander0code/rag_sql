"""Scanner automático de esquemas de base de datos."""

import json
import logging
from pathlib import Path
from typing import Optional
from core.execution.query_executor import QueryExecutor

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "infrastructure" / "config" / "schemas"


class SchemaScanner:
    def __init__(self, db_uri: str):
        self.executor = QueryExecutor(db_uri)
        self.schemas_data = {}
    
    def scan(self, target_schema: Optional[str] = None) -> dict:
        """Escanea la DB. Si target_schema es None, escanea todos."""
        schemas = self._get_user_schemas()
        
        if not schemas:
            logger.warning("No se encontraron schemas")
            return {}
        
        # Si solo hay un schema, usarlo
        if len(schemas) == 1:
            target_schema = schemas[0]
            logger.info(f"DB con un solo schema: {target_schema}")
        
        # Si se especifica uno, escanearlo
        if target_schema:
            if target_schema in schemas:
                self.schemas_data = {target_schema: self._scan_schema(target_schema)}
            else:
                logger.error(f"Schema '{target_schema}' no existe")
                return {}
        else:
            # Escanear todos
            logger.info(f"Escaneando {len(schemas)} schemas: {schemas}")
            for s in schemas:
                self.schemas_data[s] = self._scan_schema(s)
        
        return self.schemas_data
    
    def _get_user_schemas(self) -> list:
        """Obtiene schemas del usuario (excluye system schemas)."""
        try:
            result = self.executor.execute("""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                AND schema_name NOT LIKE 'pg_%'
                ORDER BY schema_name
            """)
            return [r[0] for r in result.get("data", [])]
        except:
            return []
    
    def _scan_schema(self, schema: str) -> list:
        """Escanea todas las tablas de un schema."""
        tables = []
        
        # Obtener tablas
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
    
    def _scan_table(self, schema: str, table: str) -> dict:
        """Escanea columnas y relaciones de una tabla."""
        # Columnas
        cols_result = self.executor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = '{schema}' AND table_name = '{table}'
            ORDER BY ordinal_position
        """)
        
        columns = [f"{r[0]} ({r[1].upper()})" for r in cols_result.get("data", [])]
        
        # Foreign keys
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
        
        return {
            "schema_text": f"Tabla '{table}' en schema {schema}. Columnas: {', '.join(columns[:5])}...",
            "metadata": {
                "table_name": table,
                "schema": schema,
                "columns": columns,
                "related_tables": related
            }
        }
    
    def save(self, filename: str = "discovered_schemas.json"):
        """Guarda los schemas descubiertos."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / filename
        
        # Convertir a formato plano
        all_tables = []
        for schema, tables in self.schemas_data.items():
            all_tables.extend(tables)
        
        data = {
            "version": "auto-discovered",
            "schemas_found": list(self.schemas_data.keys()),
            "schemas": all_tables
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Guardado: {path} ({len(all_tables)} tablas)")
        return path
    
    def get_info(self) -> dict:
        """Resumen de lo escaneado."""
        return {
            "schemas": list(self.schemas_data.keys()),
            "total_tables": sum(len(t) for t in self.schemas_data.values()),
            "single_schema": len(self.schemas_data) == 1
        }
