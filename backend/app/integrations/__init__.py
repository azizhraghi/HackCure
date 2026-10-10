"""Glue between the three developers' parts on one backend.

d2_bridge  - D2A extraction + safety graph -> D3 plan draft (code grounding, patient confirmation);
             the patient's "D2 JSON" for D1; active plan -> D2B RAG index (per patient).
d1_bridge  - D1 expected-recovery trajectory (home-screen card) computed in the background and cached.
"""
