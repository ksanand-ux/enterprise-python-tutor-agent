# Tutor production readiness

The protected portfolio milestone is complete. The invite-only pilot is a separate release candidate and is not yet cleared for live users. This checklist records implementation separately from deployment evidence.

## I. Scope

Assumed first target: up to five invited adult learners using an API, with no code execution, uploads, public signup or stored chat history. The operator must still confirm the hosting/API budget, latency/availability targets, support ownership and retention policy. No paid infrastructure has been provisioned.

## II. Completion checklist

| Block | Implemented in this candidate | Still needed before pilot launch |
| --- | --- | --- |
| Caller protection | Distinct hashed caller keys, revocation, no shared-key fallback in pilot mode | Private key issuance, cloud configuration and rotation rehearsal |
| Usage controls | Atomic Redis minute/day/global limits and concurrency leases; fail closed on store outage or missing initialization | Durable noeviction Redis, persistence/backup evidence and agreed limits |
| Provider safety | Async deadline, no automatic SDK retries, token/tool-call bounds, safe errors and pause controls | One live request with these settings; provider spend alerts and pause drill |
| Evaluation/security | Failure exit status, shared strict URL policy, runtime citation/completion checks, deterministic regression cases, dependency/image/history scan gates | Passing exact-revision CI, full live evaluation review and adversarial answer-quality assessment |
| Operations | Content-free correlated request/usage logs; readiness; incident and recovery procedures | Delivered monitoring alert, privacy/retention settings, measured load, actual backup/restore and rollback drills |
| Release | Local staging Compose, hash-locked runtime, packaged smoke checks, explicit paid evaluation workflow | Disable automatic pilot deployment; separate staging/production secrets; deploy and verify the identified revision |

## III. Evidence already recorded

- Baseline protected demo: commit `1851393`, 14 deterministic tests, local Docker smoke checks, cloud rejection/refusal/normal-answer checks and one live evaluation.
- PR #1 merged as `9c0ba03`: failed evaluations return nonzero and retain reports. Main CI `35867100715` passed.
- PR #2 merged as `a29df3b`: deceptive citation URLs fail evaluation. Main CI `35867800335` passed.
- Pilot candidate: local deterministic tests and runtime dependency audit executed during preparation. The PR and its CI record the final candidate revision; no cloud-pilot evidence is claimed here.

## IV. Operator references

Follow [pilot-operations.md](pilot-operations.md) for setup, release and recovery. See [pilot-threat-model.md](pilot-threat-model.md) for threats, controls and residual risks.

A manual release workflow is not automatically a Render deployment gate. The operator must configure deployment access and turn off automatic pilot deployment. A clean scan does not certify security. A local concurrency test is not a cloud capacity benchmark. A documented backup is not a completed restore drill.

## V. Compact debrief notes

1. Failure exit status lets automation recognise an evaluation failure.
2. Parse the destination hostname; a domain appearing in URL text proves nothing.
3. Each caller has its own revocable key and usage bucket.
4. Shared counters prevent extra workers from multiplying the allowance.
5. Requests have bounded waits and no automatic paid retries.
6. Logs record outcomes and token usage without learner content or keys.
7. Release and recovery checks need observed cloud evidence before launch.

These notes replace additional lesson queues. Keep the detailed debrief until the implementation/deployment block is complete.
