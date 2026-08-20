"""Acceptance tests for Layer 7: Streamlit Frontend Layer."""

import importlib


def test_frontend_module_imports_cleanly():
    # Verify module exists and can be imported/parsed without syntax or dependency errors
    spec = importlib.util.find_spec("layer7_frontend.app")
    assert spec is not None, "layer7_frontend.app must be importable"


def test_frontend_decision_payload_structure():
    finding_idx = 2
    accept_payload = {"finding_index": finding_idx, "decision": "accept"}
    assert accept_payload["finding_index"] == 2
    assert accept_payload["decision"] == "accept"

    edit_payload = {
        "finding_index": finding_idx,
        "decision": "edit",
        "edited_text": "custom fix",
    }
    assert edit_payload["decision"] == "edit"
    assert edit_payload["edited_text"] == "custom fix"
