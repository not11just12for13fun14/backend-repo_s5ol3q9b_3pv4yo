import os
import uuid
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timezone

from database import db, create_document
from schemas import Track

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def read_root():
    return {"message": "Music Upload API ready"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Helper to build public URLs

def build_media_url(filename: str):
    base = os.getenv("PUBLIC_BACKEND_URL")  # optional explicit public URL
    if base:
        return f"{base}/media/{filename}"
    # Fallback relative path; frontend should prefix with backend base
    return f"/media/{filename}"


@app.post("/api/tracks/upload")
async def upload_track(
    file: UploadFile = File(...),
    title: str = Form(...),
    artist: Optional[str] = Form(None),
    album: Optional[str] = Form(None),
    genre: Optional[str] = Form(None),
    cover_url: Optional[str] = Form(None),
):
    # Validate content type
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Only audio files are allowed")

    # Generate safe unique filename
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)

    # Save file to disk
    try:
        contents = await file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)
        size = len(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create DB record
    try:
        track = Track(
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            cover_url=cover_url,
            filename=unique_name,
            original_filename=file.filename,
            content_type=file.content_type,
            file_size=size,
        )
        inserted_id = create_document("track", track)
    except Exception as e:
        # Rollback saved file if DB fails
        try:
            os.remove(dest_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "_id": inserted_id,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "genre": track.genre,
        "cover_url": track.cover_url,
        "filename": track.filename,
        "original_filename": track.original_filename,
        "content_type": track.content_type,
        "file_size": track.file_size,
        "media_url": build_media_url(track.filename),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/tracks")
def list_tracks(limit: Optional[int] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    cursor = db["track"].find({}).sort("created_at", -1)
    if limit:
        cursor = cursor.limit(limit)
    items = []
    for doc in cursor:
        doc["_id"] = str(doc.get("_id"))
        doc["media_url"] = build_media_url(doc.get("filename"))
        items.append(doc)
    return items


@app.get("/api/tracks/{track_id}")
def get_track(track_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    from bson import ObjectId
    try:
        oid = ObjectId(track_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid track id")

    doc = db["track"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Track not found")
    doc["_id"] = str(doc["_id"])
    doc["media_url"] = build_media_url(doc.get("filename"))
    return doc


@app.get("/media/{filename}")
def serve_media(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")

    # Try to infer content type from DB record for accuracy
    content_type = None
    if db is not None:
        rec = db["track"].find_one({"filename": filename})
        if rec and rec.get("content_type"):
            content_type = rec.get("content_type")

    return FileResponse(path, media_type=content_type)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
