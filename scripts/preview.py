"""Visual QA: render README.md through GitHub's real sanitizer and screenshot it.

  python scripts/preview.py            # README screenshots + motion frames → qa/
  python scripts/preview.py --dir qa/fixture   # preview another build output (e.g. a fixture)

Needs: gh (logged in), playwright (+ `python -m playwright install chromium`). qa/ is git-ignored.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CSS_URL = "https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown.css"
# Approximate width of GitHub's profile README column at each viewport (content box).
VIEWPORTS = {"1280": (1280, 900, 1), "390": (390, 844, 2)}
PAGE_BG = {"dark": "#0d1117", "light": "#ffffff"}


def render_html(readme: Path, login: str) -> str:
    return subprocess.run(
        ["gh", "api", "markdown", "-f", "mode=gfm", "-f", f"context={login}/{login}", "-F", f"text=@{readme}"],
        capture_output=True, text=True, encoding="utf-8", check=True).stdout


def css(qa: Path) -> Path:
    path = qa / "cache" / "github-markdown.css"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(CSS_URL, path)
    return path


def page(html: str, base: Path, css_path: Path) -> str:
    def local(m: re.Match) -> str:
        return f'{m.group(1)}="{(base / m.group(2)).resolve().as_uri()}"'
    html = re.sub(r'(src|srcset)="(assets/[^"]+)"', local, html)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{css_path.resolve().as_uri()}">
<style>
body{{margin:0;background:var(--bgColor-default,#fff)}}
@media (prefers-color-scheme: dark){{body{{background:#0d1117}}}}
.wrap{{max-width:896px;margin:0 auto;padding:24px 16px}}
.markdown-body{{border:1px solid rgba(128,128,128,.25);border-radius:6px;padding:24px}}
@media (max-width:767px){{.wrap{{padding:16px}} .markdown-body{{padding:16px}}}}
</style></head><body><div class="wrap"><article class="markdown-body">{html}</article></div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=ROOT)
    ap.add_argument("--login", default="hunainx")
    ap.add_argument("--wait", type=float, default=13.0, help="seconds to let one-shot motion finish")
    ap.add_argument("--only", choices=("readme", "motion"), help="run just one half")
    args = ap.parse_args()
    base = args.dir.resolve()
    qa = ROOT / "qa"
    out = qa / ("shots" if base == ROOT else f"shots-{base.name}")
    out.mkdir(parents=True, exist_ok=True)

    html_path = out / "preview.html"
    html_path.write_text(page(render_html(base / "README.md", args.login), base, css(qa)), encoding="utf-8")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # CDP media emulation does not reach SVGs loaded through <img>; a browser-level preference
        # (what a real OS setting becomes) does, so the static pass uses a separately flagged browser.
        browser_rm = pw.chromium.launch(channel="chromium", args=["--force-prefers-reduced-motion"])
        # Full README, both themes, both widths, after the one-shot animations have finished.
        for scheme in (("dark", "light") if args.only != "motion" else ()):
            for name, (w, h, dpr) in VIEWPORTS.items():
                for motion in ("no-preference", "reduce"):
                    host = browser if motion == "no-preference" else browser_rm
                    ctx = host.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr,
                                           color_scheme=scheme,
                                           reduced_motion="no-preference" if motion == "no-preference" else "null")
                    pg = ctx.new_page()
                    pg.goto(html_path.as_uri())
                    pg.wait_for_load_state("networkidle")
                    # Grow the viewport to the full page first: a resize during capture would restart SVG timelines.
                    pg.set_viewport_size({"width": w, "height": pg.evaluate("document.documentElement.scrollHeight")})
                    pg.wait_for_load_state("networkidle")
                    if motion == "no-preference":
                        pg.wait_for_timeout(args.wait * 1000)
                    suffix = "" if motion == "no-preference" else "-static"
                    pg.screenshot(path=str(out / f"readme-{scheme}-{name}{suffix}.png"))
                    ctx.close()

        # Motion frames of the animated panels: t=0, 1.5s, 6s.
        for stem in (("hero/hero", "panels/now") if args.only != "readme" else ()):
            for scheme in ("dark", "light"):
                svg = base / "assets" / f"{stem}-{scheme}.svg"
                if not svg.exists():
                    continue
                ctx = browser.new_context(viewport={"width": 880, "height": 300}, color_scheme=scheme)
                pg = ctx.new_page()
                frame = out / f"frame-{Path(stem).name}-{scheme}.html"
                frame.write_text(f'<body style="margin:20px;background:{PAGE_BG[scheme]}">'
                                 f'<img id="i" src="{svg.as_uri()}"></body>', encoding="utf-8")
                pg.goto(frame.as_uri())
                pg.wait_for_function("document.getElementById('i').complete")
                el = pg.locator("#i")
                last = 0.0
                for t in (0.0, 1.5, 6.0):
                    pg.wait_for_timeout((t - last) * 1000)
                    last = t
                    el.screenshot(path=str(out / f"motion-{Path(stem).name}-{scheme}-t{t:g}.png"))
                ctx.close()
        browser.close()
        browser_rm.close()
    print(f"preview: screenshots in {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
