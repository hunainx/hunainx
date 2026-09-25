# Maintaining this profile

Everything visible on github.com/hunainx is generated from one file you edit by hand.

## Edit content

1. Change **`data/profile.yml`**: name, tagline, focus, about, now, stack, links, principles,
   featured repos, repo blurbs.
2. Commit and push to `main`. The **refresh** workflow rebuilds the SVGs and README and commits
   the result (usually within a minute).

Empty fields are left out of the page. Nothing gets invented to fill a gap.

Prose you write in `README.md` **outside** the `<!-- START:x -->` / `<!-- END:x -->` markers is
never touched. Anything **inside** the markers is regenerated on every build.

## How sections appear

| Section | Shows when | Controlled by |
|---|---|---|
| Hero, footer | always | `profile.yml` |
| Now panel, intro, toolkit, how I work | the field has content | `profile.yml` |
| Link chips | at least one of `links:` is filled | `profile.yml` |
| Selected work | at least 1 public, non-fork, non-archived repo other than `hunainx` | GitHub data |
| Signal: stats | at least 1 such repo | `config.yml` → `thresholds` |
| Signal: activity | at least 10 public contributions in 12 months | `config.yml` → `thresholds` |
| Signal: languages | at least 1 such repo with language bytes | `config.yml` → `thresholds` |

Selected work auto-picks the most-starred, most-recent repos (up to 4). To choose them yourself,
list names in `featured_repos:`, and use `repo_blurbs: {repo-name: "One line."}` to override a
repo's GitHub description.

## Automation

`.github/workflows/refresh.yml` runs daily at 21:23 UTC, on manual dispatch (Actions → refresh →
Run workflow), and on pushes that change `data/profile.yml`, `data/config.yml`, `templates/` or
`scripts/`. It runs fetch → build → check and commits **only if something changed**.

- **Private contribution count (optional).** Create a fine-grained, read-only token for your
  account and save it as the repo secret `PROFILE_READ_TOKEN`. Only the count is used, never
  repo names. Without the secret, that tile is simply absent.
- **Scheduled runs pause after 60 days without repo activity.** The 52-week contribution window
  moves every week, so the workflow normally commits at least weekly, and that keeps the schedule
  alive. If it ever gets disabled, re-enable it from the Actions tab or run the workflow manually.
- Actions are pinned to commit SHAs. To update them, change the SHA and the `# vX` comment together.

## Run it locally

```bash
pip install -r requirements.txt
python -m playwright install chromium      # preview only
python scripts/fetch.py      # GitHub API → data/github.json (uses GITHUB_TOKEN or `gh auth token`)
python scripts/build.py      # → assets/ + README regions
python scripts/check.py      # quality gates; must print "check: OK"
python scripts/preview.py    # renders via GitHub's sanitizer → screenshots in qa/
```

To preview sections that are hidden today, write a fake `qa/fixture/data/github.json` and
`qa/fixture/data/profile.yml`, then run
`python scripts/build.py --data qa/fixture/data/github.json --profile qa/fixture/data/profile.yml --out qa/fixture`.
After that, run `check.py --dir qa/fixture` and `preview.py --dir qa/fixture`. The `qa/` folder is
git-ignored.

## Files

| Path | Role |
|---|---|
| `data/profile.yml` | Your content (the brief). |
| `data/config.yml` | Thresholds, breakpoint, colour tokens, accents, size budgets, fixed labels. |
| `data/github.json` | API snapshot. Every rendered number comes from here. `last_changed` moves only when the data moves. |
| `scripts/svgkit.py` | Font → SVG path conversion (fontTools, GPOS kerning), contrast maths. |
| `templates/svg/*.svg.tpl` | One template per asset type: CSS, motion, reduced-motion block. |
| `fonts/` | Inter Display SemiBold, Inter Regular, JetBrains Mono Medium, with OFL licences. |

## Design rules worth knowing

- **Accent:** set `accent:` in `profile.yml` to `ember`, `signal` or `ion`. Light-theme ember text
  uses `#AA5B1A`, because the spec's `#B5611C` is only 4.48:1 on white. `faint` is used for
  decoration only, never for text.
- **Narrow variants (`*-mobile-*.svg`, 360px wide).** These are used when the viewport is at most
  1011px. Below that width GitHub's README column is only 308–685px, so the 840px art would shrink
  its text under 11px.
- **Explicit-theme viewers.** When a signed-in viewer sets GitHub to an explicit light or dark theme,
  GitHub's `<themed-picture>` script rewrites each theme `<source>`'s `media` string and drops any width
  condition. Desktop sources are listed first, so those viewers see the desktop art in the correct
  theme. They don't see the mobile art on phones. Signed-out and "sync with system" viewers get
  both theme and width right.
- **Monogram letters** live in `LETTERS` in `scripts/build.py` (7×11 dot bitmaps). If your
  initials change, add the new letters there.

## Troubleshooting

- **`check: FAILED`** lists each violated rule. Fix the input; don't loosen the check.
- **Profile didn't update after a push.** Look at the Actions tab. Image changes can take about
  5 minutes to show, because of GitHub's image cache.
- **A number looks wrong.** Open `data/github.json`. That file is exactly what the API returned.

## Profile settings (not controlled by this repo)

Your bio, avatar, pins and website field are set at github.com/settings/profile.
