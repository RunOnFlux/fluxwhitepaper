#!/usr/bin/env python3
"""Measured network characteristics for the Flux whitepaper, from the live public API.

Inputs : evidence/measured/{listzelnodes,getzelnodecount,globalappsspecifications,deploymentinformation}.json
Outputs: evidence/_measured_network.md  and  paper/data/*.dat
Every figure the paper quotes from here carries its endpoint and retrieval date.
"""
import json, collections, statistics, pathlib, datetime

ROOT = pathlib.Path("/Users/tadeaskmenta/repos/fluxwhitepaper")
M = ROOT / "evidence" / "measured"
DAT = ROOT / "paper" / "data"
DAT.mkdir(parents=True, exist_ok=True)
STAMP = (M / "RETRIEVED_AT").read_text().strip()

def load(n):
    d = json.loads((M / n).read_text())
    return d.get("data", d) if isinstance(d, dict) else d

nodes = load("listzelnodes.json")
count = load("getzelnodecount.json")
apps  = load("globalappsspecifications.json")
depl  = load("deploymentinformation.json")

out = []
w = out.append
w(f"# Measured network characteristics  [measured {STAMP}]\n")
w("All figures below are computed from the live public API. Endpoints and retrieval date are")
w("given per table. Reproduce with `scripts/05-network-analysis.py`.\n")

# ---------------------------------------------------------------- fleet
w("## 1. Fleet census  `api.runonflux.io/daemon/getzelnodecount`\n")
w("| field | value |")
w("|---|---|")
for k, v in count.items():
    w(f"| `{k}` | {v} |")
w("")

TIER_COLLATERAL = {"CUMULUS": 1000, "NIMBUS": 12500, "STRATUS": 40000}
by_tier = collections.Counter(n["tier"] for n in nodes)
w(f"`listzelnodes` returned **{len(nodes)}** node records. Tier split from the records themselves:\n")
w("| tier | nodes | collateral each (FLUX) | tier collateral (FLUX) | vote weight (1/1000 FLUX) | share of voting power |")
w("|---|---|---|---|---|---|")
total_w = sum(TIER_COLLATERAL[n["tier"]] / 1000 for n in nodes)
for t in ("CUMULUS", "NIMBUS", "STRATUS"):
    c = by_tier[t]; coll = c * TIER_COLLATERAL[t]; wt = coll / 1000
    w(f"| {t.capitalize()} | {c} | {TIER_COLLATERAL[t]:,} | {coll:,} | {wt:,.1f} | {100*wt/total_w:.2f}% |")
w(f"| **total** | **{len(nodes)}** | | **{int(total_w*1000):,}** | **{total_w:,.1f}** | 100% |")
w("")

# ---------------------------------------------------------------- concentration
w("## 2. Operator concentration — the load-bearing measurement for the moderation design\n")
w("Voting weight is collateral-weighted at one unit per 1,000 FLUX. The moderation design assumes")
w("no single party can reach a removal threshold alone; that is an empirical claim about ownership")
w("concentration. Two proxies for operator identity are available in the public record:")
w("`payment_address` (where the node's rewards are sent) and `pubkey` (the node key). Neither is")
w("proof of common ownership — one operator may use many addresses, and a shared custodian may")
w("serve many operators — so both are reported and both are **lower bounds on concentration**.\n")

