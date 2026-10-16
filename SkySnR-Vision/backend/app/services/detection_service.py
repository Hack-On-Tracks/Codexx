"""Roboflow hosted inference. Never returns fabricated predictions."""
import base64
import httpx
from fastapi import HTTPException
from ..config import get_settings


def is_configured() -> bool:
    s = get_settings()
    return bool(s.roboflow_api_key and s.roboflow_model_id)


def call_roboflow(image_bytes: bytes) -> dict:
    s = get_settings()
    if not is_configured():
        raise HTTPException(status_code=503,
                            detail="Inference is not configured. Set ROBOFLOW_API_KEY and ROBOFLOW_MODEL_ID.")
    url = f"https://detect.roboflow.com/{s.roboflow_model_id}"
    try:
        r = httpx.post(url, params={"api_key": s.roboflow_api_key, "confidence": s.roboflow_confidence},
                       content=base64.b64encode(image_bytes),
                       headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=60)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="The inference service could not be reached.")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"The inference service returned an error ({r.status_code}).")
    try:
        return r.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="The inference service returned an invalid response.")


def parse_roboflow_response(payload: dict, image_w: int, image_h: int) -> list[dict]:
    """Convert Roboflow's centre-based boxes (x, y, width, height, pixels) to top-left pixel boxes."""
    if not isinstance(payload, dict) or not isinstance(payload.get("predictions"), list):
        raise HTTPException(status_code=502, detail="The inference service returned an unexpected response.")
    img = payload.get("image") or {}
    w = int(img.get("width") or image_w)
    h = int(img.get("height") or image_h)
    out = []
    for p in payload["predictions"]:
        try:
            cx, cy, bw, bh = float(p["x"]), float(p["y"]), float(p["width"]), float(p["height"])
            out.append({"object_class": str(p["class"]), "confidence": float(p["confidence"]),
                        "bounding_box": {"x": cx - bw / 2, "y": cy - bh / 2, "width": bw, "height": bh},
                        "image_width": w, "image_height": h,
                        "model_detection_id": p.get("detection_id")})
        except (KeyError, TypeError, ValueError):
            continue
    return out
