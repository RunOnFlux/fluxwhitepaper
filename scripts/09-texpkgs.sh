#!/usr/bin/env bash
SP=/private/tmp/claude-501/-Users-tadeaskmenta-repos-fluxwhitepaper/f94bed4d-7cc9-4f27-b7af-e26ef45074f5/scratchpad/tl
TH=/Users/tadeaskmenta/Library/TinyTeX/texmf-local
BASE=https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2025/tlnet-final/archive
mkdir -p "$SP" "$TH"; cd "$SP" || exit 1
for p in mathtools mhsetup siunitx listings algorithm2e relsize pgf pgfplots microtype cleveref todonotes ifoddpage trimspaces l3packages xkeyval koma-script float caption; do
  [ -s "$p.tar.xz" ] || curl -sSfL --max-time 300 -o "$p.tar.xz" "$BASE/$p.tar.xz" || { echo "DL-FAIL $p"; rm -f "$p.tar.xz"; continue; }
  tar -xf "$p.tar.xz" -C "$TH" && echo "OK $p" || echo "EXTRACT-FAIL $p"
done
echo DONE
