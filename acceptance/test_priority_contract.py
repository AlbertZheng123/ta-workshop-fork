"""TA-owned checks of the issue's backend contract, not generated tests.

These intentionally fail on the starter. Run them only in the feature QA stage.
Frontend behavior still needs a browser demonstration and human review.
"""

import pytest
import app as app_module


@pytest.fixture
def client():
    """Keep acceptance tests independent of baseline test ordering."""
    app_module.tasks.clear()
    app_module.next_id = 1
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


@pytest.mark.parametrize("priority", ["Low", "Medium", "High"])
def test_priority_round_trip(client, priority):
    """Store and return every priority named in the original issue."""
    response = client.post("/api/tasks", json={
        "title": "Example task", "priority": priority,
    })
    assert response.status_code == 201
    assert response.get_json()["priority"] == priority
    assert client.get("/api/tasks").get_json()[0]["priority"] == priority


def test_missing_priority_defaults_to_medium(client):
    """Keep old clients working when they submit only a title."""
    response = client.post("/api/tasks", json={"title": "Old client"})
    assert response.status_code == 201
    assert response.get_json()["priority"] == "Medium"
