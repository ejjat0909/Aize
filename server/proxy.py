"""One public port for both Aize services: /search -> search server, everything else -> Valhalla.

The platform exposes one preview port per VM, so this fronts both on :8002.
"""
import sys

import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN = int(__import__("os").environ.get("PORT", "8002"))
SEARCH = __import__("os").environ.get("SEARCH_URL", "http://127.0.0.1:8001")
VALHALLA = __import__("os").environ.get("VALHALLA_URL", "http://127.0.0.1:8002")


class Proxy:
    def __init__(self, port):
        self.port = port

    def get(self, path, timeout=60):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=timeout) as r:
            return r.status, r.read()

    def post(self, path, body, ctype, timeout=60):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body,
                                     headers={"Content-Type": ctype}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()


SEARCH_SRV = Proxy(int(SEARCH.rsplit(":", 1)[1]))
SEARCH_PREFIXES = ("/search", "/categories")
VALHALLA_SRV = Proxy(int(VALHALLA.rsplit(":", 1)[1]))


def target_for(path, search=SEARCH_SRV, valhalla=VALHALLA_SRV):
    """Which upstream answers this path.

    Anything not listed here falls through to Valhalla, whose 404 ("Unrecognized request URL")
    looks like a broken app rather than a missing route. /categories was in exactly that hole: the
    chips silently fell back to the app's built-in list and nobody noticed the server was never asked.
    """
    return search if path.startswith(SEARCH_PREFIXES) else valhalla


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _relay(self, fn):
        target = target_for(self.path)
        try:
            status, body = fn(target)
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read()
        except Exception as e:
            status, body = 502, ('{"error": "upstream unavailable: %s"}' % e).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._relay(lambda t: t.get(self.path))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        ctype = self.headers.get("Content-Type") or "application/json"
        self._relay(lambda t: t.post(self.path, body, ctype))

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"proxy on :{LISTEN}  search={SEARCH}  valhalla={VALHALLA}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", LISTEN), Handler).serve_forever()
