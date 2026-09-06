#!/usr/bin/env bash
# Queries totalSupply() and balanceOf() for every issuer-held FLUX parallel-asset
# address, per chain, using ONLY public RPC endpoints (no API keys).
#
# Address set = the "current" (post-rotation) addresses in
#   balance-checker/config/default.js  (authoritative registry, see
#   evidence/_issuer_addresses.md). Six roles per EVM chain: SNAPSHOT, MINING,
#   SWAP, LOCKED, LOCKED SNAPSHOT, LOCKED MINING. All are issuer/Fusion-controlled
#   operational or reserve wallets, i.e. none of them are "circulating".
#
# The FEES address (0x9b77c6af70878c5c748d0ab456dcac1dfc01f962) appears ONLY in
# flux-supply-tracker/index.html, not in balance-checker. It is queried
# separately and NOT added to the primary issuer-held sum, since the
# authoritative registry does not confirm it. See evidence file for details.
#
# Usage: ./13-issuer-balances.sh | tee ../evidence/measured/issuer_balances.txt
set -u

BALOF=0x70a08231
TOTALSUPPLY=0x18160ddd
FEES=0x9b77c6af70878c5c748d0ab456dcac1dfc01f962

call() { # rpc contract data  (3 attempts, 2s backoff, tolerates transient public-RPC rate limiting)
  local rpc="$1" contract="$2" data="$3" out="" attempt
  for attempt in 1 2 3; do
    out=$(curl -sS --max-time 30 -X POST -H 'Content-Type: application/json' \
      --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$contract\",\"data\":\"$data\"},\"latest\"]}" \
      "$rpc" 2>/dev/null | sed -n 's/.*"result":"0x\([0-9a-fA-F]*\)".*/\1/p')
    [ -n "$out" ] && break
    sleep 2
  done
  echo "$out"
}
balcall() { python3 -c "print('0x70a08231'+'0'*24+'$1'.lower().replace('0x',''))"; }

# chain name, rpc, contract, then 6 "label:address" pairs (current / post-rotation)
chain() {
  local name="$1" rpc="$2" contract="$3"; shift 3
  echo "== $name =="
  echo "   contract: $contract"
  echo "   rpc:      $rpc"

  local ts_hex; ts_hex=$(call "$rpc" "$contract" "$TOTALSUPPLY")
  local ts_ok=1
  if [ -z "$ts_hex" ]; then ts_ok=0; echo "   totalSupply: RPC FAIL"; fi

  local sum=0 missing=0 rows=""
  for pair in "$@"; do
    local label="${pair%%:*}" addr="${pair#*:}"
    local h; h=$(call "$rpc" "$contract" "$(balcall "$addr")")
    if [ -z "$h" ]; then
      echo "   $label ($addr): RPC FAIL"
      missing=1
      continue
    fi
    rows="$rows $label:$h"
    sum=$(python3 -c "print($sum + int('${h}' or '0', 16))")
    sleep 1   # space out requests; public RPCs (esp. mainnet.base.org) rate-limit bursts
  done

  # FEES probe (unverified address, not part of issuer-held sum)
  local fees_hex; fees_hex=$(call "$rpc" "$contract" "$(balcall "$FEES")")

  python3 - "$name" "$ts_ok" "${ts_hex:-0}" "$sum" "$missing" "${fees_hex:-}" <<'PY'
import sys
name, ts_ok, ts_hex, issuer_sum, missing, fees_hex = sys.argv[1:7]
D = 1e8  # FLUX uses 8 decimals
ts_ok = ts_ok == "1"
ts = int(ts_hex, 16) if ts_hex else 0
issuer = int(issuer_sum)
missing = missing == "1"

for lbl_hex in []:
    pass

print(f"   issuer-held (sum of 6 roles) = {issuer/D:>18,.8f} FLUX" + (" [INCOMPLETE - one or more addresses FAILED]" if missing else ""))
if fees_hex:
    fees = int(fees_hex, 16)
    print(f"   FEES addr (unverified, not counted) = {fees/D:>10,.8f} FLUX")
else:
    print("   FEES addr (unverified, not counted) = RPC FAIL")

if not ts_ok:
    print("   totalSupply UNAVAILABLE -> cannot compute outstanding liability for this chain")
else:
    liability = ts - issuer
    bound = " (lower bound only; one or more issuer addresses FAILED to resolve)" if missing else ""
    print(f"   totalSupply                  = {ts/D:>18,.8f} FLUX")
    print(f"   outstanding liability         = {liability/D:>18,.8f} FLUX{bound}")
PY
  echo
}

