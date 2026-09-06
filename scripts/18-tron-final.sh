#!/usr/bin/env bash
# Tron FLUX (TRC-20) issuer-held balance via Tronscan (no API key required).
# Issuer registry: balance-checker/config/default.js
set -uo pipefail
C=TWr6yzukRwZ53HDe3bzcC8RCTbiKa4Zzb6
for a in TSHXNnsrKGf6KAfosq5mckCnaY7gUfGwBJ TVkT9g2zzgcztm81RozqBA1UbwzZpoN8cM \
         TA7U2PTnHDyhHBns3X6NsDndjZDBUE3oUa THV8NGvAwyaL22kkhkXHVhL7JBDyxRs3BZ \
         TNSgkA1VqiZ4KDJrVKGoy2f9TgGoNjDFWC TGwJYVkJGEnS5mWP1SE9zaiXMQ7frCzitj; do
  v=$(curl -s --max-time 25 "https://apilist.tronscan.org/api/account?address=$a" \
      | python3 -c "
import sys,json
try:
  d=json.load(sys.stdin)
  for t in d.get('trc20token_balances',[]) or []:
    if t.get('tokenId')=='$C':
      print(int(t.get('balance',0))/10**int(t.get('tokenDecimal',8))); break
  else: print('0')
except Exception: print('NA')")
  echo "$a $v"
  sleep 1
done
