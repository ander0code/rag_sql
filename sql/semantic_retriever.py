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
        Define los esquemas estáticos para el sistema multi-tenant de voluntarios.
        
        Returns:
            Lista de esquemas con metadatos estructurados (PUBLIC + TENANT)
        """
        return [
            # ========== SCHEMA PUBLIC (Centralizadas) ==========
            {
                "schema_text": "Tabla 'administradores' en schema PUBLIC contiene los administradores principales de la plataforma. Gestiona accesos y permisos a nivel global.",
                "metadata": {
                    "table_name": "administradores",
                    "schema": "public",
                    "columns": [
                        "id (UUID)",
                        "nombre (TEXT)",
                        "correo (TEXT)",
                        "hash_contrasena (TEXT)",
                        "permisos (JSONB)",
                        "creado_en (TIMESTAMP)",
                        "actualizado_en (TIMESTAMP)"
                    ],
                    "relationships": [],
                    "related_tables": [],
                    "enums": {},
                    "indices": [
                        {
                            "name": "administradores_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        },
                        {
                            "name": "administradores_correo_key",
                            "type": "unique",
                            "columns": ["correo"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'organizaciones' en schema PUBLIC contiene información de todos los tenants/organizaciones. Cada organización tiene su propio schema dinámico.",
                "metadata": {
                    "table_name": "organizaciones",
                    "schema": "public",
                    "columns": [
                        "id (UUID)",
                        "nombre (TEXT)",
                        "nombre_esquema (TEXT)",
                        "subdominio (TEXT)",
                        "email (TEXT)",
                        "creado_en (TIMESTAMP)",
                        "actualizado_en (TIMESTAMP)"
                    ],
                    "relationships": [
                        {
                            "type": "uno-a-muchos",
                            "description": "organizaciones.id -> suscripciones.organizacion_id",
                            "target_table": "suscripciones"
                        },
                        {
                            "type": "uno-a-muchos",
                            "description": "organizaciones.id -> tenant_usuarios.tenant_id",
                            "target_table": "tenant_usuarios"
                        }
                    ],
                    "related_tables": ["suscripciones", "tenant_usuarios"],
                    "enums": {},
                    "indices": [
                        {
                            "name": "organizaciones_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        },
                        {
                            "name": "organizaciones_nombre_esquema_key",
                            "type": "unique",
                            "columns": ["nombre_esquema"]
                        },
                        {
                            "name": "organizaciones_subdominio_key",
                            "type": "unique",
                            "columns": ["subdominio"]
                        },
                        {
                            "name": "organizaciones_email_key",
                            "type": "unique",
                            "columns": ["email"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'suscripciones' en schema PUBLIC gestiona los planes y pagos de cada organización/tenant. Controla el estado de suscripción de cada tenant.",
                "metadata": {
                    "table_name": "suscripciones",
                    "schema": "public",
                    "columns": [
                        "id (UUID)",
                        "organizacion_id (UUID)",
                        "plan (TEXT)",
                        "fecha_inicio (DATE)",
                        "fecha_proximo_pago (DATE)",
                        "estado (TEXT)",
                        "creado_en (TIMESTAMP)",
                        "actualizado_en (TIMESTAMP)"
                    ],
                    "relationships": [
                        {
                            "type": "muchos-a-uno",
                            "description": "suscripciones.organizacion_id -> organizaciones.id",
                            "target_table": "organizaciones"
                        }
                    ],
                    "related_tables": ["organizaciones"],
                    "enums": {
                        "estado": ["activa", "suspendida", "cancelada", "vencida"]
                    },
                    "indices": [
                        {
                            "name": "suscripciones_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        }
                    ]
                },
                "score": 1.0
            },
            {
                "schema_text": "Tabla 'tenant_usuarios' en schema PUBLIC contiene COORDINADORES y usuarios de cada tenant/organización. Los coordinadores tienen rol='coordinador'. Esta es la tabla principal para consultas sobre coordinadores.",
                "metadata": {
                    "table_name": "tenant_usuarios",
                    "schema": "public",
                    "columns": [
                        "id (UUID)",
                        "tenant_id (UUID)",
                        "nombre (TEXT)",
                        "correo (TEXT)",
                        "hash_contrasena (TEXT)",
                        "rol (TEXT)",
                        "permisos (JSONB)",
                        "creado_en (TIMESTAMP)",
                        "actualizado_en (TIMESTAMP)"
                    ],
                    "relationships": [
                        {
                            "type": "muchos-a-uno",
                            "description": "tenant_usuarios.tenant_id -> organizaciones.id",
                            "target_table": "organizaciones"
                        }
                    ],
                    "related_tables": ["organizaciones"],
                    "enums": {
                        "rol": ["coordinador", "admin", "usuario"]
                    },
                    "indices": [
                        {
                            "name": "tenant_usuarios_pkey",
                            "type": "primary",
                            "columns": ["id"]
                        },
                        {
                            "name": "tenant_usuarios_correo_key",
                            "type": "unique",
                            "columns": ["correo"]
                        }
                    ]
                },
                "score": 1.0
            },
            
            # ========== SCHEMA TENANT (Dinámicas por organización) ==========
            {
                "schema_text": "Tabla 'areas' almacena las diferentes áreas de trabajo para voluntarios, cada una con competencias específicas. Incluye id único, nombre del área y array de competencias requeridas. El coordinador_id referencia a public.tenant_usuarios.",
                "metadata": {
                    "table_name": "areas",
                    "columns": [
                        "id (UUID)",
                        "nombre (TEXT)", 
                        "competencias (text[])",
                        "coordinador_id (UUID)"
                    ],
                    "relationships": [
                        {
                            "type": "uno-a-muchos",
                            "description": "areas.id -> voluntarios.area_id",
                            "target_table": "voluntarios"
                        },
                        {
                            "type": "muchos-a-uno",
                            "description": "areas.coordinador_id -> public.tenant_usuarios.id",
                            "target_table": "tenant_usuarios",
                            "cross_schema": True
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
                "schema_text": "Tabla 'voluntarios' contiene información personal y de contacto de todos los voluntarios registrados. Incluye datos personales, estado actual, historial de participación y referencias a coordinador y área asignada. El coordinador_id referencia a public.tenant_usuarios.",
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
                            "type": "muchos-a-uno",
                            "description": "voluntarios.coordinador_id -> public.tenant_usuarios.id",
                            "target_table": "tenant_usuarios",
                            "cross_schema": True
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
                "schema_text": "Tabla 'operaciones' define las diferentes actividades y eventos donde pueden participar los voluntarios. Contiene información detallada sobre fechas, ubicación, capacidad y requisitos específicos. El coordinador_id referencia a public.tenant_usuarios.",
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
                            "type": "muchos-a-uno",
                            "description": "operaciones.coordinador_id -> public.tenant_usuarios.id",
                            "target_table": "tenant_usuarios",
                            "cross_schema": True
                        },
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
                "schema_text": "Tabla 'asistencia' registra la participación efectiva de voluntarios en operaciones. Permite marcar asistencia y controlar la participación real vs inscripciones. El coordinador_id referencia a public.tenant_usuarios.",
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
                        },
                        {
                            "type": "muchos-a-uno",
                            "description": "asistencia.coordinador_id -> public.tenant_usuarios.id",
                            "target_table": "tenant_usuarios",
                            "cross_schema": True
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
                "schema_text": "Tabla 'certificados' gestiona los certificados emitidos a voluntarios por su participación en operaciones completadas. Almacena URLs de PDFs y metadata de emisión. El coordinador_id referencia a public.tenant_usuarios.",
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
                        },
                        {
                            "type": "muchos-a-uno",
                            "description": "certificados.coordinador_id -> public.tenant_usuarios.id",
                            "target_table": "tenant_usuarios",
                            "cross_schema": True
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
        Selección inteligente multi-tenant MEJORADA.
        
        - Mantiene tu lógica LLM original al 100%
        - Añade detección automática de schemas sin hardcodeo
        - Mejora el prompt con información de arquitectura
        - Fallback inteligente mejorado
        """
        logger.info(f"🤖 Selección inteligente multi-tenant para: '{query}'")
        
        # ========== PREPARACIÓN INTELIGENTE DE DATOS (MEJORADO) ==========
        table_info = []
        public_tables = []
        tenant_tables = []
        
        for schema in self.schemas:
            table_name = schema["metadata"]["table_name"]
            schema_type = schema["metadata"].get("schema", "tenant")  # Detección automática
            columns = [col.split(" (")[0] for col in schema["metadata"].get("columns", [])]
            description = schema["schema_text"]
            
            # TU LÓGICA ORIGINAL: Incluir información sobre tipos de datos importantes
            column_types = []
            for col in schema["metadata"].get("columns", []):
                if "UUID" in col or "coordinador" in col.lower() or "estado" in col.lower():
                    column_types.append(col)
            
            # NUEVO: Información enriquecida con schema type
            enhanced_table_info = {
                "table": table_name,
                "schema_type": schema_type,  # NUEVO: Identificar automáticamente el tipo
                "desc": description,
                "cols": columns,
                "important_cols": column_types
            }
            
            table_info.append(enhanced_table_info)
            
            # NUEVO: Separar por schema automáticamente
            if schema_type == "public":
                public_tables.append(enhanced_table_info)
            else:
                tenant_tables.append(enhanced_table_info)
        
        # ========== PROMPT MEJORADO (combinando ambos enfoques) ==========
        system_prompt = """Eres experto SQL multi-tenant. Selecciona SOLO las tablas MÍNIMAS necesarias.

    ARQUITECTURA AUTOMÁTICA DETECTADA:
    - Tablas PUBLIC: Datos centralizados (coordinadores, organizaciones)
    - Tablas TENANT: Datos específicos por organización (voluntarios, operaciones)

    REGLAS INTELIGENTES:
    1. Para consultas simples (contar, listar) usa UNA tabla del schema correcto
    2. Para consultas complejas usa las tablas relacionadas necesarias
    3. Considera automáticamente el tipo de schema (public vs tenant)
    4. Sé MINIMALISTA pero PRECISO

    Responde solo JSON sin markdown:
    {"selected_tables": ["tabla1"], "reasoning": "breve explicación considerando schemas"}"""

        # NUEVO: Prompt enriquecido con información de arquitectura
        user_prompt = f"""ARQUITECTURA MULTI-TENANT DETECTADA:

    📊 TABLAS PUBLIC (centralizadas): {len(public_tables)} tablas
    {json.dumps(public_tables, ensure_ascii=False, indent=1)}

    📊 TABLAS TENANT (por organización): {len(tenant_tables)} tablas  
    {json.dumps(tenant_tables, ensure_ascii=False, indent=1)}

    CONSULTA: {query}

    ¿Qué tablas específicas necesitas? Considera que algunas están en schema público y otras en tenant dinámico."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            logger.info(f"🤖 Respuesta LLM multi-tenant: {response.content}")
            
            # TU LÓGICA ORIGINAL: Limpiar markdown del JSON
            clean_response = response.content.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '').strip()
            elif clean_response.startswith('```'):
                clean_response = clean_response.replace('```', '').strip()
            
            # TU LÓGICA ORIGINAL: Parsear respuesta JSON
            response_data = json.loads(clean_response)
            selected_table_names = response_data.get("selected_tables", [])
            reasoning = response_data.get("reasoning", "Sin explicación")
            
            logger.info(f"🎯 LLM seleccionó {len(selected_table_names)} tablas: {selected_table_names}")
            logger.info(f"🧠 Razonamiento multi-tenant: {reasoning}")
            
            # NUEVO: Logging mejorado con información de schemas
            selected_public = [t for t in selected_table_names if t in [pt["table"] for pt in public_tables]]
            selected_tenant = [t for t in selected_table_names if t in [tt["table"] for tt in tenant_tables]]
            
            logger.info(f"📊 Distribución: PUBLIC({len(selected_public)}): {selected_public}")
            logger.info(f"📊 Distribución: TENANT({len(selected_tenant)}): {selected_tenant}")
            
            # TU LÓGICA ORIGINAL: Filtrar esquemas basado en la selección del LLM
            selected_schemas = []
            for schema in self.schemas:
                table_name = schema["metadata"]["table_name"]
                if table_name in selected_table_names:
                    schema_copy = schema.copy()
                    schema_copy["score"] = 1.0
                    selected_schemas.append(schema_copy)
            
            if not selected_schemas:
                logger.warning("⚠️ LLM no seleccionó tablas válidas, usando fallback inteligente")
                return self._intelligent_fallback_enhanced(query)
            
            return selected_schemas
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON: {e}")
            logger.error(f"Respuesta limpia: {clean_response}")
            return self._intelligent_fallback_enhanced(query)
            
        except Exception as e:
            logger.error(f"❌ Error en selección LLM: {e}")
            return self._intelligent_fallback_enhanced(query)

    def _intelligent_fallback_enhanced(self, query: str) -> list:
        """
        Fallback inteligente MEJORADO que combina tu lógica con detección automática.
        
        - Mantiene tu búsqueda por menciones directas
        - Añade detección automática de schema types
        - Sin hardcodeo: usa la metadata de los schemas
        """
        logger.info("🔄 Usando fallback inteligente multi-tenant")
        
        query_lower = query.lower()
        selected_schemas = []
        
        # ========== NIVEL 1: TU LÓGICA ORIGINAL (Menciones directas) ==========
        for schema in self.schemas:
            table_name = schema["metadata"]["table_name"]
            table_singular = table_name[:-1] if table_name.endswith('s') else table_name
            
            if table_name in query_lower or table_singular in query_lower:
                schema_copy = schema.copy()
                schema_copy["score"] = 1.0
                selected_schemas.append(schema_copy)
                logger.info(f"🔍 Mención directa encontrada: {table_name}")
        
        # ========== NIVEL 2: DETECCIÓN AUTOMÁTICA POR SCHEMA TYPE (NUEVO) ==========
        if not selected_schemas:
            logger.info("🔍 Sin menciones directas, usando detección automática por schema")
            
            # Detectar automáticamente qué tipo de tablas podrían ser relevantes
            public_candidates = []
            tenant_candidates = []
            
            for schema in self.schemas:
                table_name = schema["metadata"]["table_name"]
                schema_type = schema["metadata"].get("schema", "tenant")
                columns = [col.lower() for col in schema["metadata"].get("columns", [])]
                
                # Buscar coincidencias semánticas en columnas y descripción
                semantic_score = 0
                description_lower = schema["schema_text"].lower()
                
                # Calcular relevancia basada en contenido, no hardcodeo
                query_words = query_lower.split()
                for word in query_words:
                    if word in description_lower:
                        semantic_score += 2
                    if any(word in col for col in columns):
                        semantic_score += 1
                
                if semantic_score > 0:
                    candidate = {
                        "schema": schema,
                        "score": semantic_score,
                        "schema_type": schema_type
                    }
                    
                    if schema_type == "public":
                        public_candidates.append(candidate)
                    else:
                        tenant_candidates.append(candidate)
            
            # Seleccionar los mejores candidatos automáticamente
            all_candidates = public_candidates + tenant_candidates
            all_candidates.sort(key=lambda x: x["score"], reverse=True)
            
            if all_candidates:
                best_candidate = all_candidates[0]
                schema_copy = best_candidate["schema"].copy()
                schema_copy["score"] = 1.0
                selected_schemas.append(schema_copy)
                
                logger.info(f"🤖 Detección automática seleccionó: {best_candidate['schema']['metadata']['table_name']} "
                        f"(schema: {best_candidate['schema_type']}, score: {best_candidate['score']})")
        
        # ========== NIVEL 3: TU FALLBACK ORIGINAL (si todo falla) ==========
        if not selected_schemas:
            logger.info("🔄 Usando fallback original: tabla por defecto")
            default_schema = self.get_schema_by_table_name("voluntarios")
            if default_schema:
                default_schema_copy = default_schema.copy()
                default_schema_copy["score"] = 1.0
                selected_schemas = [default_schema_copy]
        
        # ========== LOGGING MEJORADO ==========
        selected_names = [s['metadata']['table_name'] for s in selected_schemas]
        selected_types = [s['metadata'].get('schema', 'tenant') for s in selected_schemas]
        
        logger.info(f"🔄 Fallback inteligente seleccionó: {selected_names}")
        logger.info(f"📊 Tipos de schema: {dict(zip(selected_names, selected_types))}")
        
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