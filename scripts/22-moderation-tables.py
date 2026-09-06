#!/usr/bin/env python3
"""Reproduce the measured tables of paper/sections/23-governance.tex (the moderation quorum).

Written fresh for round 18, item 20 (G21): the scratch scripts that produced these tables
(`mod.py`, `tenure.py`) were never committed. Every figure the section prints from the
2026-09-03 `listzelnodes` snapshot is recomputed here from the retained input and compared
against the printed value, so a table either reproduces or is marked `\\notestablished`.

Input : evidence/measured/listzelnodes.json   (api.runonflux.io/daemon/listzelnodes, 2026-09-03)
Output: stdout — one line per printed figure, `ok` or `MISMATCH`, exit 1 on any mismatch.

Definitions (as the section states them):
  weight      collateral / 1000 per node (Cumulus 1, Nimbus 12.5, Stratus 40)
  owner id    payment_address           node key   pubkey
  tip         max(last_confirmed_height) over the records = 2,917,115
  tenure      tip - added_height
  kappa(v)    least number of identities, taken largest-first, whose weight reaches v * total
  cluster     union of payment_addresses joined by a shared pubkey or a shared collateral txhash
  Gini        over per-identity weights (the same formula as scripts/05-network-analysis.py)
  tenure tab  the last column is the weight of the three largest keys *among nodes with tenure >= T*,
              as a share of all weight (not the global top three restricted to tenured nodes)
  33.3% row   the section evaluates it at v = 0.333 exactly, not at 1/3
"""
import collections, json, math, pathlib, statistics, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
nodes = json.loads((ROOT / "evidence/measured/listzelnodes.json").read_text())["data"]

TIER_W = {"CUMULUS": 1.0, "NIMBUS": 12.5, "STRATUS": 40.0}
TIER_BASE = {"CUMULUS": 1.0, "NIMBUS": 3.5, "STRATUS": 9.0}
tip = max(n["last_confirmed_height"] for n in nodes)

fails = 0
def check(label, got, printed, tol=0.0, fmt="{:,.4f}"):
    global fails
    ok = abs(got - printed) <= tol
    if not ok:
        fails += 1
    print(f"{'ok      ' if ok else 'MISMATCH'} {label:<70} computed {fmt.format(got):>14}  printed {fmt.format(printed):>14}")

def gini(ws):
    s = sorted(ws); n = len(s)
    cums = sum((i + 1) * x for i, x in enumerate(s))
    return (2 * cums) / (n * sum(s)) - (n + 1) / n

def agg(keyfn, wfn, subset=None):
    a = collections.defaultdict(float)
    for n in (subset or nodes):
        a[keyfn(n)] += wfn(n)
    return a

def kappa(weights, v):
    tot = sum(weights); need = v * tot; acc = 0.0
    for k, w in enumerate(sorted(weights, reverse=True), 1):
        acc += w
        if acc >= need - 1e-9:
            return k
    return None

W = sum(TIER_W[n["tier"]] for n in nodes)
by_addr = agg(lambda n: n["payment_address"], lambda n: TIER_W[n["tier"]])
by_key  = agg(lambda n: n["pubkey"],          lambda n: TIER_W[n["tier"]])
cnt_addr = collections.Counter(n["payment_address"] for n in nodes)
cnt_key  = collections.Counter(n["pubkey"] for n in nodes)

print(f"records {len(nodes)}  tip {tip}  total weight {W:,.1f} units  "
      f"owner identities {len(by_addr)}  node keys {len(by_key)}\n")

# ---- §23 electorate: tier shares (:350), 25% threshold (:1274)
print("## Electorate")
for t, printed in (("CUMULUS", 3.67), ("NIMBUS", 22.81), ("STRATUS", 73.52)):
    check(f"tier share {t} (%)", 100 * sum(TIER_W[n['tier']] for n in nodes if n['tier'] == t) / W, printed, 0.005, "{:.2f}")
