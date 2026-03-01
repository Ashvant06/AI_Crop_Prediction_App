import argparse
import json
from pathlib import Path

import pandas as pd


def _split_columns(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert generic CSV data into assistant knowledge JSON format.")
    parser.add_argument("--csv", required=True, help="Input CSV path")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--title-column", default="title", help="Column to map as title")
    parser.add_argument("--content-column", default="content", help="Column to map as content")
    parser.add_argument(
        "--tags-columns",
        default="tags,category,crop,topic",
        help="Comma-separated candidate columns used for tags",
    )
    parser.add_argument("--source-name", default="custom_dataset", help="Source name to stamp in output")
    parser.add_argument("--region", default="india", help="Default region field for output rows")
    parser.add_argument("--id-prefix", default="kbx", help="ID prefix for generated records")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    frame = pd.read_csv(csv_path)
    title_column = args.title_column
    content_column = args.content_column
    tag_columns = _split_columns(args.tags_columns)

    if title_column not in frame.columns:
        raise ValueError(f"Title column '{title_column}' not found in CSV")
    if content_column not in frame.columns:
        raise ValueError(f"Content column '{content_column}' not found in CSV")

    records: list[dict] = []
    for index, row in frame.iterrows():
        title = str(row.get(title_column, "")).strip()
        content = str(row.get(content_column, "")).strip()
        if not title or not content:
            continue

        tags: list[str] = []
        for column in tag_columns:
            if column not in frame.columns:
                continue
            value = str(row.get(column, "")).strip()
            if not value:
                continue
            pieces = [part.strip().lower() for part in value.replace(";", ",").split(",") if part.strip()]
            tags.extend(pieces)
        unique_tags = sorted(set(tags))

        records.append(
            {
                "id": f"{args.id_prefix}-{index + 1:04d}",
                "title": title,
                "content": content,
                "tags": unique_tags,
                "source": args.source_name,
                "region": args.region.lower(),
            }
        )

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Generated {len(records)} knowledge rows -> {output_path}")


if __name__ == "__main__":
    main()
