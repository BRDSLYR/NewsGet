#!/usr/bin/env python3
"""
Standalone script replicating the Calibre Frontline recipe.
Fetches the current or specified issue of Frontline magazine and outputs an EPUB.
Usage: python fetch_frontline.py [issue] [output_path]
  issue: optional, Volume-Issue format e.g. "41-12" (defaults to current issue)
"""
import re
import sys
import html
from datetime import date, datetime
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from ebooklib import epub


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/145.0.0.0 Safari/537.36'
    )
}

BASE_URL = 'https://frontline.thehindu.com'

CSS = '''
    body { font-family: Georgia, serif; margin: 1em 2em; }
    h1 { font-size: 1.4em; }
    .caption, figcaption { font-size: small; text-align: center; color: #555; }
    .environment, .publish-time, .author { font-size: small; color: #404040; }
    .subhead, .bold { font-weight: bold; }
    .question { font-weight: bold; }
    img { display: block; margin: 0 auto; max-width: 100%; }
    .italic { font-style: italic; color: #202020; }
'''


def absurl(url):
    if url.startswith('/'):
        return BASE_URL + url
    return url


def sanitize(content):
    """Strip control characters and ensure content is non-empty valid text."""
    if not content:
        return '<p><em>Content not available.</em></p>'
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
    return content or '<p><em>Content not available.</em></p>'


def make_xhtml(title, description, body, chapter_file):
    """Wrap content in a minimal valid XHTML document for ebooklib."""
    anchor = chapter_file.replace('.xhtml', '')
    return (
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        '<head>'
        f'<title>{html.escape(title)}</title>'
        '<link rel="stylesheet" href="../style/main.css" type="text/css"/>'
        '</head>'
        '<body>'
        f'<h1>{html.escape(title)}</h1>'
        + (f'<p class="author">{html.escape(description)}</p>' if description else '')
        + '<hr/>'
        f'{body}'
        '<hr/>'
        '<p style="text-align:center;font-size:small;">'
        f'<a href="../article_index.xhtml#{anchor}">&#8592; Back to Index</a>'
        '</p>'
        '</body>'
        '</html>'
    )


def make_section_index_xhtml(feeds, issue_label):
    """Page 1 — high-level section index linking to anchors in the article index."""
    section_links = ''
    for section in feeds.keys():
        anchor = re.sub(r'\s+', '_', section)
        section_links += (
            f'<li><a href="article_index.xhtml#{html.escape(anchor)}">'
            f'{html.escape(section)}</a></li>'
        )
    return (
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        '<head>'
        f'<title>Sections — Frontline, {html.escape(issue_label)}</title>'
        '<link rel="stylesheet" href="../style/main.css" type="text/css"/>'
        '<style>'
        'ul{list-style:none;padding:0;margin:0.5em 0;}'
        'li{margin:0.6em 0;}'
        'li a{text-decoration:none;color:#1a0dab;font-size:1.1em;}'
        '</style>'
        '</head>'
        '<body>'
        f'<h1>Frontline — {html.escape(issue_label)}</h1>'
        '<hr/>'
        '<ul>'
        f'{section_links}'
        '</ul>'
        '</body>'
        '</html>'
    )


def make_index_xhtml(feeds, issue_label, chapter_map):
    """Page 2 — granular article index with anchored section headings and teaser previews."""
    sections_html = ''
    for section, articles in feeds.items():
        section_anchor = re.sub(r'\s+', '_', section)
        previews = ''
        for article in articles:
            fname = chapter_map[article['url']]
            article_anchor = fname.replace('.xhtml', '')
            teaser = article.get('description', '').strip()
            sentences = re.split(r'(?<=[.!?])\s+', teaser)
            preview_text = ' '.join(sentences[:2])
            previews += (
                f'<li id="{article_anchor}">'
                f'<a href="{html.escape(fname)}">{html.escape(article["title"])}</a>'
                + (f'<br/><span style="font-size:small;color:#444;">{html.escape(preview_text)}</span>' if preview_text else '')
                + '</li>'
            )
        sections_html += (
            f'<h2 id="{html.escape(section_anchor)}">{html.escape(section)}</h2>'
            f'<ul>{previews}</ul>'
        )
    return (
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        '<head>'
        f'<title>Index — Frontline, {html.escape(issue_label)}</title>'
        '<link rel="stylesheet" href="../style/main.css" type="text/css"/>'
        '<style>'
        'h2{font-size:1.1em;margin-top:1.2em;border-bottom:1px solid #ccc;padding-bottom:0.2em;}'
        'ul{list-style:none;padding:0;margin:0.3em 0;}'
        'li{margin:0.4em 0;}'
        'li a{text-decoration:none;color:#1a0dab;}'
        '</style>'
        '</head>'
        '<body>'
        f'<h1>Frontline — {html.escape(issue_label)}</h1>'
        '<p style="font-size:small;"><a href="section_index.xhtml">&#8592; Back to Sections</a></p>'
        '<hr/>'
        f'{sections_html}'
        '</body>'
        '</html>'
    )


