# Maintaining this profile

Everything visible on github.com/hunainx is generated from two files you edit by hand.

## Edit content

1. Edit **`data/profile.yml`**: name, role (the hero subtitle), tagline, depth (the small
   technical line under the tagline), about, current (the muted line under About), now, method,
   principles, proof, stack, focus, links, featured repos, repo blurbs.
2. Edit **`data/projects.yml`**: one block per "In motion" card, in the same order as `now`. It
   holds the type tag, an optional summary override, stack chips, status, `confidential`, the
   link and the card's drawing (`glyph`). Each card's name and description come from its `now`
   line, split at the first ":" or " — ".
3. Commit and push to `main`. The **refresh** workflow rebuilds every SVG and the README, then
   commits the result, usually within a minute.

Empty fields are left out of the page. Nothing gets invented to fill a gap: an empty `status`
means no status tag at all. `status: "Concept"` is drawn as an open ring, never as a live light.

Prose you write in `README.md` **outside** the `<!-- START:x -->` / `<!-- END:x -->` markers is
never touched. Anything **inside** the markers is regenerated on every build.

## Sections

| Section | Shows when | Built by |
|---|---|---|
| Hero (name, role, tagline, depth line, pipeline, AI toolkit, ticker) | always | `components/hero.py` |
| About + `current` line | `about` / `current` is filled | Markdown |
| Link chips | at least one `links:` field is filled | `components/misc.py` |
| In motion | `now` has items | `components/cards.py` |
| Selected work | at least 1 public, non-fork, non-archived repo other than `hunainx` | `components/work.py` |
| Stack & range | `stack` has tools (`focus` feeds its right-hand side) | `components/stack.py` |
| Shipping signal | the contributions count meets its threshold (`config.yml` → `signal`); other counts show only at their own thresholds | `components/signal.py` |
| How I work (+ principles, proof line) | `method` or `principles` is filled | `components/method.py` + Markdown |
| Footer | always | `components/misc.py` |

The hero pipeline is CHALLENGE → SPEC → ARCHITECT → BUILD → AUDIT → SHIP, with audit findings
looping back into BUILD. The AI toolkit (the `stack` category named in `config.yml` →
`hero.agents_category`) is listed top-right and feeds BUILD through faint signal lines; it is not
a stage.

Each section has a terminal-style label (`~/hunainx $ ./in-motion`) above a native `##`
heading. The label commands and headings live in `config.yml` under `sections`.

## Automation

`.github/workflows/refresh.yml` runs in three situations:
- daily at 21:23 UTC
- on manual dispatch (Actions → refresh → Run workflow)
- on pushes that change `data/profile.yml`, `data/projects.yml`, `data/config.yml`, `templates/`
  or `scripts/`

It runs fetch → build → check and commits **only if something changed**.

- **Shipping signal data.** Without a token, the counts are public data only. With an optional
  fine-grained, read-only token for your account saved as the repo secret `PROFILE_READ_TOKEN`
  (and `show_private_contribution_count: true`), the counts include private work. Only counts are
  kept, never repository names. `data/github.json` → `signal.sources` records where each number
  came from; a number that can't be established is left out, never estimated.
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
- **Copy:** your profile.yml and projects.yml text appears verbatim (hero, depth line, about,
  `current`, every card's name/description/type/status/confidential/link, method, proof, the
  5 stack categories and 7 focus domains), and no placeholder text appears anywhere.
- **Forbidden text:** rendered output (README text, `<img>` alt text, every SVG `<title>`, `<desc>`
  and `<text>`) must not contain "private", "doing the building" or "carry the implementation".
- **Bounds:** every SVG `<text>` run, measured with the committed fonts, sits inside its viewBox.
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
