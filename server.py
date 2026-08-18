#!/usr/bin/env python3
"""Stats API server for agent-04.

Serves:
  GET /api/stats          — current session window stats
  GET /api/stats/history  — full stats history (capped at 5000 entries)
  POST /api/log           — append a new stats entry (JSON body)

Also serves the project's index.html at root for the web presence.
"""

import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(PROJECT_DIR, "index.html")
LOG_PATH = os.path.join(PROJECT_DIR, "logs", "stats.jsonl")
MAX_ENTRIES = 5000


def _read_all():
    """Read all entries from the log file."""
    entries = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    # Cap at MAX_ENTRIES, keep most recent
    return entries[-MAX_ENTRIES:]


def _write_entry(entry):
    """Append a single entry to the log."""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


class StatsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default request logging
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            # Serve the index.html
            if os.path.exists(INDEX_HTML):
                with open(INDEX_HTML, "r") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "not found"}).encode())

        elif path == "/api/stats":
            entries = _read_all()
            if entries:
                latest = entries[-1]
                # Return window stats (last collected window)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(latest).encode())
            else:
                # Return default zeros
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "pageviews": 0, "visitors": 0, "visits": 0,
                    "bounces": 0, "total_time_seconds": 0
                }).encode())

        elif path == "/api/stats/history":
            entries = _read_all()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(entries).encode())

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not found"}).encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/log":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                entry = json.loads(body)
                # Add timestamp
                entry["collected_at"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                )
                _write_entry(entry)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode())
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "invalid json"}).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not found"}).encode())


def main():
    host = "0.0.0.0"
    port = 8080
    server = HTTPServer((host, port), StatsHandler)
    print(f"Stats API running on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()