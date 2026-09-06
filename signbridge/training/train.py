import json
from pathlib import Path

import torch
import torch.nn as nn

from training.models.bigru_model import (
    BiGRUModel
)

from training.dataloaders.create_dataloaders import (
    create_dataloaders
)


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

EPOCHS = 20
LEARNING_RATE = 0.001

CHECKPOINT_DIR = Path(
    "models/checkpoints"
)

CHECKPOINT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# DEVICE
# --------------------------------------------------

device = torch.device("cpu")

print(
    "Device:",
    device
)


# --------------------------------------------------
# LOAD NUMBER OF CLASSES
# --------------------------------------------------

with open(
    "data/metadata/classes.json",
    "r",
    encoding="utf-8"
) as file:

    classes = json.load(file)

NUM_CLASSES = len(classes)

print(
    "Classes:",
    NUM_CLASSES
)


# --------------------------------------------------
# DATALOADERS
# --------------------------------------------------

train_loader, val_loader, test_loader = (
    create_dataloaders()
)


# --------------------------------------------------
# MODEL
# --------------------------------------------------

model = BiGRUModel(
    input_size=258,
    hidden_size=128,
    num_layers=2,
    num_classes=NUM_CLASSES,
    dropout=0.3
)

model = model.to(device)


# --------------------------------------------------
# LOSS
# --------------------------------------------------

criterion = nn.CrossEntropyLoss()


# --------------------------------------------------
# OPTIMIZER
# --------------------------------------------------

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)


# --------------------------------------------------
# TRAIN FUNCTION
# --------------------------------------------------

def train_one_epoch():

    model.train()

    total_loss = 0

    correct = 0
    total = 0

    for X, y in train_loader:

        X = X.to(device)
        y = y.to(device)

        optimizer.zero_grad()

        outputs = model(X)

        loss = criterion(
            outputs,
            y
        )

        loss.backward()

        optimizer.step()

        total_loss += loss.item()

        predictions = torch.argmax(
            outputs,
            dim=1
        )

        correct += (
            predictions == y
        ).sum().item()

        total += y.size(0)

    avg_loss = (
        total_loss
        / len(train_loader)
    )

    accuracy = (
        correct / total
    ) * 100

    return avg_loss, accuracy


# --------------------------------------------------
# VALIDATION FUNCTION
# --------------------------------------------------

def validate():

    model.eval()

    total_loss = 0

    correct = 0
    total = 0

    with torch.no_grad():

        for X, y in val_loader:

            X = X.to(device)
            y = y.to(device)

            outputs = model(X)

            loss = criterion(
                outputs,
                y
            )

            total_loss += loss.item()

            predictions = torch.argmax(
                outputs,
                dim=1
            )

            correct += (
                predictions == y
            ).sum().item()

            total += y.size(0)

    avg_loss = (
        total_loss
        / len(val_loader)
    )

    accuracy = (
        correct / total
    ) * 100

    return avg_loss, accuracy


# --------------------------------------------------
# TRAINING LOOP
# --------------------------------------------------

best_val_accuracy = 0

for epoch in range(EPOCHS):

    train_loss, train_accuracy = (
        train_one_epoch()
    )

    val_loss, val_accuracy = (
        validate()
    )

    print()
    print(
        f"Epoch {epoch + 1}/{EPOCHS}"
    )

    print(
        f"Train Loss: {train_loss:.4f}"
    )

    print(
        f"Train Acc : {train_accuracy:.2f}%"
    )

    print(
        f"Val Loss  : {val_loss:.4f}"
    )

    print(
        f"Val Acc   : {val_accuracy:.2f}%"
    )

    # ----------------------------------------------
    # SAVE BEST MODEL
    # ----------------------------------------------

    if val_accuracy > best_val_accuracy:

        best_val_accuracy = (
            val_accuracy
        )

        checkpoint = (
            CHECKPOINT_DIR
            / "best_bigru.pt"
        )

        torch.save(
            model.state_dict(),
            checkpoint
        )

        print(
            "Best model saved!"
        )


print()
print(
    "Training completed"
)

print(
    "Best validation accuracy:",
    f"{best_val_accuracy:.2f}%"
)