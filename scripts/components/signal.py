"""Shipping signal: real counts from data/github.json, nothing else.

Each count has its own threshold in config `signal`; a count that is missing from github.json
(unavailable) or below its threshold is not drawn, and nothing is drawn in its place. The
contributions count gates the panel: when it is missing or below its threshold, the section is
omitted. The caption names the data source that fetch.py recorded.
Counts only: no repository names, no charts, no derived figures.
"""
from __future__ import annotations

from svgkit import num

import re

from .base import Doc, balanced, hgrad


def tiles(gh: dict, cfg: dict) -> list[tuple[str, int]]:
    """(label, value) for every count that exists and meets its threshold, in display order."""
    sig, th, lab = gh.get("signal") or {}, cfg["signal"], cfg["labels"]
    cands = [
        (lab["contributions"], sig.get("contributions_12mo"), th["contributions_min"]),
        (lab["repos_contributed"], sig.get("repos_contributed_12mo"), th["repos_contributed_min"]),
        (lab["public_repos"], gh.get("eligible_public_repos"), th["public_repos_min"]),
        (lab["stars"], gh.get("stars_earned"), th["stars_min"]),
    ]
    out = [(label, int(v)) for label, v, minimum in cands if isinstance(v, int) and v >= minimum]
    # the contributions count is the headline: without it the panel is not shown at all
    return out if out and out[0][0] == lab["contributions"] else []


def caption(gh: dict, cfg: dict) -> str:
    mode = (gh.get("signal") or {}).get("mode")
    return cfg["labels"]["signal_token" if mode == "profile_read_token" else "signal_public"]


def render(t: dict, gh: dict, cfg: dict, tier: str, width: int) -> tuple[str, int]:
    W = width
    d = Doc(W, t)
    items = tiles(gh, cfg)
    head, cap = cfg["labels"]["signal_header"], caption(gh, cfg)
    mobile = tier == "mobile"
    pad = 22 if not mobile else 18
    num_fs = 34 if not mobile else 30

    # left block (header + source) beside the tiles; on phones it sits above them
    lead_w = {"desktop": 250, "mid": 190, "mobile": W - 2 * pad}[tier]
    cols = min(len(items), 4) if not mobile else min(len(items), 2)
    tx0 = pad + (lead_w + 24 if not mobile else 0)
    tw = (W - pad - tx0) / max(cols, 1)
    # a parenthesised qualifier such as "(12 mo)" never breaks across lines
    labels = [balanced(d, "sans", 14, re.findall(r"\([^)]*\)|\S+", lab), " ", tw - (24 if not mobile else 10)) for lab, _ in items]
    rows = (len(items) + cols - 1) // cols
    row_h = [max([len(labels[k]) for k in range(r * cols, min(len(items), (r + 1) * cols))]) * 19 + 58 for r in range(rows)]
    ty0 = 26 if not mobile else 86
    H = max(ty0 + sum(row_h) + 18, 118 if not mobile else 0)

    d.add(f'<rect class="panel" x=".5" y=".5" width="{W - 1}" height="{num(H - 1)}" rx="10"/>')
    # a slow scan across the panel (decorative, carries no data)
    hgrad(d, "scg", t["text"], "0", ".06")
    d.add(f'<rect class="scan" x="-80" y="1" width="80" height="{num(H - 2)}" fill="url(#scg)"/>')
    d.animate("scan", "animation:pscan 11.9s cubic-bezier(.45,0,.3,1) 1s infinite")
    d.keyframes("pscan", f"0%{{transform:translateX(0)}}35%,100%{{transform:translateX({W + 80}px)}}")

    hy = 40 if not mobile else 34
    lx = pad
    d.add(f'<circle class="led" cx="{num(lx + 4)}" cy="{num(hy - 4)}" r="3.5"/>'
          f'<circle class="ping" cx="{num(lx + 4)}" cy="{num(hy - 4)}" r="3.5"/>')
    d.animate("led", "animation:led 2.3s ease-in-out infinite", "led")
    d.animate("ping", f"transform-origin:{num(lx + 4)}px {num(hy - 4)}px;animation:ping 3.1s ease-out infinite")
    d.keyframes("ping", "0%{transform:scale(1);opacity:.7}70%,100%{transform:scale(2.3);opacity:0}")
    d.add(d.mono_text(12, head, lx + 20, hy, "head", "start", 2))
    d.add(d.mono_text(12, cap, lx + 20, hy + 22, "cap", "start", .4))
    if not mobile:
        d.add(f'<path class="sep" d="M{num(tx0 - 12.5)} 20V{num(H - 20)}"/>')

    for i, ((lab, val), lines) in enumerate(zip(items, labels)):
        c, r = i % cols, i // cols
        x = tx0 + c * tw + (12 if not mobile else 0)
        y = ty0 + sum(row_h[:r])
        d.add(f'<g class="val">{d.text("display", num_fs, str(val), x, y + 36)}</g>')
        d.add(f'<path class="ul u{i}" pathLength="100" stroke-dasharray="100" d="M{num(x)} {num(y + 48)}h32"/>')
        d.animate(f"u{i}", f"animation:draw .9s cubic-bezier(.2,.7,.2,1) {.3 + i * .12:.2f}s backwards", "draw")
        d.add("".join(d.body_text(14, ln, x, y + 70 + k * 19, "lbl") for k, ln in enumerate(lines)))

    d.rule(f".panel{{fill:{t['surface']};stroke:{t['line']}}}.led{{fill:{t['accent']}}}.ping{{fill:none;stroke:{t['accent']}}}"
           f".head{{fill:{t['text']}}}.cap,.lbl{{fill:{t['muted']}}}.val{{fill:{t['text']}}}.sep{{stroke:{t['line']}}}"
           f".ul{{stroke:{t['accent']};stroke-width:2;stroke-linecap:round;fill:none}}")
    desc = f"{head.capitalize()} ({cap}): " + "; ".join(f"{lab}: {v}" for lab, v in items) + "."
    return d.render(H, "Shipping signal", desc), d.anim
