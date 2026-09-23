# Pilot threat model

Scope: invite-only text tutoring API, existing hosted model, official-document web search. Learner text and retrieved pages are untrusted. The model has no shell, file-write, credential-read or general-purpose execution tool.

| Threat | Implemented control | Verification / remaining boundary |
| --- | --- | --- |
| Stolen caller key | Per-caller random key hashes; persistent revocation; caller quotas | Tests reject revoked and wrong keys. Operators must practise rotation and revoke leaks. |
| Repeated paid calls | Atomic per-caller/global admission, daily/minute counts and shared concurrency leases | Tests use real Redis in CI. Persistent noeviction storage and edge abuse controls require deployment configuration. |
| Quota bypass through more workers | Shared Redis counters and server time | Cross-client/concurrent admission tests; Redis recovery needs conservative reconciliation. |
| Missing security state | Fail-closed pilot configuration, initialization marker and store outage handling | Tests cover missing/invalid settings and store failure. Do not silently downgrade to demo mode. |
| Oversized/slow request body | 16 KiB actual body cap and five-second read deadline | Local regression tests; platform connection limits are still required against volumetric denial of service. |
| Provider outage or runaway retries | Async deadline, SDK retries disabled, output/tool-call bounds, pause switch | Injected timeout/rate/auth/network failures. Timeout cannot guarantee remote work was cancelled. |
| Prompt injection | Pre-model patterns, trusted instructions separated from input, narrowly configured web tool, no execution tools | Pattern tests and tool-contract tests are useful but not proof against every injection. Live adversarial answer-quality evaluation remains required. |
| Misleading citations | Exact parsed HTTPS host policy in runtime and evaluator; reject empty/incomplete answers | Tests reject deceptive hosts, credentials, query/path tricks and missing sources. Host approval does not prove factual correctness or prevent every misleading sentence in answer text. |
| Secret leakage | Caller hashes, private environment variables, no keys in prompts/logs, generic errors, history scan | Test payload/log checks and Gitleaks; operator screenshots/debug logging remain risks. |
| Vulnerable dependencies | Hash-locked runtime, dependency and image scans, non-root container | CI gates high/critical image findings and known Python advisories; scans do not prove absence of vulnerabilities. |
| Bad deployment or data loss | Separate staging, documented pause/rollback/restore procedures | Actual cloud drills and release access settings remain launch gates. |

Trust boundaries: caller → HTTPS API; API → Redis; API → provider; provider → retrieved documentation; operator → deployment/secrets. Use separate credentials and restricted access at each applicable boundary. Caller identifiers must be opaque IDs, not emails or real names.

This candidate does not include public signup, payment processing, per-user document storage, organisation tenancy or code execution. Add a new threat review before introducing any of them.
