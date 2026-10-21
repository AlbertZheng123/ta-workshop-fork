import pytest

from app import app, tasks


@pytest.fixture
def client():
    """Provide a Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset the in-memory task list before each test."""
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Project-1 Report", "description": ""},
        {"id": 2, "title": "Project-2 MMFs", "description": ""}
    ])


def test_index(client):
    """Render the task tracker page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Task Tracker" in response.data


def test_get_tasks(client):
    """Return all existing tasks."""
    response = client.get('/api/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert all(task['description'] == '' for task in data)


def test_add_task_success(client):
    """Create a task without a description."""
    response = client.post('/api/tasks', json={"title": "Test new task"})
    assert response.status_code == 201
    assert response.get_json()['title'] == "Test new task"
    get_response = client.get('/api/tasks')
    assert len(get_response.get_json()) == 3


def test_add_task_with_description(client):
    """Save and return a supplied task description."""
    response = client.post(
        '/api/tasks',
        json={"title": "Document feature", "description": "Add API docs"}
    )

    assert response.status_code == 201
    assert response.get_json()['description'] == "Add API docs"

    get_response = client.get('/api/tasks')
    created_task = get_response.get_json()[-1]
    assert created_task['title'] == "Document feature"
    assert created_task['description'] == "Add API docs"


def test_add_task_omitted_description_defaults_to_empty_string(client):
    """Use an empty description when the field is omitted."""
    response = client.post('/api/tasks', json={"title": "No details"})

    assert response.status_code == 201
    assert response.get_json()['description'] == ''

    get_response = client.get('/api/tasks')
    created_task = get_response.get_json()[-1]
    assert created_task['description'] == ''


def test_add_task_missing_title(client):
    """Reject task creation when the title is missing."""
    response = client.post('/api/tasks', json={"wrong_key": "value"})
    assert response.status_code == 400
    assert "error" in response.get_json()
    response2 = client.post('/api/tasks', json={})
    assert response2.status_code == 400


def test_delete_task(client):
    """Delete an existing task."""
    response = client.delete('/api/tasks/1')
    assert response.status_code == 200
    get_response = client.get('/api/tasks')
    data = get_response.get_json()
    assert len(data) == 1
    assert data[0]['id'] == 2
