import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.leaked_key_drill import InfraiClient, LeakedKeyDrill, TenantDrillRequest


def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    project_id = os.environ.get("INFRAI_PROJECT_ID")
    if not api_key or not project_id:
        raise SystemExit("Set INFRAI_API_KEY and INFRAI_PROJECT_ID before running the drill")

    request = TenantDrillRequest(
        tenant_slug="studio-acme",
        project_id=project_id,
        confirmed_leak=True,
        grace_hours=1,
    )
    result = LeakedKeyDrill(InfraiClient(api_key=api_key)).run(request)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
