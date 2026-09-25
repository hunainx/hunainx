"""Hero: frame + corner meta, name, role, tagline, agents cluster, pipeline diagram, log ticker.

Copy comes verbatim from profile.yml: name and role (displayed uppercase), tagline, the first
sentence of each principle (ticker) and the tools of the stack category named in
config `hero.agents_category` (agent cluster labels). Stage names are the owner's process.
"""
from __future__ import annotations

import math
import re

from svgkit import num

from .base import Doc, hgrad, lead, radial_glow, split_tokens

STAGES = ["agents", "spec", "build", "audit", "ship"]
LAYOUT = {
    #          pad  name  role  tag  meta tick  chipw chiph labels_in_chip
    "desktop": (32, 46, 15, 17, 12, 15, 110, 42, True),
    "mid":     (24, 40, 14, 16, 12, 14, 52, 44, False),
    "mobile":  (18, 32, 13, 16, 13, 13, 46, 44, False),
}


def render(t: dict, profile: dict, cfg: dict, tier: str, width: int) -> tuple[str, int]:
    W = width
    pad, name_fs, role_fs, tag_fs, meta_fs, tick_fs, cw, ch, inside = LAYOUT[tier]
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
    tag_lines = split_tokens(d, "sans", tag_fs, re.split(r"(?<=[.!?]) ", tagline), " ", text_w, 0) if tagline else []
    tag_ys = []
    for _ in tag_lines:
        tag_ys.append(y)
        y += tag_fs + 7
    cy = y + (72 if desktop else 70)
    y = cy + ch / 2 + (22 if inside else 44)
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
        d.add(f'<g class="meta c{i}">{glyph}{d.text("mono", meta_fs, txt, cx, cy_, 1.2, anc)}</g>')
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
    agents_cluster(d, t, tier, W, x0, top_g, name_y, agents)

    # ---------------- pipeline diagram
    n = len(STAGES)
    xs = [x0 + cw / 2 + i * (W - 2 * x0 - cw) / (n - 1) for i in range(n)]
    g = []
    lift = 30 if desktop else 26
    top = cy - ch / 2 - 2
    loop = f"M{num(xs[3])} {num(top)}C{num(xs[3])} {num(top - lift)} {num(xs[2])} {num(top - lift)} {num(xs[2])} {num(top)}"
    g.append(f'<path class="loop" d="{loop}"/><path class="chev" d="M{num(xs[2] - 3.5)} {num(top - 5)}l3.5 4 3.5-4"/>')
    g.append('<rect class="rpkt" x="-3.5" y="-2" width="7" height="4" rx="2"/>')
    d.animate("rpkt", f"offset-path:path('{loop}');offset-rotate:auto;animation:ret 6.3s cubic-bezier(.5,0,.5,1) 4.1s infinite")
    d.keyframes("ret", "0%{offset-distance:0%;opacity:0}6%{opacity:1}34%{opacity:1}40%,100%{offset-distance:100%;opacity:0}")
    wires, flow = [], []
    for i in range(n - 1):
        a, b = xs[i] + cw / 2 + 4, xs[i + 1] - cw / 2 - 4
        wires.append(f"M{num(a)} {num(cy + .5)}H{num(b)}")
        flow.append(f"M{num(a)} {num(cy + .5)}H{num(b - 5)}")
        g.append(f'<path class="chev" d="M{num(b - 5)} {num(cy - 3)}l4 3.5-4 3.5"/>')
    g.append(f'<path class="wire" d="{"".join(wires)}"/><path class="flow" d="{"".join(flow)}"/>')
    d.animate("flow", "animation:march 1.9s linear infinite", "march")
    for i, dur in enumerate([3.1, 4.7, 3.7, 5.3]):
        a, b = xs[i] + cw / 2 + 4, xs[i + 1] - cw / 2 - 10
        if b - a < 8:
            continue
        g.append(f'<rect class="pkt p{i}" x="{num(a)}" y="{num(cy - 1.5)}" width="7" height="4" rx="2"/>')
        d.animate(f"p{i}", f"animation:pk{i} {dur}s cubic-bezier(.5,0,.5,1) {2.3 + i * .7:.2f}s infinite")
        d.keyframes(f"pk{i}", f"0%{{transform:translateX(0);opacity:0}}8%{{opacity:1}}42%{{transform:translateX({num(b - a)}px);opacity:1}}"
                              f"48%,100%{{transform:translateX({num(b - a)}px);opacity:0}}")
    for i, (stage, period) in enumerate(zip(STAGES, [2.3, 3.1, 1.9, 4.3, 2.9])):
        x = xs[i] - cw / 2
        g.append(f'<rect class="chip" x="{num(x + .5)}" y="{num(cy - ch / 2 + .5)}" width="{cw - 1}" height="{ch - 1}" rx="8"/>')
        if inside:
            ix = x + 14
            g.append(d.icon(stage, ix, cy - 8))
            g.append(f'<g class="lbl">{d.text("mono", 13, stage.upper(), x + 38, cy + 4.6, 1.6)}</g>')
            led = (x + cw - 9, cy - ch / 2 + 9)
        else:
            ix = xs[i] - 8
            g.append(d.icon(stage, ix, cy - 8))
            g.append(f'<g class="lbl">{d.text("mono", 13 if tier == "mobile" else 12, stage.upper(), xs[i], cy + ch / 2 + 20, 0, "middle")}</g>')
            led = (x + cw - 7, cy - ch / 2 + 7)
        g.append(f'<circle class="led l{i}" cx="{num(led[0])}" cy="{num(led[1])}" r="2.5"/>')
        d.animate(f"l{i}", f"animation:led {period}s ease-in-out {i * .37:.2f}s infinite", "led")
        if stage == "audit":
            # scanner sweeps the icon only (behind nothing, never over the label)
            d.defs.append(f'<clipPath id="ac"><rect x="{num(ix - 3)}" y="{num(cy - 11)}" width="22" height="22" rx="3"/></clipPath>')
            hgrad(d, "scg", t["accent2"], "0", ".5")
            g.append(f'<g clip-path="url(#ac)"><g class="scan"><rect x="{num(ix - 15)}" y="{num(cy - 11)}" width="12" height="22" fill="url(#scg)"/>'
                     f'<rect x="{num(ix - 3.5)}" y="{num(cy - 11)}" width="1.2" height="22" class="scanl"/></g></g>')
            d.animate("scan", "animation:scan 2.9s cubic-bezier(.45,0,.55,1) 2s infinite alternate")
            d.keyframes("scan", "from{transform:translateX(0)}to{transform:translateX(24px)}")
    d.add(f'<g class="diag">{"".join(g)}</g>')
    d.animate("diag", "animation:rise .9s cubic-bezier(.2,.7,.2,1) 1.7s backwards", "rise")

    # ---------------- log ticker: first sentence of each principle, typed then faded
    if ticker:
        ticker_block(d, ticker, x0, tick_y, tick_fs)

    d.rule(f".guide{{stroke:{t['line_strong']};fill:none}}.cross{{stroke:{t['faint']};fill:none}}"
           f".meta{{fill:{t['muted']}}}.gl{{fill:none;stroke:{t['muted']};stroke-width:1.3}}"
           f".name{{fill:{t['text']}}}.edge{{fill:{t['accent']}}}.role{{fill:{t['accent_text']}}}.tag{{fill:{t['muted']}}}"
           f".chip{{fill:{t['surface']};stroke:{t['line_strong']}}}.ic{{fill:none;stroke:{t['text']};stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}}"
           f".lbl{{fill:{t['text']}}}.led{{fill:{t['accent']}}}.wire{{stroke:{t['line_strong']};fill:none}}"
           f".flow{{stroke:{t['accent']};stroke-opacity:.55;stroke-dasharray:2 6;fill:none}}.chev{{stroke:{t['muted']};fill:none;stroke-width:1.2}}"
           f".pkt{{fill:{t['accent']}}}.loop{{fill:none;stroke:{t['accent2']};stroke-opacity:.6;stroke-dasharray:3 4}}.rpkt{{fill:{t['accent2']};opacity:0}}"
           f".scanl{{fill:{t['accent2']}}}.orb{{fill:none;stroke:{t['line_strong']};stroke-dasharray:1 5}}.sat{{fill:{t['accent']}}}"
           f".core{{fill:{t['surface']};stroke:{t['line_strong']}}}.alab{{fill:{t['text']}}}.ahead{{fill:{t['muted']}}}"
           f".pr{{fill:{t['accent_text']}}}.tk{{fill:{t['text']}}}.cur{{fill:{t['accent']}}}")
    parts = [f"{name}.", f"{role}." if role else "", tagline,
             "Diagram of how I work: agents, spec, build, audit, ship, with audit findings looping back to build.",
             f"Agents: {', '.join(agents)}." if agents else "",
             ("Principles: " + " ".join(ticker)) if ticker else "",
             " · ".join(v for v in meta.values() if v) + "."]
    return d.render(H, name, " ".join(p for p in parts if p)), d.anim