check("25% threshold (FLUX)", 0.25 * W * 1000, 22128625, 0.5, "{:,.0f}")
check("Nimbus nodes needed for 25%", math.ceil(0.25 * W / 12.5), 1771, 0, "{:,.0f}")
check("owner identities (869)", len(by_addr), 869, 0, "{:,.0f}")
check("node keys (819)", len(by_key), 819, 0, "{:,.0f}")
check("largest node key, nodes (:499)", max(cnt_key.values()), 480, 0, "{:,.0f}")
check("largest owner identity, nodes (:500)", max(cnt_addr.values()), 479, 0, "{:,.0f}")
check("largest node key share of capacity (%)", 100 * max(cnt_key.values()) / len(nodes), 7.40, 0.005, "{:.2f}")
check("Gini of node counts by key (:500)", gini(cnt_key.values()), 0.716, 0.0005, "{:.3f}")

# ---- turnout table (:1015-1017): abstaining prefix by node key
print("\n## Turnout by abstaining prefix (tab at :1008)")
ks = sorted(by_key.values(), reverse=True)
for m, rem_pct, rem_units, share in ((3, 74.9, 66314.5, 33.4), (16, 49.9, 44193.0, 50.1)):
    rem = W - sum(ks[:m])
    check(f"{m} largest keys abstain: remaining (units)", rem, rem_units, 0.05, "{:,.1f}")
    check(f"{m} largest keys abstain: remaining (%)", 100 * rem / W, rem_pct, 0.05, "{:.1f}")
    check(f"{m} largest keys abstain: share of remainder (%)", 100 * 0.25 * W / rem, share, 0.05, "{:.1f}")

# ---- kappa table (:1117-1129)
print("\n## kappa(v) table (:1112)")
kt = {0.10: (8851.5, 1, 1, 222, 13.6), 0.15: (13277.2, 2, 2, 332, 20.4), 0.20: (17702.9, 3, 2, 443, 27.2),
      0.25: (22128.6, 4, 3, 554, 34.1), 0.30: (26554.4, 6, 5, 664, 40.8), 0.333: (29475.3, 8, 6, 737, 45.3),
      0.40: (35405.8, 12, 10, 886, 54.5), 0.50: (44257.3, 19, 16, 1107, 68.0), 0.51: (45142.4, 20, 17, 1129, 69.4)}
n_strat = sum(1 for n in nodes if n["tier"] == "STRATUS")
for v, (need, ko, kk, sn, ss) in kt.items():
    # 0.30 and 0.50 land on an exact .x5 (26,554.35 / 44,257.25); the table rounds half up, float does not
    check(f"v={v:.3f} required weight", v * W, need, 0.06, "{:,.1f}")
    check(f"v={v:.3f} kappa owner", kappa(by_addr.values(), v), ko, 0, "{:.0f}")
    check(f"v={v:.3f} kappa node key", kappa(by_key.values(), v), kk, 0, "{:.0f}")
    check(f"v={v:.3f} Stratus nodes alone", math.ceil(v * W / 40), sn, 0, "{:.0f}")
    check(f"v={v:.3f} of Stratus set (%)", 100 * math.ceil(v * W / 40) / n_strat, ss, 0.05, "{:.1f}")

# ---- linked clusters (:1138-1139): union-find over addresses by shared pubkey / shared txhash
print("\n## Linked clusters (caption :1137-1140)")
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb
for a in by_addr: find(a)
for link in ("pubkey", "txhash"):
    first = {}
    for n in nodes:
        k = n[link]
        if k in first: union(first[k], n["payment_address"])
        else: first[k] = n["payment_address"]
cl = collections.defaultdict(float)
for a, w in by_addr.items(): cl[find(a)] += w
check("clusters (797)", len(cl), 797, 0, "{:.0f}")
for v, printed in ((0.10, 1), (0.15, 2), (0.25, 3), (0.50, 16)):
    check(f"cluster kappa at {v:.2f}", kappa(cl.values(), v), printed, 0, "{:.0f}")

