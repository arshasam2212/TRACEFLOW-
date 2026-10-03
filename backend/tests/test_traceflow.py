import json, sys, pathlib
import pandas as pd, pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.graph_builder import validate, DataError, build_graph
from engine.network_analyzer import analyze
from engine.velocity_engine import velocity
from engine.risk_engine import score_network
TRUTH = json.load(open(ROOT / "data" / "ground_truth.json"))


@pytest.fixture(scope="module")
def A():
    return analyze(validate(pd.read_csv(ROOT / "data" / "transactions.csv"))[0])


def tiny(rows):
    return pd.DataFrame(rows, columns=["transaction_id", "timestamp", "sender_account", "receiver_account", "sender_bank",
                                       "receiver_bank", "amount", "transaction_type", "location"])


def test_ground_truth_rediscovered(A):
    for k, v in TRUTH.items():
        if not v["suspicious"]:
            continue
        best = max(A.networks.values(), key=lambda n: len(set(n["accounts"]) & set(v["accounts"])))
        assert set(v["accounts"]) <= set(best["accounts"]), k
        assert set(v["expected_patterns"]) <= set(best["pattern_types"]), k
    assert len(A.networks) == sum(v["suspicious"] for v in TRUTH.values())


def test_cycle_metrics(A):
    p = [p for p in A.networks[A.acct_net["A101"]]["patterns"] if p["pattern"] == "circular_flow"][0]
    assert (p["hops"], p["elapsed_seconds"], p["retention_percent"]) == (4, 94, 90.8)


def test_mule_and_smurf_detected(A):
    assert "mule_chain" in A.networks[A.acct_net["A501"]]["pattern_types"]
    s = [p for p in A.networks[A.acct_net["A700"]]["patterns"] if p["pattern"] == "smurfing"][0]
    assert s["unique_counterparties"] == 8 and s["hub_account"] == "A700"


def test_benign_not_flagged(A):
    for a in ["A1086", "A1011", "A1001", "A1041"]:
        assert a not in A.acct_net
    assert any(b["account"] == "A1086" and b["likely_benign"] for b in A.benign)


def test_velocity():
    from datetime import datetime, timedelta
    t = datetime(2026, 1, 1)
    v = velocity([t, t + timedelta(seconds=31), t + timedelta(seconds=62), t + timedelta(seconds=94)])
    assert v["elapsed_seconds"] == 94 and v["label"] == "HIGH" and v["median_delay_seconds"] == 31


def test_risk_score(A):
    for n in A.networks.values():
        r = n["risk"]
        assert 0 <= r["score"] <= 100 and r["score"] == sum(f["score"] for f in r["factors"])
        assert all(f["score"] <= f["max"] for f in r["factors"])


def test_csv_validation():
    with pytest.raises(DataError):
        validate(tiny([]))
    with pytest.raises(DataError):
        validate(pd.DataFrame({"a": [1]}))
    clean, rep = validate(tiny([["T1", "2026-01-01T10:00:00", "A", "B", "X", "Y", 100, "T", "C"],
                                ["T2", "not-a-date", "A", "B", "X", "Y", 100, "T", "C"],
                                ["T3", "2026-01-01T10:00:00", "A", "B", "X", "Y", "abc", "T", "C"],
                                ["T4", "2026-01-01T10:00:00", "", "B", "X", "Y", 5, "T", "C"]]))
    assert len(clean) == 1 and rep["rows_dropped"] == 3
    assert analyze(clean).networks == {}  # no suspicious network: no crash
    assert len(build_graph(clean).edges) == 1


def test_api():
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        assert c.get("/api/dashboard/stats").json()["stats"]["suspicious_networks"] == 23
        nid = c.get("/api/accounts/A101/flow").json()["network_id"]
        assert c.get("/api/accounts/A101/replay").json()["final_label"] == "CIRCULAR FLOW DETECTED"
        assert c.get("/api/networks/" + nid).json()["elements"]["edges"]
        assert c.get("/api/investigations/" + nid).json()["evidence"]
        assert "retained" in c.get(f"/api/investigations/{nid}/explanation").json()["text"]
        w = c.post(f"/api/investigations/{nid}/what-if", json={"account": "A205"}).json()
        assert w["simulation"] and w["after"]["cycles"] == 0
        assert c.get(f"/api/investigations/{nid}/dossier").content[:4] == b"%PDF"
        assert c.get("/api/accounts/NOPE").status_code == 404
        assert c.get("/api/accounts/A1086/flow").json()["found"] is False
        assert c.post("/api/transactions/upload", files={"file": ("x.csv", b"")}).status_code == 400
        up = c.post("/api/transactions/upload", files={"file": ("t.csv", open(ROOT / "data" / "transactions.csv", "rb"))})
        assert up.json()["ok"] and up.json()["stats"]["transactions"] == 20400
