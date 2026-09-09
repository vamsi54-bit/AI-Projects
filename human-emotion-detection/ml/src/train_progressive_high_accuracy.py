import argparse
import json
from pathlib import Path

import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

from ml.src.ferplus_dataloader import CLASSES, create_ferplus_dataloaders
from ml.src.high_accuracy_model import create_high_accuracy_model


CLASS_COUNTS = torch.tensor(
    [2096, 162, 554, 6399, 8761, 2987, 3028],
    dtype=torch.float32,
)


def parse_args():
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--initial-checkpoint",
        type=Path,
        default=project_root / "ml/models/checkpoints/best_high_accuracy_model.pt",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=project_root / "ml/models/checkpoints/progressive_v2",
    )
    parser.add_argument("--image-size", type=int, default=260)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--validation-size", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--accuracy-drop-limit", type=float, default=0.005)
    return parser.parse_args()


def checkpoint_state(checkpoint):
    for key in ("model_state_dict", "state_dict", "model"):
        if key in checkpoint:
            return checkpoint[key]
    return checkpoint


def gentle_class_weights(device):
    weights = torch.sqrt(CLASS_COUNTS.mean() / CLASS_COUNTS)
    weights = weights.clamp(0.75, 1.50)
    weights = weights / weights.mean()
    return weights.to(device)


def metrics_from_confusion(confusion):
    true_positive = confusion.diag().float()
    precision = true_positive / confusion.sum(dim=0).clamp_min(1)
    recall = true_positive / confusion.sum(dim=1).clamp_min(1)
    f1 = 2 * precision * recall / (precision + recall).clamp_min(1e-12)
    accuracy = true_positive.sum() / confusion.sum().clamp_min(1)
    return accuracy.item(), f1.mean().item(), f1.tolist()


def update_confusion(confusion, labels, predictions):
    class_count = len(CLASSES)
    indices = labels.detach().cpu() * class_count + predictions.detach().cpu()
    confusion += torch.bincount(
        indices,
        minlength=class_count * class_count,
    ).reshape(class_count, class_count)


def train_epoch(model, loader, criterion, optimizer, scaler, device):
    model.train()
    total_loss = 0.0
    sample_count = 0
    confusion = torch.zeros(len(CLASSES), len(CLASSES), dtype=torch.long)
    progress = tqdm(loader, desc="Training", leave=False)

    for images, labels in progress:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)

        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=device.type == "cuda",
        ):
            logits = model(images)
            loss = criterion(logits, labels)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

        batch_size = labels.size(0)
        total_loss += loss.item() * batch_size
        sample_count += batch_size
        update_confusion(confusion, labels, logits.argmax(dim=1))
        progress.set_postfix(loss=f"{loss.item():.4f}")

    accuracy, macro_f1, _ = metrics_from_confusion(confusion)
    return total_loss / sample_count, accuracy, macro_f1


@torch.inference_mode()
def evaluate(model, loader, criterion, device, description="Validation"):
    model.eval()
    total_loss = 0.0
    sample_count = 0
    confusion = torch.zeros(len(CLASSES), len(CLASSES), dtype=torch.long)

    for images, labels in tqdm(loader, desc=description, leave=False):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        logits = model(images)
        loss = criterion(logits, labels)
        batch_size = labels.size(0)
        total_loss += loss.item() * batch_size
        sample_count += batch_size
        update_confusion(confusion, labels, logits.argmax(dim=1))

    accuracy, macro_f1, class_f1 = metrics_from_confusion(confusion)
    return total_loss / sample_count, accuracy, macro_f1, class_f1


def configure_stage(model, blocks):
    if blocks == "all":
        model.unfreeze_all()
    else:
        model.unfreeze_top_blocks(number_of_blocks=blocks)


def make_optimizer(model, backbone_lr, classifier_lr):
    return AdamW(
        [
            {
                "params": model.network.features.parameters(),
                "lr": backbone_lr,
            },
            {
                "params": model.network.classifier.parameters(),
                "lr": classifier_lr,
            },
        ],
        weight_decay=2e-4,
    )


def save_checkpoint(path, model, stage, epoch, accuracy, macro_f1, image_size):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "stage": stage,
            "epoch": epoch,
            "validation_accuracy": accuracy,
            "validation_macro_f1": macro_f1,
            "classes": CLASSES,
            "image_size": image_size,
        },
        path,
    )


