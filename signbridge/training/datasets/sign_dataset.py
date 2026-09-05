import csv
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset


class SignDataset(Dataset):
    def __init__(self, csv_file="data/metadata/metadata.csv"):
        self.csv_file = Path(csv_file)

        if not self.csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")

        self.samples = []

        with open(self.csv_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                self.samples.append({
                    "sequence_file": row["sequence_file"],
                    "label": int(row["class_index"])
                })

        print(f"Dataset loaded: {len(self.samples)} samples")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self,index):
        sample = self.samples[index]

        sequence_path = Path(sample["sequence_file"])

        sequence = np.load(sequence_path)

        sequence = torch.tensor(
            sequence,dtype = torch.float32
        )

        label = torch.tensor(
            sample["label"], dtype = torch.long
        )

        return sequence,label


