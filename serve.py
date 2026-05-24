#!/usr/bin/env python3
"""Static file server with optional cross-origin isolation headers."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class COIRequestHandler(SimpleHTTPRequestHandler):
    """Serve files; optionally add COOP/COEP for SharedArrayBuffer experiments."""

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
