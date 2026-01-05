# 🔷 Arquitectura RAG-SQL - Hexagonal

## Diagrama de Arquitectura

```
                    ╔═══════════════════════════════════════╗
                    ║         ADAPTADORES ENTRADA           ║
                    ║   CLI (cli.py) │ API (api.py)         ║
                    ╚═══════════════════╤═══════════════════╝
                                        │
                    ╔═══════════════════▼═══════════════════╗
                    ║              CORE                      ║
                    ║  ┌─────────────────────────────────┐   ║
                    ║  │         SERVICES                │   ║
                    ║  │  pipeline.py (orquestador)      │   ║
                    ║  │  sql_generator.py               │   ║
                    ║  │  sql_executor.py                │   ║
                    ║  │  schema_scanner.py              │   ║
                    ║  │  schema_retriever.py            │   ║
                    ║  │  query_rewriter.py              │   ║
                    ║  │  response_generator.py          │   ║
                    ║  │  ambiguity_detector.py          │   ║
                    ║  │  security.py (consolidado)      │   ║
                    ║  │  session_manager.py             │   ║
                    ║  └─────────────────────────────────┘   ║
                    ║  ┌─────────────────────────────────┐   ║
                    ║  │         DOMAIN                  │   ║
                    ║  │  Query, Schema, Session         │   ║
                    ║  └─────────────────────────────────┘   ║
                    ║  ┌─────────────────────────────────┐   ║
                    ║  │         PORTS                   │   ║
                    ║  │  DatabasePort, LLMPort, Cache   │   ║
                    ║  └─────────────────────────────────┘   ║
                    ╚═══════════════════╤═══════════════════╝
                                        │
                    ╔═══════════════════▼═══════════════════╗
                    ║         ADAPTADORES SALIDA            ║
                    ║  PostgreSQL │ OpenAI/Deepseek         ║
                    ║  Redis      │ Qdrant                  ║
                    ╚═══════════════════════════════════════╝
```

---

## Estructura de Archivos

```
rag_sql/
├── main.py                              # Entry point
│
├── adapters/                            # Adaptadores externos
│   ├── inbound/                         # Entrada
│   │   ├── cli.py                       # Línea de comandos
│   │   └── api.py                       # FastAPI REST
│   └── outbound/                        # Salida
│       ├── database/postgresql.py       # PostgreSQL/MySQL/SQLServer
│       ├── llm/openai_deepseek.py       # OpenAI + Deepseek
│       └── cache/                       # Redis + Qdrant
│
├── core/                                # Núcleo de negocio
│   ├── ports/                           # Interfaces/Contratos
│   ├── domain/                          # Entidades
│   └── services/                        # Lógica de negocio
│
├── config/settings.py                   # Configuración
├── data/schemas/                        # Cache de schemas
└── utils/logging.py                     # Logging + tokens
```

---

## Flujo Principal

```
1. Usuario envía query natural
      ↓
2. InputSanitizer limpia entrada
      ↓
3. PromptGuard verifica injection
      ↓
4. QueryRewriter normaliza query
      ↓
5. SchemaRetriever selecciona tablas via LLM
      ↓
6. SQLGenerator crea SQL via LLM
      ↓
7. SQLValidator valida seguridad
      ↓
8. QueryExecutor ejecuta en DB
      ↓
9. ResponseGenerator crea respuesta natural
      ↓
10. SemanticCache guarda para búsquedas similares
```

---

## Seguridad

| Capa | Protección |
|------|------------|
| **Input** | Sanitización, longitud máxima, caracteres |
| **Prompt** | Detección prompt injection |
| **SQL** | Solo SELECT, sin comandos peligrosos |
| **Data** | Bloqueo columnas sensibles |
| **System** | Sin acceso pg_catalog, information_schema |

---

## Uso

### CLI
```bash
PYTHONPATH=. python main.py --info
PYTHONPATH=. python main.py --query "¿Cuántos usuarios?"
PYTHONPATH=. python main.py --scan
```

### API
```bash
PYTHONPATH=. uvicorn adapters.inbound.api:app --reload
```

### Endpoints
- `GET /` - Status
- `GET /health` - Health check
- `GET /info` - Info de DB
- `POST /query` - Ejecutar consulta
- `POST /session` - Crear sesión
- `POST /scan` - Re-escanear DB
