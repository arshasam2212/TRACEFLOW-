"""Phases 8/11/12/13: shared analysis state, flow, replay, what-if, investigation detail."""
import io, time
from itertools import islice
from pathlib import Path
import networkx as nx
import pandas as pd
from engine.graph_builder import validate, DataError
from engine.network_analyzer import analyze

DATA = Path(__file__).resolve().parent.parent / "data"
STATE = {"A": None}
SCENARIOS = [(1, "Circular laundering route", "A101"), (2, "Rapid mule chain", "A501"),
             (3, "Smurfing ring", "A700"), (4, "Normal high-volume commerce", "A1086"),
             (5, "Mixed circular + mule network", "A801")]
LABEL = dict(circular_flow="CIRCULAR FLOW DETECTED", mule_chain="RAPID MULE CHAIN DETECTED",
             smurfing="SMURFING RING DETECTED", one_to_many="ONE-TO-MANY BURST DETECTED")


def load_df(df):
    t, stages = time.time(), []
    clean, report = validate(df); stages.append(("Validated schema and parsed timestamps", round(time.time() - t, 2)))
    A = analyze(clean); stages.append(("Built graph and ran detectors", round(time.time() - t, 2)))
    A.report, STATE["A"] = report, A
    return A, stages


def load_default():
    return load_df(pd.read_csv(DATA / "transactions.csv"))[0]


def load_upload(raw: bytes):
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception:
        raise DataError("Could not read this file as CSV. Check the format and try again.")
    return load_df(df)


def get():
    return STATE["A"] or load_default()


def net_of(nid):
    A = get()
    if nid not in A.networks:
        raise LookupError(f"Network {nid} not found.")
    return A, A.networks[nid]


def scenarios():
    A = get()
    return [dict(id=i, title=t, account=a, network_id=A.acct_net.get(a), available=a in A.G) for i, t, a in SCENARIOS]


def elements(A, net):
    tx = A.txs(net["transaction_ids"])
    return dict(
        nodes=[dict(data=dict(id=a, label=a, bank=A.G.nodes[a]["bank"], key=a == net["key_intermediary"])) for a in net["accounts"]],
        edges=[dict(data=dict(id=t["transaction_id"], source=t["sender_account"], target=t["receiver_account"],
                              amount=t["amount"], timestamp=t["timestamp"], bank_s=t["sender_bank"],
                              bank_r=t["receiver_bank"], type=t["transaction_type"])) for t in tx])


def summary(net):
    return dict(id=net["id"], case_id=net["case_id"], category=net["category"], pattern_types=net["pattern_types"],
                accounts=len(net["accounts"]), banks=net["banks"], total_amount=net["total_amount"],
                tx_count=net["tx_count"], risk=net["risk"], status=net["status"], start=net["start"],
                key_intermediary=net["key_intermediary"])


def dashboard():
    A = get()
    return dict(stats=A.stats, recent=[summary(n) for n in list(A.networks.values())[:10]], high_volume=A.benign[:6],
                report=getattr(A, "report", None))


def list_networks(pattern=None, bank=None, risk=None, min_amount=0):
    out = [n for n in get().networks.values()
           if (not pattern or pattern in n["pattern_types"]) and (not bank or bank in n["banks"])
           and (not risk or n["risk"]["level"] == risk.upper()) and n["total_amount"] >= min_amount]
    return [summary(n) for n in out]


def account(acc):
    A = get()
    if acc not in A.G:
        raise LookupError(f"Account {acc} was not found in the loaded dataset.")
    df = A.df
    s, r = df[df.sender_account == acc], df[df.receiver_account == acc]
    nid = A.acct_net.get(acc)
    prof = None
    if len(s) + len(r) >= 20:
        from engine.risk_engine import benign_profile
        prof = benign_profile(df, acc, acc in A.cyc_accts, acc in A.chain_accts)
    recent = pd.concat([s, r]).sort_values("_ts").tail(15)
    return dict(account_id=acc, bank=A.G.nodes[acc]["bank"], sent_count=len(s), sent_total=int(s.amount.sum()),
                received_count=len(r), received_total=int(r.amount.sum()), network_id=nid,
                case_id=A.networks[nid]["case_id"] if nid else None, risk=A.networks[nid]["risk"] if nid else None,
                profile=prof, recent=[A.txs([i])[0] for i in recent.transaction_id])


