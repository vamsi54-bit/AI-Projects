from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from tqdm import tqdm

from ml.src.ferplus_dataloader import (
    CLASSES,
    create_ferplus_dataloaders,
)
from ml.src.high_accuracy_model import create_high_accuracy_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "ml/models/checkpoints/best_high_accuracy_model.pt"
)

RESULTS_DIR = PROJECT_ROOT / "ml/data/processed/evaluation"


@torch.inference_mode()
def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    _, _, test_loader = create_ferplus_dataloaders(
        image_size=260,
        batch_size=32,
        num_workers=0,
        balanced_sampling=False,
    )

    model = create_high_accuracy_model(
        number_of_classes=len(CLASSES),
        freeze_backbone=False,
    ).to(device)

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=device,
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    true_labels = []
    normal_predictions = []
    tta_predictions = []
    confidence_scores = []

    for images, labels in tqdm(test_loader, desc="TTA evaluation"):
        images = images.to(device)

        normal_probabilities = torch.softmax(
            model(images),
            dim=1,
        )

        flipped_images = torch.flip(images, dims=[3])

        flipped_probabilities = torch.softmax(
            model(flipped_images),
            dim=1,
        )

        tta_probabilities = (
            normal_probabilities + flipped_probabilities
        ) / 2

        confidence, predictions = tta_probabilities.max(dim=1)

        true_labels.extend(labels.tolist())
        normal_predictions.extend(
            normal_probabilities.argmax(dim=1).cpu().tolist()
        )
        tta_predictions.extend(predictions.cpu().tolist())
        confidence_scores.extend(confidence.cpu().tolist())

    normal_accuracy = accuracy_score(
        true_labels,
        normal_predictions,
    )

    tta_accuracy = accuracy_score(
        true_labels,
        tta_predictions,
    )

    print(f"\nNormal accuracy: {normal_accuracy * 100:.2f}%")
    print(f"TTA accuracy: {tta_accuracy * 100:.2f}%")

    report = classification_report(
        true_labels,
        tta_predictions,
        target_names=CLASSES,
        output_dict=True,
        zero_division=0,
    )

    print(
        classification_report(
            true_labels,
            tta_predictions,
            target_names=CLASSES,
            zero_division=0,
        )
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(report).transpose().to_csv(
        RESULTS_DIR / "tta_classification_report.csv"
    )

    prediction_records = pd.DataFrame(
        {
            "actual": [CLASSES[index] for index in true_labels],
            "predicted": [
                CLASSES[index] for index in tta_predictions
            ],
            "confidence": confidence_scores,
        }
    )

    prediction_records.to_csv(
        RESULTS_DIR / "test_predictions.csv",
        index=False,
    )

    matrix = confusion_matrix(
        true_labels,
        tta_predictions,
    )

    plt.figure(figsize=(10, 8))

    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=CLASSES,
        yticklabels=CLASSES,
    )

    plt.xlabel("Predicted emotion")
    plt.ylabel("Actual emotion")
    plt.title("FERPlus Test Confusion Matrix")
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / "confusion_matrix.png",
        dpi=200,
    )

    plt.close()

    print("Results saved to:", RESULTS_DIR)


if __name__ == "__main__":
    main()