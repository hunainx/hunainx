"""Stack map: technical depth on the left (the profile.yml `stack` categories and their tools) feeds
a hub that fans out to the strategic range on the right (the profile.yml `focus` domains). Every
label is verbatim profile.yml text. The map grows taller to fit its content; text never shrinks."""
from __future__ import annotations

from svgkit import num

from .base import Doc, balanced

CAT_PERIODS = [3.7, 5.9, 4.3, 7.1, 5.3, 6.7]
OUT_PERIODS = [4.7, 6.1, 3.9, 5.5, 7.3, 4.9, 6.5]


def render(t: dict, stack: dict, focus: list[str], tier: str, width: int, heads: tuple[str, str] = ("DEPTH", "RANGE")) -> tuple[str, int]:
    W = width
    d = Doc(W, t)
    cats = [(k, [s for s in v if s.strip()]) for k, v in stack.items() if any(s.strip() for s in v)]
    focus = [f for f in focus if f.strip()]
    mobile = tier == "mobile"
    lab_fs, tool_fs, out_fs = (12, 14, 14)
    links, parts = [], []

    if not mobile:
        colw, out_w, gap = (340, 250, 12) if tier == "desktop" else (230, 200, 10)
        lx, rx = 16, W - 16 - out_w
        y0 = 40
        wrapped = [balanced(d, "sans", tool_fs, tools, " · ", colw - 32) for _, tools in cats]
        heights = [34 + len(lines) * 20 + 8 for lines in wrapped]
        left_h = sum(heights) + gap * (len(cats) - 1)
        ogap = 12
        flines = [balanced(d, "sans", out_fs, f.split(" "), " ", out_w - 40) for f in focus]
        ohs = [26 + 20 * len(fl) - 4 for fl in flines]
        right_h = sum(ohs) + ogap * (len(focus) - 1)
        body = max(left_h, right_h)
        H = y0 + body + 20
        hub = (lx + colw + (rx - lx - colw) / 2, y0 + body / 2)
        parts.append(d.mono_text(12, heads[0], lx, 22, "head", "start", 2) + d.mono_text(12, heads[1], rx, 22, "head", "start", 2))
        y = y0 + (body - left_h) / 2
        for i, ((name, tools), lines, h) in enumerate(zip(cats, wrapped, heights)):
            parts.append(f'<rect class="blk" x="{lx + .5}" y="{num(y + .5)}" width="{colw - 1}" height="{h - 1}" rx="8"/>')
            parts.append(d.mono_text(lab_fs, name.upper(), lx + 16, y + 22, "cat", "start", 1.8))
            parts.append("".join(d.body_text(tool_fs, ln, lx + 16, y + 44 + j * 20, "tool") for j, ln in enumerate(lines)))
            port = (lx + colw, y + h / 2)
            parts.append(f'<circle class="port q{i}" cx="{num(port[0])}" cy="{num(port[1])}" r="3.5"/>')
            d.animate(f"q{i}", f"animation:led {CAT_PERIODS[i % 6]}s ease-in-out {i * .6:.1f}s infinite", "led")
            links.append(f"M{num(port[0] + 4)} {num(port[1])}C{num(port[0] + 60)} {num(port[1])} {num(hub[0] - 70)} {num(hub[1])} {num(hub[0] - 26)} {num(hub[1])}")
            y += h + gap
        oy = y0 + (body - right_h) / 2
        for j, (f, fl, oh) in enumerate(zip(focus, flines, ohs)):
            yy = oy + sum(ohs[:j]) + j * ogap
            parts.append(f'<rect class="out" x="{rx + .5}" y="{num(yy + .5)}" width="{out_w - 1}" height="{oh - 1}" rx="{min(20, (oh - 1) / 2)}"/>')
            parts.append("".join(d.body_text(out_fs, ln, rx + 22, yy + 19 + k * 20, "otxt") for k, ln in enumerate(fl)))
            port = (rx, yy + oh / 2)
            parts.append(f'<circle class="port o{j}" cx="{num(port[0])}" cy="{num(port[1])}" r="3.5"/>')
            d.animate(f"o{j}", f"animation:led {OUT_PERIODS[j % 7]}s ease-in-out {1.2 + j * .6:.1f}s infinite", "led")
            links.append(f"M{num(hub[0] + 26)} {num(hub[1])}C{num(hub[0] + 70)} {num(hub[1])} {num(port[0] - 60)} {num(port[1])} {num(port[0] - 4)} {num(port[1])}")
    else:
        pad = 16
        y = 38
        parts.append(d.mono_text(12, heads[0], pad, 22, "head", "start", 2))
        busx = W - pad - 6
        ports = []
        for i, (name, tools) in enumerate(cats):
            lines = balanced(d, "sans", tool_fs, tools, " · ", W - 2 * pad - 52)
            h = 34 + len(lines) * 20 + 8
            parts.append(f'<rect class="blk" x="{pad + .5}" y="{num(y + .5)}" width="{W - 2 * pad - 25}" height="{h - 1}" rx="8"/>')
            parts.append(d.mono_text(lab_fs, name.upper(), pad + 14, y + 22, "cat", "start", 1.6))
            parts.append("".join(d.body_text(tool_fs, ln, pad + 14, y + 44 + j * 20, "tool") for j, ln in enumerate(lines)))
            port = (W - pad - 24, y + h / 2)
            ports.append(port)
            parts.append(f'<circle class="port q{i}" cx="{num(port[0])}" cy="{num(port[1])}" r="3.5"/>')
            d.animate(f"q{i}", f"animation:led {CAT_PERIODS[i % 6]}s ease-in-out {i * .6:.1f}s infinite", "led")
            y += h + 10
        hub = (W / 2, y + 40)
        for port in ports:
            links.append(f"M{num(port[0] + 4)} {num(port[1])}H{num(busx)}V{num(hub[1])}H{num(hub[0] + 26)}")
        y = hub[1] + 72
        # range as a tree: one trunk from the hub down the left edge, a branch into each domain
        trunk_x, ow, oh, og = pad + 8, W - 2 * pad - 24, 38, 10
        ox = trunk_x + 16
        parts.append(d.mono_text(12, heads[1], ox, y - 14, "head", "start", 2))
        last = y + (len(focus) - 1) * (oh + og) + oh / 2
        links.append(f"M{num(hub[0])} {num(hub[1] + 26)}V{num(y - 34)}H{num(trunk_x)}V{num(last)}")
        for j, f in enumerate(focus):
            cy_ = y + j * (oh + og)
            parts.append(f'<path class="link" d="M{num(trunk_x)} {num(cy_ + oh / 2)}H{num(ox - 4)}"/>')
            parts.append(f'<rect class="out" x="{num(ox + .5)}" y="{num(cy_ + .5)}" width="{num(ow - 1)}" height="{oh - 1}" rx="{(oh - 1) / 2}"/>')
            parts.append(d.body_text(14, f, ox + 20, cy_ + oh / 2 + 5, "otxt"))
            port = (ox, cy_ + oh / 2)
            parts.append(f'<circle class="port o{j}" cx="{num(port[0])}" cy="{num(port[1])}" r="3"/>')
            d.animate(f"o{j}", f"animation:led {OUT_PERIODS[j % 7]}s ease-in-out {1.2 + j * .6:.1f}s infinite", "led")
        H = y + len(focus) * (oh + og) + 8

    # links underneath, signals travelling along them
    wires = "".join(f'<path class="link" d="{p}"/>' for p in links)
    sig = []
    for i, p in enumerate(links):
        per = (CAT_PERIODS + OUT_PERIODS)[i % 13]
        sig.append(f'<circle class="sig z{i}" r="2.4"/>')
        d.animate(f"z{i}", f"offset-path:path('{p}');animation:sig {per}s cubic-bezier(.5,0,.5,1) {i * .45:.2f}s infinite")
    d.keyframes("sig", "0%{offset-distance:0%;opacity:0}10%{opacity:1}45%{offset-distance:100%;opacity:1}50%,100%{offset-distance:100%;opacity:0}")
    hub_svg = (f'<circle class="hubr" cx="{num(hub[0])}" cy="{num(hub[1])}" r="26"/>'
               f'<circle class="hub" cx="{num(hub[0])}" cy="{num(hub[1])}" r="20"/>' + d.icon("build", hub[0] - 8, hub[1] - 8))
    d.animate("hubr", f"transform-origin:{num(hub[0])}px {num(hub[1])}px;animation:glowb 8.3s ease-in-out infinite", "glowb")
    d.add(wires, "".join(sig), hub_svg, '<g class="nodes">' + "".join(parts) + "</g>")
    d.animate("nodes", "animation:fade .8s ease-out .2s backwards", "fade")

    d.rule(f".head{{fill:{t['muted']}}}.blk{{fill:{t['surface']};stroke:{t['line']}}}.cat{{fill:{t['accent_text']}}}.tool{{fill:{t['text']}}}"
           f".out{{fill:none;stroke:{t['line_strong']}}}.otxt{{fill:{t['text']}}}.port{{fill:{t['accent']}}}"
           f".link{{fill:none;stroke:{t['line_strong']}}}.sig{{fill:{t['accent']};opacity:0}}"
           f".hub{{fill:{t['surface']};stroke:{t['line_strong']}}}.hubr{{fill:none;stroke:{t['accent']};stroke-opacity:.5}}"
           f".ic{{fill:none;stroke:{t['text']};stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}}")
    desc = (f"{heads[0].capitalize()}: " + "; ".join(f"{n}: {', '.join(tl)}" for n, tl in cats)
            + (f". {heads[1].capitalize()}: " + ", ".join(focus) + "." if focus else "."))
    return d.render(H, "Stack & range", desc), d.anim
