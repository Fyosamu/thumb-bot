# -*- coding: utf-8 -*-
"""one-shot localhost:8090 listener - grabs the ?code= from the OAuth
redirect and writes it to _oauth_code.txt.  run as a background process
before opening the consent URL."""
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

OUT = Path(__file__).resolve().parent / "_oauth_code.txt"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        code = (qs.get("code") or [None])[0]
        err = (qs.get("error") or [None])[0]
        if code:
            OUT.write_text(code, encoding="utf-8")
            body = b"OK - you can close this window."
        elif err:
            OUT.write_text("ERROR:" + err, encoding="utf-8")
            body = b"ERROR - see listener file."
        else:
            body = b"waiting..."
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


HTTPServer(("127.0.0.1", 8090), H).handle_request()
sys.exit(0)
