import pytest
from shared.db.repositories import jobs as repo
from shared.domain.auth import User
from shared.schemas.jobs import JobInput


@pytest.mark.asyncio
async def test_job_initial_state(client):
    payload = {
        "document_url": "https://example.com/file.pdf",
        "extract_keywords": True,
        "generate_summary": True,
    }

    res = await client.post("/jobs", json=payload)
    job_id = res.json()["job_id"]

    get_res = await client.get(f"/jobs/{job_id}")
    data = get_res.json()

    assert data["status"] in ("PENDING", "QUEUED")


@pytest.mark.asyncio
async def test_cancel_queued_job_marks_it_cancelled(client, sessionmaker_fixture):
    user = User(id="test-user", username="test")
    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
        callback_url=None,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)

    res = await client.post(f"/jobs/{job.id}/cancel")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_running_job_requests_cooperative_cancellation(client, sessionmaker_fixture):
    user = User(id="test-user", username="test")
    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
        callback_url=None,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)
        await repo.mark_running(db, job.id)

    res = await client.post(f"/jobs/{job.id}/cancel")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RUNNING"

    async with sessionmaker_fixture() as db:
        updated = await repo.get_by_id_for_worker(db, job.id)

    assert updated is not None
    assert updated.cancel_requested is True
