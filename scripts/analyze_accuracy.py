import json
import sys
from collections import Counter


def analyze_file(input_file: str):
    print(f"Analyzing {input_file}...")

    total = 0
    with_tags = 0
    with_address = 0
    normalized_address = 0
    tag_counts = Counter()
    sources = Counter()

    with open(input_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                total += 1

                # Check Source
                src = data.get("source_title") or "Unknown"
                sources[src] += 1

                # Check Address
                if data.get("address_raw"):
                    with_address += 1
                    if data.get("pref_slug") and data.get("city_slug"):
                        normalized_address += 1

                # Check Tags
                parsed = data.get("parsed_json")
                if parsed and isinstance(parsed, dict):
                    tags = parsed.get("tags")
                    if tags and isinstance(tags, list) and len(tags) > 0:
                        with_tags += 1
                        for t in tags:
                            tag_counts[t] += 1

            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line[:50]}...")
                continue

    print("\n=== Analysis Report ===")
    print(f"Total Candidates: {total}")

    print("\n[Source Distribution]")
    for src, count in sources.most_common():
        print(f"  {src}: {count}")

    print("\n[Address Quality]")
    print(
        f"  Has Raw Address: {with_address} ({with_address / total * 100:.1f}%)"
        if total
        else "  Has Raw Address: 0"
    )
    print(
        f"  Normalized (Pref/City): {normalized_address} ({normalized_address / total * 100:.1f}%)"
        if total
        else "  Normalized: 0"
    )

    print("\n[Tag Extraction]")
    print(f"  Has Tags: {with_tags} ({with_tags / total * 100:.1f}%)" if total else "  Has Tags: 0")
    print(f"  Unique Tags Found: {len(tag_counts)}")
    print("  Top 20 Tags:")
    for tag, count in tag_counts.most_common(20):
        print(f"    {tag}: {count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/analyze_accuracy.py <jsonl_file>")
        sys.exit(1)

    analyze_file(sys.argv[1])
