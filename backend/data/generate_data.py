"""TRACEFLOW synthetic data generator.

Writes transactions.csv, accounts.csv and ground_truth.json next to this file.
Deterministic for a given --seed. No real data is used.

Planted suspicious networks (23): circular 5, mule chain 8, smurfing 7, mixed 3.
Planted benign high-volume networks (4): payroll, merchant, e-commerce hub, supplier payer.
"""
import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BANKS = ["BANK_A", "BANK_B", "BANK_C", "BANK_D", "BANK_E"]
CITIES = ["Chennai", "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Kolkata",
          "Pune", "Ahmedabad", "Kochi", "Jaipur"]
START = datetime(2026, 7, 1)
END = datetime(2026, 10, 3, 23, 59, 59)
HOUR_W = np.array([1, 1, 1, 1, 1, 2, 3, 5, 8, 10, 11, 11, 10, 10, 10, 10, 10, 9, 8, 7, 5, 3, 2, 1], float)
HOUR_W /= HOUR_W.sum()
P2P_TYPES = ["UPI", "IMPS", "NEFT", "TRANSFER"]
LAUNDER_TYPES = ["TRANSFER", "NEFT", "IMPS"]


def ids(lo, hi):
    return [f"A{i}" for i in range(lo, hi + 1)]


# Business account ranges (planted suspicious accounts live in A100-A999)
EMPLOYERS, MERCHANTS = ids(1001, 1010), ids(1011, 1040)
COMPANIES, SUPPLIERS, HUBS = ids(1041, 1055), ids(1056, 1085), ids(1086, 1087)


