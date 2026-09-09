from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import f1_score
from torch.nn.utils import clip_grad_norm_
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

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


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CHECKPOINT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "balanced_checkpoints"
)


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def set_backbone_trainable(model, trainable):
    if not hasattr(model, "features"):
        raise AttributeError(
            "Model does not contain EfficientNet features."
        )

    for parameter in model.features.parameters():
        parameter.requires_grad = trainable

    for parameter in model.classifier.parameters():
        parameter.requires_grad = True


def calculate_accuracy(predictions, labels):
    return (
        predictions.eq(labels)
        .float()
        .mean()
        .item()
        * 100
    )


def run_epoch(
    model,
    loader,
    criterion,
    device,
    optimizer=None,
    scaler=None,
):
    training = optimizer is not None

    if training:
        model.train()
        description = "Training"
    else:
        model.eval()
        description = "Validation"

    running_loss = 0.0
    correct = 0
    sample_count = 0

    all_predictions = []
    all_labels = []

    progress = tqdm(
        loader,
        desc=description,
        leave=False,
    )

    for images, labels in progress:
        images = images.to(
            device,
            non_blocking=True,
        )

        labels = labels.to(
            device,
            non_blocking=True,
        )

        if training:
            optimizer.zero_grad(
                set_to_none=True
            )

        with torch.set_grad_enabled(training):
            with torch.autocast(
                device_type=device.type,
                enabled=device.type == "cuda",
            ):
                logits = model(images)
                loss = criterion(logits, labels)

            if training:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)

                clip_grad_norm_(
                    model.parameters(),
                    max_norm=1.0,
                )

                scaler.step(optimizer)
                scaler.update()

        predictions = logits.argmax(dim=1)

        batch_size = labels.size(0)

        running_loss += (
            loss.item() * batch_size
        )

        correct += (
            predictions.eq(labels)
            .sum()
            .item()
        )

        sample_count += batch_size

        all_predictions.extend(
            predictions.detach().cpu().tolist()
        )

        all_labels.extend(
            labels.detach().cpu().tolist()
        )

        progress.set_postfix(
            loss=f"{loss.item():.4f}"
        )

    epoch_loss = (
        running_loss / max(sample_count, 1)
    )

    epoch_accuracy = (
        100 * correct / max(sample_count, 1)
    )

    macro_f1 = f1_score(
        all_labels,
        all_predictions,
        average="macro",
        zero_division=0,
    )

    return (
        epoch_loss,
        epoch_accuracy,
        macro_f1,
    )


