# Inyección de dependencias para FastAPI

import logging
from typing import Optional

from adapters.factory import create_pipeline
from core.services.pipeline import Pipeline
from core.services.context import SessionManager, get_session_manager
from core.services.security import (
    PromptGuard,
    InputSanitizer,
    RateLimiter,
    AuditLogger,
    TopicDetector,
    OutputValidator,
    get_prompt_guard,
    get_sanitizer,
    get_rate_limiter,
    get_audit_logger,
    get_topic_detector,
    get_output_validator,
)

logger = logging.getLogger(__name__)


class AppDependencies:
    """
    Contenedor de dependencias de la aplicación.
    Singleton que se inicializa una vez y provee dependencias a los endpoints.
    """

    _instance: Optional["AppDependencies"] = None

    def __init__(self):
        self._pipeline: Optional[Pipeline] = None
        self._session_manager: Optional[SessionManager] = None
        self._prompt_guard: Optional[PromptGuard] = None
        self._sanitizer: Optional[InputSanitizer] = None
        self._rate_limiter: Optional[RateLimiter] = None
        self._audit_logger: Optional[AuditLogger] = None
        self._topic_detector: Optional[TopicDetector] = None
        self._output_validator: Optional[OutputValidator] = None

    @classmethod
    def get_instance(cls) -> "AppDependencies":
        """Obtiene la instancia singleton"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset para testing"""
        cls._instance = None

    # Propiedades con lazy loading

    @property
    def pipeline(self) -> Pipeline:
        if self._pipeline is None:
            self._pipeline = create_pipeline()
        return self._pipeline

    @property
    def session_manager(self) -> SessionManager:
        if self._session_manager is None:
            self._session_manager = get_session_manager()
        return self._session_manager

    @property
    def prompt_guard(self) -> PromptGuard:
        if self._prompt_guard is None:
            self._prompt_guard = get_prompt_guard()
        return self._prompt_guard

    @property
    def sanitizer(self) -> InputSanitizer:
        if self._sanitizer is None:
            self._sanitizer = get_sanitizer()
        return self._sanitizer

    @property
    def rate_limiter(self) -> RateLimiter:
        if self._rate_limiter is None:
            self._rate_limiter = get_rate_limiter()
        return self._rate_limiter

    @property
    def audit_logger(self) -> AuditLogger:
        if self._audit_logger is None:
            self._audit_logger = get_audit_logger()
        return self._audit_logger

    @property
    def topic_detector(self) -> TopicDetector:
        if self._topic_detector is None:
            self._topic_detector = get_topic_detector()
        return self._topic_detector

    @property
    def output_validator(self) -> OutputValidator:
        if self._output_validator is None:
            self._output_validator = get_output_validator()
        return self._output_validator

    def initialize_all(self) -> None:
        """Pre-carga todas las dependencias (para startup)"""
        _ = self.pipeline
        _ = self.session_manager
        _ = self.prompt_guard
        _ = self.sanitizer
        _ = self.rate_limiter
        _ = self.audit_logger
        _ = self.topic_detector
        _ = self.output_validator
        logger.info("Todas las dependencias inicializadas")


# Funciones para FastAPI Depends()

def get_deps() -> AppDependencies:
    """Obtiene el contenedor de dependencias"""
    return AppDependencies.get_instance()


def get_pipeline_dep() -> Pipeline:
    """Dependencia: Pipeline"""
    return get_deps().pipeline


def get_session_manager_dep() -> SessionManager:
    """Dependencia: SessionManager"""
    return get_deps().session_manager
