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


@pytest.mark.asyncio
async def test_get_job_by_id(client):
    payload = {
        "document_url": "https://example.com/file.pdf",
        "extract_keywords": True,
        "generate_summary": True,
        "callback_url": None,
    }

    create_res = await client.post("/jobs", json=payload)
    assert create_res.status_code == 200

    job_id = create_res.json()["job_id"]

    get_res = await client.get(f"/jobs/{job_id}")

    assert get_res.status_code == 200
    data = get_res.json()

    assert data["job_id"] == job_id


@pytest.mark.asyncio
async def test_list_jobs(client):
    payload = {
        "document_url": "https://example.com/file.pdf",
        "extract_keywords": True,
        "generate_summary": True,
        "callback_url": None,
    }

    # create at least one job
    await client.post("/jobs", json=payload)

    res = await client.get("/jobs")

    assert res.status_code == 200
    data = res.json()

    assert isinstance(data, list)
    assert len(data) >= 1