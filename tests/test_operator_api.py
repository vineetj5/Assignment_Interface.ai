"""Tests for Phase 7 operator API."""

from fastapi.testclient import TestClient
from app import app
from handoff.models import InterventionRequest, InterventionSource
import api.operator as operator_api


client = TestClient(app)


def test_operator_page_loads():
    response = client.get("/operator")
    assert response.status_code == 200
    assert "Operator Handoff Console" in response.text


def test_operator_intervention_list_endpoint():
    operator_api.manager.store.interventions.clear()
    operator_api.manager.store.save_intervention(
        InterventionRequest(
            intervention_id="int_api",
            run_id="run_api",
            source=InterventionSource.REPLAY,
            reason_code="VERIFICATION_REQUIRED",
            reason="verify",
            browser_session_id="browser_api",
        )
    )

    response = client.get("/operator/api/interventions")
    assert response.status_code == 200
    assert response.json()["interventions"][0]["intervention_id"] == "int_api"

    documented_response = client.get("/api/operator/interventions")
    assert documented_response.status_code == 200
    assert documented_response.json()["interventions"][0]["intervention_id"] == "int_api"
