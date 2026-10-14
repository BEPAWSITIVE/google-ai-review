import sqlite3
import os
import re
import tempfile
from typing import Optional, List, Dict, Any

if os.environ.get("VERCEL"):
    DB_PATH = os.path.join(tempfile.gettempdir(), "reviews_app.db")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "reviews_app.db")

def _get_raw_conn():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        fallback_path = os.path.join(tempfile.gettempdir(), "reviews_app.db")
        conn = sqlite3.connect(fallback_path)
        conn.row_factory = sqlite3.Row
        return conn

_db_initialized = False

def init_db():
    conn = _get_raw_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        category TEXT DEFAULT 'Business',
        google_review_url TEXT NOT NULL,
        keywords TEXT DEFAULT '',
        highlights TEXT DEFAULT '',
        brand_color TEXT DEFAULT '#2563eb',
        welcome_msg TEXT DEFAULT 'Thank you for choosing us! We would love your feedback.',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    conn.commit()

    # Seed sample client if table is empty
    cursor.execute("SELECT COUNT(*) FROM clients")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO clients (name, slug, category, google_review_url, keywords, highlights, brand_color, welcome_msg)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Apex Dental & Aesthetic Care",
            "apex-dental",
            "Dental Clinic",
            "https://search.google.com/local/writereview?placeid=ChIJN1t_tDeuEmsRUsoyG83frY4",
            "painless treatment, friendly dentists, modern equipment, hygienic clinic, gentle cleaning, best root canal, clear pricing",
            "Painless Treatment, Gentle Staff, Clean Clinic, Quick Booking, Great Doctor",
            "#0d9488",
            "We hope you had a comfortable visit! Help others discover our gentle care by sharing a quick review."
        ))
        conn.commit()
    conn.close()

def get_db():
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f"Error initializing db: {e}")
    return _get_raw_conn()

try:
    init_db()
    _db_initialized = True
except Exception:
    pass

def generate_slug(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
    if not slug:
        slug = "business"
    # Ensure uniqueness
    conn = get_db()
    cursor = conn.cursor()
    base_slug = slug
    counter = 1
    while True:
        cursor.execute("SELECT id FROM clients WHERE slug = ?", (slug,))
        if not cursor.fetchone():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    conn.close()
    return slug

def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["value"]
    return os.environ.get(key, default)

def set_setting(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

import base64
import json

def encode_client_payload(client: Dict[str, Any]) -> str:
    compact = {
        "n": client.get("name", ""),
        "c": client.get("category", ""),
        "u": client.get("google_review_url", ""),
        "k": client.get("keywords", ""),
        "h": client.get("highlights", ""),
        "b": client.get("brand_color", "#2563eb"),
        "w": client.get("welcome_msg", "")
    }
    raw = json.dumps(compact, separators=(',', ':')).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def decode_client_payload(payload_str: str) -> Optional[Dict[str, Any]]:
    try:
        padding = "=" * (-len(payload_str) % 4)
        raw = base64.urlsafe_b64decode(payload_str + padding)
        data = json.loads(raw.decode("utf-8"))
        name = data.get("n", "Business")
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
        return {
            "name": name,
            "slug": slug,
            "category": data.get("c", "Business"),
            "google_review_url": data.get("u", ""),
            "keywords": data.get("k", ""),
            "highlights": data.get("h", ""),
            "brand_color": data.get("b", "#2563eb"),
            "welcome_msg": data.get("w", "Thank you for visiting! We would love your review.")
        }
    except Exception:
        return None

def upsert_client(client_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    name = client_data.get("name", "Business")
    slug = client_data.get("slug") or re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
    category = client_data.get("category", "Business")
    google_review_url = client_data.get("google_review_url", "")
    keywords = client_data.get("keywords", "")
    highlights = client_data.get("highlights", "")
    brand_color = client_data.get("brand_color", "#2563eb")
    welcome_msg = client_data.get("welcome_msg", "Thank you for visiting!")

    cursor.execute("SELECT id FROM clients WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
        UPDATE clients
        SET name=?, category=?, google_review_url=?, keywords=?, highlights=?, brand_color=?, welcome_msg=?
        WHERE slug=?
        """, (name, category, google_review_url, keywords, highlights, brand_color, welcome_msg, slug))
        client_id = row["id"]
    else:
        cursor.execute("""
        INSERT INTO clients (name, slug, category, google_review_url, keywords, highlights, brand_color, welcome_msg)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, slug, category, google_review_url, keywords, highlights, brand_color, welcome_msg))
        client_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_client_by_id(client_id)

def list_clients() -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["payload"] = encode_client_payload(d)
        results.append(d)
    return results

def get_client_by_id(client_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["payload"] = encode_client_payload(d)
        return d
    return None

def get_client_by_slug(slug: str, fallback_payload: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["payload"] = encode_client_payload(d)
        return d
    
    # If not found in database but fallback payload is provided (e.g. from QR code query parameter)
    if fallback_payload:
        decoded = decode_client_payload(fallback_payload)
        if decoded:
            return upsert_client(decoded)
            
    return None

def create_client(name: str, category: str, google_review_url: str, keywords: str, highlights: str, brand_color: str, welcome_msg: str) -> Dict[str, Any]:
    slug = generate_slug(name)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO clients (name, slug, category, google_review_url, keywords, highlights, brand_color, welcome_msg)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, slug, category, google_review_url, keywords, highlights, brand_color or '#2563eb', welcome_msg))
    client_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_client_by_id(client_id)

def update_client(client_id: int, name: str, category: str, google_review_url: str, keywords: str, highlights: str, brand_color: str, welcome_msg: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE clients
    SET name = ?, category = ?, google_review_url = ?, keywords = ?, highlights = ?, brand_color = ?, welcome_msg = ?
    WHERE id = ?
    """, (name, category, google_review_url, keywords, highlights, brand_color, welcome_msg, client_id))
    conn.commit()
    conn.close()
    return get_client_by_id(client_id)

def delete_client(client_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
