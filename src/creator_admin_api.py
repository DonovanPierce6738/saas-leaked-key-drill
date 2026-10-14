import os

from fastapi import FastAPI, HTTPException

from .leaked_key_drill import DrillResult, InfraiClient, InfraiError, LeakedKeyDrill, TenantDrillRequest


app = FastAPI(title="Creator SaaS leaked-key drill")


@app.post("/admin/leaked-key-drills", response_model=DrillResult)
def run_leaked_key_drill(request: TenantDrillRequest) -> DrillResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")

    try:
        return LeakedKeyDrill(InfraiClient(api_key=api_key)).run(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
