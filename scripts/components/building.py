"""Currently building: numbered system cards (3 across on desktop/mid, stacked on mobile).

Per card: index, optional codename, optional status (hidden when empty), PRIVATE tag (when
projects.yml says private), an architecture glyph, the verbatim summary (projects.yml summary or
profile.yml now[i]) and real stack chips. Nothing is shown for an empty field.
"""
from __future__ import annotations

import math

from svgkit import num

from .base import Doc, wrap

TIER = {
    #          cols gap pad  sum_fs chip_fs chip_pad
    "desktop": (3, 12, 20, 15, 12, 9),
    "mid":     (3, 10, 16, 14, 12, 7),
    "mobile":  (1, 12, 20, 15, 12, 9),
}
RUNS = [7.3, 8.9, 10.1]


def cards_data(profile: dict, projects: dict) -> list[dict]:
    now = [s.strip() for s in profile.get("now") or [] if s.strip()]
    entries = (projects or {}).get("building") or []
    out = []
    for i, text in enumerate(now):
        e = entries[i] if i < len(entries) else {}
        out.append({
            "id": str(e.get("id") or f"{i + 1:02d}"),
            "codename": (e.get("codename") or "").strip(),
            "summary": (e.get("summary") or "").strip() or text,
            "stack": [s.strip() for s in e.get("stack") or [] if s and s.strip()],
            "status": (e.get("status") or "").strip(),
            "private": bool(e.get("private")),
            "glyph": (e.get("glyph") or "").strip(),
        })
    return out


def render(t: dict, cards: list[dict], tier: str, width: int) -> tuple[str, int]:
    W = width
    cols, gap, pad, sum_fs, chip_fs, chip_pad = TIER[tier]
    d = Doc(W, t)
    cw = (W - gap * (cols - 1)) / cols
    inner = cw - 2 * pad
    g_top, g_h = 58, 72

    # measure every card, then use one height per row so the grid is even
    metas = []
    for c in cards:
        lines = wrap(d, "sans", sum_fs, c["summary"], inner)
        rows_, cur, rw = [], [], 0.0
        for tool in c["stack"]:
            w = d.width("mono", chip_fs, tool) + 2 * chip_pad
            if cur and rw + w > inner:
                rows_.append(cur)
                cur, rw = [], 0.0
            cur.append((tool, w))
            rw += w + 6
        if cur:
            rows_.append(cur)
        body_h = g_top + g_h + 26 + len(lines) * (sum_fs + 7)
        chips_h = (len(rows_) * 30 + 8) if rows_ else 0
        metas.append((lines, rows_, body_h, chips_h))
    # one height per row: even across a desktop row, natural when stacked on mobile
    rows = math.ceil(len(cards) / cols)
    row_h = [max(bh + ch for _, _, bh, ch in metas[r * cols:(r + 1) * cols]) + 14 for r in range(rows)]
    H = sum(row_h) + (rows - 1) * gap

    for i, (c, (lines, chip_rows, body_h, chips_h)) in enumerate(zip(cards, metas)):
        col, row = i % cols, i // cols
        ox, oy = col * (cw + gap), sum(row_h[:row]) + row * gap
        card_h = row_h[row]
        k = f"k{i}"
        parts = []
        rect = f'x="{num(ox + .5)}" y="{num(oy + .5)}" width="{num(cw - 1)}" height="{num(card_h - 1)}" rx="10"'
        parts.append(f'<rect class="panel" {rect}/>')
        parts.append(f'<rect class="run {k}run" {rect} pathLength="1000" stroke-dasharray="90 910"/>')
        d.animate(f"{k}run", f"animation:run {RUNS[i % 3]}s linear {-i * 2.1:.1f}s infinite")
        d.keyframes("run", "to{stroke-dashoffset:-1000}")

        # header: index · codename ............ status · PRIVATE
        hy = oy + 36
        parts.append(f'<g class="idx">{d.text("mono", 20, c["id"], ox + pad, hy + 2)}</g>')
        if c["codename"]:
            parts.append(f'<g class="hl">{d.text("mono", 12, c["codename"], ox + pad + 34, hy - 1, .8)}</g>')
        rx_ = ox + cw - pad
        if c["private"]:
            tw = d.width("mono", 11, "PRIVATE", 1.2)
            pw = tw + 36
            parts.append(f'<rect class="tag" x="{num(rx_ - pw + .5)}" y="{num(hy - 15.5)}" width="{num(pw - 1)}" height="21" rx="10.5"/>')
            parts.append(d.icon("lock", rx_ - pw + 9, hy - 13, "tic", .72))
            parts.append(f'<g class="tt">{d.text("mono", 11, "PRIVATE", rx_ - 11, hy - 1, 1.2, "end")}</g>')
            rx_ -= pw + 8
        if c["status"]:
            sw = d.width("mono", 12, c["status"], .8)
            parts.append(f'<circle class="sled {k}led" cx="{num(rx_ - sw - 10)}" cy="{num(hy - 5)}" r="3"/>')
            parts.append(f'<g class="hl">{d.text("mono", 12, c["status"], rx_, hy - 1, .8, "end")}</g>')
            d.animate(f"{k}led", "animation:led 2.3s ease-in-out infinite", "led")
        parts.append(f'<path class="hr" d="M{num(ox + pad)} {num(oy + 48.5)}H{num(ox + cw - pad)}"/>')

        # architecture glyph
        parts.append(glyph(d, t, c["glyph"] or ("documents", "availability", "audit")[i % 3], k,
                           ox + pad, oy + g_top, inner, g_h))

        # summary
        sy = oy + g_top + g_h + 26
        parts.append("".join(d.body_text(sum_fs, ln, ox + pad, sy + j * (sum_fs + 7), "sum") for j, ln in enumerate(lines)))

        # stack chips follow the summary, fading in on a stagger
        cyy = sy + len(lines) * (sum_fs + 7) + 2
        n = 0
        for r_ in chip_rows:
            cx = ox + pad
            for tool, w in r_:
                parts.append(f'<g class="{k}c{n}"><rect class="tchip" x="{num(cx + .5)}" y="{num(cyy + .5)}" width="{num(w - 1)}" height="23" rx="11.5"/>'
                             f'<g class="ttool">{d.text("mono", chip_fs, tool, cx + chip_pad, cyy + 16)}</g></g>')
                d.animate(f"{k}c{n}", f"animation:fade .5s ease-out {.4 + i * .25 + n * .12:.2f}s backwards", "fade")
                cx += w + 6
                n += 1
            cyy += 30
        d.add('<g>' + "".join(parts) + "</g>")

    d.rule(f".panel{{fill:{t['surface']};stroke:{t['line']}}}.run{{fill:none;stroke:{t['accent']};stroke-width:1.5;stroke-linecap:round;stroke-opacity:.9}}"
           f".idx{{fill:{t['accent_text']}}}.hl{{fill:{t['muted']}}}.hr{{stroke:{t['line']}}}.sled{{fill:{t['accent']}}}"
           f".tag{{fill:none;stroke:{t['line_strong']}}}.tic{{fill:none;stroke:{t['muted']};stroke-width:1.6;stroke-linecap:round}}.tt{{fill:{t['muted']}}}"
           f".cell{{fill:{t['line']}}}.hot{{fill:{t['accent']}}}.wire{{stroke:{t['line_strong']};fill:none}}"
           f".node{{fill:{t['bg']};stroke:{t['line_strong']}}}.ic{{fill:none;stroke:{t['text']};stroke-width:1.3;stroke-linecap:round;stroke-linejoin:round}}"
           f".doc{{fill:{t['bg']};stroke:{t['line_strong']}}}.docl{{stroke:{t['faint']}}}.ring{{fill:none;stroke:{t['accent']}}}"
           f".code{{fill:{t['line']}}}.scanb{{fill:{t['accent2']};fill-opacity:.16}}.scanl{{fill:{t['accent2']}}}.sev{{fill:{t['accent']}}}"
           f".dat{{fill:{t['accent']}}}.sum{{fill:{t['text']}}}.tchip{{fill:none;stroke:{t['line_strong']}}}.ttool{{fill:{t['muted']}}}")
    desc = " ".join(
        f"{c['id']}: {c['summary']}"
        + (f" Codename {c['codename']}." if c["codename"] else "")
        + (f" Status: {c['status']}." if c["status"] else "")
        + (" Private." if c["private"] else "")
        + (f" Stack: {', '.join(c['stack'])}." if c["stack"] else "")
        for c in cards)
    return d.render(H, "Currently building", desc), d.anim


