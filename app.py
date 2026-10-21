"""A tiny campus task board used to demonstrate the CCA 2 CI/CD pipeline."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


TASKS = [
    {"title": "Submit cloud computing lab", "status": "In progress"},
    {"title": "Review Kubernetes notes", "status": "To do"},
    {"title": "Prepare CI/CD demo", "status": "Done"},
]
TASKS_LOCK = threading.Lock()
TASK_STATUSES = {"In progress", "To do", "Done"}

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Campus Task Board</title>
  <style>
    :root{font-family:system-ui,sans-serif;color:#182230;background:#f3f6fb}
    body{margin:0;padding:4rem 1.25rem}.card{max-width:660px;margin:auto;padding:2.25rem;
      background:white;border:1px solid #dce4ef;border-radius:20px;box-shadow:0 16px 50px #18223012}
    .tag{color:#155eef;font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.78rem}
    h1{margin:.6rem 0;font-size:2.2rem}p{color:#526173}.task{display:flex;justify-content:space-between;
      gap:1rem;padding:1rem 0;border-top:1px solid #e7ecf3}.status{font-size:.86rem;color:#155eef}
    .summary{margin:0 0 1rem;font-weight:600;color:#344054}
    .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
      clip:rect(0,0,0,0);white-space:nowrap;border:0}
    form{display:grid;grid-template-columns:1fr auto auto;gap:.6rem;margin:1.4rem 0 1rem}
    input,select,button{font:inherit;padding:.7rem .8rem;border:1px solid #cbd5e1;border-radius:9px}
    button{background:#155eef;color:#fff;border:0;font-weight:700;cursor:pointer}
    button:hover{background:#004eeb}button:disabled{opacity:.6;cursor:wait}
    #message{min-height:1.4em;margin:.3rem 0;color:#155eef;font-size:.9rem}
    @media(max-width:560px){body{padding:1.5rem .7rem}.card{padding:1.25rem}form{grid-template-columns:1fr}h1{font-size:1.8rem}}
    footer{margin-top:1.5rem;font-size:.85rem;color:#667085}
  </style>
</head>
<body><main class="card"><div class="tag">Student project · CI/CD demo</div>
  <h1>Campus Task Board</h1><p>A small project deployed automatically with Jenkins, Docker and Kubernetes.</p>
  <p id="summary" class="summary" aria-live="polite"></p>
  <form id="task-form">
    <label for="task-title" class="sr-only">Task name</label>
    <input id="task-title" name="title" placeholder="Enter a task" maxlength="120" required>
    <label for="task-status" class="sr-only">Task status</label>
    <select id="task-status" name="status"><option>To do</option><option>In progress</option><option>Done</option></select>
    <button id="submit-task" type="submit">Add task</button>
  </form>
  <p id="message" role="status" aria-live="polite"></p>
  <section id="tasks" aria-live="polite">Loading tasks…</section><footer id="version"></footer>
  <script>
    async function refreshBoard(){
      const response=await fetch('/api/tasks');
      if(!response.ok) throw new Error('Could not load tasks.');
      const data=await response.json();
      const taskList=document.querySelector('#tasks');
      taskList.replaceChildren();
      data.tasks.forEach(task=>{
        const row=document.createElement('div'); row.className='task';
        const title=document.createElement('strong'); title.textContent=task.title;
        const status=document.createElement('span'); status.className='status'; status.textContent=task.status;
        row.append(title,status); taskList.append(row);
      });
      document.querySelector('#summary').textContent=
        `${data.summary.total} tasks · ${data.summary.in_progress} in progress · ${data.summary.to_do} to do · ${data.summary.done} done`;
      document.querySelector('#version').textContent=`Application version ${data.version}`;
    }
    refreshBoard().catch(()=>document.querySelector('#tasks').textContent='Could not load tasks.');
    document.querySelector('#task-form').addEventListener('submit',async event=>{
      event.preventDefault();
      const form=event.currentTarget;
      const button=document.querySelector('#submit-task');
      const message=document.querySelector('#message');
      button.disabled=true; message.textContent='Adding task…';
      try{
        const response=await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({title:form.elements.title.value,status:form.elements.status.value})});
        const result=await response.json();
        if(!response.ok) throw new Error(result.error||'Could not add task.');
        form.reset(); message.textContent=`Added “${result.task.title}” (${result.task.status}).`;
        await refreshBoard();
      }catch(error){message.textContent=error.message;}
      finally{button.disabled=false;}
    });
  </script>
</main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/health":
            self._send(200, "ok", "text/plain; charset=utf-8")
        elif self.path == "/api/tasks":
            with TASKS_LOCK:
                tasks = [task.copy() for task in TASKS]
            self._send_json(200, {
                "version": app_version(),
                "tasks": tasks,
                "summary": summarize_tasks(tasks),
            })
        elif self.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "Not found", "text/plain; charset=utf-8")

    def do_POST(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path != "/api/tasks":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= content_length <= 4096:
                raise ValueError("Request body must be between 1 and 4096 bytes")
            payload = json.loads(self.rfile.read(content_length))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object")
            title = payload.get("title")
            status = payload.get("status", "To do")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("Task title is required")
            title = title.strip()
            if len(title) > 120:
                raise ValueError("Task title must be 120 characters or fewer")
            if status not in TASK_STATUSES:
                raise ValueError("Status must be In progress, To do, or Done")
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
            return

        task = {"title": title, "status": status}
        with TASKS_LOCK:
            TASKS.append(task)
            summary = summarize_tasks(TASKS)
        self._send_json(201, {"task": task, "summary": summary})

    def _send_json(self, status, payload):
        self._send(status, json.dumps(payload), "application/json; charset=utf-8")

    def _send(self, status, body, content_type):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        print(f"{self.client_address[0]} - {fmt % args}")


def main():
    port = configured_port()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Campus Task Board {app_version()} listening on port {port}")
    server.serve_forever()


def app_version():
    """Return the configured display version, defaulting to the starter version."""
    return os.environ.get("APP_VERSION", "1.0.0")


def summarize_tasks(tasks):
    """Return counts for the task board's supported statuses."""
    return {
        "total": len(tasks),
        "in_progress": sum(task["status"] == "In progress" for task in tasks),
        "to_do": sum(task["status"] == "To do" for task in tasks),
        "done": sum(task["status"] == "Done" for task in tasks),
    }


def configured_port():
    """Read and validate PORT so configuration errors fail with a clear message."""
    raw_port = os.environ.get("PORT", "8080")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError("PORT must be an integer from 1 to 65535") from error
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be an integer from 1 to 65535")
    return port


if __name__ == "__main__":
    main()
