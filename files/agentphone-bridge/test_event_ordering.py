import hashlib
import hmac
import importlib.util
import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("agentphone_bridge.py")
spec = importlib.util.spec_from_file_location("agentphone_bridge_under_test", MODULE_PATH)
bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bridge)


class EventOrderingTests(unittest.TestCase):
    def test_extract_event_fields_prefers_message_received_at_over_delivery_timestamp(self):
        payload = {
            "event": "agent.message",
            "channel": "imessage",
            "timestamp": "2026-07-10T00:28:01.000000Z",
            "data": {
                "conversationId": "conv-1",
                "from": "+15555550123",
                "direction": "inbound",
                "message": "older message delivered late",
                "messageId": "msg-old",
                "receivedAt": "2026-07-10T00:26:21.184000Z",
            },
        }

        fields = bridge.extract_event_fields(payload)

        self.assertEqual(fields["timestamp"], "2026-07-10T00:26:21.184000Z")

    def test_late_older_message_is_rejected_by_conversation_watermark(self):
        with tempfile.TemporaryDirectory() as tmp:
            watermark_path = Path(tmp) / "conversation_watermarks.json"
            newer = {
                "conversation_id": "conv-1",
                "sender": "+15555550123",
                "message_id": "msg-new",
                "timestamp": "2026-07-10T00:27:04.656000Z",
            }
            older_delivered_late = {
                "conversation_id": "conv-1",
                "sender": "+15555550123",
                "message_id": "msg-old",
                "timestamp": "2026-07-10T00:26:21.184000Z",
            }

            accepted_new, _ = bridge.mark_conversation_event_if_fresh(newer, watermark_path)
            accepted_old, latest = bridge.mark_conversation_event_if_fresh(older_delivered_late, watermark_path)

            self.assertTrue(accepted_new)
            self.assertFalse(accepted_old)
            self.assertEqual(latest, newer["timestamp"])
            stored = json.loads(watermark_path.read_text())
            self.assertEqual(stored["conv-1"]["timestamp"], newer["timestamp"])

    def test_http_handler_does_not_start_job_for_stale_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            secret = "test-webhook-secret"
            started_message_ids = []
            original = {
                "CONFIG": bridge.CONFIG,
                "WEBHOOK_SECRET": bridge.WEBHOOK_SECRET,
                "SEEN_PATH": bridge.SEEN_PATH,
                "EVENTS_LOG": bridge.EVENTS_LOG,
                "mark": bridge.mark_conversation_event_if_fresh,
                "reaction": bridge.handle_reaction_only,
                "start": bridge.start_conversation_job,
                "run": bridge.run_hermes_and_reply,
            }
            watermark_path = tmp_path / "watermarks.json"
            bridge.CONFIG = {
                "AGENTPHONE_ALLOWED_SENDERS": "+15555550123",
                "AGENTPHONE_FULL_ACCESS_NUMBERS": "+15555550123",
            }
            bridge.WEBHOOK_SECRET = secret
            bridge.SEEN_PATH = tmp_path / "seen.json"
            bridge.EVENTS_LOG = tmp_path / "events.log"
            bridge.mark_conversation_event_if_fresh = (
                lambda fields: original["mark"](fields, watermark_path)
            )
            bridge.handle_reaction_only = lambda fields: False

            def fake_start(fields, reply_target):
                started_message_ids.append(fields["message_id"])
                return {"interrupted_previous": False}

            bridge.start_conversation_job = fake_start
            bridge.run_hermes_and_reply = lambda *args: None
            server = bridge.BridgeHTTPServer(("127.0.0.1", 0), bridge.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def post(message_id, received_at, text):
                payload = {
                    "event": "agent.message",
                    "channel": "imessage",
                    "timestamp": "2026-07-10T00:30:00Z",
                    "data": {
                        "conversationId": "conv-1",
                        "from": "+15555550123",
                        "direction": "inbound",
                        "message": text,
                        "messageId": message_id,
                        "receivedAt": received_at,
                    },
                }
                raw = json.dumps(payload).encode()
                signature_ts = str(int(time.time()))
                signature = "sha256=" + hmac.new(
                    secret.encode(), signature_ts.encode() + b"." + raw, hashlib.sha256
                ).hexdigest()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/hooks/agentphone",
                    data=raw,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Timestamp": signature_ts,
                        "X-Webhook-Signature": signature,
                    },
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    return response.status, json.loads(response.read())

            try:
                fresh_status, fresh_body = post(
                    "msg-new", "2026-07-10T00:27:04.656000Z", "newer"
                )
                stale_status, stale_body = post(
                    "msg-old", "2026-07-10T00:26:21.184000Z", "older delivered late"
                )
                time.sleep(0.05)

                self.assertEqual(fresh_status, 200)
                self.assertTrue(fresh_body["accepted"])
                self.assertEqual(stale_status, 200)
                self.assertEqual(stale_body["ignored"], "stale message")
                self.assertEqual(started_message_ids, ["msg-new"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
                bridge.CONFIG = original["CONFIG"]
                bridge.WEBHOOK_SECRET = original["WEBHOOK_SECRET"]
                bridge.SEEN_PATH = original["SEEN_PATH"]
                bridge.EVENTS_LOG = original["EVENTS_LOG"]
                bridge.mark_conversation_event_if_fresh = original["mark"]
                bridge.handle_reaction_only = original["reaction"]
                bridge.start_conversation_job = original["start"]
                bridge.run_hermes_and_reply = original["run"]


if __name__ == "__main__":
    unittest.main()
