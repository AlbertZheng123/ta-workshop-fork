// Client-side rendering for the starter. The AI adds priority during the demo.
document.addEventListener('DOMContentLoaded', fetchTasks);

async function fetchTasks() {
    const response = await fetch('/api/tasks');
    const tasks = await response.json();
    const taskList = document.getElementById('task-list');
    taskList.innerHTML = '';

    tasks.forEach(task => {
        const li = document.createElement('li');
        // A task title is user input, not HTML.
        const title = document.createElement('span');
        title.textContent = task.title;
        const button = document.createElement('button');
        button.className = 'delete-btn';
        button.textContent = 'Delete';
        button.addEventListener('click', () => deleteTask(task.id));
        li.append(title, button);
        taskList.appendChild(li);
    });
}

async function addTask() {
    const titleInput = document.getElementById('task-title');
    const title = titleInput.value.trim();

    if (!title) return;

    await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
    });

    titleInput.value = '';
    fetchTasks();
}

async function deleteTask(id) {
    await fetch(`/api/tasks/${id}`, {
        method: 'DELETE'
    });
    fetchTasks();
}
