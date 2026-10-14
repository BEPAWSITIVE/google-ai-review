import os
import sys
import html

# Test database
import database
database.init_db()
clients = database.list_clients()
print(f"Database initialized. Seeded clients count: {len(clients)}")
assert len(clients) > 0, "Clients should not be empty"
c = clients[0]
print(f"Sample client: {c['name']} (slug: {c['slug']})")

# Test Gemini service fallback
import gemini_service
res = gemini_service.generate_reviews_with_gemini(
    client_name=c["name"],
    category=c["category"],
    keywords_raw=c["keywords"],
    highlights_raw=c["highlights"],
    selected_tags=["Painless Treatment"],
    api_key=""
)
print(f"Generated reviews count: {len(res['reviews'])}, source: {res['source']}")
assert len(res["reviews"]) >= 5, "Should generate at least 5 reviews"
for r in res["reviews"][:3]:
    print(f"  [{r['tag']}] {r['text'][:60]}...")

# Test FastAPI routes via TestClient
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# 1. Dashboard page
r = client.get("/")
assert r.status_code == 200, f"Dashboard failed: {r.status_code}"
assert "Google Review QR Generator" in r.text
print("Dashboard page OK (200)")

# 2. Customer review page
r = client.get(f"/r/{c['slug']}")
assert r.status_code == 200, f"Review page failed: {r.status_code}"
assert c["name"].split()[0] in r.text
print("Customer review page OK (200)")

# 3. Printable flyer
r = client.get(f"/flyer/{c['slug']}")
assert r.status_code == 200, f"Flyer page failed: {r.status_code}"
print("Flyer page OK (200)")

# 4. QR Code image
r = client.get(f"/api/qr/{c['slug']}")
assert r.status_code == 200, f"QR endpoint failed: {r.status_code}"
assert r.headers["content-type"] == "image/png"
assert len(r.content) > 100
print(f"QR code endpoint OK (200, {len(r.content)} bytes PNG)")

# 5. Generate reviews API
r = client.post("/api/generate-reviews", json={"slug": c["slug"], "selected_tags": ["Clean Clinic"]})
assert r.status_code == 200, f"Generate reviews API failed: {r.status_code}"
data = r.json()
assert "reviews" in data and len(data["reviews"]) >= 5
print(f"Generate reviews API OK ({len(data['reviews'])} reviews returned)")

# 6. Create client API
new_client_payload = {
    "name": "Urban Bistro & Cafe",
    "category": "Restaurant & Cafe",
    "google_review_url": "https://search.google.com/local/writereview?placeid=ChIJcafe123",
    "keywords": "authentic wood-fired pizza, artisan coffee, cosy ambience, quick lunch, friendly staff",
    "highlights": "Wood-fired Pizza, Artisan Coffee, Great Vibe, Fast Service",
    "brand_color": "#ea580c",
    "welcome_msg": "Thank you for dining with us! How was your meal today?"
}
r = client.post("/api/clients", json=new_client_payload)
assert r.status_code == 200, f"Create client failed: {r.status_code}"
created = r.json()
print(f"Create client OK: ID {created['id']}, slug: {created['slug']}")

# 7. Config API
r = client.post("/api/config", json={"gemini_api_key": "test_dummy_key_123456789"})
assert r.status_code == 200
r = client.get("/api/config")
assert r.json()["has_gemini_key"] is True
print(f"Config API OK: {r.json()}")

print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY!")
