# Clarify Agent - Aclara ambigüedades consultando la DB

import logging
from typing import List, Dict, Optional, Tuple
from core.services.sql_executor import QueryExecutor

logger = logging.getLogger(__name__)


class ClarifyAgent:
    """
    Cuando hay ambigüedad, consulta la DB y ofrece opciones reales.
    Ejemplo: "ventas de qué producto?" → Lista productos reales de la DB
    """

    def __init__(self, executor: QueryExecutor, retriever=None):
        self.executor = executor
        self.retriever = retriever

    def set_retriever(self, retriever):
        """Inyecta el retriever después de inicializar"""
        self.retriever = retriever

    def get_options_for_entity(self, entity_type: str, limit: int = 10) -> List[str]:
        """
        Obtiene opciones disponibles de la DB para una entidad.

        Args:
            entity_type: Tipo de entidad (ej: "producto", "cliente", "mes")
            limit: Máximo de opciones a retornar

        Returns:
            Lista de opciones reales de la DB
        """
        if not self.retriever:
            logger.warning("ClarifyAgent: sin retriever configurado")
            return []

        # Buscar tabla relacionada con la entidad
        context_query = f"buscar {entity_type} listar {entity_type}s"
        relevant_schemas = self.retriever.get_relevant(context_query)

        if not relevant_schemas:
            logger.debug(f"No se encontraron tablas para: {entity_type}")
            return []

        table_meta = relevant_schemas[0].get("metadata", {})
        table_name = table_meta.get("table_name")
        schema_name = table_meta.get("schema", "public")
        columns = table_meta.get("columns", [])

        if not table_name:
            return []

        # Encontrar campo de display
        display_field = self._find_display_field(columns)
        if not display_field:
            logger.debug(f"No se encontró campo de display para: {table_name}")
            return []

        return self._fetch_options(schema_name, table_name, display_field, limit)

    def _find_display_field(self, columns: List[str]) -> Optional[str]:
        """Encuentra el mejor campo para mostrar opciones"""
        if not columns:
            return None

        parsed_cols = []
        for col in columns:
            parts = col.split(" ")
            name = parts[0]
            col_type = parts[1] if len(parts) > 1 else ""
            parsed_cols.append({"name": name, "type": col_type.upper()})

        # Priorizar campos descriptivos
        display_patterns = ["nombre", "name", "titulo", "title", "descripcion", "label"]
        for pattern in display_patterns:
            for col in parsed_cols:
                if pattern in col["name"].lower():
                    return col["name"]

        # Buscar campos de texto que no sean IDs o sensibles
        skip_patterns = [
            "id",
            "_id",
            "fk_",
            "password",
            "token",
            "hash",
            "key",
            "secret",
        ]
        text_types = ["VARCHAR", "TEXT", "CHAR", "CHARACTER"]

        for col in parsed_cols:
            name_lower = col["name"].lower()
            is_text = any(t in col["type"] for t in text_types)
            is_skip = any(p in name_lower for p in skip_patterns)

            if is_text and not is_skip:
                return col["name"]

        # Fallback: primer campo que no sea ID
        for col in parsed_cols:
            if not col["name"].lower().endswith("id"):
                return col["name"]

        return parsed_cols[0]["name"] if parsed_cols else None

    def _fetch_options(
        self, schema_name: str, table_name: str, field: str, limit: int
    ) -> List[str]:
        """Ejecuta query para obtener opciones únicas"""
        query = f'''
            SELECT DISTINCT "{field}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE "{field}" IS NOT NULL 
            ORDER BY "{field}" 
            LIMIT {limit}
        '''

        try:
            result = self.executor.execute(query)
            if "error" not in result and result.get("data"):
                options = [str(row[0]) for row in result["data"] if row[0]]
                logger.debug(f"Opciones de {table_name}.{field}: {len(options)}")
                return options
        except Exception as e:
            logger.warning(f"Error obteniendo opciones: {e}")

        return []

    def build_clarification_response(
        self, question: str, entity_type: str, options: List[str]
    ) -> Dict:
        """
        Construye respuesta de clarificación para el usuario.

        Args:
            question: Pregunta al usuario
            entity_type: Tipo de entidad
            options: Opciones disponibles

        Returns:
            Dict con estructura de clarificación
        """
        response = {
            "needs_clarification": True,
            "question": question,
            "entity_type": entity_type,
            "options": options[:10],
        }

        if options:
            options_text = "\n".join(
                [f"  {i + 1}. {opt}" for i, opt in enumerate(options[:10])]
            )
            response["message"] = f"{question}\n\nOpciones disponibles:\n{options_text}"
        else:
            response["message"] = question

        return response

    def clarify(self, entity_type: str, question: str) -> Tuple[bool, Dict]:
        """
        Proceso completo de clarificación.

        Returns:
            (success, clarification_response)
        """
        options = self.get_options_for_entity(entity_type)
        response = self.build_clarification_response(question, entity_type, options)
        return True, response


_clarify_agent: Optional[ClarifyAgent] = None


def get_clarify_agent(executor: QueryExecutor) -> ClarifyAgent:
    """Obtiene instancia del ClarifyAgent"""
    global _clarify_agent
    if _clarify_agent is None:
        _clarify_agent = ClarifyAgent(executor)
    return _clarify_agent
