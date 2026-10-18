"""Small in-memory task API; priority is intentionally left for the demo."""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

tasks = [
    {"id": 1, "title": "Project-1 Report"},
    {"id": 2, "title": "Project-2 MMFs"}
]
next_id = 3

@app.route('/')
def index():
    """Serve the task tracker page."""
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Return the current tasks; restarting the app resets this list."""
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Create a task with a server-assigned ID."""
    global next_id
    data = request.get_json()

    if not data or not data.get('title'):
        return jsonify({"error": "Title is required"}), 400

    new_task = {
        "id": next_id,
        "title": data['title']
    }
    tasks.append(new_task)
    next_id += 1

    return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task without replacing the shared list object."""
    tasks[:] = [t for t in tasks if t['id'] != task_id]
    return jsonify({"result": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
