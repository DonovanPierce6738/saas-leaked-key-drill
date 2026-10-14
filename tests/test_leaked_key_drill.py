from typing import Any

import pytest

from src.leaked_key_drill import LeakedKeyDrill, TenantDrillRequest


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def create_drill_key(self, project_id: str, tenant_slug: str, operation_id: str) -> dict[str, str]:
        self.calls.append(("create", project_id, tenant_slug, operation_id))
        return {"id": "key_drill_42", "key": "one-time-plaintext-value"}

    def report_compromise(self, key_id: str) -> dict[str, bool]:
        self.calls.append(("report", key_id))
        return {"reported": True}

    def rotate_key(self, key_id: str, grace_hours: int, operation_id: str) -> dict[str, bool]:
        self.calls.append(("rotate", key_id, grace_hours, operation_id))
        return {"rotated": True}

    def search_logs(self) -> dict[str, list[dict[str, str]]]:
        self.calls.append(("logs",))
        return {"items": [{"api_key_id": "key_drill_42"}, {"api_key_id": "another_key"}]}


def test_confirmed_leak_refuses_key_without_cleanup_capability() -> None:
    client = RecordingClient()
    drill = LeakedKeyDrill(client)  # type: ignore[arg-type]
    request = TenantDrillRequest(
        tenant_slug="video-studio",
        project_id="project_7",
        confirmed_leak=True,
        grace_hours=2,
    )

    with pytest.raises(RuntimeError, match="no delete or revoke"):
        drill.run(request, operation_id="drill-001")

    assert client.calls == []


def test_unconfirmed_report_stops_before_account_changes() -> None:
    client = RecordingClient()
    request = TenantDrillRequest(
        tenant_slug="video-studio",
        project_id="project_7",
        confirmed_leak=False,
    )

    with pytest.raises(ValueError, match="explicitly confirmed"):
        LeakedKeyDrill(client).run(request, operation_id="drill-002")  # type: ignore[arg-type]

    assert client.calls == []
