import torch
from torch import nn
from torchvision.models import (
    EfficientNet_B2_Weights,
    efficientnet_b2,
)


class HighAccuracyEmotionModel(nn.Module):
    def __init__(
        self,
        number_of_classes=7,
        freeze_backbone=True,
    ):
        super().__init__()

        self.network = efficientnet_b2(
            weights=EfficientNet_B2_Weights.DEFAULT
        )

        input_features = self.network.classifier[1].in_features

        self.network.classifier = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(input_features, 512),
            nn.LayerNorm(512),
            nn.SiLU(),
            nn.Dropout(p=0.3),
            nn.Linear(512, number_of_classes),
        )

        if freeze_backbone:
            self.freeze_backbone()

    def freeze_backbone(self):
        for parameter in self.network.features.parameters():
            parameter.requires_grad = False

    def unfreeze_top_blocks(self, number_of_blocks=3):
        self.freeze_backbone()

        for block in self.network.features[-number_of_blocks:]:
            for parameter in block.parameters():
                parameter.requires_grad = True

    def unfreeze_all(self):
        for parameter in self.network.parameters():
            parameter.requires_grad = True

    def forward(self, images):
        return self.network(images)


def create_high_accuracy_model(
    number_of_classes=7,
    freeze_backbone=True,
):
    return HighAccuracyEmotionModel(
        number_of_classes=number_of_classes,
        freeze_backbone=freeze_backbone,
    )


if __name__ == "__main__":
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    model = create_high_accuracy_model().to(device)
    model.eval()

    sample = torch.randn(2, 3, 260, 260).to(device)

    with torch.inference_mode():
        output = model(sample)

    print("Device:", device)
    print("Input shape:", sample.shape)
    print("Output shape:", output.shape)