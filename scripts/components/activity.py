"""Activity panel.

Low-data state (below the contribution threshold): a radar whose blips are the real weeks with
public contributions in github.json (angle = week position in the 52-week window), plus the
owner-approved "building in private" label and the true public total.

Data state (threshold met): stats row, a daily heatmap revealed as a diagonal wave, and
language bars. Every number comes from github.json.
"""
from __future__ import annotations

import math

from svgkit import num

from .base import Doc, hgrad

SWEEP = 5.3


def low_data(t: dict, gh: dict, labels: dict, tier: str, width: int) -> tuple[str, int]:
    W = width
    d = Doc(W, t)
    mobile = tier == "mobile"
    weeks = gh["contributions"]["weeks"]
    total = gh["contributions"]["total_12mo"]
    R = 58 if not mobile else 50
    H = 2 * R + 60 if not mobile else 2 * R + 170
    cx, cy = (24 + R + 10, H / 2) if not mobile else (W / 2, 30 + R)

    d.add(f'<rect class="panel" x=".5" y=".5" width="{W - 1}" height="{num(H - 1)}" rx="10"/>')
    rings = "".join(f'<circle class="ring" cx="{num(cx)}" cy="{num(cy)}" r="{num(R * f)}"/>' for f in (1, .66, .33))
    cross = f'<path class="ring" d="M{num(cx - R)} {num(cy)}H{num(cx + R)}M{num(cx)} {num(cy - R)}V{num(cy + R)}"/>'
    d.add(rings, cross)
    # sweep wedge (rotating sector with a fading trail)
    a = math.radians(38)
    wedge = (f"M{num(cx)} {num(cy)}L{num(cx + R)} {num(cy)}"
             f"A{R} {R} 0 0 1 {num(cx + R * math.cos(a))} {num(cy + R * math.sin(a))}Z")
    # the beam leads (counter-clockwise); the fading trail sits behind it, below the beam
    d.defs.append(f'<linearGradient id="wg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".45"/>'
                  f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></linearGradient>')
    d.add(f'<g class="swp"><path d="{wedge}" fill="url(#wg)"/><path class="beam" d="M{num(cx)} {num(cy)}H{num(cx + R)}"/></g>')
    d.animate("swp", f"transform-origin:{num(cx)}px {num(cy)}px;animation:spin {SWEEP}s linear infinite")
    d.keyframes("spin", "from{transform:rotate(0)}to{transform:rotate(-360deg)}")

    # blips: one per week that has public contributions (real data), capped at 12
    active = [(i, w["count"]) for i, w in enumerate(weeks) if w["count"] > 0][-12:]
    peak = max((c for _, c in active), default=1)
    for j, (i, c) in enumerate(active):
        ang = 2 * math.pi * i / max(len(weeks), 1)
        rr = R * (.35 + .55 * (c / peak))
        bx, by = cx + rr * math.cos(ang), cy - rr * math.sin(ang)
        d.add(f'<circle class="blip b{j}" cx="{num(bx)}" cy="{num(by)}" r="3"/>')
        # counter-clockwise sweep reaches angle `ang` after ang/2π of a turn
        delay = SWEEP * (ang / (2 * math.pi))
        d.animate(f"b{j}", f"animation:blip {SWEEP}s linear {delay:.2f}s infinite backwards")
    d.keyframes("blip", "0%{opacity:1}35%{opacity:.35}100%{opacity:.35}")

    # slow scan across the panel
    hgrad(d, "scg", t["text"], "0", ".06")
    d.add(f'<rect class="scan" x="-80" y="1" width="80" height="{num(H - 2)}" fill="url(#scg)"/>')
    d.animate("scan", "animation:pscan 11.9s cubic-bezier(.45,0,.3,1) 1s infinite")
    d.keyframes("pscan", f"0%{{transform:translateX(0)}}35%,100%{{transform:translateX({W + 80}px)}}")

    # text block
    if not mobile:
        tx, ty = cx + R + 40, cy - 16
    else:
        tx, ty = 20, cy + R + 42
    head = labels["activity_header"]
    d.add(f'<circle class="led" cx="{num(tx + 3.5)}" cy="{num(ty - 26)}" r="3"/>'
          f'<g class="head">{d.text("mono", 12, head, tx + 14, ty - 22, 2)}</g>')
    d.animate("led", "animation:led 2.3s ease-in-out infinite", "led")
    fs = 22 if not mobile else 19
    g, end = d.typed("bl", "mono", fs, labels["activity_low"], tx, ty + 12, 1.0, .06, 0, "big")
    d.add(g)
    cw = d.width("mono", fs, labels["activity_low"])
    d.add(f'<rect class="cur" x="{num(tx + cw + 3)}" y="{num(ty + 12 - fs * .8)}" width="{num(fs * .6 - 1)}" height="{num(fs * 1.02)}"/>')
    d.animate("cur", "animation:blink 1.1s steps(1,end) infinite", "blink")
    cap = f"{total} {labels['activity_caption']}"
    d.add(d.body_text(15, cap, tx, ty + 44, "cap"))

    d.rule(f".panel{{fill:{t['surface']};stroke:{t['line']}}}.ring{{fill:none;stroke:{t['line_strong']}}}"
           f".beam{{stroke:{t['accent']};stroke-width:1.5}}.blip{{fill:{t['accent']}}}.led{{fill:{t['accent']}}}"
           f".head{{fill:{t['muted']}}}.big{{fill:{t['text']}}}.cur{{fill:{t['accent']}}}.cap{{fill:{t['muted']}}}")
    desc = f"Activity: {labels['activity_low']}. {cap}."
    return d.render(H, "Activity", desc), d.anim


def with_data(t: dict, gh: dict, profile: dict, cfg: dict, tier: str, width: int) -> tuple[str, int]:
    W = width
    d = Doc(W, t)
    labels, th = cfg["labels"], cfg["thresholds"]
    mobile = tier == "mobile"
    pad = 20
    y = 20
    # stats row
    tiles = []
    if gh["eligible_public_repos"] >= th["stats_min_public_repos"]:
        tiles.append((labels["public_repos"], str(gh["eligible_public_repos"])))
        if gh["stars_earned"] > 0:
            tiles.append((labels["stars"], str(gh["stars_earned"])))
    tiles.append((labels["contributions"], str(gh["contributions"]["total_12mo"])))
    if profile.get("show_private_contribution_count") and gh.get("private_contributions_12mo", 0) > 0:
        tiles.append((labels["private_contributions"], str(gh["private_contributions_12mo"])))
    cols = len(tiles) if not mobile else 2
    tw = (W - 2 * pad) / cols
    for i, (lab, val) in enumerate(tiles):
        c, r = i % cols, i // cols
        x, yy = pad + c * tw, y + r * 70
        d.add(f'<g class="val">{d.text("display", 28, val, x, yy + 32)}</g>')
        d.add(f'<path class="ul u{i}" pathLength="100" stroke-dasharray="100" d="M{num(x)} {num(yy + 42)}h32"/>')
        d.animate(f"u{i}", f"animation:draw .9s cubic-bezier(.2,.7,.2,1) {.3 + i * .12:.2f}s backwards", "draw")
        d.add(d.body_text(14, lab, x, yy + 62, "lbl"))
    y += ((len(tiles) + cols - 1) // cols) * 70 + 16

    # heatmap: 52 weeks x 7 days, revealed as a diagonal wave (cells grouped into bands)
    weeks = gh["contributions"]["weeks"]
    peak = max((c for w in weeks for c in w.get("days", [])), default=0) or 1
    # cell size fits 52 columns into the tier width
    cs, gp = {"desktop": (11, 3), "mid": (8, 2.4), "mobile": (4.6, 1.3)}[tier]
    gx = pad
    nb = 20
    # one path per (wave band, level). A cell is a zero-length stroke with a square cap
    # (stroke-width = cell size), reached by a relative move from the previous cell.
    cells: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for wi, w in enumerate(weeks):
        for di, c in enumerate(w.get("days", [])):
            lvl = 0 if c == 0 else min(4, 1 + int(3 * c / peak))
            b = (wi + di) * nb // (len(weeks) + 7)
            cells.setdefault((b, lvl), []).append((gx + wi * (cs + gp) + cs / 2, y + di * (cs + gp) + cs / 2))
    def cell_path(pts):
        out, px, py = [], None, None
        for x, yy in pts:
            out.append(f"M{num(x)} {num(yy)}h0" if px is None else f"m{num(x - px)} {num(yy - py)}h0")
            px, py = x, yy
        return "".join(out)
    for b in sorted({k[0] for k in cells}):
        d.add(f'<g class="w{b}">' + "".join(f'<path class="h{lvl}" d="{cell_path(cells[(b, lvl)])}"/>'
                                            for lvl in range(5) if (b, lvl) in cells) + "</g>")
        d.animate(f"w{b}", f"animation:fade .5s ease-out {.4 + b * .06:.2f}s backwards", "fade")
    total = gh["contributions"]["total_12mo"]
    cap = f"{total} {labels['activity_caption']}"
    y += 7 * (cs + gp) + 26
    d.add(d.body_text(14, cap, pad, y, "lbl"))
    y += 22

    # language bars
    share = gh.get("language_share") or []
    colors = gh.get("language_colors", {})
    if gh.get("repos_with_language_bytes", 0) >= th["languages_min_repos"] and share:
        bw = W - 2 * pad - 176
        for i, s in enumerate(share):
            yy = y + i * 24
            d.add(d.body_text(14, s["name"], pad, yy + 11, "lbl"))
            d.add(f'<rect class="track" x="{pad + 110}" y="{yy + 2}" width="{num(bw)}" height="8" rx="4"/>')
            d.add(f'<rect class="bar r{i}" x="{pad + 110}" y="{yy + 2}" width="{num(max(bw * float(s["pct"]) / 100, 3))}" height="8" rx="4" '
                  f'fill="{colors.get(s["name"], t["faint"])}"/>')
            d.animate(f"r{i}", f"transform-origin:{pad + 110}px {yy + 6}px;animation:grow .9s cubic-bezier(.2,.7,.2,1) {.6 + i * .1:.2f}s backwards")
            d.add(f'<g class="pct">{d.text("mono", 13, s["pct"] + "%", W - pad, yy + 11, 0, "end")}</g>')
        d.keyframes("grow", "from{transform:scaleX(0)}")
        y += len(share) * 24 + 4
    H = y + 12
    d.body.insert(0, f'<rect class="panel" x=".5" y=".5" width="{W - 1}" height="{num(H - 1)}" rx="10"/>')
    lv = [t["line"], t["accent"], t["accent"], t["accent"], t["accent"]]
    op = [1, .35, .55, .78, 1]
    d.rule(f".panel{{fill:{t['surface']};stroke:{t['line']}}}.val{{fill:{t['text']}}}.lbl{{fill:{t['muted']}}}.pct{{fill:{t['muted']}}}"
           f".ul{{stroke:{t['accent']};stroke-width:2;stroke-linecap:round;fill:none}}.track{{fill:{t['line']}}}"
           + f"[class^=h]{{stroke-width:{num(cs)};stroke-linecap:square;fill:none}}"
           + "".join(f".h{i}{{stroke:{lv[i]};stroke-opacity:{op[i]}}}" for i in range(5)))
    desc = "; ".join(f"{a}: {v}" for a, v in tiles) + f". {total} {labels['activity_caption']}." + (
        " Languages: " + ", ".join(f'{s["name"]} {s["pct"]}%' for s in share) + "." if share else "")
    return d.render(H, "Activity", desc), d.anim
