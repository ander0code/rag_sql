# Audit Logger - Logs de auditoría para producción

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from config.settings import settings

logger = logging.getLogger(__name__)

# Directorio para logs de auditoría
LOGS_DIR = Path(__file__).parent.parent / "logs"


class AuditLogger:
    """
    Logger de auditoría para tracking de queries y acciones.

    Comportamiento:
    - DEBUG=true (desarrollo): logs mínimos, solo a consola
    - DEBUG=false (producción): logs completos a archivo
    """

    def __init__(self, enabled: bool = True, log_to_file: bool = True):
        self.enabled = enabled
        self.log_to_file = log_to_file and not settings.debug
        self._file_handler = None

        if self.log_to_file:
            self._setup_file_logging()

    def _setup_file_logging(self):
        """Configura logging a archivo solo en producción"""
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOGS_DIR / "audit.log"

            self._file_handler = logging.FileHandler(log_file, encoding="utf-8")
            self._file_handler.setLevel(logging.INFO)
            self._file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(message)s")
            )
            logger.info(f"AuditLogger: escribiendo a {log_file}")
        except Exception as e:
            logger.warning(f"No se pudo crear archivo de auditoría: {e}")
            self.log_to_file = False

    def log_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        result_status: str = "success",
        tokens_used: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Registra una query ejecutada.

        Args:
            query: Query del usuario
            user_id: ID de usuario o sesión
            ip: IP del cliente
            result_status: "success", "error", "blocked"
            tokens_used: Tokens consumidos
            duration_ms: Duración en ms
            metadata: Datos adicionales
        """
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "query",
            "query": query[:200],  # Truncar por seguridad
            "user_id": user_id,
            "ip": ip,
            "status": result_status,
            "tokens": tokens_used,
            "duration_ms": duration_ms,
        }

        if metadata:
            entry["metadata"] = metadata

        self._write_log(entry)

    def log_security_event(
        self,
        event_type: str,
        description: str,
        ip: Optional[str] = None,
        user_id: Optional[str] = None,
        severity: str = "warning",
    ):
        """
        Registra evento de seguridad.

        Args:
            event_type: "rate_limit", "sql_injection", "prompt_injection", etc.
            description: Descripción del evento
            ip: IP del cliente
            user_id: ID de usuario
            severity: "info", "warning", "critical"
        """
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "security",
            "event": event_type,
            "description": description[:500],
            "ip": ip,
            "user_id": user_id,
            "severity": severity,
        }

        self._write_log(entry)

        # Eventos críticos siempre a consola
        if severity == "critical":
            logger.warning(f"SECURITY: {event_type} - {description[:100]}")

    def log_error(
        self,
        error_type: str,
        error_message: str,
        query: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ):
        """Registra errores del sistema"""
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error_type": error_type,
            "message": error_message[:500],
            "query": query[:200] if query else None,
        }

        if stack_trace and not settings.debug:
            entry["stack_trace"] = stack_trace[:1000]

        self._write_log(entry)

    def _write_log(self, entry: Dict[str, Any]):
        """Escribe entrada de log"""
        log_line = json.dumps(entry, ensure_ascii=False, default=str)

        if self.log_to_file and self._file_handler:
            # A archivo (producción)
            record = logging.LogRecord(
                name="audit",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=log_line,
                args=(),
                exc_info=None,
            )
            self._file_handler.emit(record)

        if settings.debug:
            # En desarrollo, log simplificado a consola
            logger.debug(
                f"Audit: {entry.get('type')} - {entry.get('status', entry.get('event', ''))}"
            )


# ============================================================================
# SINGLETON
# ============================================================================

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Obtiene instancia del AuditLogger.

    - En DEBUG=true: logs mínimos a consola
    - En DEBUG=false: logs completos a archivo
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(enabled=True, log_to_file=not settings.debug)
    return _audit_logger
