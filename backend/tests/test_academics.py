from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import auth_headers
from tests.factories import PASSWORD, build_school, create_admin


def test_attendance_is_idempotent_per_session(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    entry = {
        "student_id": school["student_ids"][0],
        "subject_id": school["subject_id"],
        "session_date": str(date.today()),
        "status": "absent",
    }
    client.post("/api/attendance", json={"entries": [entry]}, headers=headers)
    client.post(
        "/api/attendance", json={"entries": [{**entry, "status": "present"}]}, headers=headers
    )
    records = client.get(
        f"/api/students/{school['student_ids'][0]}/attendance", headers=headers
    ).json()
    assert len(records) == 1
    assert records[0]["status"] == "present"


def test_mark_cannot_exceed_assessment_maximum(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    assessment = client.post(
        "/api/assessments",
        json={
            "subject_id": school["subject_id"],
            "title": "Unit test",
            "assessment_type": "quiz",
            "max_score": 50,
            "held_on": str(date.today()),
        },
        headers=headers,
    ).json()
    response = client.post(
        "/api/marks",
        json={
            "assessment_id": assessment["id"],
            "student_id": school["student_ids"][0],
            "score": 60,
        },
        headers=headers,
    )
    assert response.status_code == 400


def test_teacher_cannot_grade_subject_they_do_not_teach(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)

    other_teacher = client.post(
        "/api/teachers",
        json={
            "user": {
                "email": "teacher2@test.edu",
                "full_name": "Teacher Two",
                "role": "teacher",
                "password": PASSWORD,
            },
            "department": "Arts",
        },
        headers=headers,
    ).json()
    assert other_teacher["id"]

    other_headers = auth_headers(client, "teacher2@test.edu", PASSWORD)
    response = client.post(
        "/api/assessments",
        json={
            "subject_id": school["subject_id"],
            "title": "Sneaky quiz",
            "assessment_type": "quiz",
            "max_score": 10,
            "held_on": str(date.today()),
        },
        headers=other_headers,
    )
    assert response.status_code == 403


def test_assignment_submission_upsert(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    assignment = client.post(
        "/api/assignments",
        json={
            "subject_id": school["subject_id"],
            "title": "Worksheet 1",
            "description": "Practice",
            "max_score": 20,
            "due_date": str(date.today()),
        },
        headers=headers,
    ).json()
    payload = {
        "assignment_id": assignment["id"],
        "student_id": school["student_ids"][0],
        "status": "graded",
        "submitted_on": str(date.today()),
        "score": 18,
    }
    client.post("/api/submissions", json=payload, headers=headers)
    client.post("/api/submissions", json={**payload, "score": 19}, headers=headers)
    submissions = client.get(
        f"/api/students/{school['student_ids'][0]}/submissions", headers=headers
    ).json()
    assert len(submissions) == 1
    assert submissions[0]["score"] == 19


def test_duplicate_email_is_rejected(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    response = client.post(
        "/api/students",
        json={
            "user": {
                "email": "student0@test.edu",
                "full_name": "Duplicate",
                "role": "student",
                "password": PASSWORD,
            },
            "roll_number": "R-77",
            "class_id": school["class_id"],
        },
        headers=headers,
    )
    assert response.status_code == 409
