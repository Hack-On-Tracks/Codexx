"""Detection provider interface. bbox convention: [x1, y1, x2, y2] in source-image pixels, origin top-left."""
import os, httpx
from abc import ABC, abstractmethod
class ProviderError(Exception): pass
def validate(r):
    if not isinstance(r, dict) or not isinstance(r.get("detections"), list): raise ProviderError("Invalid model response: missing detections list")
    for x in r["detections"]:
        b = x.get("bbox")
        if not isinstance(x.get("class_name"), str) or not isinstance(x.get("confidence"), (int, float)) or not 0 <= x["confidence"] <= 1: raise ProviderError("Invalid detection fields")
        if not (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)): raise ProviderError("Invalid bbox")
    return r
class DetectionProvider(ABC):
    @abstractmethod
    def get_model_status(self) -> dict: ...
    @abstractmethod
    def predict_image(self, path: str) -> dict: ...
    @abstractmethod
    def predict_video(self, path: str) -> dict: ...
    @abstractmethod
    def get_supported_classes(self) -> list: ...
class ExternalDetectionProvider(DetectionProvider):
    """Calls a Python inference service: GET /health, GET /classes, POST /predict/image, POST /predict/video (multipart 'file')."""
    def __init__(self, url, timeout=120): self.url, self.timeout = (url or "").rstrip("/"), timeout
    def get_model_status(self):
        if not self.url: return {"state": "not_configured", "message": "No model endpoint configured (MODEL_URL is empty).", "model_version": None}
        try:
            h = httpx.get(self.url + "/health", timeout=5).json(); return {"state": "ready", "model_version": h.get("model_version"), "message": "Model service reachable."}
        except Exception as e: return {"state": "failed", "model_version": None, "message": f"Model service unreachable: {type(e).__name__}"}
    def _post(self, ep, path):
        if not self.url: raise ProviderError("Model not configured")
        try:
            with open(path, "rb") as f: r = httpx.post(self.url + ep, files={"file": (os.path.basename(path), f)}, timeout=self.timeout)
            r.raise_for_status(); return validate(r.json())
        except httpx.TimeoutException: raise ProviderError("Model request timed out")
        except httpx.HTTPError as e: raise ProviderError(f"Model request failed: {e}")
    def predict_image(self, path): return self._post("/predict/image", path)
    def predict_video(self, path): return self._post("/predict/video", path)
    def get_supported_classes(self):
        try: return httpx.get(self.url + "/classes", timeout=5).json()
        except Exception: return []
SCENARIOS = {"flood": ("Flood Rescue", "flood", "Easy"), "earthquake": ("Earthquake Aftermath", "earthquake", "Hard"), "landslide": ("Landslide Response", "landslide", "Medium"),
             "urban": ("Urban Disaster Search", "other", "Hard"), "custom": ("Custom Training Scenario", "other", "Easy")}
BASE = [("person", .91, [420, 260, 500, 420]), ("person", .78, [900, 540, 960, 660]), ("car", .88, [200, 500, 420, 620]), ("debris", .69, [1200, 300, 1400, 420]), ("fallen tree", .74, [600, 100, 1000, 200]), ("truck", .83, [1300, 600, 1650, 780])]
class DemoDetectionProvider(DetectionProvider):
    """Deterministic fixtures. ONLY for explicitly labeled Simulation Mode."""
    def get_model_status(self): return {"state": "ready", "model_version": "simulation-fixtures", "message": "SIMULATION — NOT LIVE RESCUE DATA"}
    def predict_image(self, path): return self.fixtures("flood")
    def predict_video(self, path): return self.fixtures("flood")
    def get_supported_classes(self): return sorted({b[0] for b in BASE})
    def fixtures(self, key, frames=6):
        out = []
        for f in range(frames):
            for i, (c, cf, b) in enumerate(BASE):
                if (i + f + len(key)) % 5 == 0: continue
                s = f * 14; out.append({"class_name": c, "confidence": round(max(.5, cf - f * .01), 2), "bbox": [b[0] + s, b[1], b[2] + s, b[3]], "frame_index": f,
                                        "timestamp_seconds": f * 1.0, "track_id": f"sim-t{i}" if c == "person" else None})
        return {"model_version": "simulation-fixtures", "image_width": 1920, "image_height": 1080, "detections": out}
