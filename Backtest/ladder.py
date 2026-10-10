"""
Ladder ticket simulator.

Monte Carlo over a strategy's verified trade distribution: each "ticket" is a
small account that risks `risk_pct` of its current equity per trade until it
reaches `target`, falls to `floor`, or the `time_box_days` run out. Trades are
drawn (with replacement, random order) from the strategy's R-multiples; the gap
between trades is drawn from the strategy's empirical inter-trade gaps in days.

This is a measurement tool, not a recommendation. P(ruin) is always printed in
the same row as P(target).

Usage:
  python ladder.py [--config ladder.toml] [--out results/ladder]
Tests:
  python -m unittest tests.test_ladder
"""
import argparse
import csv
import datetime as dt
import json
import os
import tomllib

import numpy as np


# ----------------------------------------------------------------- distribution
def load_trades(path):
    """Returns list of (open_time, R) from a backtest trades.csv."""
    out = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            out.append((dt.datetime.fromisoformat(row["open"]), float(row["R"])))
    out.sort()
    return out


def load_calendar(path):
    """Returns sorted list of event datetimes, or None if the file is missing."""
    if not os.path.exists(path):
        return None
    ev = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            ev.append(dt.datetime.fromisoformat(row["time"]))
    return sorted(ev)


def in_session(t, sessions, session_hours):
    return any(session_hours[s][0] <= t.hour < session_hours[s][1] for s in sessions)


def near_event(t, events, minutes=30):
    if not events:
        return False
    win = dt.timedelta(minutes=minutes)
    i = np.searchsorted(np.array(events, dtype="datetime64[s]"), np.datetime64(t, "s"))
    for j in (i - 1, i):
        if 0 <= j < len(events) and abs(events[j] - t) <= win:
            return True
    return False


def build_distribution(trades, cfg, events):
    """Filter by session / news, return dict with R array, gap array, stats."""
    kept = [(t, r) for t, r in trades
            if in_session(t, cfg["sessions"], cfg["session_hours"])
            and not (cfg["news_blackout"] and near_event(t, events))]
    if len(kept) < 2:
        raise SystemExit("fewer than 2 trades after filtering; cannot build a distribution")
    R = np.array([r for _, r in kept])
    times = [t for t, _ in kept]
    gaps = np.array([(b - a).total_seconds() / 86400 for a, b in zip(times[:-1], times[1:])])
    span_days = (times[-1] - times[0]).total_seconds() / 86400
    return dict(R=R, gaps=gaps, n=len(R), n_raw=len(trades),
                win_rate=float((R > 0).mean()), avg_R=float(R.mean()),
                trades_per_day=len(R) / span_days if span_days > 0 else float("nan"),
                first=times[0], last=times[-1])


# ----------------------------------------------------------------- simulation
def simulate(R, gaps, start, target, floor, risk_pct, time_box_days, tickets, rng, max_trades=None):
    """
    Vectorised over tickets. Returns dict of arrays: final equity, outcome code
    (1 = target, -1 = ruin, 0 = time-box expired), day of exit, trades taken.
    Loss per trade is capped at the risked amount (hard stop): R is clipped at -1
    on the downside only when it would take equity below zero.
    """
    f = risk_pct / 100.0
    # Enough trades to exhaust the time box in nearly all tickets; +50 margin
    if max_trades is None:
        max_trades = int(time_box_days / max(np.min(gaps), 1e-6)) + 50
        max_trades = min(max_trades, 5000)
    r = rng.choice(R, size=(tickets, max_trades), replace=True)
    g = rng.choice(gaps, size=(tickets, max_trades), replace=True)
    day = np.cumsum(g, axis=1)                       # day at which trade k closes/opens

    equity = np.full(tickets, float(start))
    final = equity.copy()
    outcome = np.zeros(tickets, dtype=int)
    exit_day = np.full(tickets, float(time_box_days))
    n_trades = np.zeros(tickets, dtype=int)
    alive = np.ones(tickets, dtype=bool)

    for k in range(max_trades):
        act = alive & (day[:, k] <= time_box_days)
        if not act.any():
            break
        step = 1.0 + f * r[act, k]
        equity[act] = np.maximum(equity[act] * step, 0.0)
        n_trades[act] += 1
        hit = act & (equity >= target)
        dead = act & (equity <= floor) & ~hit
        for mask, code in ((hit, 1), (dead, -1)):
            outcome[mask] = code
            exit_day[mask] = day[mask, k]
            final[mask] = equity[mask]
        alive &= ~(hit | dead)
    final[alive] = equity[alive]
    return dict(final=final, outcome=outcome, exit_day=exit_day, n_trades=n_trades)


def summarise(sim, start):
    o, fin, ed = sim["outcome"], sim["final"], sim["exit_day"]
    dead = o == -1
    return dict(
        p_target=float((o == 1).mean()),
        p_ruin=float(dead.mean()),
        p_timeout=float((o == 0).mean()),
        median_final=float(np.median(fin)),
        median_days_to_death=float(np.median(ed[dead])) if dead.any() else None,
        ev_per_dollar=float(fin.mean() / start),      # expected final equity per $1 staked
        mean_trades=float(sim["n_trades"].mean()),
    )


