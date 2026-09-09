import json
from collections import Counter
from pathlib import Path

import torch
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    recall_score,
)
from sklearn.model_selection import (
    train_test_split,
)

from ml.src.ferplus_dataloader import (
    CLASSES,
    create_ferplus_dataloaders,
)
from ml.src.high_accuracy_model import (
    create_high_accuracy_model,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "ml/models/checkpoints/"
    / "best_high_accuracy_model.pt"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml/models/exported/"
    / "class_bias_calibration.json"
)


@torch.no_grad()
def collect_logits(model, loader, device):
    logits_list = []
    labels_list = []

    model.eval()

    for images, labels in loader:
        images = images.to(device)

        logits_list.append(
            model(images).cpu()
        )

        labels_list.append(labels.cpu())

    return (
        torch.cat(logits_list),
        torch.cat(labels_list),
    )


def calculate_metrics(
    logits,
    labels,
    bias,
):
    predictions = (
        logits + bias
    ).argmax(dim=1)

    accuracy = accuracy_score(
        labels.numpy(),
        predictions.numpy(),
    )

    macro_f1 = f1_score(
        labels.numpy(),
        predictions.numpy(),
        average="macro",
        zero_division=0,
    )

    recalls = recall_score(
        labels.numpy(),
        predictions.numpy(),
        average=None,
        labels=list(range(len(CLASSES))),
        zero_division=0,
    )

    return accuracy, macro_f1, recalls


def fit_bias(
    logits,
    labels,
    regularization,
):
    counts = Counter(labels.tolist())

    class_counts = torch.tensor(
        [
            counts[index]
            for index in range(len(CLASSES))
        ],
        dtype=torch.float32,
    )

    weights = (
        class_counts.max() / class_counts
    ).sqrt()

    weights = weights / weights.mean()

    bias = torch.nn.Parameter(
        torch.zeros(len(CLASSES))
    )

    optimizer = torch.optim.Adam(
        [bias],
        lr=0.02,
    )

    for _ in range(400):
        optimizer.zero_grad()

        loss = torch.nn.functional.cross_entropy(
            logits + bias,
            labels,
            weight=weights,
            label_smoothing=0.02,
        )

        loss = (
            loss
            + regularization
            * bias.pow(2).mean()
        )

        loss.backward()
        optimizer.step()

        with torch.no_grad():
            bias.subtract_(bias.mean())
            bias.clamp_(-0.50, 0.50)

    return bias.detach()


def main():
    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("Device:", device)

    _, validation_loader, _ = (
        create_ferplus_dataloaders(
            image_size=260,
            batch_size=64,
            validation_size=0.15,
            num_workers=0,
            random_seed=42,
            balanced_sampling=False,
        )
    )

    model = create_high_accuracy_model()
    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=device,
        weights_only=False,
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model = model.to(device)

    logits, labels = collect_logits(
        model,
        validation_loader,
        device,
    )

    indices = list(range(len(labels)))

    calibration_indices, holdout_indices = (
        train_test_split(
            indices,
            test_size=0.50,
            random_state=42,
            stratify=labels.numpy(),
        )
    )

    calibration_logits = logits[
        calibration_indices
    ]

    calibration_labels = labels[
        calibration_indices
    ]

    holdout_logits = logits[
        holdout_indices
    ]

    holdout_labels = labels[
        holdout_indices
    ]

    zero_bias = torch.zeros(len(CLASSES))

    (
        baseline_accuracy,
        baseline_macro_f1,
        baseline_recalls,
    ) = calculate_metrics(
        holdout_logits,
        holdout_labels,
        zero_bias,
    )

    best_bias = zero_bias
    best_accuracy = baseline_accuracy
    best_macro_f1 = baseline_macro_f1
    best_recalls = baseline_recalls

    for regularization in [
        0.05,
        0.10,
        0.20,
        0.50,
        1.00,
        2.00,
    ]:
        candidate_bias = fit_bias(
            calibration_logits,
            calibration_labels,
            regularization,
        )

        (
            accuracy,
            macro_f1,
            recalls,
        ) = calculate_metrics(
            holdout_logits,
            holdout_labels,
            candidate_bias,
        )

        accuracy_is_safe = (
            accuracy
            >= baseline_accuracy - 0.01
        )

        if (
            accuracy_is_safe
            and macro_f1 > best_macro_f1
        ):
            best_bias = candidate_bias
            best_accuracy = accuracy
            best_macro_f1 = macro_f1
            best_recalls = recalls

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "classes": CLASSES,
                "class_bias": [
                    round(value, 8)
                    for value in best_bias.tolist()
                ],
                "baseline_accuracy":
                    baseline_accuracy,
                "calibrated_accuracy":
                    best_accuracy,
                "baseline_macro_f1":
                    baseline_macro_f1,
                "calibrated_macro_f1":
                    best_macro_f1,
                "rule": (
                    "adjusted_logits = "
                    "model_logits + class_bias"
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"\nAccuracy: "
        f"{baseline_accuracy * 100:.2f}% "
        f"-> {best_accuracy * 100:.2f}%"
    )

    print(
        f"Macro-F1: "
        f"{baseline_macro_f1:.4f} "
        f"-> {best_macro_f1:.4f}"
    )

    print("\nPer-class recall:")

    for index, class_name in enumerate(
        CLASSES
    ):
        print(
            f"{class_name:>8}: "
            f"{baseline_recalls[index]:.3f} "
            f"-> {best_recalls[index]:.3f}"
        )

    print("\nBias:", best_bias.tolist())
    print("Saved:", OUTPUT_PATH)


if __name__ == "__main__":
    main()