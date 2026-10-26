"""Local forwarding proxy that records exactly what Claude Code sends to the model.

Usage: python capture_proxy.py PORT OUTDIR
Point Claude Code at it with ANTHROPIC_BASE_URL=http://127.0.0.1:PORT. To label a run's
requests, give Claude Code ANTHROPIC_CUSTOM_HEADERS="X-Draw-Id: <label>"; files are then
named <label>-<n>.json, and the header is stripped before forwarding.

Each request's method, path and JSON body go to OUTDIR. Headers are never written, because
they carry the OAuth token. Responses are forwarded unchanged (buffered, then sent), and
OUTDIR/status.log lists every request with its upstream status.
"""

import http.client
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = "api.anthropic.com"
LABEL_HEADER = "x-draw-id"
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
lock = threading.Lock()
counts: dict[str, int] = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        label = re.sub(r"[^A-Za-z0-9_.-]", "_", self.headers.get(LABEL_HEADER) or "unlabeled")
        with lock:
            counts[label] = counts.get(label, 0) + 1
            name = f"{label}-{counts[label]:02d}"
        try:
            parsed = json.loads(body) if body else None
        except ValueError:
            parsed = {"_non_json_bytes": len(body)}
        (OUT / f"{name}.json").write_text(json.dumps(
            {"method": self.command, "path": self.path, "body": parsed}, indent=1, ensure_ascii=False))
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length", "accept-encoding", "connection", LABEL_HEADER)}
        conn = http.client.HTTPSConnection(UPSTREAM, timeout=900)
        conn.request(self.command, self.path, body=body or None, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in ("transfer-encoding", "content-length", "connection", "content-encoding"):
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        with lock, (OUT / "status.log").open("a") as log:
            log.write(f"{name} {self.command} {self.path} -> {resp.status}\n")

    do_POST = _forward
    do_GET = _forward


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