# ----------------------------------------------------------------- report
def write_report(path, cfg, dist, rows, calendar_note):
    def pct(x):
        return f"{x * 100:.1f}%"
    lines = [
        f"# Ladder ticket simulation: {cfg['strategy']}",
        "",
        "**Measurement, not a recommendation.** Every row shows the probability of ruin next to the probability of success.",
        "",
        "## Setup",
        f"* Ticket: ${cfg['start_balance']:,.0f} start, target ${cfg['target']:,.0f} "
        f"(x{cfg['target'] / cfg['start_balance']:.1f}), dead at or below ${cfg['floor']:,.0f}, "
        f"time box {cfg['time_box_days']} days",
        f"* Tickets per risk level: {cfg['tickets']:,}; RNG seed: {cfg['seed']}",
        f"* Trade source: `{cfg['trades_csv']}` ({dist['n_raw']} trades, "
        f"{dist['first']:%Y-%m-%d} to {dist['last']:%Y-%m-%d})",
        f"* Session filter {cfg['sessions']}: {dist['n']} trades kept",
        f"* News blackout: {calendar_note}",
        f"* Distribution: win rate {dist['win_rate'] * 100:.1f}%, average {dist['avg_R']:+.3f}R, "
        f"{dist['trades_per_day'] * 30:.1f} trades per 30 days, "
        f"median gap between trades {np.median(dist['gaps']):.1f} days",
        "",
        "## Results",
        "",
        "| Risk % per trade | P(reach target) | P(ruin) | P(time-box expired) | Median final equity | Median day of death | EV per $1 | Avg trades |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for rp, s in rows:
        dod = f"{s['median_days_to_death']:.0f}" if s["median_days_to_death"] is not None else "-"
        lines.append(f"| {rp:.0f}% | {pct(s['p_target'])} | **{pct(s['p_ruin'])}** | {pct(s['p_timeout'])} | "
                     f"${s['median_final']:,.0f} | {dod} | {s['ev_per_dollar']:.2f} | {s['mean_trades']:.1f} |")
    lines += [
        "",
        "EV per $1 = mean final equity / start balance (1.00 = break-even on average). It rises with risk while the",
        "median falls: the mean is carried by the rare tickets that catch a big winner, the typical ticket loses money.",
        "",
        "## Caveats",
        "* The trade list comes from a bar-level backtest that has not been reconciled against MT5 (plan Phase 0); "
        "treat the distribution as unverified.",
        "* Trades are drawn independently; real losing streaks cluster in flat regimes, so ruin is more likely than shown.",
        "* Loss per trade is capped at the risked amount (hard stop). Gap slippage beyond the stop is included in R "
        "only as far as the backtest modelled it.",
        f"* The time box ({cfg['time_box_days']} days) holds only about "
        f"{dist['trades_per_day'] * cfg['time_box_days']:.0f} trades of this strategy; most tickets simply expire.",
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="ladder.toml")
    ap.add_argument("--out", default="results/ladder")
    a = ap.parse_args()
    with open(a.config, "rb") as f:
        cfg = tomllib.load(f)
    base = os.path.dirname(os.path.abspath(a.config))
    trades = load_trades(os.path.join(base, cfg["trades_csv"]))
    events = load_calendar(os.path.join(base, cfg["news_calendar"])) if cfg["news_blackout"] else None
    if cfg["news_blackout"] and events is None:
        calendar_note = f"requested but `{cfg['news_calendar']}` not found; **blackout NOT applied**"
    elif cfg["news_blackout"]:
        calendar_note = f"on, {len(events)} events from `{cfg['news_calendar']}`"
    else:
        calendar_note = "off"
    dist = build_distribution(trades, cfg, events)

    rows, out_json = [], dict(config=cfg, seed=cfg["seed"], distribution={
        k: (v if not isinstance(v, (np.ndarray, dt.datetime)) else str(v)) for k, v in dist.items()
        if k not in ("R", "gaps")}, results={})
    for rp in cfg["risk_levels"]:
        rng = np.random.default_rng(cfg["seed"])          # same seed per level: paired comparison
        sim = simulate(dist["R"], dist["gaps"], cfg["start_balance"], cfg["target"], cfg["floor"],
                       rp, cfg["time_box_days"], cfg["tickets"], rng)
        s = summarise(sim, cfg["start_balance"])
        rows.append((rp, s))
        out_json["results"][str(rp)] = s
        print(f"risk {rp:4.0f}%  P(target) {s['p_target']*100:5.1f}%  P(ruin) {s['p_ruin']*100:5.1f}%  "
              f"median final ${s['median_final']:,.0f}  EV/$ {s['ev_per_dollar']:.2f}")

    out_dir = os.path.join(base, a.out)
    write_report(os.path.join(out_dir, f"{cfg['strategy']}.md"), cfg, dist, rows, calendar_note)
    with open(os.path.join(out_dir, f"{cfg['strategy']}.json"), "w") as f:
        json.dump(out_json, f, indent=2, default=str)
    print("wrote", os.path.join(out_dir, f"{cfg['strategy']}.md"))


if __name__ == "__main__":
    main()
