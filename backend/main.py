"""
main.py — FastAPI application for AgentForge.
Exposes POST /run, GET /health, GET /benchmark.
"""

import asyncio
import logging
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import memory
from config import get_settings
from orchestrator import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title="AgentForge", version="1.0.0")

# ── CORS ───────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────

class RunRequest(BaseModel):
    task: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "redis": "connected" if memory.is_available() else "unavailable",
        "model": settings.model_name,
    }


@app.post("/run")
async def run(req: RunRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="task cannot be empty")

    logger.info("POST /run — task: %s…", req.task[:80])
    result = await run_pipeline(req.task)
    return result


BENCHMARK_TASK = "Compare PostgreSQL vs MongoDB for a startup in 2025"


@app.get("/benchmark")
async def benchmark():
    """
    Run the same task twice. First call hits LLM; second hits Redis cache.
    Returns timing comparison to demonstrate cache speedup.
    """
    # Flush any existing cache for this task so benchmark is honest
    from orchestrator import decompose_task
    subtasks = await decompose_task(BENCHMARK_TASK)
    for s in subtasks:
        key = memory.cache_key(s["prompt"])
        if memory.is_available() and memory._client:
            try:
                memory._client.delete(key)
            except Exception:
                pass

    t0 = time.perf_counter()
    run1 = await run_pipeline(BENCHMARK_TASK)
    time1 = time.perf_counter() - t0

    t0 = time.perf_counter()
    run2 = await run_pipeline(BENCHMARK_TASK)
    time2 = time.perf_counter() - t0

    return {
        "task": BENCHMARK_TASK,
        "run1_cold": {
            "total_time": round(time1, 2),
            "parallel_time": run1["parallel_time"],
            "sequential_time": run1["sequential_time"],
            "speedup": run1["speedup"],
        },
        "run2_cached": {
            "total_time": round(time2, 2),
            "parallel_time": run2["parallel_time"],
            "sequential_time": run2["sequential_time"],
        },
        "cache_speedup": round(time1 / time2, 1) if time2 > 0 else "∞",
    }
