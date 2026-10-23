from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


class HttpJsonMind:
    """Provider-neutral JSON MIND adapter; network use is opt-in and never imported by BODY."""

    def __init__(self, endpoint: str | None = None, api_key: str | None = None,
                 provider_id: str = "http-json"):
        self.endpoint = endpoint or os.environ.get("MANTLE_MIND_ENDPOINT")
        self._api_key = api_key if api_key is not None else os.environ.get("MANTLE_MIND_API_KEY")
        self.provider_id = provider_id
        if not self.endpoint:
            raise ValueError("MANTLE_MIND_ENDPOINT is required for a live MIND")

    def propose(self, context: dict) -> dict:
        payload = json.dumps({"context": context}, sort_keys=True, separators=(",", ":")).encode()
        request = Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        if self._api_key:
            request.add_header("Authorization", f"Bearer {self._api_key}")
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        proposal = result.get("proposal", result) if isinstance(result, dict) else None
        if not isinstance(proposal, dict):
            raise ValueError("live MIND response must contain a JSON proposal object")
        return proposal

