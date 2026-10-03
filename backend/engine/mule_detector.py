"""Phase 5: rapid pass-through chains A->B->C->D (>=3 hops, each within max_gap seconds)."""
from .circular_detector import path_metrics


def detect_mule_chains(found):
    out = []
    for p in found["paths"]:
        m = path_metrics(found["R"], p)
        m.update(pattern="mule_chain", intermediaries=len(m["accounts"]) - 2, bank_count=len(m["banks"]))
        out.append(m)
    return out
