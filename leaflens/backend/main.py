import io

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image

from backend.model import CROPS, predict
from backend.gradcam import heatmap_b64
from pathlib import Path
from fastapi.responses import FileResponse

app = FastAPI(title="LeafLens")


@app.get("/health")
def health():
    return {"status": "ok", "crops": CROPS}


@app.post("/predict")
async def predict_endpoint(file: UploadFile = File(...), crop: str = Form(...)):
    if crop == "Other":
        return {"supported": False,
                "message": "This crop isn't supported yet. LeafLens covers: " + ", ".join(CROPS)}
    if crop not in CROPS:
        raise HTTPException(400, f"crop must be one of {CROPS} or 'Other'")
    try:
        img = Image.open(io.BytesIO(await file.read()))
    except Exception:
        raise HTTPException(400, "Could not read that image.")
    result = predict(img, crop)
    result["heatmap_png_base64"] = heatmap_b64(img, result["top2"][0]["index"])
    return {"supported": True, **result}

FRONTEND = Path(__file__).parent.parent / "frontend"

@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")