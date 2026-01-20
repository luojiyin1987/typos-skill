#!/usr/bin/env python3
"""Apply approved typos corrections from a review JSONL file."""

from pathlib import Path
import json
import sys


def die(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def normalize_status(value):
    if value is None:
        return ""
    text = str(value).replace("_", " ").replace("-", " ")
    return " ".join(text.split()).upper()


def parse_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def line_starts(data):
    starts = [0]
    for idx, byte in enumerate(data):
        if byte == 10:
            starts.append(idx + 1)
    return starts


def locate_offset(data, line_num, needle):
    if line_num is None or line_num < 1:
        return None
    starts = line_starts(data)
    if line_num > len(starts):
        return None
    start = starts[line_num - 1]
    end = starts[line_num] if line_num < len(starts) else len(data)
    segment = data[start:end]
    first = segment.find(needle)
    if first == -1:
        return None
    if segment.find(needle, first + 1) != -1:
        raise ValueError("multiple occurrences on the same line")
    return start + first


def load_review(path):
    accepted = []
    skipped = 0
    errors = []

    with path.open("r", encoding="utf-8") as handle:
        for idx, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{idx}: invalid JSON: {exc}")
                continue

            status = normalize_status(item.get("status"))
            if not status:
                errors.append(f"{path}:{idx}: missing status")
                continue

            if status in {"FALSE POSITIVE", "FALSE POSITIVE?", "FALSEPOSITIVE", "SKIP", "REJECT"}:
                skipped += 1
                continue

            if status not in {"ACCEPT", "ACCEPT CORRECT", "CUSTOM"}:
                errors.append(f"{path}:{idx}: unsupported status: {item.get('status')}")
                continue

            file_path = item.get("path")
            typo = item.get("typo")
            if not file_path or not typo:
                errors.append(f"{path}:{idx}: missing path or typo")
                continue

            corrections = item.get("corrections") or []
            custom = item.get("correction")

            if status == "CUSTOM":
                if not custom:
                    errors.append(f"{path}:{idx}: CUSTOM requires correction")
                    continue
                correction = custom
            else:
                if custom:
                    correction = custom
                elif corrections:
                    correction = corrections[0]
                else:
                    errors.append(f"{path}:{idx}: no correction available")
                    continue

            accepted.append(
                {
                    "path": file_path,
                    "typo": typo,
                    "correction": correction,
                    "line_num": parse_int(item.get("line_num")),
                    "byte_offset": parse_int(item.get("byte_offset")),
                }
            )

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        sys.exit(1)

    return accepted, skipped


def build_plan(changes):
    errors = []
    plans = {}

    for path, items in changes.items():
        file_path = Path(path)
        if not file_path.is_file():
            errors.append(f"Missing file: {path}")
            continue
        data = file_path.read_bytes()
        replacements = []

        for item in items:
            typo_bytes = item["typo"].encode("utf-8")
            correction_bytes = item["correction"].encode("utf-8")
            offset = None

            if item["byte_offset"] is not None:
                offset = item["byte_offset"]
                if data[offset:offset + len(typo_bytes)] != typo_bytes:
                    errors.append(f"{path}: byte_offset mismatch for '{item['typo']}'")
                    continue
            else:
                try:
                    offset = locate_offset(data, item["line_num"], typo_bytes)
                except ValueError as exc:
                    errors.append(f"{path}: {exc} for '{item['typo']}' on line {item['line_num']}")
                    continue
                if offset is None:
                    errors.append(f"{path}: unable to locate '{item['typo']}' on line {item['line_num']}")
                    continue

            replacements.append((offset, len(typo_bytes), correction_bytes))

        replacements.sort(key=lambda entry: entry[0], reverse=True)
        for idx in range(len(replacements) - 1):
            current = replacements[idx]
            next_item = replacements[idx + 1]
            if current[0] < next_item[0] + next_item[1]:
                errors.append(f"{path}: overlapping replacements detected")
                break

        plans[path] = (data, replacements)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        sys.exit(1)

    return plans


def apply_plan(plans):
    for path, (data, replacements) in plans.items():
        for offset, length, correction in replacements:
            data = data[:offset] + correction + data[offset + length:]
        Path(path).write_bytes(data)


def main():
    if len(sys.argv) != 2:
        die("Usage: apply-review.py <review.jsonl>")

    review_path = Path(sys.argv[1])
    if not review_path.is_file():
        die(f"Review file not found: {review_path}")

    accepted, skipped = load_review(review_path)
    if not accepted:
        print("No accepted corrections to apply.")
        if skipped:
            print(f"Skipped {skipped} items marked as false positives.")
        return 0

    changes = {}
    for item in accepted:
        changes.setdefault(item["path"], []).append(item)

    plans = build_plan(changes)
    apply_plan(plans)

    total = len(accepted)
    print(f"Applied {total} corrections across {len(changes)} files.")
    if skipped:
        print(f"Skipped {skipped} items marked as false positives.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
