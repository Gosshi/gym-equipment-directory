import json
from collections import Counter


def analyze_content(file_path):
    print(f"Analyzing {file_path}...")

    with open(file_path, encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    total = len(lines)
    print(f"Total records: {total}")

    # 1. Suspicious Names (News/Announcements)
    suspicious_keywords = [
        "お知らせ",
        "休館",
        "閉鎖",
        "について",
        "募集",
        "案内",
        "不可",
        "中止",
        "更新",
    ]
    suspicious_entries = []

    # 2. Duplicate Addresses
    address_counts = Counter()

    # 3. Generic Names
    generic_names = ["トレーニング室", "トレーニングルーム", "スポーツセンター", "体育館"]
    generic_entries = []

    # 4. Empty Names
    empty_names = []

    for entry in lines:
        name = entry.get("name_raw") or ""
        address = entry.get("address_raw") or ""
        parsed = entry.get("parsed_json") or {}
        normalized_address = parsed.get("address")

        # Check suspicious
        if any(k in name for k in suspicious_keywords):
            suspicious_entries.append((entry["id"], name, entry.get("source_title")))

        # Check duplicates (prefer normalized, fallback to raw)
        addr_key = normalized_address or address
        if addr_key:
            address_counts[addr_key] += 1

        # Check generic
        if name in generic_names:
            generic_entries.append((entry["id"], name, entry.get("source_title")))

        # Check empty
        if not name.strip():
            empty_names.append(entry["id"])

    print("\n--- 1. Potential Non-Gym Entries (News/Announcements) ---")
    print(f"Found {len(suspicious_entries)} entries.")
    for id, name, source in suspicious_entries[:10]:
        print(f"  ID {id}: {name} ({source})")
    if len(suspicious_entries) > 10:
        print(f"  ... and {len(suspicious_entries) - 10} more.")

    print("\n--- 2. Duplicate Addresses (Potential Duplicate Scrapes) ---")
    duplicates = {k: v for k, v in address_counts.items() if v > 1}
    print(f"Found {len(duplicates)} addresses with multiple entries.")
    sorted_dupes = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)
    for addr, count in sorted_dupes[:10]:
        print(f"  {addr}: {count} entries")

    print("\n--- 3. Generic Names (Might need parent facility name) ---")
    print(f"Found {len(generic_entries)} entries with purely generic names.")
    for id, name, source in generic_entries[:10]:
        print(f"  ID {id}: {name} ({source})")

    print("\n--- 4. Empty Names ---")
    print(f"Found {len(empty_names)} entries with empty names.")


if __name__ == "__main__":
    analyze_content("candidates_prod.jsonl")