def save_checkpoint(
    path,
    model,
    optimizer,
    scheduler,
    stage,
    completed_epoch,
    best_macro_f1,
    best_accuracy,
    patience_count,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    torch.save(
        {
            "model_state_dict":
                model.state_dict(),
            "optimizer_state_dict":
                optimizer.state_dict(),
            "scheduler_state_dict": (
                scheduler.state_dict()
                if scheduler is not None
                else None
            ),
            "stage": stage,
            "completed_epoch":
                completed_epoch,
            "best_macro_f1":
                best_macro_f1,
            "best_accuracy":
                best_accuracy,
            "patience_count":
                patience_count,
            "classes": CLASSES,
        },
        path,
    )


def save_best_model(
    path,
    model,
    macro_f1,
    accuracy,
    epoch,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    torch.save(
        {
            "model_state_dict":
                model.state_dict(),
            "classes": CLASSES,
            "validation_macro_f1":
                macro_f1,
            "validation_accuracy":
                accuracy,
            "epoch": epoch,
            "training_dataset":
                "clean FERPlus + RAF-DB minorities",
        },
        path,
    )


def create_optimizer(model, stage):
    if stage == "warmup":
        return AdamW(
            model.classifier.parameters(),
            lr=3e-4,
            weight_decay=1e-4,
        )

    return AdamW(
        [
            {
                "params":
                    model.features.parameters(),
                "lr": 2e-5,
            },
            {
                "params":
                    model.classifier.parameters(),
                "lr": 1e-4,
            },
        ],
        weight_decay=1e-4,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=DEFAULT_CHECKPOINT_DIR,
    )

    parser.add_argument(
        "--warmup-epochs",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=25,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
    )

    parser.add_argument(
        "--num-workers",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--patience",
        type=int,
        default=7,
    )

    parser.add_argument(
        "--fresh",
        action="store_true",
    )

    arguments = parser.parse_args()

    seed_everything(42)

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("Device:", device)

    (
        train_loader,
        validation_loader,
        _,
    ) = create_combined_dataloaders(
        image_size=260,
        batch_size=arguments.batch_size,
        validation_size=0.15,
        num_workers=arguments.num_workers,
        random_seed=42,
        balance_power=0.75,
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

    print(
        "Class weights:",
        [
            round(value, 4)
            for value in class_weights.tolist()
        ],
    )

    model = create_high_accuracy_model()
    model = model.to(device)

    # AMP scaler
    scaler = torch.cuda.amp.GradScaler(
        enabled=device.type == "cuda"
    )

    checkpoint_directory = (
        arguments.checkpoint_dir.resolve()
    )

    last_path = (
        checkpoint_directory
        / "last_balanced_model.pt"
    )

    best_path = (
        checkpoint_directory
        / "best_balanced_model.pt"
    )

    checkpoint = None

    if (
        last_path.exists()
        and not arguments.fresh
    ):
        checkpoint = torch.load(
            last_path,
            map_location=device,
            weights_only=False,
        )

        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        print(
            "Resuming stage:",
            checkpoint["stage"],
        )

        print(
            "Completed epoch:",
            checkpoint["completed_epoch"],
        )

    best_macro_f1 = (
        checkpoint.get("best_macro_f1", 0.0)
        if checkpoint
        else 0.0
    )

    best_accuracy = (
        checkpoint.get("best_accuracy", 0.0)
        if checkpoint
        else 0.0
    )

    patience_count = (
        checkpoint.get("patience_count", 0)
        if checkpoint
        else 0
    )

    resume_stage = (
        checkpoint.get("stage")
        if checkpoint
        else None
    )

    # -------------------------
    # Stage 1: classifier warm-up
    # -------------------------

    if resume_stage != "finetune":
        set_backbone_trainable(
            model,
            trainable=False,
        )

        optimizer = create_optimizer(
            model,
            stage="warmup",
        )

        warmup_start = 0

        if resume_stage == "warmup":
            optimizer.load_state_dict(
                checkpoint[
                    "optimizer_state_dict"
                ]
            )

            warmup_start = checkpoint[
                "completed_epoch"
            ]

        for epoch in range(
            warmup_start,
            arguments.warmup_epochs,
        ):
            print(
                f"\nWarm-up epoch "
                f"{epoch + 1}/"
                f"{arguments.warmup_epochs}"
            )

            train_loss, train_accuracy, _ = (
                run_epoch(
                    model,
                    train_loader,
                    criterion,
                    device,
                    optimizer=optimizer,
                    scaler=scaler,
                )
            )

            (
                validation_loss,
                validation_accuracy,
                validation_macro_f1,
            ) = run_epoch(
                model,
                validation_loader,
                criterion,
                device,
            )

            print(
                f"Train loss: {train_loss:.4f}"
            )
            print(
                f"Train accuracy: "
                f"{train_accuracy:.2f}%"
            )
            print(
                f"Validation loss: "
                f"{validation_loss:.4f}"
            )
            print(
                f"Validation accuracy: "
                f"{validation_accuracy:.2f}%"
            )
            print(
                f"Validation macro-F1: "
                f"{validation_macro_f1:.4f}"
            )

            improved = (
                validation_macro_f1
                > best_macro_f1
            )

            if improved:
                best_macro_f1 = (
                    validation_macro_f1
                )
                best_accuracy = (
                    validation_accuracy
                )

                save_best_model(
                    best_path,
                    model,
                    best_macro_f1,
                    best_accuracy,
                    epoch + 1,
                )

                print("Best model saved!")

            save_checkpoint(
                last_path,
                model,
                optimizer,
                scheduler=None,
                stage="warmup",
                completed_epoch=epoch + 1,
                best_macro_f1=best_macro_f1,
                best_accuracy=best_accuracy,
                patience_count=0,
            )

        checkpoint = None
        patience_count = 0

    # -------------------------
    # Stage 2: full fine-tuning
    # -------------------------

    set_backbone_trainable(
        model,
        trainable=True,
    )

    optimizer = create_optimizer(
        model,
        stage="finetune",
    )

    scheduler = CosineAnnealingLR(
        optimizer,
        T_max=arguments.epochs,
        eta_min=1e-6,
    )

    finetune_start = 0

    if resume_stage == "finetune":
        optimizer.load_state_dict(
            checkpoint["optimizer_state_dict"]
        )

        if checkpoint[
            "scheduler_state_dict"
        ] is not None:
            scheduler.load_state_dict(
                checkpoint[
                    "scheduler_state_dict"
                ]
            )

        finetune_start = checkpoint[
            "completed_epoch"
        ]

    for epoch in range(
        finetune_start,
        arguments.epochs,
    ):
        print(
            f"\nFine-tuning epoch "
            f"{epoch + 1}/{arguments.epochs}"
        )

        (
            train_loss,
            train_accuracy,
            train_macro_f1,
        ) = run_epoch(
            model,
            train_loader,
            criterion,
            device,
            optimizer=optimizer,
            scaler=scaler,
        )

        (
            validation_loss,
            validation_accuracy,
            validation_macro_f1,
        ) = run_epoch(
            model,
            validation_loader,
            criterion,
            device,
        )

        scheduler.step()

        print(f"Train loss: {train_loss:.4f}")
        print(
            f"Train accuracy: "
            f"{train_accuracy:.2f}%"
        )
        print(
            f"Train macro-F1: "
            f"{train_macro_f1:.4f}"
        )
        print(
            f"Validation loss: "
            f"{validation_loss:.4f}"
        )
        print(
            f"Validation accuracy: "
            f"{validation_accuracy:.2f}%"
        )
        print(
            f"Validation macro-F1: "
            f"{validation_macro_f1:.4f}"
        )

        improved = (
            validation_macro_f1
            > best_macro_f1
        )

        if improved:
            best_macro_f1 = (
                validation_macro_f1
            )
            best_accuracy = (
                validation_accuracy
            )
            patience_count = 0

            save_best_model(
                best_path,
                model,
                best_macro_f1,
                best_accuracy,
                epoch + 1,
            )

            print("Best model saved!")

        else:
            patience_count += 1

        save_checkpoint(
            last_path,
            model,
            optimizer,
            scheduler,
            stage="finetune",
            completed_epoch=epoch + 1,
            best_macro_f1=best_macro_f1,
            best_accuracy=best_accuracy,
            patience_count=patience_count,
        )

        print(
            f"Early-stopping counter: "
            f"{patience_count}/"
            f"{arguments.patience}"
        )

        if patience_count >= arguments.patience:
            print("Early stopping activated.")
            break

    print("\nTraining completed.")
    print(
        f"Best validation macro-F1: "
        f"{best_macro_f1:.4f}"
    )
    print(
        f"Associated accuracy: "
        f"{best_accuracy:.2f}%"
    )
    print(f"Best checkpoint: {best_path}")
    print(f"Resume checkpoint: {last_path}")


if __name__ == "__main__":
    main()