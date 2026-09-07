import type { EmotionPrediction } from "@/lib/emotionInference";

export class PredictionSmoother {
  private history: EmotionPrediction[] = [];

  constructor(private readonly windowSize = 6) {}

  reset() {
    this.history = [];
  }

  update(prediction: EmotionPrediction): EmotionPrediction {
    this.history.push(prediction);
    if (this.history.length > this.windowSize) this.history.shift();

    const probabilities: Record<string, number> = {};
    for (const label of Object.keys(prediction.probabilities)) {
      probabilities[label] =
        this.history.reduce(
          (total, item) => total + (item.probabilities[label] ?? 0),
          0,
        ) / this.history.length;
    }

    let emotion = prediction.emotion;
    let confidence = probabilities[emotion] ?? prediction.confidence;
    for (const [label, probability] of Object.entries(probabilities)) {
      if (probability > confidence) {
        emotion = label;
        confidence = probability;
      }
    }

    return { emotion, confidence, probabilities };
  }
}