def _flow(d: Doc, k: str, path: str, n: int = 2, period: float = 3.7) -> str:
    out = []
    for j in range(n):
        out.append(f'<circle class="dat {k}f{j}" r="2.2"/>')
        d.animate(f"{k}f{j}", f"offset-path:path('{path}');animation:flow {period}s cubic-bezier(.5,0,.5,1) {-j * period / n:.2f}s infinite")
    d.keyframes("flow", "0%{offset-distance:0%;opacity:0}12%{opacity:1}88%{opacity:1}100%{offset-distance:100%;opacity:0}")
    return "".join(out)


def glyph(d: Doc, t: dict, kind: str, k: str, x: float, y: float, w: float, h: float) -> str:
    cy = y + h / 2
    p = []
    if kind == "documents":
        # documents → index → search
        for j in range(3):
            dx, dy = x + j * 5, y + 14 + j * 5
            cls = f"doc {k}top" if j == 2 else "doc"
            p.append(f'<g class="{cls}"><rect class="doc" x="{num(dx)}" y="{num(dy)}" width="30" height="38" rx="3"/>'
                     f'<path class="docl" d="M{num(dx + 6)} {num(dy + 10)}h18M{num(dx + 6)} {num(dy + 17)}h18M{num(dx + 6)} {num(dy + 24)}h12"/></g>')
        d.animate(f"{k}top", "animation:ingest 6.1s cubic-bezier(.2,.7,.2,1) 1s infinite")
        d.keyframes("ingest", "0%{transform:translateY(-6px);opacity:0}10%,100%{transform:translateY(0);opacity:1}")
        n1, n2 = x + w * .56, x + w - 13
        a = x + 52
        p.append(f'<path class="wire" d="M{num(a)} {num(cy)}H{num(n1 - 13)}M{num(n1 + 13)} {num(cy)}H{num(n2 - 13)}"/>')
        p.append(f'<rect class="node" x="{num(n1 - 12)}" y="{num(cy - 12)}" width="24" height="24" rx="5"/>' + d.icon("index", n1 - 8, cy - 8))
        p.append(f'<circle class="node" cx="{num(n2)}" cy="{num(cy)}" r="12"/>' + d.icon("search", n2 - 8, cy - 8))
        p.append(f'<circle class="ring {k}ring" cx="{num(n2)}" cy="{num(cy)}" r="12"/>')
        d.animate(f"{k}ring", f"transform-origin:{num(n2)}px {num(cy)}px;animation:ping 3.7s ease-out 1.6s infinite")
        d.keyframes("ping", "0%{transform:scale(1);opacity:.8}60%,100%{transform:scale(1.7);opacity:0}")
        p.append(_flow(d, k, f"M{num(a)} {num(cy)}H{num(n2 - 13)}"))
    elif kind == "availability":
        # live-availability grid → scheduler → admin console
        cols, rows_, cs, gp = 6, 3, 11, 5
        gw = cols * cs + (cols - 1) * gp
        gy = cy - (rows_ * cs + (rows_ - 1) * gp) / 2
        for rr in range(rows_):
            for cc in range(cols):
                p.append(f'<rect class="cell" x="{num(x + cc * (cs + gp))}" y="{num(gy + rr * (cs + gp))}" width="{cs}" height="{cs}" rx="2.5"/>')
        p.append(f'<rect class="hot {k}hop" x="{num(x)}" y="{num(gy)}" width="{cs}" height="{cs}" rx="2.5"/>')
        hops = [(1, 0), (4, 1), (2, 2), (5, 0), (0, 1), (3, 2)]
        frames = "".join(f"{j * 100 / len(hops):.1f}%{{transform:translate({c * (cs + gp)}px,{r * (cs + gp)}px)}}" for j, (c, r) in enumerate(hops))
        d.animate(f"{k}hop", "animation:hop 6.3s steps(1,end) infinite")
        d.keyframes("hop", frames + f"100%{{transform:translate({hops[0][0] * (cs + gp)}px,0)}}")
        n1, n2 = x + gw + (w - gw) * .45, x + w - 12
        p.append(f'<path class="wire" d="M{num(x + gw + 4)} {num(cy)}H{num(n1 - 12)}M{num(n1 + 12)} {num(cy)}H{num(n2 - 12)}"/>')
        p.append(f'<circle class="node" cx="{num(n1)}" cy="{num(cy)}" r="11"/>' + d.icon("clock", n1 - 8, cy - 8))
        p.append(f'<rect class="node" x="{num(n2 - 11)}" y="{num(cy - 11)}" width="22" height="22" rx="5"/>' + d.icon("console", n2 - 8, cy - 8))
        p.append(_flow(d, k, f"M{num(x + gw + 4)} {num(cy)}H{num(n2 - 12)}"))
    else:
        # adversarial audit: code under a scanner; findings ranked by severity
        widths = [.62, .44, .78, .36, .56]
        lw = w - 58
        for j, fr in enumerate(widths):
            p.append(f'<rect class="code" x="{num(x)}" y="{num(y + 10 + j * 11)}" width="{num(lw * fr)}" height="5" rx="2.5"/>')
        d.defs.append(f'<clipPath id="{k}cl"><rect x="{num(x - 2)}" y="{num(y + 4)}" width="{num(lw + 4)}" height="62"/></clipPath>')
        p.append(f'<g clip-path="url(#{k}cl)"><g class="{k}sc"><rect class="scanb" x="{num(x - 2)}" y="{num(y - 14)}" width="{num(lw + 4)}" height="14"/>'
                 f'<rect class="scanl" x="{num(x - 2)}" y="{num(y - 1)}" width="{num(lw + 4)}" height="1.2"/></g></g>')
        d.animate(f"{k}sc", "animation:ascan 4.1s cubic-bezier(.45,0,.55,1) infinite")
        d.keyframes("ascan", "0%{transform:translateY(0)}70%,100%{transform:translateY(70px)}")
        # three findings, ranked: largest marker = highest severity
        fx = x + lw + 22
        for j, (line, size) in enumerate([(2, 10), (0, 7), (4, 5)]):
            yy = y + 12.5 + line * 11
            p.append(f'<path class="wire" d="M{num(x + lw * widths[line] + 6)} {num(yy)}H{num(fx - size / 2 - 3)}" stroke-dasharray="2 3"/>')
            p.append(f'<rect class="sev {k}v{j}" x="{num(fx - size / 2)}" y="{num(yy - size / 2)}" width="{size}" height="{size}" rx="1.5"/>')
            d.animate(f"{k}v{j}", f"animation:led {2.3 + j * 1.1:.1f}s ease-in-out {j * .5:.1f}s infinite", "led")
    return "".join(p)
