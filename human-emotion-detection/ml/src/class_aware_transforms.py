from torchvision import transforms
from torchvision.transforms import InterpolationMode

from ml.src.high_accuracy_transforms import (
    get_high_accuracy_evaluation_transforms,
    get_high_accuracy_train_transforms,
)


IMAGENET_MEAN = [
    0.485,
    0.456,
    0.406,
]

IMAGENET_STD = [
    0.229,
    0.224,
    0.225,
]


def get_normal_train_transform(image_size=260):
    return get_high_accuracy_train_transforms(
        image_size
    )


def get_minority_train_transform(image_size=260):
    return transforms.Compose(
        [
            transforms.RandomResizedCrop(
                image_size,
                scale=(0.78, 1.0),
                ratio=(0.90, 1.10),
                interpolation=(
                    InterpolationMode.BILINEAR
                ),
            ),
            transforms.RandomHorizontalFlip(
                p=0.5
            ),
            transforms.RandomRotation(
                degrees=8,
                interpolation=(
                    InterpolationMode.BILINEAR
                ),
            ),
            transforms.RandomApply(
                [
                    transforms.ColorJitter(
                        brightness=0.18,
                        contrast=0.18,
                        saturation=0.12,
                        hue=0.02,
                    )
                ],
                p=0.6,
            ),
            transforms.RandomPerspective(
                distortion_scale=0.08,
                p=0.12,
            ),
            transforms.RandomGrayscale(
                p=0.03
            ),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=IMAGENET_MEAN,
                std=IMAGENET_STD,
            ),
            transforms.RandomErasing(
                p=0.08,
                scale=(0.02, 0.08),
                ratio=(0.5, 2.0),
                value="random",
            ),
        ]
    )


def get_evaluation_transform(image_size=260):
    return get_high_accuracy_evaluation_transforms(
        image_size
    )