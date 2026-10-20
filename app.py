"""A tiny campus task board used to demonstrate the CCA 2 CI/CD pipeline."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


TASKS = [
    {"title": "Submit cloud computing lab", "status": "In progress"},
    {"title": "Review Kubernetes notes", "status": "To do"},
    {"title": "Prepare CI/CD demo", "status": "Done"},
]

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
    footer{margin-top:1.5rem;font-size:.85rem;color:#667085}
  </style>
</head>
<body><main class="card"><div class="tag">Student project · CI/CD demo</div>
  <h1>Campus Task Board</h1><p>A small project deployed automatically with Jenkins, Docker and Kubernetes.</p>
  <p id="summary" class="summary" aria-live="polite"></p>
  <section id="tasks" aria-live="polite">Loading tasks…</section><footer id="version"></footer>
  <script>
    fetch('/api/tasks').then(r=>r.json()).then(data=>{
      document.querySelector('#tasks').innerHTML=data.tasks.map(t=>
        `<div class="task"><strong>${t.title}</strong><span class="status">${t.status}</span></div>`).join('');
      document.querySelector('#summary').textContent=
        `${data.summary.total} tasks · ${data.summary.in_progress} in progress · ${data.summary.to_do} to do · ${data.summary.done} done`;
      document.querySelector('#version').textContent=`Application version ${data.version}`;
    }).catch(()=>document.querySelector('#tasks').textContent='Could not load tasks.');
  </script>
</main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/health":
            self._send(200, "ok", "text/plain; charset=utf-8")
        elif self.path == "/api/tasks":
            body = json.dumps({
                "version": app_version(),
                "tasks": TASKS,
                "summary": summarize_tasks(TASKS),
            })
            self._send(200, body, "application/json; charset=utf-8")
        elif self.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "Not found", "text/plain; charset=utf-8")

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
