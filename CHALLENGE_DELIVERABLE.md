# Async Job Processing System Design

## Context

The product requirement is to process user-submitted jobs asynchronously. Jobs may take from a few seconds to several minutes, users submit them through an API, and users expect to query job status and receive a notification when a job completes or fails.

As an extra step beyond the design response, I also built a minimal working implementation of this architecture:

https://github.com/elandy/makai_challenge

The implementation is intentionally small, but it demonstrates the core flow: submit a job through an API, persist job state, enqueue work, process the job asynchronously, update progress, support cancellation/retry, and send a webhook notification on completion/failure.

## High-Level Architecture

I would use an asynchronous, queue-backed architecture:

```text
Client
  |
  | POST /jobs
  v
API Service
  |
  | create job row
  v
PostgreSQL
  |
  | publish job id
  v
Message Queue
  |
  | consume job
  v
Worker Pool
  |
  | update status/progress/result
  v
PostgreSQL
  |
  | notify on completion/failure
  v
Notification Service
  |
  v
Webhook / Email / Push
```

The API remains fast and responsive because it only validates the request, creates a durable job record, and publishes a message. Long-running execution happens outside the request/response path in a horizontally scalable worker pool.

Users query job status through the API, which reads from the database. Notifications are best-effort outbound events sent after terminal job states such as `COMPLETED` or `FAILED`.

## Major Components

### API Service

Responsibilities:

- Accept job submissions.
- Validate request payloads.
- Create a durable job record with initial status, usually `QUEUED`.
- Publish a job message to the queue.
- Expose status endpoints:
  - `GET /jobs/{id}`
  - `GET /jobs`
- Expose control endpoints:
  - `POST /jobs/{id}/cancel`
  - `POST /jobs/{id}/retry`
- Enforce user authorization so users can only access their own jobs.

The API should not perform long-running job work inline.

### Job Store

I would use PostgreSQL as the source of truth for job state.

The job table would store:

