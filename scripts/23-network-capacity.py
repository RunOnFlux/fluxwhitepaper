#!/usr/bin/env python3
"""Fleet capacity: what the tiers provide, and what FluxOS lets applications have.

Two different quantities, both from flux/ZelBack/config/default.js:380-395
(`fluxSpecifics`), against the 2026-09-03 tier census:

  TOTAL   -- the tier's declared allocation. CPU is in tenths of a vCPU thread,
             so cumulus 40 is 4.0 threads, not 4 physical cores; fluxbench's
             separate minimum (benchmarks.h:58-84) states cumulus as 2 cores /
             4 threads, which is the same machine counted the other way.
  USABLE  -- what the same config records as available to applications after
             node overhead, in the per-line comments ("30 available for apps").

Storage carries a third, stricter number at runtime: hwRequirements.js:385
computes useable = total * 0.95 - lockedSystemResources.hdd(60) - extrahdd(20),
which for a 220 GB cumulus is 129 GB, not the 180 GB the tier line records.
Both are printed; the runtime figure is the one a deployment actually meets.

    python3 scripts/23-network-capacity.py
"""
CENSUS = {"Cumulus": 3247, "Nimbus": 1615, "Stratus": 1627}
# tier -> (cpu_tenths_total, cpu_tenths_apps, ram_mb_total, ram_mb_apps, hdd_gb_total, hdd_gb_apps)
SPEC = {
    "Cumulus": (40,  30,  7000,  5000, 220, 180),
    "Nimbus":  (80,  70, 30000, 28000, 440, 400),
    "Stratus": (160, 150, 61000, 59000, 880, 840),
}
LOCKED_HDD, EXTRA_HDD, DISK_FACTOR = 60, 20, 0.95

tot = dict.fromkeys(("n", "cpu", "cpu_a", "ram", "ram_a", "hdd", "hdd_a", "hdd_rt"), 0)
print(f"{'tier':<9}{'nodes':>6}{'vCPU':>9}{'vCPU app':>10}{'RAM GB':>9}{'RAM app':>9}"
      f"{'HDD GB':>10}{'HDD app':>10}{'HDD rt':>10}")
for t, n in CENSUS.items():
    c, ca, r, ra, h, ha = SPEC[t]
    rt = max(0.0, h * DISK_FACTOR - LOCKED_HDD - EXTRA_HDD)     # hwRequirements.js:385
    row = (n, n*c/10, n*ca/10, n*r/1000, n*ra/1000, n*h, n*ha, n*rt)
    print(f"{t:<9}{n:>6}{row[1]:>9,.0f}{row[2]:>10,.0f}{row[3]:>9,.0f}{row[4]:>9,.0f}"
          f"{row[5]:>10,.0f}{row[6]:>10,.0f}{row[7]:>10,.0f}")
    for k, v in zip(("n","cpu","cpu_a","ram","ram_a","hdd","hdd_a","hdd_rt"), row):
        tot[k] += v

print(f"{'Total':<9}{tot['n']:>6}{tot['cpu']:>9,.0f}{tot['cpu_a']:>10,.0f}"
      f"{tot['ram']:>9,.0f}{tot['ram_a']:>9,.0f}{tot['hdd']:>10,.0f}"
      f"{tot['hdd_a']:>10,.0f}{tot['hdd_rt']:>10,.0f}")
print(f"\n  total   : {tot['cpu']:,.0f} vCPU · {tot['ram']/1024:.1f} TiB RAM · "
      f"{tot['hdd']/1e6:.2f} PB storage")
print(f"  usable  : {tot['cpu_a']:,.0f} vCPU · {tot['ram_a']/1024:.1f} TiB RAM · "
      f"{tot['hdd_a']/1e6:.2f} PB storage   (tier lines)")
print(f"  storage at the runtime check: {tot['hdd_rt']/1e6:.2f} PB "
      f"({100*tot['hdd_rt']/tot['hdd']:.0f}% of total)")
