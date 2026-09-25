# Maintaining this profile

Everything visible on github.com/hunainx is generated from two files you edit by hand.

## Edit content

1. Edit **`data/profile.yml`**: name, role (the hero subtitle), tagline, focus, about, now,
   stack, links, principles, featured repos, repo blurbs.
2. Edit **`data/projects.yml`**: one block per "Currently building" card, in the same order as
   `now`. It holds the codename, summary, stack chips, status, the `PRIVATE` tag and the card's
   drawing (`glyph`).
3. Commit and push to `main`. The **refresh** workflow rebuilds every SVG and the README, then
   commits the result, usually within a minute.

Empty fields are left out of the page. Nothing gets invented to fill a gap: an empty `status`
means no status tag at all.

Prose you write in `README.md` **outside** the `<!-- START:x -->` / `<!-- END:x -->` markers is
never touched. Anything **inside** the markers is regenerated on every build.

## Sections

| Section | Shows when | Built by |
|---|---|---|
| Hero (name, role, tagline, pipeline, agents, ticker) | always | `components/hero.py` |
| About | `about` is filled | Markdown |
| Link chips | at least one `links:` field is filled | `components/misc.py` |
| Currently building | `now` has items | `components/building.py` |
| Selected work | at least 1 public, non-fork, non-archived repo other than `hunainx` | `components/work.py` |
| Stack | `stack` has tools (`focus` feeds its right-hand side) | `components/stack.py` |
| Activity: "building in private" radar | fewer than 10 public contributions in 12 months | `components/activity.py` |
| Activity: heatmap + stats + languages | 10 or more (thresholds in `config.yml`) | `components/activity.py` |
| How I work | `principles` is filled | Markdown ordered list |
| Footer | always | `components/misc.py` |

Each section has a terminal-style label (`~/hunainx $ ./building --now`) above a native `##`
heading. The label commands and headings live in `config.yml` under `sections`.

## Automation

`.github/workflows/refresh.yml` runs in three situations:
- daily at 21:23 UTC
- on manual dispatch (Actions → refresh → Run workflow)
- on pushes that change `data/profile.yml`, `data/projects.yml`, `data/config.yml`, `templates/`
  or `scripts/`

It runs fetch → build → check and commits **only if something changed**.

- **Private contribution count (optional).** Create a fine-grained, read-only token for your
  account and save it as the repo secret `PROFILE_READ_TOKEN`. Only the count is used.
- **Scheduled runs pause after 60 days without repo activity.** The contribution window moves
  daily, so the workflow normally commits often enough to stay alive. If it ever gets disabled,
  re-enable it from the Actions tab.
- Actions are pinned to commit SHAs. When updating one, change the SHA and the `# vX` comment together.

## Run it locally

```bash
pip install -r requirements.txt
python -m playwright install chromium firefox webkit   # preview only
python scripts/fetch.py     # GitHub API → data/github.json
python scripts/build.py     # → assets/ + README regions
python scripts/check.py     # quality gates; must print "check: OK"
python scripts/preview.py   # sanitizer render, screenshots at 1280/1100/390, frames, engines, CPU → qa/
```

To see the hidden sections, build the fixture in `qa/fixture/data/`:

```bash
python scripts/build.py --data qa/fixture/data/github.json --profile qa/fixture/data/profile.yml --projects qa/fixture/data/projects.yml --out qa/fixture
```

Then run `check.py --dir qa/fixture` and `preview.py --dir qa/fixture`.

## How the SVGs are built

- **Text** is outlined from the committed OFL fonts (Inter Display, JetBrains Mono), so it looks
  the same on every OS. Each glyph is defined once per file and scaled per text run. Body copy
  (card summaries, stack tools, captions) is real `<text>` in the system sans stack; wrapping is
  measured with Inter, which is wider, so lines never overflow.
- **Motion** is CSS only: transform, opacity, stroke-dashoffset and offset-path. There is no SMIL,
  so `prefers-reduced-motion` stops everything, and every SVG looks complete when motion is off.
  Inside `<clipPath>` or `<mask>`, always use a px `transform-origin`, because Firefox doesn't draw
  `fill-box` there.
- **Tiers.** Each full-width component has three widths:
  - **840px**: viewports ≥ 1260px
  - **600px**: 1012–1259px
  - **360px**: below 1012px (GitHub's README column is 308–685px there)

  Section labels and the footer are drawn at their natural width below 1260px, and work cards are
  410px, so none of them ever scale. Every tier keeps text at 11px or more.
- **Explicit-theme viewers.** GitHub's `<themed-picture>` script drops the width condition from
  each `<source>` when a signed-in viewer uses an explicit light or dark theme. Sources are
  listed widest first, so those viewers get the desktop art in the right theme.

## Quality gates (`check.py`)

- **Security:** XML, `<title>`, `<desc>` and `role="img"` are required. No scripts, event
  attributes, external references or SMIL.
- **Budgets:** each SVG ≤ 60 KB (hero ≤ 90 KB), all assets ≤ 700 KB, and ≤ 40 animated elements
  per SVG. Every animated SVG must carry the reduced-motion block.
- **Pairs and alt text:** every asset has its dark/light twin, and every image has alt text.
- **Contrast:** every text colour is ≥ 4.5:1.
- **Copy:** your profile.yml and projects.yml text appears verbatim, and no placeholder text appears
  anywhere.
- **Numbers:** every rendered number comes from `github.json`, your own copy, or a fixed display
  string in `config.yml`.

The worst case (every section unlocked, 4 public repos) is kept under the budget. Test it with the
fixture.

## Troubleshooting

- **`check: FAILED`** lists each violated rule. Fix the input; don't loosen the check.
- **The profile didn't update after a push.** Look at the Actions tab. GitHub caches images for
  about 5 minutes.
- **A number looks wrong.** Open `data/github.json`. It's exactly what the API returned.

## Not controlled by this repo

Bio, avatar, pins and the website field are set at github.com/settings/profile.
