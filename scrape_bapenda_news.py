#!/usr/bin/env python3
"""Scrape Bapenda Medan news pages and prepare Laravel-compatible assets.

The public website uses a Cloudflare browser challenge for HTML pages. This
script therefore reads the public pages through Jina Reader while downloading
the public image assets directly from Bapenda's storage URLs.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import hashlib
import html
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import time
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import requests


SOURCE_BASE_URL = "https://bapenda.medan.go.id/berita"
READER_BASE_URL = "https://r.jina.ai/http://"
JAKARTA_TZ = timezone(timedelta(hours=7))

INDONESIAN_MONTHS = {
    "Januari": 1,
    "Februari": 2,
    "Maret": 3,
    "April": 4,
    "Mei": 5,
    "Juni": 6,
    "Juli": 7,
    "Agustus": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Desember": 12,
}

ARTICLE_BLOCK_RE = re.compile(
    r"!\[Image\s+\d+:\s*(?P<image_alt>[^\]]*)\]"
    r"\((?P<image_url>https?://[^)]+)\)\s*\n+"
    r"(?:\[\]\(https?://[^)]+/berita/[^)]+\.html\)\s*\n+)?"
    r"(?P<meta>[^\n]+?)\s*\n+"
    r"kategori\s*:\s*\[(?P<category>[^\]]+)\]\([^)]+\)\s*\n+"
    r"\[(?P<title>[^\]]+)\]"
    r"\((?P<source_url>https?://[^)]+/berita/[^)]+\.html)\)\s*\n+"
    r"(?P<excerpt>.*?)\s*\n+"
    r"\[Baca\s+Selengkapnya\.\.\.\]\([^)]+\)",
    re.IGNORECASE | re.DOTALL,
)

DETAIL_META_RE = re.compile(
    r"^\*\*(?P<date>.+?)\*\*\s*\|\s*Dibaca:\s*(?P<views>[\d.]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

MARKDOWN_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\("
    r"(?P<url>(?:https?://|/)(?:[^()\s]|\([^()\s]*\))+?)"
    r"\)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape berita Bapenda Medan beserta isi dan gambarnya."
    )
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=12)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/bapenda_news.json"),
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("output/bapenda_images"),
    )
    parser.add_argument(
        "--laravel-image-prefix",
        default="news/bapenda",
        help="Path relatif pada Laravel public disk.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("output/bapenda_cache"),
        help="Cache respons reader agar proses dapat dilanjutkan.",
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--request-delay",
        type=float,
        default=3.0,
        help="Jeda sebelum permintaan reader (detik).",
    )
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--no-images", action="store_true")
    args = parser.parse_args()

    if args.start_page < 1 or args.end_page < args.start_page:
        parser.error("Rentang halaman tidak valid.")
    if args.workers < 1 or args.workers > 8:
        parser.error("--workers harus bernilai 1 sampai 8.")
    if args.request_delay < 0:
        parser.error("--request-delay tidak boleh negatif.")

    return args


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0 Safari/537.36"
            ),
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.7",
        }
    )
    return session


def reader_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    path_and_query = parsed.netloc + parsed.path
    if parsed.query:
        path_and_query += "?" + parsed.query
    return READER_BASE_URL + path_and_query


def fetch_text(
    source_url: str,
    timeout: int,
    retries: int,
    session: Optional[requests.Session] = None,
    cache_dir: Optional[Path] = None,
    request_delay: float = 0,
) -> str:
    cache_path = None
    if cache_dir is not None:
        cache_key = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
        cache_path = cache_dir / f"{cache_key}.md"
        if cache_path.is_file():
            cached = cache_path.read_text(encoding="utf-8").strip()
            if "Markdown Content:" in cached:
                return cached

    own_session = session is None
    session = session or new_session()
    url = reader_url(source_url)

    try:
        for attempt in range(1, retries + 1):
            try:
                if request_delay:
                    time.sleep(request_delay)
                response = session.get(url, timeout=timeout)
                response.raise_for_status()
                text = response.text.strip()
                if "Markdown Content:" not in text:
                    raise ValueError("Respons reader tidak berisi Markdown Content")
                if cache_path is not None:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = cache_path.with_suffix(".md.tmp")
                    temporary.write_text(text + "\n", encoding="utf-8")
                    temporary.replace(cache_path)
                return text
            except (requests.RequestException, ValueError) as exc:
                if attempt == retries:
                    raise RuntimeError(
                        f"Gagal mengambil {source_url} setelah {retries} percobaan"
                    ) from exc
                if (
                    isinstance(exc, requests.HTTPError)
                    and exc.response is not None
                    and exc.response.status_code == 429
                ):
                    retry_after = exc.response.headers.get("Retry-After")
                    wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 30 * attempt
                else:
                    wait_seconds = min(2 ** attempt, 12)
                time.sleep(min(wait_seconds, 120))
    finally:
        if own_session:
            session.close()

    raise RuntimeError(f"Gagal mengambil {source_url}")


def markdown_content(reader_response: str) -> str:
    return reader_response.split("Markdown Content:", 1)[1].strip()


def parse_listing_meta(raw_meta: str) -> Tuple[str, Optional[int]]:
    raw_meta = " ".join(raw_meta.split())
    match = re.match(r"^(?P<date>.+?,\s*\d{2}:\d{2}:\d{2})\s+(?P<views>[\d.]+)$", raw_meta)
    if not match:
        return raw_meta, None
    return match.group("date"), int(match.group("views").replace(".", ""))


def parse_indonesian_datetime(raw_date: str) -> Optional[str]:
    raw_date = raw_date.strip().strip("*")
    match = re.match(
        r"^(?:[A-Za-z]+),\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}),\s*"
        r"(\d{2}):(\d{2}):(\d{2})$",
        raw_date,
    )
    if not match:
        return None

    day, month_name, year, hour, minute, second = match.groups()
    month = INDONESIAN_MONTHS.get(month_name)
    if month is None:
        return None

    parsed = datetime(
        int(year),
        month,
        int(day),
        int(hour),
        int(minute),
        int(second),
        tzinfo=JAKARTA_TZ,
    )
    return parsed.isoformat()


def slug_from_url(source_url: str) -> str:
    filename = Path(unquote(urlparse(source_url).path)).name
    return re.sub(r"\.html$", "", filename, flags=re.IGNORECASE)


def parse_listing_page(markdown: str, page: int) -> List[Dict[str, object]]:
    articles: List[Dict[str, object]] = []

    if "##### Berita Artikel" in markdown:
        markdown = markdown.split("##### Berita Artikel", 1)[1]
    markdown = re.split(
        r"^\*\s+\[‹\]|^####\s+Badan Pendapatan Daerah Kota Medan",
        markdown,
        maxsplit=1,
        flags=re.MULTILINE,
    )[0]

    lines = markdown.splitlines()
    image_indexes = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^!\[Image\s+\d+:\s*.*\]\(https?://.*\)\s*$", line.strip())
    ]

    for position, start_index in enumerate(image_indexes):
        end_index = image_indexes[position + 1] if position + 1 < len(image_indexes) else len(lines)
        segment = lines[start_index:end_index]
        image_match = re.match(
            r"^!\[Image\s+\d+:\s*(?P<alt>.*)\]\((?P<url>https?://.*)\)\s*$",
            segment[0].strip(),
        )
        if not image_match:
            continue

        baca_index = None
        source_url = None
        for index, line in enumerate(segment):
            baca_match = re.match(
                r"^\[Baca\s+Selengkapnya\.\.\.\]\((?P<url>https?://.*)\)\s*$",
                line.strip(),
                re.IGNORECASE,
            )
            if baca_match:
                baca_index = index
                source_url = baca_match.group("url").strip()
                break
        if baca_index is None or source_url is None:
            continue

        meta_line = next(
            (
                line.strip()
                for line in segment
                if re.match(
                    r"^[A-Za-z]+,\s*\d{1,2}\s+[A-Za-z]+\s+\d{4},\s*"
                    r"\d{2}:\d{2}:\d{2}\s+[\d.]+\s*$",
                    line.strip(),
                )
            ),
            "",
        )
        published_raw, views = parse_listing_meta(meta_line)

        category = None
        category_index = 0
        for index, line in enumerate(segment):
            category_match = re.match(
                r"^kategori\s*:\s*\[(?P<category>[^\]]+)\]\([^)]+\)\s*$",
                line.strip(),
                re.IGNORECASE,
            )
            if category_match:
                category = " ".join(category_match.group("category").split())
                category_index = index
                break

        title = None
        title_index = None
        for index, line in enumerate(segment[:baca_index]):
            title_match = re.match(
                r"^\[(?P<title>[^\]]+)\]\((?P<url>https?://.*?/berita/.*\.html)\)\s*$",
                line.strip(),
                re.IGNORECASE,
            )
            if title_match and title_match.group("url").strip() == source_url:
                title = " ".join(title_match.group("title").split())
                title_index = index

        if not title:
            title = " ".join(image_match.group("alt").split())

        excerpt_start = (title_index + 1) if title_index is not None else (category_index + 1)
        excerpt_lines = []
        for line in segment[excerpt_start:baca_index]:
            normalized = line.strip()
            if not normalized or normalized.startswith("[") or normalized.startswith("!["):
                continue
            excerpt_lines.append(normalized)
        excerpt = " ".join(" ".join(excerpt_lines).split())

        articles.append(
            {
                "source_page": page,
                "title": title,
                "slug": slug_from_url(source_url),
                "source_url": source_url,
                "category": category,
                "published_at": parse_indonesian_datetime(published_raw),
                "published_at_raw": published_raw,
                "views": views,
                "excerpt": excerpt,
                "image_alt": " ".join(image_match.group("alt").split()),
                "image_url": image_match.group("url").strip(),
            }
        )

    return articles


def trim_detail_body(body: str) -> str:
    stop_patterns = [
        r"^#{1,6}\s+Badan Pendapatan Daerah Kota Medan\s*$",
        r"^Situs Resmi Badan Pendapatan Daerah Kota Medan\.",
        r"^Jl\. A\. H\. Nasution No\. 32 Medan",
    ]
    lines = body.strip().splitlines()
    kept: List[str] = []

    for line in lines:
        if any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in stop_patterns):
            break
        kept.append(line.rstrip())

    return "\n".join(kept).strip()


def parse_detail(markdown: str) -> Dict[str, object]:
    heading_match = re.search(r"^###\s+(.+?)\s*$", markdown, re.MULTILINE)
    meta_match = DETAIL_META_RE.search(markdown)
    divider_match = re.search(r"^\*\s+\*\s+\*\s*$", markdown, re.MULTILINE)

    if divider_match:
        body = markdown[divider_match.end() :]
    elif meta_match:
        body = markdown[meta_match.end() :]
    else:
        body = markdown

    body = trim_detail_body(body)
    images = [
        {"alt": " ".join(match.group("alt").split()), "url": match.group("url")}
        for match in MARKDOWN_IMAGE_RE.finditer(body)
    ]

    result: Dict[str, object] = {
        "detail_title": " ".join(heading_match.group(1).split()) if heading_match else None,
        "content_markdown": body,
        "content_images": images,
    }

    if meta_match:
        raw_date = " ".join(meta_match.group("date").split())
        result.update(
            {
                "published_at": parse_indonesian_datetime(raw_date),
                "published_at_raw": raw_date,
                "views": int(meta_match.group("views").replace(".", "")),
            }
        )

    return result


def markdown_to_text(markdown: str) -> str:
    text = MARKDOWN_IMAGE_RE.sub(lambda match: match.group("alt"), markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|>\s*)", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def render_inline(markdown: str) -> str:
    tokens: Dict[str, str] = {}

    def stash(rendered: str) -> str:
        key = f"@@BAPENDATOKEN{len(tokens):04d}@@"
        tokens[key] = rendered
        return key

    def image_replacement(match: re.Match[str]) -> str:
        alt = html.escape(match.group("alt"), quote=True)
        url = html.escape(match.group("url"), quote=True)
        return stash(
            f'<img src="{url}" alt="{alt}" loading="lazy" class="img-fluid">'
        )

    text = MARKDOWN_IMAGE_RE.sub(image_replacement, markdown)

    def link_replacement(match: re.Match[str]) -> str:
        label = html.escape(match.group(1), quote=False)
        url = html.escape(match.group(2), quote=True)
        return stash(f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>')

    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", link_replacement, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_]+?)_(?!_)", r"<em>\1</em>", text)

    for key, rendered in tokens.items():
        text = text.replace(key, rendered)
    return text


def markdown_to_html(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    output: List[str] = []
    paragraph: List[str] = []
    list_type: Optional[str] = None

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            close_list()
            continue

        if re.match(r"^(?:\*\s+\*\s+\*|-{3,})$", line):
            flush_paragraph()
            close_list()
            output.append("<hr>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            desired_type = "ul" if bullet else "ol"
            if list_type != desired_type:
                close_list()
                output.append(f"<{desired_type}>")
                list_type = desired_type
            content = (bullet or numbered).group(1)
            output.append(f"<li>{render_inline(content)}</li>")
            continue

        if line.startswith(">"):
            flush_paragraph()
            close_list()
            output.append(f"<blockquote>{render_inline(line.lstrip('> ').strip())}</blockquote>")
            continue

        if MARKDOWN_IMAGE_RE.fullmatch(line):
            flush_paragraph()
            close_list()
            output.append(f"<p>{render_inline(line)}</p>")
            continue

        close_list()
        paragraph.append(line)

    flush_paragraph()
    close_list()
    return "\n".join(output)


def safe_image_filename(image_url: str, fallback_slug: str, index: int) -> str:
    filename = Path(unquote(urlparse(image_url).path)).name
    filename = re.sub(r"[^A-Za-z0-9._-]", "-", filename)
    stem, extension = os.path.splitext(filename)

    if not extension or len(extension) > 6:
        extension = ".jpg"
    if not stem:
        stem = f"{fallback_slug}-{index}"
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}-{stem[:160]}{extension.lower()}"


def download_image(
    image_url: str,
    destination: Path,
    timeout: int,
    retries: int,
) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    session = new_session()
    temporary = destination.with_suffix(destination.suffix + ".part")

    try:
        for attempt in range(1, retries + 1):
            try:
                with session.get(image_url, timeout=timeout, stream=True) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").lower()
                    if content_type and not content_type.startswith("image/"):
                        raise ValueError(f"Content-Type bukan gambar: {content_type}")
                    with temporary.open("wb") as file_handle:
                        for chunk in response.iter_content(chunk_size=64 * 1024):
                            if chunk:
                                file_handle.write(chunk)

                if temporary.stat().st_size == 0:
                    raise ValueError("File gambar kosong")
                temporary.replace(destination)
                return
            except (requests.RequestException, OSError, ValueError) as exc:
                temporary.unlink(missing_ok=True)
                if attempt == retries:
                    raise RuntimeError(f"Gagal mengunduh gambar {image_url}") from exc
                time.sleep(min(2 ** attempt, 12))
    finally:
        session.close()


def write_json(output: Path, payload: Dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)
        file_handle.write("\n")
    temporary.replace(output)


def fetch_listing_page(page: int, args: argparse.Namespace) -> Tuple[int, List[Dict[str, object]]]:
    source_url = SOURCE_BASE_URL if page == 1 else f"{SOURCE_BASE_URL}?page={page}"
    response = fetch_text(
        source_url,
        args.timeout,
        args.retries,
        cache_dir=args.cache_dir,
        request_delay=args.request_delay,
    )
    articles = parse_listing_page(markdown_content(response), page)
    if not articles:
        raise RuntimeError(f"Tidak ada berita yang berhasil diparse pada halaman {page}")
    return page, articles


def fetch_article_detail(
    article: Dict[str, object], args: argparse.Namespace
) -> Tuple[str, Dict[str, object]]:
    source_url = str(article["source_url"])
    response = fetch_text(
        source_url,
        args.timeout,
        args.retries,
        cache_dir=args.cache_dir,
        request_delay=args.request_delay,
    )
    detail = parse_detail(markdown_content(response))
    return source_url, detail


def unique_media(article: Dict[str, object]) -> List[Dict[str, str]]:
    media: List[Dict[str, str]] = []
    seen = set()

    cover_url = str(article.get("image_url") or "").strip()
    if cover_url:
        seen.add(cover_url)
        media.append(
            {
                "role": "cover",
                "url": cover_url,
                "alt": str(article.get("image_alt") or article.get("title") or ""),
            }
        )

    for content_image in article.get("content_images", []):
        image_url = str(content_image.get("url") or "").strip()
        if not image_url or image_url in seen:
            continue
        seen.add(image_url)
        media.append(
            {
                "role": "content",
                "url": image_url,
                "alt": str(content_image.get("alt") or ""),
            }
        )

    return media


def prepare_article_media(
    article: Dict[str, object], args: argparse.Namespace
) -> Tuple[str, List[Dict[str, str]], Dict[str, str]]:
    source_url = str(article["source_url"])
    prepared: List[Dict[str, str]] = []
    replacements: Dict[str, str] = {}

    for index, media in enumerate(unique_media(article), start=1):
        filename = safe_image_filename(media["url"], str(article["slug"]), index)
        local_path = args.image_dir / filename
        laravel_path = f"{args.laravel_image_prefix.strip('/')}/{filename}"
        download_image(media["url"], local_path, args.timeout, args.retries)
        public_url = f"/storage/{laravel_path}"
        replacements[media["url"]] = public_url
        prepared.append(
            {
                **media,
                "local_path": local_path.as_posix(),
                "image_path": laravel_path,
                "public_url": public_url,
            }
        )

    return source_url, prepared, replacements


def main() -> int:
    args = parse_args()
    started_at = datetime.now(JAKARTA_TZ)
    pages = list(range(args.start_page, args.end_page + 1))
    articles_by_page: Dict[int, List[Dict[str, object]]] = {}

    print(f"Mengambil daftar berita halaman {args.start_page}-{args.end_page}...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_listing_page, page, args): page for page in pages}
        for future in as_completed(futures):
            page, articles = future.result()
            articles_by_page[page] = articles
            print(f"  halaman {page}: {len(articles)} berita")

    articles: List[Dict[str, object]] = []
    seen_urls = set()
    for page in pages:
        for article in articles_by_page[page]:
            if article["source_url"] in seen_urls:
                continue
            seen_urls.add(article["source_url"])
            articles.append(article)

    print(f"Mengambil isi lengkap {len(articles)} berita...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_article_detail, article, args): article["source_url"]
            for article in articles
        }
        details: Dict[str, Dict[str, object]] = {}
        completed = 0
        for future in as_completed(futures):
            source_url, detail = future.result()
            details[source_url] = detail
            completed += 1
            if completed % 10 == 0 or completed == len(articles):
                print(f"  detail: {completed}/{len(articles)}")

    for article in articles:
        detail = details[str(article["source_url"])]
        detail_title = detail.pop("detail_title", None)
        if detail_title:
            article["title"] = detail_title
        for key, value in detail.items():
            if value is not None:
                article[key] = value
        if not str(article.get("content_markdown") or "").strip():
            article["content_markdown"] = article.get("excerpt") or article["title"]
        article["content_text"] = markdown_to_text(str(article["content_markdown"]))
        if re.fullmatch(r"Image\s+\d+", str(article["content_text"]), re.IGNORECASE):
            article["content_text"] = article["title"]
        if not article.get("excerpt") or re.fullmatch(
            r"Image\s+\d+", str(article["excerpt"]), re.IGNORECASE
        ):
            article["excerpt"] = str(article["content_text"])[:500]

    if not args.no_images:
        print("Mengunduh gambar berita...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(prepare_article_media, article, args): article["source_url"]
                for article in articles
            }
            prepared_media: Dict[str, Tuple[List[Dict[str, str]], Dict[str, str]]] = {}
            completed = 0
            for future in as_completed(futures):
                source_url, media, replacements = future.result()
                prepared_media[source_url] = (media, replacements)
                completed += 1
                if completed % 10 == 0 or completed == len(articles):
                    print(f"  gambar: {completed}/{len(articles)} berita")

        for article in articles:
            media, replacements = prepared_media[str(article["source_url"])]
            article["images"] = media
            cover = next((item for item in media if item["role"] == "cover"), None)
            article["image_path"] = cover["image_path"] if cover else None
            localized_markdown = str(article["content_markdown"])
            for remote_url, public_url in replacements.items():
                localized_markdown = localized_markdown.replace(remote_url, public_url)
            article["body_html"] = markdown_to_html(localized_markdown)
    else:
        for article in articles:
            article["images"] = []
            article["image_path"] = None
            article["body_html"] = markdown_to_html(str(article["content_markdown"]))

    finished_at = datetime.now(JAKARTA_TZ)
    payload: Dict[str, object] = {
        "source": SOURCE_BASE_URL,
        "page_start": args.start_page,
        "page_end": args.end_page,
        "article_count": len(articles),
        "scraped_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 2),
        "articles": articles,
    }
    write_json(args.output, payload)

    print(f"Selesai: {len(articles)} berita -> {args.output}")
    if not args.no_images:
        image_count = sum(len(article["images"]) for article in articles)
        print(f"Gambar: {image_count} file -> {args.image_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Dibatalkan oleh pengguna.", file=sys.stderr)
        raise SystemExit(130)
