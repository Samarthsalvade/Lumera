# Luméra — AI Skincare Analysis Platform

A full-stack web application that analyses your skin from a photo. It classifies your skin type (combination, dry, normal, oily, sensitive), detects up to 8 skin concerns (acne, blackheads, dark circles, eye bags, hyperpigmentation, lip hyperpigmentation, redness, texture), recommends personalised skincare products, generates morning and night routines, tracks your progress over time with an interactive calendar, and lets you chat with an AI skincare consultant. Built as a personal project from scratch.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Quick Start](#quick-start)
4. [Environment Variables](#environment-variables)
5. [Database Setup & Migrations](#database-setup--migrations)
6. [ML Models](#ml-models)
7. [Face Detection Pipeline](#face-detection-pipeline)
8. [Concern Detection Architecture](#concern-detection-architecture)
9. [API Reference](#api-reference)
10. [Database Schema](#database-schema)
11. [Frontend Pages](#frontend-pages)
12. [Features Deep Dive](#features-deep-dive)
13. [Training the Models](#training-the-models)
14. [Complete Bug Fix History](#complete-bug-fix-history)
15. [Known Limitations](#known-limitations)
16. [Roadmap](#roadmap)

---

## Tech Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 18 | UI framework |
| TypeScript | 5.x | Type safety across all components |
| Tailwind CSS | 3.x | Utility-first styling |
| React Router | v6 | Client-side routing with protected routes |
| Axios | latest | HTTP client — attaches JWT Bearer token to every request automatically |
| Vite | latest | Dev server and production bundler |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.13 | Runtime |
| Flask | 3.0 | Web framework |
| Flask-JWT-Extended | 4.x | JWT authentication — tokens issued as strings, 7-day expiry |
| SQLAlchemy | latest | ORM — models defined in `models.py`, SQLite as database |
| SQLite | built-in | Database stored at `backend/instance/lumera.db` |
| OpenCV (headless) | latest | Haar cascade face detection + all CV-based concern signals |
| MediaPipe Tasks | latest | Fallback face detector using BlazeFace model |
| Pillow | latest | Image I/O, base64 encoding for storing images in the database |
| TensorFlow | 2.21 | CNN model runtime for both skin type and concern classification |
| Keras | 3.x | High-level model loading and inference API |
| Groq SDK | latest | LLM API — llama-3.1-8b-instant for recommendations, routines, chatbot |
| reportlab | 4.x | PDF report generation using Platypus high-level API |
| requests | latest | HTTP client for Open Beauty Facts API (product image lookup) |
| python-dotenv | latest | Loads `.env` file into `os.environ` at startup |
| numpy | latest | Array operations for image processing and model inference |

---

## Project Structure

```
lumera/
├── backend/
│   ├── instance/
│   │   └── lumera.db                      # SQLite database — auto-created on first run
│   │
│   ├── ml_model/
│   │   ├── best_model.keras               # Skin type CNN v1 — 85.09% val accuracy
│   │   ├── best_model_v2.keras            # Skin type CNN v2 — multi-scale + label smoothing
│   │   ├── concern_model.keras            # Concern CNN v1 — 95.69% val accuracy
│   │   ├── concern_model_v2.keras         # Concern CNN v2 — per-concern branches
│   │   ├── concern_model_v3.keras         # Concern CNN v3 — full-face bbox-aware training
│   │   ├── class_indices.json             # Skin type class order: combination(0) dry(1) normal(2) oily(3) sensitive(4)
│   │   ├── concern_class_indices.json     # Concern class order v1
│   │   ├── concern_class_indices_v2.json  # Concern class order v2
│   │   ├── concern_class_indices_v3.json  # Concern class order v3
│   │   ├── train_model.py                 # Trains best_model_v2.keras — run from backend/
│   │   ├── train_concern_model_v2.py      # Trains concern_model_v2.keras
│   │   └── train_concern_model_v3.py      # Trains concern_model_v3.keras with bbox soft labels
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                        # POST /api/auth/register, /login · GET /api/auth/me
│   │   ├── analysis.py                    # POST /api/analysis/upload · GET history, result, image
│   │   ├── chatbot.py                     # POST /api/chatbot/chat — Groq with last 5 scan context
│   │   ├── routines.py                    # CRUD + activate for morning/night routines
│   │   ├── products.py                    # POST /api/products/recommend — Groq + OBF images
│   │   └── report.py                      # GET /api/report/summary (JSON) + /weekly (PDF)
│   │
│   ├── services/
│   │   └── ml_service.py                  # SkinAnalyzer class:
│   │                                      #   - face detection (Haar + MediaPipe fallback)
│   │                                      #   - two-crop strategy (display vs analysis)
│   │                                      #   - CNN skin type prediction
│   │                                      #   - Groq recommendation generation
│   │                                      #   Loads best_model_v2.keras first, falls back to v1
│   │
│   ├── dataset_downloads/                 # Raw training data — gitignored, download separately
│   │   ├── ds4/Skin_Conditions/           # Kaggle: Acne, Rosacea images (folder-named)
│   │   ├── ds5/Skin v2/                   # Kaggle: acne, blackheads, dark_spots, pores, wrinkles
│   │   ├── ds7/                           # Kaggle: dark_circles (train/valid/test splits)
│   │   ├── ds_rf1/_raw/                   # Roboflow: acne + dark_circles + wrinkles, 3,607 images
│   │   │                                  # ⚠ Polygon segmentation format (not standard yolov8)
│   │   ├── ds_rf2/_raw/                   # Roboflow: dark_circles dedicated, 1,114 images
│   │   └── ds_rf3/_raw/                   # Roboflow: facial health suite (optional, large)
│   │
│   ├── training_data/                     # Skin type training images — gitignored
│   │   ├── combination/  dry/  normal/  oily/  sensitive/
│   │
│   ├── concern_training_data/             # v1/v2 staged images — auto-generated by train scripts
│   │   ├── acne/  blackheads/  dark_circles/  dark_spots/  redness/  texture/
│   │
│   ├── concern_training_data_v3/          # v3 staged images — full-face with soft label map
│   │   ├── acne/  blackheads/  dark_circles/  dark_spots/  redness/  texture/
│   │   └── _label_map.json                # Maps every staged image path → soft label (0.40–0.95)
│   │
│   ├── uploads/                           # User-uploaded images — JWT-protected serving
│   ├── utils/
│   │   └── helpers.py                     # allowed_file() — validates PNG/JPG/JPEG/WEBP extensions
│   ├── app.py                             # Flask factory: CORS, blueprint registration, health check
│   ├── config.py                          # JWT settings, upload folder path, dotenv loading
│   ├── models.py                          # SQLAlchemy ORM models for all database tables
│   ├── skin_concern_detector.py           # SkinConcernDetector — hybrid ML ensemble + CV signals
│   │                                      # Loads and caches all available concern model versions
│   │                                      # Runs weighted ensemble + CV signals on every analysis
│   ├── download_concern_datasets.py       # Downloads Roboflow datasets in yolov8 format
│   │                                      # Parses label files to extract images by concern class
│   ├── migrate_db.py                      # v1→v2: adds normalized_image_b64, face_detection_confidence
│   ├── migrate_db_v3.py                   # v2→v3: creates skin_concerns, routines, routine_steps
│   ├── migrate_db_v4.py                   # v3→v4: adds annotated_image_b64 to skin_concerns
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── axios.ts                   # Axios instance — reads token from localStorage,
    │   │                                  # attaches 'Authorization: Bearer <token>' to every request
    │   ├── components/
    │   │   ├── PageShell.tsx              # Shared background wrapper used by all pages:
    │   │   │                              # #f5f3ff base colour, subtle dot-grid SVG pattern,
    │   │   │                              # two blurred purple accent circles in corners
    │   │   ├── Navbar.tsx                 # Responsive navbar — shows different links when logged in
    │   │   │                              # Logo links to /dashboard (logged in) or / (logged out)
    │   │   └── ProtectedRoute.tsx         # Synchronous JWT guard — checks localStorage directly on
    │   │                                  # render, no async delay, eliminates login-page flash
    │   ├── pages/
    │   │   ├── Home.tsx                   # Landing page with feature cards and stats strip
    │   │   ├── Login.tsx                  # Email + password login form
    │   │   ├── Signup.tsx                 # Username + email + password registration
    │   │   ├── Dashboard.tsx              # Scan history grid, quick action cards, tips section
    │   │   ├── Upload.tsx                 # Two-column layout: upload/camera form + photo guide
    │   │   │                              # SVG illustration showing good vs bad framing
    │   │   │                              # Full-face guidance enforced with amber warning banner
    │   │   ├── Results.tsx                # Three-tab layout: Concerns · Products · Routine
    │   │   │                              # Products: horizontal sliding cards with OBF real images
    │   │   ├── Progress.tsx               # Calendar + fixed-height day panel with internal scroll
    │   │   ├── Chatbot.tsx                # AI skincare consultant — full conversation history
    │   │   ├── Routines.tsx               # Morning/night routine manager with accordion expand
    │   │   └── WeeklyReport.tsx           # Interactive bar chart + scan log + PDF download
    │   ├── types/
    │   │   └── index.ts                   # TypeScript interfaces: Analysis, AnalysisResponse, etc.
    │   └── App.tsx                        # React Router setup, ProtectedRoute wrapping
    └── package.json
```

---

## Quick Start

### Prerequisites
- **Python 3.13+** — the backend uses match statements and other 3.10+ features
- **Node.js 18+** — the frontend uses Vite which requires Node 18
- **A free Groq API key** — https://console.groq.com — used for recommendations, routines, chatbot
- **A free Roboflow API key** — https://app.roboflow.com — only needed if you want to retrain the concern model from scratch

### Backend Setup

```bash
cd lumera/backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

# Install all Python dependencies
pip install -r requirements.txt

# reportlab is not in requirements.txt on some setups — install separately
pip install reportlab --break-system-packages

# Create your .env file (see Environment Variables section for exact format)
cp .env.example .env    # or create it manually

# Run database migrations in order — only needed once on a fresh setup
# Each script is idempotent (safe to run multiple times)
python migrate_db.py          # adds face detection columns
python migrate_db_v3.py       # creates concerns, routines tables
python migrate_db_v4.py       # adds annotated zone images

# Start the development server
python app.py
```

The backend runs on **http://localhost:3001**. You should see:
```
ML Model loaded: best_model_v2.keras
Class order: ['Combination', 'Dry', 'Normal', 'Oily', 'Sensitive']
Ensemble loaded: concern_model_v3.keras (weight=1.0)
Ensemble loaded: concern_model_v2.keras (weight=0.8)
Ensemble loaded: concern_model.keras (weight=0.5)
 * Running on http://127.0.0.1:3001
```

### Frontend Setup

```bash
cd lumera/frontend
npm install
npm run dev
```

The frontend runs on **http://localhost:5173**.

### Verify Everything Is Working

```bash
# 1. Check the backend is responding
curl http://localhost:3001/api/health
# Expected: {"status": "ok", "message": "Backend is running"}

# 2. Confirm the skin type model loaded correctly
python3 -c "
from services.ml_service import get_analyzer
a = get_analyzer()
print('Skin model loaded:', a.model is not None)
print('Classes:', a.skin_types)
"
# Expected: Skin model loaded: True
# Classes: ['Combination', 'Dry', 'Normal', 'Oily', 'Sensitive']

# 3. Confirm the concern ensemble loaded correctly
python3 -c "
from skin_concern_detector import SkinConcernDetector
d = SkinConcernDetector()
ensemble = d._load_ensemble()
print(f'{len(ensemble)} concern model(s) loaded:')
for model, weight, name in ensemble:
    print(f'  {name}  weight={weight}')
"
# Expected: 3 concern model(s) loaded:
#   concern_model_v3.keras  weight=1.0
#   concern_model_v2.keras  weight=0.8
#   concern_model.keras     weight=0.5
```

---

## Environment Variables

Create a file called `.env` inside the `backend/` directory with the following contents:

```env
# Flask secret key — used to sign session cookies
# Change this to a long random string in production
SECRET_KEY=lumera-super-secret-key-min-32-chars-long-12345

# JWT secret key — used to sign authentication tokens
# Should be different from SECRET_KEY in production
JWT_SECRET_KEY=lumera-super-secret-key-min-32-chars-long-12345

# Groq API key — used for AI recommendations, routine generation, chatbot
# Get a free key at https://console.groq.com
# Free tier: 14,400 requests/day, 6,000 tokens/min, no credit card required
GROQ_API_KEY=gsk_your_actual_key_here

# Roboflow API key — only needed if retraining the concern model from scratch
# Get a free key at https://app.roboflow.com → avatar → Roboflow API
ROBOFLOW_API_KEY=your_roboflow_key_here
```

**Important notes:**
- Keys must be the **literal values** in the `.env` file — not shell environment variables
- The Groq and Roboflow clients are initialised lazily: `load_dotenv()` is called inside `_get_groq()` at first request, not at import time. This is intentional — importing the module before dotenv loads would fail to find the key.
- Never commit the real `.env` file to git — add it to `.gitignore`
- If Groq is unavailable (rate limited, account issue), the system falls back to static recommendation strings per skin type

---

## Database Setup & Migrations

The database is SQLite, stored at `backend/instance/lumera.db`. It is **auto-created** on first run — you do not need to create it manually.

The schema has evolved across four versions. If you are starting fresh, run all three migration scripts in order:

```bash
# Adds normalized_image_b64 (the padded display crop) and
# face_detection_confidence to the analyses table
python migrate_db.py

# Creates the skin_concerns table (stores per-concern detection results),
# routines table, routine_steps table, and product_recommendations table.
# Also adds a skin_concerns JSON column to analyses for quick lookup.
python migrate_db_v3.py

# Adds annotated_image_b64 to skin_concerns — stores the zone annotation
# image (the face with coloured boxes showing where the concern was detected)
python migrate_db_v4.py
```

Each migration script checks whether the column or table already exists before trying to add it, so they are safe to run multiple times.

---

## ML Models

Luméra uses two independent CNN pipelines: one for skin type classification and one for concern detection. Understanding how they work is important for understanding the system's accuracy and limitations.

---

### Skin Type Classifier

The skin type classifier takes a 224×224 pixel crop of the detected face and outputs one of five classes: Combination, Dry, Normal, Oily, Sensitive.

The application automatically tries to load `best_model_v2.keras` first. If it does not exist (e.g. you have not retrained yet), it falls back to `best_model.keras`. The inference code is identical for both — feed a `[0,1]` normalised float32 array, get a 5-class softmax probability vector back.

#### v1 — `ml_model/best_model.keras`

The original model. Straightforward MobileNetV2 backbone with a simple classification head.

**Architecture:** MobileNetV2 (pretrained on ImageNet, `include_top=False`) → Global Average Pooling → BatchNorm → Dense(256, ReLU) → Dropout(0.4) → Dense(128, ReLU) → Dropout(0.3) → Dense(5, softmax)

**Preprocessing note:** MobileNetV2 expects pixel values in the range `[-1, +1]`, not `[0, 1]`. The v1 model has the `preprocess_input` rescaling baked directly into the model as `Multiply`, `TrueDivide`, and `Subtract` layers. This means you should feed raw `[0, 1]` normalised floats and let the model apply its own rescaling internally. Do NOT call `tf.keras.applications.mobilenet_v2.preprocess_input()` yourself — this would apply the scaling a second time and produce garbage predictions.

| Property | Value |
|---|---|
| Base model | MobileNetV2 (ImageNet weights, include_top=False) |
| Input shape | 224 × 224 × 3 |
| Output | 5-class softmax |
| Validation accuracy | **85.09%** |
| Validation loss | 0.5488 |
| Training phases | Phase 1: 15 epochs frozen base (LR=1e-3) · Phase 2: 10 epochs fine-tune top 30 layers (LR=1e-4) |
| Class weights | Inverse-frequency, capped at 10× — compensates for only 80 sensitive images |

---

#### v2 — `ml_model/best_model_v2.keras`

A significantly improved architecture that addresses two problems with v1: overconfident predictions and poor separation of visually similar skin types (combination vs normal vs oily).

**Problem 1 — Overconfident predictions.** v1 regularly predicted "Normal: 97%" for genuinely ambiguous faces. The root cause is that categorical cross-entropy loss with hard one-hot targets `[0,0,1,0,0]` allows the model to reduce loss without bound by pushing the correct logit toward infinity. The model has no incentive to be uncertain even when the input is ambiguous.

**Solution — Label smoothing (ε=0.10).** Instead of training on hard targets `[0,0,1,0,0]`, we train on soft targets `[0.02, 0.02, 0.92, 0.02, 0.02]`. The model can never achieve zero loss — it is always penalised for being too certain. This is applied **only to training labels**. Validation labels remain hard one-hot so that val_accuracy is an honest metric (not measuring closeness to soft targets).

**Problem 2 — Missing fine-grained texture information.** MobileNetV2's final feature map is 7×7 pixels — each pixel covers a 32×32 region of the original 224×224 image. This is excellent for capturing overall skin tone and distribution, but too coarse to capture pore texture or subtle shine patterns that distinguish oily from normal skin.

**Solution — Multi-scale feature fusion.** The model now extracts features at two spatial resolutions simultaneously:
- **Fine features** from `block_6_expand_relu` — 28×28×192 spatial map. At this scale each pixel covers an 8×8 region, capturing fine pore and texture detail.
- **Coarse features** from the final block — 7×7×1280. Captures overall skin tone and distribution.

Both are pooled and concatenated into a single feature vector before the classification head. This gives the model both local detail and global context at the same time.

**Squeeze-and-Excitation (SE) on coarse features.** Not all 1280 channels in the coarse feature map are equally informative for skin type classification — many are illumination-detector channels that fire on bright pixels regardless of skin type. The SE block learns a per-channel importance weight:

1. Global average pool the 7×7×1280 map to a 1280-d vector (the "squeeze")
2. Pass through Dense(64, ReLU) → Dense(1280, sigmoid) — a bottleneck MLP (the "excitation")
3. Element-wise multiply the original pooled vector by the learned weights (the "scale")

This suppresses unhelpful channels before the feature reaches the classification head.

**Three training phases with cosine LR decay.** v1 used only two phases. v3 adds a third phase that unlocks 60 layers (vs 30 in Phase 2) and uses a cosine learning rate schedule that smoothly decays from 5e-5 to 1e-6. This avoids the abrupt LR drops from `ReduceLROnPlateau` that caused oscillation on the small sensitive class (only 80 images).

| Property | Value |
|---|---|
| Fine branch | `block_6_expand_relu` → GAP → BatchNorm → Dense(128, ReLU) → Dropout(0.25) |
| Coarse branch | Final MobileNetV2 block → GAP → SE bottleneck(64) → BatchNorm → Dense(256, ReLU) → Dropout(0.30) |
| Fusion | Concatenate(fine, coarse) → Dense(512, ReLU, L2) → BN → Drop(0.40) → Dense(256, ReLU, L2) → BN → Drop(0.35) → Dense(128, ReLU) → BN → Drop(0.25) |
| Output | Dense(5, softmax) |
| Label smoothing | ε = 0.10 (training labels only) |
| Phase 1 | 15 epochs, frozen base, LR=1e-3 |
| Phase 2 | 10 epochs, fine-tune top 30 layers, LR=1e-4 |
| Phase 3 | 8 epochs, fine-tune top 60 layers, cosine LR 5e-5→1e-6 |
| Class weights | Inverse-frequency, capped at 10× |
| Saves to | `best_model_v2.keras` — original `best_model.keras` is never overwritten |

**Training datasets for skin type (used by both v1 and v2):**

| Dataset | Source | Classes | Approx images |
|---|---|---|---|
| Oily/Dry/Normal skin types | Kaggle: shakyadissanayake | normal, oily, dry | ~3,000 |
| Normal/Dry/Oily skin type | Kaggle: ritikasinghkatoch | normal, oily, dry (includes Indonesian labels) | ~400 |
| Facial Skin Analysis | Kaggle: killa92 | combination, dry, normal, oily | ~2,000 |
| Original project data | Manually collected | All 5 types | ~3,312 |
| **Total** | | | **~8,588** |

---

### Concern Detection Model — Three Versions, One Ensemble

The concern detector is significantly more complex than the skin type classifier because it must handle multiple concurrent concerns (a face can have acne AND dark circles simultaneously), concerns of varying severity, and concerns that are spatially localised to specific face regions.

Three model versions exist. All available versions are loaded at startup and run together as a **weighted ensemble** on every inference. Their outputs are averaged before calibration, which suppresses individual model errors and reinforces concerns that multiple models agree on.

```
concern_model_v3.keras  →  weight 1.0  (highest — best spatial awareness)
concern_model_v2.keras  →  weight 0.8  (good concern separation)
concern_model.keras     →  weight 0.5  (legacy — lower weight due to training mismatch)

Weighted average → calibration → final concern scores
```

#### v1 — `ml_model/concern_model.keras`

The original concern model. Uses sigmoid activation (not softmax) because a face can have multiple concerns simultaneously — softmax forces all probabilities to sum to 1.0 which would prevent detecting more than one concern at a time.

**Architecture:** MobileNetV2 → GlobalAveragePooling2D → BatchNorm → Dense(256, ReLU) → Dropout(0.4) → Dense(128, ReLU) → Dropout(0.3) → Dense(6, sigmoid)

**Key limitation — training/inference mismatch.** This model was trained on close-up zone crops: a dark circles sample was just the under-eye area filling the entire 224×224 frame. At inference time, the model receives a full face. The model learned "dark circles look like this [under-eye region fills frame]" but at test time it sees "dark circles are a small region in the lower-middle portion of a full face." This mismatch causes misclassification — the model confuses texture or skin tone for specific concerns.

**Overconfidence — texture class.** The texture class had ~3,614 training images vs only ~399 for redness. Even with sigmoid, the raw output for texture on a clean face is ~0.90. A hard-coded per-class baseline subtraction is applied: `calibrated = (raw - baseline) / scale`. For texture: baseline=0.90, scale=0.10 — meaning only the 0–10% range above 0.90 is treated as meaningful.

| Property | Value |
|---|---|
| Output | 6-class sigmoid |
| Val accuracy | **95.69%** |
| Classes | acne, blackheads, dark_circles, dark_spots, redness, texture |
| Loss | binary_crossentropy with one-hot labels |
| Preprocessing | `Rescaling(scale=2.0, offset=-1.0)` baked in — feed raw [0,1] float |
| Calibration | Per-class baseline subtraction in `_run_model()` |
| Ensemble weight | **0.5** |

---

#### v2 — `ml_model/concern_model_v2.keras`

Addresses the overconfidence and concern-suppression problems of v1 through architectural changes.

**Per-concern prediction branches.** In v1, all 6 concerns share a single `Dense(6, sigmoid)` weight matrix. This means the weights for acne and texture are entangled — improving texture detection risks hurting acne detection. v2 gives each concern its own small neural network:

```
Shared features → shared Dense head (512→256→128) →
  ┌→ Dense(32) → Drop(0.15) → Dense(1, sigmoid)   [acne]
  ├→ Dense(32) → Drop(0.15) → Dense(1, sigmoid)   [blackheads]
  ├→ Dense(32) → Drop(0.15) → Dense(1, sigmoid)   [dark_circles]
  ├→ Dense(32) → Drop(0.15) → Dense(1, sigmoid)   [dark_spots]
  ├→ Dense(32) → Drop(0.15) → Dense(1, sigmoid)   [redness]
  └→ Dense(32) → Drop(0.15) → Dense(1, sigmoid)   [texture]
```

Each concern's branch learns its own decision boundary from the shared feature vector without competing with other concerns for weight capacity.

**Multi-scale feature fusion + SE (same as skin type v2).** Fine features (28×28) from `block_6_expand_relu` for detail-level signals (blackhead pores, fine texture). Coarse features (7×7) with SE recalibration for global signals (overall redness, dark circles relative to skin tone).

**Honest F1 monitoring.** v1 trained on `val_accuracy`. On an imbalanced multi-label problem, a model that predicts all-zeros for every sample achieves ~85% accuracy (since most pixels belong to the negative class for any given concern). F1 score requires actually detecting the positive class to score well. v2 uses macro-averaged binary F1 as the monitored metric for both `EarlyStopping` and `ModelCheckpoint`.

**Label smoothing (ε=0.05).** Applied to training one-hot vectors only — validation uses hard labels. Prevents per-concern output neurons from collapsing to extreme 0.0/1.0 outputs, improving calibration.

| Property | Value |
|---|---|
| Per-concern branches | Dense(32) → Drop(0.15) → Dense(1, sigmoid) × 6 |
| Label smoothing | ε=0.05 (training only) |
| Monitored metric | val_f1_score (macro binary F1) |
| Phase 1 | 12 epochs frozen, LR=1e-3 |
| Phase 2 | 10 epochs fine-tune top 30, LR=1e-4 |
| Phase 3 | 8 epochs fine-tune top 60, cosine LR 5e-5→1e-7 |
| Ensemble weight | **0.8** |
| Saves to | `concern_model_v2.keras` |

---

#### v3 — `ml_model/concern_model_v3.keras`

The most significant improvement. Directly solves the train/test distribution mismatch that made v1 and v2 misclassify concerns.

**The core problem explained.** When we trained v1 and v2, the training pipeline looked like this:

```
Roboflow dataset → find image of "dark circles" → crop tightly to the annotated bbox
→ resize to 224×224 → train model

At inference: full face 224×224 → model
```

The model learned to recognise dark circles when they fill the entire 224×224 frame. But at inference it receives a full face where the dark circles are a small region in the under-eye area, roughly at y=32%-44% of the image height. This fundamental mismatch — training on patches, testing on full faces — is why the model would confuse texture (which has global texture features visible in any crop) for more localised concerns.

**The v3 fix — full-face training images.** v3 uses the full Roboflow image (with the concern somewhere in it) rather than cropping to the bbox. Now training and inference both use 224×224 full-face crops.

**The problem with naive full-face training.** If we just use the full image without the bbox, we lose information about where the concern is. An "acne" image where the acne bbox is on the forehead should train the model differently from one where the acne bbox is on the cheeks. Without using the bbox, both images look identical to the model.

**Bbox-aware soft labels — the key innovation.** Instead of a hard binary label (1.0 = concern present, 0.0 = absent), v3 computes a soft floating-point label for each training image based on how well the annotated concern bbox overlaps with the expected anatomical zone for that concern.

For example, dark circles are expected in the under-eye region `(y: 32-44%, x: 10-90%)`. If the annotated dark circles bbox has IoU (Intersection over Union) > 0.50 with this zone, the model receives label=0.95 (high confidence, well-localised). If the bbox barely overlaps the zone (IoU < 0.15), it receives label=0.55 (concern is present but something is off). If the bbox is completely outside the expected zone, it receives label=0.40 (likely a mislabelled or unusual sample).

```
bbox IoU with expected anatomical zone:
  > 0.50  →  label = 0.95   (excellent localisation — model trains strongly)
  > 0.15  →  label = 0.75   (good localisation)
  > 0.00  →  label = 0.55   (concern present, unusual position)
  = 0.00  →  label = 0.40   (no overlap — train weakly)

Non-Roboflow images (ds4, ds5, ds7 — no bboxes):
  →  label = 0.85   (full-face images, concern present, no spatial info)
```

This teaches the model spatial awareness: dark circles are associated with features in the under-eye region of a full face, not with features that fill the entire frame.

**Expected anatomical zones per concern (fractions of 224×224 face crop):**

| Concern | Expected zones |
|---|---|
| acne | left_cheek (38-72%, 4-38%), right_cheek (38-72%, 62-96%), forehead (4-28%, 22-78%), chin (72-92%, 28-72%) |
| blackheads | nose (32-65%, 36-64%), chin (72-92%, 28-72%) |
| dark_circles | under_left_eye (32-44%, 10-42%), under_right_eye (32-44%, 58-90%) |
| dark_spots | face_centre (15-85%, 15-85%) — can appear anywhere |
| redness | face_centre (15-85%, 15-85%) — global signal |
| texture | left_cheek, right_cheek, forehead (same as acne) |

**Polygon segmentation support.** The Roboflow datasets use different label formats. ds_rf1 uses YOLOv8-OBB polygon segmentation format where each line is `class_idx x1 y1 x2 y2 x3 y3 ... xN yN` with a variable number of polygon vertex pairs. The v3 label parser handles all formats:

```python
coords = parts[1:]   # everything after class index
if len(coords) == 4:
    # Standard YOLOv8: centre_x, centre_y, width, height
    cx, cy, w, h = float(coords[0]), float(coords[1]), ...
elif len(coords) >= 8 and len(coords) % 2 == 0:
    # Polygon or OBB: pairs of (x, y) vertices
    # Convert to axis-aligned bounding box
    xs = [float(coords[i]) for i in range(0, len(coords), 2)]
    ys = [float(coords[i]) for i in range(1, len(coords), 2)]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    w  = max(xs) - min(xs)
    h  = max(ys) - min(ys)
```

**`compile=False` at inference.** The training script defines a custom `BinaryF1` metric class. When Keras saves the model, it embeds metadata about this custom class. When loading, Keras tries to reconstruct the metric — but since `BinaryF1` is not decorated with `@keras.saving.register_keras_serializable()`, Keras cannot find it. The fix is to load with `compile=False`, which skips deserialising the optimizer and metrics entirely. This has zero effect on prediction accuracy — the weights and architecture load completely and correctly.

**Label path fix.** Roboflow filenames contain multiple dots (e.g. `125_jpg.rf.bf85166c12d714fb.jpg`). Python's `Path.stem` only removes the last extension — `125_jpg.rf.bf85166c12d714fb.jpg` → stem `125_jpg.rf.bf85166c12d714fb` → `125_jpg.rf.bf85166c12d714fb.txt`. This is correct. But using `(label_dir / img_path.stem).with_suffix('.txt')` would produce `label_dir/125_jpg.rf.txt` — wrong. The fix is string replacement:

```python
label_path = Path(str(img_path).replace('/images/', '/labels/')).with_suffix('.txt')
```

| Property | Value |
|---|---|
| Training images | Full-face 224×224 — NOT cropped to concern bbox |
| Label type | Per-image soft float 0.40–0.95 derived from bbox-zone IoU |
| Label map | Saved to `concern_training_data_v3/_label_map.json` for reproducibility |
| Architecture | Same as v2 (multi-scale SE + per-concern branches) |
| Monitored metric | val_f1_score |
| Phase 3 callbacks | `make_callbacks(reduce_lr=False)` — ReduceLROnPlateau incompatible with CosineDecay |
| Ensemble weight | **1.0** — highest weight, best spatial awareness |
| Saves to | `concern_model_v3.keras` |
| Load with | `compile=False` in `skin_concern_detector.py` |

**Training datasets for v3:**

| Dataset | Source | Format | Concerns | Soft label source |
|---|---|---|---|---|
| ds4/Skin_Conditions/ | Kaggle | Folder-named | acne (Acne/), redness (Rosacea/) | Fixed 0.85 |
| ds5/Skin v2/ | Kaggle | Folder-named | acne, blackheads (blackheades/), dark_spots, texture (pores/, wrinkles/) | Fixed 0.85 |
| ds7/ | Kaggle | Folder-named | dark_circles | Fixed 0.85 |
| ds_rf1/_raw/ | Roboflow | yolov8-obb polygon | acne: 1,195 · dark_circles: 991 · texture: 1,421 | Bbox-zone IoU |
| ds_rf2/_raw/ | Roboflow | Mixed standard+polygon | dark_circles: 1,114 | Bbox-zone IoU |

**Staged class counts after deduplication (capped at 2,000 per class):**

| Class | Images | Status |
|---|---|---|
| acne | 2,000 | OK |
| blackheads | 1,962 | OK |
| dark_circles | 2,000 | OK |
| dark_spots | 2,000 | OK |
| redness | 399 | LOW — only Kaggle ds4 Rosacea images |
| texture | 2,000 | OK |
| **Total** | **10,361** | |

---

## Face Detection Pipeline

Before any ML inference runs, the uploaded image must be detected and normalised. The pipeline produces **two distinct crops** from the same detected face — one for display and one for analysis. This two-crop approach is critical: the zone coordinates in the concern detector are calibrated to a tight face crop, not a padded display crop.

```
Input image (any resolution, any aspect ratio)
        │
        ▼
OpenCV Haar Cascade (primary detector)
  ├─ Tries 6 parameter combinations (scaleFactor, minNeighbors, minSize)
  ├─ Runs on both the original grayscale image AND the histogram-equalised
  │  version (equalisation helps detect low-contrast faces)
  ├─ Scores all detected candidates with:
  │     score = (face_area / total_area) × 2.5
  │           + eye_bonus (0.35 for 2 eyes, 0.12 for 1 eye, 0.0 for none)
  │           − (horizontal_distance_from_centre / half_image_width) × 0.5
  └─ Selects the highest-scoring candidate
        │
        ├──► DISPLAY CROP (stored in DB, shown to user)
        │    - Adds padding: 50% left/right, 70% top, 45% bottom
        │    - Square-pads with RGB(245,245,245) grey background
        │    - Resizes to 300×300 with Lanczos interpolation
        │    - Base64-encoded PNG stored in analyses.normalized_image_b64
        │
        └──► ANALYSIS CROP (used for all ML inference)
             - Tight bounding box only — no padding at all
             - Resizes to 224×224 with Lanczos interpolation
             - RGB uint8 numpy array
             - Used for: skin type CNN + all concern model ensemble + all CV signals
             - Never stored in the database directly

If Haar fails → MediaPipe Tasks API (requires blaze_face_short_range.tflite)
If MediaPipe fails → return face_found=False, user sees an error message
```

**Why the two-crop approach matters.** The zone coordinates in `skin_concern_detector.py` are fractions of the tight 224×224 analysis crop. For example:

```python
'under_left_eye': (0.32, 0.44, 0.10, 0.42)  # y: 32-44%, x: 10-42%
```

If you used the padded display crop (which has extra space around the face), the under-eye zone at 32-44% of the image height would point to the forehead area on the actual face. This was a real bug in early versions that caused all zone annotations to be placed on the wrong face regions.

**Why full-face photos produce better results.** After Haar detection, the tight bounding box is taken as-is. If the user uploads a zoomed-in photo of just their eyes, the "face" bbox covers the eyes only. The analysis crop then covers the eye region at 0-100% of the frame. Zone `under_left_eye` at 32-44% would point to the lower part of the iris, not the under-eye area. The Upload page now enforces full-face photos with a visual guide and warning banner.

**Face detection confidence score:**
```python
conf = min(0.55 + eyes_detected × 0.20 + (face_area / total_area) × 5.0, 0.99)
# Base: 55% (minimum for any detected face)
# +20% per detected eye (up to +40% for two eyes)
# Up to +40% bonus for large face relative to image
# Capped at 99% — we never claim 100% certainty
```

---

## Concern Detection Architecture

The `SkinConcernDetector` class in `skin_concern_detector.py` implements a 4-layer hybrid detection system.

### Layer 1 — Anatomical Zone Extraction

12 named facial zones are defined as `(y_start, y_end, x_start, x_end)` fractions of the 224×224 analysis crop:

```python
ZONES = {
    'forehead':        (0.04, 0.28, 0.22, 0.78),   # upper face
    'left_cheek':      (0.38, 0.72, 0.04, 0.38),   # left side of face
    'right_cheek':     (0.38, 0.72, 0.62, 0.96),   # right side of face
    'nose':            (0.32, 0.65, 0.36, 0.64),   # nose bridge to tip
    'chin':            (0.72, 0.92, 0.28, 0.72),   # lower face
    'left_eye':        (0.18, 0.36, 0.10, 0.42),   # eye socket area
    'right_eye':       (0.18, 0.36, 0.58, 0.90),
    'under_left_eye':  (0.32, 0.44, 0.10, 0.42),   # under-eye area
    'under_right_eye': (0.32, 0.44, 0.58, 0.90),
    'lip':             (0.65, 0.82, 0.30, 0.70),   # lip region
    't_zone':          (0.04, 0.72, 0.30, 0.70),   # forehead + nose
    'face_centre':     (0.15, 0.85, 0.15, 0.85),   # majority of face
}
```

A `_skin_tone_factor()` function computes overall face lightness (range 0.2 to 1.0) from the LAB colour space L-channel mean of the `face_centre` zone. This factor is used throughout the pipeline to adjust thresholds for different skin tones — darker skin tones have naturally higher contrast between regions, which would trigger false positives on some CV signals without tone correction.

### Layer 2 — Ensemble ML Detection + CV Signals

**ML ensemble (6 concerns):** `_load_ensemble()` loads all available concern model files at first call and caches them in `self._ensemble`. On each inference, `_run_model()` runs all cached models and computes a weighted average:

```python
total_weight = sum(w for _, w, _ in self._ensemble)
avg_probs = np.zeros(n_classes)
for model, weight, name in self._ensemble:
    probs = model.predict(arr, verbose=0)[0]   # (6,) sigmoid vector
    n = min(len(probs), n_classes)
    avg_probs[:n] += (weight / total_weight) * probs[:n]
# Calibration applied ONCE to the averaged probabilities
```

Calibration subtracts a per-class baseline and rescales. For example, for a v1-era model where texture has baseline=0.90:
```python
calibrated = max(0.0, (raw_prob - 0.90) / 0.10)
# raw=0.91 → calibrated=0.10 (weak detection)
# raw=0.95 → calibrated=0.50 (moderate detection)
```

For v3 where texture has been corrected, the baseline is much lower.

**CV-only signals (always run regardless of ML models):**

`eye_bags` — detects puffiness under the eyes using a 3-component brightness signal:
- The under-eye zone brightness is measured in LAB colour space L-channel
- Eye bags cause the under-eye to be BRIGHTER than the eye socket (bags protrude and reflect light)
- Gate: if `under_L - eye_L < 3.0`, score is 0.0 (no puffy bags detected)
- Score formula: `s1 × 0.6 + s2 × 0.25 + s3 × 0.15` where:
  - s1 = `(brightness_delta - 3.0) / 15.0` — primary brightness signal
  - s2 = row variance score — catches the horizontal ridge of a puffy bag
  - s3 = row-to-row std score — catches the sharp transition at the bag edge
- Display gate: 0.08 (lower than ML gate of 0.15, since CV scores naturally range lower)

`lip_hyperpigmentation` — detects lips that are significantly darker than the surrounding skin:
- Compares LAB L-channel mean of lip zone vs face_centre zone
- Also checks for purple/blue HSV hue ratio in the lip region (hue 120–160°)
- Both signals scaled by skin tone factor (darker skin tones have naturally darker lips)

### Layer 3 — Cross-Concern Calibration

After all raw scores are computed, a calibration pass applies three adjustments:

1. **Cross-concern boost:** If `acne > 0.35`, add 0.06 to redness (acne lesions are inflamed and typically involve some redness — this prevents redness from being missed when acne is present)
2. **Differential display gate:** CV-only signals (eye_bags, lip_hyperpigmentation) use gate=0.08. ML signals use gate=0.15. Any score below its gate is zeroed out to prevent noise concerns appearing in the UI.
3. **Clip:** All scores clamped to [0.0, 1.0]

### Layer 4 — Zone Annotation Images

For each concern that passes the display gate, a 224×224 annotated image is generated:
- Semi-transparent coloured fill overlay on the concern's associated face zones (22% opacity)
- Solid coloured border around each zone (2px)
- White inner highlight for contrast on dark skin (25% opacity)
- Small label pill above each zone, colour-coded by severity (green/amber/red)
- Upscaled to 300×300 with Lanczos interpolation
- Base64-encoded PNG stored in `skin_concerns.annotated_image_b64` in the database

### Severity Classification

| Concern | Mild | Moderate | Severe |
|---|---|---|---|
| acne | < 0.25 | 0.25 – 0.55 | > 0.55 |
| blackheads | < 0.25 | 0.25 – 0.55 | > 0.55 |
| dark_circles | < 0.25 | 0.25 – 0.55 | > 0.55 |
| eye_bags | < 0.22 | 0.22 – 0.50 | > 0.50 |
| redness | < 0.25 | 0.25 – 0.55 | > 0.55 |
| texture | < 0.30 | 0.30 – 0.65 | > 0.65 |
| hyperpigmentation | < 0.25 | 0.25 – 0.55 | > 0.55 |
| lip_hyperpigmentation | < 0.20 | 0.20 – 0.45 | > 0.45 |

---

## API Reference

All endpoints except `/api/auth/register` and `/api/auth/login` require a JWT Bearer token in the `Authorization` header. The Axios instance in `frontend/src/api/axios.ts` attaches this automatically from `localStorage`.

### Auth — `/api/auth`

**POST `/api/auth/register`**
```json
Request:  { "username": "john", "email": "john@example.com", "password": "secret123" }
Response: { "access_token": "eyJ...", "user": { "id": 1, "username": "john", "email": "..." } }
```

**POST `/api/auth/login`**
```json
Request:  { "email": "john@example.com", "password": "secret123" }
Response: { "access_token": "eyJ...", "user": { "id": 1, "username": "john", "email": "..." } }
```

**GET `/api/auth/me`** *(Auth required)*
Returns the currently authenticated user object.

---

### Analysis — `/api/analysis`

**POST `/api/analysis/upload`** *(Auth required, multipart/form-data)*

Max 16MB. Accepted formats: PNG, JPG, JPEG, WEBP. Form field name: `image`.

On success (HTTP 201), returns the complete analysis result including concern detections with annotated zone images and AI-generated recommendations. On face not detected (HTTP 200 with `success: false`), returns an error message and no analysis ID.

**GET `/api/analysis/history`** *(Auth required)*

Returns a list of all analyses for the authenticated user. The `normalized_image_b64` field is excluded from this list response to keep payload size small — it is only included in the full result endpoint.

**GET `/api/analysis/result/:id`** *(Auth required)*

Returns the complete analysis including `normalized_image_b64`, all concern detections with annotated images, and current product recommendations.

**GET `/api/analysis/uploads/:filename`** *(Auth required)*

Serves the original uploaded image file. This endpoint requires authentication because uploaded images are stored in a protected directory. The frontend uses an `AuthImage` component that fetches this via Axios (not a plain `<img src="...">`) so the JWT token is attached.

---

### Products — `/api/products`

**POST `/api/products/recommend`** *(Auth required)*

```json
Request:
{
  "skin_type": "Normal",
  "concerns": [
    { "concern_type": "dark_circles", "severity": "moderate" },
    { "concern_type": "texture", "severity": "mild" }
  ],
  "count": 5
}
```

Groq generates real, purchasable product names based on the skin type and active concerns. For each product, the backend calls the Open Beauty Facts API (`world.openbeautyfacts.org/cgi/search.pl`) with the brand and product name to retrieve a real product photo URL. No OBF API key is required.

The `amazon_image_url` field is either a real `https://` photo URL from OBF (frontend renders as `<img>`) or a `placeholder:X` marker (frontend renders a branded initial tile). Products are generated fresh on each request — not cached in the database.

---

### Routines — `/api/routines`

**POST `/api/routines/generate`** — Generates a morning or night routine using Groq based on a scan's skin type and detected concerns. Saved to database immediately.

**GET `/api/routines`** — Lists all routines for the authenticated user with their steps.

**DELETE `/api/routines/:id`** — Deletes a routine.

**POST `/api/routines/:id/activate`** — Sets the routine as active and deactivates all other routines of the same type (morning or night) for this user. At most one morning and one night routine can be active at a time.

---

### Chatbot — `/api/chatbot`

**POST `/api/chatbot/chat`** *(Auth required)*

```json
Request:
{
  "message": "What routine should I follow?",
  "history": [
    { "role": "user", "content": "previous message" },
    { "role": "assistant", "content": "previous reply" }
  ]
}
Response: { "reply": "For your skin type..." }
```

The backend reads the user's last 5 analyses from the database and includes them in the Groq system prompt as context. This means the chatbot knows your skin type, detected concerns, and recent confidence trends without you having to tell it. Conversation history is maintained in React state on the frontend and sent with each request — the backend is stateless.

---

### Report — `/api/report`

**GET `/api/report/summary`** *(Auth required)*

Returns a JSON summary of the past 7 days including total scans, average confidence, dominant skin type, confidence trend, recurring concerns with average scores, and a full list of all analyses with their normalized face images.

**GET `/api/report/weekly`** *(Auth required)*

Returns a formatted PDF file (`lumera_report_YYYYMMDD.pdf`). The PDF is built with `reportlab`'s Platypus high-level API and streamed directly from a `BytesIO` buffer — no temporary files are written to disk.

---

## Database Schema

### users
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| email | VARCHAR(120) | Unique across all users |
| username | VARCHAR(80) | Unique across all users |
| password_hash | VARCHAR(255) | bcrypt hash — plain password never stored |
| created_at | DATETIME | Set on insert, not updated |

### analyses
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | → users.id |
| image_path | VARCHAR(255) | Filename only (not full path) — e.g. `4_1773774672_IMG_1017.jpeg` |
| skin_type | VARCHAR(50) | One of: Combination, Dry, Normal, Oily, Sensitive |
| confidence | FLOAT | 0–100, percentage |
| recommendations | TEXT | JSON array of 3 strings from Groq |
| created_at | DATETIME | |
| normalized_image_b64 | TEXT | Base64 PNG of the 300×300 padded display crop |
| face_detection_confidence | FLOAT | 0–100, from Haar scoring formula |
| skin_concerns | TEXT | JSON dict mapping concern_type to raw score, for quick UI lookup |

### skin_concerns
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| analysis_id | INTEGER FK | → analyses.id |
| concern_type | VARCHAR(50) | e.g. 'dark_circles', 'eye_bags', 'hyperpigmentation' |
| confidence | FLOAT | 0.0–1.0 calibrated ensemble score |
| severity | VARCHAR(20) | 'mild', 'moderate', or 'severe' |
| notes | TEXT | AI-generated recommendation for this specific concern and severity |
| annotated_image_b64 | TEXT | Base64 PNG of the 300×300 face with coloured zone boxes drawn |
| created_at | DATETIME | |

### routines
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | → users.id |
| routine_type | VARCHAR(20) | 'morning' or 'night' |
| name | VARCHAR(200) | AI-generated name for the routine |
| description | TEXT | AI-generated description |
| is_active | BOOLEAN | True if this is the user's currently active routine of this type |
| created_at | DATETIME | |
| updated_at | DATETIME | Updated when is_active changes |

### routine_steps
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| routine_id | INTEGER FK | → routines.id |
| order | INTEGER | 1-indexed step number |
| product_type | VARCHAR(100) | e.g. 'Gentle Cleanser', 'Vitamin C Serum' |
| instruction | TEXT | What to do with the product |
| duration_seconds | INTEGER | Optional — how long to leave the product on |
| key_ingredient | VARCHAR(100) | The active ingredient to look for |
| created_at | DATETIME | |

---

## Frontend Pages

### Home (`/`)

Landing page for unauthenticated users. Shows three feature cards explaining the Upload → Analyse → Recommend workflow, and a stats strip with key numbers (95% accuracy, 9 concerns detected, AI-powered routines). Uses `PageShell` for the shared background.

### Login (`/login`) and Signup (`/signup`)

Centered card forms with the Luméra gradient icon above. Login stores `access_token` and `user` JSON in `localStorage` after a successful response. Signup does the same after registration. Neither page redirects to `/login` on error — errors are shown inline.

### Dashboard (`/dashboard`)

- Welcome banner with username and live stats (total scans, average confidence)
- Three quick-action cards: New Scan, AI Consultant, Track Progress
- Recent analyses grid using `AuthImage` component — each card shows the scan image (fetched via Axios with JWT to the protected `/api/analysis/uploads/:filename` endpoint), skin type badge, confidence bar
- Quick tips section

### Upload (`/upload`)

Two-column layout. The left panel (3/5 width) has the upload/camera form. The right panel (2/5 width) has two information cards:

**Photo guide card** — a custom inline SVG illustration showing two example photos side by side. Left: a full-face photo with a green checkmark, labelled "Full face". Right: a zoomed-in eye-only photo with a red X, labelled "Too zoomed". This visually communicates the requirement without text.

**Before you shoot checklist** — seven items with green tick icons (good) and red X icons (bad). Items cover face visibility, lighting, angle, skin preparation, and common mistakes.

**Amber warning banner** — explains in plain language why full-face photos are required: the AI maps concerns to specific face zones and a zoomed photo causes the zone coordinates to point to the wrong areas.

**Camera mode** — uses `getUserMedia` with front/rear toggle. The oval guide has `aspectRatio: 3/4.2` (taller than the previous 3/4) to encourage the user to step back until their full face fits. The guide text reads "Full face + neck should be visible".

### Results (`/results/:id`)

Three-tab layout:

**Concerns tab** — each active concern (score > 0.15) gets a card with its icon, severity badge, confidence bar, annotated zone image, and AI-generated recommendation.

**Products tab** — loaded lazily on first tab click. Displays products in a `HorizontalSlider` component. Cards are `w-64` fixed width and scroll left/right. Arrow buttons appear when there is overflow content. `ProductImageTile` renders a real `<img>` when the `amazon_image_url` starts with `https://` (from OBF). When the image fails to load or no OBF image was found, it falls back to a compact `h-14` horizontal brand-initial strip rather than a tall empty box.

**Routine tab** — generate a morning or night routine on demand. The generated steps are saved to the database automatically and can be viewed in the Routines page.

### Progress (`/progress`)

- 4 stat tiles at the top
- Interactive calendar — days with scans are highlighted with the skin type colour. Click a day to open the detail panel.
- **Fixed-height day panel** — the right panel always stays the same height regardless of how many scans are on the selected day. Scans scroll internally within a `maxHeight: 340px` container. Previously this panel expanded the page to a large height when multiple scans were selected.
- Skin type distribution bars
- Full scan history table

### Chatbot (`/chatbot`)

Conversation interface with the Lumé bot. Initial greeting with 4 suggested quick questions. Messages use gradient purple bubbles for user, grey bubbles for assistant. Typing indicator (three bouncing dots) while waiting for Groq response.

### Routines (`/routines`)

Accordion-style cards grouped by Morning and Night. Expanding a card shows all steps with step number circles, product type, instruction, timing, and key ingredient. "Set Active" and "Delete" actions per routine.

### Weekly Report (`/report`)

Interactive bar chart showing every scan from the past 7 days. Each bar is coloured by the skin type detected in that scan. Clicking a bar opens a scan detail modal with the face photo and detected concerns. Concerns section shows recurring concerns with annotated zone thumbnails that also open the scan modal when clicked. PDF download triggers a blob fetch from the `/api/report/weekly` endpoint.

---

## Features Deep Dive

### JWT Authentication Flow

Tokens are issued as `str(user.id)` (a string, not an integer). Flask-JWT-Extended v4 validates that identities are JSON-serialisable, and earlier versions that stored integers directly caused 422 errors. All route handlers call `int(get_jwt_identity())` to convert back. Token expiry is 7 days.

`ProtectedRoute` checks `localStorage.getItem('token')` synchronously on render — not in a `useEffect`. This eliminates the brief flash where a logged-in user would see the login page before the async check resolved.

### Ensemble Concern Detection — Implementation Details

`_load_ensemble()` is called at first inference request and populates `self._ensemble` with all available models. Subsequent requests use the cached list — no re-loading overhead.

```python
def _load_ensemble(self):
    if self._ensemble:   # already loaded
        return self._ensemble
    candidates = [
        ('concern_model_v3.keras', 1.0),
        ('concern_model_v2.keras', 0.8),
        ('concern_model.keras',    0.5),
    ]
    for fname, weight in candidates:
        path = os.path.join(base, fname)
        if os.path.exists(path):
            model = keras.models.load_model(path, safe_mode=False, compile=False)
            self._ensemble.append((model, weight, fname))
    return self._ensemble
```

All three models stay in RAM for the lifetime of the Flask process. Total memory: approximately 36 MB (12 MB per model). For low-memory deployments, rename or remove model files to exclude them from the ensemble.

### Eye Bags CV Signal — Why the Gate Was Lowered

The original eye bags signal required `under_L - eye_L >= 8.0` LAB-L units before scoring anything. Diagnostic testing on the same face consistently showed deltas of 45–65 LAB-L units — way above the gate. The signal itself was working correctly, producing a score of 1.0.

The problem was the display gate in `_calibrate()` was set to 0.15 for all concerns. A CV signal that produces scores in the 0.08–0.20 range for mild eye bags was being zeroed out. The fix was a differential gate: CV-only signals (eye_bags, lip_hyperpigmentation) use gate=0.08, while ML ensemble signals use gate=0.15.

### Dynamic Products with Real Images

```python
# In routes/products.py — _obf_image()
params = {
    'search_terms': f"{brand} {product_name}",
    'search_simple': 1,
    'action':        'process',
    'json':          1,
    'page_size':     5,
    'fields':        'product_name,brands,image_front_url,image_url',
}
resp = _session.get('https://world.openbeautyfacts.org/cgi/search.pl',
                    params=params, timeout=4)
products = resp.json().get('products', [])
for p in products:
    img = p.get('image_front_url') or p.get('image_url')
    if img and img.startswith('https://'):
        return img   # real product photo found
return f"placeholder:{brand[0].upper()}"   # fallback
```

The 4-second timeout means product loading never blocks the UI significantly. OBF has strong coverage of CeraVe, The Ordinary, La Roche-Posay, Neutrogena, and Kiehl's — the brands Groq most commonly recommends for skincare.

### Two-Phase Groq Recommendation Generation

During `/api/analysis/upload`, recommendations are generated twice:

1. **Immediately after skin type classification** — based on skin type and confidence only. Stored temporarily.
2. **After concern detection runs** — regenerated with the full concern context (skin type + all detected concerns + severity levels). This second set overwrites the first in the database.

This ensures that if dark circles are detected, the recommendations say "use an eye cream with caffeine" rather than generic skin type advice. If Groq is unavailable, the system falls back to a static dict of 3 recommendations per skin type.

---

## Training the Models

### Skin Type Model v2

```bash
cd lumera/backend
source venv/bin/activate

# Download all three Kaggle datasets
kaggle datasets download -d shakyadissanayake/oily-dry-and-normal-skin-types-dataset \
    -p dataset_downloads/ds1 --unzip
kaggle datasets download -d ritikasinghkatoch/normaldryoily-skin-type \
    -p dataset_downloads/ds2 --unzip
kaggle datasets download -d killa92/facial-skin-analysis-and-type-classification \
    -p dataset_downloads/ds3 --unzip

# Merge all datasets into training_data/combination/ dry/ normal/ oily/ sensitive/
python ml_model/merge_datasets.py

# Optional: scan for corrupt images before training
python ml_model/audit_data.py

# Train — saves to ml_model/best_model_v2.keras
python ml_model/train_model.py
```

**Key implementation notes:**
- `normalise_train()` applies label smoothing; `normalise_val()` uses hard labels — critical for honest validation metrics
- `augment()` uses random crop-and-resize for zoom effect — no `tfa` dependency, MPS-compatible
- Phase 3 uses `CosineDecay` schedule — no `ReduceLROnPlateau` oscillation
- A confidence distribution histogram is printed after training to verify overconfidence is reduced

---

### Concern Model v2

```bash
# Add ROBOFLOW_API_KEY to backend/.env first
python download_concern_datasets.py   # downloads ds_rf1, ds_rf2

# Train
python ml_model/train_concern_model_v2.py
```

**Key implementation notes:**
- `load_train()` applies label smoothing; `load_val()` uses hard one-hot labels
- `aug()` uses `tf.stack([crop_size, crop_size, 3])` for the crop shape tensor — passing a scalar crashes
- Monitored metric is `val_f1_score` not `val_accuracy`
- Per-concern branches give each class its own decision boundary

---

### Concern Model v3 (Full-Face + Bbox-Aware)

```bash
# Check data sources and verify everything is findable before starting:
python ml_model/train_concern_model_v3.py

# Start training (adds --train flag):
python ml_model/train_concern_model_v3.py --train
```

**Critical implementation notes — read before modifying:**

**1. Label path construction.** Roboflow filenames have multiple dots, e.g. `125_jpg.rf.bf85166c12d714fb686c3f2a8f51356c.jpg`. Using `Path.stem` gives `125_jpg.rf.bf85166c12d714fb686c3f2a8f51356c`, and `.with_suffix('.txt')` correctly gives `125_jpg.rf.bf85166c12d714fb686c3f2a8f51356c.txt`. However, `(label_dir / img_path.stem).with_suffix('.txt')` incorrectly truncates to `label_dir/125_jpg.rf.txt`. Always use string replacement:
```python
label_path = Path(str(img_path).replace('/images/', '/labels/')).with_suffix('.txt')
```

**2. Polygon label format.** ds_rf1 uses YOLOv8-OBB polygon segmentation (not standard cx/cy/w/h). Each line has a variable number of xy coordinate pairs. The parser must handle both formats:
```python
if len(coords) == 4:      # standard: cx cy w h
    cx, cy, w, h = ...
elif len(coords) >= 8 and len(coords) % 2 == 0:  # polygon
    xs = coords[0::2]; ys = coords[1::2]
    cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2
    w=max(xs)-min(xs); h=max(ys)-min(ys)
```

**3. `darkcircle` in RF_CLASS_MAP.** ds_rf1's `data.yaml` lists the class as `darkcircle` (no underscore). The yaml parser normalises it to lowercase with underscores replaced, giving `darkcircle`. This must be in `RF_CLASS_MAP` as `'darkcircle': 'dark_circles'`.

**4. Phase 3 must disable ReduceLROnPlateau.** Keras raises `TypeError` if `ReduceLROnPlateau` tries to set the learning rate on an optimizer that was created with a `LearningRateSchedule` object. Phase 3 uses `CosineDecay`, so its callbacks must be `make_callbacks(reduce_lr=False)`.

**5. BinaryF1 `add_weight` API.** Keras 3.x changed `add_weight` to require `name=` as a keyword argument. Use `self.add_weight(name='tp', shape=(n,), ...)` not `self.add_weight('tp', (n,), ...)`.

**6. `compile=False` at inference.** The model embeds the custom `BinaryF1` class in its saved metadata. Loading without `compile=False` raises `Could not locate class 'BinaryF1'`. Add `compile=False` to `keras.models.load_model()` in `skin_concern_detector.py`.

---

## Complete Bug Fix History

| # | Issue | Root Cause | Fix |
|---|---|---|---|
| 1 | Session expired on every upload | Axios interceptor deleted token on any 422 | Only clear token on genuine JWT 422s (check message content) |
| 2 | Login page flashes for logged-in users | ProtectedRoute used async 100ms timeout check | Replaced with synchronous `localStorage.getItem` check on render |
| 3 | All images classified as Oily | Feature extraction ran on full image, not face crop | Added tight face bbox extraction before all feature computation |
| 4 | 422 on all authenticated API calls | JWT identity stored as integer | Changed to `str(user.id)` on issue, `int(get_jwt_identity())` on read |
| 5 | Full-body / small faces not detected | BlazeFace (MediaPipe) misses non-close-up faces | Added OpenCV Haar cascade as primary detector, MediaPipe as fallback |
| 6 | Wrong face selected from multiple candidates | Largest bounding box was often background elements | Multi-criterion scoring: area + eye detection + horizontal centrality |
| 7 | Dashboard images return 401 | `<img src="...">` cannot send Authorization header | `AuthImage` component fetches via Axios blob (JWT token attached) |
| 8 | Model always predicts Sensitive | Hard-coded class order didn't match training order | Load class order from `class_indices.json` |
| 9 | Model predicts wrong class even with correct order | `preprocess_input` not applied before inference | Apply `preprocess_input` in `_predict_cnn` |
| 10 | Garbage predictions after preprocessing fix | Model already has `preprocess_input` baked in as layers | Feed raw [0,1] float directly — never call `preprocess_input` manually |
| 11 | `TrueDivide` unknown layer on model load | Old Sequential model incompatible with TF 2.21/Keras 3 | Retrained from scratch using Functional API |
| 12 | `RandomRotation` crash during training | Keras augmentation layer inside `tf.data.map` | Replaced with pure TF ops augmentation (no Keras layers in data pipeline) |
| 13 | Model saved to wrong path | Training script run from inside `ml_model/` | Always run train scripts from `backend/` — BASE path is relative to script location |
| 14 | Concern detection never runs | `analysis_image` not included in `analyze()` return dict | Added `'analysis_image': norm['analysis_image']` to return value |
| 15 | Concern model needs `safe_mode=False` | Model contained a `Lambda` layer for preprocessing | Replaced Lambda with `Rescaling(scale=2.0, offset=-1.0)` — serialises cleanly |
| 16 | Texture fires at 99-100% on every face | Softmax output + texture class had 9× more training data | Retrained with sigmoid output + binary_crossentropy (multi-label) |
| 17 | Texture still 99% after sigmoid retraining | Raw sigmoid baseline ~0.90 for texture even on clean face | Applied per-class calibration baselines in `_run_model()` |
| 18 | All concerns firing simultaneously | CV signal thresholds not calibrated for real face measurements | Empirical calibration using measured LAB values per signal |
| 19 | Redness fires on normal warm skin | Red dominance formula didn't account for warm/brown skin tone | Raised baseline: `0.28 + (1 - tone) × 0.15` |
| 20 | Dark circles firing on face with no dark circles | Blue ratio scored regardless of L-channel comparison | Added hard zero: `if eye_L >= cheek_L: return 0.0` |
| 21 | Hyperpigmentation fires on beard shadow | `baseline_std=30` too low — beard creates L-std of 55-60 | Raised to `55 + (1 - tone) × 10` |
| 22 | Dryness fires on normal/medium skin | Missing early-exit for shine/L-std check | Added: `if shine > 0.015 or l_std > 40: return 0.0` |
| 23 | Recommendations hardcoded | Static dict in `ml_service._get_recommendations()` | Groq call with skin type + confidence + concerns context |
| 24 | Products hardcoded | Static seeded `product_recommendations` table | Groq-generated dynamic products with OBF image enrichment |
| 25 | Weekly report 404 | `routes/report.py` was empty on disk | Rewritten via Python script (heredoc shell corruption prevented direct write) |
| 26 | Report confidence chart invisible | One bar per scan; 43 scans produced 1px-wide bars | Day-grouped chart with `groupByDay()` — max 7 bars per week |
| 27 | Report route 404 after blueprint registration | Old empty `report.py` still on disk despite correct `app.py` | Verified with `python3 -c "from routes.report import report_bp"` |
| 28 | Luméra logo navigates to landing page when logged in | `<Link to="/">` hardcoded | Changed to `to={isLoggedIn ? '/dashboard' : '/'}` |
| 29 | Routine generation 404 | `routine_bp` not registered in `app.py` | Added import + `app.register_blueprint(routine_bp, ...)` |
| 30 | Groq API key not found in routes | Client initialised at import time before `load_dotenv()` ran | Lazy init: `_get_groq()` function calls `load_dotenv()` before creating client |
| 31 | v3 training finds no images | `BASE = os.path.dirname(__file__)` = `ml_model/`, not `backend/` | Changed to `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` |
| 32 | Roboflow download fails with folder format error | All three datasets are object-detection, not classification | Download in `yolov8` format, parse label files to identify concern per image |
| 33 | ds_rf2 yaml unparseable — class name `Puffy Eyes - v3 Dark Circle` | Non-standard class name with spaces and hyphens | Added fallback: if yaml class is unparseable, treat entire dataset as dark_circles (single-class) |
| 34 | `aug()` crash with `tf.image.random_crop` | `crop_size` was a scalar — `random_crop` needs a shape tensor | Changed to `tf.stack([crop_size, crop_size, 3])` |
| 35 | Rotation augmentation silently broken | `tf.image.rot90` only rotates 90° multiples — computed angle was ignored | Replaced with crop-and-resize zoom augmentation |
| 36 | Label smoothing corrupted val accuracy | Single `load()` function applied smoothing to both train and val samples | Split into `load_train()` (smoothed) and `load_val()` (hard one-hot) |
| 37 | `fine_proj` NameError in concern model v2 | Variable named `fine_gap` all the way through, then referenced as `fine_proj` in Concatenate | Renamed final fine branch Dense output to `fine_proj` |
| 38 | Products tab returns 500 error | Groq account restricted (`organization_restricted` API error) | Added OBF image enrichment as separate step; Groq restriction resolved via support |
| 39 | Product image shows blank tall square box when no OBF image found | `ProductImageTile` always rendered a square aspect-ratio container | No-image fallback is now a compact `h-14` horizontal strip — never a tall blank box |
| 40 | Products expand page height as grid | 3-column grid with many cards made page very tall | Replaced with `HorizontalSlider` — cards slide left/right within fixed height |
| 41 | Day panel in Progress expands page when many scans on one day | Panel had no height limit, all scans stacked vertically | Fixed `minHeight: 420px`, internal `overflow-y-auto` with `maxHeight: 340px` |
| 42 | Eye bags never detected | Gate of 8.0 LAB-L too strict — real eye bags show 3–5 units delta | Lowered gate to 3.0, added row-to-row std component, lowered display gate to 0.08 |
| 43 | RF datasets return 0 samples in v3 | `Path.stem` truncated multi-dot Roboflow filenames → wrong label path | Used string replacement `/images/` → `/labels/` for label path construction |
| 44 | `darkcircle` not found in RF_CLASS_MAP | ds_rf1 yaml lists class as `darkcircle` (no underscore) | Added `'darkcircle': 'dark_circles'` to RF_CLASS_MAP |
| 45 | RF label files return 0 bboxes | ds_rf1 uses yolov8-obb polygon format (17 values per line) | Added polygon parser: any even-length coordinate list → axis-aligned bbox |
| 46 | `BinaryF1 add_weight` TypeError | Keras 3.x changed positional arg `shape` to keyword-only | Changed to `self.add_weight(name='tp', shape=(n,), ...)` throughout |
| 47 | `ReduceLROnPlateau` TypeError in Phase 3 | Cannot set LR on optimizer created with `LearningRateSchedule` | Added `reduce_lr=False` parameter to `make_callbacks()`, used in Phase 3 |
| 48 | v3 fails to load — `Could not locate class BinaryF1` | Custom metric not registered with Keras serialisation system | Load all concern models with `compile=False` — metrics not needed at inference |
| 49 | Concerns misclassified — texture detected instead of eye bags or dark circles | v1/v2 trained on zone crops, inferred on full face — train/test mismatch | v3 trained on full-face images; ensemble averaging reduces individual model errors |
| 50 | Zoomed-in photos produced wrong detections silently | No guidance shown — users uploaded close-ups of individual features | Two-column upload page with SVG illustration, photo checklist, amber warning banner |

---

## Known Limitations

**Sensitive skin class — 80 training images.** The skin type model has 3,075 Normal images but only 80 Sensitive images. This is the single largest accuracy bottleneck. The model significantly underperforms on sensitive skin detection and will often classify sensitive skin as Normal or Dry. A class weight of 10× is applied during training to compensate, but this is insufficient with only 80 examples.

**Redness detection — 399 training images.** The smallest concern class. The model raw sigmoid output for redness is typically < 0.01 on most faces, meaning it only fires on genuinely severe redness. Mild redness will usually be missed. There is no CV-only fallback for redness — the only boost is the `acne > 0.35 → redness + 0.06` cross-concern adjustment.

**v3 soft labels mostly 0.85 in practice.** The bbox-aware soft label system is implemented correctly, but the Roboflow polygon annotations for ds_rf1 tend to be very large (sometimes covering the entire face for a single concern). When the bbox covers the entire face, its IoU with any specific zone is low, and the sample falls back to the 0.40 "uncertain" label. Images from ds4/ds5/ds7 without bboxes use a fixed 0.85 label. In practice, the average soft label across all v3 samples is close to 0.85 — the IoU-based differentiation has limited effect with the current datasets. Better results would come from datasets with tightly-annotated concern-specific bboxes.

**Open Beauty Facts coverage.** OBF has excellent coverage of major Western skincare brands (CeraVe, The Ordinary, La Roche-Posay, Neutrogena, Kiehl's, Paula's Choice). It has limited coverage of Asian brands, Indian brands, and niche/indie brands. Products from these brands will fall back to the placeholder initial tile.

**Concern calibration tested on limited demographics.** The per-class calibration baselines in `_run_model()` and the CV signal thresholds were empirically tuned on Indian male skin with medium skin tone under indoor lighting. Edge cases may exist for very dark or very light skin tones, unusual lighting conditions, heavy facial hair, or atypical face geometry.

**No real-time streaming.** Groq responses are not streamed — the chatbot waits for the full completion before displaying. Adding streaming would require Server-Sent Events (SSE) or WebSocket support in both Flask and React.

**Ensemble memory usage.** All three concern models stay loaded in RAM (~36 MB total, ~12 MB each). On production servers with limited RAM, remove or rename unwanted model files to reduce the ensemble to just v3.

**MPS training speed.** On Apple Silicon with `tensorflow-metal`, some TensorFlow operations fall back to CPU execution. Training is functional but significantly slower than CUDA. The crop-and-resize augmentation was specifically chosen over `tfa.image.rotate` to avoid MPS-incompatible operations.

---

## Roadmap

- [ ] **Sensitive skin data** — collect 400+ labelled sensitive skin images to bring class to parity with others
- [ ] **Redness data** — source 1,000+ rosacea and redness images; current 399 is insufficient for reliable detection
- [ ] **Amazon PA API** — apply for Associates program to get official product images instead of OBF
- [ ] **Scan journal** — let users add free-text notes per scan (diet, products used, sleep, stress)
- [ ] **Streak tracking** — gamify scan consistency with streak badges (7-day, 30-day etc.)
- [ ] **Weekly email digest** — automated email with weekly report using Flask-Mail + scheduled job
- [ ] **PWA** — add `manifest.json` + service worker for installable mobile experience
- [ ] **Production deployment** — gunicorn + Nginx + PostgreSQL + S3/Cloudinary for image storage
- [ ] **Multi-language support** — UI translations, especially for Indian skin tone dataset annotations
- [ ] **Before/after comparison** — side-by-side scan view to visualise skin improvement over time
- [ ] **Streaming chatbot** — SSE-based streaming for Groq responses so replies appear word by word
- [ ] **eye_bags ML class** — source dedicated eye bag training images, add as a 7th ML class in v4
- [ ] **v3 tighter annotations** — source or create datasets with tight per-concern bboxes rather than full-face polygon annotations, to get meaningful soft label spread (currently most samples score 0.85 due to large annotation polygons)
- [ ] **Skin type v3** — apply the same full-face + spatial annotation approach to skin type if localised datasets become available (e.g. oily T-zone with dry cheeks for combination skin)
- [ ] **Confidence intervals** — show uncertainty range on predictions rather than a single percentage