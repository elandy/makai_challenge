# Makai Challenge

Async document-processing job API built with FastAPI, PostgreSQL, RabbitMQ, and an async Python worker.

The API accepts document-processing jobs, stores them in Postgres, publishes job IDs to RabbitMQ, and a worker consumes those jobs to simulate a multi-step document-processing workflow. When a job completes or fails, the worker can send a webhook notification to the submitted `callback_url`.

## Stack

- FastAPI for the HTTP API
- PostgreSQL for job storage
- RabbitMQ for the job queue
- SQLAlchemy async with `asyncpg`
- `aio-pika` for RabbitMQ publishing/consuming
- `httpx` for webhook callbacks
- Docker Compose for local orchestration
- Pytest for tests

## Services

Docker Compose starts:

- `api`: FastAPI app on `http://localhost:8000`
- `worker`: RabbitMQ consumer that processes queued jobs
- `postgres`: PostgreSQL on `localhost:5432`
- `rabbitmq`: RabbitMQ on `localhost:5672`
- RabbitMQ Management UI on `http://localhost:15672`

RabbitMQ default credentials:

```text
username: guest
password: guest
```

## Launch Locally

From the repository root:

```powershell
docker compose up --build
```

Or run it in the background:

```powershell
docker compose up --build -d
```

Check running services:

```powershell
docker compose ps
```

View recent logs:

```powershell
docker compose logs --since=2m api
docker compose logs --since=2m worker
```

The worker does not auto-reload code changes. If you edit worker code, restart it:

```powershell
docker compose restart worker
```

The API runs with Uvicorn reload enabled in Docker Compose, so API code changes are usually picked up automatically.

## API Docs

Open Swagger UI:

```text
http://localhost:8000/docs
```

Useful endpoints:

- `POST /jobs`: create a new document-processing job
- `GET /jobs`: list jobs for the current stub user
- `GET /jobs/{job_id}`: get job status/result
- `POST /jobs/{job_id}/cancel`: cancel queued/running job
- `POST /jobs/{job_id}/retry`: retry failed/cancelled job

Authentication is currently stubbed. Every request uses the fake user:

```text
id: test-user
username: test
```

## Test With Swagger UI

1. Open `http://localhost:8000/docs`.
2. Open `POST /jobs`.
3. Click `Try it out`.
4. Use a payload like:

```json
{
  "document_url": "https://example.com/file.pdf",
  "extract_keywords": true,
  "generate_summary": true,
  "callback_url": null
}
```

5. Click `Execute`.
6. Copy the returned `job_id`.
7. Use `GET /jobs/{job_id}` to watch progress and final result.

The worker currently simulates processing. It does not actually download or parse the PDF yet. The simulated stages are:

- `DOCUMENT_DOWNLOAD`
- `TEXT_EXTRACTION`
- `KEYWORD_ANALYSIS`

The job should complete after roughly 7 seconds once the worker receives it.

## Test Webhook Notifications

1. Go to:

```text
https://webhook.site/
```

2. Copy your unique webhook URL.
3. Submit a job with that URL as `callback_url`.

Example payload for Swagger UI:

```json
{
  "document_url": "https://example.com/file.pdf",
  "extract_keywords": true,
  "generate_summary": true,
  "callback_url": "https://webhook.site/your-webhook-id"
}
```

When the worker completes the job, webhook.site should receive a POST like:

```json
{
  "user_id": "test-user",
  "event": "job.completed",
  "data": {
    "job_id": "generated-job-id",
    "result": {
      "summary": "Document processed successfully",
      "keywords": ["async", "document", "processing"]
    }
  }
}
```

If a job fails, the event is `job.failed`.

## Test With PowerShell

PowerShell has different quoting behavior than Bash. This is the easiest Windows-friendly request:

```powershell
$body = @{
  document_url = "https://example.com/file.pdf"
  extract_keywords = $true
  generate_summary = $true
  callback_url = "https://webhook.site/your-webhook-id"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://localhost:8000/jobs" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Equivalent `curl.exe` command for Windows:

```powershell
curl.exe -X POST "http://localhost:8000/jobs" `
  -H "Content-Type: application/json" `
  -d "{\"document_url\":\"https://example.com/file.pdf\",\"extract_keywords\":true,\"generate_summary\":true,\"callback_url\":\"https://webhook.site/your-webhook-id\"}"
```

Use `curl.exe`, not plain `curl`, if your PowerShell aliases `curl` to `Invoke-WebRequest`.

## Run Tests

The intended test command is:

```powershell
docker compose run --rm test
```

This uses the `jobs_test` database configured in `docker-compose.yml`.

You can also run a focused local test from the repository if your virtual environment is installed:

```powershell
.\.venv\bin\pytest tests\unit\test_webhook_notifier.py -q
```

Some API tests create jobs through `POST /jobs`, which publishes to RabbitMQ. For the full test suite, keep Docker services available.

## Database And Queue URLs

Inside Docker Compose, services use Docker hostnames:

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/jobs
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

For running code directly from Windows/PyCharm against Compose services, use localhost:

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jobs
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

For local tests:

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jobs_test
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

## Troubleshooting

If webhook.site does not receive a POST:

1. Confirm the worker is running:

```powershell
docker compose ps
```

2. Restart the worker after code changes:

```powershell
docker compose restart worker
```

3. Check recent worker logs:

```powershell
docker compose logs --since=2m worker
```

4. Confirm the job completed:

```powershell
docker compose exec -T postgres psql -U postgres -d jobs -c "select id, status, progress, error_message, completed_at from jobs order by created_at desc limit 5;"
```

If `jobs_test` does not exist, remember that Postgres init scripts only run when the Docker volume is first created. You can create it manually:

```powershell
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE jobs_test;"
```

## Current Limitations

- Document processing is simulated; no real PDF download or extraction is implemented yet.
- Authentication is stubbed.
- Webhook delivery has no retry/backoff behavior.
- There are no migrations; tables are created through SQLAlchemy metadata at API startup.
- The worker must be restarted manually after worker code changes.
