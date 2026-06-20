"""Merge raw crawler outputs, normalize records and write books_clean.csv."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from normalize import FIELDS, normalize_record
from validate_data import build_report, partition_records


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUTS = [
    PROJECT_ROOT / "data" / "raw" / "tiki_books.json",
    PROJECT_ROOT / "data" / "raw" / "fahasa_books.json",
]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "clean" / "books_clean.csv"
DEFAULT_REJECTED = PROJECT_ROOT / "data" / "clean" / "books_rejected.json"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "clean" / "quality_report.json"


def read_records(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            print(f"Skip missing input: {path}")
            continue
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        records.extend(payload)
    return records


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (str(record["source"]), str(record["book_id"]))
        unique[key] = record
    return list(unique.values())


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)


def remove_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) != "Mn"
    )
    return text.replace("đ", "d").replace("Đ", "D")

def normalize_key(value: Any) -> str:
    text = "" if value is None else str(value)

    text = remove_accents(text)
    text = text.lower()

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)

    return text.strip()


def normalize_author_tokens(value: Any) -> set[str]:
    text = normalize_key(value)
    if not text:
        return set()
    parts = re.split(r"[,&;/]|\band\b|\bva\b|\bvà\b|\bwith\b|\+", text)
    tokens: set[str] = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        tokens.update(re.findall(r"[a-z0-9]{3,}", part))
    return tokens


def enrich_publish_year_from_fahasa(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fahasa_index_by_title: dict[str, list[tuple[set[str], int]]] = {}
    fahasa_title_year: dict[str, int | None] = {}

    for record in records:
        if record.get("source") != "fahasa":
            continue

        publish_year = record.get("publish_year")
        if publish_year is None:
            continue

        title_key = normalize_key(record.get("title"))
        if not title_key:
            continue

        author_tokens = normalize_author_tokens(record.get("author"))
        fahasa_index_by_title.setdefault(title_key, []).append((author_tokens, publish_year))

        if title_key not in fahasa_title_year:
            fahasa_title_year[title_key] = publish_year
        elif fahasa_title_year[title_key] != publish_year:
            fahasa_title_year[title_key] = None

    for record in records:
        if record.get("source") != "tiki":
            continue

        if record.get("publish_year") is not None:
            continue

        title_key = normalize_key(record.get("title"))
        if not title_key:
            continue

        candidates = fahasa_index_by_title.get(title_key)
        if not candidates:
            continue

        author_tokens = normalize_author_tokens(record.get("author"))
        matched_year = None

        if author_tokens:
            for tokens, year in candidates:
                if tokens and tokens & author_tokens:
                    matched_year = year
                    break

        if matched_year is None:
            if len(candidates) == 1:
                matched_year = candidates[0][1]
            else:
                title_year = fahasa_title_year.get(title_key)
                if title_year is not None:
                    matched_year = title_year

        if matched_year is not None:
            record["publish_year"] = matched_year

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, dest="inputs")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rejected-output", type=Path, default=DEFAULT_REJECTED)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    raw_records = read_records(args.inputs or DEFAULT_INPUTS)
    normalized = [normalize_record(record) for record in raw_records]
    normalized = [record for record in normalized if record is not None]
    normalized = enrich_publish_year_from_fahasa(normalized)
    validated, rejected = partition_records(normalized)
    valid = deduplicate(validated)
    report = build_report(len(normalized), len(valid), len(rejected))
    report["duplicate_records"] = len(validated) - len(valid)

    write_csv(args.output, valid)
    args.rejected_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    with args.rejected_output.open("w", encoding="utf-8") as file:
        json.dump(rejected, file, ensure_ascii=False, indent=2)
    with args.report_output.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()