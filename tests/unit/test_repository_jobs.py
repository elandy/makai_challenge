import pytest
from shared.db.models import JobStatus
from shared.db.repositories import jobs as repo
from shared.domain.auth import User
from shared.schemas.jobs import JobInput
from shared.domain.jobs import JobStep


@pytest.mark.asyncio
async def test_create_and_get_job(sessionmaker_fixture):
    user = User(id='1', username='test_user')

    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
        callback_url=None,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)

        assert job.id is not None
        assert job.status.name == "QUEUED"
        assert job.user_id == user.id

        fetched = await repo.get_by_id(db, user, job.id)

        assert fetched is not None
        assert fetched.id == job.id

@pytest.mark.asyncio
async def test_list_jobs(sessionmaker_fixture):
    user = User(id='1', username='test_user')

    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
    )

    async with sessionmaker_fixture() as db:
        await repo.create(db, user, input_data)
        await repo.create(db, user, input_data)

        jobs = await repo.list_jobs(db, user)

        assert len(jobs) == 2
        assert all(j.user_id == user.id for j in jobs)


@pytest.mark.asyncio
async def test_mark_running(sessionmaker_fixture):
    user = User(id='1', username='test_user')

    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)

        await repo.mark_running(db, job.id)

        updated = await repo.get_by_id_for_worker(db, job.id)

        assert updated.status == JobStatus.RUNNING
        assert updated.started_at is not None


@pytest.mark.asyncio
async def test_complete_job(sessionmaker_fixture):
    user = User(id='1', username='test_user')

    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)

        await repo.complete_job(
            db,
            job.id,
            result={"text": "processed", "keywords": ["a", "b"]},
        )

        updated = await repo.get_by_id_for_worker(db, job.id)

        assert updated.status == JobStatus.COMPLETED
        assert updated.progress == 100
        assert updated.result["text"] == "processed"
        assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_fail_job(sessionmaker_fixture):
    user = User(id='1', username='test_user')

    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)

        await repo.fail_job(db, job.id, "boom")

        updated = await repo.get_by_id_for_worker(db, job.id)

        assert updated.status == JobStatus.FAILED
        assert updated.error == "boom"



@pytest.mark.asyncio
async def test_update_progress(sessionmaker_fixture):
    user = User(id='1', username='test_user')

    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)

        await repo.update_progress(
            db,
            job.id,
            progress=42,
            current_step=JobStep.EXTRACTING,
        )

        updated = await repo.get_by_id_for_worker(db, job.id)

        assert updated.progress == 42
        assert updated.current_step == JobStep.EXTRACTING



@pytest.mark.asyncio
async def test_reset_for_retry(sessionmaker_fixture):
    user = User(id='1', username='test_user')

    input_data = JobInput(
        document_url="https://example.com/file.pdf",
        extract_keywords=True,
        generate_summary=True,
    )

    async with sessionmaker_fixture() as db:
        job = await repo.create(db, user, input_data)

        await repo.fail_job(db, job.id, "error")
        await repo.reset_for_retry(db, job.id)

        updated = await repo.get_by_id_for_worker(db, job.id)

        assert updated.status == JobStatus.QUEUED
        assert updated.progress == 0
        assert updated.error is None
        assert updated.result is None
        assert updated.cancel_requested is False
        assert updated.attempt_count == 1