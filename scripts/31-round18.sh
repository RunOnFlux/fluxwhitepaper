#!/usr/bin/env bash
#
# 31-round18.sh — propagate a newly recorded answer round across every unit.
#
# Round 18 (evidence/design/08-answers-round-2.md) rules all 30 escalations from the
# review. This runs the --decisions pass per unit: find every site that contradicts a
# decision, apply, verify against baseline, report. It is a propagation pass, not a
# fresh audit — the audit already happened.
#
#   bash scripts/31-round18.sh              # all units, resumable
#   bash scripts/31-round18.sh u09-bridging # one unit
#   ROUND=19 bash scripts/31-round18.sh     # a later round
#
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-claude-fable-5-1}"
EFFORT="${EFFORT:-xhigh}"
BUDGET="${BUDGET:-25}"
ROUND="${ROUND:-18}"
UNITS_FILE="scripts/paper-units.txt"
LOGDIR="logs/review"
mkdir -p review "$LOGDIR"

ALL=""
while read -r u; do ALL="$ALL $u"; done \
  < <(awk -F'\t+' '!/^#/ && NF>2 {print $1}' "$UNITS_FILE")
if [ $# -gt 0 ]; then UNITS="$*"; else UNITS="$ALL"; fi

for unit in $UNITS; do
  report="review/$unit.r$ROUND.md"
  if [ -f "$report" ] && [ "${FORCE:-0}" != "1" ]; then
    echo "  skip $unit — $report exists"
    continue
  fi

  echo "── $unit · round $ROUND propagation ──────────────────"
  claude --print "/finish-paper $unit --decisions $ROUND" \
      --model "$MODEL" --effort "$EFFORT" --max-budget-usd "$BUDGET" \
      --permission-mode acceptEdits \
      --allowedTools Read Grep Glob Write Edit Bash \
      --output-format stream-json --verbose \
    | python3 scripts/_stream.py "$LOGDIR/$unit.r$ROUND.cost.json" \
    | tee "$LOGDIR/$unit.r$ROUND.log" || true

  # A usage-limited session still reports success; the report is the real signal.
  if [ ! -f "$report" ]; then
    echo "  INCOMPLETE: $unit wrote no report" >&2
    grep -q "session limit\|usage limit" "$LOGDIR/$unit.r$ROUND.log" 2>/dev/null \
      && echo "  cause: usage limit — rerun this command when it resets." >&2
    echo "  stopping; rerun to resume from $unit" >&2
    break
  fi
done

echo
python3 - <<PY
import glob, json
tot = 0.0
for p in sorted(glob.glob("logs/review/*.r${ROUND}.cost.json")):
    try: d = json.load(open(p))
    except Exception: continue
    c = d.get("cost_usd") or 0.0
    tot += c
    print(f"  {p.split('/')[-1].replace('.r${ROUND}.cost.json',''):<22} \${c:6.2f}")
print(f"  {'total':<22} \${tot:6.2f}")
PY
echo "Baseline: $(cat review/_baseline.txt 2>/dev/null)"
echo "Current:  $(python3 scripts/_buildstats.py paper/main.log 2>/dev/null)"
