import logging
import json
from typing import List, Dict, Any
from langchain.schema import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class SchemaRetriever:
    """
    Gestiona esquemas estáticos para el sistema de gestión de voluntarios.
    
    Ya no depende de Qdrant - usa definiciones estáticas optimizadas.
    """
    
    def __init__(self):
        """Inicializa con esquemas predefinidos de voluntarios."""
        logger.info("SchemaRetriever inicializado para sistema de voluntarios")
        self.schemas = self._get_volunteer_schemas()
        # Importar aquí para evitar dependencias circulares
        from utils.clients import get_available_llm
        self.llm = get_available_llm()

    def _get_volunteer_schemas(self) -> List[Dict[str, Any]]:
        """
        Define los esquemas estáticos para el sistema de voluntarios.
        
        Returns:
            Lista de esquemas con metadatos estructurados
        """
        return [
            {
                "schema_text": "Tabla 'areas' almacena las diferentes áreas de trabajo para voluntarios, cada una con competencias específicas. Incluye id único, nombre del área y array de competencias requeridas.",
                "metadata": {
                    "table_name": "areas",
                    "columns": [
                        "id (UUID)",
                        "nombre (TEXT)", 
                        "competencias (text[])"
                    ],
                    "relationships": [
                        {
                            "type": "uno-a-muchos",
                            "description": "areas.id -> voluntarios.area_id",
                            "target_table": "voluntarios"
                        }
                    ],
                    "related_tables": ["voluntarios"],
                    "enums": {},
                    "indices": [
                        {
                            "name": "areas_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'voluntarios' contiene información personal y de contacto de todos los voluntarios registrados. Incluye datos personales, estado actual, historial de participación y referencias a coordinador y área asignada.",
                "metadata": {
                    "table_name": "voluntarios",
                    "columns": [
                        "id (UUID)",
                        "nombre_completo (TEXT)",
                        "dni (TEXT)",
                        "correo (TEXT)",
                        "telefono (TEXT)",
                        "estado (TEXT)",
                        "historial (JSONB)",
                        "registrado_en (TIMESTAMP)",
                        "coordinador_id (UUID)",
                        "area_id (UUID)"
                    ],
                    "relationships": [
                        {
                            "type": "muchos-a-uno",
                            "description": "voluntarios.area_id -> areas.id",
                            "target_table": "areas"
                        },
                        {
                            "type": "uno-a-muchos",
                            "description": "voluntarios.id -> inscripciones.voluntario_id",
                            "target_table": "inscripciones"
                        },
                        {
                            "type": "uno-a-muchos",
                            "description": "voluntarios.id -> certificados.voluntario_id",
                            "target_table": "certificados"
                        }
                    ],
                    "related_tables": ["areas", "inscripciones", "certificados"],
                    "enums": {
                        "estado": ["activo", "inactivo", "suspendido", "pendiente"]
                    },
                    "indices": [
                        {
                            "name": "voluntarios_pkey", 
                            "type": "primary",
                            "columns": ["id"]
                        },
                        {
                            "name": "voluntarios_dni_key",
                            "type": "unique", 
                            "columns": ["dni"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'operaciones' define las diferentes actividades y eventos donde pueden participar los voluntarios. Contiene información detallada sobre fechas, ubicación, capacidad y requisitos específicos.",
                "metadata": {
                    "table_name": "operaciones",
                    "columns": [
                        "id (UUID)",
                        "titulo (TEXT)",
                        "descripcion (TEXT)",
                        "fecha_inicio (TIMESTAMP)",
                        "fecha_fin (TIMESTAMP)",
                        "ubicacion (TEXT)",
                        "tipo (TEXT)",
                        "estado (TEXT)",
                        "coordinador_id (UUID)",
                        "capacidad (INTEGER)",
                        "creado_en (TIMESTAMP)",
                        "actualizado_en (TIMESTAMP)",
                        "requisitos (JSONB)"
                    ],
                    "relationships": [
                        {
                            "type": "uno-a-muchos",
                            "description": "operaciones.id -> inscripciones.operacion_id",
                            "target_table": "inscripciones"
                        },
                        {
                            "type": "uno-a-muchos",
                            "description": "operaciones.id -> certificados.operacion_id",
                            "target_table": "certificados"
                        }
                    ],
                    "related_tables": ["inscripciones", "certificados"],
                    "enums": {
                        "tipo": ["emergencia", "capacitacion", "evento", "proyecto"],
                        "estado": ["planificada", "activa", "completada", "cancelada"]
                    },
                    "indices": [
                        {
                            "name": "operaciones_pkey",
                            "type": "primary", 
                            "columns": ["id"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'inscripciones' registra la participación de voluntarios en operaciones específicas. Funciona como tabla de unión entre voluntarios y operaciones, manteniendo el estado de cada inscripción.",
                "metadata": {
                    "table_name": "inscripciones", 
                    "columns": [
                        "id (UUID)",
                        "operacion_id (UUID)",
                        "voluntario_id (UUID)",
                        "estado (TEXT)",
                        "fecha_inscripcion (TIMESTAMP)",
                        "creado_en (TIMESTAMP)",
                        "actualizado_en (TIMESTAMP)"
                    ],
                    "relationships": [
                        {
                            "type": "muchos-a-uno",
                            "description": "inscripciones.operacion_id -> operaciones.id",
                            "target_table": "operaciones"
                        },
                        {
                            "type": "muchos-a-uno", 
                            "description": "inscripciones.voluntario_id -> voluntarios.id",
                            "target_table": "voluntarios"
                        },
                        {
                            "type": "uno-a-muchos",
                            "description": "inscripciones.id -> asistencia.inscripcion_id",
                            "target_table": "asistencia"
                        }
                    ],
                    "related_tables": ["operaciones", "voluntarios", "asistencia"],
                    "enums": {
                        "estado": ["pendiente", "confirmada", "cancelada", "completada"]
                    },
                    "indices": [
                        {
                            "name": "inscripciones_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'asistencia' registra la participación efectiva de voluntarios en operaciones. Permite marcar asistencia y controlar la participación real vs inscripciones.",
                "metadata": {
                    "table_name": "asistencia",
                    "columns": [
                        "id (UUID)",
                        "inscripcion_id (UUID)",
                        "estado (TEXT)",
                        "marcado_en (TIMESTAMP)",
                        "coordinador_id (UUID)"
                    ],
                    "relationships": [
                        {
                            "type": "muchos-a-uno",
                            "description": "asistencia.inscripcion_id -> inscripciones.id", 
                            "target_table": "inscripciones"
                        }
                    ],
                    "related_tables": ["inscripciones"],
                    "enums": {
                        "estado": ["presente", "ausente", "tardanza", "salida_temprana"]
                    },
                    "indices": [
                        {
                            "name": "asistencia_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'certificados' gestiona los certificados emitidos a voluntarios por su participación en operaciones completadas. Almacena URLs de PDFs y metadata de emisión.",
                "metadata": {
                    "table_name": "certificados",
                    "columns": [
                        "id (UUID)",
                        "voluntario_id (UUID)",
                        "operacion_id (UUID)",
                        "url_pdf (TEXT)",
                        "emitido_en (TIMESTAMP)",
                        "coordinador_id (UUID)"
                    ],
                    "relationships": [
                        {
                            "type": "muchos-a-uno",
                            "description": "certificados.voluntario_id -> voluntarios.id",
                            "target_table": "voluntarios"
                        },
                        {
                            "type": "muchos-a-uno",
                            "description": "certificados.operacion_id -> operaciones.id",
                            "target_table": "operaciones"
                        }
                    ],
                    "related_tables": ["voluntarios", "operaciones"],
                    "enums": {},
                    "indices": [
                        {
                            "name": "certificados_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        }
                    ]
                },
                "score": 1.0
            }
        ]

    def preprocess_query(self, query: str) -> str:
        return query
    
    def get_relevant_tables(self, query: str, top_k=6) -> list:
        """
        Usa el LLM para seleccionar inteligentemente las tablas necesarias.
        ENFOQUE 100% LLM: Sin hardcoding, el modelo decide todo.
        """
        logger.info(f"🤖 Usando LLM para seleccionar tablas para: '{query}'")
        
        # Preparar información de tablas para el LLM (OPTIMIZADA - menos tokens)
        table_info = []
        for schema in self.schemas:
            table_name = schema["metadata"]["table_name"]
            # Solo columnas esenciales para reducir tokens
            columns = [col.split(" (")[0] for col in schema["metadata"].get("columns", [])][:3]
            # Descripción condensada
            description = schema["schema_text"][:100] + "..." if len(schema["schema_text"]) > 100 else schema["schema_text"]
            
            table_info.append({
                "table": table_name,
                "desc": description,
                "cols": columns
            })
        
        # Prompt OPTIMIZADO para menos tokens
        system_prompt = """Eres experto SQL. Selecciona SOLO las tablas MÍNIMAS necesarias.

REGLAS:
1. Para consultas simples (contar, listar) usa UNA tabla
2. Para consultas complejas usa las tablas relacionadas necesarias
3. Sé MINIMALISTA

Responde solo JSON sin markdown:
{"selected_tables": ["tabla1"], "reasoning": "breve explicación"}"""

        user_prompt = f"""TABLAS:
{json.dumps(table_info, ensure_ascii=False)}

CONSULTA: {query}

JSON de respuesta:"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            logger.info(f"🤖 Respuesta del LLM: {response.content}")
            
            # Limpiar markdown del JSON
            clean_response = response.content.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '').strip()
            elif clean_response.startswith('```'):
                clean_response = clean_response.replace('```', '').strip()
            
            # Parsear respuesta JSON
            response_data = json.loads(clean_response)
            selected_table_names = response_data.get("selected_tables", [])
            reasoning = response_data.get("reasoning", "Sin explicación")
            
            logger.info(f"🎯 LLM seleccionó {len(selected_table_names)} tablas: {selected_table_names}")
            logger.info(f"🧠 Razonamiento: {reasoning}")
            
            # Filtrar esquemas basado en la selección del LLM
            selected_schemas = []
            for schema in self.schemas:
                table_name = schema["metadata"]["table_name"]
                if table_name in selected_table_names:
                    schema_copy = schema.copy()
                    schema_copy["score"] = 1.0
                    selected_schemas.append(schema_copy)
            
            if not selected_schemas:
                logger.warning("⚠️ LLM no seleccionó tablas válidas, usando fallback")
                return self._fallback_table_selection(query)
            
            return selected_schemas
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON: {e}")
            logger.error(f"Respuesta limpia: {clean_response}")
            return self._fallback_table_selection(query)
            
        except Exception as e:
            logger.error(f"❌ Error en selección LLM: {e}")
            return self._fallback_table_selection(query)

    def _fallback_table_selection(self, query: str) -> list:
        """
        Fallback mínimo si el LLM falla.
        Solo busca menciones directas de nombres de tabla.
        """
        logger.info("🔄 Usando fallback mínimo para selección de tablas")
        
        query_lower = query.lower()
        selected_schemas = []
        
        # Buscar menciones directas de tablas
        for schema in self.schemas:
            table_name = schema["metadata"]["table_name"]
            table_singular = table_name[:-1] if table_name.endswith('s') else table_name
            
            if table_name in query_lower or table_singular in query_lower:
                schema_copy = schema.copy()
                schema_copy["score"] = 1.0
                selected_schemas.append(schema_copy)
        
        # Si no encuentra nada, usar la tabla de voluntarios como default
        if not selected_schemas:
            logger.info("🔄 No se encontraron menciones directas, usando tabla por defecto")
            default_schema = self.get_schema_by_table_name("voluntarios")
            if default_schema:
                default_schema_copy = default_schema.copy()
                default_schema_copy["score"] = 1.0
                selected_schemas = [default_schema_copy]
        
        logger.info(f"🔄 Fallback seleccionó: {[s['metadata']['table_name'] for s in selected_schemas]}")
        return selected_schemas
    
    def get_schema_by_table_name(self, table_name: str) -> dict:
        """Obtiene esquema específico por nombre de tabla."""
        for schema in self.schemas:
            if schema["metadata"]["table_name"] == table_name:
                return schema
        return None
    
    @staticmethod
    def convert_schema(schema):
        """
        Normaliza el formato de los esquemas obtenidos de Qdrant.
        
        Parámetros:
        - schema: Puede ser dict o resultado crudo de Qdrant
        
        Retorna:
        - Diccionario estandarizado con estructura {metadata, schema_text, score}
        """
        if isinstance(schema, dict):
            return schema
            
        payload = schema.payload
        metadata = payload.get("metadata", {})
        if "table_name" not in metadata:
            metadata["table_name"] = "Desconocida"
            
        return {
            "schema_text": payload.get("schema_text"),
            "metadata": metadata,
            "score": schema.score
        }
    
    def expand_schemas(self, schemas: list) -> list:
        """
        Expande la lista de esquemas incluyendo tablas relacionadas.
        
        Algoritmo:
        1. Convertir todos los esquemas a formato estándar
        2. Buscar recursivamente tablas relacionadas
        3. Evitar duplicados usando diccionario
        """
        converted = [self.convert_schema(s) for s in schemas]
        expanded = { s["metadata"]["table_name"]: s for s in converted }
        
        for s in converted:
            for rt in s["metadata"].get("related_tables", []):
                if rt not in expanded:
                    related_schema = self.get_schema_by_table_name(rt)
                    if related_schema:
                        converted_related = self.convert_schema(related_schema)
                        expanded[rt] = converted_related
                        
        return list(expanded.values())