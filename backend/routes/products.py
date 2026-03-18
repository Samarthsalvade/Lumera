"""
routes/products.py
──────────────────
Dynamic AI-generated product recommendations using Groq,
enriched with real product images from Open Beauty Facts API.

Flow:
  1. Groq generates product names + metadata for the user's skin type/concerns
  2. For each product, Open Beauty Facts is searched by product name + brand
  3. If a match with an image is found, the real product photo URL is returned
  4. If no match, falls back to branded initial placeholder (same as before)

Open Beauty Facts — completely free, no API key required.
  Search endpoint: https://world.openbeautyfacts.org/cgi/search.pl
  Docs: https://openfoodfacts.github.io/openfoodfacts-server/api/
  License: Open Database License (ODbL)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import os, json, re, urllib.parse
import requests

products_bp = Blueprint('products', __name__)

# Persistent session — OBF requests a descriptive User-Agent
_session = requests.Session()
_session.headers.update({
    'User-Agent': 'Lumera-SkinApp/1.0 (personal skincare project)',
})

OBF_SEARCH = 'https://world.openbeautyfacts.org/cgi/search.pl'


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq():
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        raise ValueError('No GROQ_API_KEY in .env')
    from groq import Groq
    return Groq(api_key=api_key)


# ── Open Beauty Facts image lookup ────────────────────────────────────────────

def _obf_image(product_name: str, brand: str) -> str:
    """
    Search Open Beauty Facts for a real product photo.
    Returns the image_front_url if found, otherwise a placeholder marker.

    OBF has strong coverage of: CeraVe, The Ordinary, La Roche-Posay,
    Neutrogena, Kiehl's, Paula's Choice, Cetaphil, Olay — exactly the
    brands Groq tends to recommend for skincare.
    """
    query = f"{brand} {product_name}".strip()
    params = {
        'search_terms':  query,
        'search_simple': 1,
        'action':        'process',
        'json':          1,
        'page_size':     5,
        'fields':        'product_name,brands,image_front_url,image_url',
    }
    try:
        resp = _session.get(OBF_SEARCH, params=params, timeout=4)
        resp.raise_for_status()
        products = resp.json().get('products', [])

        # Return the first product that has a valid HTTPS image
        for p in products:
            img = p.get('image_front_url') or p.get('image_url')
            if img and img.startswith('https://'):
                return img

    except Exception:
        pass  # Network error or parse failure — fall through to placeholder

    # Placeholder marker — frontend renders a branded initial tile
    return f"placeholder:{brand[0].upper() if brand else 'P'}"


# ── Amazon URL builder ────────────────────────────────────────────────────────

def _amazon_url(product_name: str, brand: str) -> str:
    query   = f"{brand} {product_name}".strip()
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.amazon.com/s?k={encoded}"


# ── Groq product generation ───────────────────────────────────────────────────

def generate_products(skin_type: str, concerns: list, count: int = 5) -> list:
    """
    Ask Groq for real skincare product names, then enrich each with:
      - A real product photo from Open Beauty Facts
      - An Amazon search link
    """
    concern_str = ', '.join([
        f"{c.get('concern_type', '').replace('_', ' ')} ({c.get('severity', '')})"
        for c in concerns if c.get('concern_type')
    ]) or 'general care'

    prompt = f"""You are an expert dermatologist and skincare product specialist.

Patient profile:
- Skin type: {skin_type}
- Primary concerns: {concern_str}

Recommend exactly {count} real, purchasable skincare products available on Amazon.
Choose well-known products from recognisable brands such as CeraVe, The Ordinary,
Neutrogena, La Roche-Posay, Paula's Choice, Olay, Cetaphil, or Kiehl's.
Include a mix of price ranges (budget, mid, premium).

Respond ONLY with a valid JSON array. No markdown, no backticks, no extra text.
Each object must have exactly these fields:
{{
  "product_name": "exact product name as sold on Amazon",
  "brand": "brand name",
  "description": "1-2 sentence description of why this helps",
  "key_ingredients": ["ingredient1", "ingredient2", "ingredient3"],
  "price_range": "budget",
  "concern_tags": ["concern1", "concern2"]
}}

price_range must be exactly one of: budget, mid, premium
Return only the JSON array, nothing else."""

    client = _get_groq()
    completion = client.chat.completions.create(
        model='llama-3.1-8b-instant',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=1200,
    )

    text = completion.choices[0].message.content or '[]'

    # Strip accidental markdown fences
    text = re.sub(r'^```[a-z]*\n?', '', text.strip())
    text = re.sub(r'\n?```$',       '', text.strip())

    parsed = json.loads(text)

    # Some models wrap the array in an object — unwrap if needed
    if isinstance(parsed, dict):
        for key in ('products', 'recommendations', 'items'):
            if key in parsed and isinstance(parsed[key], list):
                parsed = parsed[key]
                break

    result = []
    for p in parsed[:count]:
        name  = p.get('product_name', '')
        brand = p.get('brand', '')
        result.append({
            'product_name':    name,
            'brand':           brand,
            'description':     p.get('description', ''),
            'key_ingredients': p.get('key_ingredients', []),
            'price_range':     p.get('price_range', 'mid'),
            'concern_tags':    p.get('concern_tags', []),
            'amazon_url':      _amazon_url(name, brand),
            # Real product photo from OBF, or placeholder initial tile
            'amazon_image_url': _obf_image(name, brand),
        })

    return result


# ── Route ─────────────────────────────────────────────────────────────────────

@products_bp.route('/recommend', methods=['POST'])
@jwt_required()
def recommend():
    try:
        data      = request.get_json() or {}
        skin_type = data.get('skin_type', 'Normal')
        concerns  = data.get('concerns', [])
        count     = min(int(data.get('count', 5)), 8)

        products = generate_products(skin_type, concerns, count)
        return jsonify({'products': products}), 200

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse AI response: {e}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500