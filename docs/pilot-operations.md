# Invite-only pilot: operator checklist

Status: implementation candidate. This document does not certify a live production service. Keep the existing demo available while verifying the pilot separately.

## I. Fixed scope for this candidate

1. Up to five invited adult learners, API access only; each gets a different random key.
2. No code execution, uploads, chat-history storage, public signup or payment processing.
3. Proposed limits: five requests/minute and 20/day per caller; 50/day across all callers; two simultaneous admitted requests; 45-second provider deadline; 1,200 output tokens and at most two built-in tool calls per provider request. Failed and refused admitted requests still consume quota. Windows use Redis server time; day means UTC day. Fixed windows can permit a burst across their boundary.
4. These defaults bound activity, not a dollar bill. Provider processing might continue after a client timeout. Token estimates exclude search/tool fees. Set a real spending budget and account alerts before opening access.
5. The service owner must record acceptable latency, availability, monthly spend and a support contact before launch. Those business decisions remain open.

## II. Prepare private configuration

1. Use the reviewed Git revision and Python 3.12. Install the hash-locked runtime with `python -m pip install --require-hashes -r requirements.lock`, then development dependencies with `python -m pip install --require-hashes -r requirements-dev.lock`.
2. Copy `.env.pilot.example` to a new private `.env.pilot`. Keep `TUTOR_MODE=pilot`. Demo mode preserves the original shared-key workflow and does not enforce Redis quotas; it is not the pilot configuration.
3. Run `python -m scripts.pilot_admin issue --caller learner-01` on your trusted machine. Save the printed caller key privately. Place only the printed ID/hash entry in `TUTOR_CALLERS_JSON`. Repeat for each learner and combine entries in one JSON object. Do not commit keys or send them in screenshots.
4. Set provider credentials/model privately. A caller key is separate from the provider key. Production must not accept the old shared `TUTOR_ACCESS_KEY`.
5. For cloud use, select a dedicated, persistent Redis service with `noeviction`, private networking or verified TLS (`rediss://`), restricted access and backups. Use separate staging/production stores and namespaces. Application-worker restarts must not reset counters. Free ephemeral stores cannot establish durable quota enforcement.
6. Limit Redis credentials to this application's key namespace and required commands (get/set, mget, exists, hash/set/sorted-set operations, expire, time and eval). An operator credential may additionally administer backups. Never expose Redis directly to the public internet.

## III. Local staging rehearsal

1. Fill `.env.pilot` with caller hashes and the provider configuration; Compose supplies the internal Redis URL.
2. Run `docker compose -f compose.pilot.yml up --build -d`. Redis is private to the Docker network and persists to a named volume. Do not use `down -v` during a recovery rehearsal.
3. Run `docker compose -f compose.pilot.yml exec tutor python -m scripts.pilot_admin initialize`. A new store starts paused. Existing stores/counters are preserved.
4. Run `docker compose -f compose.pilot.yml exec tutor python -m scripts.pilot_admin enable`.
5. In Ubuntu, run `read -rsp 'Caller key: ' TUTOR_CALL_KEY`, then paste the saved caller key at the hidden prompt. Run `export TUTOR_CALL_KEY` so the smoke script can read it.
6. Run `python -m scripts.smoke http://127.0.0.1:10000`. This checks health, missing-key rejection and an authorised guardrail refusal without model calls.
7. When ready for one paid request, repeat with `--live-model`. Then run `unset TUTOR_CALL_KEY`.
8. Check `/ready`: it checks configuration, store initialization and the pause switch without a paid request. It does not prove provider credentials work. `/health` remains basic liveness, even while the pilot is paused.

## IV. Release checks and cloud configuration

