"""Protected baseline checks for the original, pre-priority app."""

import pytest
import app as app_module
from app import app, tasks

@pytest.fixture
def client():
    """Provide an isolated Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset both task data and the ID counter before every test."""
    app_module.next_id = 3
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Project-1 Report"},
        {"id": 2, "title": "Project-2 MMFs"}
    ])

def test_index(client):
    """Render the original task tracker page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Task Tracker" in response.data

def test_get_tasks(client):
    """Return the two seeded tasks."""
    response = client.get('/api/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2

def test_add_task_success(client):
    """Add a title and expose the new task in the list."""
    response = client.post('/api/tasks', json={"title": "Test new task"})
    assert response.status_code == 201
    assert response.get_json()['title'] == "Test new task"
    get_response = client.get('/api/tasks')
    assert len(get_response.get_json()) == 3

def test_add_task_missing_title(client):
    """Reject missing titles without creating a task."""
    response = client.post('/api/tasks', json={"wrong_key": "value"})
    assert response.status_code == 400
    assert "error" in response.get_json()
    response2 = client.post('/api/tasks', json={})
    assert response2.status_code == 400

def test_delete_task(client):
    """Test deleting an existing task."""
    response = client.delete('/api/tasks/1')
    assert response.status_code == 200
    get_response = client.get('/api/tasks')
    data = get_response.get_json()
    assert len(data) == 1
    assert data[0]['id'] == 2
