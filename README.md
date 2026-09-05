# MeetingOS AI Worker & Inference Service

An enterprise-grade, asynchronous AI processing service built with **Python 3.11**, **FastAPI**, **RabbitMQ (aio-pika)**, and **Google Gemini 2.0 / 1.5 Flash**.

This service is responsible for:
1. **Semantic Transcript Processing**: Cleaning, formatting, speaker diarization alignment, and token-aware chunking.
2. **Structured Meeting Intelligence**: Generating executive summaries, key decisions, and prioritized action items with direct transcript timestamp citations.
3. **Vector Embeddings**: Creating dense vector embeddings for meeting segments and storing them in Supabase `pgvector`.
4. **Document Generation**: Exporting high-fidelity executive PDF (via Playwright headless Chromium) and Microsoft Word `.docx` reports.
5. **Asynchronous Task Consumer**: Consuming message jobs from RabbitMQ queues for background processing.

---

## 🏗 Architecture & Folder Structure

```
ai-service/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # REST API route handlers
│   │       │   ├── extraction.py   # AI summary & action items
│   │       │   ├── export.py       # PDF and DOCX generators
│   │       │   └── health.py       # Liveness / Readiness probes
│   │       └── router.py       # API v1 aggregator
│   ├── core/
│   │   ├── config.py           # Pydantic BaseSettings environment loader
│   │   └── logger.py           # Structured logging
│   ├── models/
│   │   └── schemas.py          # Pydantic v2 validation & response models
│   ├── providers/
│   │   ├── base.py             # Abstract LLM provider interface
│   │   └── gemini.py           # Gemini 2.0 Flash / Pro integration
│   ├── services/
│   │   ├── chunker.py          # Semantic transcript chunking
│   │   ├── extractor.py        # Summary & action item extraction logic
│   │   ├── embeddings.py       # Vector embedding generation
│   │   └── exporter.py         # Playwright PDF & python-docx engine
│   ├── worker/
│   │   └── consumer.py         # aio-pika RabbitMQ background consumer
│   └── main.py                 # FastAPI application lifecycle & entrypoint
├── tests/                      # Pytest suite
├── Dockerfile                  # Production container image with Playwright
├── requirements.txt            # Python dependencies
└── README.md                   # This documentation
```

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- **Python 3.10+** (Python 3.11 recommended)
- **pip** and `venv`
- Running **RabbitMQ** instance (optional if running REST endpoints in standalone mode)

---

### Step 1: Create and Activate Virtual Environment

```bash
# Navigate to ai-service directory
cd ai-service

# Create virtual environment named 'venv'
python3 -m venv venv

# Activate on macOS / Linux:
source venv/bin/activate

# (Or on Windows PowerShell: .\venv\Scripts\Activate.ps1)
```

---

### Step 2: Install Python Dependencies

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install project requirements
pip install -r requirements.txt
```

---

### Step 3: Install Playwright Chromium (Required for PDF Export)

The PDF exporter uses headless Chromium for pixel-perfect document rendering:

```bash
playwright install chromium
```

---

### Step 4: Configure Environment Variables

Create or update your `.env` file in the project root or configure the following variables in your environment:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | `string` | *Required* | API Key from [Google AI Studio](https://aistudio.google.com/) |
| `RABBITMQ_URL` | `string` | `amqp://meetingos:meetingos_pass@localhost:5672` | AMQP broker connection string |
| `DATABASE_URL` | `string` | *Optional* | PostgreSQL connection string with `pgvector` |
| `WORKER_PORT` | `integer` | `8001` | Port for the FastAPI HTTP server |
| `AI_PROVIDER` | `string` | `gemini` | LLM Provider (`gemini`, `openai`, `anthropic`) |
| `DEFAULT_MODEL` | `string` | `gemini-2.0-flash` | Default Gemini model for extraction |
| `ENVIRONMENT` | `string` | `development` | Environment mode (`development`, `production`) |

---

### Step 5: Run the Development Server

#### Method A: Using `uvicorn` CLI (Recommended with Hot-Reload)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### Method B: Running directly via Python module
```bash
python -m app.main
```

---

## 🐳 Running with Docker

You can run the AI Service in isolation or alongside the full stack using Docker Compose:

### Run Standalone via Docker Compose:
```bash
# From the project root
docker compose up -d ai-service
```

### Build & Run Container Manually:
```bash
# Build the Docker image
docker build -t meetingos-ai-service:latest -f ai-service/Dockerfile .

# Run the container
docker run -p 8001:8001 \
  -e GEMINI_API_KEY="your-api-key" \
  -e RABBITMQ_URL="amqp://meetingos:meetingos_pass@host.docker.internal:5672" \
  meetingos-ai-service:latest
```

---

## 📡 API Endpoints & Verification

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | Service health check and version status |
| `/docs` | `GET` | Interactive Swagger / OpenAPI documentation |
| `/redoc` | `GET` | ReDoc API specifications |
| `/api/v1/extract/summary` | `POST` | Generates executive summary & decisions from transcript |
| `/api/v1/extract/action-items` | `POST` | Extracts structured action items with assignees & due dates |
| `/api/v1/export/pdf` | `POST` | Renders and streams formatted meeting summary PDF |
| `/api/v1/export/docx` | `POST` | Generates structured Microsoft Word document |

### Quick Health Verification:
```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "MeetingOS AI Worker Service",
  "version": "1.0.0"
}
```

---

## ⚡ RabbitMQ Asynchronous Worker Queues

In production, the service subscribes to RabbitMQ queues to process meeting transcripts asynchronously without blocking HTTP requests:

- **Queue Name**: `meeting.transcripts.process`
- **Exchange**: `meetingos.direct`
- **Routing Key**: `transcript.process`

### Sample Message Payload:
```json
{
  "jobId": "job_984f93a1-7c23-42e1",
  "meetingId": "meet_550e8400-e29b-41d4-a716-446655440000",
  "transcriptText": "[00:00:05] Aryan: Let's finalize the Q3 product roadmap...\n[00:00:15] Sarah: I will deliver the auth pipeline by Friday.",
  "options": {
    "generateSummary": true,
    "extractActionItems": true,
    "generateEmbeddings": true
  }
}
```

---

## 🛡️ Edge Cases & Reliability Design

1. **AMQP Connection Resilience**: `aio-pika` consumer uses exponential backoff reconnection logic so the worker survives RabbitMQ restarts.
2. **Context Window Protection**: Transcripts exceeding standard prompt limits are automatically segmented using the semantic chunker in `app/services/chunker.py` and processed hierarchically (Map-Reduce summary).
3. **Structured JSON Output Validation**: All Gemini LLM outputs use Pydantic `response_schema` enforcement to guarantee deterministic JSON output without hallucinated formats.
4. **Playwright Sandbox in Docker**: The Dockerfile includes all required system libraries (`libnss3`, `libatk`, `libcups2`, etc.) and runs Chromium with `--no-sandbox` to prevent container crashes.

---

## 🧪 Testing

```bash
# Run pytest test suite
pytest tests/ -v
```
