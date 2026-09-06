#!/usr/bin/env bash
# Pass 0a: pull repo metadata from GitHub. No cloning, no model tokens.
set -euo pipefail
cd "$(dirname "$0")/.."
ORGS="${ORGS:-RunOnFlux zelcash}"
mkdir -p out
: > out/inventory.json.tmp
for org in $ORGS; do
  echo "fetching $org ..." >&2
  gh repo list "$org" --limit 1000 --json \
    name,description,isFork,isArchived,pushedAt,createdAt,primaryLanguage,stargazerCount,repositoryTopics,diskUsage,url \
  | jq --arg org "$org" '[.[] | . + {org:$org, full:($org+"/"+.name)}]' >> out/inventory.json.tmp
done
jq -s 'add | unique_by(.full)' out/inventory.json.tmp > out/inventory.json
rm -f out/inventory.json.tmp
jq -r '["repo","pushed","stars","lang","kb","description"], (.[] | [.full,.pushedAt[0:10],.stargazerCount,(.primaryLanguage.name//"-"),(.diskUsage//0),((.description//"")|.[0:80])]) | @tsv' \
  out/inventory.json > out/inventory.tsv
echo "total: $(jq length out/inventory.json) repos -> out/inventory.json / out/inventory.tsv"
