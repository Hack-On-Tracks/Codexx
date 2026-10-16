import io
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from ..config import get_settings

ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


async def read_image_upload(file: UploadFile) -> tuple[bytes, str, int, int]:
    s = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext in VIDEO:
        raise HTTPException(status_code=415,
                            detail="Video analysis is not supported yet. Upload a single image frame (JPG, PNG or WebP).")
    if ext not in ALLOWED:
        raise HTTPException(status_code=415, detail="Unsupported file type. Use JPG, PNG or WebP.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is larger than {s.max_upload_mb} MB.")
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="The file is not a valid image.")
    return data, ext, w, h


def save_media(folder: str, data: bytes, ext: str) -> str:
    d = get_settings().media_dir / folder
    d.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (d / name).write_bytes(data)
    return f"{folder}/{name}"
