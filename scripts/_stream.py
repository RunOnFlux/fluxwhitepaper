#!/usr/bin/env python3
"""Render `claude --output-format stream-json` as readable progress, and capture cost.

Live progress matters on a run that takes tens of minutes per unit; the exact cost
matters more than anyone's estimate of it. This gives both.

    claude --print ... --output-format stream-json --verbose | python3 scripts/_stream.py OUT.json
"""
import json
import sys

out_path = sys.argv[1] if len(sys.argv) > 1 else None
result = {}

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        ev = json.loads(line)
    except ValueError:
        continue

    kind = ev.get("type")

    if kind == "assistant":
        for block in ev.get("message", {}).get("content", []):
            btype = block.get("type")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    print(text, flush=True)
            elif btype == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input", {}) or {}
                hint = (
                    inp.get("file_path")
                    or inp.get("pattern")
                    or inp.get("command")
                    or inp.get("path")
                    or ""
                )
                print(f"  · {name} {str(hint)[:110]}".rstrip(), flush=True)

    elif kind == "result":
        result = {
            "subtype": ev.get("subtype"),
            "cost_usd": ev.get("total_cost_usd"),
            "turns": ev.get("num_turns"),
            "duration_ms": ev.get("duration_ms"),
            "usage": ev.get("usage", {}),
        }
        cost = result["cost_usd"]
        mins = (result["duration_ms"] or 0) / 60000
        print(
            f"\n  → {result['subtype']} · ${cost:.2f} · {result['turns']} turns · {mins:.0f}m"
            if isinstance(cost, (int, float))
            else f"\n  → {result['subtype']}",
            flush=True,
        )

if out_path and result:
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

# Non-zero exit if the run did not succeed, so the driver can react.
sys.exit(0 if result.get("subtype") == "success" else 1)
