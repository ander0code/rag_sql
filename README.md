# RAG-SQL

Consultas en lenguaje natural a SQL usando Retrieval-Augmented Generation con Arquitectura Hexagonal.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Bases de datos:**
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![SQLServer](https://img.shields.io/badge/SQL_Server-CC2927?logo=microsoft-sql-server&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)

**LLMs:**
![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Claude-191919?logo=anthropic&logoColor=white)
![Google](https://img.shields.io/badge/Gemini-4285F4?logo=google&logoColor=white)

## Descripción

RAG-SQL convierte preguntas en lenguaje natural a consultas SQL usando LLMs. Descubre automáticamente el esquema de la base de datos y genera queries optimizadas.

**Características principales:**
- Auto-descubrimiento de esquema (tablas, columnas, relaciones, ENUMs)
- Soporte multi-LLM (Deepseek, OpenAI, Claude, Groq, Gemini, Ollama)
- Soporte multi-DB (PostgreSQL, MySQL, SQL Server, SQLite)
- Streaming SSE para respuestas en tiempo real
- Cache semántico con Qdrant
- Gestión de sesiones conversacionales con Redis
- Protección contra SQL injection y prompt injection
- Rate limiting y auditoría
- Arquitectura hexagonal

## Arquitectura

```
rag_sql/
├── adapters/
│   ├── inbound/              # CLI, FastAPI, Routes
│   ├── outbound/             # Database, LLM, Cache
│   └── factory.py            # Inyección de dependencias
├── core/
│   ├── domain/               # Entidades, Errores, DTOs
│   ├── ports/                # Interfaces (ABC)
│   └── services/             # Pipeline, SQL, Schema, Security
├── config/                   # Configuración centralizada
├── utils/                    # Logging, Métricas
└── tests/                    # Unitarios, Integración, Carga
```

Ver documentación completa en [docs/architecture.md](docs/architecture.md)

## Requisitos

- Python 3.10+
- Base de datos (PostgreSQL, MySQL, SQL Server o SQLite)
- API key de al menos un proveedor LLM
- Redis (opcional, para sesiones)
- Qdrant (opcional, para cache semántico)

## Instalación

```bash
git clone https://github.com/yourusername/rag_sql.git
cd rag_sql

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt

cp .env.example .env
# Editar .env con credenciales
```

## Configuración

Variables requeridas en `.env`:

```bash
# Proveedor LLM
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-tu-key

# Base de datos
DATABASE_URL=postgresql://user:pass@localhost:5432/database

# Opcional
DEBUG=true
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
```

## Uso

### CLI

```bash
# Información de la base de datos
python main.py --info

# Escanear esquema
python main.py --scan

# Ejecutar consulta
python main.py --query "¿Cuántos usuarios hay?"

# Especificar schema
python main.py --query "Ventas del mes" --schema public
```

### API

```bash
uvicorn adapters.inbound.api:app --reload --port 8000
```

### Docker

```bash
docker compose -f docker/docker-compose.dev.yml up
```

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Status |
| GET | `/health` | Health check |
| GET | `/health/detailed` | Health con métricas |
| GET | `/info` | Info de la DB |
| GET | `/metrics` | Métricas JSON |
| GET | `/metrics/prometheus` | Métricas Prometheus |
| POST | `/query` | Ejecutar consulta |
| POST | `/query/stream` | Consulta con streaming |
| POST | `/session` | Crear sesión |
| DELETE | `/session/{id}` | Eliminar sesión |
| POST | `/scan` | Re-escanear DB |

### Ejemplo

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Cuántos productos hay?"}'
```

## Flujo de Procesamiento

```
Query → Sanitizar → PromptGuard → TopicDetector → Enhancer
                                                      ↓
    Respuesta ← ResponseGenerator ← Executor ← SQLGenerator ← SchemaRetriever
        ↓                              ↓
   SemanticCache                   SQLValidator
```

Ver diagrama completo en [docs/flujos_rag.md](docs/flujos_rag.md)

## Componentes

| Componente | Función |
|------------|---------|
| QueryEnhancer | Mejora la query del usuario |
| AmbiguityDetector | Detecta queries incompletas |
| ClarifyAgent | Genera opciones de clarificación |
| TopicDetector | Rechaza queries fuera del dominio |
| SchemaRetriever | Selecciona tablas relevantes |
| SQLGenerator | Genera SQL via LLM |
| SQLValidator | Valida seguridad del SQL |
| ResponseGenerator | Crea respuesta en lenguaje natural |
| SemanticCache | Cache de queries similares |
| SessionManager | Gestiona historial conversacional |

## Seguridad

- Detección de SQL injection (bloquea DROP, DELETE, UPDATE)
- Protección contra prompt injection
- Validación de tema (solo consultas sobre DB)
- Sanitización de output
- Bloqueo de columnas sensibles (passwords, tokens)
- Rate limiting (30 req/min por IP)
- Sanitización de input
- Logging de auditoría

## Tests

```bash
# Tests unitarios
pytest tests/test_pipeline.py -v

# Tests de integración
pytest tests/test_api.py -v

# Tests de carga
python tests/load_test.py
```

## Documentación

- [Arquitectura](docs/architecture.md)
- [Flujos](docs/flujos_rag.md)
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Licencia

MIT License
