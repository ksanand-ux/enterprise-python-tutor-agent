# Tutor production readiness

This checklist defines the proposed next release for a small, invite-only Python tutor API. The deployed portfolio milestone is complete. This production release is **not complete** until the applicable checks below have evidence and the pilot operating requirements have been agreed.

Baseline: commit `1851393`, 14 deterministic tests, protected Render deployment, one successful authorised cloud answer and one successful live evaluation. The current service uses one shared caller key. No real-user production operating history is claimed.

## I. Scope and operating requirements

Proposed scope: a small invited adult learner group using an API, with no code execution, file uploads or stored conversation history. A graphical interface is not required for this release. LangGraph, CrewAI, a vector database and Kubernetes are not prerequisites.

Before provisioning or launch, record the intended number of users, monthly hosting and API budget, maximum simultaneous requests, acceptable response times, support owner, and data-retention period. These are launch requirements, not unspecified promises of enterprise scale. No new paid resources are authorised by this checklist alone.

- [ ] Record operating requirements and the deployment architecture.
- [ ] Document a threat model covering stolen caller credentials, automated abuse, secret leakage, prompt injection, dependency compromise and provider failure.
- [ ] Confirm applicable privacy requirements and what data the provider and hosting service retain.

## II. Identity and abuse controls

- [ ] Issue independently revocable caller credentials or use managed user authentication; do not distribute one common key to all users.
- [ ] Test missing, wrong, revoked and valid credentials. Bind permissions and usage accounting to the authenticated caller.
- [ ] Enforce request, concurrency and daily-use limits before paid calls. Choose limits from the operating requirements.
- [ ] Demonstrate that restarting or adding an application worker does not reset or multiply enforced quotas. Select a suitable shared/persistent store before claiming distributed enforcement.
- [ ] Record secret storage, least-privilege provider access and a rotation procedure; practise rotation without exposing keys.

Acceptance evidence: denied callers never reach the provider; excess requests receive a controlled rejection; one caller cannot bypass another caller's limits. If user-owned data is later added, add ownership-isolation tests before launch.

## III. Provider failures and cost controls

- [ ] Configure and test an overall model-request deadline, bounded retries, output limits and concurrency limits; account for SDK retry behaviour.
- [ ] Test provider timeout, rate limit, authentication failure and outage using injected failures. Return safe, consistent errors without credentials or raw provider responses.
- [ ] Record usage and cost estimates with the model/pricing basis and distinguish estimates from billing. Configure spend alerts and suitable account controls.
- [ ] Provide a tested operator switch to disable paid requests while preserving basic health access.

Acceptance evidence: requests finish or fail within the agreed deadline; failures do not cause unbounded retries or spending; costs are visible and controls are exercised.

## IV. Evaluation and application security

- [x] Evaluation CLI failure exit status merged in `9c0ba03` (PR #1, 23 September 2026). Five regression cases passed CI before merge. Reports are retained; promotion still needs to invoke the check.
- [ ] Establish a representative, versioned evaluation set and acceptance thresholds. Rerun the full existing scenario set for the release and inspect failures rather than loosening checks just to obtain a pass.
- [ ] Make release promotion depend on the required evaluation result. Paid live evaluations should be deliberate, budgeted release checks, not implicit in every PR.
- [x] Source-validation regression suite passed in PR #2 on 23 September 2026 (CI run `35867405715`): evaluation requires every citation URL to use HTTPS and the exact expected hostname. Tests cover lookalike hosts, misleading paths/query strings, user information, malformed URLs and mixed trusted/untrusted sources. This checks evaluation results; it does not add runtime response filtering.
- [ ] Test instructions injected in user input and retrieved content; define how missing citations and incomplete model responses are handled.
- [ ] Scan dependencies, the container and repository secrets; triage findings and record fixes or reasoned exceptions. A clean scan is not proof of security.

Acceptance evidence: known negative cases fail for the expected reason; release checks cannot report success when required evaluations fail; the retrieval and citation policy is tested against adversarial URLs.

## V. Observability and recovery

- [ ] Produce structured server logs with request ID, outcome, duration and caller identifier, excluding keys and raw learner content by default.
- [ ] Monitor failures, latency, traffic, provider errors, rate-limit events and spending; test an alert end to end.
- [ ] Separate basic liveness from readiness semantics. Do not make every health probe incur a paid model request.
- [ ] Create an incident procedure for leaked credentials, runaway spend and provider failure; rehearse disable, investigate, restore and verify.
- [ ] If persistent user or quota data is introduced, define and test backup/restore and retention. Do not claim recovery based only on a scheduled backup.

## VI. Release and pilot acceptance

- [ ] Use separate staging and production configuration with isolated secrets.
- [ ] Deploy an identified revision or immutable image; record the relationship between reviewed source and the deployed artifact.
- [ ] Run load and failure tests against the agreed workload. Report measured results and their limits.
- [ ] Practise rollback to a known-good revision and verify health and access controls afterwards.
- [ ] Run a limited authorised pilot and record incidents, latency, cost and feedback against agreed targets.
- [ ] Sign off the applicable controls, known limitations and operational ownership before opening access further.

## Evidence and completion rule

For each checkbox record: implementation commit, test or drill, observed result and date. The application is ready for the defined pilot only when its required gates pass. Larger audiences, sensitive data or additional tools require a fresh review of scope and controls.

## Short debrief log

| Step | Change | Why |
| --- | --- | --- |
| 1 | Evaluation command returns failure when any case fails. | Automation can detect a failed evaluation. |
| 2 | Evaluate parsed citation hosts instead of searching URL text. | A misleading link must not pass as official documentation. |

Step 1 is merged. Step 2 passed automated tests and Docker build in PR #2; see the PR for merge status. Remaining controls above are still open; passing these checks does not establish full production readiness.
