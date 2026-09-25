"""Shared building blocks for every SVG component.

Motion rules (REDESIGN §5): CSS only (no SMIL), animate transform / opacity / stroke-dashoffset
(plus offset-distance for motion along a path), prime-ish periods, entrances once, ambient loops
forever, and every SVG looks complete when animation is off.

Engine notes (tested through <img> in Chromium, Firefox and WebKit):
- inside <clipPath>/<mask>, use a px transform-origin; Firefox does not draw fill-box there.
- CSS offset-path works in all three engines, so paths never need SMIL <animateMotion>.
"""
from __future__ import annotations

import re

from svgkit import SANS_STACK, GlyphAtlas, esc, esc_text, num

RM = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"

# Keyframes shared by several components; emitted only when used.
KEYFRAMES = {
    "fade": "from{opacity:0}",
    "rise": "from{opacity:0;transform:translateY(8px)}",
    "draw": "from{stroke-dashoffset:100}",
    "led": "0%,100%{opacity:.35}50%{opacity:1}",
    "blink": "50%{opacity:0}",
    "march": "to{stroke-dashoffset:-16}",
    "orbit": "from{offset-distance:0%}to{offset-distance:100%}",
    "type": "from{transform:scaleX(0)}",
    "glowb": "0%,100%{opacity:.55;transform:scale(.94)}50%{opacity:1;transform:scale(1.04)}",
}

# In-house 16px stroke icons (no brand marks).
ICONS = {
    "agents": '<circle cx="8" cy="4" r="2.4"/><circle cx="3.5" cy="12" r="2.4"/><circle cx="12.5" cy="12" r="2.4"/><path d="M6.8 6.1 4.7 9.9M9.2 6.1l2.1 3.8M5.9 12h4.2"/>',
    "spec": '<path d="M3.5 1.5h6l3 3v10h-9z"/><path d="M9.5 1.5v3h3M5.5 8h5M5.5 10.5h5M5.5 13h3"/>',
    "build": '<path d="M8 1.8 14.2 5 8 8.2 1.8 5z"/><path d="M1.8 8.2 8 11.4l6.2-3.2M1.8 11.4 8 14.6l6.2-3.2"/>',
    "audit": '<circle cx="7" cy="7" r="4.6"/><path d="m10.4 10.4 3.8 3.8M4.6 7h4.8"/>',
    "ship": '<path d="M8 10.5V1.8M4.6 5 8 1.6 11.4 5"/><path d="M2 9.5v4.7h12V9.5"/>',
    "lock": '<rect x="3" y="7" width="10" height="7.5" rx="1.6"/><path d="M5.3 7V5a2.7 2.7 0 0 1 5.4 0v2"/>',
    "branch": '<circle cx="4" cy="3.5" r="1.8"/><circle cx="4" cy="12.5" r="1.8"/><circle cx="11.5" cy="5.5" r="1.8"/><path d="M4 5.3v5.4M11.5 7.3c0 3-7.5 1.6-7.5 3.4"/>',
    "search": '<circle cx="7" cy="7" r="4.6"/><path d="m10.4 10.4 3.8 3.8"/>',
    "clock": '<circle cx="8" cy="8" r="6.2"/><path d="M8 4.6V8l2.6 1.6"/>',
    "console": '<rect x="1.5" y="2.5" width="13" height="11" rx="2"/><path d="M4.5 6.5 6.5 8l-2 1.5M8 10h3.5"/>',
    "index": '<path d="M2 3.5h12M2 8h12M2 12.5h12"/><path d="M5 2v3M9 6.5v3M6.5 11v3"/>',
}


