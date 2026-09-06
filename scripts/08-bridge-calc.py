# Computation log for plan/mech-bridge.md. All inputs are task-given or from evidence/*.md.
from math import comb, exp, factorial, log2, ceil

print("== A. Fleet and collateral (task-given counts; evidence/_measured_network.md shows 6,489 / 3,247, one-node drift) ==")
N = 6488; nC, nN, nS = 3246, 1615, 1627
cC, cN, cS = 1000, 12500, 40000           # V2 collateral, fluxd fluxnode.h:57-63
assert nC+nN+nS == N
tot_coll = nC*cC + nN*cN + nS*cS
print(f"N = {N}; total collateral = {tot_coll:,} FLUX")
maj = N//2 + 1
print(f"node-count majority = {maj:,} nodes; cheapest (all Cumulus) = {maj*cC:,} FLUX = {maj*cC/tot_coll:.2%} of standing collateral")
print(f"per-slot per-node eligibility q ~ 1/N = {1/N:.6f}  (uniform sortition, one hash per node per slot)")

print("\n== B. Reorg race under PoN (block-count race, fixed 2^40 chainwork/blk; Nakamoto catch-up with q = attacker's share of slot wins) ==")
def catchup(qshare, z):
    p = 1-qshare; q = qshare
    lam = z*q/p
    s = 0.0
    for k in range(z+1):
        pois = lam**k * exp(-lam) / factorial(k)
        s += pois * (1 - (q/p)**(z-k))
    return 1-s
def slot_share(frac):   # attacker per-slot win prob a vs honest h, given share of nodes
    q = 1/N
    a = 1-(1-q)**(frac*N); h = 1-(1-q)**((1-frac)*N)
    return a/(a+h)
print("attacker node share -> per-slot share of blocks; P(catch up) at depth z in {6,20,40}; cost at Cumulus price")
for frac in (0.05,0.10,0.20,0.30,0.40,0.45):
    qs = slot_share(frac)
    nodes = ceil(frac*N)
    print(f"  {frac:>4.0%} ({nodes:>5,} nodes, {nodes*cC:>12,} FLUX): q={qs:.3f}; z=6 {catchup(qs,6):.2e}; z=20 {catchup(qs,20):.2e}; z=40 {catchup(qs,40):.2e}")
print("MAX_REORG_LENGTH = 40 blocks (fluxd main.h:74) -> 40 x 30 s = %d s = %.0f min; reorg > 40 rejected by consensus" % (40*30, 40*30/60))

print("\n== C. Finality latencies ==")
eth_fin = 2*32*12
print(f"Ethereum Casper-FFG finality: 2 epochs x 32 slots x 12 s = {eth_fin} s = {eth_fin/60:.1f} min (protocol constant; sometimes 3 epochs in practice = {3*32*12/60:.1f} min)")
print(f"Flux L1 D_L1 = 40 blocks -> {40*30/60:.0f} min; D_L1 = 100 blocks (COINBASE_MATURITY) -> {100*30/60:.0f} min")
print(f"Solana finalized commitment ~ 32 slots x 400 ms = {32*0.4:.1f} s (nominal; open parameter)")
print("BSC fast finality: depth is a deploy-time open parameter (BEP-126); not fixed here")

print("\n== D. k-of-n: theft vs censorship thresholds ==")
print(" n   k   steal(k)  censor(n-k+1)  k/n")
for n,k in ((5,3),(7,5),(9,6),(11,8),(15,10),(15,11),(21,14),(31,21),(51,34)):
    print(f"{n:>2}  {k:>2}   {k:>5}      {n-k+1:>6}       {k/n:.2f}")

print("\n== E. Audited Schnorr AA account (MultiSigSmartAccount) X-of-Y = enumerated combined addresses: sum_{j>=k} C(n,j) ==")
for n,k in ((3,2),(5,3),(7,5),(9,6),(11,8),(15,10)):
    cnt = sum(comb(n,j) for j in range(k,n+1))
    print(f"  n={n:>2} k={k:>2}: {cnt:>6,} OWNER_ROLE grants at initialize (each ~25k gas SSTORE -> ~{cnt*25_000/1e6:,.1f}M gas)")

