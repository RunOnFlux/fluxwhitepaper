#!/usr/bin/env python3
"""Cross-section consistency checks the paper cannot do for itself.

1. Numeric collisions: the same named quantity given different values in different sections.
2. Tense discipline: PLANNED/VISION material written in the present tense.
3. Provenance: \shipped without a nearby provenance macro.
Run from the repository root.
"""
import re, pathlib, collections

SEC = sorted(pathlib.Path("paper/sections").glob("*.tex"))
def clean(s):
    s = re.sub(r'%.*', '', s)
    return s

# ---------- 1. numeric collisions -------------------------------------------
# Track distinctive large numbers and where they appear.
num_re = re.compile(r'\\num\{([0-9]+(?:\.[0-9]+)?)\}|([0-9]{1,3}(?:\{,\}[0-9]{3})+(?:\.[0-9]+)?)')
where = collections.defaultdict(set)
for f in SEC:
    t = clean(f.read_text())
    for m in num_re.finditer(t):
        v = (m.group(1) or m.group(2) or "").replace("{,}", "")
        if not v: continue
        try: fv = float(v)
        except ValueError: continue
        if fv < 1000: continue
        where[v].add(f.name)

# Known quantities that must agree wherever they appear.
CANON = {
 "6489": "fleet size", "1195": "deployed applications", "88514500": "locked collateral",
 "429466823.97": "supply at 2,912,015", "2020000": "PoN activation height",
 "3787502": "PA Depletion height", "86400": "drip constant K", "1932380": "v8 enforcement height",
 "219958321.46": "measured EVM liability", "6386040": "operator issuance at activation",
 "156217342.78": "Ethereum outstanding", "77188.75921324": "Sapling pool",
 "835554": "UPGRADE_FLUX height", "2176519": "v8 min-instance height",
}
print("=== 1. canonical quantities and where they appear ===")
for v, name in CANON.items():
    hits = where.get(v, set())
    print(f"  {name:34} {v:>16}  in {len(hits)} section(s)")

# Numbers that look like near-misses of a canonical value (possible stale copies)
print("\n=== possible stale variants of canonical numbers ===")
canon_f = {float(k): (k, n) for k, n in CANON.items()}
flagged = 0
for v, files in where.items():
    try: fv = float(v)
    except ValueError: continue
    for cf, (ck, cn) in canon_f.items():
        if cf == fv: continue
        if cf and abs(fv - cf) / cf < 0.05 and abs(fv - cf) > 0:
            print(f"  {v:>16} ~ {ck} ({cn})  in {sorted(files)}")
            flagged += 1
print(f"  ({flagged} near-misses)")

# ---------- 2. tense discipline ---------------------------------------------
PRESENT = r'\b(is|are|does|has|have|provides|pays|enforces|holds|runs|uses|makes|allows|gives)\b'
print("\n=== 2. present tense within one line of a PLANNED/VISION tag ===")
tense = 0
for f in SEC:
    lines = clean(f.read_text()).splitlines()
    for i, l in enumerate(lines):
        if not re.search(r'\\(planned|vision)\b', l): continue
        seg = l
        if re.search(r'\\(planned|vision)\b\s*' + PRESENT, seg):
            tense += 1
            if tense <= 12:
                print(f"  {f.name}:{i+1}  {seg.strip()[:104]}")
print(f"  ({tense} candidate lines; manual review — many will be legitimate)")

# ---------- 3. shipped provenance -------------------------------------------
print("\n=== 3. \\shipped with no provenance macro within +/-3 lines ===")
bad = 0
for f in SEC:
    lines = clean(f.read_text()).splitlines()
    for i, l in enumerate(lines):
        if "\\shipped" not in l: continue
        if re.search(r'\\begin\{\w+\}\[', l) or "&" in l or "\\caption" in l: continue
        win = " ".join(lines[max(0,i-3):i+4])
        if not re.search(r'\\src(code|branch|measured|doc|roadmap|intent|inferred)', win):
            bad += 1
            if bad <= 10: print(f"  {f.name}:{i+1}  {l.strip()[:100]}")
print(f"  ({bad} total)")
