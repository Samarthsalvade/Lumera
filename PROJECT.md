# Luméra — AI Skincare Analysis Platform

A full-stack web application that analyses your skin from a photo. It classifies your skin type (combination, dry, normal, oily, sensitive), detects up to 8 skin concerns (acne, blackheads, dark circles, eye bags, hyperpigmentation, lip hyperpigmentation, redness, texture), recommends personalised skincare products, generates morning and night routines, tracks your progress over time with an interactive calendar, and lets you chat with an AI skincare consultant. Built as a personal project from scratch.

**Live App:** https://lumera-wheat.vercel.app
**Backend API:** https://samarth1812-lumera-backend.hf.space/api/health

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Local Development Setup](#local-development-setup)
5. [Environment Variables](#environment-variables)
6. [Database — Neon PostgreSQL](#database--neon-postgresql)
7. [Image Storage — Cloudinary](#image-storage--cloudinary)
8. [ML Models — Git LFS](#ml-models--git-lfs)
9. [Backend Deployment — Hugging Face Spaces](#backend-deployment--hugging-face-spaces)
10. [Why We Migrated Away From Render](#why-we-migrated-away-from-render)
11. [Frontend Deployment — Vercel](#frontend-deployment--vercel)
12. [Making Changes and Redeploying](#making-changes-and-redeploying)
13. [Keep HF Space Awake — UptimeRobot](#keep-hf-space-awake--uptimerobot)
14. [ML Models Deep Dive](#ml-models-deep-dive)
15. [Face Detection Pipeline](#face-detection-pipeline)
16. [Concern Detection Architecture](#concern-detection-architecture)
17. [API Reference](#api-reference)
18. [Database Schema](#database-schema)
19. [Frontend Pages](#frontend-pages)
20. [Features Deep Dive](#features-deep-dive)
21. [Training the Models](#training-the-models)
22. [Complete Bug Fix History](#complete-bug-fix-history)
23. [Known Limitations](#known-limitations)
24. [Roadmap](#roadmap)

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
| **Vercel** | — | Frontend hosting — auto-deploys on every push to main |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.12 | Runtime |
| Flask | 3.0 | Web framework |
| Gunicorn | 21.2 | Production WSGI server — replaces Flask dev server on HF Spaces |
| Flask-JWT-Extended | 4.x | JWT authentication — tokens issued as strings, 7-day expiry |
| SQLAlchemy | latest | ORM — models defined in `models.py` |
| psycopg2-binary | 2.9.9 | PostgreSQL driver for Neon |
| OpenCV (headless) | 4.10 | Haar cascade face detection + all CV-based concern signals |
| Pillow | 11.0 | Image compression, resize, base64 encoding |
| TensorFlow | 2.21 | CNN model runtime for both skin type and concern classification |
| Keras | 3.x | High-level model loading and inference API |
| Cloudinary SDK | 1.41 | Image upload to cloud storage |
| Groq SDK | latest | LLM API — llama-3.1-8b-instant for recommendations, routines, chatbot |
| reportlab | 4.x | PDF report generation using Platypus high-level API |
| requests | latest | HTTP client for Open Beauty Facts API (product image lookup) |
| python-dotenv | latest | Loads `.env` file into `os.environ` at startup |
| numpy | latest | Array operations for image processing and model inference |
| **Hugging Face Spaces** | — | Backend hosting — Docker-based, 16 GB RAM, free tier |

### Data & Storage
| Service | What it stores | Free tier |
|---|---|---|
| **Neon** (PostgreSQL) | Users, analyses, concerns, routines, products | 0.5 GB storage, no credit card |
| **Cloudinary** | Uploaded + compressed face photos | 25 GB storage, 25 GB bandwidth/month |
| **Git LFS** | ML model `.keras` files (~135 MB total) | Tracked in repo, pushed to HF via LFS |

---

## Architecture Overview

```
User Browser (https://lumera-wheat.vercel.app)
     │
     │  React + TypeScript + Tailwind
     │  Axios attaches JWT to every request
     │
     ▼
Vercel CDN — static React build
     │
     │  HTTPS API calls to Hugging Face Spaces
     │
     ▼
HF Spaces Docker Container (https://samarth1812-lumera-backend.hf.space)
     │  Gunicorn → Flask → SQLAlchemy
     │  1 worker, 300s timeout, 16 GB RAM
     │  Models baked into Docker image via Git LFS — no runtime download
     │
     ├──► Neon PostgreSQL
     │    users, analyses, skin_concerns,
     │    routines, routine_steps, product_recommendations
     │
     ├──► Cloudinary
     │    Original + compressed uploaded images
     │    Served directly to frontend via https:// URL
     │
     └──► Groq API (llama-3.1-8b-instant)
          Recommendations, routines, chatbot responses
```

**Key design decisions:**
- Images are compressed to max 1024px JPEG before ML processing — prevents timeouts on large phone photos
- ML models load in a background thread at startup — server is live immediately, models ready within 2–3 minutes
- Models are baked directly into the Docker image via Git LFS — zero re-download on every deploy (unlike the previous Render setup)
- Cloudinary URLs stored in DB instead of base64 — keeps database lean
- Normalised face crop (300×300 padded) stored as base64 in DB for instant Results page display without re-fetching

---

## Project Structure

```
lumera/
├── .gitignore
├── .gitattributes                     # Git LFS tracking rules — *.keras tracked via LFS
├── PROJECT.md                         # This file — full project documentation
├── README.md                          # HF Spaces config (YAML frontmatter only)
├── Dockerfile                         # Root-level Dockerfile for HF Spaces Docker SDK
├── render.yaml                        # Legacy Render config — kept for reference, no longer used
├── frontend/
│   ├── vercel.json                    # SPA routing fix — rewrites all paths to index.html
│   ├── .env.development               # VITE_API_URL=http://localhost:3001/api
│   ├── .env.production                # VITE_API_URL=https://samarth1812-lumera-backend.hf.space/api
│   ├── public/
│   │   └── favicon.svg                # Purple gradient L icon
│   ├── src/
│   │   ├── api/
│   │   │   └── axios.ts               # Axios instance — reads VITE_API_URL env var
│   │   ├── components/
│   │   │   ├── PageShell.tsx          # Shared bg: #f5f3ff + dot-grid SVG + purple accent circles
│   │   │   ├── Navbar.tsx             # Responsive navbar, logo routes to dashboard/home by auth state
│   │   │   └── ProtectedRoute.tsx     # Synchronous JWT guard — no async delay, no login flash
│   │   ├── pages/
│   │   │   ├── Home.tsx               # Landing page
│   │   │   ├── Login.tsx / Signup.tsx
│   │   │   ├── Dashboard.tsx          # Scan history grid, quick actions
│   │   │   ├── Upload.tsx             # Camera/file upload with photo guide + image compression
│   │   │   ├── Results.tsx            # Concerns · Products · Routine tabs
│   │   │   ├── Progress.tsx           # Calendar + day panel
│   │   │   ├── Chatbot.tsx            # AI skincare consultant
│   │   │   ├── Routines.tsx           # Morning/night routine manager
│   │   │   └── WeeklyReport.tsx       # Bar chart + PDF download
│   │   ├── types/index.ts
│   │   └── App.tsx
│   └── package.json
│
└── backend/
    ├── app.py                         # Flask factory — CORS, blueprints, background model loading
    ├── config.py                      # Reads DATABASE_URL, CLOUDINARY_*, GROQ_API_KEY from env
    ├── models.py                      # SQLAlchemy ORM: User, Analysis, SkinConcern, Routine, etc.
    ├── download_models.py             # Legacy — downloaded .keras files from Google Drive on Render
    │                                  # No longer called at startup — models are baked into image
    ├── skin_concern_detector.py       # SkinConcernDetector — hybrid ML ensemble + CV signals
    ├── requirements.txt
    ├── routes/
    │   ├── auth.py                    # /register /login /logout /me
    │   ├── analysis.py                # /upload (compress→ML→Cloudinary) /history /result/:id
    │   ├── chatbot.py                 # /chat — Groq with last 5 scan context
    │   ├── routines.py                # CRUD + /activate
    │   ├── products.py                # /recommend — Groq + OBF images
    │   └── report.py                  # /summary (JSON) + /weekly (PDF)
    ├── services/
    │   └── ml_service.py              # SkinAnalyzer: face detection, two-crop, CNN inference
    ├── utils/
    │   └── helpers.py                 # allowed_file() — validates PNG/JPG/JPEG/WEBP
    └── ml_model/
        ├── best_model_v2.keras        # Skin type CNN v2 — tracked via Git LFS
        ├── concern_model_v3.keras     # Concern CNN v3 — tracked via Git LFS
        ├── concern_model_v2.keras     # Concern CNN v2 — tracked via Git LFS
        ├── concern_model.keras        # Concern CNN v1 — tracked via Git LFS
        ├── class_indices.json         # Skin type class order (small, committed normally)
        ├── concern_class_indices*.json
        └── train_*.py                 # Training scripts (run locally, not on HF Spaces)
```

---

## Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- Git + Git LFS installed (`git lfs install`)
- A free Groq API key — https://console.groq.com
- A free Cloudinary account — https://cloudinary.com
- The `.keras` model files — automatically available after `git clone` if LFS is installed

### Backend

```bash
cd lumera/backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

# Install all dependencies
pip install -r requirements.txt

# Create .env file (see Environment Variables section)
touch .env
# Paste your credentials into it

# Start backend
python app.py
# Runs on http://localhost:3001
```

Expected startup output:
```
✓ Database tables created
⏳ ML models loading in background...
🚀 Starting backend on http://localhost:3001
 * Running on http://127.0.0.1:3001
...
✓ Skin type model ready — classes: ['Combination', 'Dry', 'Normal', 'Oily', 'Sensitive']
✓ Concern model ready: concern_model_v3.keras (weight=1.0)
✓ Concern model ready: concern_model_v2.keras (weight=0.8)
✓ Concern model ready: concern_model.keras (weight=0.5)
✅ All models loaded and ready
```

### Frontend

```bash
cd lumera/frontend
npm install
npm run dev
# Runs on http://localhost:5173 (or 5174 if 5173 is taken)
```

The frontend reads `VITE_API_URL` from `.env.development` which points to `http://localhost:3001/api`. Both CORS origins (5173 and 5174) are whitelisted in `app.py`.

### Verify Everything Works

```bash
# Backend health check
curl http://localhost:3001/api/health
# Expected: {"status": "ok", "message": "Backend is running"}

# Verify skin type model
python3 -c "
from services.ml_service import get_analyzer
a = get_analyzer()
print('Model loaded:', a.model is not None)
print('Classes:', a.skin_types)
"

# Verify concern ensemble
python3 -c "
from skin_concern_detector import SkinConcernDetector
d = SkinConcernDetector()
for model, weight, name in d._load_ensemble():
    print(f'{name}  weight={weight}')
"
```

---

## Environment Variables

### `backend/.env` — local only, never commit

```env
SECRET_KEY=lumera-super-secret-key-min-32-chars-long-12345
JWT_SECRET_KEY=lumera-super-secret-key-min-32-chars-long-12345

# Leave DATABASE_URL absent locally — Flask uses SQLite automatically
# DATABASE_URL=postgresql://...   ← only set this on HF Spaces

GROQ_API_KEY=gsk_your_actual_key_here

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### `frontend/.env.development` — local frontend

```env
VITE_API_URL=http://localhost:3001/api
```

### `frontend/.env.production` — committed, no secrets

```env
VITE_API_URL=https://samarth1812-lumera-backend.hf.space/api
```

### HF Spaces Secrets — set in Space dashboard

Go to: `https://huggingface.co/spaces/Samarth1812/lumera-backend` → **Settings** → **Variables and secrets**

| Key | Where to get it |
|---|---|
| `SECRET_KEY` | Any long random string |
| `JWT_SECRET_KEY` | Any long random string |
| `DATABASE_URL` | Neon dashboard → Connection string (includes `?sslmode=require`) |
| `GROQ_API_KEY` | console.groq.com → API Keys |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary dashboard → Account details |
| `CLOUDINARY_API_KEY` | Cloudinary dashboard → Account details |
| `CLOUDINARY_API_SECRET` | Cloudinary dashboard → Account details |

**Note:** No `MODEL_ID_*` variables are needed. Models are baked into the Docker image via Git LFS and are available on disk at container startup — no runtime download.

**Important:** `DATABASE_URL` must NOT be set in your local `.env`. Without it, `config.py` falls back to `sqlite:///lumera.db` — local dev uses SQLite, production uses Neon. They never share data or interfere with each other.

---

## Database — Neon PostgreSQL

**Provider:** [neon.tech](https://neon.tech) — free tier, no credit card, 0.5 GB storage.

**How it connects:** `config.py` reads `DATABASE_URL` from the environment:

```python
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///lumera.db')
```

On HF Spaces the Neon URL is present. Locally it falls back to SQLite.

**Tables created automatically** by SQLAlchemy's `db.create_all()` on every startup:
- `users` — email, username, bcrypt password hash (VARCHAR 512 — scrypt hashes are long)
- `analyses` — skin type, confidence, Cloudinary image URL, normalized face base64, skin concerns JSON
- `skin_concerns` — per-concern scores, severity, AI notes, annotated zone images (base64)
- `routines` + `routine_steps` — AI-generated morning/night routines with steps
- `product_recommendations` — product data

**One manual migration needed when switching from SQLite to Neon** — the `password_hash` column needs widening to 512 chars:

```bash
python -c "
from app import create_app
from models import db
app = create_app()
with app.app_context():
    db.session.execute(db.text('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(512)'))
    db.session.commit()
    print('Done')
"
```

**Neon connection string format:**
```
postgresql://username:password@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

The `?sslmode=require` is mandatory — Neon rejects unencrypted connections.

---

## Image Storage — Cloudinary

**Provider:** [cloudinary.com](https://cloudinary.com) — free tier: 25 GB storage, 25 GB bandwidth/month.

**Upload flow in `routes/analysis.py`:**

```
User uploads image (any size, any format)
        │
        ▼
Saved temporarily to backend/uploads/ on the container's ephemeral disk
        │
        ▼
_compress_image() — resize to max 1024px, save as JPEG quality 85
  → typically reduces a 5MB phone photo to ~300KB
  → consistent input size for ML pipeline
        │
        ▼
analyze_skin() — ML inference on compressed local file
        │
        ▼
cloudinary.uploader.upload() — compressed file → Cloudinary folder lumera/uploads/
        │
        ▼
Local temp file deleted
        │
        ▼
Cloudinary secure_url stored in analyses.image_path column
```

**Frontend rendering:** The `AuthImage` component checks if `image_path` starts with `https://` — if so, renders it directly as an `<img>` tag. No proxy needed, no JWT required for Cloudinary URLs.

---

## ML Models — Git LFS

The `.keras` model files are 25–35 MB each and cannot be committed to GitHub as regular files (100 MB file limit). They are tracked via **Git LFS** and pushed directly to the Hugging Face Spaces repository.

### How Git LFS tracking works

The `.gitattributes` file at the repo root declares LFS tracking:

```
*.keras filter=lfs diff=lfs merge=lfs -text
```

This means any `.keras` file anywhere in the repo is automatically stored in LFS rather than in the regular git object store. The actual binary data lives in the LFS server; the repo stores a small pointer file.

### How models get into the Docker image

When you push to HF Spaces, the HF git server resolves LFS pointers and provides the actual binary files to the Docker build context. The `COPY backend/ .` instruction in the Dockerfile then copies the entire `backend/` folder — including `ml_model/*.keras` — into the container image at build time. The models are frozen into the image layer and are immediately available on disk when the container starts.

This is fundamentally different from the previous Render approach (see [Why We Migrated Away From Render](#why-we-migrated-away-from-render)) where models were downloaded from Google Drive at runtime on every deploy.

### Model files and sizes

| Model | Size | Purpose |
|---|---|---|
| `best_model_v2.keras` | ~34 MB | Skin type classification (5 classes) |
| `concern_model_v3.keras` | ~35 MB | Concern detection v3 — full-face bbox-aware |
| `concern_model_v2.keras` | ~35 MB | Concern detection v2 — per-concern branches |
| `concern_model.keras` | ~25 MB | Concern detection v1 — legacy ensemble member |
| **Total** | **~135 MB** | |

### Pushing model updates

If you retrain a model and want to deploy the new version:

```bash
# Models are already LFS-tracked — just add and commit normally
git add backend/ml_model/concern_model_v3.keras
git commit -m "update concern model v3 with new training run"
git push huggingface main --force
```

HF will rebuild the Docker image with the new model baked in. The `--force` is needed because HF rewrites history differently from GitHub.

**Important:** Always push to `huggingface` remote for backend changes and to `origin` for GitHub sync. They are two separate remotes:

```bash
git remote -v
# origin        https://github.com/Samarthsalvade/lumera.git
# huggingface   https://Samarth1812:hf_token@huggingface.co/spaces/Samarth1812/lumera-backend
```

---

## Backend Deployment — Hugging Face Spaces

**Provider:** [huggingface.co/spaces](https://huggingface.co/spaces) — free tier Docker Spaces.

**Space URL:** `https://huggingface.co/spaces/Samarth1812/lumera-backend`
**API base URL:** `https://samarth1812-lumera-backend.hf.space`

### How HF Spaces Docker works

HF Spaces accepts a `Dockerfile` at the root of the pushed repository and builds it on their infrastructure. The resulting container runs on HF's servers. Key constraints of the free tier:

- **16 GB RAM** — this is the critical advantage over Render (512 MB). TensorFlow at ~400 MB plus the three concern models at ~36 MB fits easily.
- **Port 7860** — HF Spaces always proxies port 7860. The Dockerfile must `EXPOSE 7860` and Gunicorn must bind to `0.0.0.0:7860`.
- **Persistent container** — unlike Render's free tier which sleeps after 15 minutes of inactivity (triggering a cold start), HF Spaces containers stay running as long as UptimeRobot pings them. The Space does sleep after ~48h of total inactivity but this is prevented by UptimeRobot.
- **Public Space required** — the free tier requires the Space to be public. The API is accessible to anyone who knows the URL, but JWT authentication on all endpoints is the actual security layer.
- **Ephemeral filesystem** — like Render, the container filesystem resets on redeploy. This is why Cloudinary is used for image storage and Neon for the database — both are external services that survive container restarts.

### Root-level `Dockerfile`

The Dockerfile lives at the **repo root** (not inside `backend/`), because HF looks for it at root. It copies from `backend/` explicitly:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN mkdir -p ml_model uploads && chmod -R 777 ml_model uploads

ENV PORT=7860
EXPOSE 7860

CMD ["gunicorn", "--workers", "1", "--timeout", "300", "--bind", "0.0.0.0:7860", "app:create_app()"]
```

**Key notes:**
- `libgl1` is used instead of `libgl1-mesa-glx` — the latter does not exist in Debian trixie (the base image used by `python:3.12-slim` as of early 2026). Using the old package name causes the build to fail at the `apt-get install` step with "Package has no installation candidate."
- `git` and `git-lfs` are NOT installed at runtime — they are only needed during the build phase (when HF's build system resolves LFS pointers). Installing them in the runtime layer wastes image space.
- `COPY backend/ .` copies the entire backend folder into `/app`, including `ml_model/*.keras` which were resolved from LFS by HF's build system before Docker even runs.

### Root-level `README.md` for HF Spaces config

HF Spaces reads configuration from a YAML frontmatter block in `README.md` at the repo root. Without this, the Space shows a `CONFIG_ERROR`. The file must use exact `---` fences:

```yaml
---
title: Lumera Backend
emoji: 🌿
colorFrom: purple
colorTo: pink
sdk: docker
pinned: false
---
```

The `sdk: docker` line is what tells HF to use the Dockerfile rather than treating the repo as a Gradio or Streamlit app. Without `sdk: docker`, HF will attempt to run it as a Gradio app and fail immediately.

**Important:** The repo root also contains `PROJECT.md` (this file, the full project documentation). `README.md` at root is intentionally kept minimal — just the HF config frontmatter — because HF reads `README.md` for its Space card display.

### Gunicorn configuration

```
gunicorn --workers 1 --timeout 300 --bind 0.0.0.0:7860 app:create_app()
```

**Why `--workers 1`:** TensorFlow alone uses ~400 MB RAM. Even with 16 GB available, running multiple workers means multiple copies of TensorFlow and all three concern models in memory simultaneously. One worker is the correct choice given that inference is CPU-bound and requests are short.

**Why `--timeout 300`:** The first upload after a deploy triggers TensorFlow to JIT-compile the model graphs — this can take 30–60 seconds on cold CPU. 300 seconds gives enough headroom.

### Deploying backend changes

```bash
git add backend/<changed_files>
git commit -m "describe your change"
git push huggingface main --force
```

The `--force` is required because HF Spaces and GitHub have diverged histories (due to the initial force-push during migration). This only applies to the `huggingface` remote — never force-push to `origin`.

Watch the build at:
`https://huggingface.co/spaces/Samarth1812/lumera-backend` → **Logs** tab

Build times:
- First build or requirements change: 8–12 minutes (pip installing TensorFlow etc.)
- Code-only changes: 1–2 minutes (Docker layer cache skips the pip install layer)
- Model updates: 3–5 minutes (LFS resolution + COPY layer invalidation)

### Checking Space status via API

```bash
curl -s https://huggingface.co/api/spaces/Samarth1812/lumera-backend | python3 -m json.tool | grep "stage"
```

Possible stages:
- `CONFIG_ERROR` — README.md missing or has bad YAML frontmatter
- `NO_APP_FILE` — HF cannot find a runnable app at root (Dockerfile missing or wrong SDK)
- `BUILDING` — Docker build in progress
- `RUNNING` — container is up and accepting requests
- `FAILED` — build or runtime error — check Logs tab

---

## Why We Migrated Away From Render

The original backend was deployed on Render's free tier web service. After sustained use, two critical problems emerged that made Render unsuitable for this project:

### Problem 1 — 512 MB RAM limit caused OOM kills

TensorFlow 2.21 requires approximately 400 MB of RAM just to load the runtime and JIT-compile the model graphs. The three concern models add another ~36 MB. Serving a single inference request pushed the process to ~450–480 MB — dangerously close to the 512 MB free tier limit. Any additional memory pressure (a slightly larger image, a concurrent request, OS overhead) caused the process to be OOM-killed by the Linux kernel. The Gunicorn worker would die mid-request, the user's upload would hang until the 300-second timeout, and the app would appear frozen.

### Problem 2 — Models re-downloaded from Google Drive on every deploy

Because Render's filesystem is ephemeral and resets on every deploy, the `.keras` model files (~130 MB total) had to be downloaded from Google Drive at container startup via `download_models.py`. This download ran in a background thread so the server could start immediately, but:

- The download added 3–4 minutes to every deploy before the ML pipeline was ready
- During this window, uploads fell back to a feature-based analysis (skin brightness, texture variance) rather than CNN inference
- Google Drive occasionally throttled large file downloads, causing the models to download as 0-byte files and making the fallback permanent until the next restart
- The `MODEL_ID_*` environment variables for each model's Google Drive file ID had to be maintained in the Render dashboard

### The solution — Hugging Face Spaces with Docker

Hugging Face Spaces Docker tier resolves both problems:

| Property | Render (old) | HF Spaces (new) |
|---|---|---|
| RAM | 512 MB | **16 GB** |
| Model loading | Downloaded from Google Drive at runtime | **Baked into Docker image via Git LFS** |
| Cold start after idle | 30–60 seconds | ~5 seconds (container stays warm with UptimeRobot) |
| OOM kills | Frequent during inference | **Never — TF uses <3% of available RAM** |
| Model download time | 3–4 minutes per deploy | **Zero — models are in the image** |
| Inference timeout | Common on large images | **Eliminated** |
| Cost | Free (with limitations) | Free |

The migration required:
1. Adding a root-level `Dockerfile` that copies from `backend/` (since the full repo is pushed, not just the backend subfolder)
2. Adding a root-level `README.md` with HF Spaces YAML frontmatter (`sdk: docker`)
3. Removing the `download_models()` call from `app.py`'s background thread (models are already on disk)
4. Updating `app.py` CORS origins to include `https://samarth1812-lumera-backend.hf.space`
5. Updating `frontend/.env.production` to point to the new HF URL
6. Removing `backend/services/blaze_face_short_range.tflite` from git history (HF rejected binary files not tracked via LFS)
7. Purging the `.tflite` file from all git history using `git filter-branch` (the file existed in old commits even after removal)
8. Replacing `libgl1-mesa-glx` with `libgl1` in the Dockerfile (the former package does not exist in Debian trixie)

### Migration issues encountered and resolved

**`libgl1-mesa-glx` not found:** The `python:3.12-slim` base image uses Debian trixie as of early 2026. The `libgl1-mesa-glx` package was replaced by `libgl1` in trixie. The Docker build failed at the `apt-get install` step with "Package has no installation candidate." Fixed by replacing `libgl1-mesa-glx` with `libgl1`.

**`.tflite` binary file rejection:** HF Spaces rejects binary files that are not tracked via LFS. The `blaze_face_short_range.tflite` file was committed as a regular binary in an old commit. Even after `git rm --cached` and a new commit, the file still existed in the git history and HF's pre-receive hook rejected the push. Fixed by running `git filter-branch` to rewrite all history and remove the file from every commit, followed by `git reflog expire` and `git gc --prune=now --aggressive`.

**README YAML not parsed:** The `cat > README.md << 'EOF' ... EOF` heredoc command was accidentally written into the file as literal text (the shell command became the file contents). HF's YAML parser could not find the `---` fences and showed `CONFIG_ERROR`. Fixed by using `printf` instead: `printf -- '---\ntitle: ...\n---\n' > README.md`.

**Full repo pushed instead of just backend:** The first attempts to use `git subtree split --prefix backend` to push only the backend folder as root failed due to the repo being in a `Luméra/` directory (Unicode in path). The workaround was to keep the full repo on HF but place the Dockerfile and README at the repo root, with the Dockerfile using `COPY backend/requirements.txt .` and `COPY backend/ .` to copy from the backend subfolder.

**HF auth requires token, not password:** `git push huggingface main` failed with "Invalid username or password." HF Spaces git remotes require a personal access token with Write scope, not your HF account password. Fixed by updating the remote URL to include the token: `https://Samarth1812:hf_token@huggingface.co/spaces/Samarth1812/lumera-backend`.

**`NO_APP_FILE` after config error resolved:** After fixing the README YAML, the stage changed from `CONFIG_ERROR` to `NO_APP_FILE`. HF was looking for an `app.py` or `Dockerfile` at the repo root but found them inside `backend/`. Fixed by adding a root-level Dockerfile.

---

## Frontend Deployment — Vercel

**Provider:** [vercel.com](https://vercel.com) — free tier, unlimited deployments.

**Vercel project settings:**
- Root Directory: `frontend`
- Framework Preset: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

**Environment variable in Vercel dashboard:**
```
VITE_API_URL = https://samarth1812-lumera-backend.hf.space/api
```

This must be set in the Vercel dashboard (Settings → Environment Variables) in addition to being in `frontend/.env.production`. Vite bakes the API URL at build time — if the dashboard variable differs from the file, the dashboard value wins.

**`frontend/vercel.json`** — required for React Router:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Without this, refreshing `/dashboard` returns a Vercel 404 because Vercel tries to find a static `dashboard.html` file.

**CORS configuration in `app.py`:**

```python
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:5174",
            "https://lumera-wheat.vercel.app",
            "https://samarth1812-lumera-backend.hf.space",
        ],
    }
})
```

---

## Making Changes and Redeploying

### Backend changes (Flask, ML, routes)

```bash
git add backend/<changed_files>
git commit -m "describe your change"
git push huggingface main --force   # deploys to HF Spaces
git push origin main                # syncs to GitHub (may need --force once)
```

### Frontend changes (React, TypeScript)

```bash
git add frontend/<changed_files>
git commit -m "describe your change"
git push origin main                # triggers Vercel auto-deploy
```

### Both changed simultaneously

```bash
git add .
git commit -m "describe your change"
git push huggingface main --force
git push origin main
```

| What you changed | Deploys to | Time |
|---|---|---|
| Any `backend/` file | HF Spaces | 1–12 min depending on whether pip cache hits |
| Any `frontend/` file | Vercel | ~1 min |
| ML model `.keras` file | HF Spaces | 3–5 min (LFS transfer) |

**Exception — environment variables / secrets:**
New secrets must be added manually in the HF Spaces dashboard or Vercel dashboard. Pushing to git does not update secrets.

---

## Keep HF Space Awake — UptimeRobot

HF Spaces free tier containers sleep after ~48 hours of inactivity. The first request after sleep triggers a cold start (~5–10 seconds). Set up a free external ping to prevent this:

1. Go to [uptimerobot.com](https://uptimerobot.com) → sign up free
2. Click **Add New Monitor**
3. Monitor Type: **HTTP(s)**
4. Friendly Name: `Lumera Backend`
5. URL: `https://samarth1812-lumera-backend.hf.space/api/health`
6. Monitoring Interval: **5 minutes**
7. Click **Create Monitor**

The health endpoint returns `{"status": "ok", "message": "Backend is running"}` and is extremely lightweight — no database query, no ML inference. This keeps the server permanently warm at zero cost.

---

## ML Models Deep Dive

Luméra uses two independent CNN pipelines: one for skin type classification and one for concern detection.

### Skin Type Classifier

Takes a 224×224 pixel tight crop of the detected face and outputs one of five classes: Combination, Dry, Normal, Oily, Sensitive. Tries `best_model_v2.keras` first, falls back to `best_model.keras`.

#### v1 — `best_model.keras` — 85.09% val accuracy

**Architecture:** MobileNetV2 (ImageNet, include_top=False) → GAP → BatchNorm → Dense(256, ReLU) → Dropout(0.4) → Dense(128, ReLU) → Dropout(0.3) → Dense(5, softmax)

**Preprocessing note:** MobileNetV2 expects `[-1, +1]` input. The v1 model has `preprocess_input` rescaling baked in as `Multiply`, `TrueDivide`, `Subtract` layers. Feed raw `[0,1]` floats — never call `preprocess_input()` manually on v1 inputs or predictions will be garbage.

| Property | Value |
|---|---|
| Input | 224 × 224 × 3 |
| Output | 5-class softmax |
| Val accuracy | **85.09%** |
| Training | Phase 1: 15 epochs frozen (LR=1e-3) · Phase 2: 10 epochs fine-tune top 30 (LR=1e-4) |
| Class weights | Inverse-frequency, capped at 10× |

#### v2 — `best_model_v2.keras` — improved architecture

Addresses overconfident predictions and poor separation of similar skin types.

**Problem 1 — Overconfident predictions.** v1 predicted "Normal: 97%" for ambiguous faces. Cross-entropy with hard one-hot targets allows the model to reduce loss without bound.

**Fix — Label smoothing (ε=0.10).** Trains on soft targets `[0.02, 0.02, 0.92, 0.02, 0.02]`. Applied only to training labels — validation uses hard one-hot for honest metrics.

**Problem 2 — Missing texture information.** MobileNetV2's final feature map is 7×7 — too coarse for pore texture or subtle shine patterns.

**Fix — Multi-scale feature fusion:**
- Fine: `block_6_expand_relu` → 28×28×192 — 8px receptive field, captures pore/texture detail
- Coarse: final MobileNetV2 block → 7×7×1280 with Squeeze-and-Excitation recalibration

**Squeeze-and-Excitation** learns per-channel importance weights to suppress illumination-detector channels that fire on bright pixels regardless of skin type.

| Property | Value |
|---|---|
| Fine branch | `block_6_expand_relu` → GAP → BN → Dense(128, ReLU) → Drop(0.25) |
| Coarse branch | Final block → GAP → SE(64) → BN → Dense(256, ReLU) → Drop(0.30) |
| Fusion | Concat → Dense(512, L2) → BN → Drop(0.40) → Dense(256, L2) → BN → Drop(0.35) → Dense(128) → BN → Drop(0.25) → Dense(5, softmax) |
| Label smoothing | ε = 0.10 (training only) |
| Phase 3 | 8 epochs, top 60 layers, cosine LR 5e-5→1e-6 |
| Class weights | Inverse-frequency, capped at 10× |

**Training datasets:**

| Dataset | Source | Classes | Images |
|---|---|---|---|
| Oily/Dry/Normal | Kaggle: shakyadissanayake | normal, oily, dry | ~3,000 |
| Normal/Dry/Oily | Kaggle: ritikasinghkatoch | normal, oily, dry | ~400 |
| Facial Skin Analysis | Kaggle: killa92 | combination, dry, normal, oily | ~2,000 |
| Original project data | Manually collected | All 5 | ~3,312 |
| **Total** | | | **~8,588** |

---

### Concern Detection — Three Versions, One Ensemble

Three model versions run together as a weighted ensemble on every inference:

```
concern_model_v3.keras  →  weight 1.0  (full-face, bbox-aware training)
concern_model_v2.keras  →  weight 0.8  (per-concern branches, F1 monitoring)
concern_model.keras     →  weight 0.5  (legacy — lower weight, training mismatch)

Weighted average → per-class calibration → final concern scores
```

#### v1 — `concern_model.keras` — 95.69% val accuracy

Uses sigmoid (not softmax) — a face can have multiple concurrent concerns.

**Architecture:** MobileNetV2 → GAP → BN → Dense(256, ReLU) → Drop(0.4) → Dense(128, ReLU) → Drop(0.3) → Dense(6, sigmoid)

**Key limitation:** Trained on tight zone crops (dark circles filling the entire 224×224 frame), inferred on full faces. Severe train/test distribution mismatch.

| Classes | acne, blackheads, dark_circles, dark_spots, redness, texture |
|---|---|
| Calibration | Per-class baseline: texture=0.90, scale=0.10 |
| Ensemble weight | **0.5** |

#### v2 — `concern_model_v2.keras`

**Per-concern branches:** Each concern gets its own `Dense(32) → Drop(0.15) → Dense(1, sigmoid)` head. No cross-concern weight entanglement.

**F1 monitoring:** Uses macro binary F1 (not accuracy) — prevents high accuracy from predicting all-zeros.

| Ensemble weight | **0.8** |
|---|---|
| Label smoothing | ε = 0.05 |
| Monitored metric | val_f1_score |

#### v3 — `concern_model_v3.keras`

Directly solves the train/test distribution mismatch by training on full-face 224×224 images (same as inference).

**Bbox-aware soft labels:** Each training image gets a soft float 0.40–0.95 based on how well the annotated concern bbox overlaps with the expected anatomical zone:

```
bbox IoU with expected zone:
  > 0.50  →  label = 0.95  (excellent localisation)
  > 0.15  →  label = 0.75  (good localisation)
  > 0.00  →  label = 0.55  (concern present, unusual position)
  = 0.00  →  label = 0.40  (no overlap — train weakly)
Non-Roboflow images (no bboxes):
  →  label = 0.85  (concern present, no spatial info)
```

**Expected anatomical zones:**

| Concern | Zones |
|---|---|
| acne | left_cheek, right_cheek, forehead, chin |
| blackheads | nose, chin |
| dark_circles | under_left_eye, under_right_eye |
| dark_spots | face_centre (can appear anywhere) |
| redness | face_centre (global signal) |
| texture | left_cheek, right_cheek, forehead |

**Training datasets for v3:**

| Dataset | Source | Format | Concerns |
|---|---|---|---|
| ds4/Skin_Conditions/ | Kaggle | Folder-named | acne, redness (Rosacea) |
| ds5/Skin v2/ | Kaggle | Folder-named | acne, blackheads, dark_spots, texture |
| ds7/ | Kaggle | Folder-named | dark_circles |
| ds_rf1/ | Roboflow | yolov8-obb polygon | acne: 1,195 · dark_circles: 991 · texture: 1,421 |
| ds_rf2/ | Roboflow | Mixed standard+polygon | dark_circles: 1,114 |

**Staged class counts (capped at 2,000):**

| Class | Images |
|---|---|
| acne | 2,000 |
| blackheads | 1,962 |
| dark_circles | 2,000 |
| dark_spots | 2,000 |
| redness | 399 ⚠ LOW |
| texture | 2,000 |
| **Total** | **10,361** |

| Ensemble weight | **1.0** |
|---|---|
| Load with | `compile=False` — custom `BinaryF1` metric not registered with Keras |

---

## Face Detection Pipeline

```
Input image (any resolution, any format)
        │
        ▼ _compress_image()
Resized to max 1024px JPEG — consistent input, prevents timeouts
        │
        ▼
OpenCV Haar Cascade (primary detector)
  ├─ 6 parameter combinations (scaleFactor, minNeighbors, minSize)
  ├─ Runs on both original grayscale AND histogram-equalised version
  ├─ Scores candidates:
  │     score = (face_area / total_area) × 2.5
  │           + eye_bonus (0.35 for 2 eyes, 0.12 for 1, 0.0 for none)
  │           − (horizontal_distance_from_centre / half_width) × 0.5
  └─ Selects highest-scoring candidate
        │
        ├──► DISPLAY CROP (stored in DB as base64)
        │    Padding: 50% L/R, 70% top, 45% bottom
        │    Square-padded with RGB(245,245,245) grey
        │    Resized to 300×300 Lanczos
        │    Stored in analyses.normalized_image_b64
        │
        └──► ANALYSIS CROP (ML inference only, never stored)
             Tight bbox, no padding
             Resized to 224×224 Lanczos
             RGB uint8 numpy array
             → skin type CNN + concern ensemble + CV signals

If Haar fails → MediaPipe BlazeFace (disabled on HF Spaces — protobuf conflict with TF 2.21)
If both fail  → face_found=False, user sees error message
```

**Why two crops?** Zone coordinates in `skin_concern_detector.py` are calibrated to the tight 224×224 analysis crop. Using the padded display crop would cause zone coordinates to point to wrong face regions (e.g. under-eye zone pointing to the forehead).

**Face detection confidence:**
```python
conf = min(0.55 + eyes × 0.20 + (face_area / total_area) × 5.0, 0.99)
```

---

## Concern Detection Architecture

The `SkinConcernDetector` class implements a 4-layer hybrid system.

### Layer 1 — Anatomical Zones

12 named zones as `(y_start, y_end, x_start, x_end)` fractions of the 224×224 analysis crop:

```python
ZONES = {
    'forehead':        (0.04, 0.28, 0.22, 0.78),
    'left_cheek':      (0.38, 0.72, 0.04, 0.38),
    'right_cheek':     (0.38, 0.72, 0.62, 0.96),
    'nose':            (0.32, 0.65, 0.36, 0.64),
    'chin':            (0.72, 0.92, 0.28, 0.72),
    'left_eye':        (0.18, 0.36, 0.10, 0.42),
    'right_eye':       (0.18, 0.36, 0.58, 0.90),
    'under_left_eye':  (0.32, 0.44, 0.10, 0.42),
    'under_right_eye': (0.32, 0.44, 0.58, 0.90),
    'lip':             (0.65, 0.82, 0.30, 0.70),
    't_zone':          (0.04, 0.72, 0.30, 0.70),
    'face_centre':     (0.15, 0.85, 0.15, 0.85),
}
```

Skin tone factor computed from LAB L-channel mean — adjusts thresholds to prevent false positives on darker skin tones.

### Layer 2 — Ensemble ML + CV Signals

**ML ensemble:** Weighted average of all loaded models, then per-class calibration:
```python
calibrated = max(0.0, (raw_prob - baseline) / scale)
```

**CV-only signals (always run regardless of ML models):**

`eye_bags` — brightness delta between under-eye and eye socket in LAB L-channel. Gate lowered to 3.0 delta units (was 8.0). Three-component score: brightness delta + row variance + row-to-row std.

`lip_hyperpigmentation` — L-channel comparison of lip vs face_centre, plus purple/blue HSV hue ratio. Scaled by skin tone factor.

### Layer 3 — Cross-Concern Calibration

- `acne > 0.35` → add 0.06 to redness (inflamed acne involves redness)
- CV-only signals use display gate 0.08; ML signals use 0.15
- All scores clamped to [0.0, 1.0]

### Layer 4 — Zone Annotation Images

Per-concern 224×224 annotated images with semi-transparent fills (22% opacity), coloured borders (2px), white inner highlight (25%), severity-coloured label pills. Upscaled to 300×300 and stored as base64 in `skin_concerns.annotated_image_b64`.

### Severity Thresholds

| Concern | Mild | Moderate | Severe |
|---|---|---|---|
| acne | < 0.25 | 0.25–0.55 | > 0.55 |
| blackheads | < 0.25 | 0.25–0.55 | > 0.55 |
| dark_circles | < 0.25 | 0.25–0.55 | > 0.55 |
| eye_bags | < 0.22 | 0.22–0.50 | > 0.50 |
| redness | < 0.25 | 0.25–0.55 | > 0.55 |
| texture | < 0.30 | 0.30–0.65 | > 0.65 |
| hyperpigmentation | < 0.25 | 0.25–0.55 | > 0.55 |
| lip_hyperpigmentation | < 0.20 | 0.20–0.45 | > 0.45 |

---

## API Reference

All endpoints except `/api/auth/register` and `/api/auth/login` require `Authorization: Bearer <token>`.

### Auth — `/api/auth`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/register` | No | Register new user, returns JWT |
| POST | `/login` | No | Login, returns JWT |
| POST | `/logout` | Yes | Registers logout on backend, clears server-side state |
| GET | `/me` | Yes | Returns current user object |

### Analysis — `/api/analysis`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/upload` | Yes | Upload image → compress → ML → Cloudinary → save results |
| GET | `/history` | Yes | All analyses for user (excludes normalized_image_b64) |
| GET | `/result/:id` | Yes | Full analysis with all concern details and annotated images |

**POST `/upload`** accepts `multipart/form-data`, field name `image`. Max 16MB before compression. Formats: PNG, JPG, JPEG, WEBP. Returns HTTP 201 on success, HTTP 200 with `success: false` if no face detected.

### Products — `/api/products`

**POST `/recommend`** — Groq generates product names, backend enriches each with Open Beauty Facts image URL.

```json
Request: { "skin_type": "Normal", "concerns": [{"concern_type": "dark_circles", "severity": "moderate"}], "count": 5 }
```

### Routines — `/api/routines`

**POST `/generate`** — AI routine based on scan. **GET `/`** — list all. **DELETE `/:id`** — delete. **POST `/:id/activate`** — set as active (deactivates others of same type).

### Chatbot — `/api/chatbot`

**POST `/chat`** — Groq with last 5 scan context injected into system prompt. Frontend sends full conversation history with each request — backend is stateless.

```json
Request: { "message": "What routine should I follow?", "history": [...] }
Response: { "reply": "For your skin type..." }
```

### Report — `/api/report`

**GET `/summary`** — 7-day JSON summary with total scans, average confidence, dominant skin type, recurring concerns.

**GET `/weekly`** — PDF file streamed from BytesIO buffer (no temp files written to disk).

---

## Database Schema

### users
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| email | VARCHAR(120) | Unique |
| username | VARCHAR(80) | Unique |
| password_hash | VARCHAR(512) | scrypt hash — 512 chars needed (was 128, caused truncation error) |
| created_at | DATETIME | |

### analyses
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | → users.id |
| image_path | VARCHAR(500) | Cloudinary HTTPS URL (500 chars for long URLs) |
| skin_type | VARCHAR(50) | Combination / Dry / Normal / Oily / Sensitive |
| confidence | FLOAT | 0–100 percentage |
| recommendations | TEXT | JSON array of 3 strings from Groq |
| normalized_image_b64 | TEXT | Base64 PNG of 300×300 padded display crop |
| face_detection_confidence | FLOAT | 0–100 from Haar scoring formula |
| skin_concerns | TEXT | JSON dict: `{"acne": 0.45, "dark_circles": 0.12, ...}` |
| created_at | DATETIME | |

### skin_concerns
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| analysis_id | INTEGER FK | → analyses.id |
| concern_type | VARCHAR(50) | |
| confidence | FLOAT | 0.0–1.0 calibrated ensemble score |
| severity | VARCHAR(20) | mild / moderate / severe |
| notes | TEXT | AI-generated per-concern recommendation |
| annotated_image_b64 | TEXT | Base64 PNG of face with coloured zone boxes |
| created_at | DATETIME | |

### routines
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | → users.id |
| routine_type | VARCHAR(20) | morning / night |
| name | VARCHAR(200) | AI-generated |
| description | TEXT | AI-generated |
| is_active | BOOLEAN | At most one morning + one night active per user |
| created_at / updated_at | DATETIME | |

### routine_steps
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| routine_id | INTEGER FK | → routines.id |
| order | INTEGER | 1-indexed |
| product_type | VARCHAR(100) | e.g. Gentle Cleanser, Vitamin C Serum |
| instruction | TEXT | |
| duration_seconds | INTEGER | Optional |
| key_ingredient | VARCHAR(100) | e.g. salicylic acid, retinol |
| created_at | DATETIME | |

---

## Frontend Pages

### Home (`/`) — Landing page for unauthenticated users
Feature cards explaining Upload → Analyse → Recommend workflow. Stats strip (95% accuracy, 9 concerns, AI routines). `PageShell` background: #f5f3ff + dot-grid SVG + two blurred purple accent circles.

### Login / Signup
JWT auth forms. On success, stores `access_token` and `user` JSON in `localStorage`. `ProtectedRoute` checks `localStorage.getItem('token')` synchronously — no async delay, no login-page flash for logged-in users.

### Dashboard (`/dashboard`)
Welcome banner with username + live stats. Scan history grid. `AuthImage` component checks if `image_path` starts with `https://` — if yes, renders directly from Cloudinary. If legacy local path, fetches via Axios with JWT.

### Upload (`/upload`)
Two-column layout: upload/camera form + photo guide. Custom inline SVG illustration showing full-face ✓ vs zoomed ✗. Camera mode with front/rear toggle. Oval guide with `aspectRatio: 3/4.2` to encourage stepping back for full face. Amber warning banner explaining why full-face photos are required.

### Results (`/results/:id`)
Three tabs: Concerns (annotated zone images + severity badges + AI notes), Products (horizontal slider with OBF real images, brand initial tile fallback), Routine (AI generation, saves to DB).

### Progress (`/progress`)
Interactive calendar with skin type colour coding per day. Fixed-height day panel with internal scroll — doesn't expand the page regardless of scan count. Skin type distribution bars. Full scan history table.

### Chatbot (`/chatbot`)
Conversation interface. Initial greeting with 4 suggested quick questions. Gradient purple user bubbles, grey assistant bubbles. Typing indicator (3 bouncing dots) while waiting for Groq response.

### Routines (`/routines`)
Accordion cards grouped by Morning and Night. Expanding shows steps with step number circles, product type, instruction, timing, key ingredient. Set Active and Delete per routine.

### Weekly Report (`/report`)
Interactive bar chart (past 7 days, bars coloured by skin type). Click bar → scan detail modal. Recurring concerns section with annotated zone thumbnails. PDF download triggers blob fetch from `/api/report/weekly`.

---

## Features Deep Dive

### Image Compression Pipeline

All uploaded images go through `_compress_image()` before ML processing:

```python
def _compress_image(filepath, max_dimension=1024, quality=85):
    with PILImage.open(filepath) as img:
        img = img.convert('RGB')
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), PILImage.LANCZOS)
        new_filepath = os.path.splitext(filepath)[0] + '_compressed.jpg'
        img.save(new_filepath, 'JPEG', quality=quality, optimize=True)
        return new_filepath
```

A 10MB phone photo becomes ~300KB. ML accuracy is unchanged — face detection and CNN both operate on 224×224 crops regardless of input resolution.

### Background Model Loading

Models load in a background thread so the server starts immediately:

```python
thread = threading.Thread(target=_load_models_background, daemon=True)
thread.start()
print("⏳ ML models loading in background...")
```

On HF Spaces, the models are already on disk (baked into the Docker image via Git LFS). The background thread only needs to run TensorFlow's JIT compilation, which takes ~2–3 minutes. During this window uploads use feature-based analysis as fallback.

Note: `download_models.py` still exists in the repo but `_load_models_background()` in `app.py` no longer calls it. The download logic was removed when migrating to HF Spaces. The file is kept for reference in case a future deployment target requires runtime model download.

### Two-Phase Groq Recommendations

1. Initial recommendations generated from skin type + confidence only
2. After concern detection, regenerated with full context (skin type + all concerns + severities)
3. Second set overwrites first in the database

Ensures concern-specific advice: "use eye cream with caffeine" instead of generic skin type advice when dark circles are detected. Falls back to static dict if Groq is unavailable.

### Dynamic Products with Real Images

```python
resp = requests.get('https://world.openbeautyfacts.org/cgi/search.pl', params={
    'search_terms': f"{brand} {product_name}",
    'json': 1, 'page_size': 5,
    'fields': 'product_name,brands,image_front_url,image_url',
}, timeout=4)
```

4-second timeout prevents blocking the UI. OBF has strong coverage of CeraVe, The Ordinary, La Roche-Posay, Neutrogena, Kiehl's. Falls back to branded initial tile for unrecognised brands.

---

## Training the Models

### Skin Type Model v2

```bash
cd lumera/backend
source venv/bin/activate

kaggle datasets download -d shakyadissanayake/oily-dry-and-normal-skin-types-dataset -p dataset_downloads/ds1 --unzip
kaggle datasets download -d ritikasinghkatoch/normaldryoily-skin-type -p dataset_downloads/ds2 --unzip
kaggle datasets download -d killa92/facial-skin-analysis-and-type-classification -p dataset_downloads/ds3 --unzip

python ml_model/merge_datasets.py
python ml_model/train_model.py   # saves to ml_model/best_model_v2.keras
```

### Concern Model v3

```bash
# Set ROBOFLOW_API_KEY in backend/.env first
python download_concern_datasets.py

python ml_model/train_concern_model_v3.py          # dry run
python ml_model/train_concern_model_v3.py --train  # actually train
```

**Critical implementation notes:**
- Label path: `Path(str(img_path).replace('/images/', '/labels/')).with_suffix('.txt')` — NOT `Path.stem` (truncates multi-dot Roboflow filenames like `125_jpg.rf.abc123.jpg`)
- ds_rf1 uses YOLOv8-OBB polygon format — parser handles both standard (4 coords) and polygon (8+ even coords)
- Phase 3 must use `make_callbacks(reduce_lr=False)` — `ReduceLROnPlateau` incompatible with `CosineDecay`
- `compile=False` at inference — custom `BinaryF1` metric not registered with Keras serialisation

---

## Complete Bug Fix History

| # | Issue | Root Cause | Fix |
|---|---|---|---|
| 1 | Session expired on every upload | Axios interceptor deleted token on any 422 | Only clear token on genuine JWT 422s |
| 2 | Login page flashes for logged-in users | ProtectedRoute used async 100ms timeout | Synchronous `localStorage.getItem` on render |
| 3 | All images classified as Oily | Feature extraction ran on full image | Tight face bbox extraction before all features |
| 4 | 422 on all authenticated API calls | JWT identity stored as integer | `str(user.id)` on issue, `int(get_jwt_identity())` on read |
| 5 | Full-body faces not detected | BlazeFace misses non-close-up faces | OpenCV Haar as primary, MediaPipe as fallback |
| 6 | Wrong face selected | Largest bbox was often background | Multi-criterion scoring: area + eyes + centrality |
| 7 | Dashboard images return 401 | `<img>` cannot send Authorization header | `AuthImage` fetches via Axios blob |
| 8 | Model always predicts Sensitive | Hard-coded class order mismatch | Load from `class_indices.json` |
| 9–10 | Garbage predictions | Double `preprocess_input` application | Feed raw [0,1] floats — model has scaling baked in |
| 11 | `TrueDivide` unknown layer | Old Sequential model + TF 2.21/Keras 3 | Retrained with Functional API |
| 16–17 | Texture fires 99% on every face | Softmax + 9× more texture training data | Sigmoid + binary_crossentropy + per-class calibration |
| 18–22 | All CV concerns firing simultaneously | Thresholds not calibrated for real faces | Empirical calibration on real LAB measurements |
| 42 | Eye bags never detected | Gate 8.0 LAB-L too strict | Lowered to 3.0, added row variance + row-to-row std |
| 43–45 | RF datasets return 0 samples | `Path.stem` truncation, polygon format | String replacement + polygon parser |
| 46–48 | v3 training/loading errors | Keras 3.x API changes | `add_weight(name=...)`, `compile=False` |
| 49 | Texture detected instead of localised concerns | Train on crops, infer on full faces | v3 full-face training + bbox-aware soft labels |
| 50 | Wrong detections from zoomed photos | No upload guidance | SVG photo guide + amber warning banner |
| 51 | `ModuleNotFoundError: cloudinary` on Render | Build cache served old requirements | Added `# requirements vN` comment to force fresh install |
| 52 | Registration fails: `value too long for VARCHAR(128)` | scrypt produces longer hashes than bcrypt | Extended to VARCHAR(512) + ALTER TABLE on Neon |
| 53 | Upload times out for large images | TensorFlow load + large file > 300s | Image compression to max 1024px JPEG before processing |
| 54 | Server deadlock on stuck requests | Flask dev server is single-threaded | Switched to Gunicorn `--workers 1 --timeout 300` |
| 55 | Models not found on Render | Ephemeral filesystem resets between deploys | Download from Google Drive in background thread at startup |
| 56 | Models download as 0.0 MB | Google Drive virus scan page returned instead of file | Use `drive.usercontent.google.com?confirm=t` URL |
| 57 | Boot timeout waiting for model download | 130MB download blocked startup | Background thread — server live immediately, models load async |
| 58 | CORS blocking Vercel frontend | Only localhost:5173 whitelisted | Added `https://lumera-wheat.vercel.app` to CORS origins |
| 59 | 404 on page refresh in production | Vercel tries to find static file for each route | `vercel.json` rewrite: all paths → `index.html` |
| 60 | Original image not loading in Results | `AuthImage` always used `/api/uploads/` endpoint | Check if `image_path` starts with `https://`, render directly from Cloudinary |
| 61 | OOM kills on Render during inference | TF 400MB + models in 512MB RAM limit | Migrated to HF Spaces (16 GB RAM) |
| 62 | Inference timeouts on Render | 512MB RAM limit causing thrashing under load | Migrated to HF Spaces — TF uses <3% of available RAM |
| 63 | Models re-download 3–4 min every Render deploy | Render ephemeral filesystem + Google Drive download | Baked models into Docker image via Git LFS on HF Spaces |
| 64 | HF push rejected — binary file not in LFS | `blaze_face_short_range.tflite` committed as regular binary | `git filter-branch` to purge file from entire history |
| 65 | HF push rejected after filter-branch | File still in old commits scanned by HF pre-receive hook | `git reflog expire --expire=now --all` + `git gc --prune=now` |
| 66 | HF auth failed with password | HF git remotes require access token not password | Set remote URL with `hf_token` in URL |
| 67 | `CONFIG_ERROR` on HF Space | README.md missing `---` YAML fences (shell heredoc wrote command as file content) | Used `printf` to write clean YAML fences |
| 68 | `NO_APP_FILE` after config error resolved | Dockerfile inside `backend/` not visible at repo root | Added root-level Dockerfile with `COPY backend/ .` |
| 69 | Docker build fails — `libgl1-mesa-glx` not found | Package removed in Debian trixie (python:3.12-slim base) | Replaced with `libgl1` |
| 70 | Frontend still hitting Render after HF migration | `VITE_API_URL` not updated in Vercel dashboard | Updated both `.env.production` and Vercel dashboard env var |
| 71 | CORS blocking HF Space requests | HF URL not in CORS origins list in `app.py` | Added `https://samarth1812-lumera-backend.hf.space` to origins |

---

## Known Limitations

**HF Spaces free tier sleeping.** Without UptimeRobot, the Space sleeps after ~48 hours of inactivity. First request after sleep takes ~10 seconds. With UptimeRobot pinging every 5 minutes, this never happens in practice.

**Single Gunicorn worker.** Even with 16 GB RAM, one worker means two simultaneous uploads queue — one waits for the other. This is acceptable at 10–50 scans/day. For higher traffic, increase `--workers` and adjust accordingly.

**Ephemeral container filesystem.** Like Render, HF Spaces containers reset on redeploy. Uploaded images are stored in Cloudinary (not local disk) and the database is in Neon — both survive redeploys. The only thing lost on redeploy is any temp file in `/tmp` which is intentional.

**Sensitive skin — 80 training images.** vs ~3,000 for Normal. Model frequently misclassifies as Normal or Dry. 10× class weight partially compensates.

**Redness — 399 training images.** Lowest concern class. Only fires on severe redness. Mild redness usually missed. No CV-only fallback for redness.

**v3 soft labels mostly 0.85.** Roboflow polygon annotations tend to cover the full face — IoU with specific anatomical zones is low, most samples fall back to the 0.85 fixed label. Meaningful spatial differentiation requires tightly-annotated datasets.

**Open Beauty Facts coverage.** Strong for CeraVe, The Ordinary, La Roche-Posay, Neutrogena, Kiehl's. Limited for Indian and Asian brands — falls back to brand initial tile.

**Calibration demographics.** CV signal thresholds tuned on Indian male skin, medium tone, indoor lighting. Edge cases possible for very dark/light skin, heavy facial hair, unusual lighting conditions.

**MediaPipe disabled on HF Spaces.** `mediapipe==0.10.14` has a `protobuf<5` requirement that conflicts with TensorFlow 2.21's `protobuf>=6`. Haar cascade alone handles all face detection on production. This was also the case on Render.

---

## Roadmap

- [ ] Sensitive skin data — 400+ labelled images to reach parity
- [ ] Redness data — 1,000+ rosacea images
- [ ] eye_bags ML class — dedicated training images, 7th ML class in v4
- [ ] Amazon PA API — official product images instead of OBF
- [ ] Streaming chatbot — SSE for word-by-word Groq responses
- [ ] Scan journal — free-text notes per scan (diet, products, sleep, stress)
- [ ] Streak tracking — gamification with scan consistency badges
- [ ] Before/after comparison — side-by-side scan view
- [ ] Weekly email digest — Flask-Mail + scheduled job
- [ ] PWA — `manifest.json` + service worker for mobile install
- [ ] v3 tighter annotations — datasets with tight per-concern bboxes for meaningful soft label spread
- [ ] Upgrade HF Spaces — paid tier for persistent storage and guaranteed uptime SLA
- [ ] Confidence intervals — uncertainty range on predictions
- [ ] Multi-language support — especially for Indian skin tone annotations
- [ ] Skin type v3 — full-face + spatial annotation if localised datasets become available