# SQL validator: valida que el SQL sea seguro

import re
import logging
from typing import Tuple
from core.security.sensitive_data_guard import get_sensitive_guard

logger = logging.getLogger(__name__)

ALLOWED_COMMANDS = ["SELECT"]

DANGEROUS_COMMANDS = [
    "DROP",
    "DELETE",
    "TRUNCATE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
    "MERGE",
    "REPLACE",
    "LOAD",
    "INTO OUTFILE",
    "INTO DUMPFILE",
    "COPY",
    "VACUUM",
]

DANGEROUS_FUNCTIONS = [
    r"pg_read_file",
    r"pg_write_file",
    r"pg_ls_dir",
    r"pg_stat_file",
    r"lo_import",
    r"lo_export",
    r"dblink",
    r"copy\s+\(",
    r"pg_sleep",
    r"pg_terminate_backend",
    r"pg_cancel_backend",
    r"set_config",
    r"current_setting",
]

SYSTEM_TABLES = [
    r"pg_catalog\.",
    r"information_schema\.",
    r"pg_shadow",
    r"pg_authid",
    r"pg_roles",
    r"pg_user",
    r"pg_password",
    r"pg_hba\.conf",
]

INJECTION_PATTERNS = [
    r";\s*\w+\s+",
    r"--\s*$",
    r"/\*.*?\*/",
    r"'\s*OR\s+'?\d*'?\s*=\s*'?\d*",
    r"'\s*OR\s+1\s*=\s*1",
    r"UNION\s+(ALL\s+)?SELECT",
    r";\s*(DROP|DELETE|UPDATE|INSERT)",
]


# Valida SQL bloqueando comandos peligrosos
class SQLValidator:
    def __init__(self):
        self.dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
        ]
        self.dangerous_functions = [
            re.compile(p, re.IGNORECASE) for p in DANGEROUS_FUNCTIONS
        ]
        self.system_tables = [re.compile(p, re.IGNORECASE) for p in SYSTEM_TABLES]

    # Valida que el SQL sea seguro
    def validate(self, sql: str) -> Tuple[bool, str]:
        if not sql:
            return False, "SQL vacío"

        sql_upper = sql.upper().strip()
        sql_clean = self._remove_strings(sql)

        if not sql_upper.startswith("SELECT"):
            return False, "Solo se permiten consultas SELECT"

        for cmd in DANGEROUS_COMMANDS:
            pattern = rf"\b{cmd}\b"
            if re.search(pattern, sql_clean, re.IGNORECASE):
                logger.warning(f"Comando peligroso detectado: {cmd}")
                return False, f"Comando no permitido: {cmd}"

        for pattern in self.dangerous_functions:
            if pattern.search(sql_clean):
                logger.warning("Función peligrosa detectada")
                return False, "Función de sistema no permitida"

        for pattern in self.system_tables:
            if pattern.search(sql):
                logger.warning("Acceso a tabla de sistema detectado")
                return False, "Acceso a tablas del sistema no permitido"

        for pattern in self.dangerous_patterns:
            if pattern.search(sql):
                logger.warning("Patrón de inyección detectado")
                return False, "Patrón de SQL injection detectado"

        if self._has_multiple_statements(sql_clean):
            return False, "Múltiples statements no permitidos"

        subquery_count = sql_upper.count("SELECT")
        if subquery_count > 5:
            return False, "Demasiadas subconsultas"

        sensitive_guard = get_sensitive_guard()
        is_safe, reason = sensitive_guard.check_sql(sql)
        if not is_safe:
            return False, reason

        return True, ""

    def _remove_strings(self, sql: str) -> str:
        result = re.sub(r"'[^']*'", "''", sql)
        result = re.sub(r'"[^"]*"', '""', result)
        return result

    def _has_multiple_statements(self, sql: str) -> bool:
        parts = sql.split(";")
        meaningful_parts = [p.strip() for p in parts if p.strip()]
        return len(meaningful_parts) > 1


_sql_validator = None


def get_sql_validator() -> SQLValidator:
    global _sql_validator
    if _sql_validator is None:
        _sql_validator = SQLValidator()
    return _sql_validator


def is_safe_sql(sql: str) -> bool:
    validator = get_sql_validator()
    is_safe, _ = validator.validate(sql)
    return is_safe
