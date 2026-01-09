#!/usr/bin/env python3
import asyncio
import aiohttp
import time
import json
import os
import random
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List

# Configuración - Lee de variable de entorno o usa default
API_URL = os.getenv("RAG_SQL_API_URL", "http://localhost:8000")
CONCURRENT_USERS = int(os.getenv("LOAD_TEST_USERS", "20"))
QUERIES_PER_USER = int(os.getenv("LOAD_TEST_QUERIES", "3"))
REPORT_DIR = Path(__file__).parent / "reports"

# Preguntas basadas en el schema de Interbarrios
SAMPLE_QUERIES = [
    # Consultas simples (rápidas, probablemente cacheadas)
    "cuantos arbitros hay",
    "cuantos equipos hay registrados",
    "cuantos torneos hay",
    "cuantos jugadores hay en total",
    "cuantas canchas hay",
    # Consultas de listado
    "lista todos los arbitros",
    "dame los nombres de los equipos",
    "cuales son los torneos activos",
    "lista los partidos finalizados",
    # Consultas con filtros
    "cuantos equipos estan en regla",
    "cuantos partidos estan pendientes",
    "cuantos jugadores son delanteros",
    "cuantos jugadores son arqueros",
    # Consultas de estadísticas
    "cual es el equipo con mas goles",
    "cuantas tarjetas amarillas hubo",
    "cuantas tarjetas rojas hubo",
    "cuantos goles se anotaron en total",
    # Consultas más complejas
    "cuantos partidos tiene el torneo VIII EDICIÓN INTERBARRIOS VES",
    "cuantos equipos participan en el torneo SUB 16",
    "cuantos jugadores tiene cada equipo en promedio",
]


@dataclass
class QueryResult:
    user_id: int
    session_id: str
    query: str
    result: str
    time_seconds: float
    tokens_used: int
    success: bool
    error: str = ""
    needs_clarification: bool = False


