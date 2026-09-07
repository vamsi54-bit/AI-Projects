import json
from pathlib import Path

import torch
from torch import nn
from torch.optim import LBFGS
from tqdm import tqdm

from ml.src.ferplus_dataloader import create_ferplus_dataloaders
from ml.src.high_accuracy_model import create_high_accuracy_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "ml/models/checkpoints/best_high_accuracy_model.pt"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ml/models/exported/calibration.json"
)


@torch.no_grad()
def collect_logits(model, loader, device):
    all_logits = []
    all_labels = []

    for images, labels in tqdm(loader, desc="Collecting logits"):
        images = images.to(device)

        all_logits.append(model(images).cpu())
        all_labels.append(labels)

    return (
        torch.cat(all_logits),
        torch.cat(all_labels),
    )


def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    _, validation_loader, _ = create_ferplus_dataloaders(
        image_size=260,
        batch_size=32,
        num_workers=0,
        balanced_sampling=False,
    )

    model = create_high_accuracy_model(
        number_of_classes=7,
        freeze_backbone=False,
    ).to(device)

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=device,
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    logits, labels = collect_logits(
        model,
        validation_loader,
        device,
    )

    logits = logits.detach().clone().to(device)
    labels = labels.detach().clone().to(device)

    loss_function = nn.CrossEntropyLoss()

    original_loss = loss_function(
        logits,
        labels,
    ).item()

    log_temperature = nn.Parameter(
        torch.zeros(1, device=device)
    )

    optimizer = LBFGS(
        [log_temperature],
        lr=0.1,
        max_iter=50,
    )

    def closure():
        optimizer.zero_grad()

        temperature = torch.exp(log_temperature)

        loss = loss_function(
            logits / temperature,
            labels,
        )

        loss.backward()
        return loss

    optimizer.step(closure)

    temperature = torch.exp(
        log_temperature
    ).clamp(0.5, 10.0).item()

    calibrated_loss = loss_function(
        logits / temperature,
        labels,
    ).item()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            {
                "temperature": temperature,
                "original_loss": original_loss,
                "calibrated_loss": calibrated_loss,
            },
            file,
            indent=4,
        )

    print(f"Temperature: {temperature:.4f}")
    print(f"Original loss: {original_loss:.4f}")
    print(f"Calibrated loss: {calibrated_loss:.4f}")
    print("Saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()