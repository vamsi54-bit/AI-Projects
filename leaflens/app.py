
import io
import base64

import gradio as gr
import spaces
from PIL import Image

from backend.model import CROPS, predict
from backend.gradcam import heatmap_b64
from backend.advice import get_advice, LANGS
from backend.weather import DISTRICTS, get_weather
from backend.rag import passages_for


@spaces.GPU
def _gpu_check():
    # Never called. It only exists so ZeroGPU accepts the Space.
    return True


def analyse(image, crop, lang, district):
    if image is None:
        return "Please upload a leaf photo.", None, "", ""

    if crop == "Other":
        return "This crop isn't supported yet. LeafLens covers: " + ", ".join(CROPS), None, "", ""

    img = Image.fromarray(image) if not isinstance(image, Image.Image) else image
    result = predict(img, crop)

    lines = [f"{t['label']}: {t['confidence'] * 100:.0f}%" for t in result["top2"]]
    text = "\n".join(lines)

    if result["not_sure"]:
        text = result["message"] + "\n\n" + text

    heat = Image.open(
        io.BytesIO(
            base64.b64decode(
                heatmap_b64(img, result["top2"][0]["index"])
            )
        )
    )

    label = result["top2"][0]["label"]

    try:
        passages = passages_for(label, crop)
    except Exception as e:  # RAG must never break the app
        print("RAG error:", repr(e))
        passages = []

    weather_text, weather_note = get_weather(district)
    advice = get_advice(label, crop, lang, weather_note, passages)

    return text, heat, weather_text, advice


demo = gr.Interface(
    fn=analyse,
    inputs=[
        gr.Image(type="numpy", label="Leaf photo"),
        gr.Dropdown(CROPS + ["Other"], value="Tomato", label="Which crop is this?"),
        gr.Dropdown(list(LANGS), value="English", label="Language"),
        gr.Dropdown(list(DISTRICTS), value="Not specified", label="District (for weather advice)"),
    ],
    outputs=[
        gr.Textbox(label="Most likely diseases"),
        gr.Image(label="Where the model looked"),
        gr.Textbox(label="Weather"),
        gr.Markdown(label="Advice"),
    ],
    title="🌿 LeafLens",
    description="Upload a leaf photo and pick the crop. Informational only. Confirm any treatment with a local agriculture officer.",
)


if __name__ == "__main__":
    demo.launch()
