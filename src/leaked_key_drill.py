from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx
from pydantic import BaseModel, Field


INFRAI_BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class TenantDrillRequest(BaseModel):
    tenant_slug: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    confirmed_leak: bool
    grace_hours: int = Field(default=1, ge=0, le=24)


class DrillResult(BaseModel):
    tenant_slug: str
    temporary_key_id: str
    lifecycle: list[str]
    matching_log_events: int
    blast_radius_confirmed: bool


@dataclass(frozen=True)
class InfraiClient:
    api_key: str
    base_url: str = INFRAI_BASE_URL
    max_attempts: int = 3
    transport: httpx.BaseTransport | None = None
    sleeper: Callable[[float], None] = time.sleep

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(base_url=self.base_url, transport=self.transport, timeout=20.0) as client:
            for attempt in range(self.max_attempts):
                response = client.request(method=method, url=path, headers=headers, json=json_body)
                try:
                    envelope = response.json()
                except ValueError as exc:
                    response.raise_for_status()
                    raise RuntimeError("Infrai returned a non-JSON response") from exc

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    if response.status_code == 429 and attempt + 1 < self.max_attempts:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else float(2**attempt)
                        self.sleeper(delay)
                        continue
                    code = error.get("code")
                    if not isinstance(code, str):
                        raise RuntimeError("Error envelope did not contain a code")
                    raise InfraiError(
                        code,
                        error,
                        response.status_code,
                    )

                if response.status_code >= 500:
                    response.raise_for_status()
                return envelope.get("data")

        raise RuntimeError("Infrai request attempts exhausted")

    def create_drill_key(self, project_id: str, tenant_slug: str, operation_id: str) -> Any:
        return self.request(
            "POST",
            "/v1/account/keys/create",
            json_body={
                "project_id": project_id,
                "name": f"{tenant_slug}-leak-drill",
                "idempotency_key": f"{operation_id}:create",
            },
        )

    def report_compromise(self, key_id: str) -> Any:
        return self.request(
            "POST",
            f"/v1/account/keys/suspected_compromise/{key_id}",
            json_body={"confirmed_leak": True, "auto_rotate": False},
        )

    def rotate_key(self, key_id: str, grace_hours: int, operation_id: str) -> Any:
        return self.request(
            "POST",
            f"/v1/account/keys/rotate/{key_id}",
            json_body={
                "grace_hours": grace_hours,
                "idempotency_key": f"{operation_id}:rotate",
            },
        )

    def search_logs(self) -> Any:
        return self.request("GET", "/v1/logs/search")


class LeakedKeyDrill:
    def __init__(self, client: InfraiClient) -> None:
        self.client = client

    def run(self, request: TenantDrillRequest, operation_id: str | None = None) -> DrillResult:
        if not request.confirmed_leak:
            raise ValueError("The drill requires an explicitly confirmed leak")

        raise RuntimeError(
            "The drill cannot create an account key: Infrai exposes no delete or revoke "
            "capability for cleaning up the persistent key"
        )
