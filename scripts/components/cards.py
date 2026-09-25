"""Cards for "Currently building" and "Client work": one SVG per card, so each can carry its own
link. Cards in a row are rendered at the row's tallest height, so the grid stays even.

Every field is optional; an empty field is not drawn. Building cards show their id, status (where
set), PRIVATE (where private), an architecture glyph, the verbatim summary, stack chips and, when
`link` is set, the link. Client cards show the name, status, a PRIVATE CODE tag, a browser glyph,
summary, chips and the live-site link only where `link` is set.
"""
from __future__ import annotations

import re

from svgkit import num

from .base import Doc, wrap

TIER = {
    #          width pad sum_fs chip_fs chip_pad
    "desktop": (414, 20, 15, 12, 9),
    "mid":     (285, 16, 14, 12, 7),
    "mobile":  (360, 20, 15, 12, 9),
}
GLYPH_H = 72
RUNS = [7.3, 8.9, 10.1, 11.3, 9.7, 12.7]


def building_cards(profile: dict, projects: dict) -> list[dict]:
    now = [s.strip() for s in profile.get("now") or [] if s.strip()]
    entries = (projects or {}).get("building") or []
    out = []
    for i, text in enumerate(now):
        e = entries[i] if i < len(entries) else {}
        out.append(_card(e, kind="building", fallback_title=f"{i + 1:02d}", fallback_summary=text,
                         glyph=(e.get("glyph") or ("documents", "availability", "audit", "pipeline")[i % 4]),
                         private_label="PRIVATE"))
    return out


def client_cards(projects: dict) -> list[dict]:
    return [_card(e, kind="client", fallback_title="", fallback_summary="", glyph=e.get("glyph") or "browser",
                  private_label="PRIVATE CODE")
            for e in (projects or {}).get("client_work") or [] if (e.get("name") or "").strip()]


def _card(e: dict, kind: str, fallback_title: str, fallback_summary: str, glyph: str, private_label: str) -> dict:
    link = (e.get("link") or "").strip()
    title = (e.get("name") or "").strip() if kind == "client" else str(e.get("id") or fallback_title)
    return {
        "kind": kind,
        "title": title,
        "codename": (e.get("codename") or "").strip(),
        "summary": (e.get("summary") or "").strip() or fallback_summary,
        "stack": [s.strip() for s in e.get("stack") or [] if s and s.strip()],
        "status": (e.get("status") or "").strip(),
        "private": bool(e.get("private")),
        "private_label": private_label,
        "link": link,
        "link_text": re.sub(r"^https?://(www\.)?", "", link).rstrip("/"),
        "glyph": glyph,
    }


def alt(c: dict) -> str:
    parts = [f"{c['title']}: {c['summary']}"]
    if c["codename"]:
        parts.append(f"Codename {c['codename']}.")
    if c["status"]:
        parts.append(f"Status: {c['status']}.")
    if c["private"]:
        parts.append(f"{c['private_label'].capitalize()}.")
    if c["stack"]:
        parts.append(f"Stack: {', '.join(c['stack'])}.")
    if c["link_text"]:
        parts.append(f"Link: {c['link_text']}.")
    return " ".join(parts)


# ------------------------------------------------------------------ layout

def _header(d: Doc, c: dict, inner: float) -> tuple[float, float, float]:
    """Returns (title width, tags width, extra height when tags wrap below the title)."""
    title_fs = 20 if c["kind"] == "building" else 17
    tw = d.width("mono", title_fs, c["title"]) + (d.width("mono", 12, c["codename"], .8) + 12 if c["codename"] else 0)
    tags = 0.0
    if c["private"]:
        tags += d.width("mono", 11, c["private_label"], 1.2) + 36 + 8
    if c["status"]:
        tags += d.width("mono", 12, c["status"], .8) + 18 + 8
    return tw, tags, (0 if tw + tags + 8 <= inner else 28)


def measure(c: dict, tier: str) -> dict:
    W, pad, sum_fs, chip_fs, chip_pad = TIER[tier]
    d = Doc(W, {})
    inner = W - 2 * pad
    tw, tags, extra = _header(d, c, inner)
    lines = wrap(d, "sans", sum_fs, c["summary"], inner) if c["summary"] else []
    rows, cur, rw = [], [], 0.0
    for tool in c["stack"]:
        w = d.width("mono", chip_fs, tool) + 2 * chip_pad
        if cur and rw + w > inner:
            rows.append(cur)
            cur, rw = [], 0.0
        cur.append((tool, w))
        rw += w + 6
    if cur:
        rows.append(cur)
    top = 58 + extra
    h = top + GLYPH_H + 26 + len(lines) * (sum_fs + 7) + (len(rows) * 30 + 6 if rows else 0) + (26 if c["link"] else 0) + 12
    return {"lines": lines, "rows": rows, "extra": extra, "height": h}


# ------------------------------------------------------------------ render

