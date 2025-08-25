from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .utils.logger import get_logger


class DirectusError(Exception):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise DirectusError(f"Missing required environment variable: {name}")
    return value


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status in {429, 500, 502, 503, 504}
    if isinstance(exc, requests.RequestException):
        return True
    return False


@dataclass
class DirectusClient:
    base_url: str
    token: str
    session: requests.Session

    @classmethod
    def from_env(cls) -> DirectusClient:
        base_url = _required_env("DIRECTUS_URL").rstrip("/")
        token = _required_env("DIRECTUS_TOKEN")
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )
        return cls(base_url=base_url, token=token, session=session)

    def _items_url(self, collection: str) -> str:
        return f"{self.base_url}/items/{collection}"

    @retry(
        wait=wait_exponential_jitter(initial=0.5, max=8), stop=stop_after_attempt(5), reraise=True
    )
    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        resp = self.session.request(method, url, timeout=30, **kwargs)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            if _should_retry(e):
                raise
            # Attach response text for easier debugging
            body = None
            try:
                body = resp.text
            except Exception:
                body = None
            msg = (
                f"HTTP {resp.status_code} for {url}: {body}"
                if body
                else f"HTTP {resp.status_code} for {url}"
            )
            raise DirectusError(msg) from e
        return resp

    def get_debtors_to_enrich(self, limit: int) -> list[dict[str, Any]]:
        url = self._items_url("debtors")
        # Filter enrichment_status in ['pending','partial']
        params = {
            "filter": json.dumps({"enrichment_status": {"_in": ["pending", "partial"]}}),
            "limit": limit,
        }
        resp = self._request("GET", url, params=params)
        payload = resp.json()
        return payload.get("data", [])

    def create_row(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        url = self._items_url(collection)
        resp = self._request("POST", url, json=data)
        return resp.json().get("data")

    def update_row(self, collection: str, id: Any, data: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._items_url(collection)}/{id}"
        resp = self._request("PATCH", url, json=data)
        return resp.json().get("data")

    def list_related(
        self, collection: str, filters: dict[str, Any], limit: int = 100
    ) -> list[dict[str, Any]]:
        url = self._items_url(collection)
        params = {
            "filter": json.dumps(filters),
            "limit": limit,
        }
        resp = self._request("GET", url, params=params)
        return resp.json().get("data", [])

    def delete_row(self, collection: str, id_or_filter: Any) -> None:
        """Delete a single row by id, or multiple rows by filter."""
        if isinstance(id_or_filter, dict):
            # Bulk delete via filter
            url = self._items_url(collection)
            params = {"filter": json.dumps(id_or_filter)}
            self._request("DELETE", url, params=params)
        else:
            # Delete by id
            url = f"{self._items_url(collection)}/{id_or_filter}"
            self._request("DELETE", url)


def get_client_and_logger() -> tuple[DirectusClient, Any]:
    dx = DirectusClient.from_env()
    log = get_logger()
    return dx, log
