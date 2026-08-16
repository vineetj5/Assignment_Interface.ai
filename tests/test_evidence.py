import json
from pathlib import Path
from automation.evidence import EvidenceStore
from automation.models import ActionResult, ActionType, Observation
from automation.redaction import EvidenceSanitizer


def test_evidence_sanitizer():
    sanitizer = EvidenceSanitizer()
    text = "Member SSN is 123-45-6789 and password is password=Secret123!"
    sanitized = sanitizer.sanitize_text(text)
    assert "123-45-6789" not in sanitized
    assert "[REDACTED]" in sanitized

    d = {"user_ssn": "123-45-6789", "nested": {"card": "4111 1111 1111 1111"}}
    sanitized_d = sanitizer.sanitize_dict(d)
    assert sanitized_d["user_ssn"] == "[REDACTED]"


def test_evidence_store(tmp_path: Path):
    store = EvidenceStore(base_dir=tmp_path, run_id="run_test_001")
    store.write_metadata({"target": "http://127.0.0.1:8000"})
    assert (tmp_path / "run_test_001" / "metadata.json").exists()

    action = ActionResult(
        action_id="act_001",
        action_type=ActionType.CLICK,
        status="success",
        started_at="2026-08-15T12:00:00Z",
        completed_at="2026-08-15T12:00:01Z",
        duration_ms=100.5,
    )
    store.append_action(action, step=1)
    actions_file = tmp_path / "run_test_001" / "actions.jsonl"
    assert actions_file.exists()
    with actions_file.open() as f:
        line = f.readline()
        data = json.loads(line)
        assert data["action_id"] == "act_001"
        assert data["step"] == 1

    obs = Observation(
        observation_id="obs_001",
        page_url="http://127.0.0.1:8000/legacy",
        page_title="Legacy Shell",
    )
    saved_path = store.save_observation(obs)
    assert saved_path.exists()
