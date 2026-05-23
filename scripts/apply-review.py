#!/usr/bin/env python3
"""Apply approved typos corrections from a review JSONL file."""

from pathlib import Path
import json
import os
import sys
import tempfile


def die(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def normalize_status(value):
    if value is None:
        return ""
    text = str(value).replace("_", " ").replace("-", " ")
    return " ".join(text.split()).upper()


def parse_optional_int(value):
    if value is None:
        return None, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, int):
        return value, True
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text), True
    return None, False


def parse_corrections(value):
    if value is None:
        return [], True
    if not isinstance(value, list):
        return [], False
    for item in value:
        if not isinstance(item, str) or not item:
            return [], False
    return value, True


def resolve_target_path(review_path, target):
    candidate = Path(str(target))
    if not candidate.is_absolute():
        candidate = review_path.parent / candidate
    return str(candidate.resolve(strict=False))


def line_starts(data):
    starts = [0]
    for idx, byte in enumerate(data):
        if byte == 10:
            starts.append(idx + 1)
    return starts


def locate_offset(data, line_num, needle, occurrence_index=None):
    if line_num is None or line_num < 1:
        return None
    starts = line_starts(data)
    if line_num > len(starts):
        return None
    start = starts[line_num - 1]
    end = starts[line_num] if line_num < len(starts) else len(data)
    segment = data[start:end]
    positions = []
    cursor = segment.find(needle)
    while cursor != -1:
        positions.append(cursor)
        cursor = segment.find(needle, cursor + 1)

    if not positions:
        return None

    if occurrence_index is None:
        if len(positions) > 1:
            raise ValueError("multiple occurrences on the same line")
        return start + positions[0]

    if occurrence_index < 1:
        raise ValueError("occurrence_index must be >= 1")
    if occurrence_index > len(positions):
        return None
    return start + positions[occurrence_index - 1]


def load_review(path):
    accepted = []
    skipped = 0
    errors = []

    try:
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
                if not isinstance(file_path, str) or not file_path.strip():
                    errors.append(f"{path}:{idx}: missing or invalid path")
                    continue
                if not isinstance(typo, str) or not typo:
                    errors.append(f"{path}:{idx}: missing path or typo")
                    continue
                resolved_path = resolve_target_path(path, file_path)

                corrections, corrections_ok = parse_corrections(item.get("corrections"))
                if not corrections_ok:
                    errors.append(f"{path}:{idx}: corrections must be a list of non-empty strings")
                    continue

                custom = item.get("correction")
                if custom is None:
                    custom = ""
                elif not isinstance(custom, str):
                    errors.append(f"{path}:{idx}: correction must be a string")
                    continue

                line_num, line_num_ok = parse_optional_int(item.get("line_num"))
                byte_offset, byte_offset_ok = parse_optional_int(item.get("byte_offset"))
                occurrence_index, occurrence_index_ok = parse_optional_int(item.get("occurrence_index"))
                if not line_num_ok:
                    errors.append(f"{path}:{idx}: line_num must be an integer")
                if not byte_offset_ok:
                    errors.append(f"{path}:{idx}: byte_offset must be an integer")
                if not occurrence_index_ok:
                    errors.append(f"{path}:{idx}: occurrence_index must be an integer")
                if not line_num_ok or not byte_offset_ok or not occurrence_index_ok:
                    continue

                if status == "CUSTOM":
                    if not custom.strip():
                        errors.append(f"{path}:{idx}: CUSTOM requires correction")
                        continue
                    correction = custom
                else:
                    if custom.strip():
                        correction = custom
                    elif corrections:
                        correction = corrections[0]
                    else:
                        errors.append(f"{path}:{idx}: no correction available")
                        continue

                if byte_offset is None and line_num is None:
                    errors.append(f"{path}:{idx}: missing locator; provide byte_offset or line_num")
                    continue
                if occurrence_index is not None and occurrence_index < 1:
                    errors.append(f"{path}:{idx}: occurrence_index must be >= 1")
                    continue

                accepted.append(
                    {
                        "path": resolved_path,
                        "typo": typo,
                        "correction": correction,
                        "line_num": line_num,
                        "byte_offset": byte_offset,
                        "occurrence_index": occurrence_index,
                    }
                )
    except OSError as exc:
        die(f"cannot read review file '{path}': {exc}")

    if errors:
        die("\n".join(errors))

    return accepted, skipped


