import pandas as pd

from sklearn.model_selection import train_test_split
from torch.utils.data import Subset

from training.datasets.sign_dataset import SignDataset


def stratified_split(
    dataset,
    csv_file="data/metadata/dataset.csv"
):

    df = pd.read_csv(csv_file)

    indices = list(range(len(df)))
    labels = df["class_index"].values

    # 70% train, 30% temporary
    train_indices, temp_indices = train_test_split(
        indices,
        test_size=0.30,
        stratify=labels,
        random_state=42
    )

    temp_labels = (
        df.iloc[temp_indices]["class_index"].values
    )

    # remaining 30%:
    # 15% validation
    # 15% test
    val_indices, test_indices = train_test_split(
        temp_indices,
        test_size=0.50,
        stratify=temp_labels,
        random_state=42
    )

    train_dataset = Subset(
        dataset,
        train_indices
    )

    val_dataset = Subset(
        dataset,
        val_indices
    )

    test_dataset = Subset(
        dataset,
        test_indices
    )

    return (
        train_dataset,
        val_dataset,
        test_dataset
    )