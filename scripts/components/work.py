"""Selected work card (one per public repo). Hidden while there are no eligible public repos."""
from __future__ import annotations

import datetime as dt

from svgkit import num

from .base import Doc, wrap


def render(t: dict, repo: dict, blurb: str, color: str, tier: str, width: int, idx: int = 0) -> tuple[str, int]:
    W = width
    d = Doc(W, t)
    pad = 20
    gh_h = 64
    lines = wrap(d, "sans", 14, blurb, W - 2 * pad) if blurb else []
    if len(lines) > 2:  # two lines at most; the second ends in an ellipsis
        second = lines[1]
        while second and d.width("sans", 14, second + "…") > W - 2 * pad:
            second = second.rsplit(" ", 1)[0] if " " in second else second[:-1]
        lines = [lines[0], second.rstrip(",.;:") + "…"]
    # fixed height (room for two lines) so cards in a row line up whatever the blurb length
    H = 24 + gh_h + 26 + 18 + 2 * 21 + 44
    rect = f'x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10"'
    d.add(f'<rect class="panel" {rect}/><rect class="run" {rect} pathLength="1000" stroke-dasharray="80 920"/>')
    d.animate("run", f"animation:run {9.1 + idx * 1.3:.1f}s linear infinite")
    d.keyframes("run", "to{stroke-dashoffset:-1000}")

    # mini diagram: a branch that forks and merges, commits flowing along it
    y0, x0, x1 = 24 + gh_h / 2, pad + 6, W - pad - 6
    main = f"M{num(x0)} {num(y0)}H{num(x1)}"
    fork = f"M{num(x0 + 60)} {num(y0)}C{num(x0 + 90)} {num(y0 - 22)} {num(x1 - 120)} {num(y0 - 22)} {num(x1 - 90)} {num(y0)}"
    d.add(f'<path class="br" d="{main}"/><path class="br" d="{fork}"/>')
    for j, fx in enumerate((x0, x0 + 60, x1 - 90, x1)):
        d.add(f'<circle class="cm" cx="{num(fx)}" cy="{num(y0)}" r="4"/>')
    for j, (p, per) in enumerate(((main, 4.3), (fork, 5.9))):
        d.add(f'<circle class="dot f{j}" r="2.4"/>')
        d.animate(f"f{j}", f"offset-path:path('{p}');animation:flow {per}s cubic-bezier(.5,0,.5,1) {j * 1.3:.1f}s infinite")
    d.keyframes("flow", "0%{offset-distance:0%;opacity:0}10%{opacity:1}90%{opacity:1}100%{offset-distance:100%;opacity:0}")

    y = 24 + gh_h + 26
    d.add(f'<g class="name">{d.text("mono", 16, repo["name"], pad, y)}</g>')
    d.add(f'<g class="cta">{d.text("mono", 16, "↗", W - pad, y, 0, "end")}</g>')
    d.animate("cta", "animation:nudge 2.7s ease-in-out infinite")
    d.keyframes("nudge", "0%,70%,100%{transform:translate(0,0)}80%{transform:translate(2px,-2px)}")
    y += 26
    for ln in lines:
        d.add(d.body_text(14, ln, pad, y, "blurb"))
        y += 21
    meta = []
    x = pad
    fy = H - 20
    if repo.get("language"):
        d.add(f'<circle cx="{x + 5}" cy="{fy - 4}" r="5" fill="{color}"/>')
        x += 16
        meta.append(repo["language"])
    if repo.get("stars", 0) > 0:
        meta.append(f"★ {repo['stars']}")
    meta.append("updated " + dt.date.fromisoformat(repo["pushed"]).strftime("%b %Y"))
    if repo.get("homepage"):
        meta.append("live ↗")
    d.add(d.body_text(13, "  ·  ".join(meta), x, fy, "meta").replace("<text ", '<text xml:space="preserve" '))
    d.rule(f".panel{{fill:{t['surface']};stroke:{t['line']}}}.run{{fill:none;stroke:{t['accent']};stroke-width:1.5;stroke-linecap:round}}"
           f".br{{fill:none;stroke:{t['line_strong']}}}.cm{{fill:{t['bg']};stroke:{t['accent']};stroke-width:1.5}}.dot{{fill:{t['accent']}}}"
           f".name{{fill:{t['text']}}}.cta{{fill:{t['accent_text']}}}.blurb{{fill:{t['muted']}}}.meta{{fill:{t['muted']}}}")
    desc = f"{repo['name']}" + (f": {blurb}" if blurb else "") + ". " + " · ".join(meta)
    return d.render(H, repo["name"], desc), d.anim
