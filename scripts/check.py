"""Quality gates (PRD §11). Exits non-zero on any violation.

  python scripts/check.py              # checks the repo
  python scripts/check.py --dir qa/fixture   # checks another build output
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from svgkit import ROOT, contrast

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}href"
NUM = re.compile(r"\d+(?:\.\d+)?")


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.checked = 0

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def ok(self, cond: bool, msg: str) -> None:
        self.checked += 1
        if not cond:
            self.fail(msg)


def svg_text(root: ET.Element) -> str:
    parts = []
    for el in root.iter():
        tag = el.tag.replace(SVG_NS, "")
        if tag in ("text", "tspan", "title", "desc"):
            parts.append(el.text or "")
    return " ".join(parts)


def check_svgs(base: Path, cfg: dict, r: Report) -> str:
    budgets = cfg["budgets"]
    assets = base / "assets"
    svgs = sorted(assets.rglob("*.svg"))
    r.ok(bool(svgs), "no SVG assets found")
    texts, total = [], 0
    for f in sorted(assets.rglob("*")):
        if f.is_file():
            total += f.stat().st_size
    r.ok(total <= budgets["assets_total_max"], f"assets/ total {total} B > {budgets['assets_total_max']} B")

    for f in svgs:
        rel = f.relative_to(base).as_posix()
        raw = f.read_text(encoding="utf-8")
        limit = budgets["hero_max"] if "/hero/" in f"/{rel}" else budgets["svg_max"]
        r.ok(f.stat().st_size <= limit, f"{rel}: {f.stat().st_size} B > {limit} B")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            r.fail(f"{rel}: invalid XML ({e})")
            continue
        r.ok(root.tag == f"{SVG_NS}svg", f"{rel}: root is not <svg>")
        r.ok(root.get("role") == "img", f'{rel}: missing role="img"')
        title = root.find(f"{SVG_NS}title")
        r.ok(title is not None and (title.text or "").strip() != "", f"{rel}: missing non-empty <title>")
        for el in root.iter():
            tag = el.tag.replace(SVG_NS, "")
            r.ok(tag not in ("script", "foreignObject", "iframe"), f"{rel}: forbidden <{tag}>")
            for attr, val in el.attrib.items():
                name = attr.split("}")[-1]
                r.ok(not name.lower().startswith("on"), f"{rel}: event attribute {name}")
                if name == "href" or attr == XLINK:
                    r.ok(val.startswith("#"), f"{rel}: external reference {val[:60]}")
            if tag == "image":
                href = el.get("href") or el.get(XLINK) or ""
                r.ok(href.startswith("data:") or href.startswith("#"), f"{rel}: <image> points outside the file")
        r.ok(not re.search(r"url\(\s*['\"]?(https?:|//)", raw), f"{rel}: external url() reference")
        r.ok("@import" not in raw, f"{rel}: @import is not allowed")
        animated = "animation" in raw or "<animate" in raw
        if animated:
            r.ok("prefers-reduced-motion" in raw, f"{rel}: animated but no prefers-reduced-motion block")
        texts.append(svg_text(root))

    # Twins: every *-dark.svg has *-light.svg and vice versa.
    names = {f.relative_to(base).as_posix() for f in svgs}
    for n in names:
        for a, b in (("-dark.svg", "-light.svg"), ("-light.svg", "-dark.svg")):
            if n.endswith(a):
                r.ok(n[: -len(a)] + b in names, f"{n}: missing twin {b}")
        if not (n.endswith("-dark.svg") or n.endswith("-light.svg")):
            r.fail(f"{n}: not part of a dark/light pair")
    return " ".join(texts)


def readme_visible_text(md: str) -> str:
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    alts = " ".join(re.findall(r'alt="([^"]*)"', md))
    md = re.sub(r"<[^>]+>", " ", md)
    return md + " " + alts


def check_readme(base: Path, r: Report) -> str:
    path = base / "README.md"
    r.ok(path.exists() and path.stat().st_size > 0, "README.md missing or empty")
    if not path.exists():
        return ""
    md = path.read_text(encoding="utf-8")
    for bad in ("TODO", "lorem", "{{", "}}", "coming soon", "shields.io"):
        r.ok(bad.lower() not in md.lower(), f"README contains {bad!r}")

    imgs = re.findall(r"<img\b[^>]*>", md)
    for tag in imgs:
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
            after = re.sub(r"</?div[^>]*>", "", body[h.end():]).strip()
            r.ok(bool(after), f"README section {h.group(0)!r} is empty")
    return readme_visible_text(md)


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


def check_numbers(base: Path, cfg: dict, text: str, r: Report) -> None:
    """Every rendered number must come from github.json (API), the brief's own copy, or a fixed
    display string in config.yml (hero meta line, labels) — never from thresholds or budgets."""
    gh = base / "data" / "github.json"
    allowed = set(NUM.findall(gh.read_text(encoding="utf-8"))) if gh.exists() else set()
    ppath = base / "data" / "profile.yml"
    profile = yaml.safe_load((ppath if ppath.exists() else ROOT / "data" / "profile.yml").read_text(encoding="utf-8")) or {}
    display = [cfg.get("hero_meta", ""), cfg.get("hero_meta_mobile", []), cfg.get("labels", {})]
    for s in _strings(profile) + _strings(display):
        allowed |= set(NUM.findall(s))
    for n in sorted(set(NUM.findall(text))):
        r.ok(n in allowed, f"number {n!r} is rendered but not traceable to github.json / brief / display strings")
    for claim in sorted(set(re.findall(r"\b\d+(?:\.\d+)?\s?[xX×]\b", text))):
        r.fail(f"multiplier claim {claim!r} is not allowed (truth policy)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=ROOT)
    args = ap.parse_args()
    base = args.dir.resolve()
    cfg = yaml.safe_load((ROOT / "data" / "config.yml").read_text(encoding="utf-8"))
    r = Report()
    svg_texts = check_svgs(base, cfg, r)
    readme_text = check_readme(base, r)
    check_contrast(cfg, r)
    check_numbers(base, cfg, svg_texts + " " + readme_text, r)
    if r.errors:
        print(f"check: FAILED ({len(r.errors)} of {r.checked} checks)")
        for e in r.errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"check: OK ({r.checked} checks)")


if __name__ == "__main__":
    main()
