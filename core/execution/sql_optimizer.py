# Optimizador SQL: agrega LIMIT y limpia espacios

import re


# Aplica optimizaciones básicas al SQL generado
def optimize_sql(sql: str) -> str:
    sql_upper = sql.upper()

    # Agregar LIMIT si no existe y no es agregación
    if "LIMIT" not in sql_upper:
        has_aggregation = any(
            agg in sql_upper
            for agg in ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN(", "COUNT ("]
        )
        if not has_aggregation:
            sql = sql.rstrip(";").rstrip() + " LIMIT 100;"

    # Limpiar espacios múltiples
    sql = re.sub(r"\s+", " ", sql).strip()

    # Asegurar que termine con ;
    if not sql.endswith(";"):
        sql += ";"

    return sql
