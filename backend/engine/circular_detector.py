"""Phase 4: time-respecting rapid paths. Cycles and chains are found in one DFS pass.
A hop is a transaction leaving the account that just received funds within max_gap seconds,
moving roughly the same amount (0.8x-1.02x). This keeps enumeration cheap and avoids
flagging slow, naturally-occurring cycles in ordinary P2P traffic."""
from bisect import bisect_right


def _maximal(paths):
    out, sets = [], []
    for p in sorted({tuple(p) for p in paths}, key=len, reverse=True):
        s = set(p)
        if not any(s <= k for k in sets):
            out.append(list(p)); sets.append(s)
    return out


def rapid_paths(df, max_len=6, max_gap=600, min_hop_ret=0.8):
    R = df.to_dict("records")
    T = [r["_ts"] for r in R]
    idx = {}
    for i, r in enumerate(R):
        idx.setdefault(r["sender_account"], []).append(i)
    tms = {s: [T[i] for i in l] for s, l in idx.items()}

    def nxt(i):
        r = R[i]; s = r["receiver_account"]
        l = idx.get(s)
        if not l:
            return
        for j in l[bisect_right(tms[s], T[i]):]:
            if T[j] - T[i] > max_gap:
                break
            if min_hop_ret * r["amount"] <= R[j]["amount"] <= 1.02 * r["amount"]:
                yield j

    cycles, paths = [], []

    def dfs(path, accts):
        ext = False
        for j in nxt(path[-1]):
            rc = R[j]["receiver_account"]
            if rc == R[path[0]]["sender_account"]:
                if len(path) + 1 >= 3:
                    cycles.append(path + [j])
                ext = True
            elif rc not in accts and len(path) < max_len:
                ext = True
                dfs(path + [j], accts | {rc})
        if not ext and len(path) >= 3:
            paths.append(path)

    for i in range(len(R)):
        dfs([i], {R[i]["sender_account"], R[i]["receiver_account"]})
    cycles = _maximal(cycles)
    cs = [set(c) for c in cycles]
    paths = [p for p in _maximal(paths) if not any(set(p) <= c for c in cs)]  # open slice of a cycle != mule chain
    return dict(R=R, cycles=cycles, paths=paths)


def path_metrics(R, path, cycle=False):
    tx = [R[i] for i in path]
    t = [x["timestamp"] for x in tx]
    el = (t[-1] - t[0]).total_seconds()
    accts = [x["sender_account"] for x in tx] + ([] if cycle else [tx[-1]["receiver_account"]])
    ini, fin = tx[0]["amount"], tx[-1]["amount"]
    return dict(accounts=accts, hops=len(tx), transaction_ids=[x["transaction_id"] for x in tx],
                elapsed_seconds=int(el), avg_delay_seconds=round(el / len(tx), 1),
                initial_amount=int(ini), final_amount=int(fin), retention_percent=round(fin / ini * 100, 1),
                total_amount=int(sum(x["amount"] for x in tx)),
                banks=sorted({x["sender_bank"] for x in tx} | {x["receiver_bank"] for x in tx}),
                start=t[0].isoformat(), end=t[-1].isoformat())


def detect_cycles(found):
    return [dict(pattern="circular_flow", **path_metrics(found["R"], p, True)) for p in found["cycles"]]
