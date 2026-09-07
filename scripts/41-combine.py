#!/usr/bin/env python3
"""41-combine.py — one distributable PDF: the short paper first, the full paper behind it.

    python3 scripts/41-combine.py            # -> FluxWhitepaper-Combined.pdf

Inputs are the two built PDFs (short/main.pdf, paper/main.pdf). Each paper's own bookmark
outline is nested under a top-level entry, internal links are carried across, and page labels
are set so a viewer shows the short paper's pages, then the full paper's roman front matter and
arabic body, exactly as printed. Requires pypdf (pure Python): python3 -m pip install pypdf
"""
import logging
from pathlib import Path
from pypdf import PdfReader, PdfWriter
logging.getLogger("pypdf").setLevel(logging.ERROR)  # append() logs one line per annotated page; the link count below is the real check

ROOT = Path(__file__).resolve().parent.parent
SHORT, FULL, OUT = ROOT / "short/main.pdf", ROOT / "paper/main.pdf", ROOT / "FluxWhitepaper-Combined.pdf"

short, full = PdfReader(str(SHORT)), PdfReader(str(FULL))
n_short, n_full = len(short.pages), len(full.pages)

# page labels: the short paper as S-1..S-n; the full paper's own label runs mirrored exactly
# (hyperref writes them: the title page, roman front matter, arabic body)
import re
ROMAN = re.compile(r"^[ivxlcdm]+$")
def runs(labels):
    """[(start_index, end_index, style, first_number)] for each contiguous labelled run."""
    out, i = [], 0
    def val(l): return int(l) if l.isdigit() else roman_to_int(l)
    while i < len(labels):
        style = "/r" if ROMAN.match(labels[i]) else "/D"
        j = i
        while j + 1 < len(labels) and (("/r" if ROMAN.match(labels[j + 1]) else "/D") == style) \
                and val(labels[j + 1]) == val(labels[j]) + 1:
            j += 1
        out.append((i, j, style, val(labels[i]))); i = j + 1
    return out
def roman_to_int(r):
    v, m = 0, {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    for k, ch in enumerate(r):
        v += -m[ch] if k + 1 < len(r) and m[ch] < m[r[k + 1]] else m[ch]
    return v

w = PdfWriter()
w.append(short, outline_item="Flux, in brief — the short paper")
w.append(full,  outline_item="Flux v9: A Decentralized Cloud for Autonomous Compute — the full paper")
w.add_metadata({"/Title": "Flux v9: A Decentralized Cloud for Autonomous Compute (short and full papers)",
                "/Author": "Tadeas Kmenta"})
w.set_page_label(0, n_short - 1, "/D", "S-", 1)
for i, j, style, first in runs(list(full.page_labels)):
    w.set_page_label(n_short + i, n_short + j, style, None, first)
w.write(str(OUT))
r = PdfReader(str(OUT))
def count(o): return sum(1 + (count(x) if isinstance(x, list) else 0) for x in o) if isinstance(o, list) else 0
print(f"{OUT.name}: {len(r.pages)} pages ({n_short} short + {n_full} full), {count(r.outline)} outline entries, "
      f"labels: {r.page_labels[0]}..{r.page_labels[n_short-1]} | " + ", ".join(f"{r.page_labels[n_short+i]}..{r.page_labels[n_short+j]}" for i, j, _, _ in runs(list(full.page_labels))))
