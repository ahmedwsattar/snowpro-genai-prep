# SnowPro Specialty: Gen AI (GES-C02) — Prep Hub

A self-contained study site for the **SnowPro Specialty: Gen AI (GES-C02)** exam.
Every page is a single HTML file with inline CSS/JS — no build step, no network
calls, no external libraries — so it runs anywhere, including GitHub Pages.

## Live site

Once GitHub Pages is enabled (see below), the hub is served from **`index.html`**.

## Pages

| File | What it is |
|------|------------|
| `index.html` | Landing page / hub linking everything below |
| `study-guide.html` | All four domains in one scrollable guide (built from the `.md` notes) |
| `quiz.html` | 34 self-graded scenario questions |
| `exam-hard.html` | 34 tougher, nuance-driven questions |
| `exam-targeted.html` | 75 questions organized by exam subtopic (filterable) |
| `exam-hardest.html` | 24 brutal exam-edge questions on the classic traps |
| `mock-exam.html` | 65-question full mock, sampled at real domain weights (18/38/29/15%) |

## Enable GitHub Pages

1. Push this repo to GitHub (see below).
2. In the repo, go to **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **Deploy from a branch**.
4. Select branch **`main`** and folder **`/ (root)`**, then **Save**.
5. Your site publishes at `https://<username>.github.io/<repo>/`.

## Rebuilding the generated pages

The quiz/drill pages are hand-maintained; two pages and one bundle are generated
from the Markdown notes and question pools:

```bash
python3 build_study_guide.py   # -> study-guide.html
python3 build_mock_exam.py     # -> mock-exam.html (samples the question pools)
python3 build_hardest.py       # -> exam-hardest.html (clones the drill engine)
```

Requires `python3` and the `markdown` package (`pip install markdown`).

## Not in this repo

Private/copyrighted study materials (exam PDFs, the PPTX deck, and the `Lab/`
training folder) are excluded via `.gitignore` and are **not** published.