def render(t: dict, c: dict, tier: str, width: int, height: float, idx: int = 0) -> tuple[str, int]:
    W, pad, sum_fs, chip_fs, chip_pad = TIER[tier]
    m = measure(c, tier)
    H = max(height, m["height"])
    d = Doc(W, t)
    inner = W - 2 * pad
    rect = f'x=".5" y=".5" width="{W - 1}" height="{num(H - 1)}" rx="10"'
    d.add(f'<rect class="panel" {rect}/><rect class="run" {rect} pathLength="1000" stroke-dasharray="90 910"/>')
    d.animate("run", f"animation:run {RUNS[idx % len(RUNS)]}s linear {-idx * 2.1:.1f}s infinite")
    d.keyframes("run", "to{stroke-dashoffset:-1000}")

    # header: title (+ codename) .......... status · PRIVATE  (tags wrap below when narrow)
    hy = 36
    title_fs = 20 if c["kind"] == "building" else 17
    cls = "idx" if c["kind"] == "building" else "ttl"
    d.add(f'<g class="{cls}">{d.text("mono", title_fs, c["title"], pad, hy + 2)}</g>')
    if c["codename"]:
        d.add(d.mono_text(12, c["codename"], pad + d.width("mono", title_fs, c["title"]) + 12, hy - 1, "hl", "start", .8))
    ty = hy + m["extra"]
    rx_ = W - pad
    if c["private"]:
        tw = d.width("mono", 11, c["private_label"], 1.2)
        pw = tw + 36
        d.add(f'<rect class="tag" x="{num(rx_ - pw + .5)}" y="{num(ty - 15.5)}" width="{num(pw - 1)}" height="21" rx="10.5"/>')
        d.add(d.icon("lock", rx_ - pw + 9, ty - 13, "tic", .72))
        d.add(d.mono_text(11, c["private_label"], rx_ - 11, ty - 1, "tt", "end", 1.2))
        rx_ -= pw + 8
    if c["status"]:
        sw = d.width("mono", 12, c["status"], .8)
        live = c["status"].lower() == "live"
        d.add(f'<circle class="sled{" ok" if live else ""}" cx="{num(rx_ - sw - 10)}" cy="{num(ty - 5)}" r="3.2"/>')
        d.add(d.mono_text(12, c["status"], rx_, ty - 1, "st", "end", .8))
        d.animate("sled", "animation:led 2.3s ease-in-out infinite", "led")
    d.add(f'<path class="hr" d="M{pad} {48.5 + m["extra"]}H{W - pad}"/>')

    top = 58 + m["extra"]
    d.add(GLYPHS[c["glyph"]](d, t, pad, top, inner, GLYPH_H))

    sy = top + GLYPH_H + 26
    d.add("".join(d.body_text(sum_fs, ln, pad, sy + j * (sum_fs + 7), "sum") for j, ln in enumerate(m["lines"])))
    cyy = sy + len(m["lines"]) * (sum_fs + 7) + 2
    n = 0
    for row in m["rows"]:
        cx = pad
        for tool, w in row:
            d.add(f'<g class="c{n}"><rect class="tchip" x="{num(cx + .5)}" y="{num(cyy + .5)}" width="{num(w - 1)}" height="23" rx="11.5"/>'
                  + d.mono_text(chip_fs, tool, cx + chip_pad, cyy + 16, "ttool") + "</g>")
            d.animate(f"c{n}", f"animation:fade .5s ease-out {.4 + n * .1:.2f}s backwards", "fade")
            cx += w + 6
            n += 1
        cyy += 30
    if c["link"]:
        ly = H - 22
        # the arrow leads, so its spacing never depends on the system font's width
        d.add(f'<g class="arr">{d.text("mono", 12, "↗", pad, ly)}</g>')
        d.add(d.mono_text(12, c["link_text"], pad + 16, ly, "lnk"))
        d.animate("arr", "animation:nudge 2.7s ease-in-out infinite")
        d.keyframes("nudge", "0%,70%,100%{transform:translate(0,0)}80%{transform:translate(2px,-2px)}")

    ok = t.get("success", t["accent"])
    d.rule(f".panel{{fill:{t['surface']};stroke:{t['line']}}}.run{{fill:none;stroke:{t['accent']};stroke-width:1.5;stroke-linecap:round;stroke-opacity:.9}}"
           f".idx{{fill:{t['accent_text']}}}.ttl{{fill:{t['text']}}}.hl,.st,.tt,.ttool{{fill:{t['muted']}}}.hr{{stroke:{t['line']}}}"
           f".sled{{fill:{t['accent']}}}.sled.ok{{fill:{ok}}}"
           f".tag,.tchip{{fill:none;stroke:{t['line_strong']}}}.tic{{fill:none;stroke:{t['muted']};stroke-width:1.6;stroke-linecap:round}}"
           f".wire{{stroke:{t['line_strong']};fill:none}}.node{{fill:{t['bg']};stroke:{t['line_strong']}}}"
           f".ic{{fill:none;stroke:{t['text']};stroke-width:1.3;stroke-linecap:round;stroke-linejoin:round}}"
           f".dat{{fill:{t['accent']}}}.ring{{fill:none;stroke:{t['accent']}}}.sum{{fill:{t['text']}}}.lnk,.arr{{fill:{t['accent_text']}}}"
           + GLYPH_CSS[c["glyph"]](t))
    return d.render(H, c["title"], alt(c)), d.anim


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


