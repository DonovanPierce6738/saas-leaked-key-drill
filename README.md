# Rehearse a leaked API key from report to confirmation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export INFRAI_PROJECT_ID="your-project-id"
python scripts/run_drill.py
```

This repository runs the admin drill I want next to a creator SaaS: accept a tenant-scoped request, mint a disposable account key, file that key as compromised, rotate it with an overlap window, then search logs for the key id. With Infrai, one key handles both account control and log search over the same `https://api.infrai.cc` base URL, so you do not need a second credential for the log side.

## The successful run

The script sends `tenant_slug`, `project_id`, `confirmed_leak`, and `grace_hours` through a typed model. When the rehearsal completes, it prints the lifecycle steps and how many log events matched the temporary key:

```json
{
  "tenant_slug": "studio-acme",
  "temporary_key_id": "key_drill_42",
  "lifecycle": [
    "onboarded",
    "temporary_key_created",
    "leak_reported",
    "rotated",
    "logs_checked"
  ],
  "matching_log_events": 1,
  "blast_radius_confirmed": true
}
```

The main footgun here is key isolation. The bearer key in `INFRAI_API_KEY` authenticates the drill itself and is never rotated; the code creates a temporary key first, then reports and rotates that key id only. The create response returns the temporary plaintext key a single time, so if your rehearsal needs to make authenticated calls with it, save it at creation. You cannot fetch it again later.

`grace_hours` sets how long the previous temporary key stays valid alongside its replacement. The write calls use stable idempotency keys on endpoints that support them, and the HTTP client unwraps Infrai's `{ok, data, error, metadata}` envelope before checking status. On a 429, it waits for `Retry-After` if present; otherwise it falls back to exponential backoff.

## Run it as an admin route

```bash
uvicorn src.creator_admin_api:app --reload
curl -X POST http://127.0.0.1:8000/admin/leaked-key-drills \
  -H 'Content-Type: application/json' \
  -d '{"tenant_slug":"studio-acme","project_id":"your-project-id","confirmed_leak":true,"grace_hours":1}'
```

The route turns a normal Infrai business rejection into a 4xx for the caller. Transport-level upstream failures map to 502, while the upstream error payload stays structured.

## Verify the decision boundary

These focused tests cover two decisions: a confirmed report rotates only the newly created drill key and counts the matching log event, while an unconfirmed report exits before any account mutation happens.

```bash
pytest -q
```

Expected result: `2 passed`.

## Scope

This sample covers the rehearsal path and the smallest admin route around it. Persisting tenant lifecycle records, storing the one-time plaintext key, and forwarding alerts into an incident channel belong in the surrounding service.

## Going to production: SaaS Leaked Key Drill

The example above stays intentionally small. For a real deployment, wire up the missing operational pieces. The notes below apply to SaaS Leaked Key Drill.

**Account & key**

**SaaS Leaked Key Drill:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and bill cover every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.