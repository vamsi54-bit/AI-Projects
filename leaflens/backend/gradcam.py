import base64, io
from pathlib import Path

import numpy as np
import timm, torch
from PIL import Image
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

from backend.model import CLASSES, MEAN, STD, preprocess

_ckpt = torch.load(Path(__file__).parent / "effnet_b0_field.pt", map_location="cpu")
_model = timm.create_model("efficientnet_b0", pretrained=False, num_classes=len(CLASSES))
_model.load_state_dict(_ckpt["model"])
_model.eval()
_cam = GradCAM(model=_model, target_layers=[_model.conv_head])


def heatmap_b64(img: Image.Image, class_idx: int) -> str:
    x = torch.from_numpy(preprocess(img))
    grayscale = _cam(input_tensor=x, targets=[ClassifierOutputTarget(class_idx)])[0]
    rgb = np.asarray(img.convert("RGB").resize((224, 224)), dtype=np.float32) / 255.0
    overlay = show_cam_on_image(rgb, grayscale, use_rgb=True)
    buf = io.BytesIO()
    Image.fromarray(overlay).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()