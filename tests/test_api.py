from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import create_app


def _get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_end_to_end_flow(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(database_url=f"sqlite:///{db_path}")
    client = TestClient(app)

    # Register analyst
    register_payload = {
        "email": "analyst@example.org",
        "password": "SecurePass123",
        "full_name": "Test Analyst",
        "role": "analyst",
    }
    register_resp = client.post("/api/v1/auth/register", json=register_payload)
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == register_payload["email"]

    # Login
    token = _get_token(client, register_payload["email"], register_payload["password"])
    headers = {"Authorization": f"Bearer {token}"}

    # Create event with new fields
    create_event_payload = {
        "title": "Naval transit disruption",
        "summary": "Increased patrol activity around a strategic chokepoint.",
        "region": "Middle East",
        "country": "N/A",
        "theme": "shipping",
        "sector": "energy",
        "risk_type": "operational",
        "severity": 4,
        "confidence": 0.74,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "tags": ["shipping", "energy", "chokepoint"],
        "sources": [
            {
                "name": "Licensed Intel Feed",
                "url": "https://example.org/report",
                "reliability": 0.8,
            }
        ],
    }

    event_response = client.post("/api/v1/events", json=create_event_payload, headers=headers)
    assert event_response.status_code == 201
    event_body = event_response.json()
    assert event_body["title"] == create_event_payload["title"]
    assert event_body["sector"] == "energy"
    assert event_body["risk_type"] == "operational"
    assert "shipping" in event_body["tags"]
    assert event_body["fingerprint"]
    assert len(event_body["timeline"]) == 1
    assert event_body["is_published"] is False
    event_id = event_body["id"]

    # Test search/filter
    search_resp = client.get("/api/v1/events", params={"region": "Middle East", "severity_min": 3}, headers=headers)
    assert search_resp.status_code == 200
    assert len(search_resp.json()) == 1

    # Publish event
    publish_resp = client.patch(f"/api/v1/events/{event_id}/publish", json={"publish": True}, headers=headers)
    assert publish_resp.status_code == 200
    assert publish_resp.json()["is_published"] is True
    assert publish_resp.json()["published_at"] is not None

    # Check published feed (no auth required for this endpoint)
    published_resp = client.get("/api/v1/events/published")
    assert published_resp.status_code == 200
    # Demo data includes 1 published event, plus the one we just created
    assert len(published_resp.json()) >= 1

    # Try duplicate detection
    dup_check = client.get(
        "/api/v1/events/check-duplicate",
        params={
            "title": create_event_payload["title"],
            "region": create_event_payload["region"],
            "occurred_at": create_event_payload["occurred_at"],
        },
        headers=headers,
    )
    assert dup_check.status_code == 200
    assert dup_check.json()["duplicate"] is True

    # Generate outlooks
    outlook_response = client.post("/api/v1/outlooks/generate", json={"horizons": [24, 48, 72]}, headers=headers)
    assert outlook_response.status_code == 200
    outlook_body = outlook_response.json()
    assert len(outlook_body) == 3
    assert outlook_body[0]["status"] == "draft"
    outlook_id = outlook_body[0]["id"]

    # Update outlook status
    status_resp = client.patch(
        f"/api/v1/outlooks/{outlook_id}/status",
        json={"status": "reviewed", "reviewer_notes": "Approved by senior analyst"},
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "reviewed"
    assert status_resp.json()["reviewed_at"] is not None

    # Publish outlook
    publish_outlook_resp = client.patch(
        f"/api/v1/outlooks/{outlook_id}/status",
        json={"status": "published"},
        headers=headers,
    )
    assert publish_outlook_resp.status_code == 200
    assert publish_outlook_resp.json()["status"] == "published"

    # Check published outlooks
    pub_outlooks = client.get("/api/v1/outlooks/published")
    assert pub_outlooks.status_code == 200
    assert len(pub_outlooks.json()) >= 1

    # Create scenario template
    template_payload = {
        "name": "Regional Conflict Template",
        "case_type": "baseline",
        "triggers": "Military mobilization or border incidents",
        "impacts": "Supply chain disruption and market volatility",
        "time_horizon_hours": 168,
        "is_template": True,
    }
    template_resp = client.post("/api/v1/scenarios", json=template_payload, headers=headers)
    assert template_resp.status_code == 201
    assert template_resp.json()["is_template"] is True
    template_id = template_resp.json()["id"]

    # Clone from template
    clone_resp = client.post(
        f"/api/v1/scenarios/{template_id}/clone",
        json={"name": "Gulf Shipping Scenario"},
        headers=headers,
    )
    assert clone_resp.status_code == 201
    assert clone_resp.json()["name"] == "Gulf Shipping Scenario"
    assert clone_resp.json()["template_id"] == template_id
    assert clone_resp.json()["is_template"] is False

    # List templates
    templates_resp = client.get("/api/v1/scenarios/templates", headers=headers)
    assert templates_resp.status_code == 200
    assert len(templates_resp.json()) >= 1

    # Create regular scenario
    scenario_payload = {
        "name": "Shipping Pressure Baseline",
        "case_type": "baseline",
        "triggers": "Sustained military signaling and inspection delays",
        "impacts": "Higher transit costs and delayed cargo rotations",
        "time_horizon_hours": 72,
        "probability": 0.58,
    }
    scenario_response = client.post("/api/v1/scenarios", json=scenario_payload, headers=headers)
    assert scenario_response.status_code == 201
    assert scenario_response.json()["case_type"] == "baseline"

    # Test AskAnything
    ask_resp = client.post(
        "/api/v1/ask",
        json={"question": "What are the key shipping risks in the Middle East?"},
        headers=headers,
    )
    assert ask_resp.status_code == 200
    ask_body = ask_resp.json()
    assert "answer" in ask_body
    assert "confidence" in ask_body
    assert "sentiment" in ask_body

    # Check Q&A history
    history_resp = client.get("/api/v1/ask/history", headers=headers)
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1

    # Test source verification
    # First get the event sources
    event_detail = client.get(f"/api/v1/events/{event_id}", headers=headers)
    assert event_detail.status_code == 200
    sources = event_detail.json()["sources"]
    assert len(sources) == 1
    source_id = sources[0]["id"]

    # Get sources with verification status
    sources_resp = client.get(f"/api/v1/stories/events/{event_id}/sources", headers=headers)
    assert sources_resp.status_code == 200
    assert sources_resp.json()[0]["verification_status"] == "unverified"

    # Verify the source
    verify_resp = client.post(
        f"/api/v1/stories/sources/{source_id}/verify",
        json={
            "source_id": source_id,
            "status": "verified",
            "verification_method": "cross-reference",
            "verification_notes": "Confirmed by secondary source",
            "verified_url": "https://example.org/evidence"
        },
        headers=headers,
    )
    assert verify_resp.status_code == 201
    assert verify_resp.json()["status"] == "verified"

    # Check verification status for event
    verif_status = client.get(f"/api/v1/stories/verification-status?event_ids={event_id}", headers=headers)
    assert verif_status.status_code == 200
    assert verif_status.json()["all_sources_verified"] is True

    # Generate news story from event
    story_gen_resp = client.post(
        "/api/v1/stories/generate",
        json={
            "event_ids": [event_id],
            "include_business_implications": True,
            "include_recommended_actions": True
        },
        headers=headers,
    )
    assert story_gen_resp.status_code == 201
    story = story_gen_resp.json()
    assert story["headline"]
    assert story["body"]
    assert story["status"] == "draft"
    assert story["all_sources_verified"] is True
    story_id = story["id"]

    # Get story
    get_story = client.get(f"/api/v1/stories/{story_id}", headers=headers)
    assert get_story.status_code == 200

    # Update story status - submit for review
    review_resp = client.patch(
        f"/api/v1/stories/{story_id}/status",
        json={"status": "review"},
        headers=headers,
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "review"

    # Approve story
    approve_resp = client.patch(
        f"/api/v1/stories/{story_id}/status",
        json={"status": "approved", "reviewer_notes": "Looks good"},
        headers=headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # Publish story
    publish_story_resp = client.patch(
        f"/api/v1/stories/{story_id}/status",
        json={"status": "published"},
        headers=headers,
    )
    assert publish_story_resp.status_code == 200
    assert publish_story_resp.json()["status"] == "published"
    assert publish_story_resp.json()["published_at"] is not None

    # Check published stories feed (no auth required)
    pub_stories = client.get("/api/v1/stories/published")
    assert pub_stories.status_code == 200
    assert len(pub_stories.json()) >= 1

    # List all stories with filter
    all_stories = client.get("/api/v1/stories?verified_only=true", headers=headers)
    assert all_stories.status_code == 200
    assert len(all_stories.json()) >= 1

