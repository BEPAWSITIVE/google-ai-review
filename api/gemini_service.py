import os
import json
import random
import requests
from typing import List, Dict, Any, Optional

def get_api_key(db_key: Optional[str] = None) -> str:
    if db_key and db_key.strip():
        return db_key.strip()
    return os.environ.get("GEMINI_API_KEY", "").strip()

def generate_fallback_reviews(client_name: str, category: str, keywords: List[str], selected_tags: List[str]) -> List[Dict[str, Any]]:
    """Smart fallback generator if Gemini API key is not configured or in case of network issue."""
    kw_str = ", ".join(keywords[:3]) if keywords else "exceptional service and quality"
    tag_str = ", ".join(selected_tags) if selected_tags else "overall experience"
    
    k1 = keywords[0] if len(keywords) > 0 else "fantastic service"
    k2 = keywords[1] if len(keywords) > 1 else "friendly and professional team"
    k3 = keywords[2] if len(keywords) > 2 else "top-notch experience"
    k4 = keywords[3] if len(keywords) > 3 else "clean and welcoming atmosphere"
    
    templates = [
        {
            "tag": "Short & Sweet",
            "text": f"Had an outstanding experience with {client_name}! Truly {k1} and courteous staff. 5 stars all the way!"
        },
        {
            "tag": "Detailed & Professional",
            "text": f"I can confidently recommend {client_name}. From start to finish, the entire process was smooth, professional, and well-managed. Their focus on {k1} and {k2} really sets them apart. Will definitely be returning!"
        },
        {
            "tag": "Warm & Friendly",
            "text": f"Such a delightful experience! The team at {client_name} was super welcoming and attentive. You can tell they genuinely care about their customers. Special mention for their {k2}!"
        },
        {
            "tag": "First-Time Customer",
            "text": f"It was my first time visiting {client_name}, and they exceeded all expectations. Everything was seamless, especially the {k1}. If you are looking for reliable {category.lower()}, this is the place to go!"
        },
        {
            "tag": "Value & Quality",
            "text": f"Top quality and honest service at {client_name}. Transparent pricing, {k3}, and zero hassle. It is rare to find businesses with this level of dedication!"
        },
        {
            "tag": "Staff & Service Focus",
            "text": f"The staff at {client_name} are exceptionally skilled and polite. They took the time to explain everything and ensured {k2}. Great atmosphere and wonderful hospitality!"
        },
        {
            "tag": "Highest Recommendation",
            "text": f"Best {category.lower()} in town! {client_name} provides impeccable service, with {k1} and {k4}. Do not hesitate to check them out!"
        },
        {
            "tag": "Quick & Efficient",
            "text": f"Super fast, efficient, and thoroughly professional. {client_name} handled everything with great care and {k3}. Highly satisfied with the results!"
        }
    ]
    
    # Shuffle slightly to provide variety on regeneration
    random.shuffle(templates)
    for idx, item in enumerate(templates):
        item["id"] = idx + 1
    return templates

def generate_reviews_with_gemini(
    client_name: str,
    category: str,
    keywords_raw: str,
    highlights_raw: str,
    selected_tags: List[str],
    api_key: str
) -> Dict[str, Any]:
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    highlights = [h.strip() for h in highlights_raw.split(",") if h.strip()]
    
    clean_key = get_api_key(api_key)
    if not clean_key:
        reviews = generate_fallback_reviews(client_name, category, keywords, selected_tags)
        return {
            "source": "smart_templates",
            "message": "Generated using optimized review templates. Add your Gemini API Key in Settings to enable live AI personalization.",
            "reviews": reviews
        }
    
    # Construct prompt for Gemini
    keywords_prompt = ", ".join(keywords) if keywords else "great service, friendly staff, highly recommended"
    focus_prompt = f"Customer highlighted points: {', '.join(selected_tags)}" if selected_tags else "General positive customer satisfaction"

    prompt = f"""You are an expert local SEO and customer review specialist.
Generate exactly 7 distinct, genuine, natural-sounding 5-star Google review drafts for a business.
Customers will scan a QR code at this business, pick their favorite review draft, copy it, and paste it directly onto Google Reviews.

Business Information:
- Business Name: {client_name}
- Industry / Category: {category}
- Priority SEO Keywords to naturally include: {keywords_prompt}
- Specific highlights to touch upon: {focus_prompt}

Guidelines for the Reviews:
1. Tone: Warm, authentic, human, and conversational. NEVER sound like promotional ad copy or robot-generated text.
2. Diversity of lengths and styles:
   - 1-2 Short & punchy reviews (1-2 sentences, ideal for busy people).
   - 2-3 Moderate reviews (2-3 sentences mentioning staff, quality, or atmosphere).
   - 2 Detailed reviews (3-4 sentences outlining the pleasant experience).
3. Naturally weave in 1 or 2 of the provided keywords in each review so it boosts Google search rankings without keyword-stuffing.
4. Do NOT use fake names, bracket placeholders like [Doctor], or hashtags.
5. Return ONLY a valid JSON array of objects with the exact format:
[
  {{
    "id": 1,
    "tag": "Short & Sweet",
    "text": "Review text here..."
  }},
  ...
]
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={clean_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.85,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code != 200:
            # Fallback to gemini-1.5-flash if 2.5 is unavailable
            url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
            response = requests.post(url_fallback, json=payload, timeout=20)
            
        if response.status_code == 200:
            res_json = response.json()
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            reviews = json.loads(raw_text)
            if isinstance(reviews, list) and len(reviews) > 0:
                for idx, r in enumerate(reviews):
                    r["id"] = idx + 1
                    if "tag" not in r:
                        r["tag"] = "Review Option"
                return {
                    "source": "gemini_ai",
                    "message": "AI reviews generated successfully via Gemini API.",
                    "reviews": reviews
                }
        
        # If API returned error code, fallback gracefully
        error_msg = f"Gemini API returned status {response.status_code}: {response.text[:200]}"
        print(error_msg)
        reviews = generate_fallback_reviews(client_name, category, keywords, selected_tags)
        return {
            "source": "smart_templates_fallback",
            "message": f"Gemini API issue ({response.status_code}). Showing smart templates.",
            "reviews": reviews
        }
    except Exception as e:
        print(f"Exception calling Gemini: {e}")
        reviews = generate_fallback_reviews(client_name, category, keywords, selected_tags)
        return {
            "source": "smart_templates_fallback",
            "message": f"Could not reach Gemini ({str(e)}). Showing smart templates.",
            "reviews": reviews
        }
