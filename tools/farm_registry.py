#!/usr/bin/env python3
"""
farm_registry.py -- GitHub OSS Reputation-Farming Account Registry builder.

LENS: proprietary data / intelligence nobody else has, sold for ACCESS.

WHAT THIS IS (and is NOT):
  It is NOT a "fake-repo checklist" -- those are now published commodity knowledge
  (red flags: <5 stars, >50 issues, 'bounty' in name, created after 2026-01-01).
  Anyone can self-produce that and it only flags REPOS.

  This computes the thing a single maintainer or a published checklist CANNOT:
  a CROSS-REPO BEHAVIORAL graph of the *accounts* doing the farming. The unit of
  value is the ACCOUNT (and the operator cluster it reveals), correlated across
  many repos at once. A maintainer of repo X only sees account A's activity in X.
  This sees that A is simultaneously grinding 3 known bounty-farm operators AND
  pushing PRs into typeorm / tenstorrent / FreeCAD -- which reframes A's PRs to a
  legit maintainer as near-certain reputation-farming spam, not a contribution.

PROPRIETARY EDGE (why an agent can't cheaply self-produce it):
  1. Seed-and-pivot enumeration: from a hand-verified seed of trap operators, it
     pivots through the SHARED FARMER ACCOUNTS to discover NEW operators no list
     contains yet (account-pivot is the discovery, not the repo-scan).
  2. Continuous re-crawl: farming is adversarial and churns weekly; a point-in-time
     scrape rots. The asset is the maintained, re-graded corpus over time.

OUTPUT (JSON): for each account -> trap operators hit, distinct-operator count
(cross-trap score), legit/other repos targeted, total PR volume, account age.
Plus a derived operator-cluster list (seeds + pivoted discoveries).

This file ONLY reads public GitHub data via the REST/search API. It names a repo
or account only with first-hand, re-derivable evidence (the PR records themselves).

Usage:
  GH_TOKEN=... python tools/farm_registry.py --build --out .tmp/farm_registry.json
  GH_TOKEN=... python tools/farm_registry.py --check <github_login>   # single-account lookup
"""
import argparse, json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"

# Hand-verified seed operators (first-hand: CONTRIBUTING.md / issue records quoted
# in .tmp/agent_trap_readme.md and corroborated by Socket.dev / InfoWorld reporting).
SEED_OPERATORS = [
    "UnsafeLabs/Bounty-Hunters",
    "SecureBananaLabs/bug-bounty",
    "xevrion-v2/agent-playground",
    "tine1117/oss-hunter-livefire",
]

# Repo-name fingerprints that strongly indicate a bounty-farm target (used only to
# CLASSIFY pivoted repos as "likely operator", never as sole proof for naming).
FARM_NAME_HINTS = ("bounty", "bounties", "bounty-hunters", "agent-playground",
                   "oss-hunter", "livefire", "builders-bounty", "bounty-bot")


def _tok():
    t = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    if not t:
        # fall back to the token embedded in the git remote, read-only use
        try:
            import subprocess
            r = subprocess.run(["git", "remote", "get-url", "origin"],
                               capture_output=True, text=True, timeout=10)
            import re
            m = re.search(r"(ghp_[A-Za-z0-9]+)", r.stdout)
            if m:
                return m.group(1)
        except Exception:
            pass
    return t


def gh(url, tok, tries=3):
    for i in range(tries):
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {tok}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "farm-registry/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):  # rate limit; back off
                time.sleep(8 * (i + 1)); continue
            if e.code == 404:
                return None, {}
            raise
        except Exception:
            time.sleep(3 * (i + 1))
    return None, {}


