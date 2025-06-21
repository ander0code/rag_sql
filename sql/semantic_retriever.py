from langchain_openai.embeddings import OpenAIEmbeddings
import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv(".env")
openai_api_key = os.getenv("OPENAI_API_KEY")

encoder = OpenAIEmbeddings(openai_api_key=openai_api_key)
qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_client = QdrantClient(url=qdrant_url)

class SchemaRetriever:
    """
    Clase para recuperar esquemas de base de datos relevantes usando embeddings semánticos.
    
    Funcionalidades principales:
    - Preprocesamiento de consultas
    - Búsqueda semántica de tablas relevantes
    - Expansión de esquemas con relaciones
    """
    
    def __init__(self):
        """Inicializa el encoder de embeddings y el cliente Qdrant."""
        self.encoder = encoder
        self.qdrant = qdrant_client

    #agregar terminos de busqueda en un futuro.
    def preprocess_query(self, query: str) -> str:
        return query

    def get_relevant_tables(self, query: str, top_k=3) -> list:
        """
        Recupera las tablas más relevantes usando embeddings semánticos.
        
        Flujo de trabajo:
        1. Preprocesar consulta para normalización
        2. Buscar en el vector store de Qdrant
        3. Priorizar tablas con relaciones mediante scoring
        4. Filtrar y ordenar resultados
        """
        masked_query = self.preprocess_query(query)

        results = self.qdrant.search(
            collection_name="custom_db_schema",
            query_vector=self.encoder.embed_query(masked_query),
            with_payload=True,
            limit=top_k * 2
        )

        prioritized_results = []
        for res in results:
            metadata = res.payload.get("metadata", {})
            related_tables = metadata.get("related_tables", [])
            
            if related_tables:
                res.score *= 1.5
            
            prioritized_results.append({
                "schema_text": res.payload["schema_text"],
                "metadata": metadata,
                "score": res.score
            })

        prioritized_results.sort(key=lambda x: x["score"], reverse=True)
        return prioritized_results[:top_k]
    
    def get_schema_by_table_name(self, table_name: str) -> dict:
        """
        Obtiene el esquema completo de una tabla específica por nombre.
        
        Retorna:
        - Documento completo con metadatos y estructura de la tabla
        - None si no se encuentra la tabla
        """
        results = self.qdrant.search(
            collection_name="custom_db_schema",
            query_vector=self.encoder.embed_query(table_name),
            with_payload=True,
            limit=1
        )
        return results[0] if results else None
    
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