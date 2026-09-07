from pathlib import Path

import kagglehub


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = PROJECT_ROOT / "ml" / "data" / "ferplus"

OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

print("Downloading FERPlus...")

dataset_path = kagglehub.dataset_download(
    "subhaditya/fer2013plus",
    output_dir=str(OUTPUT_DIRECTORY),
)

print("Downloaded to:", dataset_path)

images = list(OUTPUT_DIRECTORY.rglob("*.png"))
images += list(OUTPUT_DIRECTORY.rglob("*.jpg"))
images += list(OUTPUT_DIRECTORY.rglob("*.jpeg"))

print("Images found:", len(images))