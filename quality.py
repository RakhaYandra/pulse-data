"""Quality gates: fail the run on dirty data."""


def check(df: dict) -> dict:
    errors: list[str] = []
    m, c, inc = df["monitors"], df["monitor_checks"], df["incidents"]

    if len(m) == 0:
        errors.append("monitors: empty (load demo_data.sql first)")
    if len(c) == 0:
        errors.append("monitor_checks: empty")

    mids = set(m["id"].astype(str))
    for t, frame in [("monitor_checks", c), ("incidents", inc)]:
        orph = frame[~frame["monitor_id"].astype(str).isin(mids)]
        if len(orph):
            errors.append(f"{t} orphan monitor_id: {len(orph)}")

    if (m["url"].astype(str).str.strip() == "").any():
        errors.append("monitors: blank url")
    if ((m["interval_seconds"] < 60)).any():
        errors.append("monitors: interval_seconds < 60")
    if ((m["timeout_seconds"] <= 0) | (m["timeout_seconds"] >= m["interval_seconds"])).any():
        errors.append("monitors: timeout out of (0, interval)")
    if ((m["failure_threshold"] < 1) | (m["recovery_threshold"] < 1)).any():
        errors.append("monitors: threshold < 1")

    rt = c["response_time_ms"].dropna()
    if (rt < 0).any():
        errors.append("monitor_checks: negative response_time_ms")

    bad = inc[inc["resolved_at"].notna() & (inc["resolved_at"] < inc["started_at"])]
    if len(bad):
        errors.append(f"incidents resolved<started: {len(bad)}")

    if c.duplicated(["monitor_id", "checked_at"]).any():
        errors.append("monitor_checks: duplicate (monitor_id, checked_at)")

    report = {"tables": {t: len(df[t]) for t in df}, "errors": errors}
    if errors:
        raise SystemExit("QUALITY FAIL: " + "; ".join(errors))
    return report
