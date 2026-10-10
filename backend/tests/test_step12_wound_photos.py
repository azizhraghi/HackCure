"""Wound photos: measured by code (no AI), compared with the first photo, linked to the agent's photo request."""

import io

from PIL import Image

from app import clock, wound_image, wounds
from app import models as m
from seed import simulator


def jpeg(color=(200, 150, 130), size=(400, 300), red_patch=None) -> bytes:
    im = Image.new("RGB", size, color)
    if red_patch:
        # sharp-edged red area in the centre (+ texture so it is not "blurry")
        for x in range(0, size[0], 7):
            for y in range(0, size[1], 7):
                im.putpixel((x, y), (color[0] - 20, color[1] - 20, color[2] - 20))
        w, h = size
        box = (w // 2 - red_patch, h // 2 - red_patch // 2, w // 2 + red_patch, h // 2 + red_patch // 2)
        im.paste((190, 60, 60), box)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=95)
    return b.getvalue()


def test_real_demo_photos_measured():
    day1 = wound_image.analyze(wounds.demo_bytes("day1"))
    day3 = wound_image.analyze(wounds.demo_bytes("day3"))
    assert day1["quality"] == "good" and day3["quality"] == "good"
    cmp = wound_image.compare(day1, day3)
    assert cmp["available"] and cmp["trend"] == "up"
    assert set(cmp["not_measured"]) >= {"swelling", "drainage"}  # never reported as "none"


def test_bad_photos_ask_for_retake_not_numbers():
    dark = wound_image.analyze(jpeg((8, 8, 8)))
    assert dark["quality"] == "unusable" and "redness_area_pct" not in dark
    assert any("dark" in p for p in dark["problems"])
    assert wound_image.analyze(b"not an image")["quality"] == "unusable"
    assert not wound_image.compare(dark, wound_image.analyze(wounds.demo_bytes("day1")))["available"]


def test_more_red_area_is_detected():
    small = wound_image.analyze(jpeg(red_patch=20))
    large = wound_image.analyze(jpeg(red_patch=60))
    assert large["redness_area_pct"] > small["redness_area_pct"]
    assert wound_image.compare(small, large)["trend"] == "up"


def test_upload_compares_with_reference(client):
    r = client.post("/patients/sarah/wound-photos", files={"file": ("knee.jpg", wounds.demo_bytes("day3"), "image/jpeg")},
                    data={"dressing_change_confirmed": "true"})
    body = r.json()
    assert r.status_code == 200 and body["url"].startswith("/uploads/")
    assert body["reference_url"] == "/static/photos/day1.jpg"
    assert body["comparison"]["available"] and body["comparison"]["trend"] == "up"
    listing = client.get("/patients/sarah/wound-photos").json()
    assert listing["reference"]["label"] == "day1" and listing["photos"][0]["observation_id"] == body["observation_id"]


def test_upload_answers_the_agents_photo_request(repo, client):
    res = simulator.inject(repo, "infection_pattern")
    inv_id = next(r["investigation_id"] for r in res["results"] if r["investigation_id"])
    r = client.post("/patients/sarah/wound-photos", files={"file": ("knee.jpg", wounds.demo_bytes("day3"), "image/jpeg")},
                    data={"dressing_change_confirmed": "true"})
    assert r.json()["answered_request_id"]
    repo.s.expire_all()
    inv = repo.get(m.Investigation, inv_id)
    assert inv.patient_requests == 2  # resumed after the photo, then asked its follow-up question


def test_upload_needs_confirmation_and_a_dressing_window(client):
    photo = {"file": ("knee.jpg", wounds.demo_bytes("day3"), "image/jpeg")}
    assert client.post("/patients/sarah/wound-photos", files=photo).status_code == 409  # not confirmed
    clock.advance(24 * 3600)  # day 4: no dressing change planned
    r = client.post("/patients/sarah/wound-photos", files=photo, data={"dressing_change_confirmed": "true"})
    assert r.status_code == 409 and "dressing change" in r.json()["detail"]
