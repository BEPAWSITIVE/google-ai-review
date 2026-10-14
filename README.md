# Google Review QR & AI Revert Platform

A complete solution for agencies and local businesses to gather high-converting 5-star Google Reviews optimized with target SEO keywords.

## Features
- **Client & Business Management**: Add businesses with their category, target keywords, Google review URL, and brand color.
- **Dynamic QR Generator & Printable Stand Cards**:
  - Instant QR code generation linking to the customer review page.
  - Download PNG QR codes.
  - Ready-to-print Table Tent / Counter Stand flyers (`/flyer/{slug}`).
- **Customer Mobile Experience (`/r/{slug}`)**:
  - Automatically loads 5 to 10 natural, keyword-rich review reverts using **Google Gemini Flash** (with fallback smart templates).
  - **"Regenerate"** button to instantly get fresh variations.
  - **Click-to-Copy**: Tapping any review draft selects and copies it to the clipboard.
  - **Editable Preview**: Customers can edit or add their own touch.
  - **"Next: Post on Google"**: Ensures clipboard copy with toast feedback and directly launches the client's Google Review dialog in a new tab!

## Running the Webapp
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.