def concentration(keyfn, label, subset=None, fh=None):
    pool = subset if subset is not None else nodes
    agg = collections.Counter()
    for n in pool:
        agg[keyfn(n)] += TIER_COLLATERAL[n["tier"]] / 1000
    tot = sum(agg.values())
    ranked = sorted(agg.values(), reverse=True)
    lines = []
    lines.append(f"### {label}\n")
    lines.append(f"Distinct {label.split('by ')[-1]}: **{len(agg):,}** controlling **{tot:,.1f}** weight units "
                 f"({int(tot*1000):,} FLUX).\n")
    cum = 0.0; need = {}
    for i, v in enumerate(ranked, 1):
        cum += v
        for th in (0.10, 0.15, 0.25, 0.50):
            if th not in need and cum >= th * tot:
                need[th] = i
    lines.append("| threshold of total voting power | smallest number of identities that reach it | as % of identities |")
    lines.append("|---|---|---|")
    for th in (0.10, 0.15, 0.25, 0.50):
        k = need.get(th, len(ranked))
        lines.append(f"| {int(th*100)}% | **{k:,}** | {100*k/len(agg):.2f}% |")
    lines.append("")
    lines.append("| top-N identities | share of total voting power |")
    lines.append("|---|---|")
    for N in (1, 5, 10, 20, 50, 100, 250):
        if N <= len(ranked):
            lines.append(f"| {N} | {100*sum(ranked[:N])/tot:.2f}% |")
    # Gini
    s = sorted(agg.values()); n_ = len(s); cums = 0.0
    for i, v in enumerate(s, 1): cums += i * v
    gini = (2 * cums) / (n_ * sum(s)) - (n_ + 1) / n_
    lines.append("")
    lines.append(f"Gini coefficient of voting weight across {label.split('by ')[-1]}: **{gini:.4f}** "
                 f"(0 = perfectly equal, 1 = one identity holds everything).\n")
    top_id = max(agg, key=lambda k: agg[k])
    top_nodes = sum(1 for n in pool if keyfn(n) == top_id)
    lines.append(f"Largest single identity holds **{ranked[0]:,.1f}** weight units "
                 f"(**{100*ranked[0]/tot:.2f}%**) across **{top_nodes:,}** nodes; the most nodes held "
                 f"by any one identity is **{max(collections.Counter(keyfn(n) for n in pool).values()):,}**.\n")
    if fh is not None:
        with open(fh, "w") as f:
            f.write(f"# rank cumulative_share  ({label}) retrieved {STAMP}\n")
            c = 0.0
            for i, v in enumerate(ranked, 1):
                c += v
                f.write(f"{i} {c/tot:.6f}\n")
    return lines, need, len(agg)

l1, need_addr, n_addr = concentration(lambda n: n["payment_address"], "by `payment_address`",
                                      fh=DAT / "concentration_payment_address.dat")
out.extend(l1)
l2, need_pk, n_pk = concentration(lambda n: n["pubkey"], "by `pubkey`",
                                  fh=DAT / "concentration_pubkey.dat")
out.extend(l2)

strat = [n for n in nodes if n["tier"] == "STRATUS"]
l3, need_s, n_s = concentration(lambda n: n["payment_address"], "by `payment_address`, Stratus only", subset=strat)
out.extend(l3)

w("### Reading of the concentration result\n")
w(f"A 25% removal threshold is reached by the **{need_addr[0.25]:,}** largest payment addresses "
  f"(of {n_addr:,}), or by the **{need_pk[0.25]:,}** largest node keys (of {n_pk:,}). "
  "Both are lower bounds: they assume every address is a distinct operator.\n")

# ---------------------------------------------------------------- rotation
w("## 3. PoN payment rotation, measured\n")
tip = max(n["last_confirmed_height"] for n in nodes)
w(f"Chain tip observed in the node records: height **{tip:,}**. For each node, "
  "`tip - last_paid_height` is the number of blocks since it was last paid; under a deterministic "
  "one-node-per-tier-per-block rotation this should be bounded by the tier's node count.\n")
w("| tier | nodes | expected rotation (blocks) | max blocks since paid | median | 95th pct | rotation at 30 s |")
w("|---|---|---|---|---|---|---|")
rot_rows = []
for t in ("CUMULUS", "NIMBUS", "STRATUS"):
    g = [tip - n["last_paid_height"] for n in nodes if n["tier"] == t and n["last_paid_height"] > 0]
    g.sort()
    if not g: continue
    p95 = g[int(0.95 * (len(g) - 1))]
    hrs = by_tier[t] * 30 / 3600
    w(f"| {t.capitalize()} | {by_tier[t]:,} | {by_tier[t]:,} | {max(g):,} | {statistics.median(g):,.0f} | {p95:,} | {hrs:.2f} h |")
    rot_rows.append((t, by_tier[t], max(g), statistics.median(g), p95, hrs))
w("")
with open(DAT / "rotation.dat", "w") as f:
    f.write(f"# tier nodes expected_rotation max_since_paid median_since_paid p95_since_paid rotation_hours  retrieved {STAMP}\n")
    for r in rot_rows:
        f.write(f"{r[0]} {r[1]} {r[2]} {r[3]:.0f} {r[4]} {r[5]:.3f}\n")

