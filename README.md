# Flux v9: A Decentralized Cloud for Autonomous Compute

**[FluxWhitepaper-Combined.pdf](FluxWhitepaper-Combined.pdf)** — the one document for any
audience: the 16-page short paper first, the 423-page full paper behind it, each with its own
bookmarks. Also separately: **[FluxWhitepaper.pdf](FluxWhitepaper.pdf)** (full paper, 423 pages,
version 1.0) and **[FluxWhitepaper-Short.pdf](FluxWhitepaper-Short.pdf)** (short paper, 16 pages).

A technical description of the Flux network as deployed, and a specification of the
architecture it is being rebuilt into. Both halves are written to the same standard:
every claim carries a provenance citation, every claim about deployed behaviour carries
a source-code citation, and every element of the target architecture that is undecided
is marked as such rather than filled with a plausible default.

Claims are tagged for **maturity** — shipped, in progress, planned, vision — and for
**provenance** — read from code, from roadmap material, from design intake, or inferred.
The two axes are independent and both are always given. One label,
*Not established by this survey*, marks the 22 places where the evidence read for the
paper does not settle a question; those are stated limits, not omissions.

## Building

```
bash scripts/build.sh          # -> FluxWhitepaper.pdf, FluxWhitepaper-Short.pdf, FluxWhitepaper-Combined.pdf
CLEAN=1 bash scripts/build.sh  # full rebuild from scratch
```

Requires a TeX distribution with `latexmk`, `pgfplots`, `algorithm2e`, `siunitx`,
`booktabs`, `longtable`, `tikz`, `adjustbox`, `titlesec` and `biblatex`'s `natbib`
compatibility; the combined document needs `pypdf` (`python3 -m pip install pypdf`). A clean
build produces no errors, no undefined references and no undefined citations.

## Reproducing the measurements

Every measured figure in the paper cites its endpoint and retrieval date. The scripts
that produced them are here:

```
bash    scripts/04-measure.sh              # live API snapshot
python3 scripts/05-network-analysis.py     # fleet, concentration, rotation, applications
python3 scripts/23-network-capacity.py     # aggregate CPU / RAM / storage capacity
bash    scripts/12-parallel-liability.sh   # per-chain totalSupply and issuer-held balances
bash    scripts/13-issuer-balances.sh      # outstanding parallel-asset liability
python3 scripts/07-pnr-settlement.py       # drip trade-off and crossover series
python3 scripts/21-private-renewal.py      # anonymity classes, schedule, verification budget
python3 scripts/22-moderation-tables.py    # governance concentration and tenure tables
python3 scripts/14-consistency.py          # cross-section numeric and provenance checks
```

### Two source snapshots are deliberately not included

`scripts/04-measure.sh` regenerates every snapshot from the public API. Two of the
2026-09-03 captures are **not** committed here:

- `listzelnodes.json` — carries the IP address of every one of 6,479 nodes.
- `globalappsspecifications.json` — carries tenant application specifications, including
  contact strings and environment variables.

Both come from public endpoints, but committing them to a public repository would
aggregate and persist third-party operator and tenant data in a way the live API does
not. Run `scripts/04-measure.sh` to fetch current equivalents; figures will differ from
the paper's, which are pinned to 2026-09-03 and cited with that date throughout.

Three scripts need one or both of those files and will not run until you fetch them:
`05-network-analysis.py`, `21-private-renewal.py` and `22-moderation-tables.py`.
`23-network-capacity.py` runs either way — it falls back to the published census.

The aggregate snapshots the other scripts need — network totals, the price table, the
per-chain liability figures — are included under `evidence/measured/`.

## Licence

The paper is © Tadeas Kmenta. The scripts are provided so that every measured figure in
it can be checked.
