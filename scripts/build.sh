#!/usr/bin/env bash
#
# build.sh — build both papers and the combined document, publishing them to the repository root.
#
# latexmk writes paper/main.pdf and short/main.pdf; the distributable copies at the root are
# FluxWhitepaper.pdf (full), FluxWhitepaper-Short.pdf, and FluxWhitepaper-Combined.pdf (short
# paper first, full paper behind it — the one document to hand to any audience).
#
#   bash scripts/build.sh          # incremental
#   CLEAN=1 bash scripts/build.sh  # full rebuild from scratch
#
set -euo pipefail
cd "$(dirname "$0")/.."

[ "${CLEAN:-0}" = "1" ] && ( cd paper && latexmk -C >/dev/null 2>&1 )

( cd paper && latexmk -pdf -interaction=nonstopmode main.tex >/dev/null 2>&1 ) || {
  echo "build failed — see paper/main.log" >&2; exit 1; }

cp paper/main.pdf FluxWhitepaper.pdf
echo "FluxWhitepaper.pdf  $(pdfinfo FluxWhitepaper.pdf | awk '/Pages/{print $2}') pages, $(du -h FluxWhitepaper.pdf | cut -f1)"
python3 scripts/_buildstats.py paper/main.log

# the short paper, and the combined document (short paper first, full paper behind it)
( cd short && latexmk -pdf -interaction=nonstopmode main.tex >/dev/null 2>&1 ) || {
  echo "short-paper build failed — see short/main.log" >&2; exit 1; }
cp short/main.pdf FluxWhitepaper-Short.pdf
echo "FluxWhitepaper-Short.pdf  $(pdfinfo FluxWhitepaper-Short.pdf | awk '/Pages/{print $2}') pages"
python3 scripts/41-combine.py
