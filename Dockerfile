# Python FastAPI AI Worker & Document Export Service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for build, postgres connections, and headless browser
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies list
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browser binaries and system dependencies
RUN playwright install --with-deps chromium

# Copy application source code
COPY . .

ENV PYTHONUNBUFFERED=1
ENV WORKER_PORT=8001
ENV ENVIRONMENT=production

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
