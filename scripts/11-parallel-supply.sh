#!/usr/bin/env bash
# Measure circulating supply of every FLUX parallel asset (Lambda_c), for the
# bridge conservation requirement: no migration mint may precede R0 >= Lambda.
# Public RPC only, no keys, no writes.
set -u
OUT=/Users/tadeaskmenta/repos/fluxwhitepaper/evidence/measured
mkdir -p "$OUT"
# ERC-20 totalSupply() selector
SEL=0x18160ddd
evm () { # name rpc contract
  local r
  r=$(curl -sS --max-time 40 -X POST -H 'Content-Type: application/json' \
      --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$3\",\"data\":\"$SEL\"},\"latest\"]}" "$2" 2>/dev/null)
  local hex; hex=$(printf '%s' "$r" | sed -n 's/.*"result":"0x\([0-9a-fA-F]*\)".*/\1/p')
  if [ -n "$hex" ]; then
    python3 -c "print(f'$1\t{int('$hex',16)/1e8:.8f}\t(raw {int('$hex',16)})')"
  else
    echo -e "$1\tFAIL\t$(printf '%s' "$r" | head -c 120)"
  fi
}
echo "# FLUX parallel-asset supply, retrieved $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "# EVM values assume 8 decimals (FLUX convention); verify per contract."
evm ethereum   https://eth.llamarpc.com                 0x720cd16b011b987da3518fbf38c3071d4f0d1495
evm bsc        https://bsc-dataseed.binance.org         0xaff9084f2374585879e8b434c399e29e80cce635
evm polygon    https://polygon-rpc.com                  0xA2bb7A68c46b53f6BbF6cC91C865Ae247A82E99B
evm avalanche  https://api.avax.network/ext/bc/C/rpc    0xc4B06F17ECcB2215a5DBf042C672101Fc20daF55
evm base       https://mainnet.base.org                 0xb008bdcf9cdff9da684a190941dc3dca8c2cdd44
# Solana SPL mint supply
sol=$(curl -sS --max-time 40 -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"getTokenSupply","params":["FLUX1wa2GmbtSB6ZGi2pTNbVCw3zEeKnaPCkPtFXxqXe"]}' \
  https://api.mainnet-beta.solana.com 2>/dev/null)
echo -e "solana\t$(printf '%s' "$sol" | sed -n 's/.*"uiAmountString":"\([0-9.]*\)".*/\1/p' | head -1)"
# Algorand ASA
alg=$(curl -sS --max-time 40 "https://mainnet-api.algonode.cloud/v2/assets/1029804829" 2>/dev/null)
echo -e "algorand\t$(printf '%s' "$alg" | python3 -c "import sys,json;d=json.load(sys.stdin);p=d['params'];print(p['total']/10**p['decimals'])" 2>/dev/null || echo FAIL)"
# Ergo token
erg=$(curl -sS --max-time 40 "https://api.ergoplatform.com/api/v1/tokens/e8b20745ee9d18817305f32eb21015831a48f02d40980de6e849f886dca7f807" 2>/dev/null)
echo -e "ergo\t$(printf '%s' "$erg" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('emissionAmount',0)/10**d.get('decimals',0))" 2>/dev/null || echo FAIL)"
