"""Phase 7b: explainable investigation-priority score (NOT a probability of crime) + benign profile."""
from collections import Counter
import numpy as np

DISCLAIMER = "Investigation-priority score. Not a probability of criminal activity; requires human review."


def level(s):
    return "HIGH" if s >= 65 else "MEDIUM" if s >= 35 else "LOW"


def score_network(net):
    P = net["patterns"]
    cyc = [p for p in P if p["pattern"] == "circular_flow"]
    smu = [p for p in P if p["pattern"] == "smurfing"]
    circ = min(30, round(30 * max((p["retention_percent"] for p in cyc), default=0) / 90))
    vel = {"HIGH": 20, "MEDIUM": 12, "LOW": 4}[net["velocity"]["label"]]
    sm = min(20, 14 + min(6, max(p["unique_counterparties"] for p in smu) - 5)) if smu else 0
    nb, na = len(net["banks"]), len(net["accounts"])
    cross = 0 if nb < 2 else 5 if nb == 2 else 10
    st = min(10, 4 * len(net["pattern_types"]) + (4 if na >= 6 else 2 if na >= 4 else 0))
    el = net["velocity"]["elapsed_seconds"]
    tim = (6 if el <= 900 else 3 if el <= 14400 else 0) + round(4 * net["off_hours_fraction"])
    f = [("Circularity", circ, 30), ("Velocity", vel, 20), ("Smurfing", sm, 20),
         ("Cross-bank movement", cross, 10), ("Network structure", st, 10), ("Timing anomaly", min(tim, 10), 10)]
    s = sum(x[1] for x in f)
    return dict(score=s, level=level(s), factors=[dict(name=a, score=b, max=c) for a, b, c in f], disclaimer=DISCLAIMER)


def benign_profile(df, acct, in_cycle, in_chain):
    g = df[(df.sender_account == acct) | (df.receiver_account == acct)]
    cp = np.where(g.sender_account == acct, g.receiver_account, g.sender_account)
    c, n = Counter(cp), len(g)
    repeat = sum(v for v in c.values() if v >= 2) / n
    cva, cvg = [], []
    for k, v in c.items():
        if v >= 3:
            s = g[cp == k]; a = s.amount.to_numpy(); d = np.diff(s._ts.to_numpy())
            cva.append(a.std() / a.mean()); cvg.append(d.std() / d.mean() if d.mean() > 0 else 9)
    regular = len(cva) >= 3 and (np.median(cva) <= 0.1 or np.median(cvg) <= 0.35)
    checks = [
        dict(label="Stable counterparties", ok=bool(repeat >= 0.6), detail=f"{repeat:.0%} of transactions are with repeat counterparties"),
        dict(label="Broad distribution or regular timing/amounts", ok=bool(len(c) >= 20 or regular),
             detail=f"{len(c)} distinct counterparties" + ("; regular amounts/timing" if regular else "")),
        dict(label="No circular route", ok=not in_cycle, detail="No rapid circular flow involves this account" if not in_cycle else "Account is on a circular route"),
        dict(label="No rapid pass-through", ok=not in_chain, detail="No rapid multi-hop pass-through" if not in_chain else "Account is on a pass-through chain")]
    ok = all(x["ok"] for x in checks)
    return dict(account=acct, transactions=int(n), counterparties=len(c), checks=checks,
                classification="Likely normal high-volume commerce" if ok else "Mixed indicators - requires human review",
                likely_benign=ok, note="Contextual assessment only; not a certainty.")
