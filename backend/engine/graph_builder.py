"""Phase 3: validation + directed temporal multigraph."""
import pandas as pd
import networkx as nx

REQ = ["transaction_id", "timestamp", "sender_account", "receiver_account", "sender_bank",
       "receiver_bank", "amount", "transaction_type", "location"]


class DataError(ValueError):
    """Friendly, user-facing data problem."""


def validate(df):
    """Return (clean_df, report). Never crashes on bad rows; drops and counts them."""
    if df is None or len(df) == 0:
        raise DataError("The CSV is empty - upload a file with transaction rows.")
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    miss = [c for c in REQ if c not in df.columns]
    if miss:
        raise DataError("Missing required columns: " + ", ".join(miss))
    n = len(df)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    for c in REQ:
        if c not in ("timestamp", "amount"):
            df[c] = df[c].fillna("").astype(str).str.strip()
    reasons = {
        "invalid_timestamp": df.timestamp.isna(),
        "invalid_amount": df.amount.isna() | (df.amount <= 0),
        "missing_account": (df.sender_account == "") | (df.receiver_account == ""),
        "self_transfer": (df.sender_account == df.receiver_account) & (df.sender_account != ""),
    }
    bad = pd.concat(reasons.values(), axis=1).any(axis=1)
    if bad.all():
        raise DataError("No valid rows found (check timestamps, amounts and account columns).")
    out = df[~bad].copy()
    blank = out.transaction_id == ""
    out.loc[blank, "transaction_id"] = [f"ROW{i}" for i in out.index[blank]]
    out = out.drop_duplicates("transaction_id").sort_values("timestamp", kind="stable").reset_index(drop=True)
    out["_ts"] = out.timestamp.map(lambda t: t.timestamp())
    report = dict(rows_in=n, rows_valid=len(out), rows_dropped=n - len(out),
                  dropped_reasons={k: int(v.sum()) for k, v in reasons.items() if v.sum()})
    return out, report


def build_graph(df):
    G = nx.MultiDiGraph()
    for r in df.itertuples(index=False):
        G.add_node(r.sender_account, bank=r.sender_bank)
        G.add_node(r.receiver_account, bank=r.receiver_bank)
        G.add_edge(r.sender_account, r.receiver_account, key=r.transaction_id, transaction_id=r.transaction_id,
                   amount=float(r.amount), timestamp=r.timestamp, transaction_type=r.transaction_type)
    return G


def simple_digraph(G):
    return nx.DiGraph(G)


def temporal_edges(G):
    return sorted(G.edges(keys=True, data=True), key=lambda e: e[3]["timestamp"])


def centrality(G):
    return nx.degree_centrality(simple_digraph(G))


def extract_subgraph(G, tx_ids):
    ids = set(tx_ids)
    return G.edge_subgraph([(u, v, k) for u, v, k in G.edges(keys=True) if k in ids]).copy()
