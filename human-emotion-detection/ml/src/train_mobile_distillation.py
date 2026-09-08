import argparse
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

from ml.src.ferplus_dataloader import (
    create_ferplus_dataloaders,
)
from ml.src.high_accuracy_model import (
    create_high_accuracy_model,
)
from ml.src.mobile_emotion_model import (
    create_mobile_emotion_model,
)


NUMBER_OF_CLASSES = 7
IMAGE_SIZE = 160


def load_state(checkpoint_path, device):
    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=False,
    )

    return checkpoint.get(
        "model_state_dict",
        checkpoint,
    )


def calculate_metrics(confusion):
    true_positive = confusion.diag().float()

    precision = true_positive / (
        confusion.sum(dim=0).float() + 1e-8
    )

    recall = true_positive / (
        confusion.sum(dim=1).float() + 1e-8
    )

    f1 = (
        2 * precision * recall
        / (precision + recall + 1e-8)
    )

    accuracy = (
        true_positive.sum()
        / confusion.sum().clamp_min(1)
    )

    return accuracy.item(), f1.mean().item()


def train_epoch(
    student,
    teacher,
    loader,
    optimizer,
    scaler,
    device,
):
    student.train()
    teacher.eval()

    total_loss = 0.0
    correct = 0
    samples = 0

    progress = tqdm(loader, desc="Training")

    for images, labels in progress:
        images = images.to(
            device,
            non_blocking=True,
        )

        labels = labels.to(
            device,
            non_blocking=True,
        )

        optimizer.zero_grad(set_to_none=True)

        with torch.inference_mode():
            teacher_logits = teacher(images)

        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=device.type == "cuda",
        ):
            student_logits = student(images)

            hard_loss = F.cross_entropy(
                student_logits,
                labels,
                label_smoothing=0.05,
            )

            temperature = 3.0

            soft_loss = F.kl_div(
                F.log_softmax(
                    student_logits / temperature,
                    dim=1,
                ),
                F.softmax(
                    teacher_logits / temperature,
                    dim=1,
                ),
                reduction="batchmean",
            ) * (temperature**2)

            loss = (
                0.45 * hard_loss
                + 0.55 * soft_loss
            )

        scaler.scale(loss).backward()

        scaler.unscale_(optimizer)

        nn.utils.clip_grad_norm_(
            student.parameters(),
            max_norm=2.0,
        )

        scaler.step(optimizer)
        scaler.update()

        total_loss += loss.item() * labels.size(0)

        predictions = student_logits.argmax(dim=1)

        correct += (
            predictions == labels
        ).sum().item()

        samples += labels.size(0)

        progress.set_postfix(
            loss=f"{loss.item():.4f}"
        )

    return (
        total_loss / samples,
        correct / samples,
    )


@torch.inference_mode()
def validate(model, loader, device):
    model.eval()

    confusion = torch.zeros(
        NUMBER_OF_CLASSES,
        NUMBER_OF_CLASSES,
        dtype=torch.long,
    )

    total_loss = 0.0
    samples = 0

    for images, labels in tqdm(
        loader,
        desc="Validation",
    ):
        images = images.to(device)
        labels = labels.to(device)

        logits = model(images)

        loss = F.cross_entropy(
            logits,
            labels,
        )

        predictions = logits.argmax(dim=1)

        positions = (
            labels.cpu() * NUMBER_OF_CLASSES
            + predictions.cpu()
        )

        confusion += torch.bincount(
            positions,
            minlength=NUMBER_OF_CLASSES**2,
        ).reshape(
            NUMBER_OF_CLASSES,
            NUMBER_OF_CLASSES,
        )

        total_loss += loss.item() * labels.size(0)
        samples += labels.size(0)

    accuracy, macro_f1 = calculate_metrics(
        confusion
    )

    return (
        total_loss / samples,
        accuracy,
        macro_f1,
    )


