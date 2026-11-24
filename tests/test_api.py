import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check_and_observability_headers(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers


def test_chroma_reactive_cotton_prediction(client):
    payload = {
        "fabric_type": "cotton",
        "fabric_gsm": 185,
        "liquor_ratio": "1:10",
        "target_L": 43.2,
        "target_a": 50.1,
        "target_b": 17.5,
    }
    response = client.post("/api/v1/predict-recipe", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["dye_class"] == "reactive"
    assert data["product_range"] == "Reactive Dyes"
    assert data["prediction_source"] == "deterministic_fallback"
    assert data["salt_g_per_l"] > 0
    assert data["temperature_c"] == 60
    assert data["prediction_id"] is not None


def test_vibrasperse_disperse_polyester_prediction(client):
    payload = {
        "fabric_type": "polyester",
        "fabric_gsm": 155,
        "liquor_ratio": "1:8",
        "target_L": 71.2,
        "target_a": -7.9,
        "target_b": 62.8,
    }
    response = client.post("/api/v1/predict-recipe", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["dye_class"] == "disperse"
    assert data["product_range"] == "Disperse Dyes"
    assert data["salt_g_per_l"] == 0.0
    assert data["dispersing_agent_g_per_l"] > 0
    assert data["temperature_c"] == 130


def test_invalid_cie_lab_rejected(client):
    bad_payload = {
        "fabric_type": "cotton",
        "fabric_gsm": 180,
        "target_L": 150.0,
        "target_a": 20.0,
        "target_b": 10.0,
    }
    response = client.post("/api/v1/predict-recipe", json=bad_payload)
    assert response.status_code == 422


def test_api_key_enforcement_when_configured(client, monkeypatch):
    monkeypatch.setenv("SMARTLAB_API_KEY", "super-secret-lab-key")
    payload = {
        "fabric_type": "cotton",
        "fabric_gsm": 180,
        "target_L": 43.2,
        "target_a": 50.1,
        "target_b": 17.5,
    }
    unauthorized = client.post("/api/v1/predict-recipe", json=payload)
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/api/v1/predict-recipe",
        json=payload,
        headers={"X-API-Key": "super-secret-lab-key"},
    )
    assert authorized.status_code == 200


def test_evaluation_metrics_and_history(client):
    eval_resp = client.get("/api/v1/metrics/evaluate")
    assert eval_resp.status_code == 200
    metrics = eval_resp.json()
    assert metrics["evaluated_samples"] >= 13
    assert metrics["accuracy_pct"] >= 90.0
    assert metrics["lab_trial_reduction_pct"] >= 35.0

    hist_resp = client.get("/api/v1/predictions")
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) >= 1


def test_lab_feedback_submission_and_404(client):
    pred_resp = client.post(
        "/api/v1/predict-recipe",
        json={
            "fabric_type": "linen",
            "fabric_gsm": 190,
            "liquor_ratio": "1:10",
            "target_L": 59.5,
            "target_a": 4.5,
            "target_b": -21.8,
        },
    )
    assert pred_resp.status_code == 200
    pred_id = pred_resp.json()["prediction_id"]

    fb_resp = client.post(
        f"/api/v1/predictions/{pred_id}/feedback",
        json={"actual_delta_e": 0.72, "actual_lab_trials": 3},
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["actual_delta_e"] == 0.72
    assert fb_resp.json()["actual_lab_trials"] == 3

    missing = client.post(
        "/api/v1/predictions/999999/feedback",
        json={"actual_delta_e": 0.5, "actual_lab_trials": 2},
    )
    assert missing.status_code == 404
