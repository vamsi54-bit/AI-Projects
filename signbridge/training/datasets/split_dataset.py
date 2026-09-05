import torch
from torch.utils.data import random_split

from training.datasets.sign_dataset import SignDataset

def split_dataset(dataset,train_ratio = 0.75,val_ratio = 0.15):
    total_size = len(dataset)

    train_size = int(
        train_ratio * total_size
    )

    val_size = int(
        val_ratio * total_size
    )

    test_size = (
        total_size - train_size - val_size
    )

    generator = torch.Generator().manual_seed(42)

    train_dataset,test_dataset,val_dataset = (
        random_split(
            dataset,
            [train_size,val_size,test_size], generator = generator
        )
    )

    return (
        train_dataset,
        val_dataset,
        test_dataset
    )

if __name__ == "__main__":

    dataset = SignDataset()

    train_dataset, val_dataset, test_dataset = (
        split_dataset(dataset)
    )

    print(
        "Total:",
        len(dataset)
    )

    print(
        "Train:",
        len(train_dataset)
    )

    print(
        "Validation:",
        len(val_dataset)
    )

    print(
        "Test:",
        len(test_dataset)
    )

    