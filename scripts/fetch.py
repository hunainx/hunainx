"""Fetch public GitHub data for the profile into data/github.json.

Tokens (never printed):
  GITHUB_TOKEN        public data (in Actions: the workflow token). Locally falls back to `gh auth token`.
  PROFILE_READ_TOKEN  optional, owner-created, read-only. Used only to derive the private
                      contribution COUNT. No private repo names or details are stored.

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
    restrictedContributionsCount
    contributionCalendar{ totalContributions
      weeks{ contributionDays{ date contributionCount } } } } } }
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


def calendar(user: dict) -> dict:
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"][-52:]
    return {
        "total_12mo": cal["totalContributions"],
        "weeks": [
            {"start": w["contributionDays"][0]["date"],
             "count": sum(d["contributionCount"] for d in w["contributionDays"])}
            for w in weeks
        ],
    }


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
            "description": r["description"] or "",
            "language": r["language"] or "",
            "stars": r["stargazers_count"],
            "topics": sorted(r.get("topics") or []),
            "pushed": (r["pushed_at"] or r["updated_at"])[:10],
            "has_language_bytes": bool(langs),
        })

    public = calendar(graphql(CONTRIB_QUERY, login, tok))

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
        "contributions": public,
    }

    private_tok = os.environ.get("PROFILE_READ_TOKEN")
    if private_tok and profile.get("show_private_contribution_count"):
        owner = graphql(CONTRIB_QUERY, login, private_tok)["contributionsCollection"]
        owner_total = owner["contributionCalendar"]["totalContributions"]
        # Owner view counts private work; the public view does not. Only the difference is kept.
        data["private_contributions_12mo"] = max(owner_total - public["total_12mo"],
                                                 owner["restrictedContributionsCount"])

    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev_changed = previous.pop("last_changed", None)
    data["last_changed"] = prev_changed if previous == data and prev_changed else dt.date.today().isoformat()

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"fetch: {len(repos)} eligible public repos, {public['total_12mo']} public contributions (12 mo)"
          f"{', private count included' if 'private_contributions_12mo' in data else ''}.")


if __name__ == "__main__":
    main()