class LoadTester:
    def __init__(self):
        self.results: List[QueryResult] = []
        self.start_time = None
        self.end_time = None

    async def make_query(
        self,
        session: aiohttp.ClientSession,
        user_id: int,
        query: str,
        session_id: str = None,
    ) -> QueryResult:
        """Hace una consulta a la API."""
        payload = {"query": query}
        if session_id:
            payload["session_id"] = session_id

        try:
            start = time.time()
            async with session.post(
                f"{API_URL}/query",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                elapsed = time.time() - start

                if resp.status == 200:
                    data = await resp.json()
                    return QueryResult(
                        user_id=user_id,
                        session_id=data.get("session_id", ""),
                        query=query,
                        result=data.get("result", "")[:200],
                        time_seconds=elapsed,
                        tokens_used=data.get("tokens_used", 0) or 0,
                        success=True,
                        needs_clarification=data.get("needs_clarification", False),
                    )
                elif resp.status == 429:
                    return QueryResult(
                        user_id=user_id,
                        session_id=session_id or "",
                        query=query,
                        result="",
                        time_seconds=elapsed,
                        tokens_used=0,
                        success=False,
                        error="Rate limited",
                    )
                else:
                    error_text = await resp.text()
                    return QueryResult(
                        user_id=user_id,
                        session_id=session_id or "",
                        query=query,
                        result="",
                        time_seconds=elapsed,
                        tokens_used=0,
                        success=False,
                        error=f"HTTP {resp.status}: {error_text[:100]}",
                    )
        except Exception as e:
            return QueryResult(
                user_id=user_id,
                session_id=session_id or "",
                query=query,
                result="",
                time_seconds=0,
                tokens_used=0,
                success=False,
                error=str(e)[:100],
            )

    async def simulate_user(self, session: aiohttp.ClientSession, user_id: int):
        """Simula un usuario haciendo múltiples consultas."""
        session_id = None

        for i in range(QUERIES_PER_USER):
            query = random.choice(SAMPLE_QUERIES)
            result = await self.make_query(session, user_id, query, session_id)

            if result.session_id:
                session_id = result.session_id

            self.results.append(result)

            # Pequeña pausa entre consultas del mismo usuario
            await asyncio.sleep(random.uniform(0.5, 2.0))

    async def run_load_test(self):
        """Ejecuta el test de carga."""
        print("\nIniciando test de carga...")
        print(f"   Usuarios concurrentes: {CONCURRENT_USERS}")
        print(f"   Consultas por usuario: {QUERIES_PER_USER}")
        print(f"   Total consultas: {CONCURRENT_USERS * QUERIES_PER_USER}\n")

        self.start_time = time.time()

        async with aiohttp.ClientSession() as session:
            # Verificar que la API esté disponible
            try:
                async with session.get(f"{API_URL}/health") as resp:
                    if resp.status != 200:
                        print("[ERROR] API no disponible")
                        return
                    print("[OK] API disponible\n")
            except Exception as e:
                print(f"[ERROR] No se puede conectar a la API: {e}")
                return

            # Ejecutar usuarios concurrentes
            tasks = [
                self.simulate_user(session, user_id)
                for user_id in range(CONCURRENT_USERS)
            ]

            await asyncio.gather(*tasks)

        self.end_time = time.time()

        # Generar reporte
        self.generate_report()

    def generate_report(self):
        """Genera el reporte de resultados."""
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        total_time = self.end_time - self.start_time
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        cached = [r for r in successful if r.time_seconds < 0.5]
        clarifications = [r for r in successful if r.needs_clarification]

        avg_time = (
            sum(r.time_seconds for r in successful) / len(successful)
            if successful
            else 0
        )
        total_tokens = sum(r.tokens_used for r in successful)

        # Calcular percentiles
        times = sorted([r.time_seconds for r in successful])
        p50 = times[len(times) // 2] if times else 0
        p95 = times[int(len(times) * 0.95)] if times else 0
        p99 = times[int(len(times) * 0.99)] if times else 0

        # Sesiones únicas
        unique_sessions = len(set(r.session_id for r in successful if r.session_id))

        report = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "concurrent_users": CONCURRENT_USERS,
                "queries_per_user": QUERIES_PER_USER,
                "total_queries": len(self.results),
                "total_time_seconds": round(total_time, 2),
            },
            "results": {
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": f"{len(successful) / len(self.results) * 100:.1f}%",
                "cached_responses": len(cached),
                "clarification_requests": len(clarifications),
                "unique_sessions": unique_sessions,
            },
            "performance": {
                "avg_response_time": round(avg_time, 2),
                "p50_response_time": round(p50, 2),
                "p95_response_time": round(p95, 2),
                "p99_response_time": round(p99, 2),
                "throughput_qps": round(len(successful) / total_time, 2),
            },
            "tokens": {
                "total_tokens_used": total_tokens,
                "avg_tokens_per_query": round(total_tokens / len(successful), 0)
                if successful
                else 0,
            },
            "errors": {
                "rate_limited": len([r for r in failed if "Rate" in r.error]),
                "other_errors": len([r for r in failed if "Rate" not in r.error]),
            },
            "sample_results": [
                {
                    "user": r.user_id,
                    "query": r.query,
                    "result": r.result[:100],
                    "time": r.time_seconds,
                    "tokens": r.tokens_used,
                }
                for r in successful[:10]
            ],
        }

        # Guardar JSON
        report_file = (
            REPORT_DIR / f"load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Imprimir resumen
        print("\n" + "=" * 60)
        print("REPORTE DE TEST DE CARGA")
        print("=" * 60)
        print(f"\nTiempo total: {total_time:.1f}s")
        print(f"Total consultas: {len(self.results)}")
        print(
            f"Exitosas: {len(successful)} ({len(successful) / len(self.results) * 100:.1f}%)"
        )
        print(f"Fallidas: {len(failed)}")
        print(f"Cacheadas: {len(cached)}")
        print(f"Clarificaciones: {len(clarifications)}")
        print(f"Sesiones unicas: {unique_sessions}")
        print("\nRendimiento:")
        print(f"   Promedio: {avg_time:.2f}s")
        print(f"   P50: {p50:.2f}s")
        print(f"   P95: {p95:.2f}s")
        print(f"   P99: {p99:.2f}s")
        print(f"   QPS: {len(successful) / total_time:.2f}")
        print(f"\nTokens: {total_tokens} total")
        print(f"\nReporte guardado: {report_file}")
        print("=" * 60)


if __name__ == "__main__":
    tester = LoadTester()
    asyncio.run(tester.run_load_test())
