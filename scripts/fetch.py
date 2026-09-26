"""Fetch public GitHub data for the profile into data/github.json.

Tokens (never printed):
  GITHUB_TOKEN        public data (in Actions: the workflow token). Locally falls back to `gh auth token`.
  PROFILE_READ_TOKEN  optional, owner-created, read-only. When it works (it authenticates as the
                      profile owner) and profile.yml allows it, the shipping-signal counts include
                      private work. Only counts are kept: no repository names or details are stored.

Every shipping-signal number records its source in `signal.sources`. A number that cannot be
established from public data (for example when the local token is the owner's and private
contributions would leak into the count) is left out, never estimated.

The output has a stable key order and no fetch timestamps, so unchanged data produces an
unchanged file and the workflow makes no commit. `last_changed` moves only when data moves.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "github.json"
API = "https://api.github.com"

CONTRIB_QUERY = """
query($login:String!){ user(login:$login){
  contributionsCollection{
    contributionCalendar{ totalContributions
      weeks{ contributionDays{ date contributionCount } } }
    commitContributionsByRepository(maxRepositories:100){ repository{ id isPrivate } }
    issueContributionsByRepository(maxRepositories:100){ repository{ id isPrivate } }
    pullRequestContributionsByRepository(maxRepositories:100){ repository{ id isPrivate } }
    pullRequestReviewContributionsByRepository(maxRepositories:100){ repository{ id isPrivate } }
    repositoryContributions(first:100){ nodes{ repository{ id isPrivate } } } } } }
"""

# Language colours for the cards/bar (REST /languages has bytes but no colours).
COLOR_QUERY = """
query($login:String!){ user(login:$login){
  repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC){
    nodes{ name languages(first:20){ nodes{ name color } } } } } }
"""


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sys.exit("fetch: set GITHUB_TOKEN (or log in with gh).")


def request(url: str, tok: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "hunainx-profile-refresh")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:  # message only; never the token
        sys.exit(f"fetch: {req.get_method()} {url} -> HTTP {e.code}")


def graphql(query: str, login: str, tok: str) -> dict:
    res = request(f"{API}/graphql", tok, {"query": query, "variables": {"login": login}})
    if res.get("errors"):
        sys.exit(f"fetch: GraphQL error: {res['errors'][0].get('message', 'unknown')}")
    return res["data"]["user"]


def viewer_login(tok: str) -> str:
    """Who the token authenticates as; "" when the API won't say (e.g. an Actions token)."""
    req = urllib.request.Request(f"{API}/graphql", data=json.dumps({"query": "{ viewer { login } }"}).encode(), method="POST")
    for k, v in (("Authorization", f"Bearer {tok}"), ("User-Agent", "hunainx-profile-refresh")):
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return ((json.loads(resp.read().decode()).get("data") or {}).get("viewer") or {}).get("login") or ""
    except (urllib.error.URLError, ValueError):
        return ""


def calendar(cc: dict) -> dict:
    cal = cc["contributionCalendar"]
    return {
        "total_12mo": cal["totalContributions"],
        "weeks": [
            {"start": w["contributionDays"][0]["date"],
             "count": sum(d["contributionCount"] for d in w["contributionDays"]),
             "days": [d["contributionCount"] for d in w["contributionDays"]]}
            for w in cal["weeks"][-52:]
        ],
    }


def contributed_repos(cc: dict) -> list[tuple[str, bool]]:
    """(opaque id, is_private) of every repository with a contribution in the window. Ids are
    only used to count distinct repositories and are never written out."""
    seen = {}
    for key in ("commitContributionsByRepository", "issueContributionsByRepository",
                "pullRequestContributionsByRepository", "pullRequestReviewContributionsByRepository"):
        for item in cc[key]:
            seen[item["repository"]["id"]] = item["repository"]["isPrivate"]
    for node in cc["repositoryContributions"]["nodes"]:
        seen[node["repository"]["id"]] = node["repository"]["isPrivate"]
    return sorted(seen.items())