- Job ID
- User ID
- Input payload
- Status: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`
- Progress percentage
- Current processing step
- Attempt count and max attempts
- Result or error message
- Cancellation flag
- Timestamps: created, started, updated, completed

The database gives durable state, queryability, and a reliable source for real-time status reads.

### Message Queue

The queue decouples submission from execution and absorbs bursts.

The queue message should be small, usually just:

```json
{
  "job_id": "..."
}
```

The worker loads the full job from the database. This avoids stale or oversized queue messages and keeps the database as the source of truth.

RabbitMQ, SQS, Pub/Sub, Kafka, or Redis Streams could work depending on scale and operational constraints. For the minimal implementation, I used RabbitMQ.

### Worker Pool

Workers consume job messages and execute the long-running task.

Responsibilities:

- Claim or load a job.
- Mark it `RUNNING`.
- Execute the work in stages.
- Update progress and current step.
- Check for cancellation between stages.
- Mark the job `COMPLETED` with result data.
- Mark the job `FAILED` with an error message if processing fails.
- Trigger notifications on terminal states.

Workers should be horizontally scalable. Queue prefetch/concurrency settings should be tuned based on job cost, downstream dependencies, and fairness needs.

### Notification Service

Users expect to be notified when jobs complete or fail. I would model notifications as a separate concern, even if initially implemented inside the worker.

Notification channels may include:

- Webhooks
- Email
- Push notifications
- Internal events

For webhooks, I would send a structured event such as:

```json
{
  "user_id": "user-id",
  "event": "job.completed",
  "data": {
    "job_id": "job-id",
    "result": {}
  }
}
```

In a production system, webhook delivery should have retries, backoff, timeout handling, signature verification, and delivery logs.

## Handling Key Requirements

### High Submission Volume And Spikes

The queue is the main buffer for unpredictable spikes. The API only needs to perform fast database writes and message publication, while workers scale independently.

Approach:

- Keep submission path lightweight.
- Use durable queue messages.
- Add worker autoscaling based on queue depth and processing latency.
- Apply rate limits per user or tenant.
- Use idempotency keys on job submission to avoid duplicate jobs during client retries.
- Consider separate queues or priorities for different job types.

### Retry Logic

Jobs may fail due to transient issues such as network timeouts, third-party errors, or temporary resource limits.

Approach:

- Track `attempt_count` and `max_attempts`.
- Retry only failures that are safe to retry.
- Use exponential backoff with jitter.
- Store the last error message.
- Move permanently failed jobs to a terminal `FAILED` state.
- Use dead-letter queues for messages that cannot be processed successfully.

Retry behavior must be idempotent. If the same job runs more than once, it should not corrupt state or duplicate irreversible side effects.

### Real-Time Status Queries

Users should be able to query job status at any time.

Approach:

- Store all meaningful job state transitions in PostgreSQL.
- Update progress after each meaningful processing stage.
- Keep status reads simple and indexed by `job_id` and `user_id`.
- Optionally add WebSockets, Server-Sent Events, or polling optimizations if the UI needs live progress.

For an initial version, polling `GET /jobs/{id}` is sufficient and simple.

### Cancellation

Cancellation is hardest when jobs are already running. A queued job can be cancelled immediately. A running job usually needs cooperative cancellation.

Approach:

- If the job is `QUEUED`, mark it `CANCELLED`.
- If the job is `RUNNING`, set `cancel_requested = true`.
- Workers check `cancel_requested` at safe checkpoints.
- If cancellation is detected, stop processing and mark the job `CANCELLED`.

Some work may not be instantly interruptible. The API should make that clear: cancellation is requested and completed once the worker reaches a safe stopping point.

## Hardest Problems

### 1. Idempotency And Exactly-Once Expectations

Distributed systems rarely provide true exactly-once execution. Queue messages can be delivered more than once, workers can crash midway, and clients may retry submissions.

My approach:

- Treat processing as at-least-once.
- Make job state transitions idempotent.
- Use idempotency keys for job creation.
- Have workers check current job status before processing.
- Avoid repeating irreversible side effects, or guard them with deduplication keys.
- Make notifications idempotent or track delivery attempts.

The user-facing guarantee should be framed around durable job state, not exactly-once worker execution.

### 2. Cancellation Semantics

Cancellation sounds simple, but it depends heavily on the task being performed. Some tasks can stop immediately; others need safe checkpoints.

My approach:

- Use cooperative cancellation.
- Store a cancellation request flag in the job record.
- Check that flag between meaningful stages.
- Clearly distinguish `cancel requested` from `cancelled` if the UI needs that nuance.
- Avoid cancelling during critical sections that would leave partial state inconsistent.

### 3. Backpressure And Fairness Under Load

During spikes, the system needs to avoid letting a few users or expensive jobs starve everyone else.

My approach:

- Use queue depth and job age as scaling signals.
- Apply per-user or per-tenant rate limits.
- Consider priority queues or separate queues by job class.
- Bound worker concurrency.
- Add visibility into queue latency, processing time, failure rate, and retry volume.

This is mostly an operational problem, not just an application-code problem.

## Assumptions

- Jobs can be represented by a durable input payload and a generated job ID.
- Users can tolerate polling for status in the first version.
- A job may be executed at least once; worker logic should be idempotent.
- Cancellation can be cooperative rather than instant.
- Notifications are expected but should not block marking the job completed.
- The database is the source of truth for job state.
- Queue messages can be small and reference the job by ID.
- Initial scale can be handled with a single relational database plus horizontally scalable workers.

## Minimal Implementation Notes

The accompanying repository implements a minimal version of this design:

https://github.com/elandy/makai_challenge

Implemented:

- FastAPI job submission/status/cancel/retry endpoints
- PostgreSQL job persistence
- RabbitMQ queue publishing and consuming
- Async worker process
- Simulated multi-step processing
- Progress and status updates
- Cooperative cancellation flag
- Retry endpoint for failed/cancelled jobs
- Webhook notification on completion/failure
- Docker Compose setup
- Basic unit tests

Intentionally simplified:

- The worker simulates document processing instead of performing real PDF extraction.
- Authentication is stubbed.
- Webhook delivery has no retry/backoff system yet.
- There are no database migrations.
- There is no production-grade worker autoscaling or dead-letter queue configuration yet.

The goal of the implementation is to demonstrate the architecture and prove the main asynchronous flow works end to end, not to present a production-complete system.