# ---- prose (:1145-1158)
print("\n## Prose after the kappa table (:1145-1158)")
top_addr = max(by_addr.items(), key=lambda kv: kv[1])
check("largest identity share (%)", 100 * top_addr[1] / W, 10.71, 0.005, "{:.2f}")
check("largest identity Stratus nodes (237)", sum(1 for n in nodes if n["payment_address"] == top_addr[0] and n["tier"] == "STRATUS"), 237, 0, "{:.0f}")
top3 = sorted(by_key.items(), key=lambda kv: -kv[1])[:3]
for (k, w), (pu, pn, pp) in zip(top3, ((9480, 237, 10.71), (9360, 234, 10.57), (3360, 84, 3.80))):
    check(f"top key units ({pu})", w, pu, 0.05, "{:,.0f}")
    check(f"top key nodes ({pn})", cnt_key[k], pn, 0, "{:.0f}")
    check(f"top key share ({pp}%)", 100 * w / W, pp, 0.005, "{:.2f}")
check("top-3 keys sum (%)", 100 * sum(w for _, w in top3) / W, 25.08, 0.005, "{:.2f}")
check("top-3 keys collateral (FLUX)", 1000 * sum(w for _, w in top3), 22200000, 0.5, "{:,.0f}")
check("Gini by payment address", gini(by_addr.values()), 0.8375, 0.00005, "{:.4f}")  # 0.837493; the paper printed 0.838 before round 18
check("Gini by node key", gini(by_key.values()), 0.839, 0.0005, "{:.3f}")
key_addrs = collections.defaultdict(set); addr_keys = collections.defaultdict(set); tx_addrs = collections.defaultdict(set)
for n in nodes:
    key_addrs[n["pubkey"]].add(n["payment_address"]); addr_keys[n["payment_address"]].add(n["pubkey"]); tx_addrs[n["txhash"]].add(n["payment_address"])
check("keys paying to >1 address (47)", sum(1 for s in key_addrs.values() if len(s) > 1), 47, 0, "{:.0f}")
check("addresses receiving from >1 key (5)", sum(1 for s in addr_keys.values() if len(s) > 1), 5, 0, "{:.0f}")
check("funding txs paying >1 address (0)", sum(1 for s in tx_addrs.values() if len(s) > 1), 0, 0, "{:.0f}")
check("distinct funding txs (6178)", len(tx_addrs), 6178, 0, "{:.0f}")
big = [k for k, c in cnt_key.items() if c >= 10]
check("keys with >=10 nodes (107)", len(big), 107, 0, "{:.0f}")
check("their share of weight (72.5%)", 100 * sum(by_key[k] for k in big) / W, 72.5, 0.05, "{:.1f}")
check("keys with exactly one node (334)", sum(1 for c in cnt_key.values() if c == 1), 334, 0, "{:.0f}")
check("sqrt(9480)", math.sqrt(9480), 97.4, 0.05, "{:.1f}")
check("237*sqrt(40)", 237 * math.sqrt(40), 1498.9, 0.05, "{:.1f}")

