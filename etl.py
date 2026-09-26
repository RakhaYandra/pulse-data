"""Extract read-only from PostgreSQL. DSN via env (no secrets in repo).

Env: PG_HOST (127.0.0.1), PG_PORT (5433), PG_USER (pulse),
     PG_PASS, PG_DB (pulse).
NOTE: users.password_hash is never selected.
"""
import os


def dsn() -> dict:
    return {
        "host": os.environ.get("PG_HOST", "127.0.0.1"),
        "port": int(os.environ.get("PG_PORT", "5433")),
        "user": os.environ.get("PG_USER", "pulse"),
        "password": os.environ.get("PG_PASS", ""),
        "dbname": os.environ.get("PG_DB", "pulse"),
    }


TABLES = ["monitors", "monitor_checks", "incidents"]


def extract(d=None) -> dict:
    import warnings

    import pandas as pd
    import psycopg

    # psycopg DBAPI works fine; silence pandas' untested-driver warning.
    warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy",
                            category=UserWarning)

    d = d or dsn()
    out = {}
    with psycopg.connect(connect_timeout=10, **d) as con:
        # Deterministic date bucketing regardless of server timezone.
        con.execute("SET TIME ZONE 'UTC'")
        for t in TABLES:
            out[t] = pd.read_sql(f"SELECT * FROM {t}", con)
    return out
