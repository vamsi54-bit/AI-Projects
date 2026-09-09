from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_ROOT = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "ferplus"
    / "fer2013plus"
    / "fer2013"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "class_balance_audit"
)

CLASSES = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise",
]

CLASS_ALIASES = {
    "anger": "angry",
    "angry": "angry",
    "disgust": "disgust",
    "fear": "fear",
    "happiness": "happy",
    "happy": "happy",
    "neutral": "neutral",
    "sadness": "sad",
    "sad": "sad",
    "surprise": "surprise",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


def calculate_hash(image_path: Path) -> str:
    hasher = hashlib.sha256()

    with image_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def get_relative_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def scan_dataset():
    records = []
    corrupted_files = []
    ignored_folders = Counter()

    for split in ["train", "test"]:
        split_directory = DATASET_ROOT / split

        if not split_directory.exists():
            raise FileNotFoundError(
                f"Dataset split not found: {split_directory}"
            )

        for class_directory in sorted(split_directory.iterdir()):
            if not class_directory.is_dir():
                continue

            image_paths = [
                path
                for path in class_directory.rglob("*")
                if path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
            ]

            canonical_class = CLASS_ALIASES.get(
                class_directory.name.lower()
            )

            # contempt and unsupported folders are ignored
            if canonical_class is None:
                ignored_folders[
                    f"{split}/{class_directory.name}"
                ] += len(image_paths)
                continue

            for image_path in image_paths:
                try:
                    with Image.open(image_path) as image:
                        width, height = image.size
                        image.verify()

                    records.append(
                        {
                            "split": split,
                            "class": canonical_class,
                            "path": get_relative_path(image_path),
                            "sha256": calculate_hash(image_path),
                            "width": width,
                            "height": height,
                        }
                    )

                except Exception as error:
                    corrupted_files.append(
                        {
                            "split": split,
                            "class": canonical_class,
                            "path": get_relative_path(image_path),
                            "error": (
                                f"{type(error).__name__}: {error}"
                            ),
                        }
                    )

    return records, corrupted_files, ignored_folders


def save_class_counts(counts):
    output_path = OUTPUT_DIR / "class_counts.csv"

    train_total = sum(counts["train"].values())
    largest_count = max(
        counts["train"][class_name]
        for class_name in CLASSES
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "class",
                "train",
                "test",
                "total",
                "train_share_percent",
                "train_vs_largest_percent",
            ],
        )

        writer.writeheader()

        for class_name in CLASSES:
            train_count = counts["train"][class_name]
            test_count = counts["test"][class_name]

            writer.writerow(
                {
                    "class": class_name,
                    "train": train_count,
                    "test": test_count,
                    "total": train_count + test_count,
                    "train_share_percent": round(
                        100 * train_count / max(train_total, 1),
                        2,
                    ),
                    "train_vs_largest_percent": round(
                        100 * train_count / max(largest_count, 1),
                        2,
                    ),
                }
            )


def save_duplicate_files(duplicate_groups):
    output_path = OUTPUT_DIR / "duplicate_files.csv"

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "sha256",
                "split",
                "class",
                "path",
            ],
        )

        writer.writeheader()

        for image_hash, items in sorted(
            duplicate_groups.items()
        ):
            for item in items:
                writer.writerow(
                    {
                        "sha256": image_hash,
                        "split": item["split"],
                        "class": item["class"],
                        "path": item["path"],
                    }
                )


def main():
    print("Auditing FERPlus dataset...")
    print("No images will be modified or deleted.\n")

    records, corrupted_files, ignored_folders = (
        scan_dataset()
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    counts = {
        "train": Counter(),
        "test": Counter(),
    }

    files_by_hash = defaultdict(list)

    for record in records:
        counts[record["split"]][record["class"]] += 1
        files_by_hash[record["sha256"]].append(record)

    duplicate_groups = {
        image_hash: items
        for image_hash, items in files_by_hash.items()
        if len(items) > 1
    }

    train_test_leakage = {
        image_hash: items
        for image_hash, items in duplicate_groups.items()
        if len({item["split"] for item in items}) > 1
    }

    cross_label_conflicts = {
        image_hash: items
        for image_hash, items in duplicate_groups.items()
        if len({item["class"] for item in items}) > 1
    }

    train_counts = [
        counts["train"][class_name]
        for class_name in CLASSES
    ]

    nonzero_counts = [
        count for count in train_counts if count > 0
    ]

    largest_class = max(
        CLASSES,
        key=lambda name: counts["train"][name],
    )

    smallest_class = min(
        CLASSES,
        key=lambda name: counts["train"][name],
    )

    imbalance_ratio = (
        max(train_counts)
        / max(min(nonzero_counts, default=1), 1)
    )

    report = {
        "dataset_root": DATASET_ROOT.as_posix(),
        "valid_images": len(records),
        "class_counts": {
            split: {
                class_name: counts[split][class_name]
                for class_name in CLASSES
            }
            for split in ["train", "test"]
        },
        "imbalance": {
            "largest_class": largest_class,
            "largest_count": counts["train"][largest_class],
            "smallest_class": smallest_class,
            "smallest_count": counts["train"][smallest_class],
            "largest_to_smallest_ratio": round(
                imbalance_ratio,
                2,
            ),
        },
        "corrupted_files": corrupted_files,
        "ignored_folders": dict(ignored_folders),
        "duplicate_group_count": len(
            duplicate_groups
        ),
        "train_test_leakage_count": len(
            train_test_leakage
        ),
        "cross_label_conflict_count": len(
            cross_label_conflicts
        ),
        "train_test_leakage": train_test_leakage,
        "cross_label_conflicts": cross_label_conflicts,
    }

    report_path = OUTPUT_DIR / "audit_report.json"

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    save_class_counts(counts)
    save_duplicate_files(duplicate_groups)

    print("Training class counts:")

    for class_name in CLASSES:
        print(
            f"{class_name:>8}: "
            f"{counts['train'][class_name]}"
        )

    print(
        f"\nLargest class: {largest_class} "
        f"({counts['train'][largest_class]})"
    )

    print(
        f"Smallest class: {smallest_class} "
        f"({counts['train'][smallest_class]})"
    )

    print(f"Imbalance ratio: {imbalance_ratio:.2f}x")
    print(f"Corrupted images: {len(corrupted_files)}")
    print(f"Duplicate groups: {len(duplicate_groups)}")

    print(
        "Train/test leakage groups: "
        f"{len(train_test_leakage)}"
    )

    print(
        "Cross-label conflicts: "
        f"{len(cross_label_conflicts)}"
    )

    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()