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


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "checkpoints"
    / "best_high_accuracy_model.pt"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "processed"
    / "evaluation"
)


def crop_largest_face(image):
    rgb_image = np.array(image)

    gray_image = cv2.cvtColor(
        rgb_image,
        cv2.COLOR_RGB2GRAY,
    )

    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    if detector.empty():
        raise RuntimeError("OpenCV face detector could not load.")

    faces = detector.detectMultiScale(
        gray_image,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )

    if len(faces) == 0:
        print("Warning: no face detected; using complete image.")
        return image

    x, y, width, height = max(
        faces,
        key=lambda face: face[2] * face[3],
    )

    center_x = x + width // 2
    center_y = y + height // 2

    # Add 10% padding on each side
    side = int(max(width, height) * 1.20)
    side = min(side, image.width, image.height)

    left = center_x - side // 2
    top = center_y - side // 2

    left = max(0, min(left, image.width - side))
    top = max(0, min(top, image.height - side))

    right = left + side
    bottom = top + side

    cropped_face = image.crop(
        (left, top, right, bottom)
    )

    print("Face detected and cropped.")

    return cropped_face


def load_model(device):
    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {CHECKPOINT_PATH}"
        )

    model = create_high_accuracy_model(
        number_of_classes=len(CLASSES),
        freeze_backbone=False,
    ).to(device)

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location=device,
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.eval()

    return model


@torch.inference_mode()
def predict(image_path):
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    model = load_model(device)

    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGB")

    face = crop_largest_face(image)

    # FERPlus contains grayscale images
    face = face.convert("L").convert("RGB")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cropped_face_path = OUTPUT_DIR / "custom_face_crop.jpg"
    face.save(cropped_face_path)

    transform = get_high_accuracy_evaluation_transforms(
        image_size=260
    )

    image_tensor = (
        transform(face)
        .unsqueeze(0)
        .to(device)
    )

    flipped_tensor = torch.flip(
        image_tensor,
        dims=[3],
    )

    normal_probabilities = torch.softmax(
        model(image_tensor),
        dim=1,
    )

    flipped_probabilities = torch.softmax(
        model(flipped_tensor),
        dim=1,
    )

    probabilities = (
        normal_probabilities
        + flipped_probabilities
    ) / 2

    probabilities = probabilities[0]

    top_probabilities, top_indices = torch.topk(
        probabilities,
        k=3,
    )

    print("\nTop facial-expression predictions:")

    for probability, index in zip(
        top_probabilities,
        top_indices,
    ):
        emotion = CLASSES[index.item()]
        confidence = probability.item() * 100

        print(f"{emotion}: {confidence:.2f}%")

    best_confidence = top_probabilities[0].item()
    best_emotion = CLASSES[top_indices[0].item()]

    if best_confidence < 0.50:
        print("\nFinal result: Uncertain")
    else:
        print(f"\nFinal result: {best_emotion}")

    print(f"Cropped face saved to: {cropped_face_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Predict a facial expression from an image."
    )

    parser.add_argument(
        "image",
        help="Path to the image",
    )

    arguments = parser.parse_args()
    predict(arguments.image)