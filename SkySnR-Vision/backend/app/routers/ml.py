import io, json
from pathlib import Path
from functools import lru_cache
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from ..dependencies import require_manager

router = APIRouter(prefix="/api/ml", tags=["machine-learning"])
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "aider_classifier.keras"
CLASSES_PATH = MODEL_PATH.with_name("class_names.json")

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.is_file() or not CLASSES_PATH.is_file():
        raise HTTPException(status_code=503, detail="AIDER model files are missing from backend/models.")
    try:
        import tensorflow as tf
        model = tf.keras.models.load_model(MODEL_PATH, compile=False)
        classes = json.loads(CLASSES_PATH.read_text(encoding="utf-8"))
        return model, classes
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not load AIDER classifier: {type(exc).__name__}. Check TensorFlow installation and model compatibility.")

@router.get("/status")
def model_status(_=Depends(require_manager)):
    return {"configured": MODEL_PATH.is_file() and CLASSES_PATH.is_file(), "task": "image_classification", "classes": json.loads(CLASSES_PATH.read_text()) if CLASSES_PATH.is_file() else [], "model_file": "backend/models/aider_classifier.keras"}

@router.post("/classify")
async def classify_image(file: UploadFile = File(...), _=Depends(require_manager)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, or WebP image.")
    raw = await file.read()
    if not raw or len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is empty or exceeds the 10 MB limit.")
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB").resize((224, 224))
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.")
    model, classes = load_model()
    arr = np.asarray(image, dtype=np.float32) / 255.0
    try:
        scores = np.asarray(model.predict(np.expand_dims(arr, 0), verbose=0))[0].reshape(-1)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {type(exc).__name__}.")
    if len(scores) != len(classes):
        raise HTTPException(status_code=500, detail="Model output count does not match class_names.json.")
    ranked = sorted([{"label": classes[i], "confidence": round(float(scores[i]), 6)} for i in range(len(classes))], key=lambda x: x["confidence"], reverse=True)
    return {"task": "image_classification", "prediction": ranked[0], "probabilities": ranked, "note": "Image-level disaster classification only; this model does not return object bounding boxes or detect people/vehicles."}
