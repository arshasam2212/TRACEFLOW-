"""Phase 6: many-to-one (smurfing) and one-to-many bursts.
Flags a burst only when senders are mostly NEW counterparties and amounts are tightly clustered
(structuring). Repeat customers / varied amounts (normal commerce) do not qualify."""
from collections import Counter
import numpy as np


def detect_smurfing(df, window=14400, min_senders=5, max_cv=0.35, min_new_ratio=0.7,
                    min_amount=1000, direction="in"):
    key, oth = ("receiver_account", "sender_account") if direction == "in" else ("sender_account", "receiver_account")
    out = []
    for hub, g in df.groupby(key):
        if len(g) < min_senders:
            continue
        ts, am = g["_ts"].to_numpy(), g["amount"].to_numpy()
        cp, ids = g[oth].to_numpy(), g["transaction_id"].to_numpy()
        tot, n, i = Counter(cp), len(g), 0
        while i < n:
            j = int(np.searchsorted(ts, ts[i] + window, side="right"))
            uniq = set(cp[i:j])
            if len(uniq) >= min_senders:
                a = am[i:j]
                new = sum(1 for s in uniq if tot[s] <= 2) / len(uniq)
                if a.std() / a.mean() <= max_cv and a.mean() >= min_amount and new >= min_new_ratio:
                    out.append(_record(df, g, i, j, hub, direction, a, ts, cp, ids, window))
                    i = j
                    continue
            i += 1
    return out


def _record(df, g, i, j, hub, direction, a, ts, cp, ids, window):
    senders = sorted(set(map(str, cp[i:j])))
    total, span = float(a.sum()), float(ts[j - 1] - ts[i])
    tx_ids = list(map(str, ids[i:j]))
    banks = set(g["sender_bank"].iloc[i:j]) | set(g["receiver_bank"].iloc[i:j])
    fwd, extra = None, []
    if direction == "in":  # onward movement of the collected funds within 2h
        end = ts[j - 1]
        nxt = df[(df.sender_account == hub) & (df._ts > end) & (df._ts <= end + 7200) & (df.amount >= 0.8 * total)]
        if len(nxt):
            r = nxt.iloc[0]
            fwd = r.receiver_account; tx_ids.append(r.transaction_id)
            banks |= {r.sender_bank, r.receiver_bank}
    cnt, edges = np.histogram(a, bins=5)
    return dict(pattern="smurfing" if direction == "in" else "one_to_many", hub_account=hub,
                accounts=[hub] + senders + ([fwd] if fwd else []), forward_account=fwd,
                unique_counterparties=len(senders), hops=1, transaction_ids=tx_ids,
                total_amount=int(total), avg_amount=int(a.mean()), min_amount=int(a.min()), max_amount=int(a.max()),
                amount_distribution=[dict(low=int(edges[k]), high=int(edges[k + 1]), count=int(cnt[k])) for k in range(5)],
                span_seconds=int(span), elapsed_seconds=int(span), avg_delay_seconds=round(span / max(len(a) - 1, 1), 1),
                time_concentration=round(1 - span / window, 2), banks=sorted(banks),
                retention_percent=round(float(df[df.transaction_id == tx_ids[-1]].amount.iloc[0]) / total * 100, 1) if fwd else None,
                start=g["timestamp"].iloc[i].isoformat(), end=g["timestamp"].iloc[j - 1].isoformat())
