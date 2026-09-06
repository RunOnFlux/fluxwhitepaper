#!/usr/bin/env bash
set -u
C=TWr6yzukRwZ53HDe3bzcC8RCTbiKa4Zzb6
echo "# Tron / Kadena, retrieved $(date -u +%Y-%m-%dT%H:%M:%SZ)"
ttot=0; ok=1
for a in TSHXNnsrKGf6KAfosq5mckCnaY7gUfGwBJ TVkT9g2zzgcztm81RozqBA1UbwzZpoN8cM TA7U2PTnHDyhHBns3X6NsDndjZDBUE3oUa \
         THV8NGvAwyaL22kkhkXHVhL7JBDyxRs3BZ TNSgkA1VqiZ4KDJrVKGoy2f9TgGoNjDFWC TGwJYVkJGEnS5mWP1SE9zaiXMQ7frCzitj; do
  r=$(curl -sS --max-time 35 "https://api.trongrid.io/v1/accounts/$a" 2>/dev/null)
  b=$(printf '%s' "$r" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin); data=d.get('data',[])
    if not data: print('NA'); raise SystemExit
    for t in data[0].get('trc20',[]):
        if '$C' in t: print(int(list(t.values())[0])/1e8); break
    else: print(0)
except Exception: print('NA')")
  printf "  TRON %-36s %16s\n" "$a" "$b"
  [ "$b" = "NA" ] && ok=0 || ttot=$(python3 -c "print($ttot + ${b:-0})")
done
if [ "$ok" = "1" ]; then
  python3 -c "print(f'TRON totalSupply=440,000,000  issuer-held={$ttot:,.6f}  OUTSTANDING={440000000-$ttot:,.6f}')"
else echo "TRON: TronGrid returned no usable data without an API key"; fi
# Kadena: module has no totalSupply; per-account balance via chainweb requires per-chain queries
echo "KADENA: the Pact module exposes no total-supply function and balances are per-chain-id;"
echo "        not retrievable from a single key-free endpoint. Left unmeasured."
