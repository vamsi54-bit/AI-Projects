"""Real local WebSocket checks. Run: python -m unittest discover -s tests -v"""
import json
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

API_DIR = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5173"

class ConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0)); cls.port = listener.getsockname()[1]
        cls.process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(cls.port), "--ws-max-size", "8192"], cwd=API_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.stop_server)
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/health", timeout=1) as response:
                    cls.health = json.load(response)
                return
            except OSError:
                if cls.process.poll() is not None: raise RuntimeError("Test API exited")
                time.sleep(.05)
        raise RuntimeError("Test API did not start")

    @classmethod
    def stop_server(cls):
        cls.process.terminate(); cls.process.wait(timeout=10)

    def ws(self, origin=ORIGIN):
        return connect(f"ws://127.0.0.1:{self.port}/ws", origin=origin, open_timeout=3, close_timeout=1)

    def ping(self, ready, **overrides):
        event = dict(type="health.ping", event_id=str(uuid4()), session_id=ready["session_id"], request_id=str(uuid4()), turn_id=ready["turn_id"], sequence=1, timestamp=datetime.now(timezone.utc).isoformat(), agent="system", payload={})
        event.update(overrides)
        return event

    def recv(self, ws):
        return json.loads(ws.recv(timeout=3))

    def test_http_health_and_real_session_round_trip(self):
        self.assertEqual(self.health, {"status":"ok", "service":"voiceteam-api"})
        with self.ws() as ws:
            ready=self.recv(ws); self.assertEqual(ready["type"], "session.ready"); self.assertEqual(ready["sequence"], 1)
            ping=self.ping(ready); ws.send(json.dumps(ping)); pong=self.recv(ws)
            self.assertEqual(pong["type"], "health.pong"); self.assertEqual(pong["request_id"], ping["request_id"]); self.assertEqual(pong["sequence"], 2)
            self.assertEqual(pong["session_id"], ready["session_id"])

    def test_invalid_messages_rejected_then_connection_accepts_valid_ping(self):
        with self.ws() as ws:
            ready=self.recv(ws)
            for raw in ["{", "null", "[]", json.dumps(self.ping(ready, extra=True)), json.dumps(self.ping(ready, sequence=True)), json.dumps(self.ping(ready, type="agent.status")), json.dumps(self.ping(ready, payload={"fake":"work"}))]:
                ws.send(raw); self.assertEqual(self.recv(ws)["payload"]["code"], "INVALID_MESSAGE")
            ws.send(json.dumps(self.ping(ready))); self.assertEqual(self.recv(ws)["type"], "health.pong")

    def test_wrong_session_turn_duplicates_and_sequence_rejected(self):
        with self.ws() as ws:
            ready=self.recv(ws)
            for changes, code in [({"session_id":str(uuid4())}, "WRONG_SESSION"), ({"turn_id":str(uuid4())}, "INVALID_TURN")]:
                ws.send(json.dumps(self.ping(ready, **changes))); self.assertEqual(self.recv(ws)["payload"]["code"],code)
            event=self.ping(ready); ws.send(json.dumps(event)); self.assertEqual(self.recv(ws)["type"],"health.pong")
            ws.send(json.dumps(event)); self.assertEqual(self.recv(ws)["payload"]["code"],"DUPLICATE_EVENT")
            ws.send(json.dumps(self.ping(ready))); self.assertEqual(self.recv(ws)["payload"]["code"],"STALE_EVENT")
            ws.send(json.dumps(self.ping(ready, sequence=2))); self.assertEqual(self.recv(ws)["type"],"health.pong")

    def test_new_connections_have_isolated_sessions(self):
        with self.ws() as first, self.ws() as second:
            a=self.recv(first); b=self.recv(second)
            self.assertNotEqual(a["session_id"],b["session_id"])
            second.send(json.dumps(self.ping(a))); self.assertEqual(self.recv(second)["payload"]["code"],"WRONG_SESSION")
        with self.ws() as again: self.assertNotEqual(a["session_id"],self.recv(again)["session_id"])

    def test_origin_is_checked(self):
        for origin in [None,"https://example.com"]:
            with self.assertRaises(InvalidStatus):
                with self.ws(origin=origin): pass

    def test_binary_and_oversized_frames_close_connection(self):
        with self.ws() as ws:
            self.recv(ws); ws.send(b"binary"); self.assertEqual(self.recv(ws)["payload"]["code"],"INVALID_MESSAGE")
            with self.assertRaises(ConnectionClosed): ws.recv(timeout=3)
        with self.ws() as ws:
            self.recv(ws); ws.send("x"*9000)
            with self.assertRaises(ConnectionClosed): ws.recv(timeout=3)
