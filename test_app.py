import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

import app


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_home_page(self):
        with urlopen(self.base + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"Campus Task Board", response.read())

    def test_health_endpoint(self):
        with urlopen(self.base + "/health") as response:
            self.assertEqual(response.read(), b"ok")

    def test_tasks_api(self):
        with patch.dict(os.environ):
            os.environ.pop("APP_VERSION", None)
            with urlopen(self.base + "/api/tasks") as response:
                data = json.load(response)
        self.assertEqual(data["version"], "1.0.0")
        self.assertGreaterEqual(len(data["tasks"]), 1)

    def test_tasks_api_includes_status_summary(self):
        with urlopen(self.base + "/api/tasks") as response:
            data = json.load(response)
        self.assertEqual(data["summary"], {
            "total": 3,
            "in_progress": 1,
            "to_do": 1,
            "done": 1,
        })

    def test_tasks_api_uses_configured_version(self):
        with patch.dict(os.environ, {"APP_VERSION": "build-42"}):
            with urlopen(self.base + "/api/tasks") as response:
                data = json.load(response)
        self.assertEqual(data["version"], "build-42")

    def test_port_defaults_to_8080(self):
        with patch.dict(os.environ):
            os.environ.pop("PORT", None)
            self.assertEqual(app.configured_port(), 8080)

    def test_port_uses_valid_environment_value(self):
        with patch.dict(os.environ, {"PORT": "9090"}):
            self.assertEqual(app.configured_port(), 9090)

    def test_port_rejects_invalid_environment_values(self):
        for value in ("abc", "0", "65536"):
            with self.subTest(value=value), patch.dict(os.environ, {"PORT": value}):
                with self.assertRaisesRegex(ValueError, "PORT must be an integer"):
                    app.configured_port()

    def test_unknown_route(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/missing")
        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