def agents_cluster(d: Doc, t: dict, tier: str, W: int, x0: float, top_g: float, name_y: float, agents: list[str]) -> None:
    """Orbiting agent nodes. Desktop also lists the agent tools (true labels from profile.yml)."""
    if tier == "desktop":
        ocx, ocy, r = W - x0 - 236, top_g + 60, 36
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
    count = max(len(agents), 2)
    for k in range(count):
        parts.append(f'<circle class="sat s{k}" r="{2.6 - k * .4:.1f}"/>')
        d.animate(f"s{k}", f"offset-path:path('{orbit}');animation:orbit 9.7s linear {-k * 9.7 / count:.2f}s infinite", "orbit")
    if tier == "desktop" and agents:
        lx = ocx + r + 26
        parts.append(f'<g class="ahead">{d.text("mono", 12, "AGENTS", lx, ocy - 22, 2)}</g>')
        for k, a in enumerate(agents[:3]):
            yy = ocy + 2 + k * 22
            parts.append(f'<circle class="led a{k}" cx="{num(lx + 3)}" cy="{num(yy - 4)}" r="2.5"/>')
            parts.append(f'<g class="alab">{d.text("mono", 13, a, lx + 14, yy)}</g>')
            d.animate(f"a{k}", f"animation:led {4.7 + k * 1.4:.1f}s ease-in-out {k * .9:.1f}s infinite", "led")
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
