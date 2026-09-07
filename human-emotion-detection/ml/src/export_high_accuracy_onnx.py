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
ONNX_PATH = OUTPUT_DIR / "emotion_model.onnx"

CLASSES = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise",
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=False,
    )

    model = create_high_accuracy_model()

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dummy_input = torch.randn(1, 3, 260, 260)

    torch.onnx.export(
        model,
        dummy_input,
        ONNX_PATH,
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

    onnx_model = onnx.load(ONNX_PATH)
    onnx.checker.check_model(onnx_model)

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

    size_mb = ONNX_PATH.stat().st_size / (1024 * 1024)

    print("ONNX model validated successfully.")
    print(f"Model: {ONNX_PATH}")
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()