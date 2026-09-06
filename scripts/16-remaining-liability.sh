#!/usr/bin/env bash
set -u
SEL=0x18160ddd
POLY_C=0xA2bb7A68c46b53f6BbF6cC91C865Ae247A82E99B
echo "# remaining chains, retrieved $(date -u +%Y-%m-%dT%H:%M:%SZ)"
# ---- Polygon: try several public RPCs
for R in https://polygon-bor-rpc.publicnode.com https://polygon.llamarpc.com https://polygon-rpc.com; do
  t=$(curl -sS --max-time 30 -X POST -H 'Content-Type: application/json' \
      --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$POLY_C\",\"data\":\"$SEL\"},\"latest\"]}" "$R" 2>/dev/null \
      | sed -n 's/.*"result":"0x\([0-9a-fA-F]*\)".*/\1/p')
  [ -n "$t" ] && { echo "polygon rpc: $R"; POLYRPC=$R; POLYSUP=$t; break; }
done
if [ -n "${POLYRPC:-}" ]; then
  tot=0
  for a in 0x25adf2050244c087fc1a27b870844ab9c1936bdf 0x208ef66cd865cc9dc862baf2be796a055d973d33 \
           0x438ad183665511d41be2c779942f6c7660710be2 0xee38530d735d485558c454268ffefe7704cc25c0 \
           0xc7b7076ca1d7971c2e27b7c4f6493d8140c2fdd0 0xd6bd199e94a9ac4dc73ce4dd4c0c02c82d6cf6c2; do
    d=$(python3 -c "print('0x70a08231'+'0'*24+'$a'.replace('0x',''))")
    h=$(curl -sS --max-time 30 -X POST -H 'Content-Type: application/json' \
        --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$POLY_C\",\"data\":\"$d\"},\"latest\"]}" "$POLYRPC" 2>/dev/null \
        | sed -n 's/.*"result":"0x\([0-9a-fA-F]*\)".*/\1/p')
    tot=$(python3 -c "print($tot + int('${h:-0}' or '0',16))")
  done
  python3 -c "
s=int('$POLYSUP',16)/1e8; h=$tot/1e8
print(f'POLYGON totalSupply={s:,.6f}  issuer-held={h:,.6f}  OUTSTANDING={s-h:,.6f}')"
else echo "POLYGON: all public RPCs refused"; fi
# ---- Ergo
etot=0
for a in 9hhRnDa1Hih5TepwqK1Zbb8SGYUbFpqTwE9G78yffudKq59xTa9 9hZ9ygGKcQ9z1oaYQEmNF53aiNQTazhBo9DFC8tQsR47a15ueGw \
         9fCKJ7g6ZffHAQb9UQY7S6YLF6dRVejBAXw284XNazkq8XLuZbw 9gtdyNTVfziFsGzH7KNjMcUj4v8MtADx4Z3prg6MWyHCCWz9NJM \
         9i24aAG4uG6NrPSqdWRk9PHzyxk472289F5o19KZMfXsdcbvXQf 9hfswHWqDMd2pLDRFCfxQWDTEjNwfsNSw6tweedZwuBe8z92ZyV; do
  b=$(curl -sS --max-time 35 "https://api.ergoplatform.com/api/v1/addresses/$a/balance/confirmed" 2>/dev/null \
      | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    for t in d.get('tokens',[]):
        if t.get('tokenId','').startswith('e8b20745'): print(t['amount']/10**t.get('decimals',8)); break
    else: print(0)
except Exception: print(0)")
  etot=$(python3 -c "print($etot + ${b:-0})")
done
python3 -c "print(f'ERGO totalSupply=440,000,000  issuer-held={$etot:,.6f}  OUTSTANDING={440000000-$etot:,.6f}')"