def export_onnx(model, output_path):
    model = model.cpu().eval()

    sample = torch.randn(
        1,
        3,
        IMAGE_SIZE,
        IMAGE_SIZE,
    )

    torch.onnx.export(
        model,
        sample,
        output_path,
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={
            "input": {0: "batch"},
            "logits": {0: "batch"},
        },
        opset_version=18,
        do_constant_folding=True,
        dynamo=False,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--teacher-checkpoint",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=12,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
    )

    parser.add_argument(
        "--num-workers",
        type=int,
        default=0,
    )

    arguments = parser.parse_args()

    output_dir = Path(arguments.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    best_checkpoint = (
        output_dir / "best_mobile_model.pt"
    )

    mobile_onnx = (
        output_dir / "emotion_model_mobile.onnx"
    )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("Device:", device)

    train_loader, validation_loader, _ = (
        create_ferplus_dataloaders(
            image_size=IMAGE_SIZE,
            batch_size=arguments.batch_size,
            validation_size=0.15,
            num_workers=arguments.num_workers,
            random_seed=42,
            balanced_sampling=False,
        )
    )

    teacher = create_high_accuracy_model(
        number_of_classes=NUMBER_OF_CLASSES,
        freeze_backbone=False,
    ).to(device)

    teacher.load_state_dict(
        load_state(
            arguments.teacher_checkpoint,
            device,
        )
    )

    teacher.eval()

    for parameter in teacher.parameters():
        parameter.requires_grad = False

    student = create_mobile_emotion_model(
        number_of_classes=NUMBER_OF_CLASSES,
        pretrained=True,
    ).to(device)

    optimizer = AdamW(
        student.parameters(),
        lr=2e-4,
        weight_decay=1e-4,
    )

    scheduler = CosineAnnealingLR(
        optimizer,
        T_max=arguments.epochs,
        eta_min=1e-6,
    )

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda",
    )

    best_macro_f1 = 0.0
    best_accuracy = 0.0
    patience_counter = 0

    for epoch in range(1, arguments.epochs + 1):
        print(
            f"\nMobile distillation epoch "
            f"{epoch}/{arguments.epochs}"
        )

        train_loss, train_accuracy = train_epoch(
            student,
            teacher,
            train_loader,
            optimizer,
            scaler,
            device,
        )

        validation_loss, validation_accuracy, macro_f1 = (
            validate(
                student,
                validation_loader,
                device,
            )
        )

        scheduler.step()

        print(f"Train loss: {train_loss:.4f}")
        print(
            f"Train accuracy: "
            f"{train_accuracy * 100:.2f}%"
        )
        print(
            f"Validation loss: "
            f"{validation_loss:.4f}"
        )
        print(
            f"Validation accuracy: "
            f"{validation_accuracy * 100:.2f}%"
        )
        print(
            f"Validation macro-F1: "
            f"{macro_f1:.4f}"
        )

        if macro_f1 > best_macro_f1:
            best_macro_f1 = macro_f1
            best_accuracy = validation_accuracy
            patience_counter = 0

            torch.save(
                {
                    "model_state_dict":
                        student.state_dict(),
                    "epoch": epoch,
                    "validation_accuracy":
                        validation_accuracy,
                    "validation_macro_f1":
                        macro_f1,
                    "image_size": IMAGE_SIZE,
                },
                best_checkpoint,
            )

            print("Best mobile model saved!")
        else:
            patience_counter += 1

        if patience_counter >= 4:
            print("Early stopping activated.")
            break

    student.load_state_dict(
        load_state(best_checkpoint, device)
    )

    export_onnx(
        student,
        mobile_onnx,
    )

    size_mb = (
        mobile_onnx.stat().st_size
        / (1024 * 1024)
    )

    print("\nMobile training completed.")
    print(
        f"Best accuracy: "
        f"{best_accuracy * 100:.2f}%"
    )
    print(
        f"Best macro-F1: {best_macro_f1:.4f}"
    )
    print(f"ONNX size: {size_mb:.2f} MB")
    print(f"Model: {mobile_onnx}")


if __name__ == "__main__":
    main()