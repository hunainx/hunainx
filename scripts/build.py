"""Build SVG assets and README regions.

Inputs : data/profile.yml (content), data/config.yml (rules + tokens), data/github.json (numbers)
Outputs: assets/** and the regions of README.md between <!-- START:x --> / <!-- END:x -->.
Prose outside the markers is never touched. Output is deterministic.

  python scripts/build.py                                  # normal build
  python scripts/build.py --data qa/fixture/data/github.json --profile qa/fixture/data/profile.yml --out qa/fixture
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import string
from pathlib import Path

import yaml

from svgkit import MONO_STACK, ROOT, SANS_STACK, GlyphAtlas, esc, esc_text, num, wrap, wrap_width

TPL = ROOT / "templates"
MANAGED = ("hero", "panels", "chips", "projects", "stats", "dividers")
REGIONS = ("hero", "now", "about", "links", "work", "toolkit", "signal", "principles", "footer")

# 7 x 11 dot-matrix letters for the monogram (two-dot strokes, crossbar on the middle row).
LETTERS = {
    "H": ["XX...XX"] * 5 + ["XXXXXXX"] + ["XX...XX"] * 5,
    "A": [".XXXXX.", "XX...XX", "XX...XX", "XX...XX", "XX...XX", "XXXXXXX",
          "XX...XX", "XX...XX", "XX...XX", "XX...XX", "XX...XX"],
}

MOBILE_W = 360  # design width of narrow variants (GitHub mobile README column is about 324px)

LINK_LABELS = {"website": "Website", "linkedin": "LinkedIn", "x": "X", "email": "Email"}
# In-house geometric glyphs on a 16px box (no brand marks).
LINK_GLYPHS = {
    "website": '<circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c-3.2 3.6-3.2 9.4 0 13M8 1.5c3.2 3.6 3.2 9.4 0 13"/>',
    "linkedin": '<rect x="1.5" y="2.5" width="13" height="11" rx="2"/><circle cx="6" cy="7" r="1.7"/><path d="M3.6 11.2c.7-1.5 3.9-1.5 4.8 0M10 6.5h2.6M10 9.2h2.6"/>',
    "x": '<path d="M2 3.5h12v7.5H8l-3.5 3v-3H2z"/>',
    "email": '<rect x="1.5" y="3" width="13" height="10" rx="1.6"/><path d="M2 4l6 4.8L14 4"/>',
}


# ---------------------------------------------------------------- context

class Build:
    def __init__(self, out: Path, data_path: Path, profile_path: Path):
        self.out = out
        self.profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        self.cfg = yaml.safe_load((ROOT / "data" / "config.yml").read_text(encoding="utf-8"))
        self.gh = json.loads(data_path.read_text(encoding="utf-8"))
        self.produced: set[str] = set()
        self.bp = int(self.cfg["mobile_breakpoint_px"])

    def theme(self, mode: str) -> dict:
        t = dict(self.cfg["tokens"][mode])
        a = self.cfg["accents"][self.profile.get("accent") or "ember"][mode]
        t.update(accent=a["primary"], accent2=a["secondary"], accent_text=a["primary_text"],
                 sans=SANS_STACK, mono=MONO_STACK)
        return t

    def write(self, rel: str, content: str) -> None:
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(line.rstrip() for line in content.strip().splitlines()) + "\n"
        path.write_text(content, encoding="utf-8", newline="\n")
        self.produced.add(rel)

    def pair(self, rel_stem: str, fn, **kw) -> tuple[str, str]:
        """Render dark + light twins; returns (dark_path, light_path)."""
        paths = []
        for mode in ("dark", "light"):
            rel = f"{rel_stem}-{mode}.svg"
            self.write(rel, fn(self.theme(mode), **kw))
            paths.append(rel)
        return paths[0], paths[1]


def tpl(name: str, **kw) -> str:
    raw = (TPL / "svg" / f"{name}.svg.tpl").read_text(encoding="utf-8")
    return string.Template(raw).substitute(**kw)


def nonempty(v) -> bool:
    if isinstance(v, str):
        return bool(v.strip())
    return bool(v)


# ---------------------------------------------------------------- hero

def matrix(initials: str, x0: float, y0: float, pitch: float, r: float):
    rows = [""] * 11
    for i, ch in enumerate(initials):
        if ch not in LETTERS:
            raise SystemExit(f"build: no dot-matrix glyph for {ch!r}; add it to LETTERS in build.py")
        for ri in range(11):
            rows[ri] += ("." if i else "") + LETTERS[ch][ri]
    on, off, clip_on, clip_off = [], [], [], []
    maxd = len(rows[0]) - 1 + len(rows) - 1
    for ri, row in enumerate(rows):
        for ci, ch in enumerate(row):
            cx, cy = num(x0 + r + ci * pitch), num(y0 + r + ri * pitch)
            circ = f'cx="{cx}" cy="{cy}" r="{num(r)}"'
            (on if ch == "X" else off).append(f'<circle class="dot d{ri + ci}" {circ}/>')
            (clip_on if ch == "X" else clip_off).append(f"<circle {circ}/>")
    w = (len(rows[0]) - 1) * pitch + 2 * r
    h = (len(rows) - 1) * pitch + 2 * r
    delays = "".join(f".d{d}{{animation-delay:{d * 0.9 / maxd:.2f}s}}" for d in range(maxd + 1))
    return {"on": "".join(on), "off": "".join(off), "clip_on": "".join(clip_on),
            "clip_off": "".join(clip_off), "w": w, "h": h, "delays": delays}


def split_tokens(at: GlyphAtlas, kind: str, size: float, tokens: list[str], sep: str,
                 max_w: float, tracking: float) -> list[str]:
    lines, cur = [], ""
    for tok in tokens:
        cand = f"{cur}{sep}{tok}" if cur else tok
        if at.width(kind, size, cand, tracking) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = tok
    return lines + ([cur] if cur else [])


def hero_svg(t: dict, b: Build, mobile: bool) -> str:
    p = b.profile
    at = GlyphAtlas("g")
    name = p["name"].strip()
    initials = "".join(w[0] for w in name.split()[:2]).upper()
    focus = [f.upper() for f in (p.get("focus") or []) if nonempty(f)]
    tagline = (p.get("tagline") or "").strip()

    if mobile:
        W, pad = MOBILE_W, 20
        pitch, r = 8, 2.5
        mx = matrix(initials, pad, 30, pitch, r)
        y = 30 + mx["h"] + 62
        name_size, sub_size, tag_size, meta_size = 36, 14, 16, 13
        text_w = W - 2 * pad
        meta_lines = b.cfg["hero_meta_mobile"]
    else:
        W, pad = 840, 40
        pitch, r = 11, 3.2
        mx_w = 14 * pitch + 2 * r
        mx = matrix(initials, W - pad - mx_w, 120 - (10 * pitch + 2 * r) / 2, pitch, r)
        y = 100
        name_size, sub_size, tag_size, meta_size = 44, 16, 17, 16
        text_w = 560
        meta_lines = [b.cfg["hero_meta"]]

    blocks = []
    blocks.append(f'<g class="name rise r1">{at.text("display", name_size, name, pad, y, -0.02 * name_size)}</g>')
    y += 34 if not mobile else 32
    if focus:
        sub_lines = split_tokens(at, "mono", sub_size, focus, " · ", text_w, 1.6)
        g = []
        for i, line in enumerate(sub_lines):
            g.append(at.text("mono", sub_size, line, pad, y, 1.6))
            y += 22
        blocks.append(f'<g class="sub rise r2">{"".join(g)}</g>')
        y += 10
    if tagline:
        g = []
        sentences = re.split(r"(?<=[.!?]) ", tagline)
        for line in split_tokens(at, "sans", tag_size, sentences, " ", text_w, 0.0):
            g.append(at.text("sans", tag_size, line, pad, y))
            y += 24
        blocks.append(f'<g class="tag rise r3">{"".join(g)}</g>')

    if mobile:
        y += 26
        meta_y0 = y
        H = int(meta_y0 + 20 * (len(meta_lines) - 1) + 28)
    else:
        H = 240
        meta_y0 = 212
    g = [at.text("mono", meta_size, line, pad, meta_y0 + i * 20, 0.6) for i, line in enumerate(meta_lines)]
    blocks.append(f'<g class="meta rise r4">{"".join(g)}</g>')

    # Monogram: corner ticks, dots, scan band clipped to the dots.
    x0 = (pad if mobile else W - pad - mx["w"])
    y0 = 30 if mobile else 120 - mx["h"] / 2
    o, k = 8, 7
    x1, y1, x2, y2 = x0 - o, y0 - o, x0 + mx["w"] + o, y0 + mx["h"] + o
    ticks = (f'<path class="tick" d="M{num(x1)} {num(y1 + k)}V{num(y1)}H{num(x1 + k)}'
             f'M{num(x2 - k)} {num(y1)}H{num(x2)}V{num(y1 + k)}'
             f'M{num(x2)} {num(y2 - k)}V{num(y2)}H{num(x2 - k)}'
             f'M{num(x1 + k)} {num(y2)}H{num(x1)}V{num(y2 - k)}"/>')
    bw = 44 if not mobile else 34
    band_x = x0 - bw - 4
    scan_dist = mx["w"] + bw + 8
    band = (f'<rect class="scan" x="{num(band_x)}" y="{num(y0 - 2)}" width="{bw}" height="{num(mx["h"] + 4)}"')
    monogram = (f'{ticks}<g class="off">{mx["off"]}</g><g class="on">{mx["on"]}</g>'
                f'<g clip-path="url(#coff)">{band} fill="url(#s2)"/></g>'
                f'<g clip-path="url(#con)">{band} fill="url(#s1)"/></g>')

    grad = lambda gid, color, op: (  # noqa: E731
        f'<linearGradient id="{gid}" x1="0" x2="1" y1="0" y2="0">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{color}" stop-opacity="{op}"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient>')
    defs = (f'<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
            f'<circle cx="12" cy="12" r="1" fill="{t["text"]}" fill-opacity=".04"/></pattern>'
            f'{grad("s1", t["text"], ".9")}{grad("s2", t["accent"], ".55")}'
            f'<clipPath id="con">{mx["clip_on"]}</clipPath><clipPath id="coff">{mx["clip_off"]}</clipPath>'
            f'{at.defs_svg()}')
    body = (f'<rect width="{W}" height="{H}" fill="url(#grid)"/>'
            f'<path class="rule" d="M0 .5H{W}M0 {num(H - .5)}H{W}"/>'
            + "".join(blocks) + monogram)
    desc_parts = [p.get("positioning"), " · ".join(p.get("focus") or []), tagline, " ".join(meta_lines)]
    return tpl("hero", w=W, h=H, title=esc(name), desc=esc(". ".join(s.strip().rstrip(".") for s in desc_parts if nonempty(s)) + "."),
               defs=defs, body=body, delays=mx["delays"], scan_dist=num(scan_dist), **t)


# ---------------------------------------------------------------- now panel

def now_svg(t: dict, b: Build, mobile: bool) -> str:
    items = [s.strip() for s in b.profile.get("now") or [] if nonempty(s)]
    at = GlyphAtlas("g")
    if mobile:
        W, size, px, tx, header, pitch, first, bottom, label_size = MOBILE_W, 13, 16, 32, 36, 23, 60, 24, 13
    else:
        W, size, px, tx, header, pitch, first, bottom, label_size = 840, 16, 24, 48, 44, 30, 68, 32, 16
    adv = size * 0.6
    maxc = int((W - tx - px) // adv)
    rows = []
    for item in items:
        for i, line in enumerate(wrap(item, maxc)):
            rows.append((line, i == 0))
    H = first + pitch * (len(rows) - 1) + bottom

    css, body = [], []
    body.append(f'<rect class="panel" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10"/>')
    hy = header / 2
    body.append("".join(f'<circle class="chrome" cx="{px + 4 + i * 13}" cy="{num(hy)}" r="3.5"/>' for i in range(3)))
    body.append(f'<g class="label">{at.text("mono", label_size, "~/now", px + 52, hy + label_size * 0.36)}</g>')
    body.append(f'<path class="rule" d="M1 {num(header + .5)}H{W - 1}"/>')

    t0 = 0.8
    for i, (line, is_first) in enumerate(rows):
        y = first + i * pitch
        n = len(line)
        if i and is_first:
            t0 += 0.3
        dur = round(n * 0.035, 2)
        if is_first:
            body.append(f'<g class="pr p{i}">{at.text("mono", size, "›", px, y)}</g>')
            css.append(f".p{i}{{animation:hide .01s {t0:.2f}s backwards}}")
        body.append(f'<g class="txt">{at.text("mono", size, line, tx, y)}</g>')
        body.append(f'<rect class="cover c{i}" x="{num(tx - .5)}" y="{num(y - size)}" '
                    f'width="{num(n * adv + 1)}" height="{num(size * 1.35)}"/>')
        body.append(f'<rect class="caret mv m{i}" x="{num(tx)}" y="{num(y - size * .8)}" '
                    f'width="{num(adv - 1)}" height="{num(size * 1.05)}"/>')
        css.append(f".c{i}{{animation:type {dur}s steps({n},end) {t0:.2f}s both}}")
        css.append(f".m{i}{{animation:k{i} {dur}s steps({n},end) {t0:.2f}s forwards,vis {dur}s step-end {t0:.2f}s forwards}}"
                   f"@keyframes k{i}{{to{{transform:translateX({num(n * adv)}px)}}}}")
        t0 += dur + 0.06
    last, _ = rows[-1]
    ly = first + (len(rows) - 1) * pitch
    body.append(f'<rect class="caret blink" x="{num(tx + len(last) * adv)}" y="{num(ly - size * .8)}" '
                f'width="{num(adv - 1)}" height="{num(size * 1.05)}"/>')
    return tpl("now", w=W, h=H, title="Now", desc=esc("Now: " + "; ".join(items) + "."),
               defs=at.defs_svg(), body="".join(body), lines="\n".join(css), blink_delay=f"{t0:.2f}", **t)


# ---------------------------------------------------------------- divider, chips

def rule_svg(t: dict, b: Build) -> str:
    W, H, pw = 840, 12, 72
    body = (f'<path class="rule" d="M0 6.5H{W}"/><rect class="node" x="{W / 2 - 3}" y="3.5" width="6" height="6" rx="1.5"/>'
            f'<rect class="pulse" x="-{pw}" y="5.5" width="{pw}" height="2" fill="url(#pg)"/>')
    return tpl("rule", w=W, h=H, title="Divider", body=body, dist=W + pw, **t)


def chip_svg(t: dict, b: Build, key: str) -> str:
    at = GlyphAtlas("g")
    label = LINK_LABELS[key]
    lw = at.width("sans", 13, label)
    W, H = int(12 + 16 + 8 + lw + 16), 32
    body = (f'<rect class="chip" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{(H - 1) / 2}"/>'
            f'<g class="glyph" transform="translate(12 8)">{LINK_GLYPHS[key]}</g>'
            f'<g class="label">{at.text("sans", 13, label, 36, 20.5)}</g>')
    return tpl("chip", w=W, h=H, title=esc(label), defs=at.defs_svg(), body=body, **t)


# ---------------------------------------------------------------- project cards

def month_year(date: str) -> str:
    return dt.date.fromisoformat(date).strftime("%b %Y")


def card_svg(t: dict, b: Build, repo: dict, blurb: str, mobile: bool = False) -> str:
    at = GlyphAtlas("g")  # used only for measuring (Inter metrics >= system sans widths: conservative)
    if mobile:
        W, H, pad, fs_name, fs_blurb, fs_meta, lh = MOBILE_W, 164, 22, 16, 14, 13, 21
    else:
        W, H, pad, fs_name, fs_blurb, fs_meta, lh = 410, 150, 24, 15, 13, 12, 20
    max_w = (W - 2 * pad) / 1.06
    lines = wrap_width(at, "sans", fs_blurb, blurb, max_w) if blurb else []
    if len(lines) > 2:
        second = lines[1]
        while second and at.width("sans", fs_blurb, second + "…") > max_w:
            second = second.rsplit(" ", 1)[0] if " " in second else second[:-1]
        lines = [lines[0], second.rstrip(",.;:") + "…"]
    body = [f'<rect class="panel" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10"/>',
            f'<path class="edge" d="M1.5 18V{H - 18}"/>',
            f'<text class="name" x="{pad}" y="42">{esc(repo["name"])}</text>']
    for i, line in enumerate(lines):
        body.append(f'<text class="blurb" x="{pad}" y="{70 + i * lh}">{esc(line)}</text>')
    x, fy = pad, H - 24
    meta = []
    if repo.get("language"):
        color = b.gh.get("language_colors", {}).get(repo["language"], t["muted"])
        body.append(f'<circle cx="{x + 5}" cy="{num(fy - fs_meta / 3)}" r="5" fill="{color}"/>')
        x += 16
        meta.append(repo["language"])
    if repo.get("stars", 0) > 0:
        meta.append(f"★ {repo['stars']}")
    meta.append(f"updated {month_year(repo['pushed'])}")
    for topic in repo.get("topics", [])[: b.cfg["selected_work"]["max_topics"]]:
        cand = meta + [f"#{topic}"]
        if at.width("sans", fs_meta, "  ·  ".join(cand)) * 1.06 > W - pad - x:
            break
        meta = cand
    body.append(f'<text class="meta" x="{x}" y="{fy}" xml:space="preserve">{esc("  ·  ".join(meta))}</text>')
    return tpl("card", w=W, h=H, title=esc(repo["name"]), desc=esc(blurb or repo["name"]),
               body="".join(body), edge_len=H - 36, fs_name=fs_name, fs_blurb=fs_blurb, fs_meta=fs_meta, **t)


# ---------------------------------------------------------------- signal

def stats_svg(t: dict, b: Build, tiles: list[tuple[str, str]], mobile: bool) -> str:
    if mobile:
        W, cols, val_size, lbl_size = MOBILE_W, 2, 26, 13
        th = 100
        H = th * ((len(tiles) + 1) // 2)
    else:
        W, cols, val_size, lbl_size = 840, len(tiles), 30, 16
        th = H = 118
    tw = W / cols
    body = [f'<rect class="panel" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10"/>']
    delays = []
    for i, (label, value) in enumerate(tiles):
        c, r = i % cols, i // cols
        x, y = c * tw + 24, r * th
        if c:
            body.append(f'<path class="sep" d="M{num(c * tw)} {num(y + 18)}V{num(y + th - 18)}"/>')
        if r and c == 0:
            body.append(f'<path class="sep" d="M18 {num(y)}H{W - 18}"/>')
        body.append(f'<text class="val" x="{num(x)}" y="{num(y + 44)}">{esc(value)}</text>')
        body.append(f'<path class="ul u{i}" d="M{num(x)} {num(y + 54)}h28"/>')
        at = GlyphAtlas("g")
        for j, part in enumerate(wrap_width(at, "sans", lbl_size, label, (tw - 36) / 1.06)[:2]):
            body.append(f'<text class="lbl" x="{num(x)}" y="{num(y + 54 + lbl_size * 1.45 + j * lbl_size * 1.3)}">{esc(part)}</text>')
        delays.append(f".u{i}{{animation-delay:{0.2 + i * 0.12:.2f}s}}")
    desc = "; ".join(f"{label}: {value}" for label, value in tiles)
    return tpl("stats", w=W, h=H, title="GitHub stats", desc=esc(desc), body="".join(body), delays="".join(delays),
               val_size=val_size, lbl_size=lbl_size, **t)


def activity_svg(t: dict, b: Build, mobile: bool) -> str:
    weeks = b.gh["contributions"]["weeks"]
    total = b.gh["contributions"]["total_12mo"]
    W, H, fs = (MOBILE_W, 150, 13) if mobile else (840, 140, 16)
    left, right, top, base = 20, 20, 44, (112 if mobile else 100)
    step = (W - left - right) / len(weeks)
    bw = max(2.0, step * 0.62)
    peak = max((w["count"] for w in weeks), default=0) or 1
    maxh = base - top
    body = [f'<rect class="panel" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10"/>']
    body.append(f'<text class="cap" x="{left}" y="{fs + 12}"><tspan class="capv">{total}</tspan> '
                f'{esc(b.cfg["labels"]["activity_caption"])}</text>')
    delays, last_month = [], None
    for i, w in enumerate(weeks):
        x = left + i * step + (step - bw) / 2
        if w["count"]:
            h = max(3.0, maxh * w["count"] / peak)
            body.append(f'<rect class="bar b{i}" x="{num(x)}" y="{num(base - h)}" width="{num(bw)}" height="{num(h)}" rx="1"/>')
            delays.append(f".b{i}{{animation-delay:{0.2 + i * 0.02:.2f}s}}")
        else:
            body.append(f'<rect class="zero" x="{num(x)}" y="{base - 2}" width="{num(bw)}" height="2" rx="1"/>')
        month = w["start"][5:7]
        if month != last_month:
            if last_month is not None:
                initial = dt.date.fromisoformat(w["start"]).strftime("%b")[0]
                body.append(f'<text class="axis" x="{num(x)}" y="{base + fs + 8}">{initial}</text>')
            last_month = month
    desc = f"{total} {b.cfg['labels']['activity_caption']}"
    return tpl("activity", w=W, h=H, title="Contribution activity", desc=esc(desc),
               body="".join(body), delays="".join(delays), fs=fs, **t)


def languages_svg(t: dict, b: Build, mobile: bool) -> str:
    share = b.gh["language_share"]
    colors = b.gh.get("language_colors", {})
    W, fs, rh = (MOBILE_W, 13, 26) if mobile else (840, 16, 30)
    cols = 2 if mobile else min(3, len(share))
    rows = -(-len(share) // cols)
    H = 44 + rows * rh + 8
    x, bar_w = 20, W - 40
    body, delays, defs = [], [], f'<clipPath id="bar"><rect x="20" y="14" width="{bar_w}" height="10" rx="5"/></clipPath>'
    body.append(f'<rect class="track" x="20" y="14" width="{bar_w}" height="10" rx="5"/><g clip-path="url(#bar)">')
    for i, s in enumerate(share):
        seg = bar_w * float(s["pct"]) / 100
        color = colors.get(s["name"], t["faint"])
        body.append(f'<rect class="seg s{i}" x="{num(x)}" y="14" width="{num(seg + (0 if i == len(share) - 1 else 1))}" height="10" fill="{color}"/>')
        delays.append(f".s{i}{{animation-delay:{0.2 + i * 0.1:.2f}s}}")
        x += seg
    body.append("</g>")
    cw = (W - 40) / cols
    for i, s in enumerate(share):
        c, r = i % cols, i // cols
        lx, ly = 20 + c * cw, 52 + r * rh
        color = colors.get(s["name"], t["faint"])
        body.append(f'<circle cx="{num(lx + 5)}" cy="{ly - 4}" r="5" fill="{color}"/>'
                    f'<text class="lbl" x="{num(lx + 16)}" y="{ly}">{esc(s["name"])} '
                    f'<tspan class="pct">{s["pct"]}%</tspan></text>')
    desc = "Languages by bytes across public repos: " + ", ".join(f'{s["name"]} {s["pct"]}%' for s in share)
    return tpl("languages", w=W, h=H, title="Languages", desc=esc(desc), defs=defs,
               body="".join(body), delays="".join(delays), fs=fs, **t)


# ---------------------------------------------------------------- README

def picture(dark: str, light: str, alt: str, mdark: str | None = None, mlight: str | None = None, bp: int = 767) -> str:
    """Theme-aware <picture>, optionally with narrow-viewport variants.

    GitHub's <themed-picture> script replaces the WHOLE media string of every theme source when a
    signed-in viewer has an explicit (non-auto) theme: the active theme becomes always-true and the
    other becomes `not all`. So desktop sources go first with a min-width condition; for those
    viewers the first source of their theme wins (desktop art, correct theme) instead of the
    mobile art leaking onto wide screens.
    """
    src = ["<picture>"]
    if mdark:
        src.append(f'  <source media="(prefers-color-scheme: dark) and (min-width: {bp + 1}px)" srcset="{dark}">')
        src.append(f'  <source media="(prefers-color-scheme: light) and (min-width: {bp + 1}px)" srcset="{light}">')
        src.append(f'  <source media="(prefers-color-scheme: dark)" srcset="{mdark}">')
        src.append(f'  <source media="(prefers-color-scheme: light)" srcset="{mlight}">')
    else:
        src.append(f'  <source media="(prefers-color-scheme: dark)" srcset="{dark}">')
    src.append(f'  <img src="{light}" alt="{esc(alt)}">')
    src.append("</picture>")
    return "\n".join(src)


def section(title: str, inner: str) -> str:
    return f'<div align="center">\n\n## {title}\n\n{inner}\n\n</div>'


def build(b: Build) -> dict[str, str]:
    p, gh, cfg = b.profile, b.gh, b.cfg
    th = cfg["thresholds"]
    regions = {k: "" for k in REGIONS}
    login = cfg["login"]

    # 1 hero (always)
    hd, hl = b.pair("assets/hero/hero", hero_svg, b=b, mobile=False)
    md, ml = b.pair("assets/hero/hero-mobile", hero_svg, b=b, mobile=True)
    alt = p["name"].strip() + (f" — {p['positioning'].strip()}" if nonempty(p.get("positioning")) else "")
    pic = picture(hd, hl, alt, md, ml, b.bp)
    site = (p.get("links") or {}).get("website", "")
    if nonempty(site):
        pic = f'<a href="{esc(site)}">\n{pic}\n</a>'
    regions["hero"] = f'<p align="center">\n{pic}\n</p>'

    # 2 now panel
    now = [s for s in p.get("now") or [] if nonempty(s)]
    if now:
        nd, nl = b.pair("assets/panels/now", now_svg, b=b, mobile=False)
        mnd, mnl = b.pair("assets/panels/now-mobile", now_svg, b=b, mobile=True)
        regions["now"] = f'<p align="center">\n{picture(nd, nl, "Now: " + "; ".join(s.strip() for s in now), mnd, mnl, b.bp)}\n</p>'

    # 3 intro
    if nonempty(p.get("about")):
        regions["about"] = f'<p align="center">\n{esc_text(p["about"].strip())}\n</p>'

    # 4 link chips
    links = {k: v.strip() for k, v in (p.get("links") or {}).items() if nonempty(v) and k in LINK_LABELS}
    if links:
        chips = []
        for key, value in links.items():
            d, l = b.pair(f"assets/chips/{key}", chip_svg, b=b, key=key)
            href = f"mailto:{value}" if key == "email" and not value.startswith("mailto:") else value
            chips.append(f'<a href="{esc(href)}">{picture(d, l, LINK_LABELS[key])}</a>')
        regions["links"] = '<p align="center">\n' + "\n".join(chips) + "\n</p>"

    # 5 selected work
    repos = {r["name"]: r for r in gh.get("repos", [])}
    featured = [n for n in (p.get("featured_repos") or []) if n in repos]
    if not featured:
        ranked = sorted(repos.values(), key=lambda r: r["pushed"], reverse=True)  # most recent first,
        ranked = sorted(ranked, key=lambda r: r["stars"], reverse=True)            # then most starred
        featured = [r["name"] for r in ranked[: cfg["selected_work"]["max_cards"]]]
    if featured:
        blurbs = p.get("repo_blurbs") or {}
        cards = []
        for name in featured:
            repo = repos[name]
            blurb = (blurbs.get(name) or repo.get("description") or "").strip()
            d, l = b.pair(f"assets/projects/{name}", card_svg, b=b, repo=repo, blurb=blurb)
            md_, ml_ = b.pair(f"assets/projects/{name}-mobile", card_svg, b=b, repo=repo, blurb=blurb, mobile=True)
            alt_c = name + (": " + blurb if blurb else "")
            cards.append(f'<a href="{esc(repo["url"])}">{picture(d, l, alt_c, md_, ml_, b.bp)}</a>')
        regions["work"] = section("Selected work", '<p align="center">\n' + "\n".join(cards) + "\n</p>")

    # 6 toolkit
    stack = {k: [s for s in (v or []) if nonempty(s)] for k, v in (p.get("stack") or {}).items()}
    stack = {k: v for k, v in stack.items() if v}
    if stack:
        rows = "\n".join(f'  <tr><th align="left">{esc_text(k)}</th><td>{" · ".join(esc_text(s) for s in v)}</td></tr>'
                         for k, v in stack.items())
        regions["toolkit"] = section("Toolkit", f"<table>\n{rows}\n</table>")

    # 7 signal
    labels = cfg["labels"]
    blocks = []
    if gh["eligible_public_repos"] >= th["stats_min_public_repos"]:
        tiles = [(labels["public_repos"], str(gh["eligible_public_repos"]))]
        if gh["stars_earned"] > 0:
            tiles.append((labels["stars"], str(gh["stars_earned"])))
        tiles.append((labels["contributions"], str(gh["contributions"]["total_12mo"])))
        if p.get("show_private_contribution_count") and gh.get("private_contributions_12mo", 0) > 0:
            tiles.append((labels["private_contributions"], str(gh["private_contributions_12mo"])))
        d, l = b.pair("assets/stats/stats", stats_svg, b=b, tiles=tiles, mobile=False)
        md_, ml_ = b.pair("assets/stats/stats-mobile", stats_svg, b=b, tiles=tiles, mobile=True)
        blocks.append(picture(d, l, "; ".join(f"{a}: {v}" for a, v in tiles), md_, ml_, b.bp))
    if gh["contributions"]["total_12mo"] >= th["activity_min_contributions"]:
        d, l = b.pair("assets/stats/activity", activity_svg, b=b, mobile=False)
        md_, ml_ = b.pair("assets/stats/activity-mobile", activity_svg, b=b, mobile=True)
        blocks.append(picture(d, l, f'{gh["contributions"]["total_12mo"]} {labels["activity_caption"]}', md_, ml_, b.bp))
    if gh.get("repos_with_language_bytes", 0) >= th["languages_min_repos"] and gh.get("language_share"):
        d, l = b.pair("assets/stats/languages", languages_svg, b=b, mobile=False)
        md_, ml_ = b.pair("assets/stats/languages-mobile", languages_svg, b=b, mobile=True)
        alt_l = "Languages: " + ", ".join(f'{s["name"]} {s["pct"]}%' for s in gh["language_share"])
        blocks.append(picture(d, l, alt_l, md_, ml_, b.bp))
    if blocks:
        regions["signal"] = section("Signal", '<p align="center">\n' + "\n<br><br>\n".join(blocks) + "\n</p>")

    # 8 principles
    principles = [s.strip() for s in (p.get("principles") or []) if nonempty(s)][:3]
    if principles:
        regions["principles"] = section("How I work", "\n".join(f'<p align="center">{esc_text(s)}</p>' for s in principles))

    # 9 footer (always)
    rd, rl = b.pair("assets/dividers/rule", rule_svg, b=b)
    wf = f"https://github.com/{login}/{login}/actions/workflows/refresh.yml"
    regions["footer"] = (f'<p align="center">\n{picture(rd, rl, "Divider")}\n<br>\n'
                         f'<sub><a href="{wf}">Auto-updated · {gh["last_changed"]}</a></sub>\n</p>')
    return regions


def write_readme(b: Build, regions: dict[str, str]) -> None:
    path = b.out / "README.md"
    text = path.read_text(encoding="utf-8") if path.exists() else (TPL / "README.md.tpl").read_text(encoding="utf-8")
    for key, content in regions.items():
        pat = re.compile(rf"(<!-- START:{key} -->)(.*?)(<!-- END:{key} -->)", re.S)
        if not pat.search(text):
            raise SystemExit(f"build: README is missing the {key} markers")
        inner = f"\n{content}\n" if content else "\n"
        text = pat.sub(lambda m: m.group(1) + inner + m.group(3), text, count=1)
    path.write_text(text, encoding="utf-8", newline="\n")


def clean_stale(b: Build) -> list[str]:
    removed = []
    for sub in MANAGED:
        d = b.out / "assets" / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.svg")):
            rel = f.relative_to(b.out).as_posix()
            if rel not in b.produced:
                f.unlink()
                removed.append(rel)
    return removed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "github.json")
    ap.add_argument("--profile", type=Path, default=ROOT / "data" / "profile.yml")
    ap.add_argument("--out", type=Path, default=ROOT)
    args = ap.parse_args()
    b = Build(args.out.resolve(), args.data.resolve(), args.profile.resolve())
    regions = build(b)
    write_readme(b, regions)
    removed = clean_stale(b)
    shown = [k for k, v in regions.items() if v]
    hidden = [k for k, v in regions.items() if not v]
    print(f"build: {len(b.produced)} assets; sections shown: {', '.join(shown)}; hidden: {', '.join(hidden) or 'none'}"
          + (f"; removed stale: {', '.join(removed)}" if removed else ""))


if __name__ == "__main__":
    main()
