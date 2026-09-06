#!/usr/bin/env python3
"""Computations for plan/mech-private-renewal.md (§21, private payment with public obligation).

Inputs (all measured, retrieved 2026-09-03T01:32:00Z):
  evidence/measured/globalappsspecifications.json  (1,195 deployed applications)
  evidence/measured/deploymentinformation.json     (price table, blocksLasting, allowances)
  evidence/measured/getblockchaininfo.json         (valuePools: sprout/sapling chainValue)
Constants from evidence/_fluxd_shielded.md §4 and evidence/_fluxd.md (block size).

Nothing here is fitted or guessed. Where a formula term is not in the cited FluxOS excerpt
(_fluxos.md §3.6) it is computed as a labelled variant, not silently assumed.
Outputs printed AND written to paper/data/private_renewal_*.dat.
"""
import json, math, os, statistics
from collections import Counter, defaultdict

ROOT = "/Users/tadeaskmenta/repos/fluxwhitepaper"
M    = f"{ROOT}/evidence/measured"
DATA = f"{ROOT}/paper/data"
GEN  = "python3 scripts/21-private-renewal.py  (repo: fluxwhitepaper; run 2026-09-03)"

def load(n):
    d = json.load(open(f"{M}/{n}"))
    return d["data"] if isinstance(d, dict) and "data" in d else d

apps  = load("globalappsspecifications.json")
depl  = load("deploymentinformation.json")
chain = load("getblockchaininfo.json")

# ---- chain / consensus constants ----------------------------------------------------
SPACING        = 30                      # s, chainparams.cpp:105
BLOCKS_DAY     = 86400 // SPACING        # 2880
MAX_BLOCK_SIZE = 2_000_000               # bytes, consensus.h:23 (_fluxd.md)
BLOCKS_LASTING = depl["blocksLasting"]   # 22,000 (pre-PoN units)
DEFAULT_EXPIRE = BLOCKS_LASTING * 4      # 88,000 post-PoN (messageVerifier.js:733-740 per _fluxos.md §3.6)
MIN_ALLOW, MAX_ALLOW, ALLOW_STEP = depl["minBlocksAllowance"], depl["maxBlocksAllowance"], depl["blocksAllowanceInterval"]
TIP = chain["blocks"]                    # 2,917,115

# price table: last segment (height 1,597,156) applies at the tip
seg = sorted(depl["price"], key=lambda s: s["height"])[-1]
P_CPU, P_RAM, P_HDD, P_MIN, P_PORT, P_SCOPE, P_SIP = (seg[k] for k in ("cpu","ram","hdd","minPrice","port","scope","staticip"))
ENT_PORTS = depl["enterprisePorts"]

def is_enterprise_port(p):
    for e in ENT_PORTS:
        if isinstance(e, str) and "-" in e:
            lo, hi = map(int, e.split("-"))
            if lo <= p <= hi: return True
        elif p == e: return True
    return False