def fetch_article_list(issue=None):
    """
    Fetch the Frontline issue index.
    issue: None = current issue; or Volume-Issue string e.g. "41-12"
    Returns (feeds dict, issue_label str, cover_url str or None)
    """
    if issue:
        url = f'{BASE_URL}/magazine/issue/vol{issue}/'
    else:
        url = f'{BASE_URL}/current-issue/'

    print(f'Fetching index: {url}')
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Cover image — mirrors: cover.find(class_='sptar-image').img['data-original']
    cover_url = None
    issue_label = issue or date.today().strftime('%-d %b %Y')

    magazine_div = soup.find('div', attrs={'class': 'magazine'})
    if magazine_div:
        cover_img = magazine_div.find('img', attrs={'data-original': True})
        if cover_img:
            src = cover_img['data-original'].replace('SQUARE_80', 'FREE_615')
            cover_url = absurl(src)
            print(f'Cover image: {cover_url}')
        # Extract issue label from sub-text (e.g. "Volume 42, Issue 13 | June 20, 2025")
        sub_text = magazine_div.find(class_='sub-text')
        if sub_text:
            issue_label = sub_text.get_text(strip=True)
            print(f'Issue: {issue_label}')
    else:
        print('Magazine div not found — trying alternate cover selector.')

    if not cover_url:
        print('Cover image not found on index page.')

    # Article listing — mirrors: mag.findAll('div', attrs={'class':'content'})
    feeds = defaultdict(list)
    listing = soup.find(class_='current-issue-in-this-issue')
    if not listing:
        raise ValueError('Could not find article listing — Frontline page structure may have changed.')

    for div in listing.find_all('div', attrs={'class': 'content'}):
        title_el = div.find(class_='title')
        if not title_el:
            continue
        a = title_el.find('a')
        if not a:
            continue
        url = absurl(a.get('href', ''))
        title = a.get_text(strip=True)
        if not url or not title:
            continue

        # Section label
        section = 'Articles'
        cat = div.find(class_='label')
        if cat:
            section = cat.get_text(strip=True)

        # Description: author + sub-text (teaser)
        description = ''
        auth = div.find(class_='author')
        sub = div.find(class_='sub-text')
        if auth:
            description = auth.get_text(strip=True)
        if sub:
            sub_text_str = sub.get_text(strip=True)
            description = f'{description} | {sub_text_str}' if description else sub_text_str

        feeds[section].append({
            'title':       title,
            'url':         url,
            'description': description,
        })

    total = sum(len(v) for v in feeds.values())
    print(f'Found {total} articles across {len(feeds)} sections')

    if not total:
        raise ValueError('No articles found — Frontline page structure may have changed.')

    return dict(feeds), issue_label, cover_url


