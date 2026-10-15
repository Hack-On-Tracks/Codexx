
import os
import uuid
import shutil
from pathlib import Path
from collections import Counter

import cv2
import numpy as np
from ultralytics import YOLO
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "yolo11n.pt"
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

CONFIDENCE = 0.25
IMAGE_SIZE = 1280

PERSON_COLOR = (40, 40, 255)      # Red, BGR
VEHICLE_COLOR = (255, 120, 30)   # Blue, BGR
OBSTACLE_COLOR = (0, 165, 255)   # Orange, reserved for future model

# --------------------------------------------------
# INITIALIZE APP AND MODEL
# --------------------------------------------------

app = FastAPI(title="SkySnR Vision API", version="1.0.0")

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

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

if not MODEL_PATH.exists():
    raise RuntimeError(
        f"Model not found at {MODEL_PATH}. "
        "Place yolo11n.pt in backend/models/"
    )

model = YOLO(str(MODEL_PATH))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# COCO class IDs used by yolo11n.pt
PERSON_ID = 0
CAR_ID = 2
BUS_ID = 5
TRUCK_ID = 7


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "project": "SkySnR Vision",
        "model": MODEL_PATH.name,
        "supported_detection_classes": [
            "person", "car", "bus", "truck"
        ],
    }


# --------------------------------------------------
# FRAME PROCESSING
# --------------------------------------------------

def process_frame(frame):
    """Run YOLO and draw numbered people and cars."""

    result = model.predict(
        source=frame,
        conf=CONFIDENCE,
        imgsz=IMAGE_SIZE,
        verbose=False,
    )[0]

    annotated = frame.copy()
    detections = []

    for box in result.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())

        x1, y1, x2, y2 = map(
            int, box.xyxy[0].tolist()
        )

        if class_id == PERSON_ID:
            label = "person"
            color = PERSON_COLOR
        elif class_id == CAR_ID:
            label = "car"
            color = VEHICLE_COLOR
        elif class_id in (BUS_ID, TRUCK_ID):
            label = model.names[class_id]
            color = VEHICLE_COLOR
        else:
            continue

        detections.append({
            "class": label,
            "confidence": round(confidence, 3),
            "bbox": [x1, y1, x2, y2],
        })

    # Number people and cars separately
    person_index = 0
    car_index = 0

    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]
        label = detection["class"]
        color = (
            PERSON_COLOR if label == "person"
            else VEHICLE_COLOR
        )

        if label == "person":
            person_index += 1
            display_label = f"Person {person_index}"
        elif label == "car":
            car_index += 1
            display_label = f"Car {car_index}"
        else:
            display_label = None

        cv2.rectangle(
            annotated, (x1, y1), (x2, y2), color, 2
        )

        if display_label:
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.55
            thickness = 2

            (tw, th), baseline = cv2.getTextSize(
                display_label, font, scale, thickness
            )

            label_top = max(0, y1 - th - baseline - 8)

            cv2.rectangle(
                annotated,
                (x1, label_top),
                (min(x1 + tw + 8, annotated.shape[1] - 1),
                 label_top + th + baseline + 6),
                color,
                -1,
            )

            cv2.putText(
                annotated,
                display_label,
                (x1 + 4, label_top + th + 2),
                font,
                scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )

    counts = Counter(d["class"] for d in detections)

    return annotated, detections, {
        "people": counts["person"],
        "cars": counts["car"],
        "buses": counts["bus"],
        "trucks": counts["truck"],
        "vehicles": counts["car"] + counts["bus"] + counts["truck"],
    }


# --------------------------------------------------
# IMAGE ANALYSIS
# --------------------------------------------------

@app.post("/api/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Upload a supported image file."
        )

    job_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{job_id}{extension}"
    output_path = OUTPUT_DIR / f"{job_id}_annotated.jpg"

    try:
        with input_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        frame = cv2.imread(str(input_path))

        if frame is None:
            raise HTTPException(
                status_code=400,
                detail="Could not decode the image."
            )

        annotated, detections, counts = process_frame(frame)

        if not cv2.imwrite(str(output_path), annotated):
            raise HTTPException(
                status_code=500,
                detail="Could not save the annotated image."
            )

        return {
            "job_id": job_id,
            "media_type": "image",
            "status": "completed",
            "result_url": f"/outputs/{output_path.name}",
            "counts": counts,
            "detections": detections,
            "message": "Image analysis completed.",
        }

    finally:
        await file.close()
        input_path.unlink(missing_ok=True)


# --------------------------------------------------
# VIDEO SIMULATION
# --------------------------------------------------

@app.post("/api/analyze/video")
async def analyze_video(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Upload an MP4, AVI, MOV, or MKV video."
        )

    job_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{job_id}{extension}"
    output_path = OUTPUT_DIR / f"{job_id}_simulation.mp4"

    cap = None
    writer = None

    try:
        with input_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        cap = cv2.VideoCapture(str(input_path))

        if not cap.isOpened():
            raise HTTPException(
                status_code=400,
                detail="Could not open the uploaded video."
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width <= 0 or height <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid video dimensions."
            )

        if fps <= 0 or not np.isfinite(fps):
            fps = 25.0

        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )

        if not writer.isOpened():
            raise HTTPException(
                status_code=500,
                detail="Could not initialize video output."
            )

        totals = Counter()
        timeline = []
        frame_index = 0

        while True:
            ok, frame = cap.read()

            if not ok:
                break

            annotated, detections, counts = process_frame(frame)
            writer.write(annotated)

            totals.update(counts)

            # Record sampled frame events for the UI.
            # These are per-frame counts, not unique people.
            if frame_index % max(1, round(fps)) == 0:
                timeline.append({
                    "timestamp_seconds": round(frame_index / fps, 2),
                    "frame": frame_index,
                    "counts": counts,
                    "detections": detections,
                })

            frame_index += 1

        writer.release()
        writer = None
        cap.release()
        cap = None

        if frame_index == 0:
            raise HTTPException(
                status_code=400,
                detail="The video contained no readable frames."
            )

        return {
            "job_id": job_id,
            "media_type": "video",
            "status": "completed",
            "video_url": f"/outputs/{output_path.name}",
            "duration_seconds": round(frame_index / fps, 2),
            "processed_frames": frame_index,
            "total_frames_reported": total_frames,
            "counts": {
                "people_frame_detections": totals["people"],
                "car_frame_detections": totals["cars"],
                "bus_frame_detections": totals["buses"],
                "truck_frame_detections": totals["trucks"],
            },
            "timeline": timeline,
            "message": (
                "Video processing completed. "
                "Counts represent detections across frames, "
                "not unique objects."
            ),
        }

    finally:
        if cap is not None:
            cap.release()
        if writer is not None:
            writer.release()

        await file.close()
        input_path.unlink(missing_ok=True)


# --------------------------------------------------
# SIMULATION SUMMARY
# --------------------------------------------------

@app.get("/api/stats")
def stats():
    return {
        "model": MODEL_PATH.name,
        "confidence_threshold": CONFIDENCE,
        "supported_classes": ["person", "car", "bus", "truck"],
        "simulation_mode": "uploaded_media",
        "note": (
            "Object counts are model detections, not verified "
            "rescue targets or unique tracked identities."
        ),
    }
