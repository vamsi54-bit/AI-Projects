import torch
from torch import nn
from torchvision.models import (
    MobileNet_V3_Small_Weights,
    mobilenet_v3_small,
)


class MobileEmotionModel(nn.Module):
    def __init__(
        self,
        number_of_classes=7,
        pretrained=True,
    ):
        super().__init__()

        weights = (
            MobileNet_V3_Small_Weights.DEFAULT
            if pretrained
            else None
        )

        self.network = mobilenet_v3_small(
            weights=weights
        )

        input_features = (
            self.network.classifier[3].in_features
        )

        self.network.classifier[3] = nn.Linear(
            input_features,
            number_of_classes,
        )

    def forward(self, images):
        return self.network(images)


def create_mobile_emotion_model(
    number_of_classes=7,
    pretrained=True,
):
    return MobileEmotionModel(
        number_of_classes=number_of_classes,
        pretrained=pretrained,
    )


if __name__ == "__main__":
    model = create_mobile_emotion_model()
    sample = torch.randn(1, 3, 160, 160)

    with torch.inference_mode():
        output = model(sample)

    print("Input:", sample.shape)
    print("Output:", output.shape)