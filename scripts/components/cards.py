""""In motion" cards: one SVG per card, so each can carry its own link. Cards in a row are rendered
at the row's tallest height, so the grid stays even; the stack chips (and the link) sit on the
card's floor, so any spare height opens between the copy and the chips, never under them.

Each card's name and description come from its profile.yml `now` line, split verbatim at the
first ":" or " — ". Everything else comes from data/projects.yml, and an empty field is not drawn:
type tag, status (none when empty), a quiet confidentiality tag (only when `confidential: true`),
stack chips and the link.
"""
from __future__ import annotations

import re

from svgkit import num

from .base import Doc, balanced, wrap

TIER = {
    #          width pad desc_fs chip_fs chip_pad name_fs glyph_h chip_pitch
    "desktop": (414, 20, 15, 12, 9, 20, 72, 30),
    "mid":     (285, 16, 14, 12, 5.5, 18, 60, 28),
    "mobile":  (360, 20, 15, 12, 9, 20, 72, 30),
}
CHIP_GAP = {"desktop": 6, "mid": 4, "mobile": 6}
RUNS = [7.3, 8.9, 10.1, 11.3, 9.7, 12.7]
CONFIDENTIAL = "CONFIDENTIAL"
SEPARATORS = (":", " — ")


def split_now(text: str) -> tuple[str, str, str]:
    """(name, separator, description): split at whichever separator comes first. Nothing is added,
    dropped or reworded; only the whitespace around the split is trimmed."""
    hits = [(text.find(s), s) for s in SEPARATORS if text.find(s) > 0]
    if not hits:
        return text.strip(), "", ""
    i, sep = min(hits)
    return text[:i].strip(), sep.strip(), text[i + len(sep):].strip()


def motion_cards(profile: dict, projects: dict) -> list[dict]:
    now = [s.strip() for s in profile.get("now") or [] if s.strip()]
    entries = (projects or {}).get("building") or []
    out = []
    for i, text in enumerate(now):
        e = entries[i] if i < len(entries) else {}
        name, sep, desc = split_now(text)
        link = (e.get("link") or "").strip()
        out.append({
            "id": str(e.get("id") or f"{i + 1:02d}"),
            "type": (e.get("type") or "").strip(),
            "name": name,
            "sep": sep,
            "desc": (e.get("summary") or "").strip() or desc,
            "stack": [s.strip() for s in e.get("stack") or [] if s and s.strip()],
            "status": (e.get("status") or "").strip(),
            "confidential": e.get("confidential") is True,
            "link": link,
            "link_text": re.sub(r"^https?://(www\.)?", "", link).rstrip("/"),
            "glyph": e.get("glyph") or ("documents", "availability", "browser", "challenge")[i % 4],
        })
    return out


def alt(c: dict) -> str:
    head = f"{c['id']}. " + (f"{c['type']}. " if c["type"] else "")
    body = c["name"] + (f"{' — ' if c['sep'] == '—' else ': '}{c['desc']}" if c["desc"] else "")
    parts = [head + body]  # the `now` line stays verbatim: no punctuation is added to it
    if c["status"]:
        parts.append(f"Status: {c['status']}.")
    if c["confidential"]:
        parts.append("Confidential.")
    if c["stack"]:
        parts.append(f"Stack: {', '.join(c['stack'])}.")
    if c["link_text"]:
        parts.append(f"Link: {c['link_text']}.")
    return parts[0] + (" · " + " ".join(parts[1:]) if len(parts) > 1 else "")


# ------------------------------------------------------------------ layout

def _tags(d: Doc, c: dict) -> list[tuple[str, float]]:
    out = []
    if c["status"]:
        out.append(("status", d.width("mono", 12, c["status"], .8) + 18))
    if c["confidential"]:
        out.append(("conf", d.width("mono", 11, CONFIDENTIAL, 1.2) + 22))
    return out


