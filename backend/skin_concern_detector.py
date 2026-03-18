"""
skin_concern_detector.py
────────────────────────
Hybrid concern detection:
  ML model (concern_model.keras) — acne, blackheads, dark_circles,
                                   dark_spots→hyperpigmentation, redness, texture
  Calibrated CV signals          — eye_bags, lip_hyperpigmentation

Classes in concern_model.keras (alphabetical = training order):
  0 acne  1 blackheads  2 dark_circles  3 dark_spots  4 redness  5 texture
"""

import cv2
import numpy as np
import base64
from typing import Dict, Tuple, Optional, List
import os


# ── Zone definitions ───────────────────────────────────────────────────────────
ZONES = {
    'forehead':       (0.04, 0.28, 0.22, 0.78),
    'left_cheek':     (0.38, 0.72, 0.04, 0.38),
    'right_cheek':    (0.38, 0.72, 0.62, 0.96),
    'nose':           (0.32, 0.65, 0.36, 0.64),
    'chin':           (0.72, 0.92, 0.28, 0.72),
    'left_eye':       (0.18, 0.36, 0.10, 0.42),
    'right_eye':      (0.18, 0.36, 0.58, 0.90),
    'under_left_eye': (0.32, 0.44, 0.10, 0.42),
    'under_right_eye':(0.32, 0.44, 0.58, 0.90),
    'lip':            (0.65, 0.82, 0.30, 0.70),
    't_zone':         (0.04, 0.72, 0.30, 0.70),
    'face_centre':    (0.15, 0.85, 0.15, 0.85),
}

CONCERN_ZONES: Dict[str, List[str]] = {
    'acne':                  ['left_cheek', 'right_cheek', 'forehead', 'chin'],
    'redness':               ['face_centre'],
    'dark_circles':          ['under_left_eye', 'under_right_eye'],
    'eye_bags':              ['under_left_eye', 'under_right_eye'],
    'blackheads':            ['nose', 'chin'],
    'lip_hyperpigmentation': ['lip'],
    'texture':               ['left_cheek', 'right_cheek', 'forehead'],
    'hyperpigmentation':     ['face_centre'],
    'dryness':               ['face_centre'],
}

SEVERITY_COLORS: Dict[str, Tuple[int, int, int]] = {
    'mild':     (34, 197, 94),
    'moderate': (234, 179, 8),
    'severe':   (239, 68, 68),
}

ZONE_LABELS: Dict[str, str] = {
    'forehead':       'Forehead',
    'left_cheek':     'Left cheek',
    'right_cheek':    'Right cheek',
    'nose':           'Nose',
    'chin':           'Chin',
    'left_eye':       'Left eye',
    'right_eye':      'Right eye',
    'under_left_eye': 'Under-eye L',
    'under_right_eye':'Under-eye R',
    'lip':            'Lip',
    't_zone':         'T-zone',
    'face_centre':    'Face',
}


def _crop(img: np.ndarray, zone: str) -> np.ndarray:
    h, w = img.shape[:2]
    y1, y2, x1, x2 = ZONES[zone]
    region = img[int(h*y1):int(h*y2), int(w*x1):int(w*x2)]
    return region if region.size > 0 else img


def _skin_tone_factor(img_rgb: np.ndarray) -> float:
    centre = _crop(img_rgb, 'face_centre')
    lab    = cv2.cvtColor(centre, cv2.COLOR_RGB2LAB)
    L_mean = float(np.mean(lab[:, :, 0]))
    return float(np.clip(L_mean / 200.0, 0.2, 1.0))


# ── CV signals (eye_bags + lip only) ──────────────────────────────────────────