# ---- Sapling wire sizes, derived from constants in _fluxd_shielded.md §4 -------------
ZC_MEMO_SIZE = 512; ZC_DIVERSIFIER_SIZE = 11; NOTEENCRYPTION_AUTH_BYTES = 16; GROTH_PROOF_SIZE = 192
enc_plaintext = 1 + ZC_DIVERSIFIER_SIZE + 8 + 32 + ZC_MEMO_SIZE      # lead byte, d, value, rcm, memo = 564
ENC_CT  = enc_plaintext + NOTEENCRYPTION_AUTH_BYTES                  # 580
OUT_CT  = 32 + 32 + NOTEENCRYPTION_AUTH_BYTES                        # pk_d, esk, tag = 80
SPEND_DESC  = 32 + 32 + 32 + 32 + GROTH_PROOF_SIZE + 64              # cv, anchor, nf, rk, proof, spendAuthSig = 384
OUTPUT_DESC = 32 + 32 + 32 + ENC_CT + OUT_CT + GROTH_PROOF_SIZE      # cv, cm, epk, encCt, outCt, proof = 948
# v4 (Sapling) tx skeleton for a z->t renewal: 1 spend, 1 change output, 2 transparent outputs
tx_header = 4 + 4 + 4 + 4 + 8            # header, versionGroupId, lockTime, expiryHeight, valueBalance
vin = 1                                  # count only (empty)
vout_p2sh  = 8 + 1 + 23                  # value, scriptlen, P2SH (t3... sink)
vout_opret = 8 + 1 + (1 + 1 + 32)        # value, scriptlen, OP_RETURN PUSH32 hash
vouts = 1 + vout_p2sh + vout_opret
shielded = 1 + SPEND_DESC + 1 + OUTPUT_DESC + 1 + 64   # counts, descs, nJoinSplit=0, bindingSig
TX_ZT = tx_header + vin + vouts + shielded
TX_TT_APPROX = 4+4+4+4+8 + 1 + (32+4+1+107+4) + 1 + (vout_p2sh + vout_opret + (8+1+25)) + 1+1+1  # 1 P2PKH in, sink+opret+change

print("== Sapling wire sizes (bytes), derived from _fluxd_shielded.md constants")
print(f"  enc plaintext {enc_plaintext}, encCiphertext {ENC_CT}, outCiphertext {OUT_CT}")
print(f"  SpendDescription {SPEND_DESC}, OutputDescription {OUTPUT_DESC}")
print(f"  z->t renewal tx (1 spend, 1 change out, sink + OP_RETURN) = {TX_ZT} bytes")
print(f"  transparent renewal tx (1 P2PKH in, sink + OP_RETURN + change) ~ {TX_TT_APPROX} bytes")
cap_zt = MAX_BLOCK_SIZE // TX_ZT
print(f"  block capacity at MAX_BLOCK_SIZE={MAX_BLOCK_SIZE}: {cap_zt} z->t renewals/block = {cap_zt/SPACING:.1f}/s; "
      f"{2*cap_zt} Groth16 proofs/block")

# ---- per-app price under the cited FluxOS formula (_fluxos.md §3.6) ---------------------
def resources(a):
    if "compose" in a:
        comps = a["compose"] or []
        return (sum(c.get("cpu",0) for c in comps), sum(c.get("ram",0) for c in comps),
                sum(c.get("hdd",0) for c in comps), comps)
    return (a.get("cpu",0), a.get("ram",0), a.get("hdd",0), None)

def price_month(a):
    cpu, ram, hdd, comps = resources(a)
    total = cpu * P_CPU * 10 + ram * P_RAM / 100 + hdd * P_HDD
    if (a.get("nodes") and len(a["nodes"])) or a.get("enterprise"):
        total += P_SCOPE
    if a.get("staticip"):
        total += P_SIP
    if a.get("enterprise") and comps:
        for c in comps:
            for p in c.get("ports", []):
                try:
                    if is_enterprise_port(int(p)): total += P_PORT
                except (TypeError, ValueError): pass
    price = math.ceil(total * 100) / 100
    return max(price, P_MIN)

def price_period(a, month):
    exp = a.get("expire", DEFAULT_EXPIRE)
    return math.ceil(month * exp / DEFAULT_EXPIRE * 100) / 100

rows = []
for a in apps:
    cpu, ram, hdd, comps = resources(a)
    pm  = price_month(a)
    inst = a.get("instances", 3)
    # VARIANT: instance scaling beyond 3 (not in the cited excerpt; labelled, see mech file)
    pm_inst = pm if inst <= 3 else math.ceil(pm * inst / 3 * 100) / 100
    exp = a.get("expire", DEFAULT_EXPIRE)
    rows.append(dict(name=a["name"], ver=a["version"], owner=a["owner"], inst=inst, exp=exp,
                     height=a["height"], next=a["height"] + exp, cpu=cpu, ram=ram, hdd=hdd,
                     ent=bool(a.get("enterprise")), sip=bool(a.get("staticip")),
                     nodes=len(a.get("nodes") or []), compose_empty=(comps is not None and len(comps)==0),
                     contacts=sum(1 for c in (a.get("contacts") or []) if isinstance(c, str) and c.strip()),
                     pm=pm, pp=price_period(a, pm), pm_inst=pm_inst, pp_inst=price_period(a, pm_inst)))

