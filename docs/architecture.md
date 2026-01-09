# Arquitectura RAG-SQL

Sistema de consultas en lenguaje natural sobre bases de datos, implementado con Arquitectura Hexagonal (Ports & Adapters).

## Diagrama General

```
                    ┌───────────────────────────────────────┐
                    │         ADAPTADORES ENTRADA           │
                    │   CLI (cli.py)  │  API (api.py)       │
                    │                 │  routes/*.py        │
                    └─────────────────┬─────────────────────┘
                                      │
                    ┌─────────────────▼─────────────────────┐
                    │              CORE                      │
                    │  ┌─────────────────────────────────┐   │
                    │  │         SERVICES                │   │
                    │  │  pipeline.py (orquestador)      │   │
                    │  │  sql/generator.py               │   │
                    │  │  sql/executor.py                │   │
                    │  │  schema/scanner.py              │   │
                    │  │  schema/retriever.py            │   │
                    │  │  query/rewriter.py              │   │
                    │  │  query/enhancer.py              │   │
                    │  │  query/ambiguity.py             │   │
                    │  │  query/clarify.py               │   │
                    │  │  response.py                    │   │
                    │  │  security/* (6 módulos)         │   │
                    │  │  context/session.py             │   │
                    │  │  context/summarizer.py          │   │
                    │  └─────────────────────────────────┘   │
                    │  ┌─────────────────────────────────┐   │
                    │  │         DOMAIN                  │   │
                    │  │  Query, Schema, Session         │   │
                    │  │  errors.py (excepciones)        │   │
                    │  │  responses.py (DTOs)            │   │
                    │  └─────────────────────────────────┘   │
                    │  ┌─────────────────────────────────┐   │
                    │  │         PORTS                   │   │
                    │  │  DatabasePort, LLMPort          │   │
                    │  │  CachePort, SemanticCachePort   │   │
                    │  └─────────────────────────────────┘   │
                    └─────────────────┬─────────────────────┘
                                      │
                    ┌─────────────────▼─────────────────────┐
                    │         ADAPTADORES SALIDA            │
                    │  database/                            │
                    │    postgresql.py, mysql.py            │
                    │    sqlserver.py, sqlite.py            │
                    │  llm/llm_factory.py (6 proveedores)   │
                    │  cache/redis_cache.py, qdrant_cache.py│
                    └───────────────────────────────────────┘
```

---

## Estructura de Directorios

```
rag_sql/
├── main.py                              # Punto de entrada CLI
├── adapters/
│   ├── factory.py                       # Fábrica de Pipeline
│   ├── inbound/
│   │   ├── api.py                       # FastAPI application
│   │   ├── cli.py                       # Interfaz de línea de comandos
│   │   ├── dependencies.py              # Contenedor de dependencias (DI)
│   │   └── routes/
│   │       ├── query.py                 # /query, /query/stream
│   │       ├── health.py                # /, /health, /metrics
│   │       ├── session.py               # /session
│   │       └── admin.py                 # /info, /scan
│   └── outbound/
│       ├── database/
│       │   ├── base.py                  # DatabaseAdapter ABC
│       │   ├── postgresql.py            # PostgreSQL
│       │   ├── mysql.py                 # MySQL/MariaDB
│       │   ├── sqlserver.py             # SQL Server
│       │   └── sqlite.py                # SQLite
│       ├── llm/
│       │   └── llm_factory.py           # Multi-proveedor LLM
│       └── cache/
│           ├── redis_cache.py           # Sesiones y rate limiting
│           └── qdrant_cache.py          # Cache semántico
├── core/
│   ├── ports/
│   │   ├── database_port.py             # Interfaz de base de datos
│   │   ├── llm_port.py                  # Interfaz de LLM
│   │   ├── cache_port.py                # Interfaz de cache
│   │   └── semantic_cache_port.py       # Interfaz cache semántico
│   ├── domain/
│   │   ├── query.py                     # Entidad Query
│   │   ├── schema.py                    # Entidad Schema, Table, Column
│   │   ├── session.py                   # Entidad Session, Message
│   │   ├── errors.py                    # Excepciones personalizadas
│   │   └── responses.py                 # DTOs de respuesta
│   └── services/
│       ├── pipeline.py                  # Orquestador principal
│       ├── response.py                  # Generador de respuestas
│       ├── sql/
│       │   ├── generator.py             # Generación SQL via LLM
│       │   └── executor.py              # Ejecución segura
│       ├── schema/
│       │   ├── scanner.py               # Descubrimiento de esquema
│       │   └── retriever.py             # Selección de tablas
│       ├── query/
│       │   ├── rewriter.py              # Normalización
│       │   ├── enhancer.py              # Mejora de queries
│       │   ├── ambiguity.py             # Detección de ambigüedad
│       │   └── clarify.py               # Agente de clarificación
│       ├── context/
│       │   ├── session.py               # Gestión de sesiones
│       │   └── summarizer.py            # Resumen de contexto
│       └── security/
│           ├── validators.py            # SQLValidator, PromptGuard
│           ├── guardrails.py            # TopicDetector, OutputValidator
│           ├── rate_limiter.py          # Rate limiting
│           └── audit.py                 # Logging de auditoría
├── config/
│   └── settings.py                      # Configuración centralizada
├── utils/
│   ├── logging.py                       # Logging y conteo de tokens
│   └── metrics.py                       # Métricas y observabilidad
├── tests/
│   ├── test_pipeline.py                 # Tests unitarios
│   ├── test_api.py                      # Tests de integración
│   └── load_test.py                     # Tests de carga
└── docker/
    ├── Dockerfile                       # Multi-stage build
    └── docker-compose.dev.yml           # Entorno de desarrollo
```