def measure(c: dict, tier: str) -> dict:
    W, pad, desc_fs, chip_fs, chip_pad, name_fs, glyph_h, pitch = TIER[tier]
    d = Doc(W, {})
    inner = W - 2 * pad
    tags = _tags(d, c)
    idw = d.width("mono", 14, c["id"]) + 16
    row1 = sum(w for _, w in tags) + 8 * max(len(tags) - 1, 0)
    # tags ride on the id row; if they don't fit, the last one drops to a second header row
    split = bool(tags) and idw + row1 > inner and len(tags) > 1
    extra = 26 if split else 0
    names = balanced(d, "display", name_fs, c["name"].split(" "), " ", inner) if c["name"] else []
    lines = wrap(d, "sans", desc_fs, c["desc"], inner) if c["desc"] else []
    rows, cur, rw = [], [], 0.0
    for tool in c["stack"]:
        w = d.width("mono", chip_fs, tool) + 2 * chip_pad
        if cur and rw + w > inner:
            rows.append(cur)
            cur, rw = [], 0.0
        cur.append((tool, w))
        rw += w + CHIP_GAP[tier]
    if cur:
        rows.append(cur)
    top = 58 + extra
    upper = top + glyph_h + 22 + (22 if c["type"] else 0) + len(names) * (name_fs + 6) + 4 + len(lines) * (desc_fs + 7)
    lower = (len(rows) * pitch if rows else 0) + (26 if c["link"] else 0) + 14
    return {"tags": tags, "split": split, "extra": extra, "names": names, "lines": lines, "rows": rows,
            "upper": upper, "lower": lower, "height": upper + 10 + lower}


# ------------------------------------------------------------------ render

def render(t: dict, c: dict, tier: str, width: int, height: float, idx: int = 0) -> tuple[str, int]:
    W, pad, desc_fs, chip_fs, chip_pad, name_fs, glyph_h, pitch = TIER[tier]
    m = measure(c, tier)
    H = max(height, m["height"])
    d = Doc(W, t)
    inner = W - 2 * pad
    rect = f'x=".5" y=".5" width="{W - 1}" height="{num(H - 1)}" rx="10"'
    d.add(f'<rect class="panel" {rect}/><rect class="run" {rect} pathLength="1000" stroke-dasharray="90 910"/>')
    d.animate("run", f"animation:run {RUNS[idx % len(RUNS)]}s linear {-idx * 2.1:.1f}s infinite")
    d.keyframes("run", "to{stroke-dashoffset:-1000}")

    # header: id .......... status · confidential (the last tag drops a row when narrow)
    hy = 34
    d.add(f'<g class="idx">{d.text("mono", 14, c["id"], pad, hy)}</g>')
    tags = list(m["tags"])
    rows_ = [tags[:-1], tags[-1:]] if m["split"] else [tags]
    for r_i, row in enumerate(rows_):
        rx_ = W - pad
        ty = hy + r_i * 26
        for kind, w in reversed(row):
            if kind == "conf":
                d.add(f'<rect class="tag" x="{num(rx_ - w + .5)}" y="{num(ty - 14.5)}" width="{num(w - 1)}" height="19" rx="9.5"/>')
                d.add(d.mono_text(11, CONFIDENTIAL, rx_ - 11, ty - 1, "tt", "end", 1.2))
            else:
                sw = w - 18
                lx, ly = rx_ - sw - 10, ty - 5
                s = c["status"].lower()
                if s == "concept":
                    # a concept is not running: an open, dashed ring that turns slowly, no light
                    d.add(f'<circle class="scon" cx="{num(lx)}" cy="{num(ly)}" r="3.6" stroke-dasharray="2.2 1.6"/>')
                    d.animate("scon", f"transform-origin:{num(lx)}px {num(ly)}px;animation:spin 9.7s linear infinite")
                    d.keyframes("spin", "to{transform:rotate(360deg)}")
                else:
                    d.add(f'<circle class="sled{" ok" if s == "live" else ""}" cx="{num(lx)}" cy="{num(ly)}" r="3.2"/>')
                    d.animate("sled", "animation:led 2.3s ease-in-out infinite", "led")
                d.add(d.mono_text(12, c["status"], rx_, ty - 1, "st", "end", .8))
            rx_ -= w + 8
    d.add(f'<path class="hr" d="M{pad} {48.5 + m["extra"]}H{W - pad}"/>')

    top = 58 + m["extra"]
    d.add(GLYPHS[c["glyph"]](d, t, pad, top, inner, glyph_h))

    y = top + glyph_h + 22
    if c["type"]:
        y += 4
        d.add(d.mono_text(11, c["type"].upper(), pad, y, "kind", "start", 1.6))
        y += 18
    for j, ln in enumerate(m["names"]):
        y += name_fs + (0 if j == 0 else 6)
        d.add(f'<g class="nm">{d.text("display", name_fs, ln, pad, y)}</g>')
    y += 6
    for j, ln in enumerate(m["lines"]):
        y += desc_fs + (4 if j == 0 else 7)
        d.add(d.body_text(desc_fs, ln, pad, y, "sum"))

    # floor: chips, then the link
    cyy = H - m["lower"] + 2
    n = 0
    for row in m["rows"]:
        cx = pad
        for tool, w in row:
            d.add(f'<g class="c{n}"><rect class="tchip" x="{num(cx + .5)}" y="{num(cyy + .5)}" width="{num(w - 1)}" height="23" rx="11.5"/>'
                  + d.mono_text(chip_fs, tool, cx + chip_pad, cyy + 16, "ttool") + "</g>")
            d.animate(f"c{n}", f"animation:fade .5s ease-out {.4 + n * .1:.2f}s backwards", "fade")
            cx += w + CHIP_GAP[tier]
            n += 1
        cyy += pitch
    if c["link"]:
        ly = H - 22
        # the arrow leads, so its spacing never depends on the system font's width
        d.add(f'<g class="arr">{d.text("mono", 12, "↗", pad, ly)}</g>')
        d.add(d.mono_text(12, c["link_text"], pad + 16, ly, "lnk"))
        d.animate("arr", "animation:nudge 2.7s ease-in-out infinite")
        d.keyframes("nudge", "0%,70%,100%{transform:translate(0,0)}80%{transform:translate(2px,-2px)}")

    ok = t.get("success", t["accent"])
    d.rule(f".panel{{fill:{t['surface']};stroke:{t['line']}}}.run{{fill:none;stroke:{t['accent']};stroke-width:1.5;stroke-linecap:round;stroke-opacity:.9}}"
           f".idx,.kind{{fill:{t['accent_text']}}}.nm{{fill:{t['text']}}}.st,.tt,.ttool{{fill:{t['muted']}}}.hr{{stroke:{t['line']}}}"
           f".sled{{fill:{t['accent']}}}.sled.ok{{fill:{ok}}}.scon{{fill:none;stroke:{t['accent2']};stroke-width:1.4}}"
           f".tag{{fill:none;stroke:{t['line_strong']};stroke-dasharray:3 2}}.tchip{{fill:none;stroke:{t['line_strong']}}}"
           f".wire{{stroke:{t['line_strong']};fill:none}}.node{{fill:{t['bg']};stroke:{t['line_strong']}}}"
           f".ic{{fill:none;stroke:{t['text']};stroke-width:1.3;stroke-linecap:round;stroke-linejoin:round}}"
           f".dat{{fill:{t['accent']}}}.ring{{fill:none;stroke:{t['accent']}}}.sum{{fill:{t['muted']}}}.lnk,.arr{{fill:{t['accent_text']}}}"
           + GLYPH_CSS[c["glyph"]](t))
    return d.render(H, c["name"] or c["id"], alt(c)), d.anim


