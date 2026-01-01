# Logger de auditoría: registra eventos de seguridad

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

AUDIT_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "audit.log"


# Registra eventos de seguridad en archivo JSON
class AuditLogger:
    def __init__(self):
        self._ensure_log_dir()
        self.enabled = settings.debug

    def _ensure_log_dir(self):
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Registra un evento genérico
    def log(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        query: Optional[str] = None,
        sql: Optional[str] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        if not self.enabled:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "session_id": session_id,
            "ip_address": ip_address,
            "query": query[:200] if query else None,
            "sql": sql[:500] if sql else None,
            "result_preview": result[:100] if result else None,
            "error": error,
            "metadata": metadata,
        }

        event = {k: v for k, v in event.items() if v is not None}

        try:
            with open(AUDIT_LOG_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Error escribiendo audit log: {e}")

    def log_request(self, session_id: str, ip: str, query: str):
        self.log("REQUEST", session_id=session_id, ip_address=ip, query=query)

    def log_sql_generated(self, session_id: str, query: str, sql: str):
        self.log("SQL_GENERATED", session_id=session_id, query=query, sql=sql)

    def log_sql_blocked(self, session_id: str, sql: str, reason: str):
        self.log("SQL_BLOCKED", session_id=session_id, sql=sql, error=reason)
        logger.warning(f"SQL bloqueado para {session_id}: {reason}")

    def log_prompt_injection(self, session_id: str, ip: str, query: str):
        self.log("PROMPT_INJECTION", session_id=session_id, ip_address=ip, query=query)
        logger.warning(f"Prompt injection de {ip}: {query[:50]}...")

    def log_rate_limit(self, ip: str, session_id: Optional[str] = None):
        self.log("RATE_LIMITED", session_id=session_id, ip_address=ip)
        logger.warning(f"Rate limit: {ip}")

    def log_response(self, session_id: str, result: str, tokens: int):
        self.log(
            "RESPONSE",
            session_id=session_id,
            result=result,
            metadata={"tokens": tokens},
        )


_audit_logger = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
