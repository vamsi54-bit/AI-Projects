"""Audit FERPlus image quality and labels without modifying the dataset.

Run from the project root:
python -m ml.src.audit_label_quality --checkpoint path/to/model.pt
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import torch
from PIL import Image, ImageFile, ImageStat
from torchvision import transforms
from tqdm import tqdm

from ml.src.high_accuracy_model import create_high_accuracy_model


ImageFile.LOAD_TRUNCATED_IMAGES = False
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "ml/data/ferplus/fer2013plus/fer2013"
DEFAULT_OUTPUT = PROJECT_ROOT / "ml/data/processed/quality_audit"
CLASSES = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
LABEL_ALIASES = {
    "anger": "angry",
    "angry": "angry",
    "disgust": "disgust",
    "fear": "fear",
    "happiness": "happy",
    "happy": "happy",
    "neutral": "neutral",
    "sadness": "sad",
    "sad": "sad",
    "surprise": "surprise",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a safe FERPlus label-quality review list.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-size", type=int, default=260)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--disagreement-confidence", type=float, default=0.85)
    parser.add_argument("--blur-threshold", type=float, default=18.0)
    return parser.parse_args()


def discover(dataset: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for split in ("train", "val", "test"):
        split_dir = dataset / split
        if not split_dir.exists() and split == "val":
            split_dir = dataset / "validation"
        if not split_dir.exists():
            print(f"Warning: missing split: {split_dir}")
            continue
        for class_dir in sorted(path for path in split_dir.iterdir() if path.is_dir()):
            label = LABEL_ALIASES.get(class_dir.name.lower())
            if label is None:
                continue
            for path in class_dir.rglob("*"):
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                    records.append({"path": path, "split": split, "label": label})
    return records


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_metrics(path: Path) -> tuple[float, float, int, int]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        gray = image.convert("L")
        width, height = gray.size
        pixels = torch.tensor(list(gray.getdata()), dtype=torch.float32).reshape(height, width)
        if width > 1 and height > 1:
            sharpness = float(
                ((pixels[:, 1:] - pixels[:, :-1]).square().mean()
                 + (pixels[1:, :] - pixels[:-1, :]).square().mean()).item()
            )
        else:
            sharpness = 0.0
        brightness = float(ImageStat.Stat(gray).mean[0])
    return sharpness, brightness, width, height


def load_model(checkpoint_path: Path, device: torch.device) -> torch.nn.Module:
    model = create_high_accuracy_model(number_of_classes=len(CLASSES), freeze_backbone=False)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    state = checkpoint.get("model_state_dict", checkpoint.get("state_dict", checkpoint))
    model.load_state_dict(state)
    model.to(device).eval()
    return model


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = arguments()
    dataset = args.dataset.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    records = discover(dataset)
    if not records:
        raise FileNotFoundError(f"No images found under {dataset}")

    review_rows: list[dict[str, object]] = []
    usable: list[dict[str, object]] = []
    hashes: defaultdict[str, list[dict[str, object]]] = defaultdict(list)

    print(f"Auditing {len(records)} images...")
    for record in tqdm(records, desc="Integrity and quality"):
        path = record["path"]
        assert isinstance(path, Path)
        row = {"path": str(path), "split": record["split"], "given_label": record["label"]}
        try:
            sharpness, brightness, width, height = image_metrics(path)
            digest = file_hash(path)
            row.update({
                "sha256": digest, "width": width, "height": height,
                "sharpness": round(sharpness, 3), "brightness": round(brightness, 3),
            })
            hashes[digest].append(record)
            usable.append({**record, **row})
            reasons = []
            if sharpness < args.blur_threshold:
                reasons.append("very_blurry")
            if brightness < 25:
                reasons.append("very_dark")
            elif brightness > 235:
                reasons.append("overexposed")
            if min(width, height) < 40:
                reasons.append("very_small")
            if reasons:
                review_rows.append({**row, "reason": ";".join(reasons)})
        except Exception as error:
            review_rows.append({**row, "reason": "corrupt_or_unreadable", "details": str(error)})

    duplicate_rows: list[dict[str, object]] = []
    leakage_hashes: set[str] = set()
    for digest, group in hashes.items():
        if len(group) < 2:
            continue
        splits = {str(item["split"]) for item in group}
        labels = {str(item["label"]) for item in group}
        if len(splits) > 1:
            leakage_hashes.add(digest)
        for item in group:
            duplicate_rows.append({
                "sha256": digest, "path": str(item["path"]), "split": item["split"],
                "label": item["label"], "group_size": len(group),
                "cross_split": len(splits) > 1, "cross_label": len(labels) > 1,
            })

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(args.checkpoint.resolve(), device)
    transform = transforms.Compose([
        transforms.Resize((args.image_size, args.image_size)),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    print(f"Checking labels on {device}...")
    for start in tqdm(range(0, len(usable), args.batch_size), desc="Model review"):
        batch_records = usable[start:start + args.batch_size]
        tensors, valid_records = [], []
        for record in batch_records:
            try:
                with Image.open(record["path"]) as image:
                    tensors.append(transform(image.convert("RGB")))
                valid_records.append(record)
            except Exception:
                continue
        if not tensors:
            continue
        with torch.inference_mode():
            probabilities = torch.softmax(model(torch.stack(tensors).to(device)), dim=1).cpu()
        top_probabilities, top_indices = probabilities.max(dim=1)
        for record, confidence, index, distribution in zip(
            valid_records, top_probabilities.tolist(), top_indices.tolist(), probabilities.tolist()
        ):
            prediction = CLASSES[index]
            if prediction != record["label"] and confidence >= args.disagreement_confidence:
                review_rows.append({
                    **record,
                    "given_label": record["label"], "predicted_label": prediction,
                    "confidence": round(confidence, 6),
                    "probabilities": json.dumps(dict(zip(CLASSES, distribution))),
                    "reason": "high_confidence_label_disagreement",
                })

    review_fields = [
        "path", "split", "given_label", "predicted_label", "confidence", "reason",
        "sharpness", "brightness", "width", "height", "sha256", "probabilities", "details",
    ]
    duplicate_fields = ["sha256", "path", "split", "label", "group_size", "cross_split", "cross_label"]
    write_csv(output / "label_review.csv", review_rows, review_fields)
    write_csv(output / "duplicate_groups.csv", duplicate_rows, duplicate_fields)

    summary = {
        "dataset": str(dataset), "total_images": len(records), "readable_images": len(usable),
        "review_rows": len(review_rows), "duplicate_images": len(duplicate_rows),
        "cross_split_leakage_groups": len(leakage_hashes),
        "class_counts": dict(Counter(str(item["label"]) for item in usable)),
        "note": "Nothing was deleted. Manually review label_review.csv before changing labels.",
    }
    (output / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Review list: {output / 'label_review.csv'}")
    print(f"Duplicates: {output / 'duplicate_groups.csv'}")


if __name__ == "__main__":
    main()