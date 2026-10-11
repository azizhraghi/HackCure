"""Cree dans l'API SurgiGuard (.NET) les comptes de l'histoire : la patiente (avec son boitier ESP32), son proche et un medecin.

    python seed_story.py [--api http://localhost:8080] [--device ESP32_001]

Idempotent : si les comptes existent deja, on se connecte au lieu de les recreer. Stdlib uniquement.
Utilise une base jetable (MongoDbSettings__DatabaseName=DB_story) pour ne pas toucher a la vraie base.
"""
import argparse
import json
import urllib.error
import urllib.request

PASSWORD = "Story2026!"


def call(api, method, path, body=None, token=None):
    req = urllib.request.Request(api + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "true",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def account(api, email, **fields):
    status, res = call(api, "POST", "/api/auth/register", {"email": email, "password": PASSWORD, **fields})
    if status == 409 or status == 400:
        status, res = call(api, "POST", "/api/auth/login", {"email": email, "password": PASSWORD})
    if status >= 300:
        raise SystemExit(f"{email}: {status} {res}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8080")
    ap.add_argument("--device", default="ESP32_001")
    a = ap.parse_args()

    sarah = account(a.api, "sarah@story.test", role="PATIENT", first_name="Sarah", last_name="Miller", phone="+21620000001",
                    whatsapp_number="21620000001", date_of_birth="1962-03-14T00:00:00Z", gender="F")
    tok = sarah["access_token"]
    st, me = call(a.api, "GET", "/api/patients/me", token=tok)
    if me.get("device_id") != a.device:
        st, res = call(a.api, "PUT", "/api/patients/me/device", {"device_id": a.device}, tok)
        print("device", a.device, st, res if st >= 300 else "")
        st, me = call(a.api, "GET", "/api/patients/me", token=tok)

    ahmed = account(a.api, "ahmed@story.test", role="FAMILY_MEMBER", first_name="Ahmed", last_name="Khan",
                    phone="+21620000002", whatsapp_number="21620000002")
    st, res = call(a.api, "POST", "/api/family/link-patient", {"link_code": me["link_code"], "relationship": "conjoint",
                                                              "whatsapp_opt_in": True, "is_primary_contact": True}, ahmed["access_token"])
    print("link family", st, "(deja lie)" if st == 409 else "")

    ruiz = account(a.api, "dr.ruiz@story.test", role="DOCTOR", first_name="Elena", last_name="Ruiz", staff_code="STAFF-2026")
    print(json.dumps({"patient_id": me["id"], "device_id": me.get("device_id"), "link_code": me["link_code"],
                      "logins": {"patient": "sarah@story.test", "family": "ahmed@story.test", "doctor": "dr.ruiz@story.test",
                                 "password": PASSWORD}}, indent=2))


if __name__ == "__main__":
    main()
