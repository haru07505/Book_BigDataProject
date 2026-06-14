"""Validate normalized book data and emit a small quality report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from normalize import FIELDS

def is_non_book_product(record: dict[str, Any]) -> bool:
    book_id = str(record.get("book_id") or "")

    return book_id in {
        "209389165",  # Bookmark
        "279296184",  # Lịch World Cup
        "279389953",  # Lịch World Cup
        "271198542",  # Thẻ VIP báo
        "2990436010637",  # Hệ Thống Tài Khoản
        "9786047957743",  # Hệ Thống Tài Khoản
        "9786043091199",
        "9786043092912",
        "9786049189524",
        "9786043092905",
        "9786049471315",
        "8936036316483",
        "8931805024118",
        "8931805024088",
        "8936036317572",
        "8931805024095",
        "8936214275151",
    }

def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for field in FIELDS:
        if field not in record:
            errors.append(f"missing field: {field}")

    if not record.get("book_id"):
        errors.append("book_id is required")

    if record.get("source") not in {"tiki", "fahasa"}:
        errors.append("source must be tiki or fahasa")

    if not record.get("title"):
        errors.append("title is required")
        
    if is_non_book_product(record):
        errors.append("non-book product")

    if not record.get("url"):
        errors.append("url is required")

    for field in ("price", "original_price", "discount_rate", "rating", "review_count", "sold_count"):
        value = record.get(field)
        if value is None or not isinstance(value, (int, float)):
            errors.append(f"{field} must be numeric")
        elif value < 0:
            errors.append(f"{field} must not be negative")

    price = record.get("price")
    if isinstance(price, (int, float)) and price <= 0:
        errors.append("price must be greater than 0")

    original_price = record.get("original_price")
    if isinstance(price, (int, float)) and isinstance(original_price, (int, float)):
        if original_price < price:
            errors.append("original_price must not be less than price")

    rating = record.get("rating")
    if isinstance(rating, (int, float)) and rating > 5:
        errors.append("rating must not exceed 5")

    publish_year = record.get("publish_year")
    if publish_year is not None:
        if not isinstance(publish_year, int):
            errors.append("publish_year must be integer or null")
        elif not (1800 <= publish_year <= 2026):
            errors.append("publish_year is out of valid range")

    page_count = record.get("page_count")
    if page_count is not None:
        if not isinstance(page_count, int):
            errors.append("page_count must be integer or null")
        elif page_count <= 0:
            errors.append("page_count must be greater than 0")

    return errors


def partition_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for record in records:
        errors = validate_record(record)
        if errors:
            rejected.append({"record": record, "errors": errors})
        else:
            valid.append(record)
    return valid, rejected


def build_report(total: int, valid: int, rejected: int) -> dict[str, int]:
    return {"total_records": total, "valid_records": valid, "rejected_records": rejected}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--valid-output", type=Path)
    parser.add_argument("--rejected-output", type=Path)
    parser.add_argument("--report-output", type=Path)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as file:
        records = json.load(file)
    valid, rejected = partition_records(records)
    report = build_report(len(records), len(valid), len(rejected))

    for path, payload in (
        (args.valid_output, valid),
        (args.rejected_output, rejected),
        (args.report_output, report),
    ):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
