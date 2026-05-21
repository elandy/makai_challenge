import pytest


@pytest.mark.asyncio
async def test_missing_required_field(client):
    payload = {
        "extract_keywords": True,
        "generate_summary": True,
    }

    res = await client.post("/jobs", json=payload)

    assert res.status_code == 422

@pytest.mark.asyncio
async def test_job_not_found(client):
    res = await client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_empty_payload(client):
    res = await client.post("/jobs", json={})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_null_document_url(client):
    res = await client.post("/jobs", json={
        "document_url": None,
        "extract_keywords": True,
        "generate_summary": True,
    })
    assert res.status_code == 422