# ------------------------------------------------------------------ glyphs

def _flow(d: Doc, path: str, n: int = 2, period: float = 3.7, key: str = "f") -> str:
    out = []
    for j in range(n):
        out.append(f'<circle class="dat {key}{j}" r="2.2"/>')
        d.animate(f"{key}{j}", f"offset-path:path('{path}');animation:flow {period}s cubic-bezier(.5,0,.5,1) {-j * period / n:.2f}s infinite")
    d.keyframes("flow", "0%{offset-distance:0%;opacity:0}12%{opacity:1}88%{opacity:1}100%{offset-distance:100%;opacity:0}")
    return "".join(out)


def g_documents(d: Doc, t: dict, x, y, w, h) -> str:
    """documents -> index -> search"""
    cy, p = y + h / 2, []
    for j in range(3):
        dx, dy = x + j * 5, y + 14 + j * 5
        p.append(f'<g class="doc{" top" if j == 2 else ""}"><rect x="{num(dx)}" y="{num(dy)}" width="30" height="38" rx="3"/>'
                 f'<path class="docl" d="M{num(dx + 6)} {num(dy + 10)}h18M{num(dx + 6)} {num(dy + 17)}h18M{num(dx + 6)} {num(dy + 24)}h12"/></g>')
    d.animate("top", "animation:ingest 6.1s cubic-bezier(.2,.7,.2,1) 1s infinite")
    d.keyframes("ingest", "0%{transform:translateY(-6px);opacity:0}10%,100%{transform:translateY(0);opacity:1}")
    n1, n2, a = x + w * .56, x + w - 13, x + 52
    p.append(f'<path class="wire" d="M{num(a)} {num(cy)}H{num(n1 - 13)}M{num(n1 + 13)} {num(cy)}H{num(n2 - 13)}"/>')
    p.append(f'<rect class="node" x="{num(n1 - 12)}" y="{num(cy - 12)}" width="24" height="24" rx="5"/>' + d.icon("index", n1 - 8, cy - 8))
    p.append(f'<circle class="node" cx="{num(n2)}" cy="{num(cy)}" r="12"/>' + d.icon("search", n2 - 8, cy - 8))
    p.append(f'<circle class="ring" cx="{num(n2)}" cy="{num(cy)}" r="12"/>')
    d.animate("ring", f"transform-origin:{num(n2)}px {num(cy)}px;animation:ping 3.7s ease-out 1.6s infinite")
    d.keyframes("ping", "0%{transform:scale(1);opacity:.8}60%,100%{transform:scale(1.7);opacity:0}")
    p.append(_flow(d, f"M{num(a)} {num(cy)}H{num(n2 - 13)}"))
    return "".join(p)


