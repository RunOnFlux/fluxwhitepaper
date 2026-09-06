#!/usr/bin/env bash
# Iteratively resolve missing LaTeX packages by fetching them from the TL2025 archive.
SP=/private/tmp/claude-501/-Users-tadeaskmenta-repos-fluxwhitepaper/f94bed4d-7cc9-4f27-b7af-e26ef45074f5/scratchpad/tl
TH=/Users/tadeaskmenta/Library/TinyTeX/texmf-local
BASE=https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2025/tlnet-final/archive
cd /Users/tadeaskmenta/repos/fluxwhitepaper/paper || exit 1
mkdir -p "$SP"
for i in $(seq 1 25); do
  pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
  miss=$(grep -oE "File \`[A-Za-z0-9@_.-]+\.(sty|cls|def|cfg)' not found" main.log | head -1 | sed -E "s/File \`([^']+)'.*/\1/")
  [ -z "$miss" ] && { echo "NO-MISSING-FILE after $i pass(es)"; break; }
  pkg="${miss%.*}"
  echo "pass $i: missing $miss -> trying package $pkg"
  if [ ! -s "$SP/$pkg.tar.xz" ]; then
    curl -sSfL --max-time 200 -o "$SP/$pkg.tar.xz" "$BASE/$pkg.tar.xz" || { echo "  DL-FAIL $pkg"; rm -f "$SP/$pkg.tar.xz"; echo "STUCK:$miss"; break; }
  fi
  tar -xf "$SP/$pkg.tar.xz" -C "$TH" || { echo "  EXTRACT-FAIL $pkg"; echo "STUCK:$miss"; break; }
  mktexlsr "$TH" >/dev/null 2>&1
done
echo "--- final error scan ---"
grep -E '^! ' main.log | head -10