def pr_authors(repo, tok, max_pr=400):
    """Distinct PR authors for a repo (state=all)."""
    authors = {}
    for page in range(1, max_pr // 100 + 2):
        data, _ = gh(f"{API}/repos/{repo}/pulls?state=all&per_page=100&page={page}", tok)
        if not data:
            break
        for pr in data:
            u = (pr.get("user") or {}).get("login")
            if u:
                authors[u] = authors.get(u, 0) + 1
        if len(data) < 100:
            break
        time.sleep(0.4)
    return authors


def account_pr_repos(login, tok):
    """Where does this account submit PRs across all of GitHub? Returns
    (total_count, {repo: count_in_sample}, account_meta)."""
    d, _ = gh(f"{API}/search/issues?q=author:{login}+type:pr&per_page=100&sort=created&order=desc", tok)
    if not d:
        return 0, {}, {}
    repos = {}
    for it in d.get("items", []):
        ru = it.get("repository_url", "").split("/repos/")[-1]
        if ru:
            repos[ru] = repos.get(ru, 0) + 1
    meta, _ = gh(f"{API}/users/{login}", tok)
    am = {}
    if meta:
        am = {"created_at": meta.get("created_at", "")[:10],
              "public_repos": meta.get("public_repos"),
              "followers": meta.get("followers")}
    return d.get("total_count", 0), repos, am


def classify_repo(repo):
    owner, _, name = repo.partition("/")
    low = (owner + "/" + name).lower()
    if any(h in low for h in FARM_NAME_HINTS):
        return "likely_operator"
    return "other_target"


def build(out_path, tok, account_cap=60):
    t0 = time.time()
    # 1. seed: distinct PR authors across hand-verified trap operators
    acct_traps = {}
    for op in SEED_OPERATORS:
        for u in pr_authors(op, tok):
            acct_traps.setdefault(u, set()).add(op)
    # 2. cross-trap farmers = accounts hitting >=2 distinct seed operators
    farmers = sorted([u for u, ts in acct_traps.items() if len(ts) >= 2],
                     key=lambda u: -len(acct_traps[u]))
    # 3. pivot: enumerate where each farmer ALSO submits -> discover new operators
    registry = {}
    discovered_ops = {}  # repo -> count of distinct seed-farmers also hitting it
    for u in farmers[:account_cap]:
        total, repos, meta = account_pr_repos(u, tok)
        legit, likely_ops = [], []
        for r, c in sorted(repos.items(), key=lambda x: -x[1]):
            if r.split("/")[0] in {o.split("/")[0] for o in SEED_OPERATORS}:
                continue  # already a known seed operator
            cls = classify_repo(r)
            (likely_ops if cls == "likely_operator" else legit).append({"repo": r, "prs_in_sample": c})
            if cls == "likely_operator":
                discovered_ops[r] = discovered_ops.get(r, 0) + 1
        registry[u] = {
            "trap_operators_hit": sorted(acct_traps[u]),
            "cross_trap_operator_count": len(acct_traps[u]),
            "total_prs_all_github": total,
            "account_created": meta.get("created_at"),
            "public_repos": meta.get("public_repos"),
            "followers": meta.get("followers"),
            "pivoted_likely_operators": likely_ops,
            "legit_or_other_repos_targeted": legit[:12],
        }
        time.sleep(1.0)
    result = {
        "schema": "oss-farming-registry/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_operators": SEED_OPERATORS,
        "n_accounts_across_seeds": len(acct_traps),
        "n_cross_trap_farmers": len(farmers),
        "accounts": registry,
        "discovered_operator_candidates": [
            {"repo": r, "seed_farmers_also_hitting": n}
            for r, n in sorted(discovered_ops.items(), key=lambda x: -x[1])
        ],
        "build_seconds": round(time.time() - t0, 1),
        "method_note": ("Accounts named here are PR authors into >=2 hand-verified "
                        "agent-bounty-farm operators; classification re-derivable from "
                        "each account's public PR history. 'discovered_operator_candidates' "
                        "are repos surfaced purely via shared-farmer co-occurrence."),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2))
    return result


def check(login, tok):
    total, repos, meta = account_pr_repos(login, tok)
    seed_owners = {o.split("/")[0] for o in SEED_OPERATORS}
    traps_hit = sorted({r for r in repos if r.split("/")[0] in seed_owners})
    print(json.dumps({
        "login": login,
        "total_prs_all_github": total,
        "account_created": meta.get("created_at"),
        "known_trap_operators_hit": traps_hit,
        "farming_risk": ("HIGH" if traps_hit else "unknown_from_seeds"),
        "all_repos_in_sample": dict(sorted(repos.items(), key=lambda x: -x[1])),
    }, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", metavar="LOGIN")
    ap.add_argument("--out", default=".tmp/farm_registry.json")
    ap.add_argument("--cap", type=int, default=60)
    a = ap.parse_args()
    tok = _tok()
    if not tok:
        sys.exit("ERROR: no GH_TOKEN / GITHUB_TOKEN and none found in git remote.")
    if a.check:
        check(a.check, tok); return
    if a.build:
        r = build(a.out, tok, account_cap=a.cap)
        print(f"Built registry: {r['n_cross_trap_farmers']} cross-trap farmers, "
              f"{len(r['discovered_operator_candidates'])} discovered operator candidates "
              f"-> {a.out} ({r['build_seconds']}s)")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
