from __future__ import annotations


def test_integrations_platforms_route_is_registered(client):
    response = client.get("/api/integrations/platforms")
    assert response.status_code == 200
    body = response.json()
    assert "platforms" in body


def test_crm_hub_providers_route_is_registered(client):
    response = client.get("/api/crm-hub/providers")
    assert response.status_code == 200
    body = response.json()
    assert "providers" in body

