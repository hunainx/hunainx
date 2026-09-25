"""Visual QA for the profile README (output in qa/, git-ignored).

  python scripts/preview.py                  # README shots + frames + engines + CPU
  python scripts/preview.py --only readme    # just the README screenshots
  python scripts/preview.py --only frames    # 0/1/3/6s + reduced-motion frames of every SVG
  python scripts/preview.py --dir qa/fixture # preview another build output

README shots: rendered through GitHub's real sanitizer (gh api markdown), dark/light, at 1280,
1100 and 390px, animated (after one-shot motion) and with real reduced motion. Frames: every
asset is loaded through <img> on one page, so all start together, then cropped at 0/1/3/6s.
Reduced motion uses a browser-level preference; CDP emulation does not reach <img> SVGs.
Needs gh (logged in) and playwright with chromium (+ firefox/webkit for --only engines).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import urllib.request
from io import BytesIO
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CSS_URL = "https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown.css"
# Viewport -> README column width measured on github.com/hunainx (content box).
VIEWPORTS = {"1280": (1280, 846, 1), "1100": (1100, 666, 1), "390": (390, 308, 2)}
BG = {"dark": "#0d1117", "light": "#ffffff"}
TIMES = (0, 1, 3, 6)


def render_html(readme: Path, login: str) -> str:
    return subprocess.run(["gh", "api", "markdown", "-f", "mode=gfm", "-f", f"context={login}/{login}", "-F", f"text=@{readme}"],
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout


def css(qa: Path) -> Path:
    path = qa / "cache" / "github-markdown.css"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(CSS_URL, path)
    return path


def page(html: str, base: Path, css_path: Path, column: int) -> str:
    html = re.sub(r'(src|srcset)="(assets/[^"]+)"', lambda m: f'{m.group(1)}="{(base / m.group(2)).resolve().as_uri()}"', html)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{css_path.resolve().as_uri()}">
<style>body{{margin:0;background:#fff}}@media (prefers-color-scheme: dark){{body{{background:#0d1117}}}}
.wrap{{width:{column}px;margin:0 auto;padding:24px 0}}.markdown-body{{box-sizing:content-box}}</style>
</head><body><div class="wrap"><article class="markdown-body">{html}</article></div></body></html>"""


def readme_shots(pw, base: Path, out: Path, login: str, wait: float) -> None:
    html = render_html(base / "README.md", login)
    b = pw.chromium.launch()
    brm = pw.chromium.launch(channel="chromium", args=["--force-prefers-reduced-motion"])
    for name, (vw, col, dpr) in VIEWPORTS.items():
        f = out / f"preview-{name}.html"
        f.write_text(page(html, base, css(ROOT / "qa"), col), encoding="utf-8")
        for scheme in ("dark", "light"):
            for motion, browser in (("", b), ("-static", brm)):
                ctx = browser.new_context(viewport={"width": vw, "height": 900}, device_scale_factor=dpr, color_scheme=scheme,
                                          reduced_motion="no-preference" if not motion else "null")
                pg = ctx.new_page()
                pg.goto(f.as_uri())
                pg.wait_for_load_state("networkidle")
                # size the viewport to the page first: resizing during capture restarts SVG timelines
                pg.set_viewport_size({"width": vw, "height": pg.evaluate("document.documentElement.scrollHeight")})
                pg.wait_for_timeout(wait * 1000 if not motion else 300)
                pg.screenshot(path=str(out / f"readme-{scheme}-{name}{motion}.png"))
                ctx.close()
    b.close()
    brm.close()


