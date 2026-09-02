from pathlib import Path

DATASET_PATH = Path("data/raw/isl_videos")

if not DATASET_PATH.exists():
    print("Dataset directory does not exist.")
    exit()

folders = [x for x in DATASET_PATH.iterdir() if x.is_dir()]

print("Number of folders/classes:", len(folders))

for folder in folders[:20]:

    videos = list(folder.glob("*.mp4"))

    print(
        folder.name,
        "->",
        len(videos),
        "videos"
    )