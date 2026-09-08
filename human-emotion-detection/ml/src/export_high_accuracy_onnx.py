import json
import shutil
from pathlib import Path

import onnx
import torch

from ml.src.high_accuracy_model import create_high_accuracy_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "ml/models/checkpoints/best_high_accuracy_model.pt"
)

CALIBRATION_PATH = (
    PROJECT_ROOT
    / "ml/models/exported/calibration.json"
)

OUTPUT_DIR = PROJECT_ROOT / "web/public/models"

DESKTOP_MODEL_PATH = (
    OUTPUT_DIR / "emotion_model_desktop.onnx"
)

MOBILE_MODEL_PATH = (
    OUTPUT_DIR / "emotion_model_mobile.onnx"
)

CLASSES = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise",
]


def export_model(
    model: torch.nn.Module,
    output_path: Path,
    image_size: int,
) -> None:
    dummy_input = torch.randn(
        1,
        3,
        image_size,
        image_size,
    )

    torch.onnx.export(
        model,
        dummy_input,
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

    onnx_model = onnx.load(output_path)
    onnx.checker.check_model(onnx_model)

    size_mb = output_path.stat().st_size / (1024 * 1024)

    print(f"Validated: {output_path.name}")
    print(f"Input size: {image_size}x{image_size}")
    print(f"File size: {size_mb:.2f} MB")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=False,
    )

    model = create_high_accuracy_model(
        number_of_classes=len(CLASSES),
        freeze_backbone=False,
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.eval()

    # Full-resolution desktop model
    export_model(
        model=model,
        output_path=DESKTOP_MODEL_PATH,
        image_size=260,
    )

    # Reduced-resolution mobile model
    export_model(
        model=model,
        output_path=MOBILE_MODEL_PATH,
        image_size=160,
    )

    with open(
        OUTPUT_DIR / "labels.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(CLASSES, file, indent=2)

    if CALIBRATION_PATH.exists():
        shutil.copy2(
            CALIBRATION_PATH,
            OUTPUT_DIR / "calibration.json",
        )

    print("\nBoth ONNX models exported successfully.")


if __name__ == "__main__":
    main()