def frames(pw, base: Path, out: Path) -> list[str]:
    """Each SVG on its own page (batches of 6), so a screenshot never delays the others by much.
    Frames are labelled with the measured time since that image finished loading."""
    import json
    from PIL import Image
    fdir = out / "frames"
    fdir.mkdir(parents=True, exist_ok=True)
    svgs = sorted((base / "assets").rglob("*.svg"))
    stem = lambda s: s.relative_to(base / "assets").as_posix().replace("/", "__")[:-4]  # noqa: E731
    times: dict[str, dict[str, float]] = {}
    b = pw.chromium.launch()
    for i in range(0, len(svgs), 6):
        batch = svgs[i:i + 6]
        pages = []
        for s in batch:
            scheme = "dark" if s.stem.endswith("dark") else "light"
            f = out / f"_frame-{stem(s)}.html"
            f.write_text(f'<body style="margin:0;padding:8px;background:{BG[scheme]};display:inline-block">'
                         f'<img id="i" src="{s.as_uri()}"></body>', encoding="utf-8")
            ctx = b.new_context(viewport={"width": 880, "height": 1400}, device_scale_factor=2)
            pg = ctx.new_page()
            pages.append((s, ctx, pg, f))
        for s, ctx, pg, f in pages:
            pg.goto(f.as_uri())
        starts = {}
        for s, ctx, pg, f in pages:
            pg.wait_for_function("document.getElementById('i').complete")
            starts[s] = pg.evaluate("performance.now()")
        for t in TIMES:
            for s, ctx, pg, f in pages:
                while pg.evaluate("performance.now()") - starts[s] < t * 1000:
                    pg.wait_for_timeout(15)
                real = (pg.evaluate("performance.now()") - starts[s]) / 1000
                pg.locator("#i").screenshot(path=str(fdir / f"{stem(s)}-t{t}.png"))
                times.setdefault(stem(s), {})[f"t{t}"] = round(real, 2)
        for s, ctx, pg, f in pages:
            ctx.close()
    b.close()
    # reduced motion: real browser-level preference (CDP emulation does not reach <img> SVGs)
    brm = pw.chromium.launch(channel="chromium", args=["--force-prefers-reduced-motion"])
    ctx = brm.new_context(viewport={"width": 880, "height": 1400}, device_scale_factor=2, reduced_motion="null")
    pg = ctx.new_page()
    for s in svgs:
        pg.goto((out / f"_frame-{stem(s)}.html").as_uri())
        pg.wait_for_function("document.getElementById('i').complete")
        pg.wait_for_timeout(150)
        pg.locator("#i").screenshot(path=str(fdir / f"{stem(s)}-static.png"))
    brm.close()
    (out / "frame-times.json").write_text(json.dumps(times, indent=1), encoding="utf-8")
    return sorted(stem(s) for s in svgs)


def sheets(out: Path, stems: list[str]) -> None:
    import json
    from PIL import Image, ImageDraw
    fdir = out / "frames"
    times = json.loads((out / "frame-times.json").read_text(encoding="utf-8"))
    cols = [f"t{t}" for t in TIMES] + ["static"]
    for stem in stems:
        ims = [Image.open(fdir / f"{stem}-{c}.png").convert("RGB") for c in cols]
        w, h = ims[0].size
        s = Image.new("RGB", (len(cols) * (w + 10) + 10, h + 40), (100, 100, 100))
        d = ImageDraw.Draw(s)
        for i, (c, im) in enumerate(zip(cols, ims)):
            label = "reduced motion" if c == "static" else f"{c[1:]}s (measured {times[stem][c]:.2f}s)"
            d.text((10 + i * (w + 10), 8), label, fill=(255, 255, 255))
            s.paste(im, (10 + i * (w + 10), 30))
        s.save(out / f"sheet-{stem}.png")


def engines(pw, out: Path) -> None:
    f = out / "preview-1280.html"
    for eng in ("firefox", "webkit"):
        b = getattr(pw, eng).launch()
        for scheme in ("dark", "light"):
            pg = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
            pg.goto(f.as_uri())
            pg.set_viewport_size({"width": 1280, "height": pg.evaluate("document.documentElement.scrollHeight")})
            pg.wait_for_timeout(8000)
            pg.screenshot(path=str(out / f"engine-{eng}-{scheme}-1280.png"))
            pg.close()
        b.close()


def cpu(pw, url: str, label: str, seconds: float = 10) -> str:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg)
    cdp.send("Performance.enable")
    pg.goto(url, wait_until="load")
    pg.wait_for_timeout(4000)
    m0 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    steps = int(seconds * 2)
    for i in range(steps):  # scroll down, then back up, while measuring
        pg.mouse.wheel(0, 160 if i < steps / 2 else -160)
        pg.wait_for_timeout(500)
    m1 = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    b.close()
    wall = m1["Timestamp"] - m0["Timestamp"]
    busy = m1["TaskDuration"] - m0["TaskDuration"]
    return (f"{label}: main thread busy {100 * busy / wall:.1f}% while scrolling for {wall:.0f}s "
            f"(layout {1000 * (m1['LayoutDuration'] - m0['LayoutDuration']):.0f} ms, "
            f"style {1000 * (m1['RecalcStyleDuration'] - m0['RecalcStyleDuration']):.0f} ms)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=ROOT)
    ap.add_argument("--login", default="hunainx")
    ap.add_argument("--wait", type=float, default=10.0)
    ap.add_argument("--only", choices=("readme", "frames", "engines", "cpu"))
    ap.add_argument("--url", help="page to measure with --only cpu (default: the local 1280 preview)")
    args = ap.parse_args()
    base = args.dir.resolve()
    out = ROOT / "qa" / ("shots" if base == ROOT else f"shots-{base.name}")
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        if args.only in (None, "readme"):
            readme_shots(pw, base, out, args.login, args.wait)
        if args.only in (None, "frames"):
            sheets(out, frames(pw, base, out))
        if args.only in (None, "engines"):
            engines(pw, out)
        if args.only in (None, "cpu"):
            print(cpu(pw, args.url or (out / "preview-1280.html").as_uri(), args.url or "local preview"))
    print(f"preview: output in {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
