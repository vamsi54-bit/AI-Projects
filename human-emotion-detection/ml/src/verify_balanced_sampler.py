from collections import Counter

from ml.src.combined_dataloader import (
    CLASSES,
    create_combined_dataloaders,
)


def main():
    train_loader, _, _ = (
        create_combined_dataloaders(
            image_size=260,
            batch_size=32,
            validation_size=0.15,
            num_workers=0,
            random_seed=42,
            balance_power=0.75,
        )
    )

    sampled_indices = list(
        iter(train_loader.sampler)
    )

    counts = Counter(
        train_loader.dataset.targets[index]
        for index in sampled_indices
    )

    sampled_distribution = [
        counts[index]
        for index in range(len(CLASSES))
    ]

    values = [
        count
        for count in sampled_distribution
        if count > 0
    ]

    ratio = max(values) / min(values)

    print("\nSampled epoch distribution:")

    for class_name, count in zip(
        CLASSES,
        sampled_distribution,
    ):
        print(f"{class_name:>8}: {count}")

    print(
        f"\nSampled imbalance ratio: "
        f"{ratio:.2f}x"
    )


if __name__ == "__main__":
    main()