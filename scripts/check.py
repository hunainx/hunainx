"""Quality gates. Exits non-zero on any violation.

  python scripts/check.py
  python scripts/check.py --dir qa/fixture      # checks another build output (uses its data/ if present)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from svgkit import ROOT, GlyphAtlas, contrast

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}href"
NUM = re.compile(r"\d+(?:\.\d+)?")
SMIL = ("animate", "animateMotion", "animateTransform", "set", "animateColor")
PLACEHOLDERS = ("‹", "<status>", "<tool>", "TODO", "lorem", "{{", "}}", "coming soon", "placeholder")
# Phrases that must never be rendered (case-insensitive). Scanned in rendered output only: README
# text, <img> alt text and every SVG's <title>, <desc> and <text>. Data keys are never rendered.
FORBIDDEN = ("private", "doing the building", "carry the implementation")
STAGES = ("challenge", "spec", "architect", "build", "audit", "ship")
_MEASURE = GlyphAtlas("chk")


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.checked = 0

    def ok(self, cond: bool, msg: str) -> None:
        self.checked += 1
        if not cond:
            self.errors.append(msg)


def load(base: Path, name: str):
    p = base / "data" / name
    p = p if p.exists() else ROOT / "data" / name
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.suffix == ".yml" else p.read_text(encoding="utf-8")


def animated_classes(css: str) -> set[str]:
    out = set()
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if re.search(r"(^|;)\s*animation\s*:", body) and "none" not in body.split("animation:")[-1][:6]:
            out |= set(re.findall(r"\.([A-Za-z_][\w-]*)", sel))
    return out


def svg_texts(root: ET.Element) -> dict:
    got = {"title": "", "desc": "", "text": [], "runs": [], "classes": set()}
    for el in root.iter():
        tag = el.tag.replace(SVG_NS, "")
        got["classes"] |= set((el.get("class") or "").split())
        if tag in ("title", "desc"):
            got[tag] = el.text or ""
        elif tag == "text":
            run = "".join(el.itertext())
            got["text"].append(run)
            got["runs"].append((run, el))
    got["text"] = " ".join(got["text"])
    return got


def text_bounds(rel: str, root: ET.Element, runs: list, r: "Report") -> None:
    """No clipping: every <text> run, measured with the committed fonts (as wide or wider than the
    system fonts it renders in), must sit inside the viewBox."""
    _, _, vw, vh = (float(v) for v in root.get("viewBox").split())
    for run, el in runs:
        if not run.strip():
            continue
        size = float(el.get("font-size") or 16)
        kind = "mono" if "mo" in (el.get("class") or "").split() else "sans"
        w = _MEASURE.width(kind, size, run, float(el.get("letter-spacing") or 0))
        x, y = float(el.get("x")), float(el.get("y"))
        left = {"middle": x - w / 2, "end": x - w}.get(el.get("text-anchor") or "start", x)
        r.ok(left >= 0 and left + w <= vw and y - size * .8 >= 0 and y + size * .25 <= vh,
             f"{rel}: text {run[:40]!r} leaves the {num_(vw)}x{num_(vh)} viewBox")


def num_(v: float) -> str:
    return f"{v:g}"


def forbidden(where: str, text: str, r: "Report") -> None:
    low = " ".join(text.split()).lower()
    for phrase in FORBIDDEN:
        r.ok(phrase not in low, f"{where}: forbidden phrase {phrase!r} is rendered")


def check_svgs(base: Path, cfg: dict, r: Report) -> dict[str, dict]:
    b = cfg["budgets"]
    assets = base / "assets"
    svgs = sorted(assets.rglob("*.svg"))
    r.ok(bool(svgs), "no SVG assets found")
    total = sum(f.stat().st_size for f in assets.rglob("*") if f.is_file())
    r.ok(total <= b["assets_total_max"], f"assets/ total {total} B > {b['assets_total_max']} B")
    info = {}
    for f in svgs:
        rel = f.relative_to(base).as_posix()
        raw = f.read_text(encoding="utf-8")
        limit = b["hero_max"] if "/hero/" in f"/{rel}" else b["svg_max"]
        r.ok(f.stat().st_size <= limit, f"{rel}: {f.stat().st_size} B > {limit} B")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            r.ok(False, f"{rel}: invalid XML ({e})")
            continue
        r.ok(root.tag == f"{SVG_NS}svg", f"{rel}: root is not <svg>")
        r.ok(root.get("role") == "img", f'{rel}: missing role="img"')
        texts = svg_texts(root)
        forbidden(f"{rel} <title>/<desc>/<text>", texts["title"] + " " + texts["desc"] + " " + texts["text"], r)
        text_bounds(rel, root, texts["runs"], r)
        r.ok(texts["title"].strip() != "", f"{rel}: missing non-empty <title>")
        r.ok(texts["desc"].strip() != "", f"{rel}: missing non-empty <desc> (alt text for the drawing)")
        css = "".join(el.text or "" for el in root.iter(f"{SVG_NS}style"))
        anim = animated_classes(css)
        count = 0
        for el in root.iter():
            tag = el.tag.replace(SVG_NS, "")
            r.ok(tag not in ("script", "foreignObject", "iframe", "image"), f"{rel}: forbidden <{tag}>")
            r.ok(tag not in SMIL, f"{rel}: SMIL <{tag}> is not allowed (it ignores reduced motion)")
            for attr, val in el.attrib.items():
                name = attr.split("}")[-1]
                r.ok(not name.lower().startswith("on"), f"{rel}: event attribute {name}")
                if name == "href" or attr == XLINK:
                    r.ok(val.startswith("#"), f"{rel}: external reference {val[:60]}")
                if name == "style":
                    r.ok("animation" not in val, f"{rel}: inline animation styles bypass the gates")
            if anim & set((el.get("class") or "").split()):
                count += 1
        r.ok(count <= b["max_animated_elements"], f"{rel}: {count} animated elements > {b['max_animated_elements']}")
        r.ok(not re.search(r"url\(\s*['\"]?(https?:|//)", raw), f"{rel}: external url() reference")
        r.ok("@import" not in raw, f"{rel}: @import is not allowed")
        if anim:
            r.ok("prefers-reduced-motion: reduce" in raw and "animation:none!important" in raw.replace(" ", ""),
                 f"{rel}: animated but no reduced-motion block")
        for bad in PLACEHOLDERS:
            r.ok(bad.lower() not in (texts["desc"] + texts["text"]).lower(), f"{rel}: placeholder text {bad!r}")
        info[rel] = {**texts, "animated": count}

    names = set(info)
    for n in names:
        if not (n.endswith("-dark.svg") or n.endswith("-light.svg")):
            r.ok(False, f"{n}: not part of a dark/light pair")
        for a_, b_ in (("-dark.svg", "-light.svg"), ("-light.svg", "-dark.svg")):
            if n.endswith(a_):
                r.ok(n[: -len(a_)] + b_ in names, f"{n}: missing twin {b_}")
    return info


def check_readme(base: Path, r: Report) -> str:
    path = base / "README.md"
    r.ok(path.exists() and path.stat().st_size > 0, "README.md missing or empty")
    if not path.exists():
        return "", ""
    md = path.read_text(encoding="utf-8")
    for bad in PLACEHOLDERS + ("shields.io",):
        r.ok(bad.lower() not in md.lower(), f"README contains {bad!r}")
    for tag in re.findall(r"<img\b[^>]*>", md):
        alt = re.search(r'alt="([^"]*)"', tag)
        r.ok(bool(alt and alt.group(1).strip()), f"README <img> without meaningful alt: {tag[:80]}")
        if alt:
            forbidden(f"README <img> alt {alt.group(1)[:30]!r}", html.unescape(alt.group(1)), r)
    for pic in re.findall(r"<picture>(.*?)</picture>", md, flags=re.S):
        r.ok(len(re.findall(r"<img\b", pic)) == 1, "a <picture> lacks exactly one <img> fallback")
        r.ok(len(re.findall(r"<source\b", pic)) >= 1, "a <picture> has no <source>")
    r.ok(md.count("<picture>") == md.count("</picture>"), "unbalanced <picture> tags")
    for ref in re.findall(r'(?:src|srcset)="([^"]+)"', md):
        r.ok(not re.match(r"(https?:)?//", ref), f"README image is not a relative path: {ref}")
        r.ok((base / ref).exists(), f"README references missing file {ref}")
    for m in re.finditer(r"<!-- START:(\w+) -->(.*?)<!-- END:\1 -->", md, flags=re.S):
        body = m.group(2)
        for h in re.finditer(r"^## .+$", body, flags=re.M):
            r.ok(bool(body[h.end():].strip()), f"README section {h.group(0)!r} is empty")
    visible = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    visible = re.sub(r"(?m)^\d+\. ", "", visible)  # ordered-list markers are structure, not numbers
    alts = " ".join(re.findall(r'alt="([^"]*)"', visible))
    forbidden("README text", html.unescape(re.sub(r"<[^>]+>", " ", visible)), r)
    return md, html.unescape(re.sub(r"<[^>]+>", " ", visible) + " " + alts)


def check_copy(base: Path, cfg: dict, profile: dict, projects: dict, info: dict, readme_md: str, readme: str, r: Report) -> None:
    """Profile copy must appear verbatim; empty fields must not appear at all."""
    def desc_of(prefix: str) -> str:
        return " ".join(v["desc"] + " " + v["text"] for k, v in info.items() if k.startswith(prefix))

    def flat(text: str) -> str:
        return " ".join(text.split())

    # hero, per tier: name, role, tagline, depth line, ticker, the six-stage pipeline, the AI toolkit
    kit_name = cfg["hero"]["agents_category"]
    r.ok(kit_name == "AI toolkit", f"config hero.agents_category is {kit_name!r}, expected 'AI toolkit'")
    kit = (profile.get("stack") or {}).get(kit_name) or []
    r.ok(bool(kit), f"profile.yml stack has no {kit_name!r} category for the hero toolkit")
    heroes = [k for k in info if k.startswith("assets/hero/")]
    r.ok(len(heroes) == 6, f"{len(heroes)} hero SVGs, expected 3 tiers x 2 themes")
    for k in heroes:
        v = info[k]
        for key in ("name", "role", "tagline"):
            if (profile.get(key) or "").strip():
                r.ok(profile[key].strip() in v["desc"], f"{k} is missing profile.yml {key} verbatim")
        depth = [x.strip() for x in profile.get("depth") or [] if x and x.strip()]
        if depth:
            r.ok(" · ".join(depth) in v["desc"], f"{k}: depth line is not profile.yml depth joined with ' · '")
            for item in depth:
                r.ok(item in v["text"], f"{k}: depth item {item!r} is not drawn")
        r.ok(("Diagram of how I work: " + ", ".join(STAGES) + ",") in v["desc"], f"{k}: pipeline is not {' → '.join(STAGES)}")
        r.ok("looping back into the build" in v["desc"], f"{k}: the return loop is not audit → build")
        r.ok("agents" not in v["desc"].lower().replace(kit_name.lower(), ""), f"{k}: an agents stage or label is still drawn")
        r.ok(kit_name.upper() in v["text"], f"{k}: toolkit heading {kit_name.upper()!r} is missing")
        for a in kit:
            r.ok(a in v["text"], f"{k}: toolkit is missing {a!r}")
        for p in profile.get("principles") or []:
            first = re.split(r"(?<=[.!?])\s", p.strip(), maxsplit=1)[0]
            r.ok(first in v["desc"], f"{k}: ticker is missing principle lead {first!r}")
    for p in profile.get("principles") or []:
        r.ok(p.strip() in readme, f"README is missing principle {p.strip()[:40]!r}")

    # about: every paragraph, verbatim, as its own Markdown paragraph; `current` as <sub> directly below
    paras = [flat(x) for x in (profile.get("about") or "").strip().split("\n") if x.strip()]
    for para in paras:
        r.ok(f"\n{para}\n" in f"\n{readme_md}\n", f"README is missing the about paragraph {para[:40]!r} as its own paragraph")
    cur = (profile.get("current") or "").strip()
    if cur:
        sub = f"<sub>{html.escape(cur, quote=False)}</sub>"
        r.ok(f"{html.escape(paras[-1], quote=False) if paras else ''}\n\n{sub}\n" in readme_md,
             "README: `current` is not a <sub> line directly under the about paragraphs")

    # in motion: one card per `now` item; name/description split verbatim; fields only when set
    r.ok("## In motion" in readme_md, "README is missing the 'In motion' heading")
    r.ok(cfg["sections"].get("motion", {}).get("command") == "./in-motion", "section label for In motion is not ./in-motion")
    entries = (projects or {}).get("building") or []
    now = [n for n in profile.get("now") or [] if n.strip()]
    motion = sorted(k for k in info if k.startswith("assets/motion/") and re.search(r"/[^/-]+-dark\.svg$", k))
    r.ok(len(motion) == len(now), f"{len(motion)} In motion cards for {len(now)} `now` items")
    for i, text in enumerate(now):
        e = entries[i] if i < len(entries) else {}
        cid = str(e.get("id") or f"{i + 1:02d}")
        files = [k for k in info if re.match(rf"assets/motion/{cid}(-mid|-mobile)?-(dark|light)\.svg$", k)]
        r.ok(len(files) == 6, f"card {cid}: {len(files)} SVGs, expected 3 tiers x 2 themes")
        hits = sorted((text.find(sep), sep) for sep in (":", " — ") if text.find(sep) > 0)
        name, desc = (text[:hits[0][0]].strip(), text[hits[0][0] + len(hits[0][1]):].strip()) if hits else (text.strip(), "")
        desc = (e.get("summary") or "").strip() or desc
        alt_m = re.search(rf'<img src="assets/motion/{cid}-light\.svg" alt="([^"]*)"', readme_md)
        alt_t = html.unescape(alt_m.group(1)) if alt_m else ""
        status = (e.get("status") or "").strip()
        typ = (e.get("type") or "").strip()
        link = (e.get("link") or "").strip()
        for k in files:
            v = info[k]
            r.ok(v["title"] == name, f"{k}: card name is {v['title']!r}, expected {name!r}")
            r.ok(f"{name}: {desc}" in v["desc"] or f"{name} — {desc}" in v["desc"], f"{k}: name/description not verbatim from `now`")
            r.ok(flat(desc) in flat(v["text"]) or not desc, f"{k}: description text is not drawn verbatim")
            for tool in e.get("stack") or []:
                r.ok(tool in v["text"], f"{k}: missing stack chip {tool!r}")
            r.ok((typ.upper() in v["text"]) if typ else True, f"{k}: type tag {typ.upper()!r} is not drawn")
            if status:
                r.ok(f"Status: {status}." in v["desc"] and status in v["text"], f"{k}: status {status!r} is not shown")
                concept = status.lower() == "concept"
                r.ok(("scon" in v["classes"]) == concept and ("sled" in v["classes"]) != concept,
                     f"{k}: status {status!r} uses the wrong light (concept must be the open ring, never a live light)")
            else:
                r.ok("Status:" not in v["desc"] and not {"st", "sled", "scon"} & v["classes"],
                     f"{k}: shows a status although projects.yml has none")
            conf = e.get("confidential") is True
            r.ok(("Confidential." in v["desc"]) == conf and ("CONFIDENTIAL" in v["text"]) == conf,
                 f"{k}: confidentiality tag does not match projects.yml")
        r.ok(bool(alt_m) and f"{name}" in alt_t and (not desc or desc in alt_t), f"card {cid}: README alt text is not verbatim")
        r.ok((f"Status: {status}." in alt_t) if status else ("Status:" not in alt_t), f"card {cid}: README alt status does not match projects.yml")
        wrapped = bool(re.search(rf'<a href="{re.escape(link)}"><picture>\s*<source[^>]*assets/motion/{cid}-', readme_md)) if link else False
        any_link = bool(re.search(rf'<a href="[^"]+"><picture>\s*<source[^>]*assets/motion/{cid}-', readme_md))
        r.ok(wrapped if link else not any_link, f"card {cid}: link does not match projects.yml")

    # the separate Client work section is gone
    r.ok("clients" not in cfg["sections"], "config still has a clients section")
    r.ok("client_work" not in (projects or {}), "projects.yml still has client_work")
    r.ok(not (base / "assets" / "clients").exists(), "assets/clients still exists")
    r.ok("## Client work" not in readme_md and "START:clients" not in readme_md, "README still has a Client work section")
    for gone in ("building", "activity"):
        r.ok(not (base / "assets" / gone).exists(), f"stale assets/{gone} still exists")

    # method: every stage in the diagram, and "stage — line" verbatim in the Markdown list
    m_desc = desc_of("assets/method/")
    for m in profile.get("method") or []:
        stage, line = m["stage"].strip(), m["line"].strip()
        r.ok(stage in m_desc, f"method diagram is missing stage {stage!r}")
        r.ok(f"**{html.escape(stage, quote=False)}** — {html.escape(line, quote=False)}" in readme_md,
             f"README method list is missing {stage!r} with its line verbatim")
    proof = profile.get("proof") or {}
    if (proof.get("text") or "").strip():
        want = html.escape(proof["text"].strip(), quote=False)
        if (proof.get("link") or "").strip():
            want = f"[{want}]({proof['link'].strip()})"
        r.ok(f"\n{want}\n" in readme_md, "README is missing the proof line (linked to proof.link) under How I work")

    # stack map, per tier: the depth categories with their tools on the left, the range on the right
    stack_files = [k for k in info if k.startswith("assets/stack/")]
    r.ok(len(stack_files) == 6, f"{len(stack_files)} stack SVGs, expected 3 tiers x 2 themes")
    cats = profile.get("stack") or {}
    focus = profile.get("focus") or []
    r.ok(len(cats) == 5, f"profile.yml stack has {len(cats)} categories, expected 5")
    r.ok(len(focus) == 7, f"profile.yml focus has {len(focus)} domains, expected 7")
    for k in stack_files:
        v = info[k]
        for cat, tools in cats.items():
            r.ok(cat.upper() in v["text"], f"{k}: missing category {cat!r}")
            for tool in tools or []:
                r.ok(tool in v["text"], f"{k}: missing tool {tool!r}")
        for f in focus:
            r.ok(f in [run for run, _ in v["runs"]] or f in v["text"], f"{k}: missing range domain {f!r}")
    r.ok("## Stack & range" in readme_md, "README stack heading does not read as range + depth")

    # shipping signal: exactly the counts that exist and meet their thresholds
    gh = json.loads(load(base, "github.json") or "{}")
    sig, th, lab = gh.get("signal") or {}, cfg["signal"], cfg["labels"]
    cands = [(lab["contributions"], sig.get("contributions_12mo"), th["contributions_min"]),
             (lab["repos_contributed"], sig.get("repos_contributed_12mo"), th["repos_contributed_min"]),
             (lab["public_repos"], gh.get("eligible_public_repos"), th["public_repos_min"]),
             (lab["stars"], gh.get("stars_earned"), th["stars_min"])]
    shown = [(l_, v_) for l_, v_, m_ in cands if isinstance(v_, int) and v_ >= m_]
    shown = shown if shown and shown[0][0] == lab["contributions"] else []  # contributions gates the panel
    sig_files = [k for k in info if k.startswith("assets/signal/")]
    r.ok(("## Shipping signal" in readme_md) == bool(shown), "Shipping signal section shown/hidden against its thresholds")
    for k in sig_files:
        for l_, v_, m_ in cands:
            want = isinstance(v_, int) and v_ >= m_
            r.ok((f"{l_}: {v_}" in info[k]["desc"]) == want if v_ is not None else l_ not in info[k]["desc"],
                 f"{k}: {l_!r} is {'missing' if want else 'shown below its threshold or unavailable'}")
    for key in ("contributions_12mo", "repos_contributed_12mo"):
        if key in sig:
            r.ok(bool((sig.get("sources") or {}).get(key)), f"github.json has no data source recorded for {key}")
    r.ok(not any(k.startswith("assets/activity/") for k in info), "the old activity radar is still built")


def check_contrast(cfg: dict, r: Report) -> None:
    for accent, modes in cfg["accents"].items():
        for mode, a in modes.items():
            t = cfg["tokens"][mode]
            for fg_name, fg in (("text", t["text"]), ("muted", t["muted"]), (f"{accent}.primary_text", a["primary_text"])):
                for bg_name in ("bg", "surface"):
                    c = contrast(fg, t[bg_name])
                    r.ok(c >= 4.5, f"contrast {mode} {fg_name} on {bg_name} = {c:.2f} < 4.5")


def _strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in _strings(v)] + [str(k) for k in node]
    if isinstance(node, list):
        return [s for v in node for s in _strings(v)]
    return []


def check_numbers(base: Path, cfg: dict, profile: dict, projects: dict, text: str, r: Report) -> None:
    """Every rendered number comes from github.json, the owner's copy (profile.yml, projects.yml)
    or a fixed display string in config.yml. Never from thresholds or budgets."""
    gh = load(base, "github.json") or ""
    allowed = set(NUM.findall(gh))
    display = [cfg.get("hero", {}), cfg.get("labels", {}), cfg.get("sections", {})]
    for s in _strings(profile) + _strings(projects) + _strings(display):
        allowed |= set(NUM.findall(s))
    for n in sorted(set(NUM.findall(text))):
        r.ok(n in allowed, f"number {n!r} is rendered but not traceable to github.json / profile.yml / projects.yml / display strings")
    for claim in sorted(set(re.findall(r"\b\d+(?:\.\d+)?\s?[xX×]\b", text))):
        r.ok(False, f"multiplier claim {claim!r} is not allowed (truth policy)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=ROOT)
    args = ap.parse_args()
    base = args.dir.resolve()
    cfg = yaml.safe_load((ROOT / "data" / "config.yml").read_text(encoding="utf-8"))
    profile = load(base, "profile.yml") or {}
    projects = load(base, "projects.yml") or {}
    r = Report()
    info = check_svgs(base, cfg, r)
    readme_md, readme = check_readme(base, r)
    check_copy(base, cfg, profile, projects, info, readme_md, readme, r)
    check_contrast(cfg, r)
    rendered = " ".join(v["desc"] + " " + v["text"] + " " + v["title"] for v in info.values()) + " " + readme
    check_numbers(base, cfg, profile, projects, rendered, r)
    worst = max(info.items(), key=lambda kv: kv[1]["animated"]) if info else ("-", {"animated": 0})
    if r.errors:
        print(f"check: FAILED ({len(r.errors)} of {r.checked} checks)")
        for e in r.errors[:60]:
            print(f"  - {e}")
        sys.exit(1)
    print(f"check: OK ({r.checked} checks; {len(info)} SVGs; max {worst[1]['animated']} animated elements in {worst[0]})")


if __name__ == "__main__":
    main()
