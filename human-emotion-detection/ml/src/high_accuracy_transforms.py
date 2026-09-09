from torchvision import transforms


MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def get_high_accuracy_train_transforms(image_size=260):
    """Mild augmentation that preserves subtle facial-expression details."""
    return transforms.Compose(
        [
            transforms.RandomResizedCrop(
                image_size,
                scale=(0.88, 1.0),
                ratio=(0.94, 1.06),
            ),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=7),
            transforms.RandomAffine(
                degrees=0,
                translate=(0.035, 0.035),
                scale=(0.96, 1.04),
            ),
            transforms.ColorJitter(
                brightness=0.12,
                contrast=0.12,
            ),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
            transforms.RandomErasing(
                p=0.08,
                scale=(0.01, 0.05),
                ratio=(0.5, 2.0),
            ),
        ]
    )


def get_high_accuracy_evaluation_transforms(image_size=260):
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]
    )
