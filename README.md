# Enterprise Python Tutor Agent

A Dockerized Generative AI MVP that teaches Python using official Python documentation.

## Request flow

Learner question → FastAPI → OpenAI Responses API → docs.python.org search → grounded tutorial with citations

## MVP capabilities

- `/health` and `/ask` FastAPI endpoints
- Pydantic request validation
- Level-aware tutor instructions
- Official Python documentation grounding
- Source citations, trace ID and activity events
- Automated tests with a fake OpenAI client
- Restricted API key stored outside source code
- Non-root Docker runtime and health check

## Run locally

    python -m uvicorn app.main:app --reload

API documentation: http://127.0.0.1:8000/docs

## Run tests

    python -m pytest -q

## Docker

Build:

    docker build -t python-tutor-agent:0.1.0 .

Run:

    docker run --rm --name python-tutor-agent -p 8000:8000 --env-file .env python-tutor-agent:0.1.0

The API key is injected at runtime and excluded from Git and the Docker image.

## Current boundary

This is a working local MVP. Planned upgrades include indexed RAG, sandboxed code execution, authentication, agent evaluations, security testing, observability, CI/CD and cloud deployment.
