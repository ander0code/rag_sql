# Entidades de Query

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Query:
    """Consulta en lenguaje natural"""

    text: str
    session_id: Optional[str] = None
    schema: str = "public"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class QueryResult:
    """Resultado de una consulta"""

    sql: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    data: List[tuple] = field(default_factory=list)
    response: Optional[str] = None
    error: Optional[str] = None
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.error is None

    @property
    def row_count(self) -> int:
        return len(self.data)
