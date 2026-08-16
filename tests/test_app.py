from fastapi.testclient import TestClient

from app import app, CUSTOMERS

client = TestClient(app)


def test_mock_data_has_50_customers():
    assert len(CUSTOMERS) == 50
    assert "12345" in CUSTOMERS
    assert set(CUSTOMERS["12345"]["accounts"]) == {"savings", "checking"}


def test_member_search_success():
    response = client.post(
        "/legacy/member-search",
        data={"member_number": "12345", "test_condition": "normal"},
    )
    assert response.status_code == 200
    assert "12345" in response.text
    assert "Regular Savings" in response.text
    assert "Current Balance" not in response.text


def test_member_not_found_is_business_outcome():
    response = client.post(
        "/legacy/member-search",
        data={"member_number": "99999", "test_condition": "normal"},
    )
    assert response.status_code == 200
    assert "MEMBER_NOT_FOUND" in response.text


def test_account_detail_exposes_balance():
    response = client.get("/legacy/account/12345/savings")
    assert response.status_code == 200
    assert "Current Balance" in response.text
    assert "$" in response.text


def test_permission_denied_is_explicit_failure():
    response = client.post(
        "/legacy/member-search",
        data={"member_number": "12345", "test_condition": "permission_denied"},
    )
    assert response.status_code == 200
    assert "PERMISSION_DENIED" in response.text
