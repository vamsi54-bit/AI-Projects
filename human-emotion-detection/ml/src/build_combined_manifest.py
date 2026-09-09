import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLEAN_DATA_DIR = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "clean_dataset"
)

RAFDB_ROOT = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "external"
    / "rafdb"
    / "DATASET"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "combined_dataset"
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

RAFDB_LABELS = {
    "1": "surprise",
    "2": "fear",
    "3": "disgust",
    "4": "happy",
    "5": "sad",
    "6": "angry",
    "7": "neutral",
}

MINORITY_CLASSES = {
    "angry",
    "disgust",
    "fear",
    "sad",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


def calculate_hash(path):
    hasher = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_manifest(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Manifest not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def normalize_ferplus_records(records):
    normalized = []

    for record in records:
        normalized.append(
            {
                "path": record["path"],
                "label": record["label"],
                "label_index": int(
                    record["label_index"]
                ),
                "split": record["split"],
                "sha256": record["sha256"],
                "source": "ferplus",
            }
        )

    return normalized


def scan_rafdb(split):
    split_directory = RAFDB_ROOT / split

    if not split_directory.exists():
        raise FileNotFoundError(
            f"RAF-DB split not found: "
            f"{split_directory}"
        )

    records = []
    corrupted = []

    for folder_name, label in RAFDB_LABELS.items():
        class_directory = (
            split_directory / folder_name
        )

        if not class_directory.exists():
            print(
                f"Warning: missing folder "
                f"{class_directory}"
            )
            continue

        for image_path in sorted(
            class_directory.rglob("*")
        ):
            if (
                not image_path.is_file()
                or image_path.suffix.lower()
                not in IMAGE_EXTENSIONS
            ):
                continue

            try:
                with Image.open(image_path) as image:
                    image.verify()

                records.append(
                    {
                        "path": image_path.relative_to(
                            PROJECT_ROOT
                        ).as_posix(),
                        "label": label,
                        "label_index": CLASSES.index(
                            label
                        ),
                        "split": split,
                        "sha256": calculate_hash(
                            image_path
                        ),
                        "source": "rafdb",
                    }
                )

            except Exception as error:
                corrupted.append(
                    {
                        "path": image_path.as_posix(),
                        "error": str(error),
                    }
                )

    return records, corrupted


def select_external_training_data(
    raf_train,
    protected_hashes,
):
    selected = []
    seen_hashes = set()
    duplicate_count = 0
    overlap_count = 0

    for record in raf_train:
        if record["label"] not in MINORITY_CLASSES:
            continue

        image_hash = record["sha256"]

        if image_hash in protected_hashes:
            overlap_count += 1
            continue

        if image_hash in seen_hashes:
            duplicate_count += 1
            continue

        seen_hashes.add(image_hash)
        selected.append(record)

    return (
        selected,
        duplicate_count,
        overlap_count,
    )


def clean_external_test(
    raf_test,
    protected_hashes,
):
    clean_records = []
    seen_hashes = set()
    removed_count = 0

    for record in raf_test:
        image_hash = record["sha256"]

        if (
            image_hash in protected_hashes
            or image_hash in seen_hashes
        ):
            removed_count += 1
            continue

        seen_hashes.add(image_hash)
        clean_records.append(record)

    return clean_records, removed_count


def save_manifest(records, path):
    fieldnames = [
        "path",
        "label",
        "label_index",
        "split",
        "sha256",
        "source",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(records)


def distribution(records):
    counts = Counter(
        record["label"]
        for record in records
    )

    return {
        label: counts[label]
        for label in CLASSES
    }


def imbalance_ratio(records):
    counts = distribution(records)
    values = [
        value
        for value in counts.values()
        if value > 0
    ]

    return round(
        max(values) / min(values),
        2,
    )


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fer_train = normalize_ferplus_records(
        load_manifest(
            CLEAN_DATA_DIR
            / "clean_train_manifest.csv"
        )
    )

    fer_test = normalize_ferplus_records(
        load_manifest(
            CLEAN_DATA_DIR
            / "clean_test_manifest.csv"
        )
    )

    print("Scanning RAF-DB training images...")
    raf_train, train_corrupted = scan_rafdb(
        "train"
    )

    print("Scanning RAF-DB testing images...")
    raf_test, test_corrupted = scan_rafdb(
        "test"
    )

    fer_hashes = {
        record["sha256"]
        for record in fer_train + fer_test
    }

    (
        selected_raf_train,
        raf_duplicates,
        fer_overlap,
    ) = select_external_training_data(
        raf_train,
        fer_hashes,
    )

    combined_train = (
        fer_train + selected_raf_train
    )

    protected_test_hashes = {
        record["sha256"]
        for record in combined_train + fer_test
    }

    clean_raf_test, raf_test_removed = (
        clean_external_test(
            raf_test,
            protected_test_hashes,
        )
    )

    combined_path = (
        OUTPUT_DIR
        / "combined_train_manifest.csv"
    )

    raf_test_path = (
        OUTPUT_DIR
        / "rafdb_test_manifest.csv"
    )

    save_manifest(
        combined_train,
        combined_path,
    )

    save_manifest(
        clean_raf_test,
        raf_test_path,
    )

    summary = {
        "ferplus_clean_train": len(
            fer_train
        ),
        "rafdb_training_images_scanned": len(
            raf_train
        ),
        "rafdb_minority_images_added": len(
            selected_raf_train
        ),
        "combined_training_images": len(
            combined_train
        ),
        "rafdb_duplicates_removed":
            raf_duplicates,
        "rafdb_ferplus_overlaps_removed":
            fer_overlap,
        "rafdb_test_images": len(
            clean_raf_test
        ),
        "rafdb_test_images_removed":
            raf_test_removed,
        "corrupted_images": (
            train_corrupted
            + test_corrupted
        ),
        "before_distribution":
            distribution(fer_train),
        "after_distribution":
            distribution(combined_train),
        "before_imbalance_ratio":
            imbalance_ratio(fer_train),
        "after_imbalance_ratio":
            imbalance_ratio(combined_train),
    }

    summary_path = (
        OUTPUT_DIR
        / "combined_summary.json"
    )

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nRAF-DB minority images added:")
    print(len(selected_raf_train))

    print("\nCombined training distribution:")

    for label, count in distribution(
        combined_train
    ).items():
        print(f"{label:>8}: {count}")

    print(
        "\nImbalance before:",
        summary["before_imbalance_ratio"],
    )
    print(
        "Imbalance after:",
        summary["after_imbalance_ratio"],
    )
    print(
        "FERPlus overlaps removed:",
        fer_overlap,
    )
    print(
        "Corrupted RAF-DB images:",
        len(train_corrupted)
        + len(test_corrupted),
    )

    print(f"\nManifest: {combined_path}")
    print(f"RAF test: {raf_test_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()