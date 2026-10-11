"""D1-F wound photos in the shared backend: OpenCV analysis + vision reading on every dressing-change photo."""

from app import llm, requests_service, wound_photos, wounds
from app import models as m
from app.integrations import d1_wound


def _dressing_photo(repo, asset="day3"):
    req_id = wound_photos.request(repo, "sarah")["request_id"]
    requests_service.answer(repo, req_id, m.RequestAnswer(photo_asset=asset, dressing_change_confirmed=True))
    return repo.get(m.Observation, repo.get(m.PatientRequest, req_id).answer_observation_id)


def test_dressing_change_photo_gets_code_analysis_overlay_and_vision_reading(repo):
    obs = _dressing_photo(repo)
    d1 = obs.value["d1"]
    assert d1["quality"]["status"] == "good" and d1["segmentation"]["found"]
    assert d1["overlay_url"].startswith("/uploads/") and (wounds.UPLOADS / d1["overlay_url"].rsplit("/", 1)[-1]).exists()
    assert "staple" in d1["segmentation"]["method"]
    # the seeded reference photo is a different (real, openly licensed) patient: no fake "change" is reported
    if d1["comparison"] is not None:
        assert d1["comparison"]["available"] is False
    vr = obs.value["vision_review"]
    assert vr["available"] and vr["mode"] == "stub" and "offline" in vr["uncertainty"].lower()
    assert obs.value.get("review_alert_id") is None
    pub = wounds.public(obs)
    assert pub["d1"]["overlay_url"] and pub["vision_review"]["note"].endswith("Not a diagnosis.")


def test_photos_still_only_inside_a_permitted_dressing_change(client):
    from app import clock
    clock.advance(6 * 3600)  # 21:30: the window closed at 20:00
    with open(wounds.DEMO_DIR / "day3.jpg", "rb") as f:
        r = client.post("/patients/sarah/wound-photos", files={"file": ("w.jpg", f, "image/jpeg")},
                        data={"dressing_change_confirmed": "true"})
    assert r.status_code == 409


def test_code_rule_raises_a_clinician_only_review_alert(repo):
    obs = _dressing_photo(repo)
    obs.value = {**obs.value, "d1": {**obs.value["d1"], "comparison": {
        "available": True, "trend": "more_red", "summary": "redder than the reference photo, and the redness extends beyond the wound edge",
        "redness_change_delta_a": 7.0, "redness_spread_change": 5.0, "area_change_pct": 10}}}
    repo.add(obs)
    alert_id = d1_wound.decide(repo, obs)
    a = repo.get(m.Alert, alert_id)
    assert a.level == "attention" and a.rule == "wound_review" and "not a diagnosis" in a.reason
    from app.integrations.surgiguard_api import CLINICIAN_ONLY
    assert a.rule.startswith(CLINICIAN_ONLY)  # not pushed to the family


def test_vision_reading_is_filtered_and_only_live_strong_findings_count(repo, monkeypatch):
    obs = _dressing_photo(repo)
    monkeypatch.setattr(llm, "mode", lambda: "live")
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "image_usable": True, "review_suggested": True, "reasons": ["edges look apart"], "uncertainty": "one photo",
        "findings": [{"aspect": "redness", "finding": "This is an infected wound", "confidence": "high"},
                     {"aspect": "discharge_appearance", "finding": "Yellowish fluid appears at the lower end", "confidence": "medium"}]})
    data = d1_wound.photo_bytes(obs.value["url"])
    vr = d1_wound.vision_review(repo, obs, data)
    assert [f["aspect"] for f in vr["findings"]] == ["discharge_appearance"]
    assert vr["removed_for_diagnosis_wording"] == ["This is an infected wound"]
    assert d1_wound.decide(repo, repo.get(m.Observation, obs.id)) is not None


def test_vision_unavailable_keeps_the_code_measurements(repo, monkeypatch):
    obs = _dressing_photo(repo)

    def down(*a, **k):
        raise llm.LLMUnavailable("down")
    monkeypatch.setattr(llm, "chat_json", down)
    vr = d1_wound.vision_review(repo, obs, d1_wound.photo_bytes(obs.value["url"]))
    assert vr["available"] is False and repo.get(m.Observation, obs.id).value["d1"]["segmentation"]["found"]


def test_api_relay_needs_the_agents_key_and_a_linked_patient(client):
    assert client.get("/hub/wound/abc").status_code == 401
    assert client.get("/hub/wound/abc", headers={"X-Api-Key": "dev-agents-key"}).status_code == 404  # link off in tests


def test_wound_status_and_detail_endpoints(client, repo):
    assert client.get("/patients/sarah/wound-status").json()["status"] == "due"
    obs = _dressing_photo(repo)
    r = client.get(f"/patients/sarah/wound-photos/{obs.id}").json()
    assert r["d1"]["segmentation"]["found"]
    r2 = client.post(f"/patients/sarah/wound-photos/{obs.id}/review").json()
    assert r2["vision_review"]["available"]
