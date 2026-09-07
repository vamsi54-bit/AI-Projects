from pathlib import Path

from torchvision.datasets import ImageFolder

from ml.src.transforms import (
    get_evaluation_transforms,
    get_train_transforms,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "ml" / "data" / "raw"


def find_directory(name):
    directory = next(
        (
            path
            for path in RAW_DATA_DIR.rglob(name)
            if path.is_dir()
        ),
        None,
    )

    if directory is None:
        raise FileNotFoundError(
            f"Could not find '{name}' inside {RAW_DATA_DIR}"
        )

    return directory


def load_datasets(image_size=224):
    train_directory = find_directory("train")
    test_directory = find_directory("test")

    train_dataset = ImageFolder(
        root=train_directory,
        transform=get_train_transforms(image_size),
    )

    test_dataset = ImageFolder(
        root=test_directory,
        transform=get_evaluation_transforms(image_size),
    )

    if train_dataset.classes != test_dataset.classes:
        raise ValueError("Train and test classes do not match.")

    return train_dataset, test_dataset


if __name__ == "__main__":
    train_data, test_data = load_datasets()

    image, label = train_data[0]

    print("Classes:", train_data.classes)
    print("Class mapping:", train_data.class_to_idx)
    print("Training images:", len(train_data))
    print("Testing images:", len(test_data))
    print("Image tensor shape:", image.shape)
    print("First label:", label)