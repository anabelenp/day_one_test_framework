#!/usr/bin/env python3
"""
Mock Response Loader for Day-1 Framework

Utility module for loading mock API responses from JSON files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class MockResponseLoader:
    """Loads mock responses from JSON files"""

    def __init__(self, base_path: Optional[str] = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path(__file__).parent.parent / "mock_responses"

    def load(self, resource: str, action: str = "list") -> Dict[str, Any]:
        """Load a mock response from JSON file"""
        file_path = self.base_path / resource / f"{action}.json"

        if not file_path.exists():
            return self._default_response(resource)

        with open(file_path, "r") as f:
            return json.load(f)

    def load_event(self, event_id: str) -> Dict[str, Any]:
        """Load a specific event by ID"""
        file_path = self.base_path / "events" / f"{event_id}.json"

        if not file_path.exists():
            return self._default_response("event")

        with open(file_path, "r") as f:
            return json.load(f)

    def _default_response(self, resource: str) -> Dict[str, Any]:
        """Return a default response when file not found"""
        return {
            "status": "success",
            "data": {
                resource: [],
                "pagination": {"page": 1, "per_page": 50, "total": 0, "total_pages": 0},
            },
            "meta": {
                "request_id": "mock_req_001",
                "timestamp": "2024-01-15T00:00:00Z",
                "version": "v2",
            },
        }

    def get_available_events(self) -> list[str]:
        """Get list of available event IDs"""
        events_dir = self.base_path / "events"
        if not events_dir.exists():
            return []
        return [f.stem for f in events_dir.glob("*.json") if f.stem != "list"]

    def get_available_policies(self) -> list[str]:
        """Get list of available policy IDs"""
        policies_dir = self.base_path / "policies"
        if not policies_dir.exists():
            return []
        return [f.stem for f in policies_dir.glob("*.json") if f.stem != "list"]

    def get_available_users(self) -> list[str]:
        """Get list of available user IDs"""
        users_dir = self.base_path / "users"
        if not users_dir.exists():
            return []
        return [f.stem for f in users_dir.glob("*.json") if f.stem != "list"]


_loader = None


def get_mock_loader() -> MockResponseLoader:
    """Get the global mock response loader"""
    global _loader
    if _loader is None:
        _loader = MockResponseLoader()
    return _loader


def load_mock_events() -> Dict[str, Any]:
    """Load mock events response"""
    return get_mock_loader().load("events")


def load_mock_policies() -> Dict[str, Any]:
    """Load mock policies response"""
    return get_mock_loader().load("policies")


def load_mock_users() -> Dict[str, Any]:
    """Load mock users response"""
    return get_mock_loader().load("users")


def load_mock_event(event_id: str) -> Dict[str, Any]:
    """Load a specific mock event by ID"""
    return get_mock_loader().load_event(event_id)


if __name__ == "__main__":
    loader = MockResponseLoader()

    print("Available events:", loader.get_available_events())
    print("Available policies:", loader.get_available_policies())
    print("Available users:", loader.get_available_users())

    events = load_mock_events()
    print(f"\nLoaded {len(events.get('data', {}).get('events', []))} events")
