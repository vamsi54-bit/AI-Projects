from collections import Counter

import torch
from torch.optim import AdamW

from ml.src.balanced_training_utils import (
    create_balanced_criterion,
)
from ml.src.combined_dataloader import (
    CLASSES,
    create_combined_dataloaders,
)
from ml.src.high_accuracy_model import (
    create_high_accuracy_model,
)


def main():
    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("Device:", device)

    train_loader, _, _ = (
        create_combined_dataloaders(
            image_size=260,
            batch_size=8,
            validation_size=0.15,
            num_workers=0,
            random_seed=42,
            balance_power=0.75,
        )
    )

    class_counter = Counter(
        train_loader.dataset.targets
    )

    class_counts = [
        class_counter[index]
        for index in range(len(CLASSES))
    ]

    criterion, class_weights = (
        create_balanced_criterion(
            class_counts=class_counts,
            device=device,
            label_smoothing=0.05,
        )
    )

    # Fresh ImageNet-pretrained model.
    # Do not load the old emotion checkpoint.
    model = create_high_accuracy_model()
    model = model.to(device)
    model.train()

    optimizer = AdamW(
        [
            parameter
            for parameter in model.parameters()
            if parameter.requires_grad
        ],
        lr=1e-4,
        weight_decay=1e-4,
    )

    images, labels = next(
        iter(train_loader)
    )

    images = images.to(
        device,
        non_blocking=True,
    )

    labels = labels.to(
        device,
        non_blocking=True,
    )

    optimizer.zero_grad(
        set_to_none=True
    )

    logits = model(images)
    loss = criterion(logits, labels)

    loss.backward()
    optimizer.step()

    predictions = logits.argmax(dim=1)

    batch_accuracy = (
        predictions.eq(labels)
        .float()
        .mean()
        .item()
        * 100
    )

    print("\nClass counts:", class_counts)

    print("\nLoss weights:")

    for class_name, weight in zip(
        CLASSES,
        class_weights.tolist(),
    ):
        print(
            f"{class_name:>8}: "
            f"{weight:.4f}"
        )

    print("\nInput shape:", images.shape)
    print("Output shape:", logits.shape)
    print(f"Test loss: {loss.item():.4f}")
    print(
        f"Batch accuracy: "
        f"{batch_accuracy:.2f}%"
    )
    print(
        "\nForward and backward pass passed."
    )


if __name__ == "__main__":
    main()
    