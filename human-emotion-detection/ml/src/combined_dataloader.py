from __future__ import annotations

import csv
import random
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sklearn.model_selection import train_test_split
from torch.utils.data import (
    DataLoader,
    Dataset,
    WeightedRandomSampler,
)

from ml.src.class_aware_transforms import (
    get_evaluation_transform,
    get_minority_train_transform,
    get_normal_train_transform,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

COMBINED_MANIFEST = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "combined_dataset"
    / "combined_train_manifest.csv"
)

FERPLUS_TEST_MANIFEST = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "clean_dataset"
    / "clean_test_manifest.csv"
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


class ManifestEmotionDataset(Dataset):
    MINORITY_CLASSES = {
        "angry",
        "disgust",
        "fear",
        "sad",
    }

    def __init__(
        self,
        records,
        transform=None,
        minority_transform=None,
    ):
        self.records = records
        self.transform = transform
        self.minority_transform = (
            minority_transform
        )

        self.targets = [
            int(record["label_index"])
            for record in records
        ]

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]

        image_path = (
            PROJECT_ROOT / record["path"]
        )

        image = Image.open(
            image_path
        ).convert("RGB")

        if (
            record["label"]
            in self.MINORITY_CLASSES
            and self.minority_transform
            is not None
        ):
            image = self.minority_transform(
                image
            )

        elif self.transform is not None:
            image = self.transform(image)

        return image, int(record["label_index"])


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
        records = list(csv.DictReader(file))

    if not records:
        raise RuntimeError(
            f"Manifest is empty: {path}"
        )

    return records


def seed_worker(worker_id):
    worker_seed = (
        torch.initial_seed() % (2**32)
    )

    np.random.seed(worker_seed)
    random.seed(worker_seed)


def calculate_distribution(records):
    counts = Counter(
        int(record["label_index"])
        for record in records
    )

    return [
        counts[index]
        for index in range(len(CLASSES))
    ]


def create_tempered_sampler(
    records,
    balance_power=0.75,
):
    """
    balance_power:
        0.0 = normal dataset distribution
        1.0 = completely class-balanced sampling
        0.75 = strong but safer balancing
    """

    class_counts = Counter(
        int(record["label_index"])
        for record in records
    )

    sample_weights = []

    for record in records:
        label = int(record["label_index"])
        class_count = class_counts[label]

        weight = (
            1.0
            / (class_count ** balance_power)
        )

        sample_weights.append(weight)

    weights_tensor = torch.tensor(
        sample_weights,
        dtype=torch.double,
    )

    return WeightedRandomSampler(
        weights=weights_tensor,
        num_samples=len(records),
        replacement=True,
    )


def create_combined_dataloaders(
    image_size=260,
    batch_size=32,
    validation_size=0.15,
    num_workers=0,
    random_seed=42,
    balance_power=0.75,
):
    combined_records = load_manifest(
        COMBINED_MANIFEST
    )

    test_records = load_manifest(
        FERPLUS_TEST_MANIFEST
    )

    indices = list(
        range(len(combined_records))
    )

    # Preserve both emotion and dataset source
    # distributions in train and validation.
    stratification_labels = [
        (
            f"{record.get('source', 'ferplus')}_"
            f"{record['label_index']}"
        )
        for record in combined_records
    ]

    train_indices, validation_indices = (
        train_test_split(
            indices,
            test_size=validation_size,
            random_state=random_seed,
            stratify=stratification_labels,
        )
    )

    train_records = [
        combined_records[index]
        for index in train_indices
    ]

    validation_records = [
        combined_records[index]
        for index in validation_indices
    ]

    train_dataset = ManifestEmotionDataset(
    train_records,
    transform=get_normal_train_transform(
        image_size
    ),
    minority_transform=(
        get_minority_train_transform(
            image_size
        )
    ),
)

    validation_dataset = ManifestEmotionDataset(
    validation_records,
    transform=get_evaluation_transform(
        image_size
    ),
)

    test_dataset = ManifestEmotionDataset(
    test_records,
    transform=get_evaluation_transform(
        image_size
    ),
)
    sampler = create_tempered_sampler(
        train_records,
        balance_power=balance_power,
    )

    generator = torch.Generator()
    generator.manual_seed(random_seed)

    common_options = {
        "batch_size": batch_size,
        "num_workers": num_workers,
        "pin_memory": torch.cuda.is_available(),
        "worker_init_fn": seed_worker,
        "generator": generator,
        "persistent_workers": num_workers > 0,
    }

    train_loader = DataLoader(
        train_dataset,
        sampler=sampler,
        shuffle=False,
        drop_last=True,
        **common_options,
    )

    validation_loader = DataLoader(
        validation_dataset,
        shuffle=False,
        drop_last=False,
        **common_options,
    )

    test_loader = DataLoader(
        test_dataset,
        shuffle=False,
        drop_last=False,
        **common_options,
    )

    print(
        "Training distribution:",
        calculate_distribution(train_records),
    )

    print(
        "Validation distribution:",
        calculate_distribution(
            validation_records
        ),
    )

    print(
        "Testing distribution:",
        calculate_distribution(test_records),
    )

    return (
        train_loader,
        validation_loader,
        test_loader,
    )


def main():
    (
        train_loader,
        validation_loader,
        test_loader,
    ) = create_combined_dataloaders(
        image_size=260,
        batch_size=32,
        validation_size=0.15,
        num_workers=0,
        random_seed=42,
        balance_power=0.75,
    )

    images, labels = next(
        iter(train_loader)
    )

    print("\nClasses:", CLASSES)
    print(
        "Training samples:",
        len(train_loader.dataset),
    )
    print(
        "Validation samples:",
        len(validation_loader.dataset),
    )
    print(
        "Testing samples:",
        len(test_loader.dataset),
    )
    print("Batch image shape:", images.shape)
    print("Batch label shape:", labels.shape)
    print(
        "First batch distribution:",
        torch.bincount(
            labels,
            minlength=len(CLASSES),
        ).tolist(),
    )


if __name__ == "__main__":
    main()