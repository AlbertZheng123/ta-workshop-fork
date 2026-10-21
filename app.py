from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

tasks = [
    {"id": 1, "title": "Project-1 Report", "description": ""},
    {"id": 2, "title": "Project-2 MMFs", "description": ""}
]
next_id = 3


def normalize_task(task):
    """Ensure a task always contains a string description."""
    task["description"] = task.get("description") or ""
    return task


@app.route('/')
def index():
    """Render the task tracker page."""
    return render_template('index.html')


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Return all tasks."""
    return jsonify([normalize_task(task) for task in tasks])


@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Create and return a task."""
    global next_id
    data = request.get_json(silent=True)

    if not data or not data.get('title'):
        return jsonify({"error": "Title is required"}), 400

    new_task = {
        "id": next_id,
        "title": data['title'],
        "description": data.get('description') or ''
    }
    tasks.append(new_task)
    next_id += 1

    return jsonify(new_task), 201


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task by ID."""
    tasks[:] = [task for task in tasks if task['id'] != task_id]
    return jsonify({"result": "success"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
