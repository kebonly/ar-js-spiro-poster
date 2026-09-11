#!/usr/bin/env python3
"""Serve the poster over HTTPS so a phone on the same wifi can test it.

Browsers only expose getUserMedia on a secure origin. `localhost` is exempt,
but a LAN address like 192.168.x.x is not -- so plain `python3 -m http.server`
is enough for a desktop smoke test and useless for testing on a real phone.
This wraps the same server in TLS using a throwaway self-signed certificate.

Your phone will show a certificate warning. That is expected for a self-signed
cert; tap through it ("Advanced" -> "Proceed"). For a warning-free test, use a
tunnel instead:  cloudflared tunnel --url http://localhost:8000

Usage:  python3 tools/serve.py [port]
"""

import http.server
import socket
import ssl
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / ".certs"
CERT = CERT_DIR / "dev-cert.pem"
KEY = CERT_DIR / "dev-key.pem"


def ensure_cert() -> None:
    if CERT.exists() and KEY.exists():
        return
    CERT_DIR.mkdir(exist_ok=True)
    print("generating a self-signed certificate (valid 365 days)...")
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(KEY), "-out", str(CERT),
            "-days", "365", "-subj", "/CN=ar-js-spiro-poster",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def lan_ip() -> str:
    """Best-effort local address; no packets are actually sent."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        # Range support matters for video seeking; SimpleHTTPRequestHandler
        # advertises it and Safari is picky when it is missing.
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8443
    ensure_cert()

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=CERT, keyfile=KEY)

    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    print()
    print(f"  desktop : https://localhost:{port}/")
    print(f"  phone   : https://{lan_ip()}:{port}/")
    print(f"  marker  : https://{lan_ip()}:{port}/marker.html")
    print()
    print("  Accept the certificate warning on the phone. Ctrl-C to stop.")
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