# ---- Sybil-neutral reweightings (:1290-1297), node-key model
print("\n## Sybil-neutral reweightings (tab at :1282), node-key model")
rows = {
    "collateral":  (lambda n: TIER_W[n["tier"]],               (73.5, 10.71, 25.08, 3, 17, 0.839, 22128625)),
    "tier base":   (lambda n: TIER_BASE[n["tier"]],            (62.2,  9.06, 21.23, 5, 22, 0.793, None)),
    "sqrt":        (lambda n: math.sqrt(TIER_W[n["tier"]]),    (53.5,  7.79, 18.31, 6, 26, 0.770, None)),
    "one node":    (lambda n: 1.0,                             (25.1,  7.40, 17.58, 6, 38, 0.716, 1623000)),
}
for name, (wfn, (ps, ptop, ptop3, pk25, pk51, pg, pcost)) in rows.items():
    bk = agg(lambda n: n["pubkey"], wfn); tot = sum(bk.values())
    srt = sorted(bk.values(), reverse=True)
    check(f"{name}: Stratus share (%)", 100 * sum(wfn(n) for n in nodes if n["tier"] == "STRATUS") / tot, ps, 0.05, "{:.1f}")
    check(f"{name}: top key (%)", 100 * srt[0] / tot, ptop, 0.005, "{:.2f}")
    check(f"{name}: top 3 (%)", 100 * sum(srt[:3]) / tot, ptop3, 0.005, "{:.2f}")
    check(f"{name}: kappa(0.25)", kappa(srt, 0.25), pk25, 0, "{:.0f}")
    check(f"{name}: kappa(0.51)", kappa(srt, 0.51), pk51, 0, "{:.0f}")
    check(f"{name}: Gini", gini(srt), pg, 0.0005, "{:.3f}")
    if pcost is not None:
        # capital to buy 25% outright with Cumulus nodes: x nodes such that x*w_c >= 0.25*(tot + x*w_c)? The
        # section's figures are 25% of the *current* total (22,128,625 = 0.25*W*1000; 1,623,000 = ceil(0.25*6489)*1000).
        cost = math.ceil(0.25 * tot / wfn({"tier": "CUMULUS"})) * 1000 if name == "one node" else 0.25 * tot * 1000
        check(f"{name}: cost of 25% (FLUX)", cost, pcost, 0.5, "{:,.0f}")

# ---- tenure table (:1583-1586) and participation (:1608-1609)
print("\n## Tenure (tab at :1576) and second-chamber participation (:1607-1609)")
tt = {20160: (5639, 86.9, 744, 90.1, 24.05), 86400: (4149, 63.9, 607, 77.0, 23.95),
      259200: (2824, 43.5, 412, 57.2, 19.66), 518400: (1516, 23.4, 286, 31.5, 9.49)}
keys_at = {}
for T, (pn, ppct, pkeys, pw, ptop3) in tt.items():
    sel = [n for n in nodes if tip - n["added_height"] >= T]
    keys_at[T] = len({n["pubkey"] for n in sel})
    tw = sum(TIER_W[n["tier"]] for n in sel)
    bk_t = agg(lambda n: n["pubkey"], lambda n: TIER_W[n["tier"]], subset=sel)
    check(f"T={T}: nodes", len(sel), pn, 0, "{:.0f}")
    check(f"T={T}: nodes (%)", 100 * len(sel) / len(nodes), ppct, 0.05, "{:.1f}")
    check(f"T={T}: distinct keys", keys_at[T], pkeys, 0, "{:.0f}")
    check(f"T={T}: tenured weight (%)", 100 * tw / W, pw, 0.05, "{:.1f}")
    check(f"T={T}: top-3 tenured keys' weight (% of all)", 100 * sum(sorted(bk_t.values(), reverse=True)[:3]) / W, ptop3, 0.005, "{:.2f}")
check("median tenure (blocks)", statistics.median(tip - n["added_height"] for n in nodes), 193620, 0, "{:,.0f}")
for m, T, printed in ((50, 86400, 8.2), (50, 259200, 12.1), (21, 86400, 3.5), (21, 259200, 5.1), (100, 86400, 16.5)):
    check(f"m={m}, T={T}: share of eligible keys (%)", 100 * m / keys_at[T], printed, 0.05, "{:.1f}")
for m, printed_cost, printed_pct, tol in ((100, 96000, 0.43, 0.005), (21, 17000, 0.077, 0.0005)):
    check(f"m={m}: collateral route (FLUX)", (m - 4) * 1000, printed_cost, 0, "{:,.0f}")
    check(f"m={m}: as % of 22,100,000", 100 * (m - 4) * 1000 / 22_100_000, printed_pct, tol, "{:.3f}")

print(f"\n{'ALL FIGURES REPRODUCE' if fails == 0 else f'{fails} MISMATCH(ES)'}")
sys.exit(1 if fails else 0)
