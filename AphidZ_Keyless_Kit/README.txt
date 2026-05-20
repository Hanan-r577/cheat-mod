==============================================================================
  AphidZ Keyless Kit
  Local auth/heartbeat emulator + patched client.
  Runs AphidZ with no license key, no concurrent-session limit, no expiry.
==============================================================================

WHAT THIS IS
------------
AphidZ talks to a live licensing server (api-rejoin.pebletz.xyz) for login
and a recurring heartbeat. The kit replaces that server with a local one
that always returns a valid, never-expiring session, and a 3-byte-patched
client DLL that accepts it. Nothing is poked in memory; the DLL's real auth
pipeline runs normally against the local server, so the session stays alive
exactly the way a paid one would.

CONTENTS
--------
  AphidZ_EMU.dll        The client. Pristine AphidZ + a single 3-byte patch
                        (runtime_core validity flag). Inject THIS.
  WinHttpRelax.dll      Hook DLL: makes WinHTTP accept the emulator's
                        self-signed cert (the client validates certs by
                        default; no system trust store changes).
  AphidZInjector.exe    DLL injector (targets PixelWorlds.exe).
  emulator\
    emulator.py         The local HTTPS server (port 443). Replays a real
                        captured session, refreshing every lease so it
                        never expires; no concurrency limit.
    aphidz_protocol.json Captured genuine server protocol (the data served).
    server.crt/.key     Self-signed cert for api-rejoin.pebletz.xyz
                        (auto-regenerated if deleted; needs Python
                        'cryptography' only for regeneration).
    START_AphidZ.ps1    One click: adds the hosts redirect + starts emulator.
    STOP_AphidZ.ps1     Removes the hosts redirect + stops the emulator.

PREREQUISITES
-------------
  - Windows x64
  - Python 3 on PATH (standard library is enough; 'cryptography' only
    needed if server.crt/.key are missing and must be regenerated)
  - Administrator rights (editing the hosts file + binding port 443)
  - PixelWorlds, launched with  -force-d3d11  (Steam launch options)
  - Port 443 free (stop Skype / IIS / other local web servers)

SETUP (ORDER MATTERS)
---------------------
  1. Right-click  emulator\START_AphidZ.ps1  -> Run with PowerShell
     (it self-elevates to admin). It:
       - adds  127.0.0.1 api-rejoin.pebletz.xyz  to your hosts file
       - starts the emulator in its own window  (LEAVE THAT WINDOW OPEN)
     You should see "AphidZ emulator listening on https://0.0.0.0:443".

  2. Launch PixelWorlds with  -force-d3d11  -- do this AFTER step 1, fresh.
     (If PixelWorlds was already running, fully close and relaunch it, or
      it will have cached the real server's IP.)

  3. Inject  WinHttpRelax.dll  FIRST, then WAIT ~5 SECONDS.
       AphidZInjector.exe --dll WinHttpRelax.dll
     (Its cert-bypass hook installs on a background thread; it must be
      fully active before the client connects, or the first TLS handshake
      to the self-signed cert fails = "cannot reach server".)

  4. Inject  AphidZ_EMU.dll
       AphidZInjector.exe --dll AphidZ_EMU.dll

  5. In the AphidZ login, type ANYTHING as the key, click Login.
     Watch the emulator window: you should see a "start" line, then
     "heartbeat" lines repeating. Login status should go valid.

  6. Toggle fly / features.

  When finished: run  emulator\STOP_AphidZ.ps1  (admin) to remove the
  hosts redirect and put traffic back to the real server.

TROUBLESHOOTING
---------------
  "cannot reach server"
     - WinHttpRelax not active in time. Reinject in the right order:
       relax first, wait 5s, THEN AphidZ_EMU. Game must be launched
       AFTER the emulator + hosts redirect are live.
     - Emulator window closed / port 443 taken. Re-run START_AphidZ.ps1;
       confirm the "listening" banner; free port 443.
     - Stale DNS: the START script flushes DNS, but if the game was open
       before, close and relaunch it.

  "Runtime core invalid - update backend"
     - You injected the wrong DLL. Inject AphidZ_EMU.dll (the patched
       one), not a clean/original AphidZ.

  "reached maximum allowed concurrent sessions"
     - That's the REAL server. It means traffic is NOT being redirected:
       the hosts entry is missing or the emulator isn't running. Re-run
       START_AphidZ.ps1 and confirm api-rejoin.pebletz.xyz resolves to
       127.0.0.1 (the emulator removes this limit entirely).

  Emulator window shows nothing when you log in
     - Traffic isn't reaching it (see "cannot reach server" above).

  Login OK but a feature is inert
     - Feature authorization comes from start+heartbeat (handled). The
       movement/command channel is replayed; if one specific feature
       misbehaves while others work, that channel's payload may need
       per-feature work -- report which feature.

HOW IT WORKS (short)
--------------------
  - hosts: api-rejoin.pebletz.xyz -> 127.0.0.1
  - emulator.py serves the 3 endpoints (start / heartbeat /
    movement/command) using a real captured session, rewriting every
    lease_until to now+1h on every request -> the session never expires;
    it has no concurrency check -> unlimited installs.
  - WinHttpRelax.dll forces WinHTTP to ignore cert errors so the
    self-signed cert is accepted (no root-store changes).
  - AphidZ_EMU.dll = original AphidZ with one 3-byte patch at the
    runtime_core validity flag, so it accepts the (lease-rewritten)
    response. The rest of the real auth/heartbeat pipeline is untouched,
    which is why the session stays alive like a genuine one.

NOTES
-----
  - For owner/recovery use of software you have rights to.
  - The bundled cert is not machine-bound; the kit is portable. Another
    machine only needs Python 3 + admin + PixelWorlds -force-d3d11.
==============================================================================
