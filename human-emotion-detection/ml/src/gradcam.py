import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps

from ml.src.ferplus_dataloader import CLASSES
from ml.src.high_accuracy_model import create_high_accuracy_model
from ml.src.high_accuracy_transforms import (
    get_high_accuracy_evaluation_transforms,
)
from ml.src.predict_custom import crop_largest_face


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "ml/models/checkpoints/best_high_accuracy_model.pt"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml/data/processed/evaluation"
)


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.activations = None
        self.gradients = None

        self.hook = target_layer.register_forward_hook(
            self.save_activations
        )

    def save_activations(self, module, inputs, output):
        self.activations = output.detach()
        output.register_hook(self.save_gradients)

    def save_gradients(self, gradients):
        self.gradients = gradients.detach()

    def generate(self, image_tensor, class_index=None):
        self.model.zero_grad(set_to_none=True)

        outputs = self.model(image_tensor)
        probabilities = torch.softmax(outputs, dim=1)

        if class_index is None:
            class_index = outputs.argmax(dim=1).item()

        outputs[0, class_index].backward()

        weights = self.gradients.mean(
            dim=(2, 3),
            keepdim=True,
        )

        heatmap = (
            weights * self.activations
        ).sum(dim=1)

        heatmap = torch.relu(heatmap)[0]

        heatmap -= heatmap.min()
        heatmap /= heatmap.max().clamp(min=1e-8)

        return (
            heatmap.cpu().numpy(),
            class_index,
            probabilities[0, class_index].item(),
        )

    def close(self):
        self.hook.remove()


def main(image_path):
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    model = create_high_accuracy_model(
        number_of_classes=len(CLASSES),
        freeze_backbone=False,
    ).to(device)

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=device,
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGB")

    face = crop_largest_face(image)
    face = face.convert("L").convert("RGB")

    transform = get_high_accuracy_evaluation_transforms(260)

    image_tensor = (
        transform(face)
        .unsqueeze(0)
        .to(device)
    )

    gradcam = GradCAM(
        model=model,
        target_layer=model.network.features[-1],
    )

    heatmap, class_index, confidence = gradcam.generate(
        image_tensor
    )

    gradcam.close()

    face_array = np.array(face)

    heatmap = cv2.resize(
        heatmap,
        (face.width, face.height),
    )

    heatmap = np.uint8(255 * heatmap)

    colored_heatmap = cv2.applyColorMap(
        heatmap,
        cv2.COLORMAP_JET,
    )

    colored_heatmap = cv2.cvtColor(
        colored_heatmap,
        cv2.COLOR_BGR2RGB,
    )

    overlay = cv2.addWeighted(
        face_array,
        0.55,
        colored_heatmap,
        0.45,
        0,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / "gradcam_overlay.jpg"

    Image.fromarray(overlay).save(output_path)

    print("Prediction:", CLASSES[class_index])
    print(f"Confidence: {confidence * 100:.2f}%")
    print("Grad-CAM saved to:", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "image",
        help="Path to a face image",
    )

    arguments = parser.parse_args()
    main(arguments.image)