"""Stack map: profile.yml stack categories (with their tools) feed a hub that fans out to the
profile.yml `focus` areas. Every label is verbatim profile.yml text."""
from __future__ import annotations

from svgkit import num

from .base import Doc, wrap

CAT_PERIODS = [3.7, 5.9, 4.3, 7.1, 5.3, 6.7]
OUT_PERIODS = [4.7, 6.1, 3.9, 5.5, 7.3, 4.9]


def render(t: dict, stack: dict, focus: list[str], tier: str, width: int) -> tuple[str, int]:
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
        heights = []
        for name, tools in cats:
            lines = wrap(d, "sans", tool_fs, " · ".join(tools), colw - 32)
            heights.append(34 + len(lines) * 20 + 8)
        total = sum(heights) + gap * (len(cats) - 1)
        H = y0 + total + 20
        hub = (lx + colw + (rx - lx - colw) / 2, y0 + total / 2)
        y = y0
        parts.append(d.mono_text(12, "STACK", lx, 22, "head", "start", 2) + d.mono_text(12, "FOCUS", rx, 22, "head", "start", 2))
        for i, ((name, tools), h) in enumerate(zip(cats, heights)):
            parts.append(f'<rect class="blk" x="{lx + .5}" y="{num(y + .5)}" width="{colw - 1}" height="{h - 1}" rx="8"/>')
            parts.append(d.mono_text(lab_fs, name.upper(), lx + 16, y + 22, "cat", "start", 1.8))
            lines = wrap(d, "sans", tool_fs, " · ".join(tools), colw - 32)
            parts.append("".join(d.body_text(tool_fs, ln, lx + 16, y + 44 + j * 20, "tool") for j, ln in enumerate(lines)))
            port = (lx + colw, y + h / 2)
            parts.append(f'<circle class="port q{i}" cx="{num(port[0])}" cy="{num(port[1])}" r="3.5"/>')
            d.animate(f"q{i}", f"animation:led {CAT_PERIODS[i % 6]}s ease-in-out {i * .6:.1f}s infinite", "led")
            links.append(f"M{num(port[0] + 4)} {num(port[1])}C{num(port[0] + 60)} {num(port[1])} {num(hub[0] - 70)} {num(hub[1])} {num(hub[0] - 26)} {num(hub[1])}")
            y += h + gap
        ogap = 14
        flines = [wrap(d, "sans", out_fs, f, out_w - 40) for f in focus]
        ohs = [26 + 20 * len(fl) - 4 for fl in flines]
        oy = hub[1] - (sum(ohs) + (len(focus) - 1) * ogap) / 2
        for j, (f, fl, oh) in enumerate(zip(focus, flines, ohs)):
            yy = oy + sum(ohs[:j]) + j * ogap
            parts.append(f'<rect class="out" x="{rx + .5}" y="{num(yy + .5)}" width="{out_w - 1}" height="{oh - 1}" rx="{min(20, (oh - 1) / 2)}"/>')
            parts.append("".join(d.body_text(out_fs, ln, rx + 22, yy + 19 + k * 20, "otxt") for k, ln in enumerate(fl)))
            port = (rx, yy + oh / 2)
            parts.append(f'<circle class="port o{j}" cx="{num(port[0])}" cy="{num(port[1])}" r="3.5"/>')
            d.animate(f"o{j}", f"animation:led {OUT_PERIODS[j % 6]}s ease-in-out {1.2 + j * .6:.1f}s infinite", "led")
            links.append(f"M{num(hub[0] + 26)} {num(hub[1])}C{num(hub[0] + 70)} {num(hub[1])} {num(port[0] - 60)} {num(port[1])} {num(port[0] - 4)} {num(port[1])}")
    else:
        pad = 16
        y = 38
        parts.append(d.mono_text(12, "STACK", pad, 22, "head", "start", 2))
        busx = W - pad - 6
        ports = []
        for i, (name, tools) in enumerate(cats):
            lines = wrap(d, "sans", tool_fs, " · ".join(tools), W - 2 * pad - 52)
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
        y = hub[1] + 56
        parts.append(d.mono_text(12, "FOCUS", pad, y - 16, "head", "start", 2))
        # two columns when every focus area fits half the width, otherwise one
        half = (W - 2 * pad - 10) / 2
        ncol = 2 if all(d.width("sans", 14, f) + 32 <= half for f in focus) else 1
        ow, oh = (half if ncol == 2 else W - 2 * pad), 40
        for j, f in enumerate(focus):
            cx, cy_ = pad + (j % ncol) * (ow + 10), y + (j // ncol) * (oh + 10)
            parts.append(f'<rect class="out" x="{num(cx + .5)}" y="{num(cy_ + .5)}" width="{num(ow - 1)}" height="{oh - 1}" rx="{(oh - 1) / 2}"/>')
            parts.append(d.body_text(14, f, cx + ow / 2, cy_ + oh / 2 + 5, "otxt", "middle"))
            port = (cx + ow / 2, cy_)
            parts.append(f'<circle class="port o{j}" cx="{num(port[0])}" cy="{num(port[1])}" r="3"/>')
            d.animate(f"o{j}", f"animation:led {OUT_PERIODS[j % 6]}s ease-in-out {1.2 + j * .6:.1f}s infinite", "led")
            links.append(f"M{num(hub[0])} {num(hub[1] + 26)}V{num(hub[1] + 34)}H{num(port[0])}V{num(port[1] - 4)}")
        H = y + ((len(focus) + ncol - 1) // ncol) * (oh + 10) + 8

    # links underneath, signals travelling along them
    wires = "".join(f'<path class="link" d="{p}"/>' for p in links)
    sig = []
    for i, p in enumerate(links):
        per = (CAT_PERIODS + OUT_PERIODS)[i % 12]
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
    desc = ("Stack: " + "; ".join(f"{n}: {', '.join(tl)}" for n, tl in cats)
            + (". Focus: " + ", ".join(focus) + "." if focus else "."))
    return d.render(H, "Stack", desc), d.anim
