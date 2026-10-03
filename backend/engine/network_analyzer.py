"""Phase 3-7 orchestrator: run detectors, merge patterns into networks, score them."""
from collections import defaultdict
import networkx as nx
import pandas as pd
from .graph_builder import build_graph
from .circular_detector import rapid_paths, detect_cycles
from .mule_detector import detect_mule_chains
from .smurfing_detector import detect_smurfing
from .velocity_engine import velocity
from .risk_engine import score_network, benign_profile

DEFAULTS = dict(max_cycle_len=6, max_gap=600, smurf_window=14400, smurf_min_senders=5)
CAT = dict(circular_flow="Circular", mule_chain="Mule", smurfing="Smurfing", one_to_many="Smurfing")


def public(r):
    d = {k: v for k, v in r.items() if k != "_ts"}
    d["timestamp"] = d["timestamp"].isoformat()
    return d


class Analysis:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def txs(self, ids):
        return [public(self.rows[i]) for i in ids]


def _network(plist, rows):
    accts = sorted({a for p in plist for a in p["accounts"]})
    ids = sorted({i for p in plist for i in p["transaction_ids"]}, key=lambda i: rows[i]["_ts"])
    tx = [rows[i] for i in ids]
    banks = sorted({r["sender_bank"] for r in tx} | {r["receiver_bank"] for r in tx})
    types = sorted({p["pattern"] for p in plist})
    cats = sorted({CAT[t] for t in types})
    hop = [p for p in plist if p["pattern"] in ("circular_flow", "mule_chain")]
    cyc = [p for p in plist if p["pattern"] == "circular_flow"]
    rets = [p["retention_percent"] for p in plist if p.get("retention_percent") is not None]
    vel = velocity([r["timestamp"] for r in tx])
    sg = nx.DiGraph([(r["sender_account"], r["receiver_account"]) for r in tx])
    bc = nx.betweenness_centrality(sg)
    key = max(accts, key=lambda a: (bc.get(a, 0), sg.degree(a)))
    net = dict(accounts=accts, banks=banks, pattern_types=types, category=cats[0] if len(cats) == 1 else "Mixed",
               patterns=plist, transaction_ids=ids, tx_count=len(ids), total_amount=int(sum(r["amount"] for r in tx)),
               start=tx[0]["timestamp"].isoformat(), end=tx[-1]["timestamp"].isoformat(), velocity=vel,
               off_hours_fraction=sum(r["timestamp"].hour < 6 for r in tx) / len(tx), key_intermediary=key,
               dna=dict(accounts=len(accts), transactions=len(ids),
                        circularity=round(max((p["retention_percent"] for p in cyc), default=0)),
                        velocity=vel["label"], retention=round(max(rets)) if rets else None,
                        cross_bank=len(banks) > 1, smurfing=any(t in types for t in ("smurfing", "one_to_many")),
                        mule_chain="mule_chain" in types, hop_patterns=len(hop)))
    net["risk"] = score_network(net)
    net["status"] = "Open" if net["risk"]["level"] == "HIGH" else "Under review"
    return net


def analyze(df, cfg=None):
    c = {**DEFAULTS, **(cfg or {})}
    G = build_graph(df)
    rows = {r["transaction_id"]: r for r in df.to_dict("records")}
    found = rapid_paths(df, c["max_cycle_len"], c["max_gap"])
    cyc, chn = detect_cycles(found), detect_mule_chains(found)
    sm = detect_smurfing(df, c["smurf_window"], c["smurf_min_senders"])
    sm += detect_smurfing(df, c["smurf_window"], c["smurf_min_senders"], direction="out")
    pats = cyc + chn + sm
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for p in pats:
        for x in p["accounts"][1:]:
            parent[find(x)] = find(p["accounts"][0])
    groups = defaultdict(list)
    for p in pats:
        groups[find(p["accounts"][0])].append(p)
    nets = sorted((_network(pl, rows) for pl in groups.values()), key=lambda n: (-n["risk"]["score"], n["start"]))
    networks = {}
    for i, n in enumerate(nets, 1):
        n["id"], n["case_id"] = f"network_{i:03d}", f"TF-{i:04d}"
        networks[n["id"]] = n
    acct_net = {a: n["id"] for n in nets for a in n["accounts"]}
    cyc_a, chn_a = {a for p in cyc for a in p["accounts"]}, {a for p in chn for a in p["accounts"]}
    cnt = pd.concat([df.sender_account, df.receiver_account]).value_counts()
    benign = sorted((benign_profile(df, a, a in cyc_a, a in chn_a) for a in cnt[cnt >= 100].index if a not in acct_net),
                    key=lambda b: -b["transactions"])
    cat = defaultdict(int)
    for n in nets:
        cat[n["category"]] += 1
    stats = dict(transactions=len(df), accounts=int(len(G)), flagged_accounts=len(acct_net), suspicious_networks=len(nets),
                 mule_chains=sum("mule_chain" in n["pattern_types"] for n in nets),
                 smurfing_rings=sum(n["dna"]["smurfing"] for n in nets), high_volume_cleared=len(benign),
                 distribution=[dict(name=k, count=cat.get(k, 0)) for k in ("Circular", "Mule", "Smurfing", "Mixed")])
    return Analysis(df=df, G=G, rows=rows, networks=networks, acct_net=acct_net, cyc_accts=cyc_a,
                    chain_accts=chn_a, benign=benign, stats=stats)
