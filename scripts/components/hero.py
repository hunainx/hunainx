"""Hero: frame + corner meta, name, role, tagline, agents cluster, pipeline diagram, log ticker.

Copy comes verbatim from profile.yml: name and role (displayed uppercase), tagline, the first
sentence of each principle (ticker) and the tools of the stack category named in
config `hero.agents_category` (agent cluster labels). Stage names are the owner's process.
"""
from __future__ import annotations

import math
import re

from svgkit import esc_text, num

from .base import Doc, hgrad, lead, radial_glow, split_tokens

STAGES = ["challenge", "spec", "architect", "agents", "audit", "ship"]
LOOP = ("audit", "agents")  # audit findings go back to the agents (the build team)
LAYOUT = {
    #          pad  name  role  tag  meta tick  chipw chiph label_fs
    "desktop": (32, 46, 15, 17, 12, 15, 56, 46, 13),
    "mid":     (24, 40, 14, 16, 12, 14, 52, 44, 12),
    "mobile":  (18, 32, 13, 16, 13, 13, 50, 44, 13),
}


def render(t: dict, profile: dict, cfg: dict, tier: str, width: int) -> tuple[str, int]:
    W = width
    pad, name_fs, role_fs, tag_fs, meta_fs, tick_fs, cw, ch, lab_fs = LAYOUT[tier]
    d = Doc(W, t)
    name = profile["name"].strip()
    role = (profile.get("role") or "").strip()
    tagline = (profile.get("tagline") or "").strip()
    ticker = [lead(p) for p in profile.get("principles") or [] if p.strip()]
    agents = [a for a in (profile.get("stack") or {}).get(cfg["hero"]["agents_category"], []) if a.strip()]
    meta = cfg["hero"]["corners"]
    desktop = tier == "desktop"
    x0 = pad + (8 if tier != "mobile" else 0)
    text_w = W - 2 * x0

    # ---------------- vertical layout
    top_g = 36 if tier != "mobile" else 34
    name_y = top_g + (66 if desktop else 58 if tier == "mid" else 52)
    y = name_y + (36 if desktop else 32)
    role_tr = 3.2 if desktop else 2.4 if tier == "mid" else 1.8
    role_lines = split_tokens(d, "mono", role_fs, [p.strip() for p in role.upper().split("·")], " · ",
                              text_w - (0 if desktop else 70), role_tr) if role else []
    role_ys = []
    for _ in role_lines:
        role_ys.append(y)
        y += role_fs + 7
    y += 10
    tag_tokens = []
    for sentence in re.split(r"(?<=[.!?]) ", tagline) if tagline else []:
        tag_tokens += sentence.split(" ") if d.width("sans", tag_fs, sentence) > text_w else [sentence]
    tag_lines = split_tokens(d, "sans", tag_fs, tag_tokens, " ", text_w, 0)
    tag_ys = []
    for _ in tag_lines:
        tag_ys.append(y)
        y += tag_fs + 7
    cy = y + (72 if desktop else 70)
    pts = stage_points(tier, W, x0, cw, ch, cy)
    y = max(p[1] for p in pts) + ch / 2 + 44
    tick_y = y + (14 if tier == "mobile" else 8)
    bot_g = tick_y + 24
    H = bot_g + 36

    # ---------------- ambience: masked dot grid, shimmer band, breathing glow
    d.defs.append(f'<pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="10" cy="10" r="1" fill="#fff"/></pattern>'
                  f'<mask id="dm"><rect width="{W}" height="{num(H)}" fill="url(#dots)"/></mask>')
    hgrad(d, "shg", t["accent"], "0", "0", ".55")
    radial_glow(d, "glow", t["accent"], t["glow"])
    d.add(f'<rect width="{W}" height="{num(H)}" fill="{t["text"]}" fill-opacity="{t["grid"]}" mask="url(#dm)"/>')
    d.add(f'<g mask="url(#dm)"><rect class="shim" x="-240" y="0" width="240" height="{num(H)}" fill="url(#shg)"/></g>')
    d.animate("shim", "animation:shim 11.3s cubic-bezier(.45,0,.3,1) 2.2s infinite")
    d.keyframes("shim", f"0%{{transform:translateX(0)}}45%,100%{{transform:translateX({W + 240}px)}}")
    d.add(f'<ellipse class="glow" cx="{W / 2}" cy="{num(cy)}" rx="{num(W * .42)}" ry="{90 if desktop else 72}" fill="url(#glow)"/>')
    d.animate("glow", f"transform-origin:{W / 2}px {num(cy)}px;animation:glowb 9.7s ease-in-out infinite", "glowb")

    # ---------------- frame guides (draw in) + crosshairs
    vx1, vx2 = (pad - 8, W - pad + 8) if tier != "mobile" else (8, W - 8)
    d.add(f'<path class="guide g0" pathLength="100" stroke-dasharray="100" d="M0 {top_g + .5}H{W}M0 {num(bot_g + .5)}H{W}"/>')
    d.add(f'<path class="guide g1" pathLength="100" stroke-dasharray="100" d="M{vx1 + .5} 10V{num(H - 10)}M{vx2 - .5} 10V{num(H - 10)}"/>')
    d.animate("g0", "animation:draw 1.2s cubic-bezier(.6,0,.2,1) backwards", "draw")
    d.animate("g1", "animation:draw 1.2s cubic-bezier(.6,0,.2,1) .2s backwards", "draw")
    cross = "".join(f"M{num(cx - 4)} {num(cy_ + .5)}h8M{num(cx + .5)} {num(cy_ - 4)}v8"
                    for cx in (vx1, vx2) for cy_ in (top_g, bot_g))
    d.add(f'<path class="cross" d="{cross}"/>')
    d.animate("cross", "animation:fade .5s ease-out 1s backwards", "fade")

    # ---------------- corner meta (true values only)
    corners = [(meta["top_left"], x0, top_g - 13, "start", False), (meta["top_right"], W - x0, top_g - 13, "end", False),
               (meta["bottom_left"], x0 + 20, H - 13, "start", True), (meta["bottom_right"], W - x0, H - 13, "end", False)]
    for i, (txt, cx, cy_, anc, branch) in enumerate(corners):
        if not txt:
            continue
        glyph = d.icon("branch", x0 - 1, H - 13 - 12, "gl", .9) if branch else ""
        d.add(f'<g class="meta c{i}">{glyph}{d.mono_text(meta_fs, txt, cx, cy_, "mt", anc, 1.2)}</g>')
        d.animate(f"c{i}", f"animation:fade .6s ease-out {0.25 + i * .15:.2f}s backwards", "fade")

    # ---------------- name: mask sweep with a travelling light edge
    name_up = name.upper()
    nw = d.width("display", name_fs, name_up, 1.0)
    hgrad(d, "nmg", "#fff", "1", "0", "1", ".86")
    d.defs.append(f'<mask id="nm"><rect class="nmask" x="{num(x0 - 60)}" y="{num(name_y - name_fs)}" width="{num(nw + 120)}" '
                  f'height="{num(name_fs * 1.3)}" fill="url(#nmg)"/></mask>')
    d.add(f'<g class="name" mask="url(#nm)">{d.text("display", name_fs, name_up, x0, name_y, 1.0)}</g>')
    d.animate("nmask", "animation:nsweep 1.1s cubic-bezier(.65,0,.25,1) .35s backwards")
    d.keyframes("nsweep", f"from{{transform:translateX(-{num(nw + 120)}px)}}")
    d.add(f'<rect class="edge" x="{num(x0 + nw + 4)}" y="{num(name_y - name_fs * .82)}" width="1.5" height="{num(name_fs * .95)}"/>')
    d.animate("edge", "opacity:0;animation:edge 1.1s cubic-bezier(.65,0,.25,1) .35s")
    d.keyframes("edge", f"0%{{opacity:1;transform:translateX(-{num(nw + 4)}px)}}85%{{opacity:1}}100%{{opacity:0;transform:translateX(0)}}")

    # ---------------- role: types in
    t_role = 1.2
    for i, (line, ry) in enumerate(zip(role_lines, role_ys)):
        g, t_role = d.typed(f"r{i}", "mono", role_fs, line, x0, ry, t_role, .045, role_tr, "role")
        d.add(g)
        t_role += .05

    # ---------------- tagline: rises in
    if tag_lines:
        d.add('<g class="tag rise">' + "".join(d.text("sans", tag_fs, ln, x0, ty) for ln, ty in zip(tag_lines, tag_ys)) + "</g>")
        d.animate("rise", f"animation:rise .9s cubic-bezier(.2,.7,.2,1) {max(t_role - .5, 1.4):.2f}s backwards", "rise")

    # ---------------- agents cluster (top-right quadrant)
    agents_cluster(d, t, tier, W, x0, top_g, name_y, agents, x0 + nw, name_fs)

    # ---------------- pipeline diagram
    d.add('<g class="diag">' + diagram(d, t, tier, pts, cw, ch, lab_fs) + "</g>")
    d.animate("diag", "animation:rise .9s cubic-bezier(.2,.7,.2,1) 1.7s backwards", "rise")

    # ---------------- log ticker: first sentence of each principle, typed then faded
    if ticker:
        ticker_block(d, ticker, x0, tick_y, tick_fs)

    d.rule(f".guide{{stroke:{t['line_strong']};fill:none}}.cross{{stroke:{t['faint']};fill:none}}"
           f".meta,.mt{{fill:{t['muted']}}}.gl{{fill:none;stroke:{t['muted']};stroke-width:1.3}}"
           f".name{{fill:{t['text']}}}.edge{{fill:{t['accent']}}}.role{{fill:{t['accent_text']}}}.tag{{fill:{t['muted']}}}"
           f".chip{{fill:{t['surface']};stroke:{t['line_strong']}}}.ic{{fill:none;stroke:{t['text']};stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}}"
           f".lbl{{fill:{t['text']}}}.led{{fill:{t['accent']}}}.wire{{stroke:{t['line_strong']};fill:none}}"
           f".flow{{stroke:{t['accent']};stroke-opacity:.55;stroke-dasharray:2 6;fill:none}}.chev{{stroke:{t['muted']};fill:none;stroke-width:1.2}}"
           f".pkt{{fill:{t['accent']}}}.loop{{fill:none;stroke:{t['accent2']};stroke-opacity:.6;stroke-dasharray:3 4}}.rpkt{{fill:{t['accent2']};opacity:0}}"
           f".scanl{{fill:{t['accent2']}}}.orb{{fill:none;stroke:{t['line_strong']};stroke-dasharray:1 5}}.sat{{fill:{t['accent']}}}"
           f".core{{fill:{t['surface']};stroke:{t['line_strong']}}}.alab{{fill:{t['text']}}}.ahead{{fill:{t['muted']}}}.adot{{fill:{t['accent']}}}"
           f".pr{{fill:{t['accent_text']}}}.tk{{fill:{t['text']}}}.cur{{fill:{t['accent']}}}")
    parts = [f"{name}.", f"{role}." if role else "", tagline,
             "Diagram of how I work: " + ", ".join(STAGES) + ", with audit findings looping back to the agents.",
             f"Agents: {', '.join(agents)}." if agents else "",
             ("Principles: " + " ".join(ticker)) if ticker else "",
             " · ".join(v for v in meta.values() if v) + "."]
    return d.render(H, name, " ".join(p for p in parts if p)), d.anim