# tenure
w("## 4. Node tenure\n")
ten = sorted(tip - n["added_height"] for n in nodes)
w(f"Blocks since `added_height`, across all {len(ten):,} nodes: median **{statistics.median(ten):,.0f}** "
  f"(~{statistics.median(ten)*30/86400:,.0f} days at 30 s), "
  f"10th pct {ten[len(ten)//10]:,}, 90th pct {ten[9*len(ten)//10]:,}, max {ten[-1]:,}.\n")

# ---------------------------------------------------------------- apps
w("## 5. Deployed applications  `api.runonflux.io/apps/globalappsspecifications`\n")
w(f"Records returned: **{len(apps):,}**.\n")
vers = collections.Counter(a.get("version") for a in apps)
w("| application specification version | applications | share |")
w("|---|---|---|")
for v, c in sorted(vers.items(), key=lambda kv: (kv[0] is None, kv[0])):
    w(f"| v{v} | {c:,} | {100*c/len(apps):.1f}% |")
w("")
with open(DAT / "appspec_versions.dat", "w") as f:
    f.write(f"# version count share  retrieved {STAMP}\n")
    for v, c in sorted(vers.items(), key=lambda kv: (kv[0] is None, kv[0])):
        f.write(f"{v} {c} {c/len(apps):.6f}\n")

def comps(a):
    return a.get("compose") or [a]

inst = sum(int(a.get("instances", 0) or 0) for a in apps)
cpu = ram = hdd = 0.0
ncomp = 0
for a in apps:
    k = int(a.get("instances", 0) or 0)
    for c in comps(a):
        ncomp += 1
        cpu += float(c.get("cpu", 0) or 0) * k
        ram += float(c.get("ram", 0) or 0) * k
        hdd += float(c.get("hdd", 0) or 0) * k
w(f"Total requested instances across all applications: **{inst:,}**. "
  f"Components (compose entries): **{ncomp:,}**.\n")
w("| resource, summed over all instances | value |")
w("|---|---|")
w(f"| CPU (vCPU-equivalents as specified) | {cpu:,.1f} |")
w(f"| RAM | {ram:,.0f} MB ({ram/1024:,.1f} GiB) |")
w(f"| HDD | {hdd:,.0f} GB |")
w("")

sizes = sorted(int(a.get("instances", 0) or 0) for a in apps)
w(f"Instances per application: median **{statistics.median(sizes):.0f}**, "
  f"mean {statistics.mean(sizes):.2f}, max {max(sizes)}, "
  f"min {min(sizes)}. Applications at the 3-instance minimum: "
  f"**{sum(1 for s in sizes if s == 3):,}** ({100*sum(1 for s in sizes if s==3)/len(sizes):.1f}%).\n")

# geolocation / staticip / enterprise usage
def has(a, f):
    v = a.get(f)
    return bool(v) and v != [] and v != ""
for field in ("geolocation", "staticip", "nodes", "enterprise", "expire", "owner", "contacts"):
    k = sum(1 for a in apps if has(a, field))
    if k:
        w(f"- applications using `{field}`: **{k:,}** ({100*k/len(apps):.1f}%)")
w("")

# registries
regs = collections.Counter()
for a in apps:
    for c in comps(a):
        img = str(c.get("repotag", ""))
        regs[img.split("/")[0] if "/" in img and ("." in img.split("/")[0] or ":" in img.split("/")[0]) else "docker.io (implicit)"] += 1
w("| image registry | components |")
w("|---|---|")
for r, c in regs.most_common(12):
    w(f"| `{r}` | {c:,} |")
w("")

# ---------------------------------------------------------------- pricing
w("## 6. Deployment pricing table  `api.runonflux.io/apps/deploymentinformation`\n")
w("```json")
w(json.dumps(depl, indent=1)[:3000])
w("```")
w("")

(ROOT / "evidence" / "_measured_network.md").write_text("\n".join(out) + "\n")
print("wrote evidence/_measured_network.md", len(out), "lines")
print("dat files:", sorted(p.name for p in DAT.glob("*.dat")))
