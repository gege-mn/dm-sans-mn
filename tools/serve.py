"""Local server for the type tester and the kerning tool.

    .venv/bin/python tools/serve.py        # then open http://localhost:8765

Serves the repo so the pages can load the built fonts, saves kerning edits to
build/kerning.json, and rebuilds the variable fonts on request.
"""
import json
import os
import subprocess
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KERNING = os.path.join(ROOT, "build", "kerning.json")
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # always show the fonts just built
        super().end_headers()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/tools/tester.html")
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/save-kerning":
            # The page sends only the pairs it changed; merging here means a stale tab can never
            # wipe values written by another tab or by tools/autokern.py.
            change = json.loads(body)
            pairs = {}
            if os.path.exists(KERNING):
                with open(KERNING, encoding="utf-8") as fh:
                    pairs = json.load(fh).get("pairs", {})
            pairs.update(change.get("set", {}))
            for pair in change.get("remove", []):
                pairs.pop(pair, None)
            with open(KERNING, "w", encoding="utf-8") as fh:
                json.dump({"pairs": pairs}, fh, ensure_ascii=False, indent=1, sort_keys=True)
                fh.write("\n")
            self._reply({"ok": True, "pairs": pairs})
        elif self.path == "/build":
            run = subprocess.run([os.path.join(ROOT, "build.sh"), "quick"], capture_output=True, text=True)
            self._reply({"ok": run.returncode == 0, "log": (run.stdout + run.stderr)[-2000:]})
        else:
            self.send_error(404)

    def _reply(self, payload):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print(f"Tester:  {url}/tools/tester.html\nKerning: {url}/tools/kerning.html\nCtrl-C to stop.")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
