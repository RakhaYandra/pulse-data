"""Reliability marts (DuckDB + parquet in work/).

- uptime_daily: per monitor per day (checks, ups, uptime %, avg/p95 ms)
- incidents_summary: per monitor (total, open, MTTR s, failures)
- status_daily: count per status per day
- adherence_daily: expected vs actual checks per interval (schedule adherence)
"""
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"


def build(df: dict) -> dict:
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    con.register("monitors", df["monitors"])
    con.register("checks", df["monitor_checks"])
    con.register("incidents", df["incidents"])
    names = dict(zip(df["monitors"]["id"].astype(str), df["monitors"]["name"]))

    uptime = con.execute("""
        SELECT monitor_id, CAST(checked_at AS DATE) AS date,
               COUNT(*) AS checks,
               SUM(CASE WHEN status='UP' THEN 1 ELSE 0 END) AS ups,
               100.0*SUM(CASE WHEN status='UP' THEN 1 ELSE 0 END)/COUNT(*) AS uptime_pct,
               AVG(response_time_ms) AS avg_ms,
               QUANTILE_CONT(response_time_ms, 0.95) AS p95_ms
        FROM checks GROUP BY 1, 2 ORDER BY 2, 1
    """).df()
    uptime["monitor_id"] = uptime["monitor_id"].astype(str)
    uptime["name"] = uptime["monitor_id"].map(names)

    inc = con.execute("""
        SELECT m.id AS monitor_id,
               COUNT(i.id) AS total,
               SUM(CASE WHEN i.status='OPEN' THEN 1 ELSE 0 END) AS open,
               AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.started_at))) FILTER (WHERE i.resolved_at IS NOT NULL) AS mttr_s,
               COALESCE(SUM(i.failure_count), 0) AS failures
        FROM monitors m LEFT JOIN incidents i ON i.monitor_id = m.id GROUP BY 1
    """).df()
    inc["monitor_id"] = inc["monitor_id"].astype(str)
    inc["name"] = inc["monitor_id"].map(names)

    status = con.execute("""
        SELECT CAST(checked_at AS DATE) AS date, status, COUNT(*) AS n
        FROM checks GROUP BY 1, 2 ORDER BY 1, 2
    """).df()

    adh = con.execute("""
        SELECT m.id AS monitor_id, CAST(c.checked_at AS DATE) AS date,
               CAST(86400 / m.interval_seconds AS INTEGER) AS expected,
               COUNT(c.id) AS actual
        FROM monitors m JOIN checks c ON c.monitor_id = m.id
        GROUP BY 1, 2, m.interval_seconds
    """).df()
    adh["monitor_id"] = adh["monitor_id"].astype(str)
    adh["name"] = adh["monitor_id"].map(names)
    adh["pct"] = (100.0 * adh["actual"] / adh["expected"]).round(1)

    return {"uptime_daily": uptime, "incidents_summary": inc,
            "status_daily": status, "adherence_daily": adh}


def save(marts: dict) -> None:
    WORK.mkdir(exist_ok=True)
    con = duckdb.connect()
    for name, frame in marts.items():
        con.register("frame", frame)
        con.execute(f"COPY frame TO '{WORK / (name + '.parquet')}' (FORMAT PARQUET)")
        con.unregister("frame")
    print("marts saved:", sorted(marts))
