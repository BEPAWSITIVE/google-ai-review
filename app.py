import os
import io
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import qrcode

import database
import gemini_service

app = FastAPI(title="Google Review QR & AI Revert Platform")
def get_resource_dir(name: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, name),
        os.path.join(base, "api", name),
        os.path.join(os.getcwd(), name),
        os.path.join(os.getcwd(), "api", name),
        f"/var/task/{name}",
        f"/var/task/api/{name}"
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    fallback = os.path.join(base, name)
    os.makedirs(fallback, exist_ok=True)
    return fallback

STATIC_DIR = get_resource_dir("static")
TEMPLATES_DIR = get_resource_dir("templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def resolve_public_base_url(request: Request) -> str:
    """Accurately resolves public URL whether behind reverse proxy/ngrok or localhost."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8000"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    return f"{proto}://{host}"

# Initialize SQLite database on startup
@app.on_event("startup")
def startup_event():
    database.init_db()

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

import requests

# Web Pages
@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    api_url = os.environ.get("API_URL")
    clients = []
    is_key_set = False
    masked_key = ""

    if api_url:
        try:
            res = requests.get(f"{api_url.rstrip('/')}/clients", timeout=3)
            if res.status_code == 200:
                clients = res.json()
        except Exception:
            pass

        try:
            res = requests.get(f"{api_url.rstrip('/')}/config", timeout=3)
            if res.status_code == 200:
                cfg = res.json()
                is_key_set = cfg.get("has_gemini_key", False)
                masked_key = cfg.get("masked_key", "")
        except Exception:
            pass

    if not clients:
        clients = database.list_clients()

    if not masked_key and not is_key_set:
        api_key = database.get_setting("gemini_api_key", "")
        is_key_set = bool(api_key.strip())
        masked_key = (api_key[:4] + "..." + api_key[-4:]) if len(api_key) > 8 else ("Set" if is_key_set else "")

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "clients": clients,
            "is_key_set": is_key_set,
            "masked_key": masked_key,
            "public_base_url": resolve_public_base_url(request)
        }
    )

@app.get("/r/{slug}", response_class=HTMLResponse)
@app.get("/review/{slug}", response_class=HTMLResponse)
async def customer_review_page(request: Request, slug: str, d: Optional[str] = None):
    client = None
    api_url = os.environ.get("API_URL")
    if api_url:
        try:
            res = requests.get(f"{api_url.rstrip('/')}/clients", timeout=3)
            if res.status_code == 200:
                for c in res.json():
                    if c.get("slug") == slug:
                        client = c
                        break
        except Exception:
            pass

    if not client:
        client = database.get_client_by_slug(slug, fallback_payload=d)

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    raw_highlights = client["highlights"] or ""
    tags = [t.strip() for t in raw_highlights.split(",") if t.strip()]
    if not tags:
        tags = ["Staff Courtesy", "Quick Service", "High Quality", "Great Ambience", "Fair Pricing", "Clean & Hygienic"]
        
    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "client": client,
            "tags": tags,
            "payload": d or client.get("payload", "")
        }
    )

@app.get("/flyer/{slug}", response_class=HTMLResponse)
async def printable_flyer_page(request: Request, slug: str, d: Optional[str] = None):
    client = None
    api_url = os.environ.get("API_URL")
    if api_url:
        try:
            res = requests.get(f"{api_url.rstrip('/')}/clients", timeout=3)
            if res.status_code == 200:
                for c in res.json():
                    if c.get("slug") == slug:
                        client = c
                        break
        except Exception:
            pass

    if not client:
        client = database.get_client_by_slug(slug, fallback_payload=d)

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    base_url = resolve_public_base_url(request)
    payload = d or client.get("payload", "")
    param = f"?d={payload}" if payload else ""
    review_url = f"{base_url}/r/{slug}{param}"
    qr_img_url = f"/api/qr/{slug}{param}"
    
    return templates.TemplateResponse(
        request=request,
        name="flyer.html",
        context={
            "client": client,
            "review_url": review_url,
            "qr_img_url": qr_img_url
        }
    )

# API Routes
@app.get("/api/clients")
async def api_list_clients():
    return database.list_clients()

@app.post("/api/clients")
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

@app.get("/api/clients/{client_id}")
async def api_get_client(client_id: int):
    client = database.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@app.put("/api/clients/{client_id}")
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

@app.delete("/api/clients/{client_id}")
async def api_delete_client(client_id: int):
    success = database.delete_client(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"success": True}

@app.get("/api/config")
async def api_get_config():
    key = database.get_setting("gemini_api_key", "")
    return {
        "has_gemini_key": bool(key.strip()),
        "masked_key": (key[:4] + "..." + key[-4:]) if len(key) > 8 else ("Set" if key else "")
    }

@app.post("/api/config")
async def api_save_config(cfg: ConfigUpdate):
    database.set_setting("gemini_api_key", cfg.gemini_api_key.strip())
    return {"success": True, "message": "Gemini API key saved successfully."}

@app.post("/api/clients/sync")
async def api_sync_clients(clients: List[ClientSyncItem]):
    synced = []
    for c in clients:
        data = c.dict()
        res = database.upsert_client(data)
        synced.append(res)
    return synced

@app.get("/api/qr")
@app.get("/api/qr/{slug}")
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

@app.post("/api/generate-reviews")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
