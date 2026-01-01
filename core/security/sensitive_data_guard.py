# Sensitive data guard: bloquea acceso a datos sensibles

import re
import logging
from typing import Tuple, List, Set

logger = logging.getLogger(__name__)

DEFAULT_SENSITIVE_COLUMNS = [
    r"password",
    r"passwd",
    r"pwd",
    r"pass_hash",
    r"password_hash",
    r"api_key",
    r"apikey",
    r"api_secret",
    r"secret_key",
    r"private_key",
    r"access_token",
    r"refresh_token",
    r"auth_token",
    r"bearer_token",
    r"jwt",
    r"session_token",
    r"csrf_token",
    r"credit_card",
    r"card_number",
    r"cvv",
    r"card_cvv",
    r"account_number",
    r"routing_number",
    r"bank_account",
    r"ssn",
    r"social_security",
    r"tax_id",
    r"national_id",
    r"hash",
    r"salt",
    r"secret",
    r"encryption_key",
    r"private",
]

DEFAULT_SENSITIVE_TABLES = [
    r"users?",
    r"usuarios?",
    r"accounts?",
    r"cuentas?",
    r"auth",
    r"authentication",
    r"credentials",
    r"login",
    r"sessions?",
    r"tokens?",
    r"api_keys?",
    r"oauth",
    r"admins?",
    r"roles?",
    r"permissions?",
    r"privileges?",
    r"audit_logs?",
    r"security_logs?",
    r"payments?",
    r"billing",
    r"subscriptions?",
    r"invoices?",
]

SYSTEM_SCHEMAS = {
    "postgresql": [r"pg_catalog", r"information_schema", r"pg_toast"],
    "mysql": [r"mysql", r"information_schema", r"performance_schema", r"sys"],
    "sqlserver": [r"sys", r"INFORMATION_SCHEMA", r"master", r"msdb", r"tempdb"],
}


# Bloquea acceso a columnas y tablas sensibles
class SensitiveDataGuard:
    def __init__(
        self,
        sensitive_columns: List[str] = None,
        sensitive_tables: List[str] = None,
        allowed_tables: List[str] = None,
        db_type: str = "postgresql",
    ):
        self._columns = sensitive_columns or DEFAULT_SENSITIVE_COLUMNS
        self._tables = sensitive_tables or DEFAULT_SENSITIVE_TABLES
        self._allowed_tables: Set[str] = set(allowed_tables or [])
        self._db_type = db_type

        self._column_patterns = [
            re.compile(rf"\b{col}\b", re.IGNORECASE) for col in self._columns
        ]
        self._table_patterns = [
            re.compile(rf"\b{tbl}\b", re.IGNORECASE) for tbl in self._tables
        ]
        self._system_patterns = [
            re.compile(rf"\b{sch}\b", re.IGNORECASE)
            for sch in SYSTEM_SCHEMAS.get(db_type, [])
        ]

    # Verifica si el SQL accede a datos sensibles
    def check_sql(self, sql: str) -> Tuple[bool, str]:
        sql_upper = sql.upper()

        if "SELECT" in sql_upper:
            for pattern in self._column_patterns:
                if pattern.search(sql):
                    col_match = pattern.pattern.replace(r"\b", "")
                    logger.warning(f"Columna sensible bloqueada: {col_match}")
                    return False, f"Acceso a columna sensible no permitido: {col_match}"

        for pattern in self._table_patterns:
            if pattern.search(sql):
                match = pattern.search(sql)
                if match:
                    table_name = match.group(0).lower()
                    if table_name not in self._allowed_tables:
                        logger.warning(f"Tabla sensible bloqueada: {table_name}")
                        return (
                            False,
                            f"Acceso a tabla sensible no permitido: {table_name}",
                        )

        for pattern in self._system_patterns:
            if pattern.search(sql):
                logger.warning("Schema del sistema bloqueado")
                return False, "Acceso a schema del sistema no permitido"

        return True, ""

    def add_allowed_table(self, table: str):
        self._allowed_tables.add(table.lower())

    def remove_allowed_table(self, table: str):
        self._allowed_tables.discard(table.lower())

    def set_db_type(self, db_type: str):
        self._db_type = db_type
        self._system_patterns = [
            re.compile(rf"\b{sch}\b", re.IGNORECASE)
            for sch in SYSTEM_SCHEMAS.get(db_type, [])
        ]

    # Carga columnas y tablas sensibles desde schema descubierto
    def load_from_discovered_schema(self, schemas: list):
        discovered_columns = set()
        discovered_tables = set()

        for schema_info in schemas:
            metadata = schema_info.get("metadata", {})

            sensitive_cols = metadata.get("sensitive_columns", [])
            for col in sensitive_cols:
                discovered_columns.add(col.lower())

            if metadata.get("is_sensitive_table", False):
                table_name = metadata.get("table_name", "")
                if table_name:
                    discovered_tables.add(table_name.lower())

        for col in discovered_columns:
            pattern = re.compile(rf"\b{re.escape(col)}\b", re.IGNORECASE)
            self._column_patterns.append(pattern)

        for tbl in discovered_tables:
            pattern = re.compile(rf"\b{re.escape(tbl)}\b", re.IGNORECASE)
            self._table_patterns.append(pattern)

        if discovered_columns or discovered_tables:
            logger.info(
                f"Cargadas {len(discovered_columns)} columnas y "
                f"{len(discovered_tables)} tablas sensibles del schema"
            )


_sensitive_guard = None


def get_sensitive_guard() -> SensitiveDataGuard:
    global _sensitive_guard
    if _sensitive_guard is None:
        try:
            from infrastructure.config.settings import settings

            custom_columns = getattr(settings, "sensitive_columns", None)
            custom_tables = getattr(settings, "sensitive_tables", None)
            allowed_tables = getattr(settings, "allowed_tables", None)
            db_type = getattr(settings, "db_type", "postgresql")

            _sensitive_guard = SensitiveDataGuard(
                sensitive_columns=custom_columns,
                sensitive_tables=custom_tables,
                allowed_tables=allowed_tables,
                db_type=db_type,
            )
        except Exception:
            _sensitive_guard = SensitiveDataGuard()

    return _sensitive_guard
