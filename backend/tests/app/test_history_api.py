from datetime import datetime, timedelta

from app.models import AppliedJob, FailedJob


def _applied(db, n=3):
    base = datetime(2026, 10, 1, 12, 0)
    for i in range(n):
        db.add(AppliedJob(job_id=str(100 + i), title=f"Dev {i}", company="Acme" if i % 2 == 0 else "Globex",
                          date_applied=base + timedelta(days=i), about_job="long text", job_link=f"https://l/{i}"))
    db.commit()


def test_applied_newest_first_and_light_items(client, db):
    _applied(db)
    page = client.get("/api/history/applied").json()
    assert page["total"] == 3 and [i["job_id"] for i in page["items"]] == ["102", "101", "100"]
    assert "about_job" not in page["items"][0]


def test_applied_filters(client, db):
    _applied(db, 5)
    assert client.get("/api/history/applied?company=globex").json()["total"] == 2
    assert client.get("/api/history/applied?q=Dev 3").json()["total"] == 1
    r = client.get("/api/history/applied?date_from=2026-10-02&date_to=2026-10-03").json()
    assert sorted(i["job_id"] for i in r["items"]) == ["101", "102"]


def test_applied_detail(client, db):
    _applied(db, 1)
    assert client.get("/api/history/applied/100").json()["about_job"] == "long text"
    assert client.get("/api/history/applied/nope").status_code == 404


def test_failed_list(client, db):
    db.add(FailedJob(job_id="9", assumed_reason="Found a Bad Word", stack_trace="trace", date_tried=datetime(2026, 10, 2)))
    db.add(FailedJob(job_id="8", assumed_reason="AI: low relevance", stack_trace="t", date_tried=datetime(2026, 10, 3)))
    db.commit()
    page = client.get("/api/history/failed").json()
    assert [i["job_id"] for i in page["items"]] == ["8", "9"]
    assert "stack_trace" not in page["items"][0]
    assert client.get("/api/history/failed?q=bad word").json()["total"] == 1
    fid = page["items"][0]["id"]
    assert client.get(f"/api/history/failed/{fid}").json()["stack_trace"] == "t"
