FROM python:3.12-slim

# System dependencies for OpenCV + TensorFlow
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code including ml_model/ with .keras files via Git LFS
COPY . .

# Hugging Face Spaces runs as a non-root user — fix permissions
RUN chmod -R 777 /app

# HF Spaces expects the app on port 7860
ENV PORT=7860

EXPOSE 7860

# Same gunicorn command as render.yaml — just different port
CMD gunicorn --workers 1 --timeout 300 --bind 0.0.0.0:7860 "app:create_app()"