class Doc:
    """Collects defs, CSS and body for one SVG, and counts animated elements."""

    def __init__(self, w: int, theme: dict, prefix: str = "g"):
        self.w, self.t = w, theme
        self.css: list[str] = []
        self.defs: list[str] = []
        self.body: list[str] = []
        self.anim = 0
        self.at = GlyphAtlas(prefix)
        self._kf: dict[str, str] = {}

    # ---- styling / motion
    def rule(self, css: str) -> None:
        self.css.append(css)

    def keyframes(self, name: str, frames: str | None = None) -> str:
        self._kf.setdefault(name, frames if frames is not None else KEYFRAMES[name])
        return name

    def animate(self, cls: str, decl: str, *uses: str) -> None:
        """Register one animated element (class `cls`). `uses` names shared keyframes."""
        for u in uses:
            self.keyframes(u)
        self.css.append(f".{cls}{{{decl}}}")
        self.anim += 1

    # ---- text (always outlined paths from the committed fonts)
    def text(self, kind: str, size: float, s: str, x: float, y: float, tr: float = 0.0, anchor: str = "start") -> str:
        return self.at.text(kind, size, s, x, y, tr, anchor)

    def body_text(self, size: float, s: str, x: float, y: float, cls: str, anchor: str = "start") -> str:
        """Body copy as real <text> in the system sans stack (wrapping is measured with Inter,
        which is wider than Segoe UI / SF / Helvetica, so lines never overflow)."""
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        return f'<text class="{cls}" x="{num(x)}" y="{num(y)}"{a} font-size="{num(size)}">{esc_text(s)}</text>'

    def width(self, kind: str, size: float, s: str, tr: float = 0.0) -> float:
        return self.at.width(kind, size, s, tr)

    def add(self, *parts: str) -> None:
        self.body.extend(parts)

    def icon(self, name: str, x: float, y: float, cls: str = "ic", scale: float = 1.0) -> str:
        tf = f"translate({num(x)} {num(y)})" + (f" scale({num(scale)})" if scale != 1 else "")
        return f'<g class="{cls}" transform="{tf}">{ICONS[name]}</g>'

    # ---- typing reveal: clip rect scaled in steps (px origin: Firefox-safe)
    def typed(self, key: str, kind: str, size: float, s: str, x: float, y: float, start: float,
              per_char: float = 0.03, tr: float = 0.0, cls: str = "") -> tuple[str, float]:
        w = self.width(kind, size, s, tr)
        self.defs.append(f'<clipPath id="{key}c"><rect class="{key}r" x="{num(x - 1)}" y="{num(y - size * 1.05)}" '
                         f'width="{num(w + 4)}" height="{num(size * 1.45)}"/></clipPath>')
        dur = max(len(s), 1) * per_char
        self.animate(f"{key}r", f"transform-origin:{num(x - 1)}px {num(y)}px;"
                                f"animation:type {dur:.2f}s steps({max(len(s), 1)},end) {start:.2f}s backwards", "type")
        return f'<g class="{cls}" clip-path="url(#{key}c)">{self.text(kind, size, s, x, y, tr)}</g>', start + dur

    def render(self, h: float, title: str, desc: str) -> str:
        kfs = "".join(f"@keyframes {n}{{{f}}}" for n, f in self._kf.items())
        font_rule = f"text{{font-family:{SANS_STACK}}}" if any("<text " in part for part in self.body) else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{num(h)}" '
                f'viewBox="0 0 {self.w} {num(h)}" role="img" aria-labelledby="t d">\n'
                f'<title id="t">{esc(title)}</title>\n<desc id="d">{esc(desc)}</desc>\n'
                f'<style>{font_rule}{"".join(self.css)}{kfs}\n{RM}</style>\n'
                f'<defs>{"".join(self.defs)}{self.at.defs_svg()}</defs>\n'
                + "".join(self.body) + "\n</svg>\n")


# ---------------------------------------------------------------- copy helpers

def lead(text: str) -> str:
    """First sentence, verbatim."""
    return re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]


def split_tokens(doc: Doc, kind: str, size: float, tokens: list[str], sep: str, max_w: float, tr: float = 0.0) -> list[str]:
    lines, cur = [], ""
    for tok in tokens:
        cand = f"{cur}{sep}{tok}" if cur else tok
        if doc.width(kind, size, cand, tr) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = tok
    return lines + ([cur] if cur else [])


def wrap(doc: Doc, kind: str, size: float, text: str, max_w: float, tr: float = 0.0) -> list[str]:
    return split_tokens(doc, kind, size, text.split(" "), " ", max_w, tr)


def radial_glow(doc: Doc, gid: str, color: str, opacity: str) -> None:
    doc.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
                    f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


def hgrad(doc: Doc, gid: str, color: str, a: str = "0", b: str = "1", mid: str | None = None, mid_at: str = ".5") -> None:
    stops = (f'<stop offset="0" stop-color="{color}" stop-opacity="{a}"/>'
             + (f'<stop offset="{mid_at}" stop-color="{color}" stop-opacity="{mid}"/>' if mid else "")
             + f'<stop offset="1" stop-color="{color}" stop-opacity="{b}"/>')
    doc.defs.append(f'<linearGradient id="{gid}" x1="0" x2="1">{stops}</linearGradient>')
