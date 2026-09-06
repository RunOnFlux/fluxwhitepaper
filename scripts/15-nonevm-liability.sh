#!/usr/bin/env bash
# Outstanding liability on the non-EVM parallel assets: totalSupply minus issuer-held,
# using balance-checker's registry. Public endpoints only, no keys, no writes.
set -u
MINT=FLUX1wa2GmbtSB6ZGi2pTNbVCw3zEeKnaPCkPtFXxqXe
SOLRPC=https://api.mainnet-beta.solana.com
echo "# non-EVM parallel-asset liability, retrieved $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ---- Solana: SPL balance per owner for the FLUX mint
sol_owner () {
  curl -sS --max-time 45 -X POST -H 'Content-Type: application/json' --data \
  "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getTokenAccountsByOwner\",\"params\":[\"$1\",{\"mint\":\"$MINT\"},{\"encoding\":\"jsonParsed\"}]}" \
  "$SOLRPC" 2>/dev/null | python3 -c "
import sys,json
try: d=json.load(sys.stdin)
except Exception: print(0); raise SystemExit
t=0.0
for a in d.get('result',{}).get('value',[]):
    t+=float(a['account']['data']['parsed']['info']['tokenAmount']['uiAmount'] or 0)
print(f'{t:.8f}')"
}
sup=$(curl -sS --max-time 45 -X POST -H 'Content-Type: application/json' \
  --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getTokenSupply\",\"params\":[\"$MINT\"]}" "$SOLRPC" 2>/dev/null \
  | sed -n 's/.*"uiAmountString":"\([0-9.]*\)".*/\1/p' | head -1)
tot=0
for a in 94W7UnJTBNEQSAk854NLTBgbqzSqHQNyFtQYPiGzNFaA 9dfk2Rq1MnuvjQvTsBkWvncpvQsuR8vrioFzkFG7HKvW \
         CCafnH2sUhPHitQWyFLDCe3Xqwz1Vrc2caNR6PAwkPzP 98duys57BNeYNdA4JPYzkraXe1XoUYXq5MMesx1JLsFY \
         CTUGomZr8KKQP4k8RrhrNdncMsd8zaCfuTRtAV6Fd71G 97BNByqDVXvyRPheDskRFTHKQcs56PXpdrzD9RcQwXw2; do
  b=$(sol_owner "$a"); printf "  SOL  %-46s %18s\n" "$a" "$b"
  tot=$(python3 -c "print(f'{$tot + ${b:-0}:.8f}')")
done
python3 -c "
s=float('${sup:-0}'); h=float('$tot')
print(f'SOLANA totalSupply={s:,.6f}  issuer-held={h:,.6f}  OUTSTANDING={s-h:,.6f}')"

# ---- Algorand: ASA holdings per address
ASA=1029804829
atot=0
for a in 2XAH2WI7726D5TGNXX7QBPL54PRMT4JUJZCXSAUWBJIBKC455AJ5RPEGAQ RNZZK5ZCVMOYE64EAHCABG6YRXN35SKVAW5EXKJLPZZLAIXC5NCACU22HI \
         5MG5DOGNHGGG44HO7B4JXEORSFFLBNHFNTLYYR6OW53RNNCJK2LVSJVNXA X6H5CRS2TLI4M3B4BNVW3DKC6RER7ZGOLJBGDMCUFI5NKJCT4BBSUCXRW4 \
         V7P7W2MIGGYLYR2VFX6HH74WEA6DWP4JVJMR5RMC2T6HGEB3K4WZ6DDSCE 6X2Q7AF53ESJZ7DJBEUSEGTXVRQLS6FTIZSAHKL725W6SXJOIZUNKM4IHQ; do
  b=$(curl -sS --max-time 40 "https://mainnet-api.algonode.cloud/v2/accounts/$a/assets/$ASA" 2>/dev/null \
      | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin); print(d['asset-holding']['amount']/1e8)
except Exception: print(0)")
  printf "  ALGO %-58s %14s\n" "$a" "$b"
  atot=$(python3 -c "print($atot + ${b:-0})")
done
python3 -c "print(f'ALGORAND totalSupply=440,000,000  issuer-held={$atot:,.6f}  OUTSTANDING={440000000-$atot:,.6f}')"
