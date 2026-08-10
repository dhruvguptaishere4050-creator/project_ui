from fastapi.testclient import TestClient

from tests.conftest import auth_headers
from tests.factories import PASSWORD, add_academic_records, build_school, create_admin


def test_metrics_flag_declining_student(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    struggling = school["student_ids"][0]
    add_academic_records(
        client, headers, school["subject_id"], struggling, [65, 60, 40, 30], absences=6
    )

    metrics = client.get(
        f"/api/insights/students/{struggling}/metrics", headers=headers
    ).json()
    assert metrics["attendance_rate"] == 40.0
    assert metrics["marks_trend"] == "declining"
    assert metrics["risk_level"] == "high"
    assert any("Attendance" in reason for reason in metrics["risk_reasons"])


def test_metrics_for_strong_student_are_low_risk(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    strong = school["student_ids"][1]
    add_academic_records(client, headers, school["subject_id"], strong, [80, 85, 88, 92])

    metrics = client.get(f"/api/insights/students/{strong}/metrics", headers=headers).json()
    assert metrics["attendance_rate"] == 100.0
    assert metrics["risk_level"] == "low"
    assert metrics["overall_average"] > 80


def test_insight_generation_falls_back_to_rules(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    student_id = school["student_ids"][0]
    add_academic_records(client, headers, school["subject_id"], student_id, [55, 45, 35])

    response = client.post(f"/api/insights/students/{student_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "rules"
    assert body["recommendations"]
    assert body["metrics"]["student_id"] == student_id

    history = client.get(
        f"/api/insights/students/{student_id}/history", headers=headers
    ).json()
    assert len(history) == 1


def test_at_risk_listing_and_class_analytics(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, headers)
    weak, strong = school["student_ids"]
    add_academic_records(client, headers, school["subject_id"], weak, [40, 30, 20], absences=7)
    add_academic_records(client, headers, school["subject_id"], strong, [88, 90, 93])

    at_risk = client.get("/api/insights/at-risk", headers=headers).json()
    assert [item["student_id"] for item in at_risk] == [weak]

    in_class = client.get(
        f"/api/insights/at-risk?class_id={school['class_id']}", headers=headers
    ).json()
    assert [item["student_id"] for item in in_class] == [weak]
    other_class = client.get("/api/insights/at-risk?class_id=9999", headers=headers).json()
    assert other_class == []

    analytics = client.get(
        f"/api/insights/classes/{school['class_id']}", headers=headers
    ).json()
    assert analytics["students_count"] == 2
    assert analytics["at_risk_count"] == 1
    assert analytics["top_performers"][0]["student_id"] == strong


def test_student_can_generate_own_insight(client: TestClient, db_session) -> None:
    create_admin(db_session)
    admin_headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, admin_headers)
    student_id = school["student_ids"][0]
    add_academic_records(client, admin_headers, school["subject_id"], student_id, [70, 72])

    student_headers = auth_headers(client, "student0@test.edu", PASSWORD)
    response = client.post(f"/api/insights/students/{student_id}", headers=student_headers)
    assert response.status_code == 200
    assert response.json()["summary"]
