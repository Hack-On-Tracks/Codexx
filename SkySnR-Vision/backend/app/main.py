from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from .config import get_settings
from .database import ensure_indexes, get_db
from .routers import auth, detections, incidents, media, missions, reports, users, ml


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if not s.jwt_secret or len(s.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be set to a random string of at least 32 characters")
    ensure_indexes(get_db())
    yield


app = FastAPI(title="SkySnR Vision API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[get_settings().frontend_origin], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth, users, missions, detections, incidents, media, reports, ml):
    app.include_router(r.router)


@app.exception_handler(PyMongoError)
async def db_error(_: Request, __):
    return JSONResponse(status_code=503, content={"detail": "The database is unavailable. Please try again."})


@app.get("/api/health")
def health():
    from .services.detection_service import is_configured
    try:
        get_db().command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    s = get_settings()
    return {"status": "ok", "database": db_ok, "inference_configured": is_configured(),
            "person_classes": sorted(s.person_class_set), "obstacle_classes": sorted(s.obstacle_class_set),
            "max_upload_mb": s.max_upload_mb}
