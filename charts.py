"""Charts Nexus-style -> charts/*.png."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
CH = ROOT / "charts"

NAVY, SURF, BLUE, LBLUE, INK, MUT, RED, GREEN = (
    "#0B1120", "#0F172A", "#3B82F6", "#60A5FA", "#F1F5F9", "#94A3B8", "#F87171", "#34D399")


def _fig():
    plt.rcParams.update({"figure.facecolor": NAVY, "axes.facecolor": SURF,
                         "text.color": INK, "axes.labelcolor": MUT,
                         "xtick.color": MUT, "ytick.color": MUT,
                         "font.family": "sans-serif"})
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s in ax.spines.values():
        s.set_color("#1E293B")
    return fig, ax


def _save(fig, name):
    CH.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(CH / name, dpi=110)
    plt.close(fig)


def uptime_by_monitor(m):
    u = (m["uptime_daily"].groupby(["monitor_id", "name"], as_index=False)
         .apply(lambda g: round(100.0 * g["ups"].sum() / g["checks"].sum(), 2),
                include_groups=False)
         .rename(columns={None: "uptime"}))
    u = u.sort_values("uptime", ascending=True)
    fig, ax = _fig()
    colors = [GREEN if v >= 99 else RED if v < 95 else BLUE for v in u["uptime"]]
    ax.barh(u["name"], u["uptime"], color=colors)
    ax.set_title("UPTIME % PER MONITOR", fontsize=10, loc="left", color=MUT, family="monospace")
    ax.set_xlim(0, 105)
    for i, v in enumerate(u["uptime"]):
        ax.text(v + 0.5, i, f" {v:.1f}%", va="center", fontsize=8, color=INK, family="monospace")
    _save(fig, "uptime_by_monitor.png")


def latency_p95_trend(m):
    t = m["uptime_daily"].sort_values("date")
    fig, ax = _fig()
    for name, g in t.groupby("name"):
        ax.plot(g["date"].astype(str), g["p95_ms"], marker="o", markersize=3, label=name)
    ax.set_title("P95 LATENCY MS PER DAY", fontsize=10, loc="left", color=MUT, family="monospace")
    ax.legend(fontsize=8)
    for l in ax.get_xticklabels():
        l.set_rotation(30)
        l.set_ha("right")
    _save(fig, "latency_p95_trend.png")


def incidents_by_monitor(m):
    s = m["incidents_summary"].sort_values("total", ascending=True)
    fig, ax = _fig()
    ax.barh(s["name"], s["total"], color=BLUE, label="total")
    ax.barh(s["name"], s["open"], color=RED, label="open")
    ax.set_title("INCIDENTS PER MONITOR", fontsize=10, loc="left", color=MUT, family="monospace")
    ax.legend(fontsize=8)
    _save(fig, "incidents_by_monitor.png")


def checks_by_status(m):
    s = m["status_daily"]
    piv = s.pivot_table(index="date", columns="status", values="n", aggfunc="sum", fill_value=0)
    fig, ax = _fig()
    bottom = None
    for st, color in [("UP", GREEN), ("DOWN", RED), ("TIMEOUT", LBLUE), ("ERROR", MUT)]:
        if st in piv.columns:
            ax.bar(piv.index.astype(str), piv[st], bottom=bottom, label=st, color=color)
            bottom = (piv[st] if bottom is None else bottom + piv[st]).values
    ax.set_title("CHECKS PER STATUS PER DAY", fontsize=10, loc="left", color=MUT, family="monospace")
    ax.legend(fontsize=8)
    for l in ax.get_xticklabels():
        l.set_rotation(30)
        l.set_ha("right")
    _save(fig, "checks_by_status.png")


def all_charts(marts):
    uptime_by_monitor(marts)
    latency_p95_trend(marts)
    incidents_by_monitor(marts)
    checks_by_status(marts)
    print("charts saved: uptime_by_monitor, latency_p95_trend, incidents_by_monitor, checks_by_status")
