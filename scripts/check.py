"""Quality gates. Exits non-zero on any violation.

  python scripts/check.py
  python scripts/check.py --dir qa/fixture      # checks another build output (uses its data/ if present)
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from svgkit import ROOT, contrast

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}href"
NUM = re.compile(r"\d+(?:\.\d+)?")
SMIL = ("animate", "animateMotion", "animateTransform", "set", "animateColor")
PLACEHOLDERS = ("‹", "<status>", "<tool>", "TODO", "lorem", "{{", "}}", "coming soon", "placeholder")


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


def svg_texts(root: ET.Element) -> dict[str, str]:
    got = {"title": "", "desc": "", "text": []}
    for el in root.iter():
        tag = el.tag.replace(SVG_NS, "")
        if tag in ("title", "desc"):
            got[tag] = el.text or ""
        elif tag in ("text", "tspan"):
            got["text"].append("".join(el.itertext()))
    got["text"] = " ".join(got["text"])
    return got


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
        return ""
    md = path.read_text(encoding="utf-8")
    for bad in PLACEHOLDERS + ("shields.io",):
        r.ok(bad.lower() not in md.lower(), f"README contains {bad!r}")
    for tag in re.findall(r"<img\b[^>]*>", md):
        alt = re.search(r'alt="([^"]*)"', tag)
        r.ok(bool(alt and alt.group(1).strip()), f"README <img> without meaningful alt: {tag[:80]}")
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
    return html.unescape(re.sub(r"<[^>]+>", " ", visible) + " " + alts)


def check_copy(profile: dict, projects: dict, info: dict, readme: str, r: Report) -> None:
    """Profile copy must appear verbatim; empty fields must not appear at all."""
    def desc_of(prefix: str) -> str:
        return " ".join(v["desc"] + " " + v["text"] for k, v in info.items() if k.startswith(prefix))

    hero_desc = desc_of("assets/hero/")
    for key in ("name", "role", "tagline"):
        if (profile.get(key) or "").strip():
            r.ok(profile[key].strip() in hero_desc, f"hero is missing profile.yml {key} verbatim")
    for p in profile.get("principles") or []:
        first = re.split(r"(?<=[.!?])\s", p.strip(), maxsplit=1)[0]
        r.ok(first in hero_desc, f"hero ticker is missing principle lead {first!r}")
        r.ok(p.strip() in readme, f"README is missing principle {p.strip()[:40]!r}…")
    if (profile.get("about") or "").strip():
        r.ok(" ".join(profile["about"].split()) in " ".join(readme.split()), "README is missing the about text verbatim")
    b_desc = desc_of("assets/building/")
    entries = (projects or {}).get("building") or []
    for i, now in enumerate(profile.get("now") or []):
        e = entries[i] if i < len(entries) else {}
        summary = (e.get("summary") or "").strip() or now.strip()
        r.ok(summary in b_desc, f"building card {i + 1} is missing its summary verbatim")
        for tool in e.get("stack") or []:
            r.ok(tool in b_desc, f"building card {i + 1} is missing stack tool {tool!r}")
    if not any((e.get("status") or "").strip() for e in entries):
        r.ok("Status:" not in b_desc, "a building card shows a status although none is set in projects.yml")
    if not any((e.get("codename") or "").strip() for e in entries):
        r.ok("Codename" not in b_desc, "a building card shows a codename although none is set in projects.yml")
    s_desc = desc_of("assets/stack/")
    for cat, tools in (profile.get("stack") or {}).items():
        for tool in tools or []:
            r.ok(tool in s_desc, f"stack map is missing {tool!r}")
    for f in profile.get("focus") or []:
        r.ok(f in s_desc, f"stack map is missing focus {f!r}")


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
    readme = check_readme(base, r)
    check_copy(profile, projects, info, readme, r)
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