print("\n== F. L1 release tx sizing (P2SH k-of-n, compressed keys) ==")
def p2sh_input_bytes(k,n):
    redeem = 1 + n*34 + 1 + 1          # OP_k, n x (push33 + 33B), OP_n, OP_CHECKMULTISIG
    scriptsig = 1 + k*(1+72) + 3 + redeem   # OP_0, k sigs (push+~72B), pushdata for redeem
    return 36 + 1 + scriptsig + 4     # outpoint, varint, scriptSig, sequence
MAX_TX = 2_000_000                    # MAX_TX_SIZE_AFTER_SAPLING = MAX_BLOCK_SIZE
for k,n in ((2,3),(5,7),(9,15),(11,15),(15,15)):
    ib = p2sh_input_bytes(k,n)
    print(f"  {k}-of-{n}: redeemScript {1+n*34+2} B (standardness cap 520 B -> n<=15), input ~{ib} B, max inputs/tx ~{MAX_TX//ib:,}; 1,000 releases x 34 B out + 1 OP_RETURN = {1000*34+45+10} B")
print("  consensus cap on OP_CHECKMULTISIG pubkeys = 20; standardness (520 B redeemScript) -> 15 compressed keys")

print("\n== G. Integer bounds: 8 decimals on every chain so 1 unit = 1 sat ==")
mm = 440_000_000 * 10**8
print(f"MAX_MONEY in sat = {mm:,} = 2^{log2(mm):.1f}; u64 max = {2**64-1:,}; fits: {mm < 2**63}")
print(f"u64 headroom: {2**64/10**8:,.0f} FLUX representable; uint256 irrelevant on EVM")
print(f"current issued supply (emission model, h=2,912,015) = 429,466,823.97 FLUX = {int(429_466_823.97*10**8):,} sat")

print("\n== H. Attestation cadence and on-chain cost if posted to Ethereum every L1 block ==")
per_day = 86400//30
for k in (5,9,15):
    gas = 21_000 + 45_000 + k*6_000      # base + storage of tuple + k x (ecrecover 3k + calldata/overhead)
    print(f"  k={k:>2}: ~{gas:,} gas/attestation x {per_day:,}/day = {gas*per_day/1e6:,.0f}M gas/day  (vs ~36M gas per Ethereum block)")
print("  -> continuous attestation must be off-chain-published; only PAUSE goes on-chain")

print("\n== I. Damage bound under full mint-quorum compromise: loss <= rho_c * ceil(T_react/T_epoch) (+ in-flight) ==")
for T_react_h in (1,6,24,72):
    for T_epoch_h in (24,):
        print(f"  T_react={T_react_h:>2} h, T_epoch={T_epoch_h} h: loss <= {ceil(T_react_h/T_epoch_h)} x rho_c   (if boundary crossed: {ceil(T_react_h/T_epoch_h)+1} x rho_c)")
print("  illustration only (rho open): rho_c = 1% of kappa_c per day -> full drain takes 100 epochs; incumbent bound = entire hot-wallet balance, no epoch")

print("\n== J. Bond condition: k_att * beta_att > rho_c * ceil(T_react/T_epoch); illustrative bonds = tier collateral ==")
for k in (5,9,15):
    for b in (cC,cN,cS):
        print(f"  k_att={k:>2}, beta_att={b:>6,} FLUX: collusion forfeits {k*b:>9,} FLUX -> rho_c per epoch must be < {k*b:,} for a 1-epoch reaction to be unprofitable")

print("\n== K. Migration surface ==")
legacy = ["Ethereum","BNB Chain","Polygon","Avalanche C","Base","Solana","Algorand","Ergo","Tron","Kadena"]
print(f"legacy contracts retired = {len(legacy)} (all ten, incl. legacy ETH/BSC/SOL); new deployments = 2 at launch + 1 later = 3")
print(f"incumbent hot keys = 11 chains x 3 roles = {11*3}; incumbent claim scripts ~130, claim functions ~40")
print(f"90-day notice precedent (roadmap md:159) = {90*2880:,} L1 blocks")
print(f"Ethereum 'Flux' legacy contract minted 440,000,000 at deploy (flux.sol:8) on EACH EVM chain -> 5 EVM chains x 440M = {5*440_000_000:,} pre-minted, unbacked by construction")
