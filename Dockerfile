FROM python:3.12-slim

# Prevent .pyc files and enable unbuffered stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: PostgreSQL client, image libs, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libfreetype6-dev \
    libpng-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Non-root user for security
RUN addgroup --system joyvet && adduser --system --group joyvet \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R joyvet:joyvet /app

USER joyvet

EXPOSE 8000
