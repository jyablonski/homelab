def _create_reminder(test_client):
    return test_client.post(
        "/reminders",
        json={
            "reminder_type": "chores",
            "reminder_message": "Water the plants",
            "reminder_start_date": "2026-04-27",
        },
    )


def test_list_reminders_returns_reminders(reminders_table, db_test_client):
    create_response = _create_reminder(db_test_client)
    response = db_test_client.get("/reminders")

    assert create_response.status_code == 201
    assert response.status_code == 200
    assert response.json()[0]["reminder_message"] == "Water the plants"


def test_get_reminder_returns_404_when_missing(reminders_table, db_test_client):
    response = db_test_client.get("/reminders/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "reminder not found"}


def test_get_reminder_returns_reminder(reminders_table, db_test_client):
    create_response = _create_reminder(db_test_client)
    response = db_test_client.get("/reminders/1")

    assert create_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["reminder_message"] == "Water the plants"


def test_create_reminder_returns_created_reminder(reminders_table, db_test_client):
    response = _create_reminder(db_test_client)

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["is_completed"] is False


def test_update_reminder_persists_partial_changes(reminders_table, db_test_client):
    create_response = _create_reminder(db_test_client)
    response = db_test_client.patch("/reminders/1", json={"is_completed": True})
    active_response = db_test_client.get("/reminders")
    all_response = db_test_client.get("/reminders?include_completed=true")

    assert create_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["is_completed"] is True
    assert response.json()["completed_at"] is not None
    assert active_response.json() == []
    assert len(all_response.json()) == 1


def test_update_reminder_returns_404_when_missing(reminders_table, db_test_client):
    response = db_test_client.patch("/reminders/404", json={"is_completed": True})

    assert response.status_code == 404
    assert response.json() == {"detail": "reminder not found"}


def test_update_reminder_reopens_completed_reminder(reminders_table, db_test_client):
    create_response = _create_reminder(db_test_client)
    complete_response = db_test_client.patch(
        "/reminders/1", json={"is_completed": True}
    )
    reopen_response = db_test_client.patch("/reminders/1", json={"is_completed": False})
    active_response = db_test_client.get("/reminders")

    assert create_response.status_code == 201
    assert complete_response.status_code == 200
    assert reopen_response.status_code == 200
    assert reopen_response.json()["is_completed"] is False
    assert reopen_response.json()["completed_at"] is None
    assert len(active_response.json()) == 1
