# Prompt guard: detecta intentos de prompt injection

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
    r"disregard\s+(previous|all|above)",
    r"forget\s+(previous|all|your)\s+(instructions?|training)",
    r"override\s+(system|previous)",
    r"you\s+are\s+(now|a)\s+(hacker|admin|root|developer)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if|a)",
    r"roleplay\s+as",
    r"show\s+(me\s+)?(your|the)\s+(system\s+)?prompt",
    r"reveal\s+(your|system)\s+(instructions?|prompt)",
    r"what\s+(are|is)\s+your\s+(system\s+)?prompt",
    r"print\s+(your|the)\s+instructions?",
    r"execute\s+(shell|bash|cmd|system)",
    r"run\s+(command|shell|bash)",
    r"\$\([^)]+\)",
    r"`[^`]+`",
    r";\s*(DROP|DELETE|TRUNCATE|UPDATE|INSERT|ALTER|CREATE)\s+",
    r"UNION\s+(ALL\s+)?SELECT",
    r"--\s*$",
    r"/\*.*\*/",
    r"<script[^>]*>",
    r"{{.*}}",
    r"\[\[.*\]\]",
]

DANGEROUS_KEYWORDS = [
    "drop table",
    "delete from",
    "truncate",
    "alter table",
    "create user",
    "grant all",
    "exec xp_",
    "information_schema",
    "sys.tables",
    "pg_catalog",
    "mysql.user",
    "sqlite_master",
    "shutdown",
    "format c:",
    "rm -rf",
    "sudo",
]


# Detecta prompt injection usando patrones
class PromptGuard:
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    # Verifica si el texto contiene prompt injection
    def check(self, text: str) -> Tuple[bool, str]:
        if not text:
            return True, ""

        text_lower = text.lower()
        for pattern in self.patterns:
            if pattern.search(text):
                reason = "Patrón sospechoso detectado"
                logger.warning(f"Prompt injection detectado: {text[:50]}...")
                return False, reason

        for keyword in DANGEROUS_KEYWORDS:
            if keyword in text_lower:
                reason = f"Palabra clave peligrosa: {keyword}"
                logger.warning(f"Keyword peligroso: {keyword}")
                return False, reason

        return True, ""

    # Limpia el texto de caracteres peligrosos
    def sanitize(self, text: str) -> str:
        if not text:
            return text

        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        text = re.sub(r"\s+", " ", text)

        max_length = 1000
        if len(text) > max_length:
            text = text[:max_length]

        return text.strip()


_prompt_guard = None


def get_prompt_guard() -> PromptGuard:
    global _prompt_guard
    if _prompt_guard is None:
        _prompt_guard = PromptGuard()
    return _prompt_guard
