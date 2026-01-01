# Input sanitizer: limpia y valida entradas de usuario

import re
import html


# Sanitiza queries y session IDs
class InputSanitizer:
    MAX_QUERY_LENGTH = 500

    # Limpia una query de usuario
    @staticmethod
    def sanitize_query(query: str) -> str:
        if not query:
            return ""

        query = query[: InputSanitizer.MAX_QUERY_LENGTH]
        query = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", query)
        query = html.escape(query)
        query = re.sub(r"\s+", " ", query)
        query = re.sub(r"[\u200b-\u200f\u2028-\u202f\u205f-\u206f]", "", query)

        return query.strip()

    # Limpia un session ID
    @staticmethod
    def sanitize_session_id(session_id: str) -> str:
        if not session_id:
            return ""

        sanitized = re.sub(r"[^a-zA-Z0-9\-]", "", session_id)
        return sanitized[:32]

    # Valida formato de session ID
    @staticmethod
    def is_valid_session_id(session_id: str) -> bool:
        if not session_id:
            return False

        pattern = r"^[a-zA-Z0-9\-]{4,32}$"
        return bool(re.match(pattern, session_id))


_sanitizer = None


def get_sanitizer() -> InputSanitizer:
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = InputSanitizer()
    return _sanitizer
