#!/usr/bin/env bash
#
# 30-finish.sh — audit, correct and verify the whitepaper, one unit per fresh session.
#
# The paper is ~1.65 MB of LaTeX (~500k tokens). Reviewing it in a single context
# leaves no headroom for the reasoning that makes the pass worth running, so each
# unit from scripts/paper-units.txt gets its own session, at the effort that unit's
# work actually needs, then a synthesis pass over the reports.
#
#   bash scripts/30-finish.sh                    # every unit, then synthesize
#   bash scripts/30-finish.sh u09-bridging       # one unit
#   AUDIT=1 bash scripts/30-finish.sh u03-pnr    # find and report, change nothing
#   EFFORT=max bash scripts/30-finish.sh u09-bridging   # override the per-unit effort
#   FORCE=1 bash scripts/30-finish.sh            # redo units already reported
#
# Env: MODEL (default claude-fable-5-1) · EFFORT (default: per-unit column) ·
#      BUDGET usd/unit (default 20) · AUDIT · FORCE · SYNTH=0 to skip synthesis.
#
# Cost is measured, not estimated: each unit writes logs/review/<unit>.cost.json and
# the run prints a total. Run one unit first and look at the number.
#
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-claude-fable-5-1}"
BUDGET="${BUDGET:-20}"
UNITS_FILE="scripts/paper-units.txt"
LOGDIR="logs/review"
mkdir -p review "$LOGDIR"

AUDIT_ARG=""; [ "${AUDIT:-0}" = "1" ] && AUDIT_ARG=" --audit-only"

# bash 3.2 (macOS system bash) has no mapfile.
ALL_UNITS=""
while read -r u; do ALL_UNITS="$ALL_UNITS $u"; done \
  < <(awk -F'\t+' '!/^#/ && NF>2 {print $1}' "$UNITS_FILE")
if [ $# -gt 0 ]; then UNITS="$*"; else UNITS="$ALL_UNITS"; fi

unit_effort() {
  awk -F'\t+' -v u="$1" '!/^#/ && $1==u {print $2; exit}' "$UNITS_FILE"
}

# ── Build baseline. §6 of the command compares against this; capture it before any
#    edit lands, or "no worse than baseline" means nothing.
if [ ! -f review/_baseline.txt ] || [ "${FORCE:-0}" = "1" ]; then
  echo "── baseline build ────────────────────────────────────"
  ( cd paper && latexmk -pdf -interaction=nonstopmode main.tex >/dev/null 2>&1 ) || true
  python3 scripts/_buildstats.py paper/main.log | tee review/_baseline.txt
fi

run_unit() {
  unit="$1"
  # An audit writes its own report, so it never shadows a later corrected pass.
  if [ "${AUDIT:-0}" = "1" ]; then
    report="review/$unit.audit.md"; log="$LOGDIR/$unit.audit.log"
    costfile="$LOGDIR/$unit.audit.cost.json"
  else
    report="review/$unit.md"; log="$LOGDIR/$unit.log"
    costfile="$LOGDIR/$unit.cost.json"
  fi

  if [ -f "$report" ] && [ "${FORCE:-0}" != "1" ]; then
    echo "  skip $unit — $report exists (FORCE=1 to redo)"
    return 0
  fi

  effort="${EFFORT:-$(unit_effort "$unit")}"
  [ -n "$effort" ] || effort=xhigh

  echo "── $unit · $MODEL · effort $effort ───────────────────"
  # --allowedTools: print mode has nobody to answer a permission prompt, so anything
  # not named here is denied and the session stalls.
  claude --print "/finish-paper ${unit}${AUDIT_ARG}" \
      --model "$MODEL" \
      --effort "$effort" \
      --max-budget-usd "$BUDGET" \
      --permission-mode acceptEdits \
      --allowedTools Read Grep Glob Write Edit Bash \
      --output-format stream-json --verbose \
    | python3 scripts/_stream.py "$costfile" \
    | tee "$log" || true

  # A session that hits its usage limit still ends with subtype "success" — it just
  # stops. The only trustworthy completion signal is the report actually existing.
  if [ ! -f "$report" ]; then
    echo "  INCOMPLETE: $unit wrote no report (see $log)" >&2
    grep -q "session limit\|usage limit\|rate limit" "$log" 2>/dev/null \
      && echo "  cause: usage limit — every later unit would fail the same way." >&2
    return 1
  fi
}

failed=""
for unit in $UNITS; do
  grep -q "^${unit}[[:space:]]" "$UNITS_FILE" || { echo "unknown unit: $unit" >&2; exit 2; }
  if ! run_unit "$unit"; then
    # Stop rather than burn the remaining units against the same wall. Completed
    # reports are on disk, so re-running resumes here.
    failed="$failed $unit"
    echo "  stopping — rerun the same command to resume from $unit" >&2
    break
  fi
done

if [ "${SYNTH:-1}" = "1" ] && [ $# -eq 0 ]; then
  echo "── synthesize ────────────────────────────────────────"
  claude --print "/finish-paper synthesize" \
      --model "$MODEL" --effort "${EFFORT:-xhigh}" --max-budget-usd "$BUDGET" \
      --permission-mode acceptEdits \
      --allowedTools Read Grep Glob Write Bash \
      --output-format stream-json --verbose \
    | python3 scripts/_stream.py "$LOGDIR/synthesize.cost.json" \
    | tee "$LOGDIR/synthesize.log" || failed="$failed synthesize"
fi

echo
python3 - <<'PY'
import glob, json
total, rows = 0.0, []
for path in sorted(glob.glob("logs/review/*.cost.json")):
    try:
        d = json.load(open(path))
    except Exception:
        continue
    cost = d.get("cost_usd") or 0.0
    total += cost
    rows.append(f"  {path.split('/')[-1].replace('.cost.json',''):<20} ${cost:6.2f}  {d.get('turns','?')} turns")
if rows:
    print("Measured cost")
    print("\n".join(rows))
    print(f"  {'total':<20} ${total:6.2f}")
PY

echo
echo "Baseline: $(cat review/_baseline.txt 2>/dev/null)"
echo "Current:  $(python3 scripts/_buildstats.py paper/main.log 2>/dev/null)"
echo "Reports:  review/"
if [ -n "$failed" ]; then
  echo "Failed:  $failed — rerun those unit ids individually" >&2
  exit 1
fi
echo "Read:     review/00-SUMMARY.md — escalations first"
