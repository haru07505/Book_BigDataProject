from __future__ import annotations

import hashlib
from itertools import product
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib import response
from urllib import response
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit

import scrapy

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler_etl.scrapy_crawler.book_crawler.items import BookItem

from crawler_etl.scrapy_crawler.book_crawler.text_utils import (
    canonical_url,
    clean_title,
    compact_text,
    config_main_category,
    config_sub_category,
    find_metadata,
    fold_text,
    parse_discount,
    parse_decimal,
    parse_human_count,
    parse_number,
)


DEFAULT_CONFIG = PROJECT_ROOT / "crawler_etl" / "config" / "fahasa_config.json"


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def category_page_url(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["p"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def response_lines(response) -> list[str]:
    lines: list[str] = []
    for value in response.xpath("//body//*[not(self::script) and not(self::style)]/text()").getall():
        text = compact_text(value)
        if text:
            lines.append(text)
    return lines


def text_from_selectors(response, selectors: list[str]) -> str | None:
    for selector in selectors:
        for node in response.css(selector):
            text = compact_text(" ".join(node.xpath(".//text()").getall()))
            if text:
                return text
    return None


def anchor_text(anchor) -> str | None:
    text = compact_text(anchor.xpath("string()").get())
    return text if text and len(text) <= 80 else None


def json_ld_product(response) -> dict[str, Any]:
    def iter_records(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            graph = payload.get("@graph")
            if isinstance(graph, list):
                return graph
            return [payload]
        return []

    for script_text in response.css('script[type="application/ld+json"]::text').getall():
        try:
            payload = json.loads(script_text.strip())
        except json.JSONDecodeError:
            continue
        for record in iter_records(payload):
            types = record.get("@type") if isinstance(record, dict) else None
            type_values = types if isinstance(types, list) else [types]
            if isinstance(record, dict) and "Product" in type_values:
                return record
    return {}


def metadata_rows(response) -> dict[str, str]:
    metadata: dict[str, str] = {}

    known_labels = {
        "ma hang",
        "sku",
        "nha cung cap",
        "tac gia",
        "author",
        "nguoi dich",
        "nxb",
        "nha xuat ban",
        "publisher",
        "nam xb",
        "nam xuat ban",
        "publish year",
        "so trang",
        "number of pages",
        "hinh thuc",
    }

    invalid_metadata_values = known_labels | {
        "trong luong gr",
        "kich thuoc bao bi",
        "ngon ngu",
        "san pham ban chay nhat",
        "du kien co hang",
    }

    for row in response.css("tr, .product-view-sa-supplier, .product-view-sa-author"):
        values = [
            text
            for text in (compact_text(value) for value in row.xpath(".//text()").getall())
            if text
        ]

        if len(values) >= 2:
            key = fold_text(values[0]).rstrip(":")
            value = values[-1].strip()
            value_key = fold_text(value).rstrip(":")

            if key in known_labels and value_key not in invalid_metadata_values:
                metadata[key] = value

    lines = response_lines(response)
    folded_lines = [fold_text(line).rstrip(":") for line in lines]

    for index, key in enumerate(folded_lines[:-1]):
        if key in known_labels and key not in metadata:
            value = lines[index + 1].strip()
            value_key = fold_text(value).rstrip(":")

            if value_key in invalid_metadata_values:
                continue

            metadata[key] = value

    return metadata


def offer_price(product: dict[str, Any]) -> float | None:
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        return None
    return parse_number(offers.get("price") or offers.get("lowPrice"))


def price_from_response(response) -> float | None:
    text = text_from_selectors(
        response,
        [
            ".special-price .price",
            ".price-box .special-price",
            ".price-info .special-price",
            ".product-view-price .special-price",
            ".fhs_product_price",
            ".price",
        ],
    )
    if text:
        return parse_number(text)
    for line in response_lines(response):
        folded = fold_text(line)
        if "special price" in folded or "gia ban" in folded or "gia fahasa" in folded:
            price = parse_number(line)
            if price is not None:
                return price
    return None


def original_price_from_response(response) -> float | None:
    text = text_from_selectors(
        response,
        [
            ".old-price .price",
            ".price-box .old-price",
            ".regular-price .price",
            ".price-info .regular-price",
        ],
    )
    if text:
        return parse_number(text)
    for line in response_lines(response):
        if "regular price" in fold_text(line) or "gia bia" in fold_text(line):
            price = parse_number(line)
            if price is not None:
                return price
    return None


def discount_from_response(response) -> float | None:
    text = text_from_selectors(response, [".discount-percent", ".discount", ".price-discount"])
    discount = parse_discount(text)

    if discount is not None:
        return abs(discount)

    for line in response_lines(response):
        discount = parse_discount(line)
        if discount is not None:
            return abs(discount)

    return None


def is_boxset_item(title: str | None, sku: str | None, url: str | None, product: dict[str, Any]) -> bool:
    """Detect boxset / box set / trọn bộ items and exclude them from crawl output."""
    txt = "" if title is None else title.casefold()
    prod_name = "" if not isinstance(product, dict) else str(product.get("name") or "").casefold()
    path = urlsplit(str(url or "")).path.lower()

    # Keywords that indicate a box set
    box_keys = ("boxset", "box set", "box-set", "trọn bộ", "tron bo", "tron-bo", "trọn-bộ")
    for k in box_keys:
        if k in txt or k in prod_name or k in path:
            return True

    # Some SKUs are long numeric EANs for boxsets; if SKU is long and name suggests a set, treat as boxset
    if sku and isinstance(sku, (str, int)):
        s = str(sku)
        if s.isdigit() and len(s) >= 13:
            if any(w in txt for w in ("set", "box", "trọn", "trọn bộ")) or any(w in prod_name for w in ("set", "box", "trọn", "trọn bộ")):
                return True

    return False


def rating_from_response(response) -> float | None:
    candidates: list[str] = []
    rating_block = text_from_selectors(response, [".product-view-tab-content-rating"])
    if rating_block:
        candidates.append(rating_block)
    product_rating = text_from_selectors(response, [".product-view-rate", ".ratings", ".rating-box", ".rating"])
    if product_rating:
        candidates.append(product_rating)
    candidates.extend(response_lines(response))
    for text in candidates:
        match = re.search(r"\b([0-5](?:[.,]\d+)?)\s*/\s*5\b", text)
        if match:
            return parse_decimal(match.group(1))
    return None


def sold_count_from_response(response) -> int | None:
    text = text_from_selectors(response, [".product-view-qty-num"])
    sold_count = parse_human_count(text)
    if sold_count is not None:
        return sold_count
    for line in response_lines(response):
        if "da ban" in fold_text(line):
            sold_count = parse_human_count(line)
            if sold_count is not None:
                return sold_count
    return None


def review_count_from_response(response) -> int | None:
    rating_block = text_from_selectors(response, [".product-view-tab-content-rating"])
    if rating_block:
        folded = fold_text(rating_block)
        match = re.search(r"\(?\s*(\d[\d.,]*)\s*(?:danh gia|nhan xet|review)", folded)
        if match:
            return parse_human_count(match.group(1))

    text = text_from_selectors(response, [".product-view-review-count", ".review-count", ".rating-links"])
    review_count = parse_human_count(text)
    if review_count is not None:
        return review_count
    for line in response_lines(response):
        folded = fold_text(line)
        if "danh gia" in folded or "nhan xet" in folded or "review" in folded:
            review_count = parse_human_count(line)
            if review_count is not None:
                return review_count
    return None


def breadcrumb_categories(response) -> tuple[str | None, str | None]:
    nodes = response.css(".breadcrumbs a, .breadcrumb a")
    if not nodes:
        nodes = response.css(".breadcrumbs li, .breadcrumb li")
    labels: list[str] = []
    skip_values = {
        "trang chu",
        "fahasa.com",
        "sach trong nuoc",
        "sach tieng viet",
        "foreign books",
        "home",
    }
    for node in nodes:
        text = compact_text(node.xpath("string()").get())
        if not text:
            continue
        folded = fold_text(text)
        if folded in skip_values or folded.startswith("top 100"):
            continue
        if text not in labels:
            labels.append(text)
    if not labels:
        return None, None
    main_category = labels[0]
    sub_category = labels[-1] if len(labels) > 1 else labels[0]
    return main_category, sub_category


def name_from_url(url: str) -> str:
    slug = Path(urlsplit(url).path).stem
    words = re.sub(r"[-_]+", " ", unquote(slug)).strip()
    return words.title() if words else "Fahasa Category"


def language_group_from_url(url: str, fallback: str | None = None) -> str | None:
    path = urlsplit(url).path
    if path.startswith("/foreigncategory/"):
        return "English"
    if path.startswith("/sach-trong-nuoc/"):
        return "Vietnamese"
    return fallback


def matches_category_prefix(url: str, prefixes: list[str]) -> bool:
    return any(url.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)

def title_from_response(response, product: dict[str, Any]) -> str | None:
    candidates = [
        response.css("h1.fhs_name_product_desktop::text").get(),
        response.css(".fhs_name_product_desktop::text").get(),
        response.css(".product-essential-detail h1::text").get(),
        response.css(".product-name h1::text").get(),
        response.css("h1::text").get(),
        response.css("meta[property='og:title']::attr(content)").get(),
        response.css("meta[name='title']::attr(content)").get(),
        product.get("name"),
        response.css("title::text").get(),
    ]

    for value in candidates:
        title = clean_title(value)
        if title and is_good_title(title):
            return title

    for value in candidates:
        title = clean_title(value)
        if title:
            return title

    return None


def is_good_title(title: str) -> bool:
    text = title.strip()

    if "�" in text:
        return False

    if text.endswith(("(", "-", ",", ";", ":")):
        return False

    if text.count("(") > text.count(")"):
        return False

    if len(text) < 5:
        return False

    return True

class FahasaSpider(scrapy.Spider):
    name = "fahasa"
    allowed_domains = ["fahasa.com"]

    def __init__(self, config: str | None = None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config_path = Path(config) if config else DEFAULT_CONFIG
        self.config_data = load_config(self.config_path)
        self.max_products_per_category = int(self.config_data["max_products_per_category"])
        self.max_discovered_categories = int(self.config_data.get("max_discovered_categories", 0))
        self.max_category_depth = int(self.config_data.get("max_category_depth", 1))
        self.category_counts: dict[str, int] = {}
        self.seed_category_counts: dict[str, int] = {}
        self.seen_category_urls: set[str] = set()
        self.seen_urls: set[str] = set()

    def start_requests(self):
        if self.config_data.get("discover_categories", False):
            for seed in self.config_data.get("category_seed_urls", []):
                yield scrapy.Request(
                    url=seed["url"],
                    callback=self.parse_category_seed,
                    cb_kwargs={"seed": seed},
                )
            return

        for seed in self.config_data.get("category_seed_urls", []):
            yield from self.schedule_category_pages(
                {
                    "name": seed.get("name"),
                    "main_category": seed.get("name"),
                    "sub_category": seed.get("name"),
                    "language_group": seed.get("language_group"),
                    "url": seed["url"],
                }
            )

    def schedule_category_pages(self, category: dict[str, Any]):
        category_url = canonical_url(category["url"])
        if category_url in self.seen_category_urls:
            return

        if self.max_discovered_categories and len(self.seen_category_urls) >= self.max_discovered_categories:
            return

        seed_key = category.get("seed_key")
        if seed_key:
            max_categories_per_seed = int(self.config_data.get("max_categories_per_seed", 0))
            current_count = self.seed_category_counts.get(seed_key, 0)
            if max_categories_per_seed and current_count >= max_categories_per_seed:
                return
            self.seed_category_counts[seed_key] = current_count + 1

        category = {**category, "url": category_url}
        category_key = str(len(self.seen_category_urls))
        self.seen_category_urls.add(category_url)
        self.category_counts[category_key] = 0

        max_pages = int(self.config_data["max_pages_per_category"])
        for page in range(1, max_pages + 1):
            yield scrapy.Request(
                url=category_page_url(category_url, page),
                callback=self.parse_category,
                cb_kwargs={"category": category, "category_key": category_key},
            )

    def parse_category_seed(self, response, seed: dict[str, Any]):
        yield from self.discover_category_links(response, seed, depth=0)

    def discover_category_links(self, response, seed: dict[str, Any], depth: int):
        prefixes = self.config_data.get("category_url_prefixes", [])
        selectors = self.config_data.get("selectors", {}).get("category_links", ["a"])
        discovered_count = 0
        seed_key = canonical_url(seed["url"])

        for selector in selectors:
            for anchor in response.css(selector):
                href = anchor.xpath("@href").get()
                if not href:
                    continue

                category_url = canonical_url(urljoin(response.url, href))
                if not matches_category_prefix(category_url, prefixes):
                    continue

                name = anchor_text(anchor) or name_from_url(category_url)
                category = {
                    "name": name,
                    "main_category": seed.get("name") or name,
                    "sub_category": name,
                    "language_group": language_group_from_url(category_url, seed.get("language_group")),
                    "seed_key": seed_key,
                    "url": category_url,
                }
                discovered_count += 1

                if category_url not in self.seen_category_urls:
                    yield from self.schedule_category_pages(category)

                    if depth < self.max_category_depth:
                        yield scrapy.Request(
                            url=category_url,
                            callback=self.parse_discovered_category,
                            cb_kwargs={"seed": seed, "depth": depth + 1},
                            priority=-1,
                        )

        if discovered_count == 0 and depth == 0:
            self.logger.warning(
                "No Fahasa category links discovered from %s.",
                response.url,
            )

    def parse_discovered_category(self, response, seed: dict[str, Any], depth: int):
        yield from self.discover_category_links(response, seed, depth=depth)

    def parse_category(self, response, category: dict[str, Any], category_key: str):
        selectors = self.config_data.get("selectors", {}).get("product_links", [])
        for selector in selectors:
            for href in response.css(selector).xpath("@href").getall():
                if self.category_counts[category_key] >= self.max_products_per_category:
                    return

                detail_url = canonical_url(urljoin(response.url, href))

                if not detail_url.endswith(".html"):
                    continue

                if "seriesbook-index" in detail_url or "/series-" in urlsplit(detail_url).path.lower():
                    continue

                path = urlsplit(detail_url).path.lower()

                if (
                    "seriesbook-index" in path
                    or path.startswith("/series-")
                    or "combo" in path
                    or "bo-sach" in path
                    or "bộ-sách" in path
                ):
                    continue

                if detail_url in self.seen_urls:
                    continue

                self.seen_urls.add(detail_url)
                self.category_counts[category_key] += 1
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    cb_kwargs={"category": category},
                    priority=1,
                )

    def parse_detail(self, response, category: dict[str, Any]):
        product = json_ld_product(response)
        metadata = metadata_rows(response)
        aggregate_rating = product.get("aggregateRating") or {}
        main_category, sub_category = breadcrumb_categories(response)
        sku = product.get("sku") or find_metadata(metadata, "ma hang", "sku")
        detail_url = canonical_url(response.url)
        fallback_id = hashlib.sha1(detail_url.encode("utf-8")).hexdigest()[:16]

        rating_value = None
        review_count = None
        if isinstance(aggregate_rating, dict):
            rating_value = parse_decimal(aggregate_rating.get("ratingValue"))
            review_count = parse_human_count(aggregate_rating.get("reviewCount"))

        detail_title = title_from_response(response, product)

        # Compute prices safely.
        # If Fahasa does not show an original/old price, treat it as no discount.
        price_val = first_not_none(offer_price(product), price_from_response(response))
        orig_price_val = original_price_from_response(response)

        if orig_price_val is None and price_val is not None:
            orig_price_val = price_val
            discount_val = 0.0
        else:
            discount_val = discount_from_response(response)

        if (
            discount_val is None
            and price_val is not None
            and orig_price_val is not None
            and orig_price_val > price_val
        ):
            discount_val = round((orig_price_val - price_val) * 100 / orig_price_val, 2)

        if (
            discount_val is not None
            and discount_val > 100
            and price_val is not None
            and orig_price_val is not None
        ):
            discount_val = round((orig_price_val - price_val) * 100 / orig_price_val, 2)

        # drop boxset items
        if is_boxset_item(detail_title, sku, detail_url, product):
            return

        yield BookItem(
            book_id=sku or fallback_id,
            source="fahasa",
            title=detail_title,
            author=find_metadata(metadata, "tac gia", "author"),
            publisher=find_metadata(metadata, "nha xuat ban", "nxb", "publisher"),
            language_group=category.get("language_group"),
            main_category=main_category or config_main_category(category),
            sub_category=(
                sub_category
                or find_metadata(metadata, "nhom san pham", "category")
                or config_sub_category(category)
            ),
            price=price_val,
            original_price=orig_price_val,
            discount_rate=discount_val,
            rating=first_not_none(rating_value, rating_from_response(response)),
            review_count=first_not_none(review_count, review_count_from_response(response)),
            sold_count=first_not_none(sold_count_from_response(response), 0),
            publish_year=find_metadata(metadata, "nam xb", "nam xuat ban", "publish year"),
            page_count=find_metadata(metadata, "so trang", "number of pages"),
            url=detail_url,
        )
