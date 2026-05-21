import pytest


@pytest.mark.asyncio
async def test_create_and_get_job(client):
    payload = {
      "document_url": "www.example.com/file.pdf",
      "extract_keywords": True,
      "generate_summary": True,
      "callback_url": "string"
}

    # Create job
    res = await client.post("/jobs", json=payload)
    print(res.status_code)
    print(res.json())
    assert res.status_code == 200

    data = res.json()
    job_id = data["job_id"]

    assert data["status"] == "QUEUED"

    # Fetch job
    res = await client.get(f"/jobs/{job_id}")
    assert res.status_code == 200

    data = res.json()
    assert data["job_id"] == job_id
    assert data["status"] == "QUEUED"