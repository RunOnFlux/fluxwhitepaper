#!/usr/bin/env bash
# Build a uniform corpus root at ./repos/<name> for every selected repository.
# Strategy: symlink fresh local checkouts, worktree large stale ones, shallow-clone the rest.
set -u
ROOT="/Users/tadeaskmenta/repos/fluxwhitepaper"
CORPUS="$ROOT/repos"
INV="$ROOT/out/inventory.json"
LOCAL="$HOME/repos"
LOG="$ROOT/logs/corpus.log"
: > "$LOG"

fresh_days=4

resolve() { # org/name -> pushedAt date
  jq -r --arg f "$1" '.[]|select(.full==$f)|.pushedAt[0:10]' "$INV" | head -1
}

add() {
  local full="$1" name="${1#*/}" ; local dest="$CORPUS/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then echo "skip-exists $name" >>"$LOG"; return; fi
  local pushed; pushed=$(resolve "$full")
  local lp="$LOCAL/$name"
  if [ -d "$lp/.git" ]; then
    local lh; lh=$(git -C "$lp" log -1 --format=%cs 2>/dev/null)
    # fresh enough?
    if [ -n "$lh" ] && [ -n "$pushed" ]; then
      local a b; a=$(date -j -f %Y-%m-%d "$lh" +%s 2>/dev/null); b=$(date -j -f %Y-%m-%d "$pushed" +%s 2>/dev/null)
      if [ -n "$a" ] && [ -n "$b" ] && [ $((b-a)) -le $((fresh_days*86400)) ]; then
        ln -s "$lp" "$dest"; echo "symlink  $name  local=$lh origin=$pushed" >>"$LOG"; return
      fi
    fi
    # stale: if the local clone is large, use a worktree off it; else re-clone shallow
    local sz; sz=$(du -sm "$lp" 2>/dev/null | cut -f1)
    if [ -n "$sz" ] && [ "$sz" -gt 120 ]; then
      git -C "$lp" fetch --quiet origin 2>>"$LOG"
      local db; db=$(git -C "$lp" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || echo "origin/master")
      git -C "$lp" worktree add --detach "$dest" "$db" >>"$LOG" 2>&1 \
        && { echo "worktree $name  at $db (local was $lh)" >>"$LOG"; return; }
    fi
  fi
  gh repo clone "$full" "$dest" -- --depth 1 --quiet >>"$LOG" 2>&1 \
    && echo "clone    $name" >>"$LOG" || echo "FAIL     $name" >>"$LOG"
}

while read -r full; do [ -z "$full" ] && continue; case "$full" in \#*) continue;; esac; add "$full"; done < "$ROOT/out/corpus-list.txt"

# Pinned upstream references (round 18, G23). A \srcbranch{<name>}{<ref>}{file:line} citation in the
# paper resolves against ./repos/<name> like every other checkout; the ref is a tag, so it is fixed.
add_pinned() { # org/name ref
  local full="$1" ref="$2" name="${1#*/}" ; local dest="$CORPUS/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then echo "skip-exists $name" >>"$LOG"; return; fi
  git clone --quiet --depth 1 --branch "$ref" "https://github.com/$full.git" "$dest" >>"$LOG" 2>&1 \
    && echo "clone    $name @ $ref" >>"$LOG" || echo "FAIL     $name @ $ref" >>"$LOG"
}
add_pinned zcash/zcash v2.1.0   # §20 lineage: the depends/packages/librustzcash.mk pin fluxd inherits
echo "DONE" >>"$LOG"
