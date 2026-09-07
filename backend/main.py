from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.graph import build_travel_graph, run_travel_graph


load_dotenv()

app = FastAPI(
    title="AI Travel Concierge API",
    description="Backend API for the AI Travel Concierge",
    version="1.0.0",
)

# Frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: str | None = None
    message_history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    thread_id: str
    tools_used: list[str]
    retry_count: int
    duration_seconds: float


@app.get("/")
def root():
    return {
        "message": "AI Travel Concierge API",
        "status": "running",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Travel Concierge",
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured.",
        )

    if not model_name:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_MODEL is not configured.",
        )

    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        graph = build_travel_graph(
            api_key=api_key,
            model_name=model_name,
        )

        result = run_travel_graph(
            graph=graph,
            user_query=request.message,
            thread_id=thread_id,
            message_history=request.message_history,
        )

        tool_results = result.get("tool_results", {})

        return ChatResponse(
            answer=result.get(
                "final_answer",
                "No answer was generated.",
            ),
            thread_id=thread_id,
            tools_used=list(tool_results.keys()),
            retry_count=result.get("retry_count", 0),
            duration_seconds=round(
                result.get("total_duration", 0.0),
                3,
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "The travel agent could not process the request: "
                f"{type(error).__name__}"
            ),
        ) from error