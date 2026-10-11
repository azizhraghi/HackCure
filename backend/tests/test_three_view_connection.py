"""Shared episode state across patient, family and clinic HTTP views."""
from app import clock


def test_three_views_share_care_state_but_family_tasks_do_not_close_alerts(client):
    c = client
    r = c.post('/checkin', json={'pain': 3, 'fatigue': 3, 'mobility': 3, 'chips': ['shortness_of_breath']})
    assert r.status_code == 200 and r.json()['status'] == 'urgent'
    clinic = c.get('/alerts', params={'role': 'clinician', 'open_only': True}).json()
    aid = next(a['id'] for a in clinic if a['level'] == 'urgent')
    def family():
        return c.get('/alerts', params={'role': 'caregiver', 'member_id': 'ahmed', 'open_only': True}).json()
    assert any(a['id'] == aid for a in family())
    assert c.get('/patients/sarah/today').json()['open_alerts'] > 0
    assert c.post(f'/alerts/{aid}/ack', json={'actor': 'ahmed'}).status_code == 403
    assert c.post(f'/alerts/{aid}/ack', json={'actor': 'dr_ruiz'}).status_code == 200
    assert next(a for a in family() if a['id'] == aid)['state'] == 'acknowledged'
    c.get('/caregiver/ahmed/digest', params={'refresh': True})
    tasks = c.get('/caregiver/ahmed/tasks').json()
    assert tasks
    tid = tasks[0]['id']
    assert c.post(f'/caregiver/tasks/{tid}/done', json={'actor': 'ahmed'}).status_code == 200
    assert c.get(f'/alerts/{aid}').json()['state'] == 'acknowledged'
    assert c.post(f'/alerts/{aid}/contacted', json={'actor': 'dr_ruiz', 'note': 'Fictional call'}).status_code == 200
    assert c.post(f'/alerts/{aid}/action', json={'actor': 'dr_ruiz', 'note': 'Review later check-in'}).status_code == 200
    assert c.post(f'/alerts/{aid}/resolve', json={'actor': 'dr_ruiz', 'reason': 'Unverified',
                  'verification_id': 'missing-verification'}).status_code == 409
    clock.advance(1)
    evidence = c.post(f'/demo/alerts/{aid}/followup-evidence', json={'actor': 'dr_ruiz'}).json()
    verification = c.post(f'/alerts/{aid}/verify', json={'actor': 'dr_ruiz', 'summary': 'Later demo check-in reviewed',
                         'outcome': 'resolved', 'observation_ids': [evidence['id']]})
    assert verification.status_code == 200
    assert c.post(f'/alerts/{aid}/resolve', json={'actor': 'dr_ruiz', 'reason': 'Follow-up verified',
                  'verification_id': verification.json()['id']}).status_code == 200
    assert all(a['id'] != aid for a in family())
    assert c.get('/patients/sarah/today').json()['open_alerts'] == 0


def test_sharing_revocation_filters_family_but_preserves_clinic_access(client):
    c = client
    c.post('/checkin', json={'pain': 3, 'fatigue': 3, 'mobility': 3, 'chips': ['shortness_of_breath']})
    c.get('/caregiver/ahmed/digest')
    clock.advance(1)
    assert c.put('/patients/sarah/sharing/ahmed', json={'categories': {'symptoms': True}}).status_code == 200
    assert c.get('/alerts', params={'role': 'caregiver', 'member_id': 'ahmed'}).json() == []
    twin = c.get('/patients/sarah/twin', params={'role': 'caregiver', 'member_id': 'ahmed'}).json()
    assert 'vitals' not in twin and 'medications' not in twin and 'wound' not in twin
    assert c.get('/caregiver/ahmed/digest').json()['shared_categories'] == ['symptoms']
    assert c.get('/alerts', params={'role': 'clinician', 'open_only': True}).json()
