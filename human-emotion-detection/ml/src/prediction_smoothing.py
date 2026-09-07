from collections import deque

import numpy as np
import torch

from ml.src.ferplus_dataloader import CLASSES


class PredictionSmoother:
    def __init__(
        self,
        window_size=8,
        confidence_threshold=0.50,
        margin_threshold=0.12,
        temperature=1.0,
    ):
        self.history = deque(maxlen=window_size)
        self.confidence_threshold = confidence_threshold
        self.margin_threshold = margin_threshold
        self.temperature = temperature

    def reset(self):
        self.history.clear()

    def update(self, logits):
        logits = torch.as_tensor(
            logits,
            dtype=torch.float32,
        ).flatten()

        probabilities = torch.softmax(
            logits / self.temperature,
            dim=0,
        ).numpy()

        self.history.append(probabilities)

        smoothed = np.mean(
            np.stack(self.history),
            axis=0,
        )

        sorted_indices = np.argsort(smoothed)[::-1]

        best_index = int(sorted_indices[0])
        second_index = int(sorted_indices[1])

        confidence = float(smoothed[best_index])
        margin = float(
            smoothed[best_index]
            - smoothed[second_index]
        )

        if (
            confidence < self.confidence_threshold
            or margin < self.margin_threshold
        ):
            emotion = "uncertain"
        else:
            emotion = CLASSES[best_index]

        return {
            "emotion": emotion,
            "confidence": confidence,
            "margin": margin,
            "probabilities": {
                name: float(smoothed[index])
                for index, name in enumerate(CLASSES)
            },
        }


if __name__ == "__main__":
    smoother = PredictionSmoother()

    sample_logits = [
        [0.2, 0.1, 0.1, 3.0, 0.4, 0.2, 0.3],
        [0.3, 0.1, 0.2, 2.7, 0.5, 0.2, 0.4],
        [0.2, 0.1, 0.1, 3.2, 0.3, 0.2, 0.3],
    ]

    for logits in sample_logits:
        result = smoother.update(logits)
        print(result["emotion"], result["confidence"])