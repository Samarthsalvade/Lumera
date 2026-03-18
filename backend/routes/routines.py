"""
routes/routines.py — Routine builder endpoints
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json, os

from models import db, User, Analysis, Routine, RoutineStep

try:
    from groq import Groq
    GROQ_OK = True
except ImportError:
    GROQ_OK = False

_groq = None  # initialized lazily on first request

def _get_groq():
    global _groq
    if _groq is None and GROQ_OK:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.environ.get('GROQ_API_KEY', '')
        if key:
            _groq = Groq(api_key=key)
    return _groq

routine_bp = Blueprint('routines', __name__)


# ── Generate ──────────────────────────────────────────────────────────────────

@routine_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_routine():
    client = _get_groq()
    if not client:
        return jsonify({'error': 'GROQ_API_KEY not found. Check backend/.env and restart Flask.'}), 503

    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data         = request.get_json() or {}
    routine_type = data.get('routine_type', 'morning')
    analysis_id  = data.get('analysis_id')
    skin_type    = data.get('skin_type', 'normal')
    concerns     = data.get('concerns', [])

    if analysis_id:
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
        if analysis:
            skin_type = analysis.skin_type
            raw = json.loads(analysis.skin_concerns or '{}')
            concerns = [k for k, v in raw.items() if v > 0.2]

    prompt = _build_prompt(routine_type, skin_type, concerns)

    try:
        # ── Correct Groq API call ──────────────────────────────────────────────
        completion = _groq.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.6,
            max_tokens=1024,
        )
        text = completion.choices[0].message.content or ''
        parsed = _parse_routine(text, routine_type, skin_type)

    except Exception as e:
        return jsonify({'error': f'AI generation failed: {e}'}), 500

    try:
        routine = Routine(
            user_id      = user_id,
            routine_type = routine_type,
            name         = parsed.get('name', f'{skin_type.title()} {routine_type.title()} Routine'),
            based_on_scan= analysis_id,
            description  = parsed.get('description', ''),
            is_active    = True,
        )
        db.session.add(routine)
        db.session.flush()

        for i, step in enumerate(parsed.get('steps', []), 1):
            db.session.add(RoutineStep(
                routine_id       = routine.id,
                order            = i,
                product_type     = step.get('product_type', 'Product'),
                instruction      = step.get('instruction', ''),
                duration_seconds = step.get('duration_seconds'),
                key_ingredient   = step.get('key_ingredient'),
            ))

        db.session.commit()
        return jsonify({'success': True, 'routine': routine.to_dict(include_steps=True)}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ── CRUD ──────────────────────────────────────────────────────────────────────

@routine_bp.route('', methods=['GET'])
@jwt_required()
def get_routines():
    user_id  = int(get_jwt_identity())
    routines = Routine.query.filter_by(user_id=user_id).order_by(Routine.routine_type).all()
    return jsonify({'routines': [r.to_dict(include_steps=True) for r in routines]}), 200


@routine_bp.route('/<int:rid>', methods=['GET'])
@jwt_required()
def get_routine(rid):
    user_id = int(get_jwt_identity())
    r = Routine.query.filter_by(id=rid, user_id=user_id).first()
    if not r:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'routine': r.to_dict(include_steps=True)}), 200


@routine_bp.route('/<int:rid>', methods=['PUT'])
@jwt_required()
def update_routine(rid):
    user_id = int(get_jwt_identity())
    r = Routine.query.filter_by(id=rid, user_id=user_id).first()
    if not r:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json() or {}
    if 'name'        in data: r.name        = data['name']
    if 'description' in data: r.description = data['description']
    if 'is_active'   in data: r.is_active   = data['is_active']

    if 'steps' in data:
        RoutineStep.query.filter_by(routine_id=rid).delete()
        for i, s in enumerate(data['steps'], 1):
            db.session.add(RoutineStep(
                routine_id=rid, order=i,
                product_type=s.get('product_type', ''),
                instruction=s.get('instruction', ''),
                duration_seconds=s.get('duration_seconds'),
                key_ingredient=s.get('key_ingredient'),
            ))

    r.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'routine': r.to_dict(include_steps=True)}), 200


@routine_bp.route('/<int:rid>', methods=['DELETE'])
@jwt_required()
def delete_routine(rid):
    user_id = int(get_jwt_identity())
    r = Routine.query.filter_by(id=rid, user_id=user_id).first()
    if not r:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({'success': True}), 200


@routine_bp.route('/<int:rid>/activate', methods=['POST'])
@jwt_required()
def activate_routine(rid):
    user_id = int(get_jwt_identity())
    r = Routine.query.filter_by(id=rid, user_id=user_id).first()
    if not r:
        return jsonify({'error': 'Not found'}), 404
    Routine.query.filter_by(user_id=user_id, routine_type=r.routine_type).update({'is_active': False})
    r.is_active = True
    db.session.commit()
    return jsonify({'routine': r.to_dict()}), 200


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_prompt(routine_type: str, skin_type: str, concerns: list) -> str:
    concern_str = ', '.join(concerns) if concerns else 'none'
    return f"""You are an expert skincare advisor. Generate a {routine_type} skincare routine for {skin_type} skin with concerns: {concern_str}.