def _signal_eye_bags(img_rgb: np.ndarray) -> float:
    bag_scores = []
    for eye_zone, under_zone in [('left_eye', 'under_left_eye'), ('right_eye', 'under_right_eye')]:
        eye   = _crop(img_rgb, eye_zone)
        under = _crop(img_rgb, under_zone)
        if eye.size == 0 or under.size == 0:
            continue
        eye_L   = float(np.mean(cv2.cvtColor(eye,   cv2.COLOR_RGB2LAB)[:, :, 0]))
        under_L = float(np.mean(cv2.cvtColor(under, cv2.COLOR_RGB2LAB)[:, :, 0]))
        abs_delta = under_L - eye_L

        # Lowered gate: 3.0 instead of 8.0 — catches mild puffiness
        if abs_delta < 3.0:
            bag_scores.append(0.0)
            continue

        # Smaller divisor (15.0 instead of 25.0) so moderate deltas score meaningfully
        s1 = (abs_delta - 3.0) / 15.0

        # Row variance — lowered floor from 5.0 to 2.0, smaller divisor
        gray_u = cv2.cvtColor(under, cv2.COLOR_RGB2GRAY).astype(float)
        s2 = max(0, float(np.std(np.mean(gray_u, axis=1))) - 2.0) / 20.0 if gray_u.shape[0] > 2 else 0.0

        # Also add a small horizontal variance signal — bags create
        # a horizontal ridge that increases row-to-row std
        s3 = 0.0
        if gray_u.shape[0] > 3:
            row_means = np.mean(gray_u, axis=1)
            s3 = float(np.std(np.diff(row_means))) / 15.0

        bag_scores.append(np.clip(s1 * 0.6 + s2 * 0.25 + s3 * 0.15, 0, 1))

    if not bag_scores:
        return 0.0
    return round(float(np.clip(np.mean(bag_scores), 0, 1)), 3)


def _signal_lip_hyperpigmentation(img_rgb: np.ndarray, tone: float) -> float:
    lip   = _crop(img_rgb, 'lip')
    cheek = _crop(img_rgb, 'face_centre')
    if lip.size == 0:
        return 0.0
    lip_L   = float(np.mean(cv2.cvtColor(lip,   cv2.COLOR_RGB2LAB)[:, :, 0]))
    cheek_L = float(np.mean(cv2.cvtColor(cheek, cv2.COLOR_RGB2LAB)[:, :, 0]))
    s1 = max(0, (cheek_L - lip_L) / (cheek_L + 1e-9)) * 2.0
    lip_hsv = cv2.cvtColor(lip, cv2.COLOR_RGB2HSV)
    purple  = cv2.inRange(lip_hsv, (120, 20, 20), (160, 255, 255))
    s2 = float(np.sum(purple > 0)) / purple.size * 3.0
    return round(float(np.clip((s1 + s2) * tone, 0, 1)), 3)


# ── Calibration ────────────────────────────────────────────────────────────────

def _calibrate(scores: Dict[str, float], tone: float) -> Dict[str, float]:
    calibrated = dict(scores)

    if calibrated.get('acne', 0) > 0.35:
        calibrated['redness'] = min(1.0, calibrated.get('redness', 0) + 0.06)

    # Lower gate for CV-only signals — they score in a smaller range
    CV_ONLY = {'eye_bags', 'lip_hyperpigmentation'}
    for k in list(calibrated.keys()):
        gate = 0.08 if k in CV_ONLY else 0.15
        if calibrated[k] < gate:
            calibrated[k] = 0.0
        else:
            calibrated[k] = round(float(np.clip(calibrated[k], 0.0, 1.0)), 3)

    return calibrated


# ── Zone annotation drawing ────────────────────────────────────────────────────