def g_availability(d: Doc, t: dict, x, y, w, h) -> str:
    """live-availability grid -> scheduler -> admin console"""
    cy, p = y + h / 2, []
    cols, rows_, cs, gp = 6, 3, 11, 5
    gw = cols * cs + (cols - 1) * gp
    gy = cy - (rows_ * cs + (rows_ - 1) * gp) / 2
    for rr in range(rows_):
        for cc in range(cols):
            p.append(f'<rect class="cell" x="{num(x + cc * (cs + gp))}" y="{num(gy + rr * (cs + gp))}" width="{cs}" height="{cs}" rx="2.5"/>')
    p.append(f'<rect class="hot hop" x="{num(x)}" y="{num(gy)}" width="{cs}" height="{cs}" rx="2.5"/>')
    hops = [(1, 0), (4, 1), (2, 2), (5, 0), (0, 1), (3, 2)]
    frames = "".join(f"{j * 100 / len(hops):.1f}%{{transform:translate({c * (cs + gp)}px,{r * (cs + gp)}px)}}" for j, (c, r) in enumerate(hops))
    d.animate("hop", "animation:hop 6.3s steps(1,end) infinite")
    d.keyframes("hop", frames + f"100%{{transform:translate({hops[0][0] * (cs + gp)}px,0)}}")
    n1, n2 = x + gw + (w - gw) * .45, x + w - 12
    p.append(f'<path class="wire" d="M{num(x + gw + 4)} {num(cy)}H{num(n1 - 12)}M{num(n1 + 12)} {num(cy)}H{num(n2 - 12)}"/>')
    p.append(f'<circle class="node" cx="{num(n1)}" cy="{num(cy)}" r="11"/>' + d.icon("clock", n1 - 8, cy - 8))
    p.append(f'<rect class="node" x="{num(n2 - 11)}" y="{num(cy - 11)}" width="22" height="22" rx="5"/>' + d.icon("console", n2 - 8, cy - 8))
    p.append(_flow(d, f"M{num(x + gw + 4)} {num(cy)}H{num(n2 - 12)}"))
    return "".join(p)


def g_browser(d: Doc, t: dict, x, y, w, h) -> str:
    """a live site: browser window with content scrolling (scroll-driven motion)"""
    p = [f'<rect class="win" x="{num(x + .5)}" y="{num(y + 4.5)}" width="{num(w - 1)}" height="{h - 9}" rx="6"/>']
    p.append("".join(f'<circle class="dotc" cx="{num(x + 12 + k * 9)}" cy="{num(y + 14)}" r="2.5"/>' for k in range(3)))
    p.append(f'<rect class="blk" x="{num(x + 44)}" y="{num(y + 10)}" width="{num(w * .45)}" height="8" rx="4"/>')
    top, bottom = y + 24, y + h - 6
    d.defs.append(f'<clipPath id="vp"><rect x="{num(x + 1)}" y="{num(top)}" width="{num(w - 2)}" height="{num(bottom - top)}"/></clipPath>')
    blocks = [(0, .9, 16, "hotb"), (22, .6, 6, "blk"), (32, .75, 6, "blk"), (46, .4, 14, "blk"), (66, .85, 16, "hotb"), (88, .55, 6, "blk"),
              (98, .7, 6, "blk"), (112, .9, 16, "hotb")]
    inner = "".join(f'<rect class="{c}" x="{num(x + 12)}" y="{num(top + 6 + oy)}" width="{num((w - 24) * fr)}" height="{hh}" rx="3"/>'
                    for oy, fr, hh, c in blocks)
    p.append(f'<g clip-path="url(#vp)"><g class="scr">{inner}</g></g>')
    d.animate("scr", "animation:scrl 8.3s cubic-bezier(.45,0,.3,1) 1s infinite")
    d.keyframes("scrl", "0%,15%{transform:translateY(0)}45%,60%{transform:translateY(-44px)}90%,100%{transform:translateY(-66px)}")
    return "".join(p)


