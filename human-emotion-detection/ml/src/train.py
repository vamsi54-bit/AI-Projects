from pathlib import Path

import matplotlib.pyplot as plt
import torch
import yaml
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau

from ml.src.dataloader import create_dataloaders
from ml.src.model import create_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "ml" / "configs" / "training.yaml"
CHECKPOINT_DIR = PROJECT_ROOT / "ml" / "models" / "checkpoints"
HISTORY_PATH = (
    PROJECT_ROOT / "ml" / "data" / "processed" / "training_history.png"
)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def calculate_class_weights(train_loader, number_of_classes):
    subset = train_loader.dataset
    original_dataset = subset.dataset

    targets = torch.tensor(
        [original_dataset.targets[index] for index in subset.indices],
        dtype=torch.long,
    )

    counts = torch.bincount(
        targets,
        minlength=number_of_classes,
    ).float()

    weights = targets.numel() / (
        number_of_classes * counts
    )

    return weights, counts


def train_one_epoch(model, loader, loss_function, optimizer, device):
    model.train()

    total_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad(set_to_none=True)

        predictions = model(images)
        loss = loss_function(predictions, labels)

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0,
        )

        optimizer.step()

        total_loss += loss.item() * images.size(0)
        correct += (
            predictions.argmax(dim=1) == labels
        ).sum().item()
        total += labels.size(0)

    return total_loss / total, correct / total


@torch.inference_mode()
def validate(model, loader, loss_function, device):
    model.eval()

    total_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        predictions = model(images)
        loss = loss_function(predictions, labels)

        total_loss += loss.item() * images.size(0)
        correct += (
            predictions.argmax(dim=1) == labels
        ).sum().item()
        total += labels.size(0)

    return total_loss / total, correct / total


def save_training_plot(history):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    epochs = range(1, len(history["train_loss"]) + 1)

    figure, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].plot(epochs, history["train_loss"], label="Train")
    axes[0].plot(epochs, history["validation_loss"], label="Validation")
    axes[0].set_title("Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].legend()

    axes[1].plot(epochs, history["train_accuracy"], label="Train")
    axes[1].plot(
        epochs,
        history["validation_accuracy"],
        label="Validation",
    )
    axes[1].set_title("Accuracy")
    axes[1].set_xlabel("Epoch")
    axes[1].legend()

    figure.tight_layout()
    figure.savefig(HISTORY_PATH, dpi=200)
    plt.close(figure)


def main():
    config = load_config()

    data_config = config["data"]
    model_config = config["model"]
    training_config = config["training"]

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    train_loader, validation_loader, _ = create_dataloaders(
        image_size=data_config["image_size"],
        batch_size=data_config["batch_size"],
        validation_size=training_config["validation_size"],
        num_workers=data_config["num_workers"],
        random_seed=training_config["random_seed"],
    )

    model = create_model(
        number_of_classes=model_config["number_of_classes"],
        freeze_backbone=True,
    ).to(device)

    class_weights, class_counts = calculate_class_weights(
        train_loader,
        model_config["number_of_classes"],
    )

    print("Class counts:", class_counts.tolist())
    print("Class weights:", class_weights.tolist())

    loss_function = nn.CrossEntropyLoss(
        weight=class_weights.to(device),
        label_smoothing=0.1,
    )

    optimizer = AdamW(
        filter(lambda parameter: parameter.requires_grad, model.parameters()),
        lr=training_config["learning_rate"],
        weight_decay=training_config["weight_decay"],
    )

    scheduler = ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=2,
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = CHECKPOINT_DIR / "best_model.pt"

    history = {
        "train_loss": [],
        "validation_loss": [],
        "train_accuracy": [],
        "validation_accuracy": [],
    }

    best_validation_accuracy = 0.0
    epochs_without_improvement = 0
    early_stopping_patience = 5

    for epoch in range(1, training_config["epochs"] + 1):
        train_loss, train_accuracy = train_one_epoch(
            model,
            train_loader,
            loss_function,
            optimizer,
            device,
        )

        validation_loss, validation_accuracy = validate(
            model,
            validation_loader,
            loss_function,
            device,
        )

        scheduler.step(validation_accuracy)

        history["train_loss"].append(train_loss)
        history["validation_loss"].append(validation_loss)
        history["train_accuracy"].append(train_accuracy)
        history["validation_accuracy"].append(validation_accuracy)

        print(f"\nEpoch {epoch}/{training_config['epochs']}")
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Train Acc : {train_accuracy * 100:.2f}%")
        print(f"Val Loss  : {validation_loss:.4f}")
        print(f"Val Acc   : {validation_accuracy * 100:.2f}%")

        if validation_accuracy > best_validation_accuracy:
            best_validation_accuracy = validation_accuracy
            epochs_without_improvement = 0

            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "validation_accuracy": validation_accuracy,
                    "classes": train_loader.dataset.dataset.classes,
                },
                checkpoint_path,
            )

            print("Best model saved!")
        else:
            epochs_without_improvement += 1

        save_training_plot(history)

        if epochs_without_improvement >= early_stopping_patience:
            print("\nEarly stopping activated.")
            break

    print("\nTraining completed.")
    print(f"Best validation accuracy: {best_validation_accuracy * 100:.2f}%")
    print(f"Checkpoint: {checkpoint_path}")
    print(f"Training graph: {HISTORY_PATH}")


if __name__ == "__main__":
    main()