---

## Proveedores LLM Soportados

| Proveedor | Modelos | Variable de Entorno |
|-----------|---------|---------------------|
| Deepseek | deepseek-chat, deepseek-coder | `DEEPSEEK_API_KEY` |
| OpenAI | gpt-4o, gpt-4o-mini | `OPENAI_API_KEY` |
| Anthropic | claude-3-5-sonnet, claude-3-haiku | `ANTHROPIC_API_KEY` |
| Groq | llama-3.1-70b, mixtral | `GROQ_API_KEY` |
| Google | gemini-1.5-pro, gemini-1.5-flash | `GOOGLE_API_KEY` |
| Ollama | llama3, codellama (local) | `OLLAMA_BASE_URL` |

---

## Bases de Datos Soportadas

| Base de Datos | Adaptador | Connection String |
|---------------|-----------|-------------------|
| PostgreSQL | `postgresql.py` | `postgresql://user:pass@host:5432/db` |
| MySQL/MariaDB | `mysql.py` | `mysql://user:pass@host:3306/db` |
| SQL Server | `sqlserver.py` | `mssql://user:pass@host:1433/db` |
| SQLite | `sqlite.py` | `sqlite:///path/to/db.sqlite` |

---

## Seguridad

| Capa | Componente | Función |
|------|------------|---------|
| Rate Limiting | `RateLimiter` | 30 req/min por IP |
| Input | `InputSanitizer` | Sanitización, longitud máxima |
| Prompt | `PromptGuard` | Detección de prompt injection |
| Topic | `TopicDetector` | Solo consultas sobre DB |
| SQL | `SQLValidator` | Solo SELECT, queries parametrizadas |
| Output | `OutputValidator` | Validación de respuestas |
| Audit | `AuditLogger` | Registro de eventos de seguridad |

---

## Endpoints API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Status del servidor |
| GET | `/health` | Health check básico |
| GET | `/health/detailed` | Health check con métricas |
| GET | `/metrics` | Métricas en JSON |
| GET | `/metrics/prometheus` | Métricas formato Prometheus |
| GET | `/info` | Información de la base de datos |
| POST | `/query` | Ejecutar consulta |
| POST | `/query/stream` | Consulta con streaming SSE |
| POST | `/session` | Crear sesión |
| DELETE | `/session/{id}` | Eliminar sesión |
| POST | `/scan` | Re-escanear base de datos |

---

## Ejecución

### CLI
```bash
python main.py --info              # Información de la DB
python main.py --scan              # Escanear esquema
python main.py --query "consulta"  # Ejecutar consulta
```

### API
```bash
uvicorn adapters.inbound.api:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker compose -f docker/docker-compose.dev.yml up
```
