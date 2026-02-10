# MY CAFE - Production Docker Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt && \
    pip install --no-cache-dir --break-system-packages gunicorn

# Copy application files
COPY app.py .
COPY db.py .
COPY qr_generator.py .
COPY setup_db.py .
COPY migrate.py .
COPY fix_database.py .

# Copy templates and static files
COPY templates/ ./templates/
COPY static/ ./static/

# Create necessary directories
RUN mkdir -p static/qr_codes && \
    mkdir -p static/icons

# Initialize database and generate QR codes
RUN python fix_database.py && \
    python setup_db.py && \
    python qr_generator.py

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Run with gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
