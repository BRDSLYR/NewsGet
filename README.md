# NewsGet

A GitHub Actions pipeline that fetches Indian publications automatically and serves them as EPUB files via GitHub Pages — ready to download and read on any device.

---

## Publications

| Publication | Frequency | Updated |
|---|---|---|
| The Hindu — Delhi Edition | Daily | Every morning at 07:00 IST |
| Frontline Magazine | Fortnightly | Checked on the 1st and 15th of each month |

Both EPUBs replicate the corresponding Calibre recipes — cover image, article images, section structure — without requiring Calibre to be installed anywhere.

---

## Live site

| Page | URL |
|---|---|
| Home | `https://BRDSLYR.github.io/NewsGet/` |
| The Hindu — Delhi | `https://BRDSLYR.github.io/NewsGet/hindu-delhi/` |
| Frontline Magazine | `https://BRDSLYR.github.io/NewsGet/frontline/` |
| The Hindu latest (permalink) | `https://BRDSLYR.github.io/NewsGet/hindu-delhi/hindu-delhi-latest.epub` |
| Frontline latest (permalink) | `https://BRDSLYR.github.io/NewsGet/frontline/frontline-latest.epub` |

---

## EPUB structure

Every EPUB — regardless of publication — contains:

- **Cover** — the issue or edition cover image
- **Section Index** — one-tap navigation to any section
- **Article Index** — every article listed with a two-sentence teaser preview, linked directly
- **Articles** — full text with embedded images; each article has a *Back to Index* link that returns to its exact entry in the Article Index

---

## Repo structure

```
.github/
  workflows/
    hindu-delhi.yml         # Daily workflow — runs at 01:30 UTC (07:00 IST)
    frontline.yml           # Fortnightly workflow — runs at 01:30 UTC on 1st and 15th
scripts/
  fetch_hindu.py            # Scraper for The Hindu Delhi print edition
  hindu-delhi-index.html    # Download page template for The Hindu
  fetch_frontline.py        # Scraper for Frontline Magazine
  frontline-index.html      # Download page template for Frontline
index.html                  # Root GitHub Pages home page (on gh-pages branch)
README.md
```

---

## How it works

### The Hindu (`hindu-delhi.yml` + `fetch_hindu.py`)

Runs daily at 01:30 UTC:

```
Install deps → Run fetch_hindu.py → Copy to latest → Stamp date into HTML → Deploy to gh-pages/hindu-delhi/
```

- Fetches `https://www.thehindu.com/todays-paper/YYYY-MM-DD/th_delhi/`
- Extracts the `grouped_articles` JSON embedded in the page's `<script>` tag
- Downloads each article, stripping navigation/share elements, keeping only `.article-section`
- Downloads and embeds all article images as local EPUB items
- Downloads and embeds the front-page cover image

### Frontline (`frontline.yml` + `fetch_frontline.py`)

Runs at 01:30 UTC on the 1st and 15th of each month:

```
Install deps → Run fetch_frontline.py → Stamp date into HTML → Deploy to gh-pages/frontline/
```

- Fetches `https://frontline.thehindu.com/current-issue/`
- Parses the `div.current-issue-in-this-issue` article listing directly from HTML (no embedded JSON)
- Handles Frontline's lazy-load image pattern: 1×1 spacer PNGs are replaced with the real image from the preceding `<source srcset>` tag, upgraded from `_320` to `_1200` resolution
- Downloads and embeds the magazine cover

### Download pages

Both download page templates live in `scripts/` on the `main` branch. Each workflow stamps the current date into `{{LAST_UPDATED}}` using a single `sed` substitution before deploying — no JavaScript or external API calls needed. The `download=` attribute on each button uses the same substitution to name the saved file correctly.

---

## Reading on iPhone

1. Open the relevant download page in Safari
2. Tap **Download Today's Edition** / **Download Latest Issue**
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

**The Hindu:**
```bash
python scripts/fetch_hindu.py delhi output/hindu-delhi-today.epub
```

To fetch a past edition:
```python
from datetime import date
feeds, today_str, cover_url = fetch_article_list('delhi', date(2026, 6, 15))
```

**Frontline:**
```bash
# Current issue
python scripts/fetch_frontline.py "" output/frontline-latest.epub

# Specific issue (Volume-Issue format)
python scripts/fetch_frontline.py "41-12" output/frontline-41-12.epub
```

---

## Adding more Hindu editions

The Hindu scraper supports all print editions. To add one, duplicate `hindu-delhi.yml` and change the edition name:

```yaml
python scripts/fetch_hindu.py chennai "output/hindu-chennai-${TODAY}.epub"
```

Available editions: `bengaluru`, `chennai`, `coimbatore`, `delhi`, `erode`, `hyderabad`, `international`, `kochi`, `kolkata`, `kozhikode`, `madurai`, `mangalore`, `mumbai`, `thiruvananthapuram`, `tiruchirapalli`, `vijayawada`, `visakhapatnam`

---

## Notes

- The Hindu EPUBs are typically **20–60 MB** depending on images in that day's edition
- Frontline EPUBs are typically **10–30 MB** per issue
- Past editions accumulate on `gh-pages` and are never deleted (`clean: false`)
- The Hindu workflow will raise a clear error if no edition is published that day (e.g. public holidays)
- Frontline's exact publication date varies slightly — if a new issue has not appeared on the 1st or 15th, the previous issue remains available until the next check