def agents_cluster(d: Doc, t: dict, tier: str, W: int, x0: float, top_g: float, name_y: float, agents: list[str],
                   name_right: float = 0, name_fs: float = 46) -> None:
    """Orbiting agent nodes. Desktop also lists the agent tools (true labels from profile.yml) in
    columns of three, right-aligned to the same inset as the name and aligned to the name's cap line."""
    if tier == "desktop":
        # list block: columns of up to three, widths measured with JetBrains Mono (>= system mono)
        cols = [agents[i:i + 3] for i in range(0, len(agents), 3)]
        col_w = [11 + max(d.width("mono", 12, a) for a in col) for col in cols]
        list_w = sum(col_w) + 18 * (len(cols) - 1)
        list_x = W - x0 - list_w
        cap_top = name_y - name_fs * .73          # cap height of Inter Display
        head_y = cap_top + 8                      # 11px heading: cap top on the name's cap line
        rows_y = [head_y + 20 + k * 17 for k in range(3)]
        r = 30
        ocy = (cap_top + rows_y[-1]) / 2
        ocx = list_x - 26 - r
        if ocx - r - 6 < name_right + 24:         # never crowd the name: shrink the orbit if needed
            r = max(18, (list_x - 26 - name_right - 24 - 6) / 2)
            ocx = list_x - 26 - r
    elif tier == "mid":
        ocx, ocy, r = W - x0 - 40, top_g + 50, 30
    else:
        ocx, ocy, r = W - x0 - 26, name_y - 12, 20
    orbit = f"M{num(ocx - r)} {num(ocy)}a{r} {r} 0 1 0 {2 * r} 0a{r} {r} 0 1 0 -{2 * r} 0"
    parts = [f'<path class="orb" d="{orbit}"/>',
             f'<circle class="core" cx="{num(ocx)}" cy="{num(ocy)}" r="{13 if tier != "mobile" else 10}"/>',
             d.icon("agents", ocx - 8, ocy - 8, "ic", 1 if tier != "mobile" else .8)]
    if tier == "mobile":
        parts[-1] = d.icon("agents", ocx - 6.4, ocy - 6.4, "ic", .8)
    for k in range(3):
        parts.append(f'<circle class="sat s{k}" r="{2.6 - k * .4:.1f}"/>')
        d.animate(f"s{k}", f"offset-path:path('{orbit}');animation:orbit 9.7s linear {-k * 9.7 / 3:.2f}s infinite", "orbit")
    if tier == "desktop" and agents:
        parts.append(d.mono_text(11, "AGENTS", list_x, head_y, "ahead", "start", 2))
        cx = list_x
        for col, w in zip(cols, col_w):
            for k, a in enumerate(col):
                parts.append(f'<circle class="adot" cx="{num(cx + 2.5)}" cy="{num(rows_y[k] - 4)}" r="2"/>')
                parts.append(d.mono_text(12, a, cx + 11, rows_y[k], "alab"))
            cx += w + 18
    d.add('<g class="clus">' + "".join(parts) + "</g>")
    d.animate("clus", "animation:fade .8s ease-out 1.5s backwards", "fade")