def flow(acc):
    A = get()
    if acc not in A.G:
        raise LookupError(f"Account {acc} was not found in the loaded dataset.")
    nid = A.acct_net.get(acc)
    if not nid:
        return dict(found=False, account=acc, message="No suspicious money-flow pattern involves this account.",
                    profile=account(acc)["profile"])
    net = A.networks[nid]
    order = {"circular_flow": 0, "mule_chain": 1, "smurfing": 2, "one_to_many": 3}
    cand = [p for p in net["patterns"] if acc in p["accounts"]] or net["patterns"]
    p = sorted(cand, key=lambda p: order[p["pattern"]])[0]
    ids = list(p["transaction_ids"])
    if p["pattern"] == "circular_flow":
        k = next((i for i, t in enumerate(A.txs(ids)) if t["sender_account"] == acc), 0)
        ids = ids[k:] + ids[:k]
    elif p["pattern"] in ("smurfing", "one_to_many"):
        ids.sort(key=lambda i: A.rows[i]["_ts"])
    steps = A.txs(ids)
    t0 = A.rows[ids[0]]["_ts"]
    run = 0
    for s in steps:
        run += s["amount"]
        s["offset_seconds"] = int(A.rows[s["transaction_id"]]["_ts"] - t0); s["cumulative_amount"] = int(run)
    ret = steps[-1]["amount"] / steps[0]["amount"] * 100 if p["pattern"] != "smurfing" else p.get("retention_percent")
    return dict(found=True, account=acc, network_id=nid, case_id=net["case_id"], pattern=p["pattern"],
                label=LABEL[p["pattern"]], steps=steps, summary=dict(
                    total_amount=int(run), elapsed_seconds=steps[-1]["offset_seconds"], hops=len(steps),
                    retention_percent=round(ret, 1) if ret is not None else None,
                    banks=p["banks"], patterns=net["pattern_types"]))


def evidence(net):
    ev = []
    for p in net["patterns"]:
        if p["pattern"] == "circular_flow":
            ev += [f"Circular route detected ({len(p['accounts'])} accounts, {p['hops']} hops)",
                   f"{p['retention_percent']}% of value retained", f"{p['elapsed_seconds']}-second cycle"]
        elif p["pattern"] == "mule_chain":
            ev.append(f"Rapid pass-through detected ({p['hops']} hops in {p['elapsed_seconds']} seconds, {p['intermediaries']} intermediaries)")
        elif p["pattern"] == "smurfing":
            ev.append(f"{p['unique_counterparties']} first-time senders converged on {p['hub_account']} within {round(p['span_seconds']/60)} minutes")
            ev.append(f"Amounts tightly clustered ({p['min_amount']:,} - {p['max_amount']:,})")
            if p["forward_account"]:
                ev.append(f"Collected funds forwarded onward to {p['forward_account']}")
        else:
            ev.append(f"One-to-many burst from {p['hub_account']} to {p['unique_counterparties']} accounts")
    if len(net["banks"]) > 1:
        ev.append(f"Cross-bank movement across {len(net['banks'])} banks")
    return list(dict.fromkeys(ev))


def investigation(nid):
    A, net = net_of(nid)
    roles = {}
    for p in net["patterns"]:
        for i, a in enumerate(p["accounts"]):
            r = ("collector" if a == p.get("hub_account") else "sender" if p["pattern"] == "smurfing" else
                 "cycle member" if p["pattern"] == "circular_flow" else
                 "source" if i == 0 else "destination" if i == len(p["accounts"]) - 1 else "intermediary")
            roles.setdefault(a, r)
    return dict(summary(net), network=net["id"], evidence=evidence(net), dna=net["dna"], velocity=net["velocity"],
                patterns=net["patterns"], timeline=A.txs(net["transaction_ids"]), elements=elements(A, net),
                accounts=[dict(account_id=a, bank=A.G.nodes[a]["bank"], role=roles.get(a, "participant")) for a in net["accounts"]],
                start=net["start"], end=net["end"])


def what_if(nid, acc):
    A, net = net_of(nid)
    if acc not in net["accounts"]:
        raise LookupError(f"{acc} is not part of {nid}.")
    tx = A.txs(net["transaction_ids"])
    g = nx.DiGraph([(t["sender_account"], t["receiver_account"]) for t in tx])
    h = g.copy(); h.remove_node(acc)

    def m(x):
        pairs = sum(len(nx.descendants(x, n)) for n in x)
        paths = 0
        for a in x:
            for b in x:
                if a != b:
                    paths += sum(1 for _ in islice(nx.all_simple_paths(x, a, b), 500))
        return dict(reachable_pairs=pairs, paths=paths, components=nx.number_weakly_connected_components(x) if len(x) else 0,
                    cycles=sum(1 for _ in nx.simple_cycles(x)), accounts=len(x))
    b, a = m(g), m(h)
    touched = [t for t in tx if acc in (t["sender_account"], t["receiver_account"])]
    return dict(simulation=True, removed_account=acc, network_id=nid, before=b, after=a,
                connectivity_before=100, connectivity_after=round(a["reachable_pairs"] / b["reachable_pairs"] * 100) if b["reachable_pairs"] else 0,
                disrupted_transactions=len(touched), total_transactions=len(tx),
                disrupted_amount=int(sum(t["amount"] for t in touched)),
                label="SIMULATION - hypothetical removal; no real accounts or transactions are affected")
