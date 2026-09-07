from pathlib import Path

import torch
import yaml
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

from ml.src.ferplus_dataloader import (
    CLASSES,
    create_ferplus_dataloaders,
)
from ml.src.high_accuracy_model import (
    create_high_accuracy_model,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "ml/configs/high_accuracy.yaml"
CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "ml/models/checkpoints/best_high_accuracy_model.pt"
)


def train_epoch(
    model,
    loader,
    criterion,
    optimizer,
    scaler,
    device,
):
    model.train()

    total_loss = 0
    total_correct = 0
    total_samples = 0
    use_amp = device.type == "cuda"

    progress = tqdm(loader, desc="Training", leave=False)

    for images, labels in progress:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=use_amp,
        ):
            outputs = model(images)
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0,
        )

        scaler.step(optimizer)
        scaler.update()

        total_loss += loss.item() * labels.size(0)
        total_correct += (
            outputs.argmax(dim=1) == labels
        ).sum().item()
        total_samples += labels.size(0)

        progress.set_postfix(loss=f"{loss.item():.4f}")

    return (
        total_loss / total_samples,
        total_correct / total_samples,
    )


@torch.inference_mode()
def evaluate(model, loader, criterion, device):
    model.eval()

    total_loss = 0
    total_correct = 0
    total_samples = 0

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        outputs = model(images)
        loss = criterion(outputs, labels)

        total_loss += loss.item() * labels.size(0)
        total_correct += (
            outputs.argmax(dim=1) == labels
        ).sum().item()
        total_samples += labels.size(0)

    return (
        total_loss / total_samples,
        total_correct / total_samples,
    )


def run_stage(
    stage_name,
    model,
    train_loader,
    validation_loader,
    criterion,
    optimizer,
    scheduler,
    scaler,
    device,
    epochs,
    best_accuracy,
    patience=None,
):
    patience_counter = 0

    for epoch in range(1, epochs + 1):
        train_loss, train_accuracy = train_epoch(
            model,
            train_loader,
            criterion,
            optimizer,
            scaler,
            device,
        )

        validation_loss, validation_accuracy = evaluate(
            model,
            validation_loader,
            criterion,
            device,
        )

        scheduler.step()

        print(f"\n{stage_name} epoch {epoch}/{epochs}")
        print(f"Train loss: {train_loss:.4f}")
        print(f"Train accuracy: {train_accuracy * 100:.2f}%")
        print(f"Validation loss: {validation_loss:.4f}")
        print(
            f"Validation accuracy: "
            f"{validation_accuracy * 100:.2f}%"
        )

        if validation_accuracy > best_accuracy:
            best_accuracy = validation_accuracy
            patience_counter = 0

            CHECKPOINT_PATH.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "validation_accuracy": best_accuracy,
                    "classes": CLASSES,
                    "image_size": 260,
                },
                CHECKPOINT_PATH,
            )

            print("Best high-accuracy model saved!")
        else:
            patience_counter += 1

        if patience and patience_counter >= patience:
            print("Early stopping activated.")
            break

    return best_accuracy


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    if device.type != "cuda":
        print("Warning: use Google Colab GPU for this training.")

    train_loader, validation_loader, _ = (
        create_ferplus_dataloaders(
            image_size=config["data"]["image_size"],
            batch_size=config["data"]["batch_size"],
            validation_size=config["data"]["validation_size"],
            num_workers=config["data"]["num_workers"],
            random_seed=config["data"]["random_seed"],
            balanced_sampling=True,
        )
    )

    model = create_high_accuracy_model(
        number_of_classes=7,
        freeze_backbone=True,
    ).to(device)

    criterion = nn.CrossEntropyLoss(
        label_smoothing=config["training"]["label_smoothing"]
    )

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda",
    )

    # Stage 1: classifier warm-up
    warmup_optimizer = AdamW(
        model.network.classifier.parameters(),
        lr=config["training"]["warmup_learning_rate"],
        weight_decay=config["training"]["weight_decay"],
    )

    warmup_scheduler = CosineAnnealingLR(
        warmup_optimizer,
        T_max=config["training"]["warmup_epochs"],
    )

    best_accuracy = run_stage(
        stage_name="Warm-up",
        model=model,
        train_loader=train_loader,
        validation_loader=validation_loader,
        criterion=criterion,
        optimizer=warmup_optimizer,
        scheduler=warmup_scheduler,
        scaler=scaler,
        device=device,
        epochs=config["training"]["warmup_epochs"],
        best_accuracy=0.0,
    )

    # Reload the best warm-up checkpoint
    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=device,
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.unfreeze_all()

    # Stage 2: complete fine-tuning
    finetune_optimizer = AdamW(
        [
            {
                "params": model.network.features.parameters(),
                "lr": config["training"]["backbone_learning_rate"],
            },
            {
                "params": model.network.classifier.parameters(),
                "lr": config["training"]["classifier_learning_rate"],
            },
        ],
        weight_decay=config["training"]["weight_decay"],
    )

    finetune_scheduler = CosineAnnealingLR(
        finetune_optimizer,
        T_max=config["training"]["finetune_epochs"],
        eta_min=1e-7,
    )

    best_accuracy = run_stage(
        stage_name="Fine-tuning",
        model=model,
        train_loader=train_loader,
        validation_loader=validation_loader,
        criterion=criterion,
        optimizer=finetune_optimizer,
        scheduler=finetune_scheduler,
        scaler=scaler,
        device=device,
        epochs=config["training"]["finetune_epochs"],
        best_accuracy=best_accuracy,
        patience=config["training"]["early_stopping_patience"],
    )

    print(
        f"\nBest validation accuracy: "
        f"{best_accuracy * 100:.2f}%"
    )
    print("Checkpoint:", CHECKPOINT_PATH)


if __name__ == "__main__":
    main()