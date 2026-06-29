# OSS Reputation-Farming Account Registry

**Cross-repo intelligence on the GitHub accounts farming maintainer attention — the data a single maintainer structurally cannot see.**

In 2026, AI agents flood open-source repos with PRs to farm merge/contribution reputation and chase fake "bounties." Published guides now tell you how to spot a *fake bounty repo* (red flags: <5 stars, >50 issues, `bounty` in the name, created after 2026-01-01). That is commodity knowledge, and it only flags **repos**.

This registry flags the **accounts** — and it does the one thing no single maintainer and no published checklist can do: **correlate an account's behaviour across many repos at once.**

## Why this is not self-producible

A maintainer of repo *X* only sees account *A*'s activity inside *X*. They cannot see that *A* is **simultaneously** grinding three known agent-bounty-farm operators **and** pushing PRs into `typeorm/typeorm`, `tenstorrent/tt-metal`, `FreeCAD`, and `Leantime`. That cross-repo view reframes *A*'s PR to a legit maintainer from "a contribution to review" into "near-certain reputation-farming spam" — *before* the maintainer spends review time on it.

The discovery method is **seed-and-pivot**: start from a hand-verified seed of trap operators, then pivot through the **shared farmer accounts** to surface **new operators no list contains yet**. The account graph is the proprietary asset, not any single repo.

## Public proof sample

`sample/farm_registry_SAMPLE.json` contains real, re-derivable output: 5 fully-revealed confirmed cross-operator farmer accounts (each PR-author into ≥2 independent hand-verified bounty-farm operators), plus 3 newly-discovered operator repos surfaced purely via shared-farmer co-occurrence. Every claim is re-derivable from each account's public PR history via the GitHub API — no rumor, first-hand only.

Totals behind the sample (full registry):
- **178** accounts scanned across the seed operators
- **20** confirmed cross-operator farmer accounts
- **21** new operator repos discovered via the account-pivot (none in any published list)

## What the paid maintainer report gives you

Send the GitHub repo(s) you maintain. Within 24h you get a report listing:
- **Every confirmed farmer account currently submitting PRs/issues to your repo(s)** — with its cross-operator evidence (which farm operators it also grinds, total PR volume, account age).
- A **triage ranking** so you can close/ignore the obvious farm PRs first and not waste review time.
- The relevant slice of the **operator cluster** so you can pattern-match future spam.

Reports are computed against a **weekly re-crawl** — farming is adversarial and churns, so a point-in-time scrape rots. The maintained corpus is the product.

→ **One-time maintainer report ($49):** https://buy.stripe.com/aFabJ0fCFfes9o0gYQb7y06
After paying, email the repo(s) you want checked to **johnanleitner1@gmail.com**.

For a continuously-monitored **webhook** (alert when a confirmed farmer opens a PR on your repo) or an **org-wide subscription**, email the same address.

## Method / ethics

Accounts are named here only as PR authors into ≥2 hand-verified agent-bounty-farm operators; the classification is re-derivable from public PR history. This is reporting on public, observable behaviour — not accusation of any individual's intent. Operators are flagged on first-hand evidence (their own `CONTRIBUTING.md` / issue records).

---
*Built by an operator who got baited so your repo's review queue doesn't have to be.*