Respond in EXACTLY this format (no markdown, no extra text):

ROUTINE_NAME: [name]
DESCRIPTION: [1-2 sentences]

STEPS:
1. [Product Type] | [Instruction] | [seconds] | [key ingredient]
2. [Product Type] | [Instruction] | [seconds] | [key ingredient]
3. [Product Type] | [Instruction] | [seconds] | [key ingredient]
4. [Product Type] | [Instruction] | [seconds] | [key ingredient]
5. [Product Type] | [Instruction] | [seconds] | [key ingredient]

Example step:
1. Cleanser | Gently massage onto damp skin for 60 seconds then rinse | 60 | salicylic acid

Generate 4-6 steps appropriate for {routine_type}. Be specific and actionable."""


def _parse_routine(text: str, routine_type: str, skin_type: str) -> dict:
    import re
    result = {
        'name':        f'{skin_type.title()} {routine_type.title()} Routine',
        'description': f'AI-generated {routine_type} routine for {skin_type} skin.',
        'steps':       [],
    }

    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith('ROUTINE_NAME:'):
            result['name'] = line.replace('ROUTINE_NAME:', '').strip()
        elif line.startswith('DESCRIPTION:'):
            result['description'] = line.replace('DESCRIPTION:', '').strip()
        elif line and line[0].isdigit() and '|' in line:
            # Format: "1. Product Type | Instruction | seconds | ingredient"
            clean = re.sub(r'^\d+\.\s*', '', line)
            parts = [p.strip() for p in clean.split('|')]
            if len(parts) >= 2:
                duration = None
                if len(parts) >= 3:
                    m = re.search(r'(\d+)', parts[2])
                    if m:
                        duration = int(m.group(1))
                result['steps'].append({
                    'product_type':     parts[0],
                    'instruction':      parts[1],
                    'duration_seconds': duration,
                    'key_ingredient':   parts[3] if len(parts) >= 4 else None,
                })

    # Fallback if parsing failed
    if not result['steps']:
        result['steps'] = [
            {'product_type': 'Cleanser',    'instruction': 'Gently cleanse face with lukewarm water', 'duration_seconds': 60,  'key_ingredient': 'ceramides'},
            {'product_type': 'Moisturizer', 'instruction': 'Apply moisturizer to face and neck',      'duration_seconds': 90,  'key_ingredient': 'hyaluronic acid'},
            {'product_type': 'Sunscreen',   'instruction': 'Apply SPF 30+ sunscreen evenly',          'duration_seconds': 120, 'key_ingredient': 'zinc oxide'},
        ]
    return result