def draw_zone_annotation(
    analysis_img_rgb: np.ndarray,
    concern_type: str,
    severity: str,
    output_size: int = 300,
) -> str:
    if analysis_img_rgb.shape[:2] != (224, 224):
        img = cv2.resize(analysis_img_rgb, (224, 224), interpolation=cv2.INTER_LANCZOS4)
    else:
        img = analysis_img_rgb.copy()

    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    h, w    = 224, 224

    zones_to_draw = CONCERN_ZONES.get(concern_type, [])
    if not zones_to_draw:
        out = cv2.resize(img_bgr, (output_size, output_size), interpolation=cv2.INTER_LANCZOS4)
        _, buf = cv2.imencode('.png', out)
        return base64.b64encode(buf).decode('utf-8')

    color_rgb = SEVERITY_COLORS.get(severity, (234, 179, 8))
    color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])

    overlay = img_bgr.copy()
    for zone_name in zones_to_draw:
        if zone_name not in ZONES:
            continue
        y1f, y2f, x1f, x2f = ZONES[zone_name]
        x1 = max(0, int(w * x1f)); x2 = min(w - 1, int(w * x2f))
        y1 = max(0, int(h * y1f)); y2 = min(h - 1, int(h * y2f))
        if x2 > x1 and y2 > y1:
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color_bgr, -1)
    cv2.addWeighted(overlay, 0.22, img_bgr, 0.78, 0, img_bgr)

    for zone_name in zones_to_draw:
        if zone_name not in ZONES:
            continue
        y1f, y2f, x1f, x2f = ZONES[zone_name]
        x1 = max(0, int(w * x1f)); x2 = min(w - 1, int(w * x2f))
        y1 = max(0, int(h * y1f)); y2 = min(h - 1, int(h * y2f))
        if x2 <= x1 or y2 <= y1:
            continue
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color_bgr, 2)
        hi = img_bgr.copy()
        cv2.rectangle(hi, (x1+1, y1+1), (x2-1, y2-1), (255, 255, 255), 1)
        cv2.addWeighted(hi, 0.25, img_bgr, 0.75, 0, img_bgr)
        label = ZONE_LABELS.get(zone_name, zone_name)
        font  = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.35; thick = 1
        (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
        pad_x, pad_y = 4, 2
        pill_h = th + pad_y * 2
        pill_y1 = y1 - pill_h - 1
        pill_y2 = y1 - 1
        if pill_y1 < 0:
            pill_y1 = y1 + 1; pill_y2 = y1 + pill_h + 1
        pill_x1 = x1; pill_x2 = min(w - 1, x1 + tw + pad_x * 2)
        cv2.rectangle(img_bgr, (pill_x1, pill_y1), (pill_x2, pill_y2), color_bgr, -1)
        cv2.putText(img_bgr, label, (pill_x1 + pad_x, pill_y2 - pad_y),
                    font, scale, (255, 255, 255), thick, cv2.LINE_AA)

    if output_size != 224:
        img_bgr = cv2.resize(img_bgr, (output_size, output_size), interpolation=cv2.INTER_LANCZOS4)
    _, buf = cv2.imencode('.png', img_bgr)
    return base64.b64encode(buf).decode('utf-8')


def generate_all_concern_annotations(
    analysis_img_rgb: np.ndarray,
    concerns: Dict[str, float],
    detector: 'SkinConcernDetector',
    output_size: int = 300,
) -> Dict[str, str]:
    result = {}
    for concern_type, confidence in concerns.items():
        if confidence <= 0.15:
            continue
        severity = detector.classify_severity(concern_type, confidence)
        result[concern_type] = draw_zone_annotation(
            analysis_img_rgb, concern_type, severity, output_size=output_size
        )
    return result


# ── Public API ─────────────────────────────────────────────────────────────────

class SkinConcernDetector:
    """
    Hybrid detector:
      ML model → acne, blackheads, dark_circles, hyperpigmentation, redness, texture
      CV signal → eye_bags, lip_hyperpigmentation
    """

    # Must match concern_class_indices.json exactly (alphabetical from training)
    _MODEL_CLASSES = ['acne', 'blackheads', 'dark_circles', 'dark_spots', 'redness', 'texture']

    _CLASS_MAP = {
        'acne':         'acne',
        'blackheads':   'blackheads',
        'dark_circles': 'dark_circles',
        'dark_spots':   'hyperpigmentation',
        'redness':      'redness',
        'texture':      'texture',
    }

    def __init__(self):
        self._model         = None
        self._model_tried   = False
        self._model_path    = ''
        self._ensemble      = [] 
        self._model_classes = list(self._MODEL_CLASSES)
        self._class_map     = dict(self._CLASS_MAP)

    def _load_model(self):
        if self._model_tried:
            return self._model
        self._model_tried = True
        try:
            import json
            from tensorflow import keras
            base     = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_model')
            v3_model = os.path.join(base, 'concern_model_v3.keras')
            v2_model = os.path.join(base, 'concern_model_v2.keras')
            v1_model = os.path.join(base, 'concern_model.keras')
            v3_idx   = os.path.join(base, 'concern_class_indices_v3.json')
            v2_idx   = os.path.join(base, 'concern_class_indices_v2.json')
            v1_idx   = os.path.join(base, 'concern_class_indices.json')

            if os.path.exists(v3_model):
                model_path, idx_path = v3_model, v3_idx
                print("Concern model v3 found — loading concern_model_v3.keras")
            elif os.path.exists(v2_model):
                model_path, idx_path = v2_model, v2_idx
                print("Loading concern_model_v2.keras")
            elif os.path.exists(v1_model):
                model_path, idx_path = v1_model, v1_idx
                print("Loading original concern_model.keras")

            self._model = keras.models.load_model(model_path, safe_mode=False, compile=False)
            self._model_path = model_path

            if os.path.exists(idx_path):
                with open(idx_path) as f:
                    idx = json.load(f)
                self._model_classes = [k for k, v in sorted(idx.items(), key=lambda x: x[1])]
                self._class_map = {
                    cls: ('hyperpigmentation' if cls == 'dark_spots' else cls)
                    for cls in self._model_classes
                }

            print(f"Concern model loaded ({self._model.output_shape[-1]} classes): {self._model_classes}")
            return self._model
        except Exception as e:
            print(f"Could not load concern model: {e}")
            return None

    # Per-class calibration baselines measured from clean face scores.
    # These are the typical sigmoid outputs on a face with NO concern present.
    # Subtracting these and rescaling gives genuine concern-above-baseline scores.
    # Measured empirically: texture fires ~0.95 on any face, acne ~0.05 etc.
    _CLASS_BASELINES = {
        'acne':             0.05,
        'blackheads':       0.08,
        'dark_circles':     0.10,
        'hyperpigmentation':0.06,
        'redness':          0.04,
        'texture':          0.90,   # model heavily biased toward texture class
    }

    # After subtracting baseline, scale so remaining range maps to 0-1
    _CLASS_SCALE = {
        'acne':             0.95,
        'blackheads':       0.92,
        'dark_circles':     0.90,
        'hyperpigmentation':0.94,
        'redness':          0.96,
        'texture':          0.10,   # only 0-10% range above baseline is meaningful
    }

    def _run_model(self, img_rgb_224: np.ndarray) -> Optional[Dict[str, float]]:
        model = self._load_model()
        if model is None:
            return None
        try:
            arr = img_rgb_224.astype(np.float32) / 255.0
            arr = np.expand_dims(arr, axis=0)

            # Run all available models and average their outputs
            all_probs = []

            # Primary model (whichever loaded — v3, v2, or v1)
            probs = model.predict(arr, verbose=0)[0]
            all_probs.append(('primary', 1.0, probs))

            # Try loading the others if primary isn't already all three
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_model')
            from tensorflow import keras as _keras

            for extra_path, weight in [
                (os.path.join(base, 'concern_model_v2.keras'), 0.8),
                (os.path.join(base, 'concern_model.keras'),    0.5),
            ]:
                if extra_path == self._model_path:
                    continue  # already included as primary
                if os.path.exists(extra_path):
                    try:
                        extra = _keras.models.load_model(extra_path, safe_mode=False, compile=False)
                        extra_probs = extra.predict(arr, verbose=0)[0]
                        all_probs.append((extra_path, weight, extra_probs))
                    except Exception as e:
                        print(f'Ensemble: skipped {os.path.basename(extra_path)}: {e}')

            # Weighted average across all models
            total_weight = sum(w for _, w, _ in all_probs)
            avg_probs = np.zeros(len(probs))
            for _, w, p in all_probs:
                # Pad or trim if models have different output sizes
                n = min(len(p), len(avg_probs))
                avg_probs[:n] += (w / total_weight) * p[:n]

            loaded = [os.path.basename(p) for p, _, _ in all_probs]
            print(f'Ensemble: {len(all_probs)} models — {loaded}')

            scores = {}
            for i, cls in enumerate(self._model_classes):
                if i >= len(avg_probs):
                    break
                concern_key = self._class_map.get(cls, cls)
                raw_prob    = float(avg_probs[i])
                baseline    = self._CLASS_BASELINES.get(concern_key, 0.05)
                scale       = self._CLASS_SCALE.get(concern_key, 0.95)
                calibrated  = max(0.0, (raw_prob - baseline) / max(scale, 0.01))
                scores[concern_key] = round(float(np.clip(calibrated, 0.0, 1.0)), 3)
            return scores

        except Exception as e:
            print(f'Concern model inference failed: {e}')
            return None
        
    def _load_ensemble(self):
        if self._ensemble:
            return self._ensemble
        from tensorflow import keras as _keras
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_model')
        candidates = [
            ('concern_model_v3.keras', 1.0),
            ('concern_model_v2.keras', 0.8),
            ('concern_model.keras',    0.5),
        ]
        for fname, weight in candidates:
            path = os.path.join(base, fname)
            if os.path.exists(path):
                try:
                    m = _keras.models.load_model(path, safe_mode=False, compile=False)
                    self._ensemble.append((m, weight, fname))
                    print(f'Ensemble loaded: {fname} (weight={weight})')
                except Exception as e:
                    print(f'Ensemble: could not load {fname}: {e}')
        return self._ensemble

    def detect_concerns(self, face_rgb_224: np.ndarray) -> Dict[str, float]:
        img = face_rgb_224
        if img.shape[:2] != (224, 224):
            img = cv2.resize(face_rgb_224, (224, 224), interpolation=cv2.INTER_LANCZOS4)

        tone = _skin_tone_factor(img)

        model_scores = self._run_model(img)

        if model_scores is not None:
            raw = dict(model_scores)
        else:
            # CV-only fallback — only used if model fails to load
            raw = {
                'acne':             0.0,
                'redness':          0.0,
                'dark_circles':     0.0,
                'blackheads':       0.0,
                'texture':          0.0,
                'hyperpigmentation':0.0,
            }

        # CV-only concerns always run
        raw['eye_bags']              = _signal_eye_bags(img)
        raw['lip_hyperpigmentation'] = _signal_lip_hyperpigmentation(img, tone)

        return _calibrate(raw, tone)

    def classify_severity(self, concern_type: str, confidence: float) -> str:
        thresholds = {
            'acne':                  (0.25, 0.55),
            'blackheads':            (0.25, 0.55),
            'dark_circles':          (0.25, 0.55),
            'eye_bags':              (0.22, 0.50),
            'redness':               (0.25, 0.55),
            'texture':               (0.30, 0.65),
            'hyperpigmentation':     (0.25, 0.55),
            'lip_hyperpigmentation': (0.20, 0.45),
            'dryness':               (0.25, 0.55),
        }
        mild_t, mod_t = thresholds.get(concern_type, (0.25, 0.55))
        if confidence < mild_t:  return 'mild'
        if confidence < mod_t:   return 'moderate'
        return 'severe'

    def get_recommendation_for_concern(self, concern_type: str, severity: str) -> str:
        tips: Dict[str, Dict[str, str]] = {
            'acne': {
                'mild':     'Use a gentle salicylic acid cleanser 1-2x per week.',
                'moderate': 'Add a benzoyl peroxide spot treatment. Avoid touching your face.',
                'severe':   'Consult a dermatologist. Use non-comedogenic products only.',
            },
            'redness': {
                'mild':     'Use fragrance-free products and avoid hot water.',
                'moderate': 'Look for centella asiatica and niacinamide to calm redness.',
                'severe':   'May indicate rosacea — consult a dermatologist.',
            },
            'dark_circles': {
                'mild':     'Stay hydrated and get 7-8 hours of sleep.',
                'moderate': 'Use an eye cream with caffeine or vitamin K.',
                'severe':   'Try retinol eye creams and vitamin C serum.',
            },
            'eye_bags': {
                'mild':     'Reduce salt intake and sleep with your head elevated.',
                'moderate': 'Use a caffeine eye cream morning and night.',
                'severe':   'Try cold compresses; consider peptide eye creams.',
            },
            'blackheads': {
                'mild':     'Use a BHA (salicylic acid) cleanser 2x per week.',
                'moderate': 'Add a niacinamide serum and a weekly clay mask.',
                'severe':   'Consider a dermatologist-prescribed retinoid.',
            },
            'lip_hyperpigmentation': {
                'mild':     'Use SPF lip balm daily. Avoid lip biting.',
                'moderate': 'Try a vitamin C lip treatment at night.',
                'severe':   'Look for kojic acid or liquorice extract lip products.',
            },
            'texture': {
                'mild':     'Exfoliate gently 1-2x per week with a chemical exfoliant.',
                'moderate': 'Use AHA/BHA with a niacinamide serum.',
                'severe':   'Consistent chemical exfoliation and barrier repair needed.',
            },
            'hyperpigmentation': {
                'mild':     'Use SPF 30+ daily.',
                'moderate': 'Add vitamin C serum in the morning.',
                'severe':   'Niacinamide, vitamin C, and kojic acid in combination.',
            },
            'dryness': {
                'mild':     'Switch to a hydrating cleanser and add hyaluronic acid serum.',
                'moderate': 'Use a rich moisturiser with ceramides twice daily.',
                'severe':   'Barrier repair cream; avoid harsh cleansers entirely.',
            },
        }
        return tips.get(concern_type, {}).get(severity, 'Consult a skincare specialist.')


# ── Groq AI recommendations ────────────────────────────────────────────────────

def get_ai_recommendations(
    skin_type: str,
    concerns: Dict[str, float],
    analyses_history: Optional[list] = None,
) -> Dict[str, str]:
    detector = SkinConcernDetector()
    active   = {k: v for k, v in concerns.items() if v > 0.15}
    if not active:
        return {}
    severities = {k: detector.classify_severity(k, v) for k, v in active.items()}
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get('GROQ_API_KEY', '')
        if not api_key:
            raise ValueError('No GROQ_API_KEY')
        from groq import Groq
        client = Groq(api_key=api_key)
        concern_lines = '\n'.join([
            f"- {k.replace('_', ' ').title()}: {v*100:.0f}% confidence, {severities[k]} severity"
            for k, v in active.items()
        ])
        history_ctx = ''
        if analyses_history:
            history_ctx = f"\nRecent scan history: {', '.join([a.get('skin_type','') for a in analyses_history[:3]])}"
        prompt = f"""You are an expert dermatologist and skincare advisor.

Patient profile:
- Skin type: {skin_type}
- Detected concerns:{history_ctx}
{concern_lines}

For EACH concern listed above, provide ONE specific, actionable recommendation (max 2 sentences).
Focus on ingredients and product types, not brand names unless very well known.
Be direct and practical.

Respond in EXACTLY this format (one line per concern, no extra text):
concern_key: recommendation text

Use these exact keys (lowercase with underscores):
{', '.join(active.keys())}"""
        completion = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.4,
            max_tokens=600,
        )
        text = completion.choices[0].message.content or ''
        recs = {}
        for line in text.strip().splitlines():
            if ':' in line:
                key, _, val = line.strip().partition(':')
                key = key.strip().lower().replace(' ', '_')
                if key in active:
                    recs[key] = val.strip()
        for k, sev in severities.items():
            if k not in recs:
                recs[k] = detector.get_recommendation_for_concern(k, sev)
        return recs
    except Exception:
        return {k: detector.get_recommendation_for_concern(k, severities[k]) for k in active}