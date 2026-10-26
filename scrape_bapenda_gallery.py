#!/usr/bin/env python3
"""Scrape all photo gallery pages from Bapenda Medan."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import requests


SOURCE_URL = "https://bapenda.medan.go.id/galeri-photo"
READER_BASE_URL = "https://r.jina.ai/http://"
JAKARTA_TZ = timezone(timedelta(hours=7))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape seluruh galeri foto Bapenda Medan beserta gambarnya."
    )
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument(
        "--end-page",
        type=int,
        help="Halaman terakhir; bila tidak diberikan akan dideteksi otomatis.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/bapenda_gallery.json"),
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("output/bapenda_gallery_images"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("output/bapenda_gallery_cache"),
    )
    parser.add_argument(
        "--laravel-image-prefix",
        default="gallery/bapenda",
        help="Path relatif pada Laravel public disk.",
    )
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--request-delay", type=float, default=4.0)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--no-images", action="store_true")
    args = parser.parse_args()

    if args.start_page < 1:
        parser.error("--start-page minimal 1.")
    if args.end_page is not None and args.end_page < args.start_page:
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


def page_url(page: int) -> str:
    return SOURCE_URL if page == 1 else f"{SOURCE_URL}?page={page}"


def reader_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    target = parsed.netloc + parsed.path
    if parsed.query:
        target += "?" + parsed.query
    return READER_BASE_URL + target


def fetch_reader(
    source_url: str,
    cache_dir: Path,
    timeout: int,
    retries: int,
    delay: float,
) -> str:
    cache_key = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    cache_path = cache_dir / f"{cache_key}.md"
    if cache_path.is_file():
        cached = cache_path.read_text(encoding="utf-8").strip()
        if "Markdown Content:" in cached:
            return cached

    session = new_session()
    try:
        for attempt in range(1, retries + 1):
            try:
                if delay:
                    time.sleep(delay)
                response = session.get(reader_url(source_url), timeout=timeout)
                response.raise_for_status()
                text = response.text.strip()
                if "Markdown Content:" not in text:
                    raise ValueError("Respons reader tidak berisi Markdown Content")

                cache_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = cache_path.with_suffix(".md.tmp")
                temporary.write_text(text + "\n", encoding="utf-8")
                temporary.replace(cache_path)
                return text
            except (requests.RequestException, ValueError) as exc:
                if attempt == retries:
                    raise RuntimeError(f"Gagal mengambil {source_url}") from exc

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
        session.close()

    raise RuntimeError(f"Gagal mengambil {source_url}")


def markdown_content(reader_response: str) -> str:
    return reader_response.split("Markdown Content:", 1)[1].strip()


def detect_last_page(markdown: str) -> int:
    pages = [int(value) for value in re.findall(r"galeri-photo\?page=(\d+)", markdown)]
    return max(pages, default=1)


def parse_gallery_page(markdown: str, page: int) -> List[Dict[str, object]]:
    if "##### Galeri Photo" in markdown:
        markdown = markdown.split("##### Galeri Photo", 1)[1]
    markdown = re.split(
        r"^\*\s+(?:\[‹\]|\d+\s*$)|^####\s+Badan Pendapatan Daerah Kota Medan",
        markdown,
        maxsplit=1,
        flags=re.MULTILINE,
    )[0]

    lines = markdown.splitlines()
    indexes = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^!\[Image\s+\d+:\s*.*\]\(https?://.*\)\s*$", line.strip())
    ]
    items: List[Dict[str, object]] = []

    for position, start in enumerate(indexes):
        end = indexes[position + 1] if position + 1 < len(indexes) else len(lines)
        segment = lines[start:end]
        image_match = re.match(
            r"^!\[Image\s+\d+:\s*(?P<alt>.*)\]\((?P<url>https?://.*)\)\s*$",
            segment[0].strip(),
        )
        if not image_match:
            continue

        heading_index: Optional[int] = None
        title: Optional[str] = None
        for index, line in enumerate(segment[1:], start=1):
            heading = re.match(r"^######\s+(.+?)\s*$", line.strip())
            if heading:
                heading_index = index
                title = " ".join(heading.group(1).split())
                break

        alt_text = " ".join(image_match.group("alt").split())
        title = title or alt_text
        caption_lines: List[str] = []
        if heading_index is not None:
            for line in segment[heading_index + 1 :]:
                normalized = line.strip()
                if not normalized or normalized.startswith("[") or normalized.startswith("!["):
                    continue
                if normalized.startswith("#") or normalized.startswith("*"):
                    continue
                caption_lines.append(normalized)

        media_url = image_match.group("url").strip()
        items.append(
            {
                "source_page": page,
                "title": title,
                "caption": " ".join(" ".join(caption_lines).split()) or None,
                "alt_text": alt_text,
                "source_url": page_url(page),
                "original_media_url": media_url,
                "source_hash": hashlib.sha256(media_url.encode("utf-8")).hexdigest(),
                "media_type": "image",
            }
        )

    return items


def safe_filename(media_url: str, title: str) -> str:
    raw_name = Path(unquote(urlparse(media_url).path)).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "-", raw_name)
    stem, extension = os.path.splitext(safe_name)
    if not stem:
        stem = re.sub(r"[^A-Za-z0-9_-]", "-", title).strip("-") or "gallery"
    if not extension or len(extension) > 6:
        extension = ".jpg"
    digest = hashlib.sha256(media_url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}-{stem[:160]}{extension.lower()}"


def download_image(
    media_url: str,
    destination: Path,
    timeout: int,
    retries: int,
) -> None:
    if destination.is_file() and destination.stat().st_size > 0:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    session = new_session()
    try:
        for attempt in range(1, retries + 1):
            try:
                with session.get(media_url, timeout=timeout, stream=True) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").lower()
                    if content_type and not content_type.startswith("image/"):
                        raise ValueError(f"Content-Type bukan gambar: {content_type}")
                    with temporary.open("wb") as output:
                        for chunk in response.iter_content(64 * 1024):
                            if chunk:
                                output.write(chunk)

                if temporary.stat().st_size == 0:
                    raise ValueError("File gambar kosong")
                temporary.replace(destination)
                return
            except (requests.RequestException, OSError, ValueError) as exc:
                temporary.unlink(missing_ok=True)
                if attempt == retries:
                    raise RuntimeError(f"Gagal mengunduh {media_url}") from exc
                time.sleep(min(2 ** attempt, 12))
    finally:
        session.close()


def prepare_item(
    item: Dict[str, object],
    args: argparse.Namespace,
) -> Tuple[str, Dict[str, object]]:
    media_url = str(item["original_media_url"])
    filename = safe_filename(media_url, str(item["title"]))
    local_path = args.image_dir / filename
    download_image(media_url, local_path, args.timeout, args.retries)
    media_path = f"{args.laravel_image_prefix.strip('/')}/{filename}"
    return str(item["source_hash"]), {
        "media_path": media_path,
        "local_path": local_path.as_posix(),
        "public_url": f"/storage/{media_path}",
    }


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    started_at = datetime.now(JAKARTA_TZ)

    first_response = fetch_reader(
        page_url(args.start_page),
        args.cache_dir,
        args.timeout,
        args.retries,
        args.request_delay,
    )
    first_markdown = markdown_content(first_response)
    end_page = args.end_page or detect_last_page(first_markdown)
    pages = list(range(args.start_page, end_page + 1))

    print(f"Mengambil galeri halaman {args.start_page}-{end_page}...")
    items_by_page: Dict[int, List[Dict[str, object]]] = {
        args.start_page: parse_gallery_page(first_markdown, args.start_page)
    }
    print(f"  halaman {args.start_page}: {len(items_by_page[args.start_page])} item")

    for page in pages[1:]:
        response = fetch_reader(
            page_url(page),
            args.cache_dir,
            args.timeout,
            args.retries,
            args.request_delay,
        )
        items_by_page[page] = parse_gallery_page(markdown_content(response), page)
        if not items_by_page[page]:
            raise RuntimeError(f"Tidak ada galeri yang terparse pada halaman {page}")
        print(f"  halaman {page}: {len(items_by_page[page])} item")

    items: List[Dict[str, object]] = []
    seen = set()
    for page in pages:
        for item in items_by_page[page]:
            if item["source_hash"] in seen:
                continue
            seen.add(item["source_hash"])
            item["source_order"] = len(items) + 1
            items.append(item)

    if not args.no_images:
        print(f"Mengunduh {len(items)} gambar galeri...")
        prepared: Dict[str, Dict[str, object]] = {}
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(prepare_item, item, args): item for item in items}
            for completed, future in enumerate(as_completed(futures), start=1):
                source_hash, media = future.result()
                prepared[source_hash] = media
                print(f"  gambar: {completed}/{len(items)}")
        for item in items:
            item.update(prepared[str(item["source_hash"])])
    else:
        for item in items:
            item.update({"media_path": None, "local_path": None, "public_url": None})

    finished_at = datetime.now(JAKARTA_TZ)
    payload: Dict[str, object] = {
        "source": SOURCE_URL,
        "page_start": args.start_page,
        "page_end": end_page,
        "gallery_count": len(items),
        "scraped_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 2),
        "galleries": items,
    }
    write_json(args.output, payload)
    print(f"Selesai: {len(items)} item -> {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Dibatalkan.", file=sys.stderr)
        raise SystemExit(130)