# ---- code-exact price, appUtilities.js:123-134 (round 18, G08) ---------------------------
# Definition 16.3 as corrected: the base is quoted per THREE instances and scaled by the
# instance count from height 1,890,000, with a 0.50 FLUX floor per additional instance for
# cheap specifications. The two older columns (pm/pm_inst) are kept as labelled bounds.
APPLY_EXTRA = 1890000

def price_month_code(a, height):
    cpu, ram, hdd, comps = resources(a)
    total = cpu * P_CPU * 10 + ram * P_RAM / 100 + hdd * P_HDD
    if (a.get("nodes") and len(a["nodes"])) or a.get("enterprise"):
        total += P_SCOPE
    if a.get("staticip"):
        total += P_SIP
    if a.get("enterprise") and comps:
        for c in comps:
            for port in c.get("ports", []):
                try:
                    if is_enterprise_port(int(port)):
                        total += P_PORT
                except (TypeError, ValueError):
                    pass
    beta = math.ceil(total / 3 * 100) / 100
    add = a.get("instances", 3) - 1
    if add > 0 and height >= APPLY_EXTRA:
        if beta < 0.50 and add > 2:
            return beta + add * 0.50
        return (math.ceil(beta * add * 100) + math.ceil(beta * 100)) / 100
    return beta

for _r, _a in zip(rows, apps):
    _r["pm_code"] = price_month_code(_a, _a["height"])
    # the minimum is re-applied after period scaling, messageVerifier.js:743-745
    _r["pp_code"] = max(price_period(_a, _r["pm_code"]), P_MIN)

N = len(rows)
print(f"\n== population: {N} applications, {sum(r['inst'] for r in rows)} requested instances")

# ---- what the specification itself publishes (the transparent-layer leak that no payment scheme fixes)
owners = Counter(r["owner"] for r in rows)
FOUNDATION_IDS = {"196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH": "former usersToExtend",
                  "1MCBJn6qsy3YRY2YasdYMYdJcdhy1ev8Rd": "usersToExtend (current)",
                  "1hjy4bCYBJr4mny4zCE85J94RXa8W6q37": "fluxTeamFluxID",
                  "16iJqiVbHptCx87q6XQwNpKdgEZnFtKcyP": "fluxSupportTeamFluxID"}
f_apps = sum(owners[k] for k in FOUNDATION_IDS)
print(f"  distinct owner IDs: {len(owners)}; apps per owner: median {statistics.median(owners.values())}, "
      f"max {max(owners.values())}; owners with 1 app: {sum(1 for v in owners.values() if v==1)}")
print(f"  top-5 owners (apps): {[v for _,v in owners.most_common(5)]}")
print(f"  apps owned by Foundation-config IDs: {f_apps} ({100*f_apps/N:.1f}%): "
      f"{ {FOUNDATION_IDS[k]: owners[k] for k in FOUNDATION_IDS} }")
contacts_n = sum(1 for r in rows if r["contacts"] > 0)
ent_n = sum(1 for r in rows if r["ent"]); ce_n = sum(1 for r in rows if r["compose_empty"])
emails = sum(1 for a in apps for c in (a.get("contacts") or []) if isinstance(c, str) and "@" in c)
print(f"  apps publishing >=1 non-blank contact string in the spec: {contacts_n} ({100*contacts_n/N:.1f}%); email-shaped entries across all apps: {emails}")
print(f"  enterprise (encrypted content) apps: {ent_n} ({100*ent_n/N:.1f}%); apps with empty compose: {ce_n}")

