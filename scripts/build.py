"""Build every SVG component and the README regions.

Inputs : data/profile.yml (copy, verbatim), data/projects.yml (building cards),
         data/config.yml (tiers, rules, tokens), data/github.json (every number)
Outputs: assets/** and README.md regions between <!-- START:x --> / <!-- END:x -->.
Prose outside the markers is never touched. Output is deterministic.

  python scripts/build.py
  python scripts/build.py --data qa/fixture/data/github.json --profile qa/fixture/data/profile.yml \
                          --projects qa/fixture/data/projects.yml --out qa/fixture
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

from components import activity, building, hero, label, misc, stack, work
from svgkit import ROOT, esc, esc_text

TPL = ROOT / "templates" / "README.md.tpl"
REGIONS = ("hero", "about", "links", "building", "work", "stack", "activity", "principles", "footer")
ASSET_DIRS = ("hero", "labels", "building", "work", "stack", "activity", "dividers", "footer", "chips")
LEGACY_DIRS = ("panels", "projects", "stats")  # v1 layout; cleaned when found


def nonempty(v) -> bool:
    return bool(v.strip()) if isinstance(v, str) else bool(v)


class Build:
    def __init__(self, out: Path, data: Path, profile: Path, projects: Path):
        self.out = out
        self.profile = yaml.safe_load(profile.read_text(encoding="utf-8")) or {}
        self.projects = yaml.safe_load(projects.read_text(encoding="utf-8")) if projects.exists() else {}
        self.cfg = yaml.safe_load((ROOT / "data" / "config.yml").read_text(encoding="utf-8"))
        self.gh = json.loads(data.read_text(encoding="utf-8"))
        self.produced: dict[str, tuple[int, int]] = {}

    def theme(self, mode: str) -> dict:
        t = dict(self.cfg["tokens"][mode])
        a = self.cfg["accents"][self.profile.get("accent") or "ember"][mode]
        t.update(accent=a["primary"], accent2=a["secondary"], accent_text=a["primary_text"],
                 glow=".16" if mode == "dark" else ".10", grid=".07" if mode == "dark" else ".09")
        return t

    def write(self, rel: str, content: str, anim: int) -> None:
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        self.produced[rel] = (len(content.encode("utf-8")), anim)

    def asset(self, comp: str, folder: str, stem: str, fn, tiers: tuple[str, ...] | None = None, **kw) -> dict:
        """Render every tier x theme. Returns {tier: (dark_path, light_path)}."""
        if tiers is None:
            tiers = ("desktop", "mid", "mobile") if comp in self.cfg["mid_tier"] else ("desktop", "mobile")
        out = {}
        for tier in tiers:
            suffix = "" if tier == "desktop" else f"-{tier}"
            pair = []
            for mode in ("dark", "light"):
                rel = f"assets/{folder}/{stem}{suffix}-{mode}.svg"
                svg, anim = fn(self.theme(mode), tier=tier, width=self.cfg["tiers"][tier]["width"], **kw)
                self.write(rel, svg, anim)
                pair.append(rel)
            out[tier] = tuple(pair)
        return out

    def picture(self, p: dict, alt: str, desktop_min: int | None = None) -> str:
        """Widest tier first: themed-picture keeps the first source of an explicit theme."""
        tiers = self.cfg["tiers"]
        src = ["<picture>"]
        d_min = desktop_min or (tiers["desktop"]["min_viewport"] if "mid" in p else tiers["mid"]["min_viewport"])
        if "mobile" in p:
            for mode, i in (("dark", 0), ("light", 1)):
                src.append(f'  <source media="(prefers-color-scheme: {mode}) and (min-width: {d_min}px)" srcset="{p["desktop"][i]}">')
            if "mid" in p:
                m_min = tiers["mid"]["min_viewport"]
                for mode, i in (("dark", 0), ("light", 1)):
                    src.append(f'  <source media="(prefers-color-scheme: {mode}) and (min-width: {m_min}px)" srcset="{p["mid"][i]}">')
            for mode, i in (("dark", 0), ("light", 1)):
                src.append(f'  <source media="(prefers-color-scheme: {mode})" srcset="{p["mobile"][i]}">')
        else:
            src.append(f'  <source media="(prefers-color-scheme: dark)" srcset="{p["desktop"][0]}">')
        src.append(f'  <img src="{p["desktop"][1]}" alt="{esc(alt)}">')
        src.append("</picture>")
        return "\n".join(src)

    def section(self, key: str, inner: str) -> str:
        s = self.cfg["sections"][key]
        lab = self.asset("label", "labels", key, lambda t, tier, width: label.render(t, s["command"], tier, width),
                         tiers=("desktop", "mobile"))
        # full-width strip where the column is ~846px; the natural-width label everywhere narrower
        pic = self.picture(lab, "$ " + s["command"], self.cfg["tiers"]["desktop"]["min_viewport"])
        return f'<p>\n{pic}\n</p>\n\n## {s["heading"]}\n\n{inner}'


def build(b: Build) -> dict[str, str]:
    p, gh, cfg = b.profile, b.gh, b.cfg
    th = cfg["thresholds"]
    regions = {k: "" for k in REGIONS}
    login = cfg["login"]

    # hero (always)
    hp = b.asset("hero", "hero", "hero", lambda t, tier, width: hero.render(t, p, cfg, tier, width))
    alt = p["name"].strip() + "".join(f" — {p[k].strip()}" for k in ("role", "tagline") if nonempty(p.get(k)))
    pic = b.picture(hp, alt)
    if nonempty((p.get("links") or {}).get("website")):
        pic = f'<a href="{esc(p["links"]["website"].strip())}">\n{pic}\n</a>'
    regions["hero"] = f'<p>\n{pic}\n</p>'

    if nonempty(p.get("about")):
        regions["about"] = esc_text(p["about"].strip())

    links = {k: v.strip() for k, v in (p.get("links") or {}).items() if nonempty(v) and k in misc.LINK_LABELS}
    if links:
        chips = []
        for key, value in links.items():
            cp = b.asset("chip", "chips", key, lambda t, tier, width, key=key: misc.chip(t, key), tiers=("desktop",))
            href = f"mailto:{value}" if key == "email" and not value.startswith("mailto:") else value
            chips.append(f'<a href="{esc(href)}">{b.picture(cp, misc.LINK_LABELS[key])}</a>')
        regions["links"] = "<p>\n" + "\n".join(chips) + "\n</p>"

    # currently building
    cards = building.cards_data(p, b.projects)
    if cards:
        bp = b.asset("building", "building", "building", lambda t, tier, width: building.render(t, cards, tier, width))
        alt_b = " ".join(f"{c['id']}: {c['summary']}" + (f" ({', '.join(c['stack'])})" if c["stack"] else "")
                         + (" Private." if c["private"] else "") for c in cards)
        regions["building"] = b.section("building", f"<p>\n{b.picture(bp, alt_b)}\n</p>")

    # selected work (only real public repos)
    repos = {r["name"]: r for r in gh.get("repos", [])}
    featured = [n for n in (p.get("featured_repos") or []) if n in repos]
    if not featured:
        ranked = sorted(repos.values(), key=lambda r: r["pushed"], reverse=True)
        ranked = sorted(ranked, key=lambda r: r["stars"], reverse=True)
        featured = [r["name"] for r in ranked[: cfg["selected_work"]["max_cards"]]]
    if featured and gh["eligible_public_repos"] >= th["stats_min_public_repos"]:
        blurbs = p.get("repo_blurbs") or {}
        items = []
        for i, name in enumerate(featured):
            r = repos[name]
            blurb = (blurbs.get(name) or r.get("description") or "").strip()
            color = gh.get("language_colors", {}).get(r.get("language", ""), b.theme("dark")["muted"])
            wp = b.asset("work", "work", name, lambda t, tier, width, r=r, blurb=blurb, color=color, i=i:
                         work.render(t, r, blurb, color, tier, 410 if tier == "desktop" else width, i))
            items.append(f'<a href="{esc(r["url"])}">{b.picture(wp, name + (": " + blurb if blurb else ""))}</a>')
        regions["work"] = b.section("work", "<p>\n" + "\n".join(items) + "\n</p>")

    # stack map
    st = {k: [s for s in (v or []) if nonempty(s)] for k, v in (p.get("stack") or {}).items()}
    st = {k: v for k, v in st.items() if v}
    if st:
        focus = [f for f in p.get("focus") or [] if nonempty(f)]
        sp = b.asset("stack", "stack", "stack", lambda t, tier, width: stack.render(t, st, focus, tier, width))
        alt_s = "; ".join(f"{k}: {', '.join(v)}" for k, v in st.items()) + (f". Focus: {', '.join(focus)}." if focus else ".")
        regions["stack"] = b.section("stack", f"<p>\n{b.picture(sp, alt_s)}\n</p>")

    # activity: honest low-data state until the threshold, then the data panel
    total = gh["contributions"]["total_12mo"]
    if total >= th["activity_min_contributions"]:
        ap = b.asset("activity", "activity", "activity", lambda t, tier, width: activity.with_data(t, gh, p, cfg, tier, width))
        alt_a = f"{total} {cfg['labels']['activity_caption']}"
    else:
        ap = b.asset("activity", "activity", "activity", lambda t, tier, width: activity.low_data(t, gh, cfg["labels"], tier, width))
        alt_a = f"{cfg['labels']['activity_low']}. {total} {cfg['labels']['activity_caption']}."
    regions["activity"] = b.section("activity", f"<p>\n{b.picture(ap, alt_a)}\n</p>")

    principles = [s.strip() for s in p.get("principles") or [] if nonempty(s)]
    if principles:
        regions["principles"] = b.section("principles", "\n".join(f"{i}. {esc_text(s)}" for i, s in enumerate(principles, 1)))

    # footer (always)
    sep = b.asset("separator", "dividers", "rule", lambda t, tier, width: misc.separator(t, tier, width))
    fp = b.asset("footer", "footer", "footer", lambda t, tier, width: misc.footer(t, gh["last_changed"], cfg["labels"]["footer"]),
                 tiers=("desktop",))
    wf = f"https://github.com/{login}/{login}/actions/workflows/refresh.yml"
    regions["footer"] = (f'<p>\n{b.picture(sep, "Divider")}\n</p>\n\n<p>\n{b.picture(fp, cfg["labels"]["footer"] + " · " + gh["last_changed"])}\n'
                         f'<br>\n<sub><a href="{wf}">refresh workflow</a></sub>\n</p>')
    return regions


def write_readme(b: Build, regions: dict[str, str]) -> None:
    path = b.out / "README.md"
    text = path.read_text(encoding="utf-8") if path.exists() else TPL.read_text(encoding="utf-8")
    known = set(re.findall(r"<!-- START:(\w+) -->", text))
    if not set(REGIONS) <= known:
        # region layout changed: start again from the template (only generated content is lost)
        text = TPL.read_text(encoding="utf-8")
    for key, content in regions.items():
        pat = re.compile(rf"(<!-- START:{key} -->)(.*?)(<!-- END:{key} -->)", re.S)
        inner = f"\n{content}\n" if content else "\n"
        text = pat.sub(lambda m: m.group(1) + inner + m.group(3), text, count=1)
    path.write_text(text, encoding="utf-8", newline="\n")


def clean_stale(b: Build) -> list[str]:
    removed = []
    for sub in ASSET_DIRS + LEGACY_DIRS:
        d = b.out / "assets" / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.svg")):
            rel = f.relative_to(b.out).as_posix()
            if rel not in b.produced:
                f.unlink()
                removed.append(rel)
        if not any(d.iterdir()):
            d.rmdir()
    return removed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "github.json")
    ap.add_argument("--profile", type=Path, default=ROOT / "data" / "profile.yml")
    ap.add_argument("--projects", type=Path, default=ROOT / "data" / "projects.yml")
    ap.add_argument("--out", type=Path, default=ROOT)
    args = ap.parse_args()
    b = Build(args.out.resolve(), args.data.resolve(), args.profile.resolve(), args.projects.resolve())
    regions = build(b)
    write_readme(b, regions)
    removed = clean_stale(b)
    total = sum(s for s, _ in b.produced.values())
    worst = max(b.produced.items(), key=lambda kv: kv[1][1])
    print(f"build: {len(b.produced)} assets, {total / 1024:.0f} KB; most animated: {worst[0]} ({worst[1][1]}); "
          f"shown: {', '.join(k for k, v in regions.items() if v)}; hidden: {', '.join(k for k, v in regions.items() if not v) or 'none'}"
          + (f"; removed {len(removed)} stale" if removed else ""))


if __name__ == "__main__":
    main()
