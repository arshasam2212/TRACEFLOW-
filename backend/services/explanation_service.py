"""Phase 14: deterministic evidence-to-text explanation. Optional Ollama polish (OLLAMA_MODEL env var).
The LLM only rewords the template; it never receives or produces new facts."""
import json, os, urllib.request


def _inr(n):
    return f"₹{int(n):,}"


def template(net):
    parts = [f"{net['case_id']} ({net['id']}) involves {len(net['accounts'])} accounts and {net['tx_count']} transactions "
             f"totalling {_inr(net['total_amount'])}."]
    for p in net["patterns"]:
        if p["pattern"] == "circular_flow":
            parts.append(f"{len(p['accounts'])} accounts form a circular transaction path. The cycle completed within "
                         f"{p['elapsed_seconds']} seconds, with approximately {p['retention_percent']}% of the initial value "
                         f"({_inr(p['initial_amount'])}) retained at the end ({_inr(p['final_amount'])}).")
        elif p["pattern"] == "mule_chain":
            parts.append(f"Funds moved through {p['hops']} hops via {p['intermediaries']} intermediary accounts in "
                         f"{p['elapsed_seconds']} seconds (about {p['avg_delay_seconds']} s per hop), retaining {p['retention_percent']}% of value.")
        elif p["pattern"] == "smurfing":
            s = f"{p['unique_counterparties']} accounts that had not previously transacted with {p['hub_account']} sent {_inr(p['total_amount'])} in total within {round(p['span_seconds']/60)} minutes, with amounts between {_inr(p['min_amount'])} and {_inr(p['max_amount'])}."
            if p["forward_account"]:
                s += f" The collected funds were then forwarded to {p['forward_account']}."
            parts.append(s)
        else:
            parts.append(f"{p['hub_account']} sent similar amounts to {p['unique_counterparties']} accounts within {round(p['span_seconds']/60)} minutes.")
    if len(net["banks"]) > 1:
        parts.append(f"The network spans {len(net['banks'])} banks ({', '.join(net['banks'])}).")
    parts.append(f"Investigation priority is {net['risk']['score']}/100 ({net['risk']['level']}). "
                 "These indicators warrant human review; they do not establish criminal conduct.")
    return " ".join(parts)


def explain(net):
    text, source = template(net), "template"
    model = os.getenv("OLLAMA_MODEL")
    if model:
        try:
            body = json.dumps(dict(model=model, stream=False, prompt="Rewrite this for an investigator in plain, clear prose. "
                                   "Do not add, remove or change any account, amount, time or fact:\n" + text)).encode()
            req = urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"})
            out = json.loads(urllib.request.urlopen(req, timeout=20).read())["response"].strip()
            if out:
                text, source = out, "ollama"
        except Exception:
            pass  # deterministic fallback
    return dict(text=text, source=source)