def g_challenge(d: Doc, t: dict, x, y, w, h) -> str:
    """validation: an idea is pushed through three narrowing gates; one candidate is stopped at a
    gate, one survives, smaller, into the smallest viable version"""
    cy, p = y + h / 2, []
    a, b = x + 13, x + w - 13
    gates = [a + 40 + k * (b - a - 80) / 2 for k in range(3)]
    gaps = [30, 20, 11]
    p.append(f'<path class="wire" stroke-dasharray="2 4" d="M{num(a + 13)} {num(cy)}H{num(b - 13)}"/>')
    for k, (gx, gap) in enumerate(zip(gates, gaps)):
        p.append(f'<g class="gate e{k}"><rect x="{num(gx - 1.5)}" y="{num(y + 8)}" width="3" height="{num(cy - gap / 2 - y - 8)}" rx="1.5"/>'
                 f'<rect x="{num(gx - 1.5)}" y="{num(cy + gap / 2)}" width="3" height="{num(y + h - 8 - cy - gap / 2)}" rx="1.5"/></g>')
        d.animate(f"e{k}", f"animation:led 5.3s ease-in-out {1 + k * .6:.1f}s infinite", "led")
    p.append(f'<circle class="node" cx="{num(a)}" cy="{num(cy)}" r="12"/>' + d.icon("challenge", a - 8, cy - 8))
    p.append(f'<rect class="node" x="{num(b - 12)}" y="{num(cy - 12)}" width="24" height="24" rx="5"/>' + d.icon("tick", b - 8, cy - 8))
    p.append(f'<rect class="ring" x="{num(b - 12)}" y="{num(cy - 12)}" width="24" height="24" rx="5"/>')
    d.animate("ring", f"transform-origin:{num(b)}px {num(cy)}px;animation:ping 5.3s ease-out 3.4s infinite")
    d.keyframes("ping", "0%{transform:scale(1);opacity:.8}60%,100%{transform:scale(1.5);opacity:0}")
    # the survivor shrinks as it passes each gate; the rejected candidate drops out at the second
    p.append('<circle class="dat pass" r="3"/>')
    d.animate("pass", f"offset-path:path('M{num(a + 13)} {num(cy)}H{num(b - 14)}');offset-distance:62%;animation:vpass 5.3s cubic-bezier(.4,0,.4,1) 1s infinite")
    d.keyframes("vpass", "0%{offset-distance:0%;transform:scale(1.9);opacity:0}8%{opacity:1}"
                         "90%{offset-distance:100%;transform:scale(.8);opacity:1}100%{offset-distance:100%;transform:scale(.8);opacity:0}")
    drop = f"M{num(a + 13)} {num(cy)}H{num(gates[1] - 7)}c4 0 5 3 5 {num(h / 2 - 12)}"
    p.append('<circle class="rej" r="2.6"/>')
    d.animate("rej", f"offset-path:path('{drop}');opacity:0;animation:vrej 5.3s cubic-bezier(.5,0,.6,1) 3.1s infinite")
    d.keyframes("vrej", "0%{offset-distance:0%;opacity:0}8%{opacity:.9}70%{opacity:.9}100%{offset-distance:100%;opacity:0}")
    return "".join(p)


GLYPH_CSS = {
    "documents": lambda t: f".doc{{fill:{t['bg']};stroke:{t['line_strong']}}}.docl{{stroke:{t['faint']}}}",
    "availability": lambda t: f".cell{{fill:{t['line']}}}.hot{{fill:{t['accent']}}}",
    "browser": lambda t: f".win{{fill:{t['bg']};stroke:{t['line_strong']}}}.blk{{fill:{t['line']}}}.hotb{{fill:{t['accent']};fill-opacity:.8}}.dotc{{fill:{t['faint']}}}",
    "challenge": lambda t: f".gate{{fill:{t['muted']};fill-opacity:.7}}.rej{{fill:{t['accent2']}}}",
}
GLYPH_CSS["audit"] = GLYPH_CSS["challenge"]

# projects.yml names card 04's drawing "audit"; it is drawn as the validation (challenge) glyph.
GLYPHS = {"documents": g_documents, "availability": g_availability, "browser": g_browser,
          "challenge": g_challenge, "audit": g_challenge}
