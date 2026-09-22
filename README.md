# Enterprise Python Tutor Agent

[![CI](https://github.com/ksanand-ux/enterprise-python-tutor-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ksanand-ux/enterprise-python-tutor-agent/actions/workflows/ci.yml)

A Python teaching API with official-document search, shared-key access control, pre-model guardrails, evaluation reports and a Docker deployment on Render.

The project demonstrates how to build and verify an AI application around an existing model. It does not train a model or execute user code.

## I. Purpose and request flow

An AI tutor needs more than an answer: callers need evidence, and the application needs controls around access and model use.

1. Uvicorn receives the HTTP request; FastAPI selects `/ask`.
2. Pydantic validates the question and learning level before the handler runs.
3. The handler checks `X-Tutor-Key` against the server's `TUTOR_ACCESS_KEY` using `secrets.compare_digest`.
4. A local guardrail checks for configured unsafe-request patterns. Matching requests receive a refusal without model access.
5. Allowed requests call the OpenAI Responses API with required web search restricted to `docs.python.org`.
6. The application returns the answer, source citations, a trace ID and activity entries.

`GET /health` is public and reports basic application responsiveness. It does not verify model credentials or answer quality.

## II. Verified milestone

Observed on 22 September 2026:

| Check | Result |
|---|---|
| Automated test suite | 14 passed |
| Local Docker image | `python-tutor-agent:0.2.2` built and smoke-tested |
| Protected cloud revision | `e5fe987` deployed on Render |
| Cloud request without caller key, after server configuration | 403 |
| Authorised unsafe cloud request | 200 with refusal; no model access reported |
| Authorised genuine cloud question | 200 with an answer and official Python citation |
| Live evaluation after runner access-key update | 1 scenario passed all four configured checks |

Public health endpoint: [enterprise-python-tutor-agent.onrender.com/health](https://enterprise-python-tutor-agent.onrender.com/health).

These results establish the demonstrated cases. They are not a security audit or a guarantee of answer quality on arbitrary questions.

## III. Local setup — Ubuntu / WSL

Use Python 3.12, Git and an OpenAI API account with access to the configured model and tools. Docker is needed for the container section. Commands run from the repository root.

```bash
git clone https://github.com/ksanand-ux/enterprise-python-tutor-agent.git
cd enterprise-python-tutor-agent
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

If you already have a checkout, use that directory instead of cloning again. The development requirements include runtime requirements.

Copy `.env.example` to `.env` if `.env` does not already exist:

```bash
cp -n .env.example .env
```

Edit your private `.env` and fill in these settings:

| Setting | Purpose |
|---|---|
| `OPENAI_API_KEY` | Provider credential used only by the application |
| `OPENAI_MODEL` | Model name; the recorded live evaluation used `gpt-5.6` |
| `TUTOR_ACCESS_KEY` | Private shared key required from callers of `/ask` |

Generate a tutor key once, then store its output privately in `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Every invocation generates a different key. Do not commit real credentials; `.env.example` contains blank key values. `.env` is excluded from Git and the Docker build context.

Start the local API:

```bash
python -m uvicorn app.main:app --reload
```

Open [local API documentation](http://127.0.0.1:8000/docs). For `/ask`, supply the tutor key in the `x-tutor-key` header field.

## IV. Send a request

In a second Ubuntu terminal, run this line first:

```bash
read -rsp 'Tutor access key: ' TUTOR_CALL_KEY
```

Press Enter after the command, then paste the same tutor key used by the local server and press Enter again. Input is hidden. Keep the variable name unchanged; do not put the key into the command itself.

Then run:

```bash
printf 'X-Tutor-Key: %s\n' "$TUTOR_CALL_KEY" | curl -sS -i \
  http://127.0.0.1:8000/ask \
  -H @- \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is a Python list?","level":"beginner"}'
unset TUTOR_CALL_KEY
```

For the deployed service, replace the request URL with `https://enterprise-python-tutor-agent.onrender.com/ask` and use its configured tutor key. Do not send your OpenAI key as the caller header. Genuine model requests consume API credit.

For a structurally valid request: missing server tutor-key configuration returns 503; missing or incorrect caller credentials return 403. Invalid request bodies can return 422 before the access check. A recognised unsafe request with a correct key returns a 200 refusal.

## V. Tests and evaluations

Run deterministic automated tests:

```bash
python -m pytest -q
```

The 14 tests cover health, request validation, response structure, source restriction, evaluator behaviour, guardrail refusals and access rejection. Model clients are replaced with test doubles where needed; tests do not require paid model calls. Rejection tests also check that downstream tutor functions are not reached.

Run one live evaluation after configuring the private local `.env`:

```bash
python -m evals.run_evals --limit 1
```

The runner uses FastAPI's `TestClient` to call the local application directly, including the tutor-key header. It does not call the Render URL, and it does not require a separately running Uvicorn process. Allowed questions use the real OpenAI API and consume credit.

The scenario bank has 15 cases. Run `python -m evals.run_evals --limit 15` only when you intend a full live evaluation. Reports are saved as `reports/eval-<run-id>.json`; inspect `passed`, `failed` and each result. The current runner does not return a nonzero process exit code merely because an evaluation fails.

The latest reviewed run, `cd66626b-d5f3-4390-8567-a31f2a827029`, contains one passing scenario with 8233.63 ms latency. Its checks cover expected terms, forbidden terms, sources and citations. These checks are useful regression signals, not a full semantic correctness assessment.

`reports/sample-evaluation-report.json` is historical sample evidence; it is separate from the latest one-scenario run. After generating a local evaluation report, recheck the latest saved report without another model call:

```bash
python -m evals.recheck_report
```

## VI. Docker and cloud deployment

Build and start the packaged application:

```bash
docker build -t python-tutor-agent:0.2.2 .
docker run --rm \
  --name python-tutor-agent \
  --env-file .env \
  -e PORT=10000 \
  -p 127.0.0.1:10000:10000 \
  python-tutor-agent:0.2.2
```

Use port 10000 in your local health and `/ask` requests for this container. Credentials are supplied at runtime. The container runs as a non-root user; its startup command and health check use `PORT`, defaulting to 8000.

For Render, connect this repository as a Docker web service. Set `TUTOR_ACCESS_KEY`, `OPENAI_API_KEY` and `OPENAI_MODEL` as environment variables. Set **Health Check Path** to `/health`, save and deploy. The health-check field takes a path, not a full URL. Keep the shared tutor key private when demonstrating the service.

GitHub Actions installs dependencies, compiles Python, runs tests and builds the image on pushes to `main` and pull requests. Check CI for the exact commit before treating a revision as verified. CI success and Render deployment status are separate checks.

## VII. Security boundaries and limitations

- Shared-key access control is implemented; per-user identity, tenant isolation and rate limiting are not.
- Missing tutor-key configuration fails closed. The access check precedes guardrails and paid model requests inside the handler.
- Pattern-based guardrails block the tested cases; they do not guarantee protection against every prompt injection.
- Secrets stay outside source control and are not included in prompts. Use restricted provider permissions suitable for the required API operations.
- Official-domain retrieval is configured, but the documentation version is not pinned. The latest evaluation cited Python 3.15 prerelease documentation while the application runtime uses Python 3.12.
- Token usage and cost fields remain unpopulated. Trace IDs and activity describe each response; durable central monitoring is not implemented.
- The application does not execute or modify user code. Sandboxed execution, persistent memory and more extensive security evaluation are future work.

## VIII. Interview summary

“I built and deployed a Python tutor API around an existing model. It validates requests, requires a shared access key, checks unsafe-request patterns before model access, and searches official Python documentation. I tested the control flow with fake model clients, verified the Docker container and cloud endpoints, and recorded a live evaluation. I can explain both the controls demonstrated and their limits.”
