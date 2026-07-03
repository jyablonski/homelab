def test_domain_endpoint_allows_requests_when_no_api_key_configured(test_client):
    response = test_client.get("/v1/events/upcoming")

    assert response.status_code == 200


def test_domain_endpoint_rejects_missing_api_key(api_key_client):
    response = api_key_client.get("/v1/events/upcoming")

    assert response.status_code == 401


def test_domain_endpoint_rejects_wrong_api_key(api_key_client):
    response = api_key_client.get(
        "/v1/events/upcoming",
        headers={"X-Homelab-Api-Key": "wrong-key"},
    )

    assert response.status_code == 401


def test_domain_endpoint_accepts_correct_api_key(api_key_client, api_key_env):
    response = api_key_client.get(
        "/v1/events/upcoming",
        headers={"X-Homelab-Api-Key": api_key_env},
    )

    assert response.status_code == 200


def test_health_endpoint_ignores_api_key_requirement(api_key_client):
    response = api_key_client.get("/healthz")

    assert response.status_code == 200
