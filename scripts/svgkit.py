"""Shared helpers for build.py and check.py: fonts → SVG paths, colour maths, escaping."""
from __future__ import annotations

import html
import re
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


_PTOK = re.compile(r"[MLHVQCZmlhvqcz]|-?(?:\d+\.?\d*|\.\d+)")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "Z": 0}


def _fmt10(n: int) -> str:
    """Format a value given in tenths as the shortest SVG number."""
    sign = "-" if n < 0 else ""
    n = abs(n)
    whole, frac = divmod(n, 10)
    if frac:
        return f"{sign}{whole if whole else ''}.{frac}"
    return f"{sign}{whole}"


def compact_path(d: str) -> str:
    """Absolute path (0.1px grid) -> compact relative path.

    - Deltas are taken between rounded absolute points (integer tenths), so the relative form
      reproduces the absolute points exactly: no accumulated rounding error.
    - A quadratic whose control point is the reflection of the previous one (TrueType's implied
      on-curve midpoints) becomes a smooth `t` segment with no control point. The reflection is
      allowed to differ by 0.1px, the grid resolution.
    - Repeated command letters are omitted (implicit repetition).
    """
    toks = _PTOK.findall(d)
    out: list[str] = []
    cx = cy = sx = sy = 0
    pq = None  # control point of the previous quadratic (absolute tenths), for reflection
    i, cmd = 0, None
    state = {"num": "", "cmd": ""}

    def emit_num(v: int) -> None:
        t = _fmt10(v)
        last = state["num"]
        if last and not t.startswith("-") and not (t.startswith(".") and "." in last):
            out.append(" ")
        out.append(t)
        state["num"] = t

    def emit_cmd(c: str) -> None:
        # implicit repetition: after "m" the implicit command is "l"
        implicit = "l" if state["cmd"] == "m" else state["cmd"]
        if c != implicit or c == "z":
            out.append(c)
            state["num"] = ""
        state["cmd"] = c

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i].upper()
            i += 1
            if cmd == "Z":
                out.append("z")
                state.update(num="", cmd="z")
                cx, cy = sx, sy
                pq = None
                continue
        n = _ARGS[cmd]
        vals = [round(float(v) * 10) for v in toks[i:i + n]]
        i += n
        if cmd == "M":
            emit_cmd("m")
            emit_num(vals[0] - cx); emit_num(vals[1] - cy)
            cx, cy = sx, sy = vals
            cmd, pq = "L", None
        elif cmd == "H":
            emit_cmd("h"); emit_num(vals[0] - cx); cx = vals[0]; pq = None
        elif cmd == "V":
            emit_cmd("v"); emit_num(vals[0] - cy); cy = vals[0]; pq = None
        elif cmd == "Q":
            qx, qy, ex, ey = vals
            if pq is not None and abs(qx - (2 * cx - pq[0])) <= 1 and abs(qy - (2 * cy - pq[1])) <= 1:
                emit_cmd("t")
                emit_num(ex - cx); emit_num(ey - cy)
                pq = (2 * cx - pq[0], 2 * cy - pq[1])  # the control the renderer will actually use
            else:
                emit_cmd("q")
                for v, c0 in zip(vals, (cx, cy, cx, cy)):
                    emit_num(v - c0)
                pq = (qx, qy)
            cx, cy = ex, ey
        else:
            emit_cmd(cmd.lower())
            for k in range(0, n, 2):
                emit_num(vals[k] - cx); emit_num(vals[k + 1] - cy)
            cx, cy = vals[n - 2], vals[n - 1]
            pq = None
    return "".join(out)


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


# Glyph outlines are defined once per font at this reference size; each text run is a group
# scaled to its real size, so every size of a font shares the same outlines.
REF = {"display": 48.0, "sans": 16.0, "mono": 16.0}


class GlyphAtlas:
    """Collects glyph outlines once per font and places them with <use>."""

    def __init__(self, prefix: str):
        self.prefix = prefix
        self.defs: dict[tuple, tuple[str, str]] = {}

    def _glyph_id(self, kind: str, gname: str) -> str | None:
        key = (kind, gname)
        if key not in self.defs:
            f = font(kind)
            gs = f.getGlyphSet()
            s = REF[kind] / f["head"].unitsPerEm
            pen = SVGPathPen(gs, ntos=num)
            gs[gname].draw(TransformPen(pen, (s, 0, 0, -s, 0, 0)))
            raw = pen.getCommands()
            self.defs[key] = (f"{self.prefix}{len(self.defs)}", compact_path(raw) if raw else "")
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
        k = size / REF[kind]
        glyphs, w = self.layout(kind, REF[kind], text, tracking / k)
        w *= k
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        uses = [f'<use href="#{gid}" x="{num(gx)}"/>' for g, gx in glyphs if (gid := self._glyph_id(kind, g))]
        if not uses:
            return ""
        tf = f"translate({num(x)} {num(y)})" + (f" scale({k:.4g})" if abs(k - 1) > 1e-9 else "")
        return f'<g transform="{tf}">' + "".join(uses) + "</g>"

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