def ticker_block(d: Doc, ticker: list[str], x0: float, tick_y: float, fs: float) -> None:
    adv = fs * 0.6
    tx = x0 + fs * 1.2
    T = 5.3
    C = T * len(ticker)
    t0 = 3.4
    parts = [f'<g class="pr">{d.text("mono", fs, "›", x0, tick_y)}</g>']
    marks = []
    for i, line in enumerate(ticker):
        nch = len(line)
        s, du, e = i * T / C * 100, nch * 0.045 / C * 100, (i + 1) * T / C * 100
        d.defs.append(f'<clipPath id="tc{i}"><rect class="tr{i}" x="{num(tx - 1)}" y="{num(tick_y - fs)}" '
                      f'width="{num(nch * adv + 2)}" height="{num(fs * 1.4)}"/></clipPath>')
        parts.append(f'<g class="tk tg{i}" clip-path="url(#tc{i})">{d.text("mono", fs, line, tx, tick_y)}</g>')
        d.animate(f"tg{i}", ("" if i == 0 else "opacity:0;") + f"animation:tgo{i} {C:.1f}s linear {t0}s infinite")
        d.keyframes(f"tgo{i}", f"0%,{max(s - .01, 0):.2f}%{{opacity:0}}{s:.2f}%{{opacity:1}}{e - 4:.2f}%{{opacity:1}}{e - .5:.2f}%,100%{{opacity:0}}")
        d.animate(f"tr{i}", f"transform-origin:{num(tx - 1)}px {num(tick_y)}px;animation:tre{i} {C:.1f}s linear {t0}s infinite")
        d.keyframes(f"tre{i}", f"0%,{s:.2f}%{{transform:scaleX(0);animation-timing-function:steps({nch},end)}}{s + du:.2f}%,100%{{transform:scaleX(1)}}")
        marks.append((s, du, e, nch))
    first = marks[0][3] * adv
    parts.append(f'<g class="blink"><rect class="cur" x="{num(tx + first + 1)}" y="{num(tick_y - fs * .8)}" '
                 f'width="{num(adv - 1)}" height="{num(fs * 1.05)}"/></g>')
    d.animate("cur", f"animation:curm {C:.1f}s linear {t0}s infinite")
    d.keyframes("curm", "".join(
        f"{s:.2f}%{{transform:translateX(-{num(first)}px);animation-timing-function:steps({nch},end)}}"
        f"{s + du:.2f}%,{e - .5:.2f}%{{transform:translateX({num(nch * adv - first)}px)}}" for s, du, e, nch in marks))
    d.animate("blink", "animation:blink 1.1s steps(1,end) infinite", "blink")
    d.add('<g class="tin">' + "".join(parts) + "</g>")
    d.animate("tin", f"animation:fade .6s ease-out {t0 - .5:.2f}s backwards", "fade")


