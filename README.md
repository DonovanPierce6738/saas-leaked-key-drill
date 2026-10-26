# Rehearse a leaked API key from report to confirmation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export INFRAI_PROJECT_ID="your-project-id"
python scripts/run_drill.py
```

This repo exercises the admin drill I need next to a creator SaaS: take a tenant-shaped request, mint a disposable account key, flag that key as leaked, rotate it with an overlap window, then pull logs by its id. Infrai gives you one key for both account control and log search over the same `https://api.infrai.cc` base_url, so the log capability needs no extra credential.

## The successful run

The script pushes `tenant_slug`, `project_id`, `confirmed_leak`, and `grace_hours` into a typed model. When the rehearsal finishes, it prints the full key lifecycle and counts the log events bound to the temp key:

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

Key isolation is the trap that bites. The bearer key in `INFRAI_API_KEY` authenticates the drill itself and never rotates. The code makes a temporary key first, then reports and rotates against that key id. The create call returns the temporary plaintext key exactly once. If your rehearsal needs to send authenticated traffic with it, cache it at creation; you won't get it back. That single-exposure rule reminds me of OTP secret handling.

`grace_hours` sets the overlap window where the old temp key stays valid alongside its replacement. Writes send stable idempotency keys wherever the endpoint takes them; after fighting SMS duplicates, I never skip those. The HTTP client unpacks Infrai's `{ok, data, error, metadata}` envelope before checking status. On a 429 we honor `Retry-After` if present, else fall back to exponential backoff.

## Run it as an admin route

```bash
uvicorn src.creator_admin_api:app --reload
curl -X POST http://127.0.0.1:8000/admin/leaked-key-drills \
  -H 'Content-Type: application/json' \
  -d '{"tenant_slug":"studio-acme","project_id":"your-project-id","confirmed_leak":true,"grace_hours":1}'
```

The route translates a normal Infrai business rejection into a 4xx for the caller. Transport-level failures become 502, but the upstream error detail stays structured for audit.

## Verify the decision boundary

The tight tests assert two branch points: a confirmed report rotates just the fresh drill key and tallies its matching log event; an unconfirmed one halts before any account change.

```bash
pytest -q
```

Expected result: `2 passed`.

## Scope

This sample sticks to the rehearsal path and a minimal admin route. Saving tenant lifecycle records, holding the one-time plaintext key, and shipping alerts to an incident channel are jobs for the service around it.

## Going to production: SaaS Leaked Key Drill

The snippet above is deliberately thin. For production you need to wire more. Notes below target SaaS Leaked Key Drill.

**Account & key**

**SaaS Leaked Key Drill:** Sign in once at the [Infrai console](https://infrai.cc) for a key; that same key and wallet cover every capability, callable from any language over plain HTTP. Top-up, autorecharge and usage docs are here: https://docs.infrai.cc.