# ---- renewal schedule ----------------------------------------------------------------
exps = Counter(r["exp"] for r in rows)
print(f"\n== expire (blocks) distribution: distinct values {len(exps)}; "
      f"median {statistics.median(r['exp'] for r in rows)}, min {min(exps)}, max {max(exps)}")
print("  most common:", [(e, c, f"{e*SPACING/86400:.1f}d") for e, c in exps.most_common(8)])
rate_block = sum(1/r["exp"] for r in rows)            # expected renewals per block, if every app renews
print(f"  steady-state renewal rate if every app renews: {rate_block:.4f}/block = {rate_block*120:.2f}/hour "
      f"= {rate_block*BLOCKS_DAY:.1f}/day = {rate_block*BLOCKS_DAY*7:.0f}/week")
print(f"  block-budget share at that rate: {100*rate_block*TX_ZT/MAX_BLOCK_SIZE:.4f}% of MAX_BLOCK_SIZE")
for mult in (1, 10, 100, 1000):
    rb = rate_block*mult
    print(f"    x{mult:4d} demand: {rb:8.2f} tx/block, {100*rb*TX_ZT/MAX_BLOCK_SIZE:6.2f}% of block, "
          f"{2*rb:8.1f} proofs/block -> verify {2*rb*2/1000:6.2f}s @2ms, {2*rb*10/1000:6.2f}s @10ms")
# actual upcoming schedule, next 30 days, by day bucket (upper bound: assumes every app renews on time)
days = defaultdict(list)
for r in rows:
    d = (r["next"] - TIP) // BLOCKS_DAY
    if 0 <= d < 30: days[d].append(r)
sched = [len(days[d]) for d in range(30)]
print(f"  apps expiring in each of the next 30 days (assuming all renew): {sched}")
print(f"    total {sum(sched)}; per-day median {statistics.median(sched)}; max {max(sched)}; days with 0: {sched.count(0)}")
already = sum(1 for r in rows if r["next"] < TIP)
print(f"  apps whose height+expire is already below the tip (stale/legacy accounting): {already}")

# ---- anonymity classes -----------------------------------------------------------------
def classes(key):
    c = Counter(key(r) for r in rows)
    sizes = [c[key(r)] for r in rows]                    # size of the class each app sits in
    return c, sizes
def describe(label, c, sizes):
    single = sum(1 for s in sizes if s == 1)
    print(f"  {label}: {len(c)} classes; apps in a singleton class {single} ({100*single/N:.1f}%); "
          f"per-app class size median {statistics.median(sizes)}, mean {statistics.mean(sizes):.1f}, "
          f"largest {max(sizes)}; apps in class>=10: {sum(1 for s in sizes if s>=10)} ({100*sum(1 for s in sizes if s>=10)/N:.1f}%)")
    return single

print("\n== anonymity classes (formula-independent tuple = lower bound; cited-formula price = upper bound)")
c_tuple, s_tuple = classes(lambda r: (r["cpu"], r["ram"], r["hdd"], r["inst"], r["exp"], r["ent"], r["sip"], r["nodes"]>0))
describe("tuple (cpu,ram,hdd,inst,expire,ent,sip,nodes)", c_tuple, s_tuple)
c_pp, s_pp = classes(lambda r: r["pp"])
describe("period price, cited formula (no instance term)", c_pp, s_pp)
c_ppi, s_ppi = classes(lambda r: r["pp_inst"])
describe("period price, VARIANT with instance scaling", c_ppi, s_ppi)
c_ppc, s_ppc = classes(lambda r: r["pp_code"])
describe("period price, Definition 16.3 as corrected (code-exact)", c_ppc, s_ppc)
c_pm, s_pm = classes(lambda r: r["pm"])
describe("monthly price only (ignoring expire)", c_pm, s_pm)

