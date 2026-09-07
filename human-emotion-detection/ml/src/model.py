import torch
from torch import nn
from torchvision.models import (
    MobileNet_V3_Small_Weights,
    mobilenet_v3_small,
)


class EmotionClassifier(nn.Module):
    def __init__(
        self,
        number_of_classes=7,
        dropout=0.3,
        freeze_backbone=True,
    ):
        super().__init__()

        weights = MobileNet_V3_Small_Weights.DEFAULT

        self.model = mobilenet_v3_small(weights=weights)

        if freeze_backbone:
            for parameter in self.model.features.parameters():
                parameter.requires_grad = False

        input_features = self.model.classifier[3].in_features

        self.model.classifier[2] = nn.Dropout(p=dropout)
        self.model.classifier[3] = nn.Linear(
            input_features,
            number_of_classes,
        )

    def forward(self, images):
        return self.model(images)

    def unfreeze_backbone(self):
        for parameter in self.model.features.parameters():
            parameter.requires_grad = True


def create_model(
    number_of_classes=7,
    freeze_backbone=True,
):
    return EmotionClassifier(
        number_of_classes=number_of_classes,
        freeze_backbone=freeze_backbone,
    )


if __name__ == "__main__":
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    model = create_model().to(device)

    test_batch = torch.randn(4, 3, 224, 224).to(device)

    with torch.no_grad():
        output = model(test_batch)

    trainable_parameters = sum(
        parameter.numel()
        for parameter in model.parameters()
        if parameter.requires_grad
    )

    total_parameters = sum(
        parameter.numel()
        for parameter in model.parameters()
    )

    print("Device:", device)
    print("Input shape:", test_batch.shape)
    print("Output shape:", output.shape)
    print("Total parameters:", total_parameters)
    print("Trainable parameters:", trainable_parameters)