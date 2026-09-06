#!/usr/bin/env bash
#
# build.sh — build the whitepaper and publish it to the repository root.
#
# latexmk writes paper/main.pdf; the distributable copy is FluxWhitepaper.pdf at
# the root, which is the name to hand people. Both are the same build.
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