def stage_points(tier: str, W: int, x0: float, cw: float, ch: float, cy: float) -> list[tuple[float, float]]:
    """Chip centres. Desktop/mid: one row. Mobile: two rows of three; the second row runs right
    to left so the third stage drops straight into the fourth."""
    n = len(STAGES)
    inset = 14  # the widest stage label (CHALLENGE) is wider than a chip; keep it inside the frame
    if tier != "mobile":
        return [(x0 + inset + cw / 2 + i * (W - 2 * (x0 + inset) - cw) / (n - 1), cy) for i in range(n)]
    cols = 3
    xs = [x0 + inset + cw / 2 + c * (W - 2 * (x0 + inset) - cw - 14) / (cols - 1) for c in range(cols)]
    row2 = cy + ch + 78
    return [(xs[i], cy) if i < cols else (xs[2 * cols - 1 - i], row2) for i in range(n)]


def diagram(d: Doc, t: dict, tier: str, pts: list, cw: float, ch: float, lab_fs: float) -> str:
    g, wires, flow = [], [], []
    n = len(STAGES)
    k = 0
    # edges: horizontal within a row (either direction); a side connector between rows
    for i in range(n - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        if ay == by:
            sgn = 1 if bx > ax else -1
            a, b = ax + sgn * (cw / 2 + 4), bx - sgn * (cw / 2 + 4)
            wires.append(f"M{num(a)} {num(ay + .5)}H{num(b)}")
            flow.append(f"M{num(a)} {num(ay + .5)}H{num(b - sgn * 5)}")
            g.append(f'<path class="chev" d="M{num(b - sgn * 5)} {num(ay - 3)}l{4 * sgn} 3.5{-4 * sgn} 3.5"/>')
            if abs(b - a) > 22:
                dur = [3.1, 4.7, 3.7, 5.3, 4.1][k % 5]
                start = a if sgn > 0 else a - 7
                dist = (b - sgn * 12) - a
                g.append(f'<rect class="pkt p{k}" x="{num(start)}" y="{num(ay - 1.5)}" width="7" height="4" rx="2"/>')
                d.animate(f"p{k}", f"animation:pk{k} {dur}s cubic-bezier(.5,0,.5,1) {2.3 + k * .7:.2f}s infinite")
                d.keyframes(f"pk{k}", f"0%{{transform:translateX(0);opacity:0}}8%{{opacity:1}}42%{{transform:translateX({num(dist)}px);opacity:1}}"
                                      f"48%,100%{{transform:translateX({num(dist)}px);opacity:0}}")
                k += 1
        else:
            side = ax + cw / 2
            # route outside the label (ARCHITECT is wider than its chip)
            wires.append(f"M{num(side)} {num(ay)}h16V{num(by)}h-16")
            flow.append(f"M{num(side)} {num(ay + .5)}h16V{num(by + .5)}h-11")
            g.append(f'<path class="chev" d="M{num(side + 5)} {num(by - 3.5)}l-4 3.5 4 3.5"/>')
    g.append(f'<path class="wire" d="{"".join(wires)}"/><path class="flow" d="{"".join(flow)}"/>')
    d.animate("flow", "animation:march 1.9s linear infinite", "march")

    # return loop: audit -> agents, arcing over the chips
    (sx, sy), (ex, ey) = pts[STAGES.index(LOOP[0])], pts[STAGES.index(LOOP[1])]
    top_s, top_e, lift = sy - ch / 2 - 2, ey - ch / 2 - 2, 28
    loop = f"M{num(sx)} {num(top_s)}C{num(sx)} {num(top_s - lift)} {num(ex)} {num(top_e - lift)} {num(ex)} {num(top_e)}"
    g.append(f'<path class="loop" d="{loop}"/><path class="chev" d="M{num(ex - 3.5)} {num(top_e - 5)}l3.5 4 3.5-4"/>')
    g.append('<rect class="rpkt" x="-3.5" y="-2" width="7" height="4" rx="2"/>')
    d.animate("rpkt", f"offset-path:path('{loop}');offset-rotate:auto;animation:ret 6.3s cubic-bezier(.5,0,.5,1) 4.1s infinite")
    d.keyframes("ret", "0%{offset-distance:0%;opacity:0}6%{opacity:1}34%{opacity:1}40%,100%{offset-distance:100%;opacity:0}")

    # chips: icon, status LED, label below
    for i, (stage, (x, y)) in enumerate(zip(STAGES, pts)):
        g.append(f'<rect class="chip" x="{num(x - cw / 2 + .5)}" y="{num(y - ch / 2 + .5)}" width="{cw - 1}" height="{ch - 1}" rx="8"/>')
        g.append(d.icon(stage, x - 8, y - 8))
        g.append(f'<g class="lbl">{d.text("mono", lab_fs, stage.upper(), x, y + ch / 2 + 20, 1.2 if tier == "desktop" else 0, "middle")}</g>')
        g.append(f'<circle class="led l{i}" cx="{num(x + cw / 2 - 7)}" cy="{num(y - ch / 2 + 7)}" r="2.5"/>')
        d.animate(f"l{i}", f"animation:led {[2.3, 3.1, 1.9, 4.3, 2.9, 3.7][i % 6]}s ease-in-out {i * .37:.2f}s infinite", "led")
        if stage == "audit":
            # the scanner sweeps the icon only, never the label
            d.defs.append(f'<clipPath id="ac"><rect x="{num(x - 11)}" y="{num(y - 11)}" width="22" height="22" rx="3"/></clipPath>')
            hgrad(d, "scg", t["accent2"], "0", ".5")
            g.append(f'<g clip-path="url(#ac)"><g class="scan"><rect x="{num(x - 23)}" y="{num(y - 11)}" width="12" height="22" fill="url(#scg)"/>'
                     f'<rect x="{num(x - 11.5)}" y="{num(y - 11)}" width="1.2" height="22" class="scanl"/></g></g>')
            d.animate("scan", "animation:scan 2.9s cubic-bezier(.45,0,.55,1) 2s infinite alternate")
            d.keyframes("scan", "from{transform:translateX(0)}to{transform:translateX(24px)}")
    return "".join(g)
