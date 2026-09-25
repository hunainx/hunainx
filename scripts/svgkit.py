"""Shared helpers for build.py and check.py: fonts → SVG paths, colour maths, escaping."""
from __future__ import annotations

import html
from functools import lru_cache
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = {
    "display": ROOT / "fonts" / "InterDisplay-SemiBold.ttf",
    "sans": ROOT / "fonts" / "Inter-Regular.ttf",
    "mono": ROOT / "fonts" / "JetBrainsMono-Medium.ttf",
}
SANS_STACK = '-apple-system, "Segoe UI", Helvetica, Arial, sans-serif'
MONO_STACK = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'


def esc(s: str) -> str:
    """Escape for attributes."""
    return html.escape(str(s), quote=True)


def esc_text(s: str) -> str:
    """Escape for text nodes; quotes stay literal so the README reads naturally."""
    return html.escape(str(s), quote=False)


def num(v: float) -> str:
    """Fixed-precision number formatting so output is deterministic."""
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ---------------------------------------------------------------- colour

def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---------------------------------------------------------------- fonts

@lru_cache(maxsize=None)
def font(kind: str) -> TTFont:
    return TTFont(FONTS[kind])


def _pair_lookups(f: TTFont):
    if "GPOS" not in f:
        return []
    gpos = f["GPOS"].table
    idx = set()
    for rec in gpos.FeatureList.FeatureRecord:
        if rec.FeatureTag == "kern":
            idx.update(rec.Feature.LookupListIndex)
    subs = []
    for i in sorted(idx):
        lk = gpos.LookupList.Lookup[i]
        for st in lk.SubTable:
            if lk.LookupType == 9:
                if st.ExtensionLookupType != 2:
                    continue
                st = st.ExtSubTable
            elif lk.LookupType != 2:
                continue
            subs.append(st)
    return subs


@lru_cache(maxsize=None)
def _kern_subtables(kind: str):
    return _pair_lookups(font(kind))


@lru_cache(maxsize=None)
def kern(kind: str, left: str, right: str) -> int:
    """GPOS pair kerning in font units (first matching subtable wins)."""
    for st in _kern_subtables(kind):
        cov = st.Coverage.glyphs
        if left not in cov:
            continue
        if st.Format == 1:
            ps = st.PairSet[cov.index(left)]
            for rec in ps.PairValueRecord:
                if rec.SecondGlyph == right:
                    return getattr(rec.Value1, "XAdvance", 0) or 0
        elif st.Format == 2:
            c1 = st.ClassDef1.classDefs.get(left, 0)
            c2 = st.ClassDef2.classDefs.get(right, 0)
            v = st.Class1Record[c1].Class2Record[c2].Value1
            return (getattr(v, "XAdvance", 0) or 0) if v else 0
    return 0


class GlyphAtlas:
    """Collects glyph outlines once per (font, size) and places them with <use>."""

    def __init__(self, prefix: str):
        self.prefix = prefix
        self.defs: dict[tuple, tuple[str, str]] = {}

    def _glyph_id(self, kind: str, size: float, gname: str) -> str | None:
        key = (kind, size, gname)
        if key not in self.defs:
            f = font(kind)
            gs = f.getGlyphSet()
            s = size / f["head"].unitsPerEm
            pen = SVGPathPen(gs, ntos=num)
            gs[gname].draw(TransformPen(pen, (s, 0, 0, -s, 0, 0)))
            d = pen.getCommands()
            self.defs[key] = (f"{self.prefix}{len(self.defs)}", d)
        gid, d = self.defs[key]
        return gid if d else None

    def width(self, kind: str, size: float, text: str, tracking: float = 0.0) -> float:
        return self.layout(kind, size, text, tracking)[1]

    def layout(self, kind: str, size: float, text: str, tracking: float = 0.0):
        f = font(kind)
        cmap = f.getBestCmap()
        hmtx = f["hmtx"]
        s = size / f["head"].unitsPerEm
        x, out, prev = 0.0, [], None
        for ch in text:
            g = cmap.get(ord(ch))
            if g is None:
                raise ValueError(f"glyph for {ch!r} missing in {kind} font")
            if prev is not None:
                x += kern(kind, prev, g) * s
            out.append((g, x))
            x += hmtx[g][0] * s + tracking
            prev = g
        return out, (x - tracking if text else 0.0)

    def text(self, kind: str, size: float, text: str, x: float, y: float,
             tracking: float = 0.0, anchor: str = "start") -> str:
        glyphs, w = self.layout(kind, size, text, tracking)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        uses = []
        for g, gx in glyphs:
            gid = self._glyph_id(kind, size, g)
            if gid:
                uses.append(f'<use href="#{gid}" x="{num(x + gx)}" y="{num(y)}"/>')
        return "".join(uses)

    def defs_svg(self) -> str:
        return "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in self.defs.values() if d)


def wrap(text: str, max_chars: int, sep: str = " ") -> list[str]:
    """Greedy word wrap by character count (used with monospace metrics)."""
    lines, cur = [], ""
    for word in text.split(sep):
        cand = f"{cur}{sep}{word}" if cur else word
        if len(cand) <= max_chars or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def wrap_width(atlas: GlyphAtlas, kind: str, size: float, text: str, max_w: float) -> list[str]:
    """Greedy word wrap by measured width in the given committed font."""
    lines, cur = [], ""
    for word in text.split(" "):
        cand = f"{cur} {word}" if cur else word
        if atlas.width(kind, size, cand) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines
