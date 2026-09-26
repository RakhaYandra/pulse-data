"""Orchestrate: extract -> quality -> marts -> cross-check API -> charts.

Cross-check: pipeline uptime/MTTR vs GET /reports/reliability on the same
scratch DB (needs a Pulse API pointed at it, see README). Prints MATCH or
MISMATCH and exits non-zero on mismatch.

Env: PG_* (extract), PULSE_API (base URL, optional), PULSE_USER/PULSE_PASS.
"""
import json
import math
import os
import urllib.request

import charts as C
import etl
import marts as M
import quality as Q


def api_reliability(base, email, password):
    login = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(base + "/api/v1/auth/login", data=login,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        token = json.load(r)["data"]["token"]
    req = urllib.request.Request(
        base + "/api/v1/reports/reliability?days=90",
        headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=10) as r:
        return {row["monitor_id"]: row for row in json.load(r)["data"]}


def main():
    df = etl.extract()
    report = Q.check(df)
    print("extract:", report["tables"])

    marts = M.build(df)
    M.save(marts)

    up = marts["uptime_daily"]
    overall = (up.assign(w=up["checks"])
                 .groupby("monitor_id")
                 .apply(lambda g: round(100.0 * g["ups"].sum() / g["checks"].sum(), 2),
                        include_groups=False)
                 .to_dict())
    mttr = (marts["incidents_summary"].set_index("monitor_id")["mttr_s"]
              .to_dict())

    C.all_charts(marts)

    base = os.environ.get("PULSE_API", "")
    if not base:
        print("cross-check skipped (PULSE_API unset)")
        return
    email = os.environ.get("PULSE_USER", "demo@pulse.local")
    password = os.environ.get("PULSE_PASS", "")
    theirs = api_reliability(base, email, password)
    bad = []
    for mid, exp_up in overall.items():
        got = theirs.get(mid, {}).get("uptime_pct")
        if got is None or abs(got - exp_up) >= 0.01:
            bad.append((mid, "uptime", exp_up, got))
    for mid, exp_mt in mttr.items():
        if exp_mt is None or (isinstance(exp_mt, float) and math.isnan(exp_mt)):
            continue
        got = theirs.get(mid, {}).get("mttr_seconds")
        if got is None or abs(got - exp_mt) >= 1.0:
            bad.append((mid, "mttr", exp_mt, got))
    if bad:
        print("cross-check API reliability: MISMATCH", bad)
        raise SystemExit(1)
    print(f"cross-check API reliability: MATCH ({len(overall)} monitors)")


if __name__ == "__main__":
    main()
