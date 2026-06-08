"""API client for Analyst Lens backend."""
from datetime import datetime
from typing import Any

import httpx

from config import API_BASE_URL, API_PREFIX


class APIClient:
    def __init__(self):
        self.base_url = f"{API_BASE_URL}{API_PREFIX}"
        self.token: str | None = None

    @property
    def headers(self) -> dict[str, str]:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def request(
        self, 
        method: str, 
        path: str, 
        json: dict | None = None,
        params: dict | None = None,
        timeout: int = 30
    ) -> Any:
        """Generic request method for flexible API calls."""
        url = f"{self.base_url}{path}"
        resp = httpx.request(
            method=method,
            url=url,
            json=json,
            params=params,
            headers=self.headers,
            timeout=timeout
        )
        resp.raise_for_status()
        try:
            return resp.json()
        except:
            return {}

    def register(self, email: str, password: str, full_name: str, role: str = "analyst") -> dict[str, Any]:
        resp = httpx.post(
            f"{self.base_url}/auth/register",
            json={"email": email, "password": password, "full_name": full_name, "role": role},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def login(self, email: str, password: str) -> str:
        resp = httpx.post(
            f"{self.base_url}/auth/login",
            data={"username": email, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        return self.token

    def get_me(self) -> dict[str, Any]:
        resp = httpx.get(f"{self.base_url}/auth/me", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def list_events(self) -> list[dict[str, Any]]:
        resp = httpx.get(f"{self.base_url}/events", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def create_event(
        self,
        title: str,
        summary: str,
        region: str,
        theme: str,
        severity: int,
        confidence: float,
        occurred_at: datetime,
        country: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "summary": summary,
            "region": region,
            "country": country,
            "theme": theme,
            "severity": severity,
            "confidence": confidence,
            "occurred_at": occurred_at.isoformat(),
            "tags": tags or [],
            "sources": [],
        }
        resp = httpx.post(f"{self.base_url}/events", json=payload, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_event(self, event_id: int) -> dict[str, Any]:
        resp = httpx.get(f"{self.base_url}/events/{event_id}", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def add_timeline_entry(self, event_id: int, description: str) -> dict[str, Any]:
        resp = httpx.post(
            f"{self.base_url}/events/{event_id}/timeline",
            params={"description": description},
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def generate_outlooks(self, horizons: list[int] | None = None) -> list[dict[str, Any]]:
        payload = {"horizons": horizons or [24, 48, 72]}
        resp = httpx.post(f"{self.base_url}/outlooks/generate", json=payload, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def list_outlooks(self) -> list[dict[str, Any]]:
        resp = httpx.get(f"{self.base_url}/outlooks", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def list_scenarios(self) -> list[dict[str, Any]]:
        resp = httpx.get(f"{self.base_url}/scenarios", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def create_scenario(
        self,
        name: str,
        case_type: str,
        triggers: str,
        impacts: str,
        time_horizon_hours: int,
        probability: float | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "case_type": case_type,
            "triggers": triggers,
            "impacts": impacts,
            "time_horizon_hours": time_horizon_hours,
            "probability": probability,
        }
        resp = httpx.post(f"{self.base_url}/scenarios", json=payload, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def health_check(self) -> bool:
        try:
            resp = httpx.get(f"{API_BASE_URL}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

