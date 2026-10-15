import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from inference_sdk import InferenceHTTPClient

# Load environment variables from backend/.env
load_dotenv()

app = FastAPI(title="SkySnR Vision Detection API")

# Allow requests from the local Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Roboflow configuration
API_KEY = os.getenv("ROBOFLOW_API_KEY")
MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID")

client = None

if API_KEY and MODEL_ID:
    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=API_KEY,
    )


@app.get("/")
def home():
    return {
        "message": "SkySnR Vision API is running",
        "model_configured": client is not None,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/detect")
async def detect(file: UploadFile = File(...)):
    if client is None:
        raise HTTPException(
            status_code=500,
            detail="Configure ROBOFLOW_API_KEY and ROBOFLOW_MODEL_ID in backend/.env",
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp"}

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, PNG, or WebP image.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image size must be 10 MB or less.",
        )

    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp:
            temp.write(content)
            temp_path = temp.name

        result = client.infer(temp_path, model_id=MODEL_ID)
        return result

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Roboflow inference failed. Check your model ID, API key, and network connection.",
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
