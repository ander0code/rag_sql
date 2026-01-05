# RAG-SQL

Consultas en lenguaje natural a SQL usando Retrieval-Augmented Generation con Arquitectura Hexagonal.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Soportado-blue.svg)
![Redis](https://img.shields.io/badge/Redis-Opcional-red.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-Opcional-purple.svg)

## Descripcion

RAG-SQL convierte preguntas en lenguaje natural a consultas SQL usando LLMs. Descubre automaticamente el esquema de tu base de datos y genera queries optimizadas.

**Caracteristicas:**
- Auto-descubrimiento de esquema de base de datos (tablas, columnas, relaciones, ENUMs)
- Soporte multi-LLM (OpenAI, Deepseek)
- Cache semantico con Qdrant
- Gestion de sesiones con Redis
- Proteccion contra SQL injection
- Rate limiting
- Arquitectura hexagonal para mantenibilidad

## Arquitectura

```
rag_sql/
├── adapters/
│   ├── inbound/         # CLI, FastAPI (entrada)
│   ├── outbound/        # PostgreSQL, LLM, Redis, Qdrant (salida)
│   └── factory.py       # Inyeccion de dependencias
├── core/
│   ├── domain/          # Entidades
│   ├── ports/           # Interfaces (ABC)
│   └── services/        # Logica de negocio
├── config/              # Configuracion
└── utils/               # Logging, tokens
```

## Requisitos

- Python 3.10+
- Base de datos PostgreSQL
- API key de OpenAI o Deepseek
- Redis (opcional, para sesiones)
- Qdrant (opcional, para cache semantico)

## Instalacion

```bash
# Clonar repositorio
git clone https://github.com/yourusername/rag_sql.git
cd rag_sql

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

## Configuracion

Copia `.env.example` a `.env` y configura:

```bash
# Requerido
DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db
DEEPSEEK_API_KEY=sk-tu-key-aqui
# o
OPENAI_API_KEY=sk-tu-key-aqui

# Opcional
REDIS_URL=redis://localhost:6379
DEBUG=true
```

## Uso

### 1. Escanear Base de Datos

Antes de usar RAG-SQL, escanea tu base de datos para descubrir su estructura:

```bash
PYTHONPATH=. python main.py --scan
```

Esto crea `data/schemas/discovered_schemas.json` con la estructura de tu base de datos.

### 2. Consultar via CLI

```bash
# Ver informacion de la base de datos
PYTHONPATH=. python main.py --info

# Hacer una pregunta
PYTHONPATH=. python main.py --query "Cuantos usuarios hay registrados?"

# Especificar schema (si hay multiples)
PYTHONPATH=. python main.py --query "Muestra las ventas" --schema public
```

### 3. Iniciar Servidor API

```bash
PYTHONPATH=. uvicorn adapters.inbound.api:app --reload --port 8000
```

**Endpoints:**

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/` | Estado del servidor |
| GET | `/health` | Health check |
| GET | `/info` | Info de la base de datos |
| POST | `/query` | Ejecutar consulta en lenguaje natural |
| POST | `/session` | Crear sesion |
| POST | `/scan` | Re-escanear base de datos |

**Ejemplo de consulta:**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Cuantos productos hay?"}'
```

## Flujo

```
Query Usuario → Sanitizar → Mejorar → Verificar Ambiguedad → Buscar Cache
      ↓                                                           ↓
   Clarificar ← (si es ambiguo)                              (si hay cache)
      ↓                                                           ↓
Seleccionar Tablas → Generar SQL → Validar → Ejecutar → Generar Respuesta
      ↓                                                           ↓
Guardar en Cache ←──────────────────────────────────── Retornar Respuesta
```

## Componentes

| Componente | Proposito |
|------------|-----------|
| QueryEnhancer | Mejora la query del usuario para mayor claridad |
| AmbiguityDetector | Detecta queries incompletas |
| ClarifyAgent | Ofrece opciones de la base de datos |
| TopicDetector | Rechaza queries fuera del dominio |
| SchemaRetriever | Selecciona tablas relevantes |
| SQLGenerator | Genera SQL via LLM |
| SQLValidator | Valida seguridad del SQL |
| OutputValidator | Sanitiza respuestas antes de retornar |
| ResponseGenerator | Crea respuesta en lenguaje natural |
| SemanticCache | Cache de queries similares (Qdrant) |
| SessionManager | Gestiona historial de conversacion (Redis) |

## Seguridad

- **Deteccion de SQL injection** - Bloquea DROP, DELETE, UPDATE, etc.
- **Proteccion contra prompt injection** - Detecta "ignora instrucciones", "actua como", etc.
- **Deteccion de tema** - Rechaza queries fuera del dominio (recetas, codigo, consejos)
- **Validacion de output** - Sanitiza respuestas antes de retornar
- **Bloqueo de columnas sensibles** - Nunca expone passwords, tokens, secrets
- **Rate limiting** - 30 peticiones/minuto por IP
- **Sanitizacion de input** - Limpia HTML, limita longitud
- **Logging de auditoria** - Registra todas las queries y eventos de seguridad

## Desarrollo

```bash
# Ejecutar tests
PYTHONPATH=. pytest tests/

# Ejecutar con logs de debug
DEBUG=true PYTHONPATH=. python main.py --query "test"
```

## Licencia

MIT License
