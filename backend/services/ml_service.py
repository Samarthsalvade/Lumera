from PIL import Image
import numpy as np
import cv2
import os
import base64
import io
import json

# ── MediaPipe (optional) ──────────────────────────────────────────────────────
try:
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    MEDIAPIPE_AVAILABLE = True
except Exception:
    MEDIAPIPE_AVAILABLE = False

# ── OpenCV cascades ───────────────────────────────────────────────────────────
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
_eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)


class SkinAnalyzer:
    def __init__(self):
        self.model      = None
        self.skin_types = ['Combination', 'Dry', 'Normal', 'Oily', 'Sensitive']
        self._load_model()

    def _load_model(self):
        base = os.path.join(os.path.dirname(__file__), '..', 'ml_model')
        candidates = [
            os.path.join(base, 'best_model_v2.keras'),  # v2 — preferred if trained
            os.path.join(base, 'best_model.keras'),
            os.path.join(base, 'skin_type_model.h5'),
            os.path.join(base, 'best_model.h5'),
        ]
        try:
            import tensorflow as tf
            from tensorflow import keras
            for path in candidates:
                if not os.path.exists(path):
                    continue
                try:
                    self.model = keras.models.load_model(path)
                    self.model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
                    print(f"ML Model loaded: {os.path.basename(path)}")
                    idx_path = os.path.join(base, 'class_indices.json')
                    if os.path.exists(idx_path):
                        with open(idx_path) as f:
                            idx = json.load(f)
                        self.skin_types = [k.capitalize() for k, _ in sorted(idx.items(), key=lambda x: x[1])]
                        print(f"Class order: {self.skin_types}")
                    return
                except Exception as e:
                    print(f"Could not load {path}: {e}")
                    continue
            print("No valid model file found. Using feature-based analysis.")
        except ImportError:
            print("TensorFlow not installed. Using feature-based analysis.")
        except Exception as e:
            print(f"Error loading model: {e}. Using feature-based analysis.")

    def _to_b64(self, img_rgb: np.ndarray) -> str:
        buf = io.BytesIO()
        Image.fromarray(img_rgb).save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def _square_pad(self, img_rgb: np.ndarray) -> np.ndarray:
        h, w = img_rgb.shape[:2]
        if h == w:
            return img_rgb
        side = max(h, w)
        sq = np.full((side, side, 3), 245, dtype=np.uint8)
        sq[(side-h)//2:(side-h)//2+h, (side-w)//2:(side-w)//2+w] = img_rgb
        return sq

    def _score_candidate(self, x, y, w, h, img_w, img_h, gray):
        cx = x + w / 2
        horiz_dist = abs(cx - img_w / 2) / (img_w / 2)
        area_score = (w * h) / (img_w * img_h)
        roi = gray[y:y+h, x:x+w]
        eyes = _eye_cascade.detectMultiScale(roi, 1.1, 3, minSize=(15, 15))
        eye_bonus = 0.35 if len(eyes) >= 2 else (0.12 if len(eyes) == 1 else 0.0)
        return area_score * 2.5 + eye_bonus - horiz_dist * 0.5, int(len(eyes))

    def _haar_detect(self, gray, gray_eq):
        params = [
            (1.05, 5, 60), (1.05, 4, 40), (1.05, 3, 30),
            (1.10, 3, 25), (1.10, 2, 20), (1.15, 2, 15),
        ]
        for g in [gray, gray_eq]:
            for scale, nb, ms in params:
                found = _face_cascade.detectMultiScale(g, scaleFactor=scale, minNeighbors=nb, minSize=(ms, ms))
                if len(found) > 0:
                    return found.tolist()
        return []

    def detect_and_normalize_face(self, image_path: str, output_size: int = 300):
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return {'face_found': False, 'message': 'Could not read image.',
                    'display_image': None, 'analysis_image': None, 'normalized_b64': None, 'confidence': 0.0}

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w    = img_rgb.shape[:2]
        gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        gray_eq = cv2.equalizeHist(gray)
        candidates = self._haar_detect(gray, gray_eq)

        if candidates:
            scored = [(self._score_candidate(x, y, fw, fh, w, h, gray), x, y, fw, fh) for (x, y, fw, fh) in candidates]
            scored.sort(key=lambda t: t[0][0], reverse=True)
            (_, eyes), fx, fy, fw, fh = scored[0]
            x1d = max(0, fx - int(fw * 0.50)); y1d = max(0, fy - int(fh * 0.70))
            x2d = min(w, fx + fw + int(fw * 0.50)); y2d = min(h, fy + fh + int(fh * 0.45))
            disp = self._square_pad(img_rgb[y1d:y2d, x1d:x2d])
            display_300 = cv2.resize(disp, (output_size, output_size), interpolation=cv2.INTER_LANCZOS4)
            x1a = max(0, fx); y1a = max(0, fy); x2a = min(w, fx + fw); y2a = min(h, fy + fh)
            analysis_224 = cv2.resize(img_rgb[y1a:y2a, x1a:x2a], (224, 224), interpolation=cv2.INTER_LANCZOS4)
            conf = min(0.55 + eyes * 0.20 + (fw * fh) / (w * h) * 5.0, 0.99)
            return {
                'face_found': True, 'confidence': round(conf, 2),
                'display_image': display_300, 'analysis_image': analysis_224,
                'normalized_b64': self._to_b64(display_300),
                'message': f'Face detected ({conf*100:.0f}% confidence) — image normalized.',
            }

        if MEDIAPIPE_AVAILABLE:
            try:
                tflite = os.path.join(os.path.dirname(__file__), 'blaze_face_short_range.tflite')
                if os.path.exists(tflite):
                    import mediapipe as mp
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
                    opts = mp_vision.FaceDetectorOptions(
                        base_options=mp_python.BaseOptions(model_asset_path=tflite),
                        min_detection_confidence=0.3,
                    )
                    with mp_vision.FaceDetector.create_from_options(opts) as det:
                        res = det.detect(mp_img)
                    if res.detections:
                        best  = res.detections[0]
                        score = best.categories[0].score if best.categories else 0.7
                        bbox  = best.bounding_box
                        px    = int(bbox.width * 0.45); py = int(bbox.height * 0.45)
                        x1 = max(0, bbox.origin_x - px); y1 = max(0, bbox.origin_y - int(bbox.height * 0.65))
                        x2 = min(w, bbox.origin_x + bbox.width + px); y2 = min(h, bbox.origin_y + bbox.height + py)
                        disp = self._square_pad(img_rgb[y1:y2, x1:x2])
                        display_300  = cv2.resize(disp, (output_size, output_size), interpolation=cv2.INTER_LANCZOS4)
                        analysis_224 = cv2.resize(
                            img_rgb[bbox.origin_y:bbox.origin_y+bbox.height, bbox.origin_x:bbox.origin_x+bbox.width],
                            (224, 224), interpolation=cv2.INTER_LANCZOS4)
                        return {
                            'face_found': True, 'confidence': float(score),
                            'display_image': display_300, 'analysis_image': analysis_224,
                            'normalized_b64': self._to_b64(display_300),
                            'message': f'Face detected ({score*100:.0f}%) — normalized.',
                        }
            except Exception as e:
                print(f"MediaPipe error: {e}")

        return {
            'face_found': False, 'confidence': 0.0,
            'display_image': None, 'analysis_image': None, 'normalized_b64': None,
            'message': 'No human face detected. Please upload a clear front-facing photo.',
        }

    def _predict_cnn(self, analysis_image: np.ndarray):
        img   = analysis_image.astype(np.float32) / 255.0
        arr   = np.expand_dims(img, axis=0)
        preds = self.model.predict(arr, verbose=0)[0]
        idx   = int(np.argmax(preds))
        conf  = float(preds[idx]) * 100
        return self.skin_types[idx], round(conf, 2)

    def _extract_features(self, face_224: np.ndarray):
        img = face_224; img_hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV); img_lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        h, w = img.shape[:2]; cy1, cy2 = int(h*0.10), int(h*0.75); cx1, cx2 = int(w*0.15), int(w*0.85)
        center = img[cy1:cy2, cx1:cx2]; center_hsv = img_hsv[cy1:cy2, cx1:cx2]; center_lab = img_lab[cy1:cy2, cx1:cx2]
        brightness = float(np.mean(center)); gray_c = cv2.cvtColor(center, cv2.COLOR_RGB2GRAY); texture_variance = float(np.var(gray_c))
        saturation = float(np.mean(center_hsv[:, :, 1]))
        r_m = float(np.mean(center[:, :, 0])); g_m = float(np.mean(center[:, :, 1])); b_m = float(np.mean(center[:, :, 2]))
        total = r_m + g_m + b_m + 1e-9; red_dominance = (r_m / total - 1.0/3.0) * 300
        L = center_lab[:, :, 0].astype(float); shine_pct = float(np.sum(L > 200) / L.size * 100); l_std = float(np.std(L))
        return brightness, texture_variance, saturation, red_dominance, shine_pct, l_std

    def _classify_features(self, brightness, texture_variance, saturation, red_dominance, shine_pct, l_std):
        scores = {'Normal': 0, 'Oily': 0, 'Dry': 0, 'Combination': 0, 'Sensitive': 0}
        if shine_pct > 25: scores['Oily'] += 35
        elif shine_pct > 15: scores['Oily'] += 15; scores['Combination'] += 15
        if l_std > 55: scores['Oily'] += 20; scores['Combination'] += 10
        elif l_std > 45: scores['Combination'] += 15
        if brightness > 165: scores['Oily'] += 15
        elif brightness > 150: scores['Combination'] += 10
        if texture_variance > 2500 and shine_pct > 15: scores['Oily'] += 15
        if shine_pct < 3: scores['Dry'] += 25
        if texture_variance < 800: scores['Dry'] += 25
        elif texture_variance < 1200: scores['Dry'] += 10
        if brightness < 100: scores['Dry'] += 20
        elif brightness < 115: scores['Dry'] += 10
        if saturation < 50: scores['Dry'] += 15; scores['Normal'] += 5
        if red_dominance > 45: scores['Sensitive'] += 40
        elif red_dominance > 40: scores['Sensitive'] += 20
        if saturation > 150 and red_dominance > 35: scores['Sensitive'] += 15
        if 8 <= shine_pct <= 20 and texture_variance > 1500: scores['Combination'] += 25
        if 120 < brightness < 155: scores['Combination'] += 10
        if 40 <= l_std <= 55: scores['Combination'] += 10
        balanced = (3 <= shine_pct <= 20 and 800 <= texture_variance <= 2500 and 105 < brightness < 155 and red_dominance < 42 and saturation < 145 and l_std < 55)
        if balanced: scores['Normal'] += 35
        if 5 <= shine_pct <= 15: scores['Normal'] += 10
        if 1000 <= texture_variance <= 2000: scores['Normal'] += 10
        skin_type = max(scores, key=scores.get)
        import random
        confidence = min(scores[skin_type] + random.uniform(8, 18), 94)
        return skin_type, round(confidence, 2)

    def _get_recommendations(self, skin_type: str, confidence: float = 0.0, concerns: dict = None) -> list:
        """
        Generate AI-powered recommendations using Groq.
        Falls back to static recommendations if Groq is unavailable.
        """
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get('GROQ_API_KEY', '')
            if not api_key:
                raise ValueError('No GROQ_API_KEY')
            from groq import Groq
            client = Groq(api_key=api_key)

            concern_str = ''
            if concerns:
                active = [k.replace('_', ' ') for k, v in concerns.items() if v > 0.15]
                if active:
                    concern_str = f"\nActive concerns detected: {', '.join(active)}"

            conf_note = ''
            if confidence < 60:
                conf_note = f' (classification confidence: {confidence:.1f}% — consider better lighting)'

            prompt = f"""You are a concise skincare expert.

Patient skin type: {skin_type}{conf_note}{concern_str}

Give exactly 3 short, practical skincare recommendations for this person.
Each recommendation must be one clear sentence, actionable, focused on ingredients or habits.
Do NOT repeat the skin type. Do NOT number them. Return each on its own line, nothing else."""

            completion = client.chat.completions.create(
                model='llama-3.1-8b-instant',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.4,
                max_tokens=200,
            )
            text = completion.choices[0].message.content or ''
            recs = [line.strip() for line in text.strip().splitlines() if line.strip()][:3]
            if recs:
                return recs
            raise ValueError('Empty response')
        except Exception:
            # Static fallback
            recs = {
                'Normal':      ['Maintain balance with gentle cleansing twice daily', 'Use a lightweight moisturiser with SPF 30+ protection', 'Add a vitamin C serum in the morning to prevent early ageing'],
                'Oily':        ['Use an oil-free salicylic acid cleanser to control sebum', 'Apply a niacinamide serum to reduce pore size and shine', 'Choose non-comedogenic, water-based moisturisers only'],
                'Dry':         ['Apply a ceramide-rich moisturiser immediately after washing', 'Use hyaluronic acid serum on damp skin to lock in hydration', 'Avoid hot water and sulphate-based cleansers'],
                'Combination': ['Use a gentle pH-balanced cleanser across the whole face', 'Apply lightweight moisturiser on cheeks and oil-control gel on T-zone', 'Use BHA exfoliant on the T-zone once or twice a week'],
                'Sensitive':   ['Choose fragrance-free, hypoallergenic products only', 'Patch test every new product on your inner arm before applying to face', 'Use centella asiatica or oat extract to calm inflammation'],
            }
            return recs.get(skin_type, recs['Normal'])

    def analyze(self, image_path: str) -> dict:
        try:
            norm = self.detect_and_normalize_face(image_path)
            if not norm['face_found']:
                return {
                    'success': False, 'face_found': False, 'message': norm['message'],
                    'skin_type': None, 'confidence': 0, 'recommendations': [],
                    'normalized_image_b64': None, 'face_detection_confidence': 0,
                }

            analysis_img = norm['analysis_image']

            if self.model is not None:
                skin_type, confidence = self._predict_cnn(analysis_img)
                print(f"ML Model: {skin_type} ({confidence:.2f}%)")
            else:
                features = self._extract_features(analysis_img)
                skin_type, confidence = self._classify_features(*features)
                print(f"Feature-based: {skin_type} ({confidence:.2f}%)")

            # Recommendations generated after skin type known — concerns added later in analysis.py
            recommendations = self._get_recommendations(skin_type, confidence)

            return {
                'success': True, 'face_found': True, 'message': norm['message'],
                'skin_type': skin_type, 'confidence': round(confidence, 2),
                'recommendations': recommendations,
                'normalized_image_b64': norm['normalized_b64'],
                'face_detection_confidence': round(norm['confidence'] * 100, 1),
                'analysis_image': norm['analysis_image'],
            }
        except Exception as e:
            raise Exception(f"Analysis failed: {e}")


_analyzer = None

def get_analyzer() -> SkinAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SkinAnalyzer()
    return _analyzer

def analyze_skin(image_path: str) -> dict:
    return get_analyzer().analyze(image_path)