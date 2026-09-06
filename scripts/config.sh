# Shared config for the scanner. Edit this, not the scripts.

# Repos that are CORE no matter what the score says (bare names, any org).
PIN_CORE="flux fluxd zelcash zelcashd fluxos fluxbench zelbench flux-domain-manager
Flux-Shared-DB fluxos-frontend fluxstats fluxnode-multitool pouwbackend
flux-network-history fluxjsdocs flux-roadmap fluxos-network-policy"

# Repos to always drop regardless of score.
PIN_SKIP=""

# Name patterns that are almost always deployment/marketing template noise.
NOISE_RE='(?:-server-website$|-website$|^website|-landing$|^docs-|^demo-|-demo$|^test-|-test$|^example|-example$|^template|-template$|^\.github$|^homepage$)'

# Keywords in name/description/topics that pull a repo toward the paper's subject.
# EDIT THESE to match thesis.md — this is the main relevance lever.
SIGNAL_RE='(?:consensus|daemon|blockchain|node|collateral|reward|tier|stake|
p2p|network|benchmark|orchestrat|docker|deploy|scal|shard|database|dns|
proof|pow|pos|mining|wallet|multisig|sign|key|relay|api|monitor|storage|
gateway|registry|bridge|token|economics|governance)'

CLONE_DIR="repos"
LOCAL_REPO_HINT="$HOME/repos"   # reuse checkouts already on disk instead of cloning
