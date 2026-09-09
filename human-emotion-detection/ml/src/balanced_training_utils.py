import torch
from torch import nn


def calculate_class_weights(
    class_counts,
    power=0.25,
    minimum=0.70,
    maximum=1.60,
    device="cpu",
):
    counts = torch.tensor(
        class_counts,
        dtype=torch.float32,
    )

    if torch.any(counts <= 0):
        raise ValueError(
            "Every class must contain samples."
        )

    largest_count = counts.max()

    weights = (
        largest_count / counts
    ).pow(power)

    weights = weights / weights.mean()

    weights = torch.clamp(
        weights,
        min=minimum,
        max=maximum,
    )

    weights = weights / weights.mean()

    return weights.to(device)


def create_balanced_criterion(
    class_counts,
    device,
    label_smoothing=0.05,
):
    weights = calculate_class_weights(
        class_counts=class_counts,
        power=0.25,
        minimum=0.70,
        maximum=1.60,
        device=device,
    )

    criterion = nn.CrossEntropyLoss(
        weight=weights,
        label_smoothing=label_smoothing,
    )

    return criterion, weights