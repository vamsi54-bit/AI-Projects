import json
from pathlib import Path

import matplotlib.pyplot as plt
import torch

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)

from training.models.bigru_model import BiGRUModel
from training.dataloaders.create_dataloaders import create_dataloaders


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

DEVICE = torch.device("cpu")

OUTPUT_DIR = Path("models/evaluation")
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# LOAD CLASSES
# --------------------------------------------------

with open(
    "data/metadata/classes.json",
    "r",
    encoding="utf-8"
) as file:

    class_map = json.load(file)


NUM_CLASSES = len(class_map)

# index -> class name
index_to_class = {
    value: key
    for key, value in class_map.items()
}

class_names = [
    index_to_class[i]
    for i in range(NUM_CLASSES)
]


# --------------------------------------------------
# LOAD TEST DATA
# --------------------------------------------------

_, _, test_loader = create_dataloaders()


# --------------------------------------------------
# LOAD MODEL
# --------------------------------------------------

model = BiGRUModel(
    input_size=258,
    hidden_size=128,
    num_layers=2,
    num_classes=NUM_CLASSES,
    dropout=0.3
)

model.load_state_dict(
    torch.load(
        "models/checkpoints/best_bigru.pt",
        map_location=DEVICE
    )
)

model.to(DEVICE)
model.eval()


# --------------------------------------------------
# TEST LOOP
# --------------------------------------------------

true_labels = []
pred_labels = []


with torch.no_grad():

    for X, y in test_loader:

        X = X.to(DEVICE)
        y = y.to(DEVICE)

        outputs = model(X)

        predictions = torch.argmax(
            outputs,
            dim=1
        )

        true_labels.extend(
            y.cpu().numpy()
        )

        pred_labels.extend(
            predictions.cpu().numpy()
        )


# --------------------------------------------------
# METRICS
# --------------------------------------------------

accuracy = accuracy_score(
    true_labels,
    pred_labels
)

precision = precision_score(
    true_labels,
    pred_labels,
    average="weighted",
    zero_division=0
)

recall = recall_score(
    true_labels,
    pred_labels,
    average="weighted",
    zero_division=0
)

f1 = f1_score(
    true_labels,
    pred_labels,
    average="weighted",
    zero_division=0
)


print("\n========== TEST RESULTS ==========")

print(f"Accuracy : {accuracy * 100:.2f}%")
print(f"Precision: {precision * 100:.2f}%")
print(f"Recall   : {recall * 100:.2f}%")
print(f"F1 Score : {f1 * 100:.2f}%")


# --------------------------------------------------
# CLASSIFICATION REPORT
# --------------------------------------------------

report = classification_report(
    true_labels,
    pred_labels,
    labels=list(range(NUM_CLASSES)),
    target_names=class_names,
    zero_division=0,
    output_dict=True
)

report_file = (
    OUTPUT_DIR
    / "classification_report.json"
)

with open(
    report_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        report,
        file,
        indent=4
    )


# --------------------------------------------------
# SAVE METRICS
# --------------------------------------------------

metrics = {
    "accuracy": accuracy,
    "precision": precision,
    "recall": recall,
    "f1_score": f1
}

metrics_file = (
    OUTPUT_DIR
    / "metrics.json"
)

with open(
    metrics_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        metrics,
        file,
        indent=4
    )


# --------------------------------------------------
# CONFUSION MATRIX
# --------------------------------------------------

cm = confusion_matrix(
    true_labels,
    pred_labels,
    labels=list(range(NUM_CLASSES))
)

fig, ax = plt.subplots(
    figsize=(20, 20)
)

display = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=class_names
)

display.plot(
    ax=ax,
    xticks_rotation=90,
    cmap="Blues",
    colorbar=False
)

plt.title(
    "SignBridge BiGRU Confusion Matrix"
)

plt.tight_layout()

confusion_file = (
    OUTPUT_DIR
    / "confusion_matrix.png"
)

plt.savefig(
    confusion_file,
    dpi=300
)

plt.close()


# --------------------------------------------------
# DONE
# --------------------------------------------------

print()
print("Evaluation completed")

print(
    "Metrics:",
    metrics_file
)

print(
    "Classification report:",
    report_file
)

print(
    "Confusion matrix:",
    confusion_file
)