def build_plan(changes):
    errors = []
    plans = {}

    for path, items in changes.items():
        file_path = Path(path)
        if not file_path.is_file():
            errors.append(f"Missing file: {path}")
            continue
        try:
            data = file_path.read_bytes()
        except OSError as exc:
            errors.append(f"{path}: unable to read file: {exc}")
            continue
        replacements = []

        for item in items:
            typo_bytes = item["typo"].encode("utf-8")
            correction_bytes = item["correction"].encode("utf-8")
            offset = None

            if item["byte_offset"] is not None:
                offset = item["byte_offset"]
                if offset < 0:
                    errors.append(f"{path}: byte_offset must be >= 0 for '{item['typo']}'")
                    continue
                # typos outputs byte_offset relative to the line start when line_num is present
                if item["line_num"] is not None:
                    starts = line_starts(data)
                    if item["line_num"] <= len(starts):
                        offset = starts[item["line_num"] - 1] + offset
                if data[offset:offset + len(typo_bytes)] != typo_bytes:
                    errors.append(f"{path}: byte_offset mismatch for '{item['typo']}'")
                    continue
            else:
                try:
                    offset = locate_offset(
                        data,
                        item["line_num"],
                        typo_bytes,
                        item["occurrence_index"],
                    )
                except ValueError as exc:
                    errors.append(
                        f"{path}: {exc} for '{item['typo']}' on line {item['line_num']}; "
                        "keep byte_offset from export or set occurrence_index"
                    )
                    continue
                if offset is None:
                    if item["occurrence_index"] is not None:
                        errors.append(
                            f"{path}: unable to locate occurrence {item['occurrence_index']} "
                            f"of '{item['typo']}' on line {item['line_num']}"
                        )
                    else:
                        errors.append(
                            f"{path}: unable to locate '{item['typo']}' on line {item['line_num']}"
                        )
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
        die("\n".join(errors))

    return plans


def apply_plan(plans):
    staged_paths = {}

    for path, (data, replacements) in plans.items():
        updated = data
        for offset, length, correction in replacements:
            updated = updated[:offset] + correction + updated[offset + length:]

        target = Path(path)
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                delete=False,
                dir=target.parent,
                prefix=f".{target.name}.typos-skill-",
                suffix=".tmp",
            ) as handle:
                handle.write(updated)
                tmp_file = Path(handle.name)
        except OSError as exc:
            if tmp_file is not None:
                try:
                    tmp_file.unlink(missing_ok=True)
                except OSError:
                    pass
            for staged in staged_paths.values():
                try:
                    staged.unlink(missing_ok=True)
                except OSError:
                    pass
            die(f"{path}: failed to stage updated file: {exc}")

        staged_paths[path] = tmp_file

    committed = []
    try:
        for path, tmp_file in staged_paths.items():
            os.replace(tmp_file, path)
            committed.append(path)
    except OSError as exc:
        rollback_errors = []

        for path in reversed(committed):
            original_data, _ = plans[path]
            try:
                Path(path).write_bytes(original_data)
            except OSError as rollback_exc:
                rollback_errors.append(f"{path}: rollback failed: {rollback_exc}")

        for path, tmp_file in staged_paths.items():
            if path in committed:
                continue
            try:
                tmp_file.unlink(missing_ok=True)
            except OSError:
                pass

        detail = f"failed to commit staged changes: {exc}"
        if rollback_errors:
            detail = f"{detail}; rollback errors: {'; '.join(rollback_errors)}"
        die(detail)


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
