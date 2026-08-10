from fastapi.testclient import TestClient

from tests.conftest import auth_headers
from tests.factories import PASSWORD, build_school, create_admin


def test_login_and_me(client: TestClient, db_session) -> None:
    create_admin(db_session)
    headers = auth_headers(client, "admin@test.edu", PASSWORD)
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_login_rejects_bad_password(client: TestClient, db_session) -> None:
    create_admin(db_session)
    response = client.post(
        "/api/auth/login", data={"username": "admin@test.edu", "password": "wrong"}
    )
    assert response.status_code == 401


def test_unauthenticated_requests_are_rejected(client: TestClient) -> None:
    assert client.get("/api/students").status_code == 401


def test_student_cannot_create_students(client: TestClient, db_session) -> None:
    create_admin(db_session)
    admin_headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, admin_headers)
    student_headers = auth_headers(client, "student0@test.edu", PASSWORD)

    response = client.post(
        "/api/students",
        json={
            "user": {
                "email": "hacker@test.edu",
                "full_name": "Hacker",
                "role": "student",
                "password": PASSWORD,
            },
            "roll_number": "R-99",
            "class_id": school["class_id"],
        },
        headers=student_headers,
    )
    assert response.status_code == 403


def test_student_cannot_read_another_students_records(client: TestClient, db_session) -> None:
    create_admin(db_session)
    admin_headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, admin_headers)
    student_headers = auth_headers(client, "student0@test.edu", PASSWORD)

    other_id = school["student_ids"][1]
    assert client.get(f"/api/students/{other_id}", headers=student_headers).status_code == 403
    assert (
        client.get(f"/api/students/{other_id}/marks", headers=student_headers).status_code == 403
    )
    assert (
        client.get(
            f"/api/insights/students/{other_id}/metrics", headers=student_headers
        ).status_code
        == 403
    )


def test_parent_sees_only_their_child(client: TestClient, db_session) -> None:
    create_admin(db_session)
    admin_headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, admin_headers)
    parent_headers = auth_headers(client, "parent@test.edu", PASSWORD)

    listed = client.get("/api/students", headers=parent_headers).json()
    assert [item["id"] for item in listed] == [school["student_ids"][0]]
    assert (
        client.get(
            f"/api/students/{school['student_ids'][1]}", headers=parent_headers
        ).status_code
        == 403
    )


def test_parent_cannot_access_at_risk_report(client: TestClient, db_session) -> None:
    create_admin(db_session)
    admin_headers = auth_headers(client, "admin@test.edu", PASSWORD)
    build_school(client, admin_headers)
    parent_headers = auth_headers(client, "parent@test.edu", PASSWORD)
    assert client.get("/api/insights/at-risk", headers=parent_headers).status_code == 403


def test_teacher_can_read_own_class_students(client: TestClient, db_session) -> None:
    create_admin(db_session)
    admin_headers = auth_headers(client, "admin@test.edu", PASSWORD)
    school = build_school(client, admin_headers)
    teacher_headers = auth_headers(client, "teacher@test.edu", PASSWORD)

    listed = client.get("/api/students", headers=teacher_headers).json()
    assert sorted(item["id"] for item in listed) == sorted(school["student_ids"])


def test_refresh_token_flow(client: TestClient, db_session) -> None:
    create_admin(db_session)
    login = client.post(
        "/api/auth/login", data={"username": "admin@test.edu", "password": PASSWORD}
    )
    # The refresh token is only ever a cookie, never part of the JSON payload.
    assert "refresh_token" not in login.json()
    assert client.cookies.get("sams_refresh")

    response = client.post("/api/auth/refresh")
    assert response.status_code == 200
    assert response.json()["access_token"]

    refresh_cookie = client.cookies["sams_refresh"]
    client.post("/api/auth/logout")
    assert client.post("/api/auth/refresh").status_code == 401

    # A copy of the pre-logout cookie cannot be replayed either.
    client.cookies.set("sams_refresh", refresh_cookie)
    assert client.post("/api/auth/refresh").status_code == 401


def test_password_change_revokes_existing_tokens(client: TestClient, db_session) -> None:
    create_admin(db_session)
    login = client.post(
        "/api/auth/login", data={"username": "admin@test.edu", "password": PASSWORD}
    )
    refresh_cookie = client.cookies["sams_refresh"]
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "NewPassword123!"},
        headers=headers,
    )
    assert changed.status_code == 204

    assert client.get("/api/auth/me", headers=headers).status_code == 401
    client.cookies.set("sams_refresh", refresh_cookie)
    assert client.post("/api/auth/refresh").status_code == 401
    client.cookies.clear()
    assert auth_headers(client, "admin@test.edu", "NewPassword123!")


def test_access_token_cannot_be_used_as_refresh_token(client: TestClient, db_session) -> None:
    create_admin(db_session)
    login = client.post(
        "/api/auth/login", data={"username": "admin@test.edu", "password": PASSWORD}
    ).json()
    client.cookies.set("sams_refresh", login["access_token"])
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401
