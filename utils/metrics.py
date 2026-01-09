# Métricas y Observabilidad para RAG-SQL

import time
import logging
from typing import Dict, Callable
from functools import wraps
from dataclasses import dataclass, field
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MetricCounter:
    """Contador simple para métricas"""

    value: int = 0
    _lock: Lock = field(default_factory=Lock)

    def inc(self, amount: int = 1):
        with self._lock:
            self.value += amount

    def get(self) -> int:
        return self.value


@dataclass
class MetricHistogram:
    """Histograma para latencias"""

    values: list = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def observe(self, value: float):
        with self._lock:
            self.values.append(value)
            # Mantener solo últimas 1000 observaciones
            if len(self.values) > 1000:
                self.values = self.values[-1000:]

    def get_stats(self) -> Dict:
        if not self.values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_vals = sorted(self.values)
        count = len(sorted_vals)

        return {
            "count": count,
            "avg": sum(sorted_vals) / count,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "p50": sorted_vals[int(count * 0.5)],
            "p95": sorted_vals[int(count * 0.95)] if count > 20 else sorted_vals[-1],
            "p99": sorted_vals[int(count * 0.99)] if count > 100 else sorted_vals[-1],
        }


class MetricsCollector:
    """
    Colector de métricas para RAG-SQL.
    Compatible con formato Prometheus.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Contadores
        self.requests_total = defaultdict(MetricCounter)  # por endpoint
        self.errors_total = defaultdict(MetricCounter)  # por tipo de error
        self.queries_total = MetricCounter()
        self.cache_hits = MetricCounter()
        self.cache_misses = MetricCounter()
        self.security_blocks = defaultdict(MetricCounter)  # por tipo
        self.llm_calls = defaultdict(MetricCounter)  # por modelo

        # Histogramas de latencia
        self.request_duration = defaultdict(MetricHistogram)  # por endpoint
        self.llm_duration = MetricHistogram()
        self.db_query_duration = MetricHistogram()
        self.pipeline_duration = MetricHistogram()

        # Gauges (valores actuales)
        self.active_sessions = 0
        self.tables_indexed = 0

        self._initialized = True

    def record_request(self, endpoint: str, duration_ms: float, success: bool):
        """Registra una request"""
        self.requests_total[endpoint].inc()
        self.request_duration[endpoint].observe(duration_ms)
        if not success:
            self.errors_total[endpoint].inc()

    def record_query(self, duration_ms: float, cached: bool):
        """Registra una query procesada"""
        self.queries_total.inc()
        self.pipeline_duration.observe(duration_ms)
        if cached:
            self.cache_hits.inc()
        else:
            self.cache_misses.inc()

    def record_llm_call(self, model: str, duration_ms: float):
        """Registra llamada a LLM"""
        self.llm_calls[model].inc()
        self.llm_duration.observe(duration_ms)

    def record_db_query(self, duration_ms: float):
        """Registra query a DB"""
        self.db_query_duration.observe(duration_ms)

    def record_security_block(self, block_type: str):
        """Registra bloqueo de seguridad"""
        self.security_blocks[block_type].inc()

    def set_active_sessions(self, count: int):
        """Actualiza número de sesiones activas"""
        self.active_sessions = count

    def set_tables_indexed(self, count: int):
        """Actualiza número de tablas indexadas"""
        self.tables_indexed = count

    def get_metrics(self) -> Dict:
        """Retorna todas las métricas en formato dict"""
        return {
            "counters": {
                "requests_total": {k: v.get() for k, v in self.requests_total.items()},
                "errors_total": {k: v.get() for k, v in self.errors_total.items()},
                "queries_total": self.queries_total.get(),
                "cache_hits": self.cache_hits.get(),
                "cache_misses": self.cache_misses.get(),
                "cache_hit_rate": (
                    self.cache_hits.get()
                    / max(1, self.cache_hits.get() + self.cache_misses.get())
                ),
                "security_blocks": {k: v.get() for k, v in self.security_blocks.items()},
                "llm_calls": {k: v.get() for k, v in self.llm_calls.items()},
            },
            "histograms": {
                "request_duration_ms": {
                    k: v.get_stats() for k, v in self.request_duration.items()
                },
                "llm_duration_ms": self.llm_duration.get_stats(),
                "db_query_duration_ms": self.db_query_duration.get_stats(),
                "pipeline_duration_ms": self.pipeline_duration.get_stats(),
            },
            "gauges": {
                "active_sessions": self.active_sessions,
                "tables_indexed": self.tables_indexed,
            },
        }

    def get_prometheus_format(self) -> str:
        """Retorna métricas en formato Prometheus"""
        lines = []
        metrics = self.get_metrics()

        # Contadores
        for endpoint, count in metrics["counters"]["requests_total"].items():
            lines.append(f'ragsql_requests_total{{endpoint="{endpoint}"}} {count}')

        lines.append(f'ragsql_queries_total {metrics["counters"]["queries_total"]}')
        lines.append(f'ragsql_cache_hits_total {metrics["counters"]["cache_hits"]}')
        lines.append(f'ragsql_cache_misses_total {metrics["counters"]["cache_misses"]}')

        for block_type, count in metrics["counters"]["security_blocks"].items():
            lines.append(f'ragsql_security_blocks_total{{type="{block_type}"}} {count}')

        # Gauges
        lines.append(f'ragsql_active_sessions {metrics["gauges"]["active_sessions"]}')
        lines.append(f'ragsql_tables_indexed {metrics["gauges"]["tables_indexed"]}')

        # Histogramas (solo avg y p95)
        pipeline_stats = metrics["histograms"]["pipeline_duration_ms"]
        lines.append(f'ragsql_pipeline_duration_avg_ms {pipeline_stats["avg"]:.2f}')
        lines.append(f'ragsql_pipeline_duration_p95_ms {pipeline_stats["p95"]:.2f}')

        return "\n".join(lines)


def get_metrics() -> MetricsCollector:
    """Obtiene la instancia singleton de métricas"""
    return MetricsCollector()


def timed(metric_name: str = None):
    """Decorador para medir tiempo de ejecución"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                name = metric_name or func.__name__
                logger.debug(f"{name} ejecutado en {duration_ms:.2f}ms")

        return wrapper

    return decorator


# Health check extendido
def get_health_status() -> Dict:
    """Retorna estado de salud completo del sistema"""
    metrics = get_metrics()
    stats = metrics.get_metrics()

    pipeline_stats = stats["histograms"]["pipeline_duration_ms"]
    error_rate = sum(stats["counters"]["errors_total"].values()) / max(
        1, sum(stats["counters"]["requests_total"].values())
    )

    # Determinar estado
    status = "healthy"
    issues = []

    if error_rate > 0.1:
        status = "degraded"
        issues.append(f"Error rate alto: {error_rate:.1%}")

    if pipeline_stats["p95"] > 5000:  # > 5 segundos
        status = "degraded"
        issues.append(f"Latencia alta: p95={pipeline_stats['p95']:.0f}ms")

    cache_hit_rate = stats["counters"]["cache_hit_rate"]
    if cache_hit_rate < 0.1 and stats["counters"]["queries_total"] > 100:
        issues.append(f"Cache hit rate bajo: {cache_hit_rate:.1%}")

    return {
        "status": status,
        "issues": issues,
        "stats": {
            "total_queries": stats["counters"]["queries_total"],
            "cache_hit_rate": f"{cache_hit_rate:.1%}",
            "avg_latency_ms": f"{pipeline_stats['avg']:.0f}",
            "p95_latency_ms": f"{pipeline_stats['p95']:.0f}",
            "error_rate": f"{error_rate:.1%}",
        },
    }
