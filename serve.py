#!/usr/bin/env python3
"""Static file server with optional cross-origin isolation headers."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class COIRequestHandler(SimpleHTTPRequestHandler):
    """Serve files; optionally add COOP/COEP for SharedArrayBuffer experiments."""

    def do_POST(self) -> None:  # noqa: N802 (standard library naming)
        if self.path.rstrip("/") != "/__gs_view_log":
            self.send_error(404, "Not Found")
            return

        raw_length = self.headers.get("Content-Length", "0")
        try:
            content_length = int(raw_length)
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return

        body = self.rfile.read(max(content_length, 0))
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "Invalid JSON payload")
            return

        scene = payload.get("scene", "unknown")
        source = payload.get("source", "auto")
        viewer = payload.get("viewer", "pc")
        snapshot = payload.get("snapshot")
        if isinstance(snapshot, dict):
            print(
                f"[PC_VIEW_TERMINAL] scene={scene} viewer={viewer} source={source} "
                f"{json.dumps(snapshot, ensure_ascii=False)}"
            )
        else:
            print(
                f"[PC_VIEW_TERMINAL] scene={scene} viewer={viewer} source={source} "
                f"invalid_snapshot={json.dumps(snapshot, ensure_ascii=False)}"
            )

        response = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def end_headers(self) -> None:
        if getattr(self.server, "coi_headers", False):
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--coi",
        action="store_true",
        help="Enable cross-origin isolation headers (not required for current viewers).",
    )
    args = parser.parse_args()

    httpd = ThreadingHTTPServer(("", args.port), COIRequestHandler)
    httpd.RequestHandlerClass.server_version = "UltraFusionStatic/1.0"
    httpd.coi_headers = args.coi
    print(f"Serving at http://127.0.0.1:{args.port}/  (COI headers: {args.coi})")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
