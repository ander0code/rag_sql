# Servicio de Seguridad - Consolidado

import re
import html
import logging
from typing import Tuple
logger = logging.getLogger(__name__)


# PATRONES Y CONSTANTES

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
]

SYSTEM_TABLES = [
    r"pg_catalog\.",
    r"information_schema\.",
    r"pg_shadow",
    r"pg_authid",
    r"pg_roles",
    r"pg_user",
    r"pg_password",
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

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
    r"disregard\s+(previous|all|above)",
    r"forget\s+(previous|all|your)\s+(instructions?|training)",
    r"override\s+(system|previous)",
    r"you\s+are\s+(now|a)\s+(hacker|admin|root|developer)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if|a)",
    r"show\s+(me\s+)?(your|the)\s+(system\s+)?prompt",
    r"reveal\s+(your|system)\s+(instructions?|prompt)",
]

SENSITIVE_COLUMNS = [
    r"password",
    r"passwd",
    r"pwd",
    r"pass_hash",
    r"api_key",
    r"secret_key",
    r"private_key",
    r"access_token",
    r"refresh_token",
    r"credit_card",
    r"card_number",
    r"cvv",
    r"ssn",
    r"hash",
    r"salt",
]

DANGEROUS_KEYWORDS = [
    "drop table",
    "delete from",
    "truncate",
    "alter table",
    "information_schema",
    "pg_catalog",
    "mysql.user",
]


# SQL VALIDATOR

class SQLValidator:
    """Valida que el SQL sea seguro"""

    def __init__(self):
        self.dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
        ]
        self.dangerous_functions = [
            re.compile(p, re.IGNORECASE) for p in DANGEROUS_FUNCTIONS
        ]
        self.system_tables = [re.compile(p, re.IGNORECASE) for p in SYSTEM_TABLES]
        self.sensitive_patterns = [
            re.compile(rf"\b{p}\b", re.IGNORECASE) for p in SENSITIVE_COLUMNS
        ]

    def validate(self, sql: str) -> Tuple[bool, str]:
        """Valida SQL, retorna (is_safe, reason)"""
        if not sql:
            return False, "SQL vacío"

        sql_upper = sql.upper().strip()
        sql_clean = self._remove_strings(sql)

        # Solo SELECT
        if not sql_upper.startswith("SELECT"):
            return False, "Solo se permiten consultas SELECT"

        # Comandos peligrosos
        for cmd in DANGEROUS_COMMANDS:
            if re.search(rf"\b{cmd}\b", sql_clean, re.IGNORECASE):
                logger.warning(f"Comando peligroso: {cmd}")
                return False, f"Comando no permitido: {cmd}"

        # Funciones peligrosas
        for pattern in self.dangerous_functions:
            if pattern.search(sql_clean):
                return False, "Función de sistema no permitida"

        # Tablas del sistema
        for pattern in self.system_tables:
            if pattern.search(sql):
                return False, "Acceso a tablas del sistema no permitido"

        # Patrones de inyección
        for pattern in self.dangerous_patterns:
            if pattern.search(sql):
                return False, "Patrón de SQL injection detectado"

        # Múltiples statements
        if self._has_multiple_statements(sql_clean):
            return False, "Múltiples statements no permitidos"

        # Columnas sensibles
        for pattern in self.sensitive_patterns:
            if pattern.search(sql):
                return False, "Acceso a columna sensible no permitido"

        return True, ""

    def _remove_strings(self, sql: str) -> str:
        result = re.sub(r"'[^']*'", "''", sql)
        return re.sub(r'"[^"]*"', '""', result)

    def _has_multiple_statements(self, sql: str) -> bool:
        parts = [p.strip() for p in sql.split(";") if p.strip()]
        return len(parts) > 1



# PROMPT GUARD

class PromptGuard:
    """Detecta intentos de prompt injection"""

    def __init__(self):
        self.patterns = [
            re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS
        ]

    def check(self, text: str) -> Tuple[bool, str]:
        """Verifica si hay prompt injection"""
        if not text:
            return True, ""

        text_lower = text.lower()

        for pattern in self.patterns:
            if pattern.search(text):
                logger.warning(f"Prompt injection: {text[:50]}...")
                return False, "Patrón sospechoso detectado"

        for keyword in DANGEROUS_KEYWORDS:
            if keyword in text_lower:
                return False, f"Palabra clave peligrosa: {keyword}"

        return True, ""


# INPUT SANITIZER

class InputSanitizer:
    """Sanitiza entradas de usuario"""

    MAX_QUERY_LENGTH = 500

    @staticmethod
    def sanitize_query(query: str) -> str:
        if not query:
            return ""
        query = query[: InputSanitizer.MAX_QUERY_LENGTH]
        query = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", query)
        query = html.escape(query)
        query = re.sub(r"\s+", " ", query)
        return query.strip()

    @staticmethod
    def sanitize_session_id(session_id: str) -> str:
        if not session_id:
            return ""
        return re.sub(r"[^a-zA-Z0-9\-]", "", session_id)[:32]



# SINGLETONS

_sql_validator = None
_prompt_guard = None
_sanitizer = None


def get_sql_validator() -> SQLValidator:
    global _sql_validator
    if _sql_validator is None:
        _sql_validator = SQLValidator()
    return _sql_validator


def get_prompt_guard() -> PromptGuard:
    global _prompt_guard
    if _prompt_guard is None:
        _prompt_guard = PromptGuard()
    return _prompt_guard


def get_sanitizer() -> InputSanitizer:
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = InputSanitizer()
    return _sanitizer


def is_safe_sql(sql: str) -> bool:
    """Función de conveniencia"""
    validator = get_sql_validator()
    is_safe, _ = validator.validate(sql)
    return is_safe
