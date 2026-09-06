#!/usr/bin/env bash
# Pass 0b: score + bucket every repo. Zero model tokens. Output is meant to be eyeballed.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh
NOW=$(date +%s)

jq -r --arg now "$NOW" \
   --arg pin "$(echo $PIN_CORE)" \
   --arg skip "$(echo $PIN_SKIP)" \
   --arg noise "$NOISE_RE" \
   --arg signal "$(echo $SIGNAL_RE | tr -d ' \n')" '
  ($pin|split(" ")) as $P | ($skip|split(" ")) as $S |
  .[] |
  .name as $nm |
  ((($now|tonumber) - (.pushedAt|fromdate)) / 86400) as $age |
  ((.name + " " + (.description//"") + " " + ([.repositoryTopics[]?.name]|join(" ")))|ascii_downcase) as $hay |
  ([$hay|scan($signal)]|unique|length) as $sig |
  ( (if .isFork then -100 else 0 end)
  + (if .isArchived then -100 else 0 end)
  + (if ($nm|ascii_downcase|test($noise)) then -60 else 0 end)
  + (if ($P|index($nm)) then 500 else 0 end)
  + (if ($S|index($nm)) then -1000 else 0 end)
  + (.stargazerCount * 4)
  + (if $age < 90 then 25 elif $age < 365 then 10 elif $age < 1095 then 0 else -25 end)
  + ($sig * 8)
  + (if (.diskUsage//0) > 20000 then 20 elif (.diskUsage//0) > 2000 then 10 elif (.diskUsage//0) < 150 then -30 else 0 end)
  + (if (.description//"")=="" then -10 else 0 end)
  ) as $score |
  [ (if $score >= 120 then "CORE" elif $score >= 45 then "SUPPORTING" else "SKIP" end),
    ($score|floor|tostring), .full, (.pushedAt[0:10]), (.stargazerCount|tostring),
    (.primaryLanguage.name//"-"), ($sig|tostring), ((.description//"no description")|.[0:70]) ]
  | @tsv
' out/inventory.json | sort -t$'\t' -k2,2nr > out/scored.tsv

awk -F'\t' '{print > ("out/tier-" $1 ".tsv")}' out/scored.tsv
cut -f3 out/tier-CORE.tsv 2>/dev/null > out/repos-selected.txt || true
cut -f3 out/tier-SUPPORTING.tsv 2>/dev/null >> out/repos-selected.txt || true

printf '%-12s %s\n' CORE "$(wc -l < out/tier-CORE.tsv 2>/dev/null || echo 0)" \
                    SUPPORTING "$(wc -l < out/tier-SUPPORTING.tsv 2>/dev/null || echo 0)" \
                    SKIP "$(wc -l < out/tier-SKIP.tsv 2>/dev/null || echo 0)"
echo
echo "extraction set -> out/repos-selected.txt ($(wc -l < out/repos-selected.txt) repos)"
echo "review out/scored.tsv, then move lines between tiers by editing PIN_CORE/PIN_SKIP in scripts/config.sh"