# price + time window: same period price AND renewal in the same day / week bucket
def window_classes(win_blocks, key):
    c = Counter((key(r), (r["next"] // win_blocks)) for r in rows)
    return [c[(key(r), r["next"] // win_blocks)] for r in rows]
for win, lab in ((1, "1 block"), (120, "1 hour"), (BLOCKS_DAY, "1 day"), (7*BLOCKS_DAY, "1 week")):
    s = window_classes(win, lambda r: r["pp"])
    single = sum(1 for x in s if x == 1)
    print(f"  price AND renewal within the same {lab}: singleton {single} ({100*single/N:.1f}%), median class {statistics.median(s)}, max {max(s)}")

# ---- denomination rounding: amount privacy by overpayment ------------------------------
print("\n== denominated payment: round the period price UP to a grid; class structure and overpayment")
tot = sum(r["pp"] for r in rows)
for grid in (0.5, 1, 2, 5, 10):
    rounded = [math.ceil(r["pp"]/grid)*grid for r in rows]
    c = Counter(rounded); sizes = [c[x] for x in rounded]
    over = sum(rounded) - tot
    single = sum(1 for s in sizes if s == 1)
    print(f"  grid {grid:>4} FLUX: {len(c):3d} classes, singleton {single:3d} ({100*single/N:4.1f}%), "
          f"median class {statistics.median(sizes):5.0f}, largest {max(sizes):4d}, overpayment {100*over/tot:5.1f}% of list revenue")
pow2 = [2**math.ceil(math.log2(max(r["pp"], 0.01))) for r in rows]
c = Counter(pow2); sizes=[c[x] for x in pow2]
print(f"  power-of-two grid: {len(c)} classes, singleton {sum(1 for s in sizes if s==1)}, median class {statistics.median(sizes):.0f}, "
      f"largest {max(sizes)}, overpayment {100*(sum(pow2)-tot)/tot:.1f}%")

# ---- revenue and the shielded pool ------------------------------------------------------
pools = {p["id"]: p["chainValue"] for p in chain["valuePools"]}
rev_month = sum(r["pm"] for r in rows); rev_month_inst = sum(r["pm_inst"] for r in rows)
rev_year  = rev_month * 365.25 / (DEFAULT_EXPIRE*SPACING/86400)
rev_year_inst = rev_month_inst * 365.25 / (DEFAULT_EXPIRE*SPACING/86400)
print(f"\n== list-price revenue of the measured population (price table at height {seg['height']}, period = {DEFAULT_EXPIRE} blocks = {DEFAULT_EXPIRE*SPACING/86400:.2f} d)")
print(f"  per period: {rev_month:,.2f} FLUX (lower bound, base only) / {rev_month_inst:,.2f} FLUX (upper bound, n/3 variant)")
print(f"  per year:   {rev_year:,.0f} FLUX / {rev_year_inst:,.0f} FLUX")

# Definition 16.3 as corrected, split by who deployed it. Both halves are reported: the
# total is what the network priced, the third-party half is what it earned from tenants.
rev_month_code = sum(r["pm_code"] for r in rows)
f_month  = sum(r["pm_code"] for r in rows if r["owner"] in FOUNDATION_IDS)
tp_month = rev_month_code - f_month
per_year = lambda m: m * 365.25 / (DEFAULT_EXPIRE*SPACING/86400)
f_n  = sum(1 for r in rows if r["owner"] in FOUNDATION_IDS)
f_i  = sum(r["inst"] for r in rows if r["owner"] in FOUNDATION_IDS)
print(f"  code-exact (Definition 16.3 as corrected, round 18 G08):")
print(f"    all applications:   {rev_month_code:,.2f} FLUX per period  ({per_year(rev_month_code):,.0f}/yr)  "
      f"[{N} apps, {sum(r['inst'] for r in rows)} instances]")
print(f"    Foundation-deployed:{f_month:>10,.2f} FLUX per period  ({per_year(f_month):,.0f}/yr)  "
      f"[{f_n} apps, {f_i} instances, {100*f_month/rev_month_code:.1f}% of priced revenue]")
print(f"    third-party:        {tp_month:>10,.2f} FLUX per period  ({per_year(tp_month):,.0f}/yr)  "
      f"[{N-f_n} apps, {100*tp_month/rev_month_code:.1f}%]")
print(f"    sapling pool / annual: {pools['sapling']/per_year(rev_month_code):.2f} yr (all) / "
      f"{pools['sapling']/per_year(tp_month):.2f} yr (third-party only)")
print(f"  median period price {statistics.median(r['pp'] for r in rows):.2f} FLUX; min {min(r['pp'] for r in rows):.2f}; max {max(r['pp'] for r in rows):.2f}")
print(f"== shielded pool (getblockchaininfo.valuePools, tip {TIP}): sprout {pools['sprout']:,.8f}  sapling {pools['sapling']:,.8f}  total {pools['sprout']+pools['sapling']:,.8f} FLUX")
print(f"  sapling pool / annual list revenue = {pools['sapling']/rev_year:.3f} yr (cited) / {pools['sapling']/rev_year_inst:.3f} yr (variant)")
print(f"  sapling pool covers {pools['sapling']/rev_month:.1f} periods of the whole population, or the median app for {pools['sapling']/statistics.median(r['pp'] for r in rows):,.0f} periods")
print(f"  t->z has been closed since height 835,554; blocks since: {TIP-835554:,} ({(TIP-835554)/BLOCKS_DAY/365.25:.2f} yr at 30 s; wall-clock longer, pre-PoN spacing was 120 s)")

# ---- prepay instead of renew: the cheapest intersection-attack mitigation ----------------
print(f"\n== prepayment: maxBlocksAllowance {MAX_ALLOW:,} blocks = {MAX_ALLOW*SPACING/86400:.1f} d; minBlocksAllowance {MIN_ALLOW:,} = {MIN_ALLOW*SPACING/86400:.2f} d; step {ALLOW_STEP:,}")
print(f"  renewal events per year at default expire: {365.25*86400/(DEFAULT_EXPIRE*SPACING):.2f}; at max allowance: {365.25*86400/(MAX_ALLOW*SPACING):.2f}")

# ---- write .dat ---------------------------------------------------------------------------
os.makedirs(DATA, exist_ok=True)
with open(f"{DATA}/private_renewal_classes.dat", "w") as f:
    f.write(f"# generated by: {GEN}\n# generated on: 2026-09-03\n# source: api.runonflux.io/apps/globalappsspecifications, retrieved 2026-09-03T01:32:00Z; {N} applications\n")
    f.write("# anonymity-class sizes: for each period-price class (cited FluxOS formula, no instance term): price_flux  apps_in_class\n")
    for p, k in sorted(c_pp.items()): f.write(f"{p:.2f} {k}\n")
with open(f"{DATA}/private_renewal_schedule.dat", "w") as f:
    f.write(f"# generated by: {GEN}\n# generated on: 2026-09-03\n# day_from_tip  apps_expiring (upper bound: assumes every application renews on time); tip {TIP}\n")
    for d in range(30): f.write(f"{d} {sched[d]}\n")
with open(f"{DATA}/private_renewal_budget.dat", "w") as f:
    f.write(f"# generated by: {GEN}\n# generated on: 2026-09-03\n# demand_multiplier  tx_per_block  pct_of_block  proofs_per_block  verify_s_at_2ms  verify_s_at_10ms\n")
    for mult in (1, 10, 100, 1000):
        rb = rate_block*mult
        f.write(f"{mult} {rb:.4f} {100*rb*TX_ZT/MAX_BLOCK_SIZE:.4f} {2*rb:.2f} {2*rb*2/1000:.4f} {2*rb*10/1000:.4f}\n")
print(f"\nwrote {DATA}/private_renewal_classes.dat, private_renewal_schedule.dat, private_renewal_budget.dat")
