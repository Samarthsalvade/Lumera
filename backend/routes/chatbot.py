from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Analysis
import os
import json

chatbot_bp = Blueprint('chatbot', __name__)

# ── Groq client setup ─────────────────────────────────────────────────────────
try:
    from groq import Groq
    _groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY', ''))
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    _groq_client = None

SYSTEM_PROMPT = """You are Lumé, an expert AI skincare consultant built into the Luméra app.

Your expertise covers:
- Skin type analysis and care (Normal, Oily, Dry, Combination, Sensitive)
- Skincare ingredients and their benefits/interactions
- Morning and evening routine building
- Product recommendations by skin type and concern
- General dermatology education (not medical diagnosis)

Rules:
- Always personalise your advice using the user's scan history when provided
- Be concise but thorough — use bullet points for routines/lists
- Never diagnose medical conditions; recommend a dermatologist for concerns
- When recommending products, suggest ingredient types (e.g. "a niacinamide serum") not specific brands unless asked
- Keep responses friendly, warm, and actionable
- If the user has no scan history yet, encourage them to do a scan first for personalised advice
"""

def _build_context(user_id: int) -> str:
    """Build a short context string from the user's most recent analyses."""
    analyses = (Analysis.query
                .filter_by(user_id=user_id)
                .order_by(Analysis.created_at.desc())
                .limit(5)
                .all())

    if not analyses:
        return "The user has not completed any skin scans yet."

    lines = ["User's recent skin scan history:"]
    for a in analyses:
        try:
            recs = json.loads(a.recommendations) if isinstance(a.recommendations, str) else a.recommendations
            rec_str = "; ".join(recs[:2])
        except Exception:
            rec_str = ""
        lines.append(
            f"- {a.created_at.strftime('%b %d %Y')}: {a.skin_type} skin "
            f"({a.confidence:.0f}% confidence). Recommendations: {rec_str}"
        )

    latest = analyses[0]
    lines.append(f"\nMost recent skin type: {latest.skin_type}")
    return "\n".join(lines)


@chatbot_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    if not GROQ_AVAILABLE:
        return jsonify({'error': 'Groq package not installed. Run: pip install groq'}), 500

    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'GROQ_API_KEY not set. See README for setup instructions.'}), 500

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body'}), 400

    user_message  = data.get('message', '').strip()
    history       = data.get('history', [])   # [{role, content}, ...]

    if not user_message:
        return jsonify({'error': 'message is required'}), 400

    user_id = int(get_jwt_identity())
    skin_context = _build_context(user_id)

    # Build messages for Groq
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'system', 'content': skin_context},
    ]

    # Include last 10 messages of conversation history for context
    for msg in history[-10:]:
        if msg.get('role') in ('user', 'assistant') and msg.get('content'):
            messages.append({'role': msg['role'], 'content': msg['content']})

    messages.append({'role': 'user', 'content': user_message})

    try:
        completion = _groq_client.chat.completions.create(
            model='llama-3.1-8b-instant',      # free, fast, good quality
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        reply = completion.choices[0].message.content
        return jsonify({'reply': reply}), 200

    except Exception as e:
        err = str(e)
        if 'api_key' in err.lower() or '401' in err:
            return jsonify({'error': 'Invalid GROQ_API_KEY. Check your .env file.'}), 401
        if 'rate' in err.lower():
            return jsonify({'error': 'Rate limit reached. Please wait a moment and try again.'}), 429
        return jsonify({'error': f'Groq error: {err}'}), 500