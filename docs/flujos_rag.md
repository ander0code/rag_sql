# Flujo de Procesamiento RAG-SQL

## Descripción

RAG-SQL implementa Retrieval-Augmented Generation especializado en bases de datos:

- **Retrieval**: Recupera schemas de tablas relevantes para la consulta
- **Augmented**: Aumenta el contexto del LLM con metadatos de la DB
- **Generation**: Genera SQL y respuestas en lenguaje natural

---

## Diagrama de Flujo

```mermaid
flowchart TD
    subgraph entrada[Entrada]
        U[Usuario]
        CLI[CLI]
        API[API REST]
    end

    subgraph seguridad[Seguridad]
        RL[RateLimiter]
        IS[InputSanitizer]
        PG[PromptGuard]
        TD[TopicDetector]
    end

    subgraph procesamiento[Procesamiento]
        QE[QueryEnhancer]
        QR[QueryRewriter]
        AD[AmbiguityDetector]
        CA[ClarifyAgent]
    end

    subgraph cache[Cache]
        SC[SemanticCache - Qdrant]
        RC[SessionCache - Redis]
    end

    subgraph rag[RAG Core]
        SR[SchemaRetriever]
        SG[SQLGenerator]
        SV[SQLValidator]
        QX[QueryExecutor]
        RG[ResponseGenerator]
    end

    subgraph contexto[Contexto]
        SM[SessionManager]
        CS[ContextSummarizer]
    end

    U --> CLI & API
    CLI & API --> RL
    RL -->|OK| IS
    RL -->|Excedido| E1[Error 429]
    IS --> PG
    PG -->|Injection| E2[Error 403]
    PG -->|OK| TD
    TD -->|Off-topic| E4[Error 400]
    TD -->|OK| QE
    QE --> QR
    QR --> AD
    AD -->|Ambiguo| CA
    CA --> U
    AD -->|Claro| SC
    SC -->|HIT| RG
    SC -->|MISS| SR
    SR --> SG
    SG --> SV
    SV -->|Peligroso| E3[Error 400]
    SV -->|OK| QX
    QX -->|Error SQL| SG
    QX -->|OK| RG
    RG --> SC
    RG --> SM
    SM --> CS
    RG --> R[Respuesta]
```

---

## Secuencia de Procesamiento

```mermaid
sequenceDiagram
    participant U as Usuario
    participant API as API/CLI
    participant SEC as Seguridad
    participant ENH as QueryEnhancer
    participant AMB as AmbiguityDetector
    participant CAC as Cache
    participant RAG as RAG Core
    participant DB as Database
    participant LLM as LLM

    U->>API: Query en lenguaje natural
    API->>SEC: RateLimiter.check(IP)
    SEC->>SEC: InputSanitizer.sanitize()
    SEC->>SEC: PromptGuard.check()
    SEC->>SEC: TopicDetector.check()
    SEC->>ENH: Query validada
    
    ENH->>LLM: Mejorar query
    LLM-->>ENH: Query mejorada
    
    ENH->>AMB: Query procesada
    AMB->>LLM: Detectar ambigüedad
    LLM-->>AMB: Resultado
    
    AMB->>CAC: Buscar en cache semántico
    CAC-->>AMB: MISS
    
    AMB->>RAG: Procesar
    RAG->>LLM: Seleccionar tablas
    LLM-->>RAG: Tablas relevantes
    
    RAG->>LLM: Generar SQL
    LLM-->>RAG: SQL generado
    
    RAG->>RAG: SQLValidator.validate()
    RAG->>DB: Ejecutar SQL
    DB-->>RAG: Resultados
    
    RAG->>LLM: Generar respuesta
    LLM-->>RAG: Respuesta natural
    
    RAG->>CAC: Guardar en cache
    RAG-->>U: Respuesta final
```

---

## Componentes y Uso de LLM

| Componente | Función | Usa LLM |
|------------|---------|:-------:|
| InputSanitizer | Limpia caracteres peligrosos | No |
| PromptGuard | Detecta prompt injection | No |
| TopicDetector | Verifica tema de DB | Sí |
| QueryEnhancer | Mejora redacción | Sí |
| AmbiguityDetector | Detecta ambigüedad | Sí |
| ClarifyAgent | Genera opciones de clarificación | Sí |
| SchemaRetriever | Selecciona tablas relevantes | Sí |
| SQLGenerator | Genera SQL | Sí |
| SQLValidator | Valida seguridad SQL | No |
| QueryExecutor | Ejecuta en DB | No |
| ResponseGenerator | Genera respuesta natural | Sí |

---

## Consumo de Tokens por Query

| Componente | Input | Output | Total |
|------------|------:|-------:|------:|
| QueryEnhancer | ~200 | ~50 | 250 |
| AmbiguityDetector | ~300 | ~50 | 350 |
| SchemaRetriever | ~500 | ~100 | 600 |
| SQLGenerator | ~800 | ~200 | 1000 |
| ResponseGenerator | ~600 | ~300 | 900 |
| **Total por query** | **2400** | **700** | **~3100** |

Costo estimado: ~$0.001 USD por query (Deepseek)

---

## Ejemplos de Uso

### Health Check
```bash
curl http://localhost:8000/health
```

### Health Detallado
```bash
curl http://localhost:8000/health/detailed
```

### Información del Sistema
```bash
curl http://localhost:8000/info
```

### Ejecutar Consulta
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Cuántos usuarios hay?"}'
```

### Consulta con Streaming
```bash
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Lista los productos más vendidos"}'
```

### Crear Sesión
```bash
curl -X POST http://localhost:8000/session
```

### Query con Contexto de Sesión
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Y cuántos son activos?", "session_id": "abc123"}'
```

### Métricas JSON
```bash
curl http://localhost:8000/metrics
```

### Métricas Prometheus
```bash
curl http://localhost:8000/metrics/prometheus
```

---

## Métricas Disponibles

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `ragsql_requests_total` | Counter | Total de requests por endpoint |
| `ragsql_queries_total` | Counter | Queries procesadas |
| `ragsql_cache_hits_total` | Counter | Hits en cache semántico |
| `ragsql_cache_misses_total` | Counter | Misses en cache |
| `ragsql_security_blocks_total` | Counter | Bloqueos por seguridad |
| `ragsql_pipeline_duration_avg_ms` | Gauge | Latencia promedio |
| `ragsql_pipeline_duration_p95_ms` | Gauge | Latencia percentil 95 |
| `ragsql_active_sessions` | Gauge | Sesiones activas |
| `ragsql_tables_indexed` | Gauge | Tablas indexadas |
