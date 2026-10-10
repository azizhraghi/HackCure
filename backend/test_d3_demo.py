import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


class D3DemoTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        os.environ["SURGIGUARD_DB_PATH"] = str(Path(self.directory.name) / "demo.sqlite3")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        os.environ.pop("SURGIGUARD_DB_PATH", None)
        self.directory.cleanup()

    def event(self, event_id="event-1", answer="yes"):
        return {
            "event_id": event_id,
            "patient_id": "synthetic-patient",
            "kind": "structured_warning",
            "code": "demo_urgent_warning",
            "answer": answer,
            "source": "patient",
            "occurred_at": "2026-10-10T08:00:00Z",
        }

    def test_safety_runs_before_investigation_and_replay_is_idempotent(self):
        url = "/v1/demo/episodes/synthetic-episode/events"
        first = self.client.post(url, json=self.event())
        self.assertEqual(first.status_code, 201)
        result = first.json()
        self.assertEqual(result["safety_decision"]["outcome"], "emergency")
        self.assertEqual(result["investigation_status"], "not_started")
        self.assertEqual(self.client.post(url, json=self.event()).json(), result)
        self.assertEqual(len(self.client.get("/v1/demo/episodes/synthetic-episode/alerts").json()["alerts"]), 1)
        self.assertEqual(len(self.client.get("/v1/demo/episodes/synthetic-episode/outbox").json()["delivery_intents"]), 2)

        report = self.client.post("/v1/demo/episodes/synthetic-episode/investigations?event_id=event-1")
        self.assertEqual(report.status_code, 201)
        self.assertEqual(report.json()["state"], "partial")
        self.assertTrue(report.json()["findings"][0]["evidence_ids"])
        self.assertEqual(self.client.post("/v1/demo/episodes/synthetic-episode/investigations?event_id=event-1").json(), report.json())

    def test_unknown_is_indeterminate_and_changed_replay_conflicts(self):
        url = "/v1/demo/episodes/synthetic-episode/events"
        response = self.client.post(url, json=self.event(answer="unknown"))
        self.assertEqual(response.json()["safety_decision"]["outcome"], "indeterminate")
        self.assertIsNone(response.json()["alert_id"])
        self.assertEqual(self.client.post(url, json=self.event(answer="yes")).status_code, 409)

    def test_followup_requires_decision_and_verification(self):
        event = self.client.post("/v1/demo/episodes/synthetic-episode/events", json=self.event()).json()
        followup_id = event["followup_id"]
        base = f"/v1/demo/followups/{followup_id}"
        premature = self.client.post(base + "/verifications", json={
            "actor_id": "demo-clinician", "expected_version": 1, "evidence_id": "proof-1"
        })
        self.assertEqual(premature.status_code, 409)
        ack = self.client.post(base + "/acknowledgements", json={
            "actor_id": "demo-patient", "expected_version": 1
        })
        self.assertEqual(ack.json()["stage"], "acknowledged")
        self.assertEqual(self.client.post(base + "/clinical-decisions", json={
            "actor_id": "demo-clinician", "expected_version": 1, "note": "Synthetic review"
        }).status_code, 409)
        decision = self.client.post(base + "/clinical-decisions", json={
            "actor_id": "demo-clinician", "expected_version": 2, "note": "Synthetic review"
        })
        self.assertEqual(decision.json()["stage"], "action_recorded")
        closed = self.client.post(base + "/verifications", json={
            "actor_id": "demo-clinician", "expected_version": 3, "evidence_id": "proof-1"
        })
        self.assertEqual(closed.json()["stage"], "closed")
        history = self.client.get(base).json()["actions"]
        self.assertEqual([item["action_type"] for item in history],
                         ["acknowledged", "clinical_decision", "verified"])


if __name__ == "__main__":
    unittest.main()
