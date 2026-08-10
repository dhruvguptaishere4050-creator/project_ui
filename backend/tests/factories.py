from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Role, User
from app.security import hash_password

PASSWORD = "Password123!"


def create_admin(db: Session, email: str = "admin@test.edu") -> User:
    admin = User(
        email=email,
        full_name="Admin User",
        hashed_password=hash_password(PASSWORD),
        role=Role.admin,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def build_school(client: TestClient, headers: dict[str, str]) -> dict[str, int]:
    """Creates a class, teacher, subject, two students and a parent."""
    class_id = client.post(
        "/api/classes",
        json={"name": "Grade 9-A", "academic_year": "2025-2026"},
        headers=headers,
    ).json()["id"]

    teacher_id = client.post(
        "/api/teachers",
        json={
            "user": {
                "email": "teacher@test.edu",
                "full_name": "Teacher One",
                "role": "teacher",
                "password": PASSWORD,
            },
            "department": "Science",
        },
        headers=headers,
    ).json()["id"]

    subject_id = client.post(
        "/api/subjects",
        json={
            "name": "Mathematics",
            "code": "MATH-9",
            "class_id": class_id,
            "teacher_id": teacher_id,
        },
        headers=headers,
    ).json()["id"]

    student_ids = []
    for index in range(2):
        response = client.post(
            "/api/students",
            json={
                "user": {
                    "email": f"student{index}@test.edu",
                    "full_name": f"Student {index}",
                    "role": "student",
                    "password": PASSWORD,
                },
                "roll_number": f"R-{index}",
                "class_id": class_id,
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        student_ids.append(response.json()["id"])

    parent_id = client.post(
        "/api/parents",
        json={
            "user": {
                "email": "parent@test.edu",
                "full_name": "Parent One",
                "role": "parent",
                "password": PASSWORD,
            },
            "phone": "123",
            "child_ids": [student_ids[0]],
        },
        headers=headers,
    ).json()["id"]

    return {
        "class_id": class_id,
        "teacher_id": teacher_id,
        "subject_id": subject_id,
        "student_ids": student_ids,
        "parent_id": parent_id,
    }


def add_academic_records(
    client: TestClient,
    headers: dict[str, str],
    subject_id: int,
    student_id: int,
    scores: list[float],
    absences: int = 0,
) -> None:
    entries = []
    for day in range(10):
        entries.append(
            {
                "student_id": student_id,
                "subject_id": subject_id,
                "session_date": str(date.today() - timedelta(days=day + 1)),
                "status": "absent" if day < absences else "present",
            }
        )
    response = client.post("/api/attendance", json={"entries": entries}, headers=headers)
    assert response.status_code == 201, response.text

    for index, score in enumerate(scores):
        assessment = client.post(
            "/api/assessments",
            json={
                "subject_id": subject_id,
                "title": f"Quiz {index} for {student_id}",
                "assessment_type": "quiz",
                "max_score": 100,
                "held_on": str(date.today() - timedelta(days=30 - index * 5)),
            },
            headers=headers,
        ).json()
        response = client.post(
            "/api/marks",
            json={
                "assessment_id": assessment["id"],
                "student_id": student_id,
                "score": score,
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
