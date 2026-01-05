# Entidades de Schema

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Column:
    """Columna de una tabla"""

    name: str
    data_type: str
    nullable: bool = True
    is_sensitive: bool = False
    enum_values: List[str] = field(default_factory=list)


@dataclass
class Table:
    """Tabla de base de datos"""

    name: str
    schema_name: str = "public"
    columns: List[Column] = field(default_factory=list)
    related_tables: List[str] = field(default_factory=list)
    is_sensitive: bool = False

    def get_columns_summary(self) -> str:
        """Resumen de columnas para prompts"""
        cols = [f"{c.name} ({c.data_type})" for c in self.columns[:8]]
        return ", ".join(cols)


@dataclass
class Schema:
    """Schema completo de la DB"""

    tables: List[Table] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_table(self, name: str) -> Optional[Table]:
        return next((t for t in self.tables if t.name == name), None)

    def get_table_names(self) -> List[str]:
        return [t.name for t in self.tables]
