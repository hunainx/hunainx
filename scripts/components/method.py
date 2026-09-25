"""How I work: the profile.yml `method` as an animated diagram.

A signal travels the track; each stage lights as it passes. A dashed loop returns from the last
stage to "Specify" (the method feeds what breaks back into the spec). Desktop is one row of 8;
mid and mobile are two rows of 4 joined by an elbow lane. Stage names are verbatim (uppercase).
"""
from __future__ import annotations

import math

from svgkit import num

from .base import Doc, split_tokens

PERIOD = 11.3


def _seg_len(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def render(t: dict, method: list[dict], tier: str, width: int, return_to: str = "Specify") -> tuple[str, int]:
    W = width
    d = Doc(W, t)
    stages = [(m["stage"].strip(), m["line"].strip()) for m in method if (m.get("stage") or "").strip()]
    n = len(stages)
    fs = 13 if tier == "mobile" else 12
    tr = 0 if tier == "mobile" else 1.2
    r = 10
    if tier == "desktop":
        pad = 44
        cols, rows = n, 1
    else:
        pad = 48 if tier == "mid" else 36
        cols, rows = math.ceil(n / 2), 2
    # keep the outer labels inside the frame: pad by half the widest label that won't wrap
    step0 = (W - 2 * pad) / max(cols - 1, 1)
    widest = max((d.width("mono", fs, s.upper(), tr) for s, _ in stages if d.width("mono", fs, s.upper(), tr) <= step0 - 10),
                 default=0)
    pad = max(pad, widest / 2 + 12)
    step = (W - 2 * pad) / max(cols - 1, 1)
    row_gap = 104
    y1 = 58
    pts = []
    for i in range(n):
        rr, cc = divmod(i, cols)
        pts.append((pad + cc * step, y1 + rr * row_gap))
    H = y1 + (rows - 1) * row_gap + 70

    # track through every stage (with the elbow lane between rows)
    track = [pts[0]]
    for i in range(1, n):
        a, b = pts[i - 1], pts[i]
        if b[1] != a[1]:
            lane = a[1] + 52
            track += [(a[0], lane), (b[0], lane)]
        track.append(b)
    tpath = "M" + "L".join(f"{num(x)} {num(y)}" for x, y in track)
    seglens = [_seg_len(track[k], track[k + 1]) for k in range(len(track) - 1)]
    total = sum(seglens)
    # distance along the track at which each stage sits
    at, acc, k = [], 0.0, 0
    for i, p in enumerate(pts):
        while track[k] != p:
            acc += seglens[k]
            k += 1
        at.append(acc / total if total else 0)

    d.add(f'<path class="trk" d="{tpath}"/><path class="flw" d="{tpath}"/>')
    d.animate("flw", "animation:march 1.9s linear infinite", "march")

    # return loop: last stage -> `return_to`
    names = [s for s, _ in stages]
    ri = names.index(return_to) if return_to in names else None
    if ri is not None:
        a, b = pts[-1], pts[ri]
        if rows == 1:
            lift = 40
            loop = f"M{num(a[0])} {num(a[1] - r - 2)}C{num(a[0])} {num(a[1] - lift - r)} {num(b[0])} {num(b[1] - lift - r)} {num(b[0])} {num(b[1] - r - 2)}"
            chev = f"M{num(b[0] - 3.5)} {num(b[1] - r - 7)}l3.5 4 3.5-4"
        else:
            bulge = 26
            loop = (f"M{num(a[0] + r + 2)} {num(a[1])}C{num(a[0] + r + bulge)} {num(a[1])} {num(b[0] + r + bulge)} {num(b[1])} "
                    f"{num(b[0] + r + 2)} {num(b[1])}")
            chev = f"M{num(b[0] + r + 7)} {num(b[1] - 3.5)}l-4 3.5 4 3.5"
        d.add(f'<path class="loop" d="{loop}"/><path class="chev" d="{chev}"/><rect class="rp" x="-3.5" y="-2" width="7" height="4" rx="2"/>')
        d.animate("rp", f"offset-path:path('{loop}');offset-rotate:auto;opacity:0;animation:ret {PERIOD}s cubic-bezier(.5,0,.5,1) {PERIOD * .92:.2f}s infinite")
        d.keyframes("ret", "0%{offset-distance:0%;opacity:0}3%{opacity:1}18%{opacity:1}22%,100%{offset-distance:100%;opacity:0}")

    # the signal
    d.add('<circle class="sig" r="4"/>')
    d.animate("sig", f"offset-path:path('{tpath}');animation:sigm {PERIOD}s linear infinite")
    d.keyframes("sigm", "0%{offset-distance:0%;opacity:0}2%{opacity:1}90%{offset-distance:100%;opacity:1}92%,100%{offset-distance:100%;opacity:0}")

    # stages: node, halo that fires as the signal arrives, label below
    for i, ((stage, _), (x, y)) in enumerate(zip(stages, pts)):
        d.add(f'<circle class="node" cx="{num(x)}" cy="{num(y)}" r="{r}"/><circle class="pip" cx="{num(x)}" cy="{num(y)}" r="3"/>')
        d.add(f'<circle class="lit h{i}" cx="{num(x)}" cy="{num(y)}" r="{r}"/>')
        d.animate(f"h{i}", f"transform-origin:{num(x)}px {num(y)}px;opacity:0;animation:lit {PERIOD}s ease-out {PERIOD * .9 * at[i]:.2f}s infinite")
        label = stage.upper()
        lines = split_tokens(d, "mono", fs, label.split(" "), " ", step - 10 if cols > 1 else W, tr)
        for j, ln in enumerate(lines):
            d.add(d.mono_text(fs, ln, x, y + r + 20 + j * (fs + 4), "lbl", "middle", tr))
    d.keyframes("lit", "0%{opacity:1;transform:scale(1.35)}25%{opacity:.9;transform:scale(1)}60%,100%{opacity:0;transform:scale(1)}")

    d.rule(f".trk{{fill:none;stroke:{t['line_strong']}}}.flw{{fill:none;stroke:{t['accent']};stroke-opacity:.35;stroke-dasharray:2 7}}"
           f".node{{fill:{t['surface']};stroke:{t['line_strong']}}}.pip{{fill:{t['muted']}}}"
           f".lit{{fill:{t['accent']};fill-opacity:.18;stroke:{t['accent']};stroke-width:1.5}}"
           f".sig{{fill:{t['accent']}}}.lbl{{fill:{t['text']}}}"
           f".loop{{fill:none;stroke:{t['accent2']};stroke-opacity:.6;stroke-dasharray:3 4}}.chev{{fill:none;stroke:{t['accent2']};stroke-width:1.2}}"
           f".rp{{fill:{t['accent2']}}}")
    desc = "Method: " + " ".join(f"{s}: {ln}" for s, ln in stages) + (f" Loop: {stages[-1][0]} back to {return_to}." if ri is not None else "")
    return d.render(H, "How I work", desc), d.anim
