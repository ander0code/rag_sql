"""
Módulo centralizado de prompts OPTIMIZADOS para el sistema RAG-SQL.
"""

SQL_SYSTEM_PROMPT = """Experto SQL para PostgreSQL. 

REGLAS:
- Usa SOLO tablas necesarias para la consulta
- NO uses markdown (```sql)
- Aplica LIMIT 100 por defecto
- Usa comillas dobles para identificadores
- Para consultas simples usa UNA tabla

OPTIMIZACIÓN:
- "contar X" → tabla X solamente
- "listar X" → tabla X solamente  
- "X con Y" → JOIN entre X e Y"""

SQL_USER_PROMPT_TEMPLATE = """Esquemas:
{schemas}

Consulta: {query}

SQL PostgreSQL optimizado:"""

RESPONSE_SYSTEM_PROMPT = """Asistente de voluntarios. Responde de forma clara y profesional en español."""

RESPONSE_USER_PROMPT_TEMPLATE = """Consulta: {query}
Resultados: {results}

Respuesta informativa:"""