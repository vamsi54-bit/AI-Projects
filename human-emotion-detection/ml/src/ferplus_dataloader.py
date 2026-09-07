from pathlib import Path

import torch
from PIL import Image
from sklearn.model_selection import train_test_split
from torch.utils.data import (
    DataLoader,
    Dataset,
    Subset,
    WeightedRandomSampler,
)

from ml.src.high_accuracy_transforms import (
    get_high_accuracy_evaluation_transforms,
    get_high_accuracy_train_transforms,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "ferplus"
    / "fer2013plus"
    / "fer2013"
)

CLASS_MAPPING = {
    "anger": "angry",
    "disgust": "disgust",
    "fear": "fear",
    "happiness": "happy",
    "neutral": "neutral",
    "sadness": "sad",
    "surprise": "surprise",
}

CLASSES = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise",
]


class FERPlusDataset(Dataset):
    def __init__(self, split, transform=None):
        self.transform = transform
        self.samples = []

        split_directory = DATASET_ROOT / split

        if not split_directory.exists():
            raise FileNotFoundError(
                f"Dataset split not found: {split_directory}"
            )

        for source_name, target_name in CLASS_MAPPING.items():
            class_directory = split_directory / source_name
            label = CLASSES.index(target_name)

            for image_path in sorted(class_directory.glob("*")):
                if image_path.suffix.lower() in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                }:
                    self.samples.append((image_path, label))

        self.targets = [label for _, label in self.samples]
        self.classes = CLASSES

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        image_path, label = self.samples[index]

        image = Image.open(image_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image, label


def create_ferplus_dataloaders(
    image_size=260,
    batch_size=32,
    validation_size=0.15,
    num_workers=0,
    random_seed=42,
    balanced_sampling=True,
):
    index_dataset = FERPlusDataset("train")
    indices = list(range(len(index_dataset)))

    train_indices, validation_indices = train_test_split(
        indices,
        test_size=validation_size,
        random_state=random_seed,
        stratify=index_dataset.targets,
    )

    augmented_dataset = FERPlusDataset(
        "train",
        transform=get_high_accuracy_train_transforms(image_size),
    )

    evaluation_dataset = FERPlusDataset(
        "train",
        transform=get_high_accuracy_evaluation_transforms(image_size),
    )

    test_dataset = FERPlusDataset(
        "test",
        transform=get_high_accuracy_evaluation_transforms(image_size),
    )

    train_dataset = Subset(
        augmented_dataset,
        train_indices,
    )

    validation_dataset = Subset(
        evaluation_dataset,
        validation_indices,
    )

    train_targets = torch.tensor(
        [index_dataset.targets[index] for index in train_indices],
        dtype=torch.long,
    )

    class_counts = torch.bincount(
        train_targets,
        minlength=len(CLASSES),
    ).float()

    generator = torch.Generator().manual_seed(random_seed)

    if balanced_sampling:
        class_weights = torch.sqrt(
            class_counts.max() / class_counts
        ).clamp(max=4.0)

        sample_weights = class_weights[train_targets]

        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True,
            generator=generator,
        )

        shuffle = False
    else:
        sampler = None
        shuffle = True

    loader_options = {
        "batch_size": batch_size,
        "num_workers": num_workers,
        "pin_memory": torch.cuda.is_available(),
        "persistent_workers": num_workers > 0,
    }

    train_loader = DataLoader(
        train_dataset,
        sampler=sampler,
        shuffle=shuffle,
        **loader_options,
    )

    validation_loader = DataLoader(
        validation_dataset,
        shuffle=False,
        **loader_options,
    )

    test_loader = DataLoader(
        test_dataset,
        shuffle=False,
        **loader_options,
    )

    print(
        "Training class counts:",
        class_counts.int().tolist(),
    )

    return train_loader, validation_loader, test_loader


if __name__ == "__main__":
    train_loader, validation_loader, test_loader = (
        create_ferplus_dataloaders(
            image_size=260,
            batch_size=32,
            num_workers=0,
        )
    )

    images, labels = next(iter(train_loader))

    print("Classes:", CLASSES)
    print("Training samples:", len(train_loader.dataset))
    print("Validation samples:", len(validation_loader.dataset))
    print("Testing samples:", len(test_loader.dataset))
    print("Batch shape:", images.shape)

    test_targets = torch.tensor(test_loader.dataset.targets)

    print(
        "Test distribution:",
        torch.bincount(
            test_targets,
            minlength=len(CLASSES),
        ).tolist(),
    )