echo "# FLUX issuer-held balances and outstanding liability"
echo "# retrieved $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "# issuer-held = SNAPSHOT + MINING + SWAP + LOCKED + LOCKED-SNAPSHOT + LOCKED-MINING"
echo "#   (current/post-rotation addresses from balance-checker/config/default.js)"
echo "# FEES address is queried but NOT included (not present in balance-checker)"
echo

chain ethereum https://ethereum-rpc.publicnode.com 0x720cd16b011b987da3518fbf38c3071d4f0d1495 \
  "SNAPSHOT:0x5a2387883bc5e875e09d533eef812b2da30f2615" \
  "MINING:0x342c34702929849b6deaa47496d211cbe4167fa5" \
  "SWAP:0x134e4c74c670adefdcb2476df6960d9297bc7dad" \
  "LOCKED:0x3d1759846bbbdeb7f71558d1fc6f00916006a795" \
  "LOCKED-SNAPSHOT:0x5a2e9f076ba06bae75d2bb6586139b95055ceeb4" \
  "LOCKED-MINING:0x1b9f4e3805119de9615d821ebfd83ac57cfb10ce"

chain bsc https://bsc-dataseed.binance.org 0xaff9084f2374585879e8b434c399e29e80cce635 \
  "SNAPSHOT:0x4004755e538b77f80004b0f9b7f7df4e9793e584" \
  "MINING:0x8cb191750096ddc8f314c2de6ef28331503774e9" \
  "SWAP:0x9b192227da99b5a50d037b10c965609ed83c43d7" \
  "LOCKED:0x0fc9fe8c3aa97f298700ad2df58e1476dc033b61" \
  "LOCKED-SNAPSHOT:0x1e1f3d2517c97295f68836f154f531049a9b133a" \
  "LOCKED-MINING:0xbfb2181c9480f911e288fa14b5d71f9db9795bf3"

chain avalanche https://api.avax.network/ext/bc/C/rpc 0xc4B06F17ECcB2215a5DBf042C672101Fc20daF55 \
  "SNAPSHOT:0x1F3b258e0ff097FC4E25B827401D10fDeAa71fC5" \
  "MINING:0x8967d37E297f6f6ede242d51783917eb07fDE293" \
  "SWAP:0xe0d28bc942B7B0b9A513F92a2fCef2bdF0377619" \
  "LOCKED:0xBdB587D89929b3188325643800f8f789Bf72FF53" \
  "LOCKED-SNAPSHOT:0x2599C465F0290237954E04550dA8cf8c94644e29" \
  "LOCKED-MINING:0xc926CbFCbF9313E6530e3342Ee1556ce5D2c0da9"

chain base https://mainnet.base.org 0xb008bdcf9cdff9da684a190941dc3dca8c2cdd44 \
  "SNAPSHOT:0xdcc46899f137e7eb82437b230898dabaf3d73046" \
  "MINING:0xe91b74d3c716ce77179384916f3c1700942226cc" \
  "SWAP:0x98f17e2d8c09f637a236d067191e0d11656a7df0" \
  "LOCKED:0x7f5f9cd4c4c67c3f80ed74e0e1fb9e3d7975a479" \
  "LOCKED-SNAPSHOT:0xe05fb97b601fb036bc7b75fcb1c8027193213af5" \
  "LOCKED-MINING:0xd86292b7e8d3ca5ddc474feaf46455bfa55ae36b"
