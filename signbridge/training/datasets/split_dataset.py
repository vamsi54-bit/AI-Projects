import re
import random

from torch.utils.data import Subset
from training.datasets.sign_dataset import SignDataset


def get_group_name(path, label):

    name = path.replace("\\", "/").split("/")[-1]

    name = re.sub(
        r"_(left_tilt|right_tilt)(?=\.npy$)",
        "",
        name
    )

    return f"{label}_{name}"


def grouped_stratified_split(dataset):

    random.seed(42)

    class_groups = {}

    # group samples class-wise
    for index, sample in enumerate(dataset.samples):

        label = sample["label"]

        group = get_group_name(
            sample["sequence_file"],
            label
        )

        class_groups.setdefault(
            label, {}
        )

        class_groups[label].setdefault(
            group, []
        ).append(index)


    train_idx = []
    val_idx = []
    test_idx = []


    # split every class separately
    for label, groups_dict in class_groups.items():

        groups = list(groups_dict.keys())

        random.shuffle(groups)

        total = len(groups)

        train_end = int(total * 0.70)
        val_end = int(total * 0.85)

        train_groups = groups[:train_end]
        val_groups = groups[train_end:val_end]
        test_groups = groups[val_end:]


        for group in train_groups:
            train_idx.extend(
                groups_dict[group]
            )

        for group in val_groups:
            val_idx.extend(
                groups_dict[group]
            )

        for group in test_groups:
            test_idx.extend(
                groups_dict[group]
            )


    return (
        Subset(dataset, train_idx),
        Subset(dataset, val_idx),
        Subset(dataset, test_idx)
    )


if __name__ == "__main__":

    dataset = SignDataset()

    train, val, test = (
        grouped_stratified_split(dataset)
    )

    print("Train:", len(train))
    print("Val:", len(val))
    print("Test:", len(test))