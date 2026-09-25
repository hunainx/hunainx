"""Separator, terminal footer and link chips."""
from __future__ import annotations

from svgkit import num

from .base import Doc, hgrad

LINK_LABELS = {"website": "Website", "linkedin": "LinkedIn", "x": "X", "email": "Email"}
LINK_GLYPHS = {
    "website": '<circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c-3.2 3.6-3.2 9.4 0 13M8 1.5c3.2 3.6 3.2 9.4 0 13"/>',
    "linkedin": '<rect x="1.5" y="2.5" width="13" height="11" rx="2"/><circle cx="6" cy="7" r="1.7"/><path d="M3.6 11.2c.7-1.5 3.9-1.5 4.8 0M10 6.5h2.6M10 9.2h2.6"/>',
    "x": '<path d="M2 3.5h12v7.5H8l-3.5 3v-3H2z"/>',
    "email": '<rect x="1.5" y="3" width="13" height="10" rx="1.6"/><path d="M2 4l6 4.8L14 4"/>',
}


def separator(t: dict, tier: str, width: int) -> tuple[str, int]:
    W, H = width, 14
    d = Doc(W, t)
    d.add(f'<path class="rule" d="M10 7.5H{W - 10}"/>'
          f'<rect class="n n0" x="1" y="4" width="6" height="6" rx="1.5"/><rect class="n n1" x="{W - 7}" y="4" width="6" height="6" rx="1.5"/>')
    d.animate("n0", "animation:led 2.9s ease-in-out infinite", "led")
    d.animate("n1", "animation:led 3.7s ease-in-out .8s infinite", "led")
    hgrad(d, "pg", t["accent"], "0", "0", "1")
    d.add(f'<rect class="pulse" x="10" y="6.5" width="72" height="2" fill="url(#pg)"/>')
    d.animate("pulse", "opacity:0;animation:spulse 6.7s cubic-bezier(.45,0,.3,1) 1s infinite")
    d.keyframes("spulse", f"0%{{opacity:1;transform:translateX(0)}}45%{{opacity:1;transform:translateX({W - 92}px)}}"
                          f"50%,100%{{opacity:0;transform:translateX({W - 92}px)}}")
    d.rule(f".rule{{stroke:{t['line_strong']}}}.n{{fill:{t['line_strong']}}}")
    return d.render(H, "Divider", "Section divider"), d.anim


def footer(t: dict, date: str, label: str, tier: str = "desktop", width: int = 0) -> tuple[str, int]:
    """Drawn at its natural width (under the 308px phone column), so it never scales: one tier."""
    fs = 14
    text = f"{label} · {date}"
    probe = Doc(10, t)
    W, H = int(8 + fs * 1.2 + probe.width("mono", fs, text) + fs + 12), 40
    d = Doc(W, t)
    x, y = 8, 25
    d.add(f'<g class="pr">{d.text("mono", fs, "›", x, y)}</g>')
    g, end = d.typed("ft", "mono", fs, text, x + fs * 1.2, y, .6, .045, 0, "txt")
    d.add(g)
    w = d.width("mono", fs, text)
    d.add(f'<rect class="cur" x="{num(x + fs * 1.2 + w + 3)}" y="{num(y - fs * .8)}" width="{num(fs * .6 - 1)}" height="{num(fs * 1.05)}"/>')
    d.animate("cur", "animation:blink 1.1s steps(1,end) infinite", "blink")
    d.rule(f".pr{{fill:{t['accent_text']}}}.txt{{fill:{t['muted']}}}.cur{{fill:{t['accent']}}}")
    return d.render(H, text, text), d.anim


def chip(t: dict, key: str, tier: str = "desktop", width: int = 0) -> tuple[str, int]:
    label = LINK_LABELS[key]
    probe = Doc(10, t)
    W = int(12 + 16 + 8 + probe.width("sans", 14, label) + 16)
    H = 34
    d = Doc(W, t)
    d.add(f'<rect class="chip" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{(H - 1) / 2}"/>'
          f'<g class="glyph gd" transform="translate(12 9)">{LINK_GLYPHS[key]}</g>'
          f'<g class="label">{d.text("sans", 14, label, 36, 22)}</g>')
    d.animate("gd", "animation:led 4.3s ease-in-out infinite", "led")
    d.rule(f".chip{{fill:{t['surface']};stroke:{t['line_strong']}}}.glyph{{fill:none;stroke:{t['accent']};stroke-width:1.5;"
           f"stroke-linecap:round;stroke-linejoin:round}}.label{{fill:{t['text']}}}")
    return d.render(H, label, label), d.anim
