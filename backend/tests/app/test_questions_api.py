from app.models import UnansweredQuestion


def _add(db, label, seen=1, qtype="text"):
    q = UnansweredQuestion(label=label, question_type=qtype, options=["A", "B"], seen_count=seen)
    db.add(q)
    db.commit()
    return q


def test_list_unanswered_with_search(client, db):
    _add(db, "Proficiency in German?")
    _add(db, "Notice period?")
    page = client.get("/api/questions/unanswered").json()
    assert page["total"] == 2
    page = client.get("/api/questions/unanswered?q=german").json()
    assert [i["label"] for i in page["items"]] == ["Proficiency in German?"]
    assert page["items"][0]["options"] == ["A", "B"]


def test_answer_unanswered_moves_to_custom_answers(client, db):
    q = _add(db, "Proficiency in German?")
    r = client.post(f"/api/questions/unanswered/{q.id}/answer", json={"answer": "None"})
    assert r.status_code == 200
    custom = client.get("/api/settings").json()["questions"]["custom_answers"]
    assert custom == [{"match": "Proficiency in German?", "answer": "None"}]
    assert client.get("/api/questions/unanswered").json()["total"] == 0
    # Answering again adds to the list, never replaces it.
    q2 = _add(db, "Years of Go?")
    client.post(f"/api/questions/unanswered/{q2.id}/answer", json={"answer": "5"})
    custom = client.get("/api/settings").json()["questions"]["custom_answers"]
    assert [c["match"] for c in custom] == ["Proficiency in German?", "Years of Go?"]


def test_answer_validation_and_missing(client, db):
    q = _add(db, "Q?")
    assert client.post(f"/api/questions/unanswered/{q.id}/answer", json={"answer": "  "}).status_code == 422
    assert client.post("/api/questions/unanswered/999999/answer", json={"answer": "x"}).status_code == 404


def test_dismiss_unanswered(client, db):
    q = _add(db, "Q?")
    assert client.delete(f"/api/questions/unanswered/{q.id}").status_code == 204
    assert client.get("/api/questions/unanswered").json()["total"] == 0
