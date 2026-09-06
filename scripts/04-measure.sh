#!/usr/bin/env bash
# Snapshot the live public Flux API for §25. Every figure in the paper cites endpoint + date.
set -u
D="/Users/tadeaskmenta/repos/fluxwhitepaper/evidence/measured"
STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
fetch() { curl -sS --max-time 180 "$1" -o "$2" && echo "ok $2 ($(du -h "$2"|cut -f1))" || echo "FAIL $1"; }
fetch https://api.runonflux.io/daemon/getzelnodecount        "$D/getzelnodecount.json"
fetch https://api.runonflux.io/apps/deploymentinformation    "$D/deploymentinformation.json"
fetch https://api.runonflux.io/apps/globalappsspecifications "$D/globalappsspecifications.json"
fetch https://api.runonflux.io/daemon/getinfo                "$D/getinfo.json"
fetch https://api.runonflux.io/daemon/getblockchaininfo      "$D/getblockchaininfo.json"
fetch https://api.runonflux.io/daemon/getzelnodestatus       "$D/getzelnodestatus.json"
fetch https://api.runonflux.io/flux/info                     "$D/fluxinfo.json"
fetch https://api.runonflux.io/apps/fluxusage                "$D/fluxusage.json"
fetch https://api.runonflux.io/daemon/listzelnodes           "$D/listzelnodes.json"
echo "$STAMP" > "$D/RETRIEVED_AT"