1. Require successful CI for the exact candidate commit: deterministic tests with real Redis, dependency audit, repository-history secret scan, Docker build/smoke checks and image scan. Investigate scan failures; do not remove gates to obtain a pass.
2. Configure GitHub environment `tutor-release` with its own limited provider key and `OPENAI_MODEL` variable. Do not supply learner keys. Run the manual `Release evaluation` workflow for the exact candidate revision with paid calls explicitly selected. Review all 15 results and retain the report. No live evaluation is run implicitly by a PR.
3. The prepared `render.pilot.yaml` defines a separate web service and private persistent Key Value store. Applying it incurs an estimated $17/month in compute charges at prices checked on 23 September 2026, excluding OpenAI, taxes and extra usage; obtain budget approval first. It starts with model calls disabled. Disable Render automatic deployment for the pilot service. Passing ordinary CI alone is not the complete release gate. Restrict deployment access to the operator; manually deploy only the revision with passing CI, live evaluation and staging evidence. Dashboard configuration is not enforced by this repository and must be checked.
4. Set pilot environment variables privately in Render, including its durable Redis URL and caller-hash JSON. Health Check Path is `/health`. For the Blueprint's private Redis connection, use the new paid service's Render Shell: run `python -m scripts.pilot_admin initialize`, then `python -m scripts.pilot_admin enable`. The shell inherits the private environment. Keep Redis public access disabled. After no-model checks, deliberately set `TUTOR_MODEL_ENABLED=true` and redeploy before the paid smoke check.
5. Run the smoke script against the HTTPS pilot URL, first without and then with `--live-model`. Record the deployed revision and request IDs. The HTTPS script refuses redirects rather than forwarding a caller key to a different destination.
6. Configure platform alerts for repeated 5xx, readiness failure, unusual 403/429 traffic and latency. Connect a real notification destination and trigger a controlled test. Logs alone are not an alert system. Set provider spend alerts separately.
7. Record a small authorised load trial against the agreed workload. CI tests concurrent admission; it does not establish cloud throughput or an uptime SLA.

## V. Incident and recovery procedures

For private cloud Redis, run the commands below in the service's trusted Render Shell and omit `--env-file .env.pilot`; the server environment supplies the connection. The env-file form is for a trusted operator machine that already has permitted network access. Never open Redis publicly just to run an operator command.

1. **Runaway usage/provider incident:** `python -m scripts.pilot_admin pause --env-file .env.pilot`. New pilot admissions return 503; existing provider calls may finish. `/health` remains available. `TUTOR_MODEL_ENABLED=false` is a second switch, requiring deployment/config reload. Neither switch reverses charges already incurred.
2. **Leaked caller key:** `python -m scripts.pilot_admin revoke --caller learner-01 --env-file .env.pilot`. Verify the old key returns 403. Generate a replacement, update the same caller ID's hash in server configuration, deploy, then restore that caller. Keeping the ID retains its usage bucket. Never merely generate a new key without replacing the accepted hash.
3. **Leaked provider key:** pause; revoke/rotate it in the provider account; update private cloud configuration; verify health, refusal and one paid answer; then enable. Inspect billing and safe request logs.
4. **Bad application release:** pause first. Deploy the previous known-good pilot revision with the same persistent store and namespace. Verify missing/revoked keys, quota enforcement and one authorised refusal before enabling. Do not roll back to a shared-key-only demo as the pilot recovery target.
5. **Store outage/loss:** admission fails closed. Restore a verified backup while access remains paused. A missing initialization marker does not auto-create a new budget. Do not initialize an empty replacement just to clear a failure; restoring an old snapshot can also restore old counters and revocations. Reconcile usage/revocations conservatively before enabling.
6. **Backup rehearsal:** take a provider-supported consistent snapshot, restore to a separate private staging store, and verify caller revocation and current-day usage. Record recovery time and possible data loss. Local Compose uses AOF with appendfsync always, but that alone is not a tested off-host backup.

## VI. Logs, privacy and evidence

Request logs contain generated request ID, opaque caller ID, route category, status and duration. Model logs contain token counts and optional operator-configured token-cost estimates. They exclude request bodies, response text and keys. Uvicorn access logging is disabled in the image to avoid recording arbitrary query strings. Do not enable raw HTTP/provider debug logs in production.

No local chat history is stored. `store=False` requests that Responses objects are not stored for later API retrieval; it does not establish zero provider retention. Review actual provider/hosting retention settings and give invited learners a clear notice. Set a log retention period (proposed seven days) and verify deletion in the hosting account. Evaluation artifacts use synthetic questions and seven-day workflow retention.

For each live step record: date, revision, command/check, observed result and request ID where applicable. Never record secret values. Outstanding account-dependent evidence: durable store configuration, hosting cost approval, cloud pilot rollout, all-scenario live evaluation, delivered alert, cloud load trial, backup restore and rollback drill.