def g_audit(d: Doc, t: dict, x, y, w, h) -> str:
    """code under a scanner; findings ranked by severity (bigger marker = higher severity)"""
    p = []
    widths = [.62, .44, .78, .36, .56]
    lw = w - 58
    for j, fr in enumerate(widths):
        p.append(f'<rect class="code" x="{num(x)}" y="{num(y + 10 + j * 11)}" width="{num(lw * fr)}" height="5" rx="2.5"/>')
    d.defs.append(f'<clipPath id="cl"><rect x="{num(x - 2)}" y="{num(y + 4)}" width="{num(lw + 4)}" height="62"/></clipPath>')
    p.append(f'<g clip-path="url(#cl)"><g class="sc"><rect class="scanb" x="{num(x - 2)}" y="{num(y - 14)}" width="{num(lw + 4)}" height="14"/>'
             f'<rect class="scanl" x="{num(x - 2)}" y="{num(y - 1)}" width="{num(lw + 4)}" height="1.2"/></g></g>')
    d.animate("sc", "animation:ascan 4.1s cubic-bezier(.45,0,.55,1) infinite")
    d.keyframes("ascan", "0%{transform:translateY(0)}70%,100%{transform:translateY(70px)}")
    fx = x + lw + 22
    for j, (line, size) in enumerate([(2, 10), (0, 7), (4, 5)]):
        yy = y + 12.5 + line * 11
        p.append(f'<path class="wire" d="M{num(x + lw * widths[line] + 6)} {num(yy)}H{num(fx - size / 2 - 3)}" stroke-dasharray="2 3"/>')
        p.append(f'<rect class="sev v{j}" x="{num(fx - size / 2)}" y="{num(yy - size / 2)}" width="{size}" height="{size}" rx="1.5"/>')
        d.animate(f"v{j}", f"animation:led {2.3 + j * 1.1:.1f}s ease-in-out {j * .5:.1f}s infinite", "led")
    return "".join(p)


def g_pipeline(d: Doc, t: dict, x, y, w, h) -> str:
    """spec -> build -> check -> ship, with a signal lighting each stage in turn"""
    cy, p = y + h / 2, []
    icons = ["spec", "build", "check", "ship"]
    xs = [x + 13 + i * (w - 26) / 3 for i in range(4)]
    p.append(f'<path class="wire" d="' + "".join(f"M{num(xs[i] + 14)} {num(cy)}H{num(xs[i + 1] - 14)}" for i in range(3)) + '"/>')
    period = 4.9
    for i, (ic, nx) in enumerate(zip(icons, xs)):
        p.append(f'<rect class="node" x="{num(nx - 13)}" y="{num(cy - 13)}" width="26" height="26" rx="6"/>' + d.icon(ic, nx - 8, cy - 8))
        p.append(f'<rect class="ring p{i}" x="{num(nx - 13)}" y="{num(cy - 13)}" width="26" height="26" rx="6"/>')
        d.animate(f"p{i}", f"opacity:0;animation:stage {period}s ease-out {period * i / 4:.2f}s infinite")
    d.keyframes("stage", "0%{opacity:1}30%,100%{opacity:0}")
    p.append(_flow(d, f"M{num(xs[0] + 14)} {num(cy)}H{num(xs[3] - 14)}", 1, period, "q"))
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


GLYPH_CSS = {
    "documents": lambda t: f".doc{{fill:{t['bg']};stroke:{t['line_strong']}}}.docl{{stroke:{t['faint']}}}",
    "availability": lambda t: f".cell{{fill:{t['line']}}}.hot{{fill:{t['accent']}}}",
    "audit": lambda t: f".code{{fill:{t['line']}}}.scanb{{fill:{t['accent2']};fill-opacity:.16}}.scanl{{fill:{t['accent2']}}}.sev{{fill:{t['accent']}}}",
    "pipeline": lambda t: "",
    "browser": lambda t: f".win{{fill:{t['bg']};stroke:{t['line_strong']}}}.blk{{fill:{t['line']}}}.hotb{{fill:{t['accent']};fill-opacity:.8}}.dotc{{fill:{t['faint']}}}",
}

GLYPHS = {"documents": g_documents, "availability": g_availability, "audit": g_audit,
          "pipeline": g_pipeline, "browser": g_browser}
