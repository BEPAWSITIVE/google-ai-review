import os
import io
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import qrcode

import database
import gemini_service

app = FastAPI(title="ReviewPulse API Service")
router = APIRouter()

# Models
class ClientCreate(BaseModel):
    name: str
    category: Optional[str] = "Business"
    google_review_url: str
    keywords: Optional[str] = ""
    highlights: Optional[str] = ""
    brand_color: Optional[str] = "#2563eb"
    welcome_msg: Optional[str] = "Thank you for visiting! How was your experience today?"

class ClientUpdate(BaseModel):
    name: str
    category: Optional[str] = "Business"
    google_review_url: str
    keywords: Optional[str] = ""
    highlights: Optional[str] = ""
    brand_color: Optional[str] = "#2563eb"
    welcome_msg: Optional[str] = "Thank you for visiting! How was your experience today?"

class ConfigUpdate(BaseModel):
    gemini_api_key: str

class GenerateReviewRequest(BaseModel):
    slug: str
    selected_tags: Optional[List[str]] = []
    d: Optional[str] = None
    api_key: Optional[str] = None

class ClientSyncItem(BaseModel):
    name: str
    slug: Optional[str] = None
    category: Optional[str] = "Business"
    google_review_url: str
    keywords: Optional[str] = ""
    highlights: Optional[str] = ""
    brand_color: Optional[str] = "#2563eb"
    welcome_msg: Optional[str] = "Thank you for visiting!"

def resolve_public_base_url(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8000"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    return f"{proto}://{host}"

@router.get("/clients")
async def api_list_clients():
    return database.list_clients()

@router.post("/clients")
async def api_create_client(client_in: ClientCreate):
    client = database.create_client(
        name=client_in.name,
        category=client_in.category or "Business",
        google_review_url=client_in.google_review_url,
        keywords=client_in.keywords or "",
        highlights=client_in.highlights or "",
        brand_color=client_in.brand_color or "#2563eb",
        welcome_msg=client_in.welcome_msg or "Thank you for visiting! We would love your review."
    )
    return client

@router.get("/clients/{client_id}")
async def api_get_client(client_id: int):
    client = database.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/clients/{client_id}")
async def api_update_client(client_id: int, client_in: ClientUpdate):
    updated = database.update_client(
        client_id=client_id,
        name=client_in.name,
        category=client_in.category or "Business",
        google_review_url=client_in.google_review_url,
        keywords=client_in.keywords or "",
        highlights=client_in.highlights or "",
        brand_color=client_in.brand_color or "#2563eb",
        welcome_msg=client_in.welcome_msg or "Thank you for visiting!"
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Client not found")
    return updated

@router.delete("/clients/{client_id}")
async def api_delete_client(client_id: int):
    success = database.delete_client(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"success": True}

@router.post("/clients/sync")
async def api_sync_clients(clients: List[ClientSyncItem]):
    synced = []
    for c in clients:
        data = c.dict()
        res = database.upsert_client(data)
        synced.append(res)
    return synced

@router.get("/config")
async def api_get_config():
    key = database.get_setting("gemini_api_key", "")
    return {
        "has_gemini_key": bool(key.strip()),
        "masked_key": (key[:4] + "..." + key[-4:]) if len(key) > 8 else ("Set" if key else "")
    }

@router.post("/config")
async def api_save_config(cfg: ConfigUpdate):
    database.set_setting("gemini_api_key", cfg.gemini_api_key.strip())
    return {"success": True, "message": "Gemini API key saved successfully."}

@router.get("/qr")
@router.get("/qr/{slug}")
async def api_get_qr(request: Request, slug: Optional[str] = None, d: Optional[str] = None, url: Optional[str] = None):
    if url:
        target_url = url
    elif slug:
        client = database.get_client_by_slug(slug, fallback_payload=d)
        base_url = resolve_public_base_url(request)
        payload = d or (client.get("payload") if client else "")
        param = f"?d={payload}" if payload else ""
        target_url = f"{base_url}/r/{slug}{param}"
    else:
        raise HTTPException(status_code=400, detail="Missing slug or url")
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@router.post("/generate-reviews")
async def api_generate_reviews(payload: GenerateReviewRequest):
    client = database.get_client_by_slug(payload.slug, fallback_payload=payload.d)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    api_key = payload.api_key or database.get_setting("gemini_api_key", "")
    result = gemini_service.generate_reviews_with_gemini(
        client_name=client["name"],
        category=client["category"] or "Business",
        keywords_raw=client["keywords"] or "",
        highlights_raw=client["highlights"] or "",
        selected_tags=payload.selected_tags or [],
        api_key=api_key
    )
    return result

# Route matching for both /... and /api/... prefixes
app.include_router(router)
app.include_router(router, prefix="/api")