def main():
    args = parse_args()
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.benchmark = True

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)
    if device.type != "cuda":
        raise RuntimeError("Run this training on a CUDA GPU.")
    if not args.initial_checkpoint.exists():
        raise FileNotFoundError(f"Checkpoint not found: {args.initial_checkpoint}")

    train_loader, validation_loader, test_loader = create_ferplus_dataloaders(
        image_size=args.image_size,
        batch_size=args.batch_size,
        validation_size=args.validation_size,
        num_workers=args.num_workers,
        random_seed=args.seed,
        balanced_sampling=False,
    )

    model = create_high_accuracy_model(
        number_of_classes=len(CLASSES),
        freeze_backbone=True,
    ).to(device)
    initial = torch.load(args.initial_checkpoint, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint_state(initial))
    print("Loaded production checkpoint:", args.initial_checkpoint)

    weights = gentle_class_weights(device)
    print("Gentle class weights:", [round(value, 3) for value in weights.tolist()])
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=0.04)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    baseline_loss, baseline_accuracy, baseline_macro_f1, baseline_class_f1 = evaluate(
        model, validation_loader, criterion, device, "Baseline validation"
    )
    print(f"Baseline loss: {baseline_loss:.4f}")
    print(f"Baseline accuracy: {baseline_accuracy * 100:.2f}%")
    print(f"Baseline macro-F1: {baseline_macro_f1:.4f}")

    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    best_path = args.checkpoint_dir / "best_progressive_model.pt"
    last_path = args.checkpoint_dir / "last_progressive_model.pt"
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    best_accuracy = baseline_accuracy
    best_macro_f1 = baseline_macro_f1
    accuracy_floor = baseline_accuracy - args.accuracy_drop_limit
    history = []

    stages = [
        ("Top-2 blocks", 2, 3, 1.0e-5, 6.0e-5),
        ("Top-4 blocks", 4, 4, 7.0e-6, 4.0e-5),
        ("Full network", "all", 5, 3.0e-6, 2.0e-5),
    ]

    for stage_name, blocks, epochs, backbone_lr, classifier_lr in stages:
        model.load_state_dict(best_state)
        configure_stage(model, blocks)
        optimizer = make_optimizer(model, backbone_lr, classifier_lr)
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=epochs,
            eta_min=backbone_lr * 0.1,
        )
        patience_counter = 0

        for epoch in range(1, epochs + 1):
            print(f"\n{stage_name} epoch {epoch}/{epochs}")
            train_loss, train_accuracy, train_macro_f1 = train_epoch(
                model, train_loader, criterion, optimizer, scaler, device
            )
            validation_loss, validation_accuracy, validation_macro_f1, class_f1 = evaluate(
                model, validation_loader, criterion, device
            )
            scheduler.step()

            print(f"Train loss: {train_loss:.4f}")
            print(f"Train accuracy: {train_accuracy * 100:.2f}%")
            print(f"Train macro-F1: {train_macro_f1:.4f}")
            print(f"Validation loss: {validation_loss:.4f}")
            print(f"Validation accuracy: {validation_accuracy * 100:.2f}%")
            print(f"Validation macro-F1: {validation_macro_f1:.4f}")

            record = {
                "stage": stage_name,
                "epoch": epoch,
                "train_loss": train_loss,
                "train_accuracy": train_accuracy,
                "train_macro_f1": train_macro_f1,
                "validation_loss": validation_loss,
                "validation_accuracy": validation_accuracy,
                "validation_macro_f1": validation_macro_f1,
                "class_f1": dict(zip(CLASSES, class_f1)),
            }
            history.append(record)
            save_checkpoint(
                last_path, model, stage_name, epoch,
                validation_accuracy, validation_macro_f1, args.image_size,
            )

            acceptable_accuracy = validation_accuracy >= accuracy_floor
            improved = (
                acceptable_accuracy
                and validation_macro_f1 > best_macro_f1 + 1e-4
            )
            if improved:
                best_accuracy = validation_accuracy
                best_macro_f1 = validation_macro_f1
                best_state = {
                    key: value.detach().cpu().clone()
                    for key, value in model.state_dict().items()
                }
                save_checkpoint(
                    best_path, model, stage_name, epoch,
                    best_accuracy, best_macro_f1, args.image_size,
                )
                patience_counter = 0
                print("Best safe model saved!")
            else:
                patience_counter += 1
                print(f"No safe improvement: {patience_counter}/3")

            if patience_counter >= 3:
                print("Stage early stopping activated.")
                break

    model.load_state_dict(best_state)
    test_loss, test_accuracy, test_macro_f1, test_class_f1 = evaluate(
        model, test_loader, criterion, device, "Final test"
    )
    results = {
        "baseline_validation_accuracy": baseline_accuracy,
        "baseline_validation_macro_f1": baseline_macro_f1,
        "best_validation_accuracy": best_accuracy,
        "best_validation_macro_f1": best_macro_f1,
        "test_loss": test_loss,
        "test_accuracy": test_accuracy,
        "test_macro_f1": test_macro_f1,
        "test_class_f1": dict(zip(CLASSES, test_class_f1)),
        "history": history,
    }
    with open(args.checkpoint_dir / "training_results.json", "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    print("\nTraining completed.")
    print(f"Best validation accuracy: {best_accuracy * 100:.2f}%")
    print(f"Best validation macro-F1: {best_macro_f1:.4f}")
    print(f"Final test accuracy: {test_accuracy * 100:.2f}%")
    print(f"Final test macro-F1: {test_macro_f1:.4f}")
    print("Output:", args.checkpoint_dir)


if __name__ == "__main__":
    main()
