import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

HERE = Path(__file__).parent
META = json.load(open(HERE / "model_meta.json"))
CLASSES = META["classes"]
WARN_THR = META["energy_warn_threshold"]
CROPS = sorted({c.split("_")[0] for c in CLASSES})   # Pepper, Potato, Tomato

SESSION = ort.InferenceSession(str(HERE / "leaflens.onnx"))
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB").resize((224, 224), Image.BILINEAR)
    x = (np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
    return x.transpose(2, 0, 1)[None]                 # (1, 3, 224, 224)


def predict(img: Image.Image, crop: str):
    logits = SESSION.run(None, {"input": preprocess(img)})[0][0]

    # energy score on the full logits (same definition as in training)
    m = logits.max()
    energy = float(-(m + np.log(np.exp(logits - m).sum())))

    # restrict to the chosen crop's classes
    allowed = np.array([c.split("_")[0] == crop for c in CLASSES])
    masked = np.where(allowed, logits, -1e9)
    p = np.exp(masked - masked.max())
    p /= p.sum()

    top = np.argsort(-p)[:2]
    return {
        "crop": crop,
        "top2": [{"label": CLASSES[i], "index": int(i), "confidence": round(float(p[i]), 3)} for i in top],
        "not_sure": energy > WARN_THR,
        "message": ("Not very sure. Retake the photo in daylight, close to the leaf, "
                    "with the leaf filling the frame.") if energy > WARN_THR else "",
    }