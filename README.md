# NewsGet

A GitHub Actions pipeline that fetches Indian newspaper print editions daily and serves them as EPUB files via GitHub Pages — ready to download and read on any device.

---

## What it does

Every morning at **07:00 IST**, a GitHub Actions workflow:

1. Scrapes The Hindu's Delhi print edition from their website
2. Downloads all article text and images
3. Packages everything into a clean, structured EPUB
4. Publishes it to GitHub Pages for download

The EPUB replicates the Calibre `TheHindu` recipe — section structure, cover image, article images, and print page numbers — without requiring Calibre to be installed anywhere.

---

## Live site

| Page | URL |
|---|---|
| Home | `https://BRDSLYR.github.io/NewsGet/` |
| The Hindu — Delhi | `https://BRDSLYR.github.io/NewsGet/hindu-delhi/` |
| Latest EPUB (permalink) | `https://BRDSLYR.github.io/NewsGet/hindu-delhi/hindu-delhi-latest.epub` |

---

## EPUB structure

Each daily EPUB contains:

- **Cover** — the front page of that day's print edition
- **Section Index** — one-tap navigation to any section (Regional, Edit, Business, Foreign, Sports, Science)
- **Article Index** — every article listed with a two-sentence teaser preview, linked directly
- **Articles** — full text with embedded images; each article has a *Back to Index* link that returns to its exact entry in the Article Index

---

## Repo structure

```
.github/
  workflows/
    hindu-delhi.yml         # Daily workflow — runs at 01:30 UTC (07:00 IST)
scripts/
  fetch_hindu.py            # Scraper: fetches articles, embeds images, builds EPUB
  hindu-delhi-index.html    # Download page template ({{LAST_UPDATED}} stamped by workflow)
index.html                  # Root GitHub Pages home page (goes on gh-pages branch)
README.md
```

---

## How it works

### Workflow (`hindu-delhi.yml`)

Runs on a daily cron schedule and on manual trigger (`workflow_dispatch`):

```
Install Python deps → Run fetch_hindu.py → Copy to latest → Stamp date into HTML → Deploy to gh-pages
```

The workflow stamps today's date into the download page using a single `sed` substitution — no JavaScript or external API calls needed.

### Scraper (`fetch_hindu.py`)

- Fetches `https://www.thehindu.com/todays-paper/YYYY-MM-DD/th_delhi/`
- Extracts the `grouped_articles` JSON embedded in the page's `<script>` tag
- Downloads each article, stripping navigation/share elements and keeping only `.article-section`
- Downloads and embeds all article images as local EPUB items (so they display offline)
- Downloads and embeds the front-page cover image
- Builds a fully navigable EPUB with custom section and article indexes

### Download page (`hindu-delhi-index.html`)

A static template stored in `scripts/`. Each workflow run stamps the current date into `{{LAST_UPDATED}}` using `sed` before deploying, so the page always shows the date of the available edition and names the downloaded file `The Hindu - Delhi - D Mon YYYY.epub`.

---

## Reading on iPhone

1. Open `https://BRDSLYR.github.io/NewsGet/hindu-delhi/` in Safari
2. Tap **Download Today's Edition**
3. Tap **Share → Copy to Books** (or open in any EPUB reader)

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `requests` | latest | HTTP fetching |
| `beautifulsoup4` | latest | HTML parsing |
| `ebooklib` | `0.18` | EPUB generation (pinned — newer versions have a nav bug) |
| `lxml` | latest | XML parser backend for ebooklib |

Install locally:

```bash
pip install requests beautifulsoup4 "ebooklib==0.18" lxml
```

---

## Running locally

```bash
python scripts/fetch_hindu.py delhi output/hindu-delhi-today.epub
```

To fetch a past edition:

```python
# Edit fetch_article_list() — pass a target_date argument
from datetime import date
feeds, today_str, cover_url = fetch_article_list('delhi', date(2026, 6, 15))
```

---

## Adding more editions

The scraper supports all Hindu print editions. To add one, duplicate `hindu-delhi.yml` and change the edition name:

```yaml
python scripts/fetch_hindu.py chennai "output/hindu-chennai-${TODAY}.epub"
```

Available editions: `bengaluru`, `chennai`, `coimbatore`, `delhi`, `erode`, `hyderabad`, `international`, `kochi`, `kolkata`, `kozhikode`, `madurai`, `mangalore`, `mumbai`, `thiruvananthapuram`, `tiruchirapalli`, `vijayawada`, `visakhapatnam`

---

## Notes

- The EPUB file size is typically **20–60 MB** depending on the number of images in that day's edition
- Past editions accumulate on `gh-pages` under `hindu-delhi/` and are not deleted (`clean: false`)
- The workflow will fail gracefully with a clear error if The Hindu has not published an edition for that date (e.g. public holidays)
