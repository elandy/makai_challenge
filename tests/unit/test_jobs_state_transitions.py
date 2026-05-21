import pytest


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