def signal(login: str, tok: str, private_tok: str | None, allow_private: bool) -> tuple[dict, dict | None]:
    """Shipping-signal counts with their sources, and the public calendar (None when it can't be
    shown to be public)."""
    cc = graphql(CONTRIB_QUERY, login, tok)["contributionsCollection"]
    repos = contributed_repos(cc)
    # A public-view token sees public contributions only. The owner's own token (a local run) also
    # sees private ones, so its calendar counts as public only when no private repository is in it.
    owner_view = viewer_login(tok).lower() == login.lower()
    public_calendar = not owner_view or not any(p for _, p in repos)
    out: dict = {"mode": "public", "sources": {}}

    if private_tok and allow_private:
        if viewer_login(private_tok).lower() == login.lower():   # the token works and is the owner's
            occ = graphql(CONTRIB_QUERY, login, private_tok)["contributionsCollection"]
            src = "PROFILE_READ_TOKEN: GraphQL contributionsCollection, owner view (public and private, counts only)"
            out.update(mode="profile_read_token", contributions_12mo=occ["contributionCalendar"]["totalContributions"],
                       repos_contributed_12mo=len(contributed_repos(occ)))
            out["sources"] = {"contributions_12mo": src, "repos_contributed_12mo": src}
        else:
            out["sources"]["profile_read_token"] = "set but not usable (does not authenticate as the owner); public data used"

    if out["mode"] == "public":
        if public_calendar:
            out["contributions_12mo"] = cc["contributionCalendar"]["totalContributions"]
            out["sources"]["contributions_12mo"] = ("public: GraphQL contributionCalendar"
                                                   + (" (owner token; no private repositories in the window)" if owner_view else ""))
        else:
            out["sources"]["contributions_12mo"] = "unavailable: the owner token's calendar includes private contributions"
        out["repos_contributed_12mo"] = sum(1 for _, p in repos if not p)
        out["sources"]["repos_contributed_12mo"] = "public: GraphQL contributionsCollection by repository, public repositories only"
    return out, (calendar(cc) if public_calendar else None)


def main() -> None:
    cfg = yaml.safe_load((ROOT / "data" / "config.yml").read_text(encoding="utf-8"))
    profile = yaml.safe_load((ROOT / "data" / "profile.yml").read_text(encoding="utf-8"))
    login = cfg["login"]
    tok = token()

    user = request(f"{API}/users/{login}", tok)
    raw = request(f"{API}/users/{login}/repos?type=owner&per_page=100&sort=full_name", tok)
    eligible = [r for r in raw if not r["fork"] and not r["archived"] and not r["private"]
                and r["name"].lower() != login.lower()]

    colors: dict[str, str] = {}
    for node in graphql(COLOR_QUERY, login, tok)["repositories"]["nodes"]:
        for lang in node["languages"]["nodes"]:
            if lang.get("color"):
                colors[lang["name"]] = lang["color"].upper()

    repos, lang_totals = [], {}
    for r in sorted(eligible, key=lambda r: r["name"].lower()):
        langs = request(f"{API}/repos/{login}/{r['name']}/languages", tok)
        for name, size in langs.items():
            lang_totals[name] = lang_totals.get(name, 0) + size
        repos.append({
            "name": r["name"],
            "url": r["html_url"],
            "homepage": (r.get("homepage") or "").strip(),
            "description": r["description"] or "",
            "language": r["language"] or "",
            "stars": r["stargazers_count"],
            "topics": sorted(r.get("topics") or []),
            "pushed": (r["pushed_at"] or r["updated_at"])[:10],
            "has_language_bytes": bool(langs),
        })

    sig, public = signal(login, tok, os.environ.get("PROFILE_READ_TOKEN"), bool(profile.get("show_private_contribution_count")))
    sig["sources"]["eligible_public_repos"] = "public: REST /users/{login}/repos (non-fork, non-archived, excluding the profile repo)"
    sig["sources"]["stars_earned"] = "public: REST stargazers_count, summed over eligible public repos"

    total_bytes = sum(lang_totals.values())
    ranked = sorted(lang_totals.items(), key=lambda kv: (-kv[1], kv[0]))
    share = [{"name": n, "pct": f"{100 * b / total_bytes:.1f}"} for n, b in ranked[:5]]
    if len(ranked) > 5:
        share.append({"name": "Other", "pct": f"{100 * sum(b for _, b in ranked[5:]) / total_bytes:.1f}"})

    data = {
        "login": login,
        "name": user.get("name") or "",
        "public_repos_total": user["public_repos"],
        "eligible_public_repos": len(repos),
        "stars_earned": sum(r["stars"] for r in repos),
        "repos": repos,
        "languages": dict(sorted(lang_totals.items(), key=lambda kv: (-kv[1], kv[0]))),
        "language_colors": {k: colors[k] for k in sorted(colors) if k in lang_totals},
        "language_share": share,
        "repos_with_language_bytes": sum(1 for r in repos if r["has_language_bytes"]),
        # public calendar: kept for the record (its daily movement also keeps the scheduled workflow alive)
        "contributions": public or {},
        "signal": {k: sig[k] for k in ("mode", "contributions_12mo", "repos_contributed_12mo", "sources") if k in sig},
    }

    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev_changed = previous.pop("last_changed", None)
    data["last_changed"] = prev_changed if previous == data and prev_changed else dt.date.today().isoformat()

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    sg = data["signal"]
    print(f"fetch: {len(repos)} eligible public repos; signal ({sg['mode']}): contributions "
          f"{sg.get('contributions_12mo', 'unavailable')}, repos contributed to {sg.get('repos_contributed_12mo', 'unavailable')}.")


if __name__ == "__main__":
    main()
