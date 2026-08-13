import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field


load_dotenv(dotenv_path=".env")


app = FastAPI(
    title="Enterprise Python Tutor Agent",
    version="0.1.0",
)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    level: str = "beginner"


class AskResponse(BaseModel):
    trace_id: str
    answer: str
    sources: list[dict[str, str]]
    activity: list[str]


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "python-tutor-agent",
    }


@app.post("/ask", response_model=AskResponse)
def ask_python_tutor(request: AskRequest):
    trace_id = str(uuid.uuid4())

    activity = [
        "Received the learner's Python question",
        "Searching only official Python documentation",
    ]

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5.6")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured",
        )

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.create(
            model=model,
            reasoning={"effort": "low"},
            instructions=(
                "You are a patient Python tutor. "
                "Use the official Python documentation found by web search. "
                "Explain the whole idea first, then the important parts, "
                "then reconnect them. Adapt the explanation to the learner's "
                "level. Include one short Python example and one quick "
                "practice question. Do not claim facts unsupported by the "
                "retrieved documentation."
            ),
            tools=[
                {
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": ["docs.python.org"],
                    },
                }
            ],
            tool_choice="required",
            include=["web_search_call.action.sources"],
            input=(
                f"Learner level: {request.level}\n"
                f"Python question: {request.question}"
            ),
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Model request failed: {type(error).__name__}",
        ) from error

    activity.append("Official documentation search completed")
    activity.append("Generated a grounded tutorial answer")

    sources = []
    seen_urls = set()
    response_data = response.model_dump()

    for item in response_data.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            for annotation in content.get("annotations", []):
                if annotation.get("type") != "url_citation":
                    continue

                url = annotation.get("url", "")
                title = annotation.get("title", "Python documentation")

                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({
                        "title": title,
                        "url": url,
                    })

    return AskResponse(
        trace_id=trace_id,
        answer=response.output_text,
        sources=sources,
        activity=activity,
    )
