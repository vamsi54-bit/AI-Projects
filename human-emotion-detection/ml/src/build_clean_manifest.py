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
    / "clean_dataset"
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


def calculate_hash(path):
    hasher = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def collect_images(split):
    split_directory = DATASET_ROOT / split
    records = []

    if not split_directory.exists():
        raise FileNotFoundError(
            f"Dataset split not found: {split_directory}"
        )

    for class_directory in sorted(
        split_directory.iterdir()
    ):
        if not class_directory.is_dir():
            continue

        class_name = CLASS_ALIASES.get(
            class_directory.name.lower()
        )

        if class_name is None:
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
                        "label": class_name,
                        "label_index": CLASSES.index(
                            class_name
                        ),
                        "split": split,
                        "sha256": calculate_hash(
                            image_path
                        ),
                    }
                )

            except Exception as error:
                print(
                    f"Skipping corrupted image: "
                    f"{image_path} — {error}"
                )

    return records


def remove_leakage_and_duplicates(
    train_records,
    test_records,
):
    test_hashes = {
        record["sha256"]
        for record in test_records
    }

    clean_train = []
    seen_train_hashes = set()

    leakage_removed = 0
    train_duplicates_removed = 0

    for record in train_records:
        image_hash = record["sha256"]

        # Never train on an image present in test
        if image_hash in test_hashes:
            leakage_removed += 1
            continue

        # Keep only one exact copy in training
        if image_hash in seen_train_hashes:
            train_duplicates_removed += 1
            continue

        seen_train_hashes.add(image_hash)
        clean_train.append(record)

    clean_test = []
    seen_test_hashes = set()
    test_duplicates_removed = 0

    for record in test_records:
        image_hash = record["sha256"]

        # Keep only one copy for strict evaluation
        if image_hash in seen_test_hashes:
            test_duplicates_removed += 1
            continue

        seen_test_hashes.add(image_hash)
        clean_test.append(record)

    statistics = {
        "leakage_train_images_removed":
            leakage_removed,
        "train_duplicates_removed":
            train_duplicates_removed,
        "test_duplicates_removed":
            test_duplicates_removed,
    }

    return clean_train, clean_test, statistics


def save_manifest(records, filename):
    output_path = OUTPUT_DIR / filename

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "path",
                "label",
                "label_index",
                "split",
                "sha256",
            ],
        )

        writer.writeheader()
        writer.writerows(records)

    return output_path


def get_distribution(records):
    counts = Counter(
        record["label"]
        for record in records
    )

    return {
        class_name: counts[class_name]
        for class_name in CLASSES
    }


def verify_clean_dataset(
    clean_train,
    clean_test,
):
    train_hashes = {
        record["sha256"]
        for record in clean_train
    }

    test_hashes = {
        record["sha256"]
        for record in clean_test
    }

    remaining_leakage = (
        train_hashes.intersection(test_hashes)
    )

    train_hash_groups = defaultdict(list)

    for record in clean_train:
        train_hash_groups[
            record["sha256"]
        ].append(record)

    remaining_duplicates = sum(
        1
        for records in train_hash_groups.values()
        if len(records) > 1
    )

    if remaining_leakage:
        raise RuntimeError(
            "Leakage still exists after cleaning."
        )

    if remaining_duplicates:
        raise RuntimeError(
            "Training duplicates still exist."
        )

    print("Clean dataset verification passed.")


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Scanning training dataset...")
    train_records = collect_images("train")

    print("Scanning testing dataset...")
    test_records = collect_images("test")

    clean_train, clean_test, statistics = (
        remove_leakage_and_duplicates(
            train_records,
            test_records,
        )
    )

    verify_clean_dataset(
        clean_train,
        clean_test,
    )

    train_manifest = save_manifest(
        clean_train,
        "clean_train_manifest.csv",
    )

    test_manifest = save_manifest(
        clean_test,
        "clean_test_manifest.csv",
    )

    summary = {
        "original_train_images": len(
            train_records
        ),
        "clean_train_images": len(
            clean_train
        ),
        "original_test_images": len(
            test_records
        ),
        "clean_test_images": len(
            clean_test
        ),
        **statistics,
        "clean_train_distribution":
            get_distribution(clean_train),
        "clean_test_distribution":
            get_distribution(clean_test),
        "important": (
            "No original image was deleted. "
            "Training must use the clean manifest."
        ),
    }

    summary_path = (
        OUTPUT_DIR
        / "cleaning_summary.json"
    )

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nCleaning completed.")
    print(
        "Original training images:",
        len(train_records),
    )
    print(
        "Clean training images:",
        len(clean_train),
    )
    print(
        "Leakage images removed:",
        statistics[
            "leakage_train_images_removed"
        ],
    )
    print(
        "Training duplicates removed:",
        statistics[
            "train_duplicates_removed"
        ],
    )
    print(
        "Test duplicates removed:",
        statistics[
            "test_duplicates_removed"
        ],
    )

    print("\nClean training distribution:")

    for class_name, count in get_distribution(
        clean_train
    ).items():
        print(f"{class_name:>8}: {count}")

    print(f"\nTrain manifest: {train_manifest}")
    print(f"Test manifest: {test_manifest}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()