class Generator:
    def __init__(self, seed, n_accounts, target_tx):
        assert n_accounts >= 1100, "need at least 1100 accounts"
        self.rng, self.np = random.Random(seed), np.random.default_rng(seed)
        self.target = target_tx
        self.accounts = ids(1, n_accounts)
        self.bank = {a: self.rng.choice(BANKS) for a in self.accounts}
        self.city = {a: self.rng.choice(CITIES) for a in self.accounts}
        self.atype = {a: "personal" for a in self.accounts}
        for group, name in [(EMPLOYERS, "employer"), (MERCHANTS, "merchant"), (COMPANIES, "company"),
                            (SUPPLIERS, "supplier"), (HUBS, "ecommerce_hub")]:
            for a in group:
                self.atype[a] = name
        biz = set(EMPLOYERS + MERCHANTS + COMPANIES + SUPPLIERS + HUBS)
        self.personal = [a for a in self.accounts if a not in biz]
        self.rows, self.meta, self.used = [], {}, set()

    # ---------- helpers ----------
    def ts(self):
        while True:
            t = START + timedelta(days=self.rng.randrange((END - START).days + 1),
                                  hours=int(self.np.choice(24, p=HOUR_W)),
                                  minutes=self.rng.randrange(60), seconds=self.rng.randrange(60))
            if t <= END:
                return t

    def add(self, t, s, r, amt, typ, tag=None):
        self.rows.append(dict(
            timestamp=t.isoformat(timespec="seconds"), sender_account=s, receiver_account=r,
            sender_bank=self.bank[s], receiver_bank=self.bank[r], amount=int(round(amt)),
            transaction_type=typ, location=self.city[s], _tag=tag))

    def amount(self, median, sigma, lo, hi, step=10):
        v = float(np.clip(self.np.lognormal(np.log(median), sigma), lo, hi))
        return round(v / step) * step

    def set_banks(self, accts, cross):
        if cross:
            off = self.rng.randrange(5)
            for i, a in enumerate(accts):
                self.bank[a] = BANKS[(off + i) % 5]
        else:
            b = self.rng.choice(BANKS)
            for a in accts:
                self.bank[a] = b

    def register(self, net, typ, label, accts, patterns, scenario=None):
        self.used.update(accts)
        self.meta[net] = dict(type=typ, label=label, suspicious=True, accounts=accts,
                              expected_patterns=patterns, demo_scenario=scenario)

    def late_start(self):
        return min(self.ts(), END - timedelta(hours=6))

    # ---------- planted suspicious patterns ----------
    def plant_cycle(self, net, accts, start, amounts=None, offsets=None):
        n = len(accts)
        if offsets is None:
            total = self.rng.randint(60, 600)
            offsets = sorted([0] + [self.rng.randint(1, total) for _ in range(n - 1)])
        if amounts is None:
            amounts = [self.rng.randrange(300000, 1500000, 10000)]
            for _ in range(n - 1):
                amounts.append(amounts[-1] * self.rng.uniform(0.95, 0.99))
        for i in range(n):
            self.add(start + timedelta(seconds=offsets[i]), accts[i], accts[(i + 1) % n],
                     amounts[i], self.rng.choice(LAUNDER_TYPES), net)
        return offsets[-1]

    def plant_chain(self, net, accts, start, init=None):
        t, amt = start, init or self.rng.randrange(200000, 1200000, 10000)
        for i in range(len(accts) - 1):
            self.add(t, accts[i], accts[i + 1], amt, self.rng.choice(LAUNDER_TYPES), net)
            amt *= self.rng.uniform(0.96, 0.99)
            t += timedelta(seconds=self.rng.randint(15, 150))

    def plant_smurf(self, net, senders, dest, start, forward=None):
        window, total = self.rng.randint(90, 180) * 60, 0
        for s in senders:
            amt = self.rng.randrange(40000, 49900, 100)  # just under a 50k reporting threshold
            total += amt
            self.add(start + timedelta(seconds=self.rng.randint(0, window)), s, dest, amt,
                     self.rng.choice(["UPI", "IMPS", "TRANSFER"]), net)
        if forward:
            self.add(start + timedelta(seconds=window + self.rng.randint(600, 1800)),
                     dest, forward, total * 0.97, "RTGS", net)

    def plant_all(self):
        # Named scenarios (ids match the product spec)
        c1 = ["A101", "A205", "A310", "A412"]
        self.register("network_001", "circular", "Circular laundering route", c1, ["circular_flow"], 1)
        self.set_banks(c1, True)
        self.plant_cycle("network_001", c1, datetime(2026, 10, 3, 10, 1, 14),
                         amounts=[980000, 950000, 920000, 890000], offsets=[0, 31, 62, 94])

        m1 = ids(501, 505)
        self.register("network_002", "mule_chain", "Rapid mule chain", m1, ["mule_chain"], 2)
        self.set_banks(m1, True)
        self.plant_chain("network_002", m1, self.late_start(), 750000)

        s1 = ids(601, 608) + ["A700"]
        self.register("network_003", "smurfing", "Smurfing ring", s1, ["smurfing"], 3)
        self.set_banks(s1, True)
        self.plant_smurf("network_003", s1[:-1], "A700", self.late_start())

        c2 = ["A111", "A222", "A333", "A444", "A555", "A666"]
        self.register("network_004", "circular", "Six-account cross-bank cycle", c2, ["circular_flow"])
        self.set_banks(c2, True)
        self.plant_cycle("network_004", c2, self.late_start())

        m2 = ids(521, 526)
        self.register("network_005", "mule_chain", "Five-hop mule chain", m2, ["mule_chain"])
        self.set_banks(m2, True)
        self.plant_chain("network_005", m2, self.late_start())

        s2 = ids(711, 716) + ["A720", "A721"]
        self.register("network_006", "smurfing", "Smurfing ring with onward forward", s2,
                      ["smurfing"])
        self.set_banks(s2, True)
        self.plant_smurf("network_006", s2[:6], "A720", self.late_start(), forward="A721")

        cyc, tail = ["A801", "A802", "A803", "A804"], ids(805, 807)
        self.register("network_007", "mixed", "Mixed circular + mule network", cyc + tail,
                      ["circular_flow", "mule_chain"], 5)
        self.set_banks(cyc + tail, True)
        start = self.late_start()
        end_off = self.plant_cycle("network_007", cyc, start)
        self.plant_chain("network_007", [cyc[0]] + tail,
                         start + timedelta(seconds=end_off + self.rng.randint(30, 120)))

        # Extra planted networks: reach 23 total
        pool = [a for a in ids(100, 999) if a not in self.used]
        self.rng.shuffle(pool)
        take = lambda k: [pool.pop() for _ in range(k)]
        specs = [("circular", 3), ("mule_chain", 6), ("smurfing", 5), ("mixed", 2)]
        k = 8
        for typ, count in specs:
            for _ in range(count):
                net, cross = f"network_{k:03d}", self.rng.random() < 0.8
                k += 1
                if typ == "circular":
                    a = take(self.rng.randint(3, 6))
                    self.register(net, typ, "Circular flow", a, ["circular_flow"])
                    self.set_banks(a, cross)
                    self.plant_cycle(net, a, self.late_start())
                elif typ == "mule_chain":
                    a = take(self.rng.randint(4, 7))
                    self.register(net, typ, "Rapid mule chain", a, ["mule_chain"])
                    self.set_banks(a, cross)
                    self.plant_chain(net, a, self.late_start())
                elif typ == "smurfing":
                    a = take(self.rng.randint(6, 13))
                    self.register(net, typ, "Smurfing ring", a, ["smurfing"])
                    self.set_banks(a, cross)
                    self.plant_smurf(net, a[:-1], a[-1], self.late_start())
                else:
                    a = take(self.rng.randint(3, 4) + 3)
                    cyc_n = len(a) - 3
                    self.register(net, typ, "Mixed circular + mule network", a,
                                  ["circular_flow", "mule_chain"])
                    self.set_banks(a, True)
                    st = self.late_start()
                    off = self.plant_cycle(net, a[:cyc_n], st)
                    self.plant_chain(net, [a[0]] + a[cyc_n:], st + timedelta(seconds=off + 60))

    # ---------- legitimate background ----------
    def background(self):
        rng = self.rng
        # Payroll: fixed salary on the 1st of each month
        for e in EMPLOYERS:
            staff = rng.sample(self.personal, rng.randint(15, 40))
            for emp in staff:
                sal = rng.randrange(30000, 120000, 500)
                for m in [(2026, 7), (2026, 8), (2026, 9), (2026, 10)]:
                    self.add(datetime(m[0], m[1], 1, 9, rng.randrange(30), rng.randrange(60)),
                             e, emp, sal, "SALARY")
        # Merchants: many customers, repeat purchases, small amounts (heavy-tailed)
        weights = self.np.lognormal(0, 0.8, len(MERCHANTS))
        weights[0] *= 4  # A1011 is deliberately very busy
        counts = (weights / weights.sum() * 6500).astype(int)
        for m, c in zip(MERCHANTS, counts):
            pool = rng.sample(self.personal, rng.randint(40, 150))
            w = 1.0 / (np.arange(len(pool)) + 3)  # repeat customers dominate
            for cust in self.np.choice(pool, size=int(c), p=w / w.sum()):
                self.add(self.ts(), cust, m, self.amount(900, 0.8, 50, 20000), rng.choice(["UPI", "PAYMENT"]))
        # Companies pay a stable set of suppliers every week, near-regular amounts
        for comp in COMPANIES:
            for sup in rng.sample(SUPPLIERS, rng.randint(5, 8)):
                base = rng.randrange(50000, 400000, 5000)
                for w in range(14):
                    t = START + timedelta(days=7 * w, hours=11, minutes=rng.randint(-20, 20))
                    if t <= END:
                        self.add(t, comp, sup, base * rng.uniform(0.98, 1.02), "NEFT")
        # E-commerce hubs: huge fan-in, small refund fan-out, regular supplier payouts
        for hub, n_in in zip(HUBS, [1100, 600]):
            pool = rng.sample(self.personal, 250)
            w = 1.0 / (np.arange(len(pool)) + 5)
            for cust in self.np.choice(pool, size=n_in, p=w / w.sum()):
                self.add(self.ts(), cust, hub, self.amount(1500, 0.9, 100, 60000), "PAYMENT")
            for _ in range(n_in // 12):
                self.add(self.ts(), hub, rng.choice(pool), self.amount(900, 0.6, 100, 20000), "UPI")
            for sup in rng.sample(SUPPLIERS, 8):
                base = rng.randrange(80000, 300000, 5000)
                for wk in range(14):
                    t = START + timedelta(days=7 * wk + 1, hours=10, minutes=rng.randint(-10, 10))
                    if t <= END:
                        self.add(t, hub, sup, base * rng.uniform(0.98, 1.02), "RTGS")
        # Everyday P2P between personal accounts (stable friend lists)
        friends = {a: rng.sample([x for x in self.personal if x != a], rng.randint(3, 8))
                   for a in self.personal}
        while len(self.rows) < self.target:
            s = rng.choice(self.personal)
            r = rng.choice(friends[s]) if rng.random() < 0.8 else rng.choice(self.personal)
            if s != r:
                self.add(self.ts(), s, r, self.amount(2500, 1.0, 100, 60000), rng.choice(P2P_TYPES))

    # ---------- output ----------
    def finalize(self, out: Path):
        df = pd.DataFrame(self.rows).sort_values("timestamp", kind="stable").reset_index(drop=True)
        df.insert(0, "transaction_id", [f"TX{i + 1:05d}" for i in range(len(df))])

        benign = [("benign_001", "A1001", "payroll", "Payroll: fixed monthly salaries to stable employees"),
                  ("benign_002", "A1011", "merchant", "Busy merchant: many repeat customers, small amounts"),
                  ("benign_003", "A1086", "ecommerce_hub", "E-commerce hub: broad customers + regular supplier payouts"),
                  ("benign_004", "A1041", "supplier_payer", "Company paying stable suppliers on a weekly schedule")]
        for net, center, sub, label in benign:
            mask = df._tag.isna() & ((df.sender_account == center) | (df.receiver_account == center))
            df.loc[mask, "_tag"] = net
            self.meta[net] = dict(type="benign_commerce", subtype=sub, label=label, suspicious=False,
                                  accounts=[center], expected_patterns=[],
                                  demo_scenario=4 if sub == "ecommerce_hub" else None)

        truth = {}
        for net, m in self.meta.items():
            sub = df[df._tag == net]
            banks = sorted(set(sub.sender_bank) | set(sub.receiver_bank))
            t0, t1 = pd.to_datetime(sub.timestamp.min()), pd.to_datetime(sub.timestamp.max())
            cps = set(sub.sender_account) | set(sub.receiver_account)
            entry = dict(m, transaction_ids=sub.transaction_id.tolist(), banks=banks,
                         cross_bank=len(banks) > 1, total_amount=int(sub.amount.sum()),
                         start=sub.timestamp.min(), end=sub.timestamp.max(),
                         elapsed_seconds=int((t1 - t0).total_seconds()))
            if not m["suspicious"]:
                entry["counterparty_count"] = len(cps) - 1
                entry["transaction_count"] = len(sub)
            truth[net] = entry

        df = df.drop(columns="_tag")
        out.mkdir(parents=True, exist_ok=True)
        df.to_csv(out / "transactions.csv", index=False)
        rng = random.Random(7)
        acc = pd.DataFrame(dict(
            account_id=self.accounts, bank=[self.bank[a] for a in self.accounts],
            account_type=[self.atype[a] for a in self.accounts],
            city=[self.city[a] for a in self.accounts],
            opened_date=[(datetime(2008, 1, 1) + timedelta(days=rng.randrange(6000))).date().isoformat()
                         for _ in self.accounts]))
        acc.to_csv(out / "accounts.csv", index=False)
        (out / "ground_truth.json").write_text(json.dumps(truth, indent=2))
        return df, acc, truth


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--accounts", type=int, default=2000)
    p.add_argument("--transactions", type=int, default=20400)
    p.add_argument("--out", type=Path, default=Path(__file__).parent)
    a = p.parse_args()
    g = Generator(a.seed, a.accounts, a.transactions)
    g.plant_all()
    g.background()
    df, acc, truth = g.finalize(a.out)
    sus = [v for v in truth.values() if v["suspicious"]]
    print(f"transactions={len(df)} accounts={len(acc)} banks={df.sender_bank.nunique()}")
    print(f"suspicious networks={len(sus)} benign networks={len(truth) - len(sus)}")
    print(f"written to {a.out}")


if __name__ == "__main__":
    main()
