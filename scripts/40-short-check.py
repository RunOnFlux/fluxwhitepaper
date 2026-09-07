#!/usr/bin/env python3
r"""
40-short-check.py — the consistency gate between the short paper and the long one.

Two documents, one set of facts. The long paper's most-repeated defect (C1a, C43, C60)
was a value corrected in one place and not another; a second document doubles that
surface. This script makes drift a build failure rather than a discovery.

For every numeric literal the short paper states — \num{...}, \SI{...}{...}, and bare
figures with thousands separators — it checks that the same value appears somewhere in
paper/sections/. A number the long paper does not contain is either a new claim (which
the short paper must not make) or a transcription error (which it must not have).

Exit 0 if every number is grounded; exit 1 and list the strays otherwise.

  python3 scripts/40-short-check.py            # check
  python3 scripts/40-short-check.py --verbose  # also list what was checked
"""
import re, sys, glob, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHORT = ROOT / "short" / "sections"
LONG  = ROOT / "paper" / "sections"

def numbers_in(text):
    """Numeric literals as the reader sees them, normalised to a bare string."""
    found = set()
    for m in re.finditer(r'\\num\{([0-9][0-9.,{}]*)\}', text):
        found.add(m.group(1).replace('{','').replace('}','').replace(',',''))
    for m in re.finditer(r'\\SI\{([0-9][0-9.,{}]*)\}', text):
        found.add(m.group(1).replace('{','').replace('}','').replace(',',''))
    # bare figures with thousands separators, e.g. 6,489 or 3,466,630
    for m in re.finditer(r'(?<![\d.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?)(?![\d])', text):
        found.add(m.group(1).replace(',',''))
    return found

def normalise_long(text):
    """Strip LaTeX grouping so \num{3{,}466{,}630} and 3,466,630 both become 3466630."""
    t = text.replace('{,}', '').replace('\\,', '')
    t = re.sub(r'\\num\{([^}]*)\}', lambda m: m.group(1).replace(',',''), t)
    t = re.sub(r'\\SI\{([^}]*)\}', lambda m: m.group(1).replace(',',''), t)
    t = re.sub(r'(\d),(\d{3})', r'\1\2', t)
    t = re.sub(r'(\d),(\d{3})', r'\1\2', t)   # second pass for 7+ digit figures
    return t

# Single digits are structural (list counts, section numbers) and are not claims;
# anything from 10 up — a percentage, a token rate, a count — is checked.
IGNORE_BELOW = 10
# Years are dates, not measurements.
def is_year(s): return re.fullmatch(r'20[2-6]\d', s) is not None

verbose = '--verbose' in sys.argv
long_text = normalise_long("\n".join(p.read_text() for p in LONG.glob("*.tex")))

strays = []; checked = 0
for f in sorted(SHORT.glob("*.tex")):
    for n in sorted(numbers_in(f.read_text())):
        try: v = float(n)
        except ValueError: continue
        if v < IGNORE_BELOW or is_year(n): continue
        checked += 1
        # accept exact, or the integer part for figures the long paper states with more decimals
        ok = (n in long_text) or (n.rstrip('0').rstrip('.') in long_text) or (n.split('.')[0] in long_text and '.' in n)
        if verbose: print(f"  {'ok ' if ok else 'STRAY'} {n:<22} {f.name}")
        if not ok: strays.append((f.name, n))

print(f"short-check: {checked} numbers checked against paper/sections/")
if strays:
    print(f"  {len(strays)} NOT grounded in the long paper:")
    for f, n in strays: print(f"    {n:<22} in {f}")
    sys.exit(1)
print("  all grounded.")