def fetch_cover(cover_url):
    """Download the cover image, return (bytes, media_type, ext) or (None, None, None)."""
    try:
        resp = requests.get(cover_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', 'image/jpeg').split(';')[0].strip()
        if content_type not in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'):
            content_type = 'image/jpeg'
        ext = content_type.split('/')[-1].replace('jpeg', 'jpg')
        return resp.content, content_type, ext
    except Exception as e:
        print(f'Warning: could not download cover image: {e}')
        return None, None, None


def fetch_and_embed_images(article, book, chapter_id):
    """Download every image in the article and embed it into the EPUB."""
    img_counter = 0
    for img in article.find_all('img'):
        src = img.get('data-original') or img.get('src') or ''
        if not src:
            img.decompose()
            continue
        # Handle the spacer pattern from the Calibre recipe:
        # if data-original ends with 1x1_spacer.png, use the preceding <source srcset> instead
        if src.endswith('1x1_spacer.png'):
            source = img.find_previous('source', srcset=True)
            img.decompose()
            if source:
                src = absurl(source.get('srcset', '').replace('_320', '_1200'))
                source.decompose()
            else:
                continue
        else:
            src = absurl(src)

        if 'placeholder' in src or 'spacer' in src or src.endswith('.gif'):
            continue

        try:
            resp = requests.get(src, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get('Content-Type', 'image/jpeg').split(';')[0].strip()
            if content_type not in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'):
                content_type = 'image/jpeg'
            ext = content_type.split('/')[-1].replace('jpeg', 'jpg')
            img_counter += 1
            img_filename = f'images/ch{chapter_id:04d}_{img_counter:03d}.{ext}'
            img_item = epub.EpubItem(
                uid=f'img-{chapter_id}-{img_counter}',
                file_name=img_filename,
                media_type=content_type,
                content=resp.content,
            )
            book.add_item(img_item)
            img['src'] = f'../{img_filename}'
            for attr in ['data-original', 'data-src', 'srcset', 'height', 'width']:
                if img.has_attr(attr):
                    del img[attr]
        except Exception as e:
            print(f'    Warning: could not embed image {src}: {e}')
            img.decompose()

    # Remove any leftover <source> tags (postprocess_html mirror)
    for source in article.find_all('source'):
        source.decompose()


def fetch_article_content(url, book, chapter_id):
    """Fetch a single article and return sanitized XHTML body content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # keep_only_tags: div.container.article-section
        article = soup.find('div', class_=lambda c: c and 'article-section' in c.split())
        if not article:
            # Fallback: any element with class article-section
            article = soup.find(class_='article-section')
        if not article:
            return '<p><em>Content not available.</em></p>'

        # remove_tags mirror
        for cls in [
            'breadcrumb', 'comments-shares', 'share-page', 'article-video',
            'referpara', 'slide-mobile', 'title-patch', 'hide-mobile', 'related-stories'
        ]:
            for el in article.find_all(class_=cls):
                el.decompose()

        # preprocess_html mirror: caption → figcaption
        for cap in article.find_all(class_='caption'):
            cap.name = 'figcaption'

        # Embed images (handles spacer pattern internally)
        fetch_and_embed_images(article, book, chapter_id)

        return sanitize(article.decode_contents())

    except Exception as e:
        return f'<p><em>Failed to fetch article: {html.escape(str(e))}</em></p>'


def build_epub(feeds, issue_label, cover_url):
    book = epub.EpubBook()
    # Use a filesystem-safe slug from the issue label for the identifier
    slug = re.sub(r'[^\w-]', '_', issue_label)[:60]
    book.set_identifier(f'frontline-{slug}')
    book.set_title(f'Frontline — {issue_label}')
    book.set_language('en')
    book.add_author('Frontline / The Hindu Group')

    # Cover
    if cover_url:
        cover_bytes, media_type, ext = fetch_cover(cover_url)
        if cover_bytes:
            book.set_cover(f'cover.{ext}', cover_bytes)
            print(f'Cover set ({media_type}, {len(cover_bytes):,} bytes)')
        else:
            print('Warning: cover download failed.')
    else:
        print('Warning: no cover URL — EPUB will have no cover.')

    style = epub.EpubItem(
        uid='main-css',
        file_name='style/main.css',
        media_type='text/css',
        content=CSS,
    )
    book.add_item(style)

    # First pass: assign filenames so indexes can link before articles are fetched
    chapter_map = {}
    chapter_id = 0
    for section, articles in feeds.items():
        for article in articles:
            chapter_id += 1
            chapter_map[article['url']] = f'ch_{chapter_id:04d}.xhtml'

    # Page 1 — section index
    section_index_page = epub.EpubHtml(
        title='Sections',
        file_name='section_index.xhtml',
        lang='en',
    )
    section_index_page.content = make_section_index_xhtml(feeds, issue_label)
    section_index_page.add_item(style)
    book.add_item(section_index_page)

    # Page 2 — granular article index
    article_index_page = epub.EpubHtml(
        title='Index',
        file_name='article_index.xhtml',
        lang='en',
    )
    article_index_page.content = make_index_xhtml(feeds, issue_label, chapter_map)
    article_index_page.add_item(style)
    book.add_item(article_index_page)

    spine = [section_index_page, article_index_page]
    toc = []
    chapter_id = 0

    for section, articles in feeds.items():
        section_chapters = []
        for article in articles:
            chapter_id += 1
            print(f'  [{section}] {article["title"]}')
            body = fetch_article_content(article['url'], book, chapter_id)

            ch = epub.EpubHtml(
                title=article['title'],
                file_name=f'ch_{chapter_id:04d}.xhtml',
                lang='en',
            )
            ch.content = make_xhtml(
                article['title'],
                article.get('description', ''),
                body,
                f'ch_{chapter_id:04d}.xhtml',
            )
            ch.add_item(style)
            book.add_item(ch)
            section_chapters.append(ch)
            spine.append(ch)

        toc.append((epub.Section(section), section_chapters))

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    return book


if __name__ == '__main__':
    issue      = sys.argv[1] if len(sys.argv) > 1 else None
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    feeds, issue_label, cover_url = fetch_article_list(issue)

    if not output_path:
        slug = re.sub(r'[^\w-]', '_', issue_label)[:40]
        output_path = f'frontline-{slug}.epub'

    book = build_epub(feeds, issue_label, cover_url)
    epub.write_epub(output_path, book)
    print(f'\nSaved: {output_path}')
