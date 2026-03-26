FROM python:3.12-slim

WORKDIR /app

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

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN mkdir -p ml_model uploads && chmod -R 777 ml_model uploads

ENV PORT=7860
EXPOSE 7860

CMD ["gunicorn", "--workers", "1", "--timeout", "300", "--bind", "0.0.0.0:7860", "app:create_app()"]