# 🔷 RAG-SQL - Flujo Principal

## Diagrama de Flujo Completo

```mermaid
flowchart TD
    subgraph ENTRADA["🔵 ENTRADA"]
        U[Usuario envía query]
        CLI[CLI: main.py]
        API[API: FastAPI]
    end

    subgraph SEGURIDAD["🔴 SEGURIDAD"]
        RL[RateLimiter<br/>30 req/min por IP]
        IS[InputSanitizer<br/>Limpia caracteres]
        PG[PromptGuard<br/>Detecta injection]
    end

    subgraph PROCESAMIENTO["🟡 PROCESAMIENTO DE QUERY"]
        QE[QueryEnhancer<br/>Mejora redacción]
        QR[QueryRewriter<br/>Normaliza texto]
        AD[AmbiguityDetector<br/>¿Falta info?]
        CA[ClarifyAgent<br/>Opciones de DB]
    end

    subgraph CACHE["🟢 CACHE"]
        SC[SemanticCache<br/>Qdrant]
        RC[Redis<br/>Sesiones]
    end

    subgraph RAG["🔷 RAG CORE"]
        SR[SchemaRetriever<br/>Selecciona tablas via LLM]
        SG[SQLGenerator<br/>Genera SQL via LLM]
        SV[SQLValidator<br/>Valida seguridad SQL]
        QX[QueryExecutor<br/>Ejecuta en PostgreSQL]
        RG[ResponseGenerator<br/>Respuesta natural via LLM]
    end

    subgraph CONTEXTO["🟣 CONTEXTO"]
        SM[SessionManager<br/>Historial en Redis]
        CS[ContextSummarizer<br/>Resume chats largos]
    end

    U --> CLI & API
    CLI & API --> RL
    RL -->|OK| IS
    RL -->|Excedido| E1[Error 429]
    IS --> PG
    PG -->|Injection| E2[Error: Rechazado]
    PG -->|OK| QE
    QE --> QR
    QR --> AD
    AD -->|Ambiguo| CA
    CA --> U
    AD -->|Claro| SC
    SC -->|HIT| RG
    SC -->|MISS| SR
    SR --> SG
    SG --> SV
    SV -->|Peligroso| E3[Error: SQL no seguro]
    SV -->|OK| QX
    QX -->|Error| SG
    QX -->|OK| RG
    RG --> SC
    RG --> SM
    SM --> CS
    RG --> R[Respuesta al Usuario]
```

---

## Flujo Detallado Paso a Paso

```mermaid
sequenceDiagram
    participant U as Usuario
    participant API as API/CLI
    participant SEC as Seguridad
    participant ENH as QueryEnhancer
    participant AMB as AmbiguityDetector
    participant CAC as Cache
    participant RAG as RAG Core
    participant DB as PostgreSQL
    participant LLM as Deepseek/OpenAI

    U->>API: "dame ventas ayer"
    API->>SEC: RateLimiter.check(IP)
    SEC->>SEC: InputSanitizer.sanitize()
    SEC->>SEC: PromptGuard.check()
    SEC->>ENH: Query limpia
    
    ENH->>LLM: Mejorar query
    LLM-->>ENH: "Muéstrame las ventas de ayer"
    
    ENH->>AMB: Query mejorada
    AMB->>LLM: ¿Es ambigua?
    LLM-->>AMB: No, es clara
    
    AMB->>CAC: Buscar en cache
    CAC-->>AMB: MISS
    
    AMB->>RAG: Procesar query
    RAG->>LLM: Seleccionar tablas
    LLM-->>RAG: [ventas, productos]
    
    RAG->>LLM: Generar SQL
    LLM-->>RAG: SELECT * FROM ventas...
    
    RAG->>RAG: SQLValidator.validate()
    RAG->>DB: Ejecutar SQL
    DB-->>RAG: Datos
    
    RAG->>LLM: Generar respuesta
    LLM-->>RAG: "Las ventas de ayer fueron $5,000"
    
    RAG->>CAC: Guardar en cache
    RAG-->>U: Respuesta final
```

## Uso de Tokens por Llamada LLM

```mermaid
pie title Tokens por Componente
    "QueryEnhancer" : 250
    "SchemaRetriever" : 600
    "SQLGenerator" : 1000
    "ResponseGenerator" : 900
```

| Componente | Input Tokens | Output Tokens | Total |
|------------|-------------|---------------|-------|
| QueryEnhancer | ~200 | ~50 | 250 |
| AmbiguityDetector | ~300 | ~50 | 350 |
| SchemaRetriever | ~500 | ~100 | 600 |
| SQLGenerator | ~800 | ~200 | 1000 |
| ResponseGenerator | ~600 | ~300 | 900 |
| **TOTAL por query** | **2400** | **700** | **~3100** |

**Costo estimado por query**: ~$0.001 USD (Deepseek)
