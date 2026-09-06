from torch.utils.data import DataLoader

from training.datasets.sign_dataset import SignDataset
from training.datasets.split_dataset import stratified_split


BATCH_SIZE = 32


def create_dataloaders(
    batch_size=BATCH_SIZE
):

    dataset = SignDataset()

    train_dataset, val_dataset, test_dataset = (
        stratified_split(dataset)
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    return (
        train_loader,
        val_loader,
        test_loader
    )