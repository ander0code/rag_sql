# Validador SQL básico: bloquea comandos peligrosos

import logging

logger = logging.getLogger(__name__)

DANGEROUS_KEYWORDS = ["DELETE", "UPDATE", "INSERT", "DROP", "TRUNCATE", "ALTER"]


# Verifica que el SQL sea solo SELECT sin comandos peligrosos
def is_safe_sql(sql: str) -> bool:
    normalized = f" {sql.upper()} "
    for kw in DANGEROUS_KEYWORDS:
        if f" {kw} " in normalized:
            logger.warning(f"SQL peligroso: {kw}")
            return False
    return "SELECT" in sql.upper()
