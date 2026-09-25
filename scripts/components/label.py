"""Section label: a terminal command strip that sits above each native `##` heading."""
from __future__ import annotations

from svgkit import esc_text, num

from .base import Doc, hgrad

SIZES = {"desktop": (52, 15), "mobile": (46, 13)}


def render(t: dict, command: str, tier: str, width: int, host: str = "~/hunainx") -> tuple[str, int]:
    """desktop: full-width strip (>= 1260px viewports, never scaled below 0.98).
    mobile: drawn at its natural width (under the 308px phone column), so it renders 1:1 at
    every narrower viewport and needs no mid tier."""
    H, fs = SIZES[tier]
    if tier != "desktop":
        probe = Doc(10, t)
        width = int(16 + 18 + probe.width("mono", fs, host) + fs * 1.8 + probe.width("mono", fs, command) + 4 + fs * .6 + 16)
    W = width
    d = Doc(W, t)
    pad, k = 16, 9
    cy = H / 2
    base_y = cy + fs * .36

    d.add(f'<rect class="bg" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="3"/>')
    br = (f"M.75 {k}V.75H{k}M{W - k} .75H{W - .75}V{k}M{W - .75} {H - k}V{H - .75}H{W - k}"
          f"M{k} {H - .75}H.75V{H - k}")
    d.add(f'<path class="br" pathLength="100" stroke-dasharray="100" d="{br}"/>')
    d.animate("br", "animation:draw 1s cubic-bezier(.6,0,.2,1) backwards", "draw")

    d.add(f'<circle class="led" cx="{pad + 4}" cy="{num(cy)}" r="3.5"/>')
    d.animate("led", "animation:dblink 3.1s steps(1,end) infinite")
    d.keyframes("dblink", "0%{opacity:1}6%{opacity:.25}12%{opacity:1}55%{opacity:1}60%{opacity:.25}64%,100%{opacity:1}")

    x = pad + 18
    # one text run in the system mono stack; the cursor is a character, so it follows the text in any font
    d.add(f'<text class="mo" x="{x}" y="{num(base_y)}" font-size="{fs}" xml:space="preserve">'
          f'<tspan class="host">{esc_text(host)}</tspan> <tspan class="dol">$</tspan> '
          f'<tspan class="cmd">{esc_text(command)}</tspan><tspan class="cur">\u2588</tspan></text>')
    d.animate("cur", "animation:fblink 1.1s steps(1,end) infinite")
    d.keyframes("fblink", "50%{fill-opacity:0}")
    # JetBrains Mono (0.6em) is as wide or wider than the system mono fonts, so the rule never overlaps
    x += d.width("mono", fs, f"{host} $ {command}") + fs * .6 + 14

    end = W - pad - 6
    if x < end - 30:
        d.add(f'<path class="rule" d="M{num(x)} {num(cy + .5)}H{end - 4}"/>'
              f'<rect class="endn" x="{end}" y="{num(cy - 2.5)}" width="5" height="5" rx="1"/>')
        dist = end - 52 - x
        hgrad(d, "pg", t["accent"], "0", "1")
        d.add(f'<rect class="pulse" x="{num(x)}" y="{num(cy - .5)}" width="48" height="2" fill="url(#pg)"/>')
        d.animate("pulse", "opacity:0;animation:lpulse 6.7s cubic-bezier(.45,0,.3,1) 1.4s infinite")
        d.keyframes("lpulse", f"0%{{opacity:1;transform:translateX(0)}}40%{{opacity:1;transform:translateX({num(dist)}px)}}"
                              f"46%,100%{{opacity:0;transform:translateX({num(dist)}px)}}")
        d.animate("endn", "animation:led 2.9s ease-in-out 2s infinite", "led")

    hgrad(d, "sg", t["text"], "0", ".10")
    d.add(f'<rect class="sweep" x="-60" y="1" width="60" height="{H - 2}" fill="url(#sg)"/>')
    d.animate("sweep", "animation:lsweep 7.9s cubic-bezier(.45,0,.3,1) .9s infinite")
    d.keyframes("lsweep", f"0%{{transform:translateX(0)}}30%,100%{{transform:translateX({W + 60}px)}}")

    d.rule(f".bg{{fill:{t['surface']};fill-opacity:.55;stroke:none}}.br{{fill:none;stroke:{t['muted']};stroke-width:1.5}}"
           f".led{{fill:{t['accent']}}}.host{{fill:{t['muted']}}}.dol{{fill:{t['accent_text']}}}.cmd{{fill:{t['text']}}}"
           f".cur{{fill:{t['accent']}}}.rule{{stroke:{t['line_strong']}}}.endn{{fill:{t['line_strong']}}}")
    return d.render(H, f"$ {command}", f"{host} $ {command}"), d.anim
