#!/usr/bin/env python3
"""
AphidZ local auth/heartbeat emulator.

Replays the captured genuine server protocol from aphidz_protocol.json,
with leases continuously refreshed so the session never expires and with
NO concurrency limit (we are the server). The clean AphidZ DLL talks to
this instead of api-rejoin.pebletz.xyz -> permanently authorized, keyless.

Endpoints (all POST, JSON):
  /api/app-session/v2/start            -> session + runtime_core + secure_data
  /api/app-session/v2/heartbeat        -> refreshed runtime_core (lease bumped)
  /api/app-session/v2/movement/command -> replayed encrypted payload

Requires: hosts entry  127.0.0.1 api-rejoin.pebletz.xyz
          + the cert-relax hook (DLL uses default WinHTTP cert validation)
Run as Administrator (binds :443).
"""
import json, os, ssl, sys, time, datetime, secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE      = os.path.dirname(os.path.abspath(__file__))
PROTO     = os.path.join(HERE, "aphidz_protocol.json")
CERT      = os.path.join(HERE, "server.crt")
KEY       = os.path.join(HERE, "server.key")
HOST      = "0.0.0.0"
PORT      = 443
HOSTNAME  = "api-rejoin.pebletz.xyz"
LEASE_WIN = 3600            # each response leases 1h ahead; refreshed every heartbeat
TTL       = 120             # keep as captured so the DLL keeps heartbeating
USERNAME  = "hawkisprolmfao55"   # name shown in the AphidZ menu

# ---- load captured protocol ------------------------------------------------
if not os.path.exists(PROTO):
    # allow the protocol json to live next to the emulator OR in Downloads
    alt = os.path.join(os.path.dirname(HERE), "aphidz_protocol.json")
    if os.path.exists(alt): PROTO = alt
with open(PROTO, "r", encoding="utf-8") as f:
    CAP = json.load(f)

START_R = CAP["/api/app-session/v2/start"]["response_json"]
HB_R    = CAP["/api/app-session/v2/heartbeat"]["response_json"]
MOVE_R  = CAP["/api/app-session/v2/movement/command"]["response_json"]


def bump_leases(rc, now):
    """Push every lease_until in a runtime_core block to now+LEASE_WIN."""
    if not isinstance(rc, dict):
        return rc
    until = now + LEASE_WIN
    if "lease_until" in rc:
        rc["lease_until"] = until
    if "ttl_seconds" in rc:
        rc["ttl_seconds"] = TTL
    feats = rc.get("features")
    if isinstance(feats, dict):
        for fv in feats.values():
            if isinstance(fv, dict) and "lease_until" in fv:
                fv["lease_until"] = until
    return rc


def make_start():
    now = int(time.time())
    r = json.loads(json.dumps(START_R))          # deep copy
    r["server_time"] = now
    r["success"] = True
    r["username"] = USERNAME                     # shown in the AphidZ menu
    if "runtime_core" in r:
        bump_leases(r["runtime_core"], now)
    return r


def make_heartbeat():
    now = int(time.time())
    r = json.loads(json.dumps(HB_R))
    r["server_time"] = now
    r["success"] = True
    r["message"] = r.get("message", "Heartbeat registered")
    r["security_score"] = 0
    r["next_challenge_nonce"] = secrets.token_hex(24)
    if "runtime_core" in r:
        bump_leases(r["runtime_core"], now)
    return r


def make_move():
    r = json.loads(json.dumps(MOVE_R))
    r["success"] = True
    return r


ROUTES = {
    "/api/app-session/v2/start":            make_start,
    "/api/app-session/v2/heartbeat":        make_heartbeat,
    "/api/app-session/v2/movement/command": make_move,
}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # quiet default logging; we print our own
        pass

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n) if n else b""

    def do_POST(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        req = self._body()
        fn = ROUTES.get(path) or ROUTES.get(path + "/") or ROUTES.get(self.path.rstrip("/"))
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        if not fn:
            print(f"[{ts}] 404 {path}")
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()
            return
        try:
            payload = json.dumps(fn(), separators=(",", ":")).encode()
        except Exception as e:
            print(f"[{ts}] 500 {path}: {e}")
            self.send_response(500); self.send_header("Content-Length", "0"); self.end_headers()
            return
        tag = path.rsplit("/", 1)[-1]
        rb = req[:80].decode("utf-8", "replace")
        print(f"[{ts}] 200 {tag:9} <- {rb}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers()
        self.wfile.write(b"ok")


def ensure_cert():
    if os.path.exists(CERT) and os.path.exists(KEY):
        return
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOSTNAME)])
    san = x509.SubjectAlternativeName([x509.DNSName(HOSTNAME),
                                       x509.DNSName("*.pebletz.xyz")])
    now = datetime.datetime.utcnow()
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(san, critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))
    with open(KEY, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))
    with open(CERT, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"[*] generated self-signed cert for {HOSTNAME}")


def main():
    ensure_cert()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    srv = ThreadingHTTPServer((HOST, PORT), H)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    print("=" * 60)
    print(f"  AphidZ emulator listening on https://{HOST}:{PORT}")
    print(f"  pretending to be {HOSTNAME}")
    print(f"  leases auto-refresh +{LEASE_WIN}s every request (never expires)")
    print(f"  features: {list(START_R.get('runtime_core',{}).get('features',{}).keys())}")
    print("=" * 60)
    print("  Need:  hosts entry '127.0.0.1 api-rejoin.pebletz.xyz'")
    print("         + cert-relax hook injected (DLL validates certs by default)")
    print("  Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] stopped")


if __name__ == "__main__":
    try:
        main()
    except PermissionError:
        print("ERROR: binding :443 needs Administrator. Run elevated.")
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: {e}\n(Is :443 already in use? Stop other servers / Skype / IIS.)")
        sys.exit(1)
