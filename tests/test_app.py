import pytest

import app as app_module


@pytest.fixture
def client():
    """Provide a test client with a clean task store."""
    app_module.tasks = [
        {
            "id": 1,
            "title": "Project-1 Report",
            "description": "",
        },
        {
            "id": 2,
            "title": "Project-2 MMFs",
            "description": "",
        },
    ]
    app_module.next_id = 3

    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as test_client:
        yield test_client


def test_index_page_is_rendered(client):
    """Render the task tracker index page."""
    response = client.get("/")

    assert response.status_code == 200
    assert b"Task Tracker" in response.data


def test_listing_returns_all_tasks(client):
    """Return all tasks with their descriptions."""
    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": 1,
            "title": "Project-1 Report",
            "description": "",
        },
        {
            "id": 2,
            "title": "Project-2 MMFs",
            "description": "",
        },
    ]


def test_task_creation_preserves_existing_behavior(client):
    """Create a task with a title and generated ID."""
    response = client.post(
        "/api/tasks",
        json={"title": "New task"},
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "id": 3,
        "title": "New task",
        "description": "",
    }


def test_description_is_saved_and_returned(client):
    """Save and return a supplied task description."""
    response = client.post(
        "/api/tasks",
        json={
            "title": "Document task",
            "description": "Write the project documentation.",
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "id": 3,
        "title": "Document task",
        "description": "Write the project documentation.",
    }

    listing = client.get("/api/tasks")
    assert listing.get_json()[-1] == response.get_json()


def test_omitted_description_defaults_to_empty_string(client):
    """Default an omitted description to an empty string."""
    response = client.post(
        "/api/tasks",
        json={"title": "Task without description"},
    )

    assert response.status_code == 201
    assert response.get_json()["description"] == ""


def test_null_description_defaults_to_empty_string(client):
    """Default a null description to an empty string."""
    response = client.post(
        "/api/tasks",
        json={
            "title": "Task with null description",
            "description": None,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["description"] == ""


@pytest.mark.parametrize("payload", [{}, {"title": ""}, None])
def test_title_is_required(client, payload):
    """Reject task creation when the title is missing or empty."""
    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {"error": "Title is required"}


def test_delete_task_removes_task(client):
    """Delete a task while preserving the remaining tasks."""
    response = client.delete("/api/tasks/1")

    assert response.status_code == 200
    assert response.get_json() == {"result": "success"}

    listing = client.get("/api/tasks")
    assert listing.get_json() == [
        {
            "id": 2,
            "title": "Project-2 MMFs",
            "description": "",
        },
    ]
