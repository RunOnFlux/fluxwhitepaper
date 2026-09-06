#!/usr/bin/env bash
# For each EVM parallel asset: totalSupply, and the balance held at the addresses
# the team's two supply tools treat as reserve. The difference between the two
# lists is the ambiguity in Lambda_c, the liability a bridge migration must back.
set -u
LOCKED=0x3d1759846bbbdeb7f71558d1fc6f00916006a795
FEES=0x9b77c6af70878c5c748d0ab456dcac1dfc01f962
BOTH="0x134e4c74c670adefdcb2476df6960d9297bc7dad 0x5a2387883bc5e875e09d533eef812b2da30f2615 0x342c34702929849b6deaa47496d211cbe4167fa5 0x5a2e9f076ba06bae75d2bb6586139b95055ceeb4 0x1b9f4e3805119de9615d821ebfd83ac57cfb10ce"
call () { curl -sS --max-time 30 -X POST -H 'Content-Type: application/json' \
  --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$2\",\"data\":\"$3\"},\"latest\"]}" "$1" 2>/dev/null \
  | sed -n 's/.*"result":"0x\([0-9a-fA-F]*\)".*/\1/p'; }
balcall () { python3 -c "print('0x70a08231'+'0'*24+'$1'.lower().replace('0x',''))"; }
chain () { # name rpc contract
  local ts; ts=$(call "$2" "$3" 0x18160ddd); [ -z "$ts" ] && { echo "$1: RPC FAIL"; return; }
  local locked fees both=0
  locked=$(call "$2" "$3" "$(balcall $LOCKED)"); fees=$(call "$2" "$3" "$(balcall $FEES)")
  for a in $BOTH; do
    h=$(call "$2" "$3" "$(balcall $a)")
    both=$(python3 -c "print($both + int('${h:-0}' or '0',16))")
  done
  python3 - "$1" "${ts:-0}" "${locked:-0}" "${fees:-0}" "$both" <<'PY'
import sys
name,ts,locked,fees,both = sys.argv[1], int(sys.argv[2],16), int(sys.argv[3] or '0',16), int(sys.argv[4] or '0',16), int(sys.argv[5])
D=1e8
tracker = both+locked+fees
print(f"{name:10} totalSupply={ts/D:>15,.2f}  locked={locked/D:>15,.2f}  shared_reserve={both/D:>12,.2f}")
print(f"{'':10} circulating per flux-supply-tracker = {(ts-tracker)/D:>15,.2f}")
print(f"{'':10} circulating per fluxstats           = {(ts-both)/D:>15,.2f}")
print(f"{'':10} AMBIGUITY (the disputed amount)     = {(locked+fees)/D:>15,.2f}")
PY
}
echo "# FLUX parallel-asset liability, retrieved $(date -u +%Y-%m-%dT%H:%M:%SZ)"
chain ethereum  https://ethereum-rpc.publicnode.com    0x720cd16b011b987da3518fbf38c3071d4f0d1495
chain bsc       https://bsc-dataseed.binance.org       0xaff9084f2374585879e8b434c399e29e80cce635
chain avalanche https://api.avax.network/ext/bc/C/rpc  0xc4B06F17ECcB2215a5DBf042C672101Fc20daF55
chain base      https://mainnet.base.org               0xb008bdcf9cdff9da684a190941dc3dca8c2cdd44
