#!/usr/bin/env python3
"""Summarise paper/main.log into the counts that matter.

A green build says nothing about whether a sentence still means anything, but a
build that got *worse* after an edit is a hard stop. This is the before/after.

    python3 scripts/_buildstats.py [paper/main.log]
"""
import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "paper/main.log"

try:
    with open(LOG, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
except OSError as exc:
    sys.exit(f"cannot read {LOG}: {exc}")

overfull = [float(m) for m in re.findall(r"Overfull \\hbox \((\d+\.?\d*)pt", text)]

stats = {
    # A duplicate label *resolves* — to the wrong target — so "0 undefined" misses it.
    "errors": len(re.findall(r"^! ", text, re.M)),
    "undef_refs": len(re.findall(r"Reference `[^']*' on page \d+ undefined", text)),
    "undef_cites": len(re.findall(r"Citation `[^']*' on page \d+ undefined", text)),
    "multiply_defined": len(re.findall(r"Label `[^']*' multiply defined", text)),
    "floats_lost": len(re.findall(r"float\(s\) lost", text, re.I)),
    "overfull_20pt": sum(1 for pt in overfull if pt > 20),
    "worst_overfull_pt": round(max(overfull), 1) if overfull else 0.0,
}

print(" · ".join(f"{k}={v}" for k, v in stats.items()))
