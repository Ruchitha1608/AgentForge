"""
agents.py — Four specialist async agent functions.
Each agent: checks Redis cache → calls OpenAI → stores in Redis.
Returns a uniform dict so orchestrator can handle all agents identically.
"""

import asyncio
import time
import logging
from openai import AsyncOpenAI
import memory
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

# ── System prompts ─────────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "research": (
        "You are a research specialist. Find facts, compare options, cite reasoning. "
        "Be specific and thorough. Structure your response with clear sections."
    ),
    "code": (
        "You are a senior software engineer. Write clean code, identify bugs, review "
        "architecture. Be precise and include working examples where relevant."
    ),
    "analysis": (
        "You are an analytical expert. Break down problems, evaluate tradeoffs, give "
        "structured reasoning. Use clear headings and bullet points."
    ),
    "writer": (
        "You are a technical writer. Write clear, structured content with headers. "
        "Be concise and professional. Do not produce generic boilerplate — "
        "tailor every sentence to the specific task."
    ),
}


# ── Core agent runner ──────────────────────────────────────────────────────────

async def _run_agent(agent_type: str, subtask: str, original_task: str) -> dict:
    """
    Generic agent executor used by all four public agent functions.
    Injects original_task as context so no agent works in isolation.
    """
    key = memory.cache_key(subtask)
    cached = memory.get_cached(key)

    if cached:
        logger.info("[%s] cache hit for subtask: %s…", agent_type, subtask[:60])
        return {
            "agent": agent_type,
            "result": cached,
            "time_taken": 0.0,
            "from_cache": True,
        }

    system_prompt = SYSTEM_PROMPTS.get(agent_type, "You are a helpful assistant.")
    user_message = (
        f"Overall task context: {original_task}\n\n"
        f"Your specific subtask: {subtask}"
    )

    start = time.perf_counter()
    response = await client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.5,
    )
    elapsed = time.perf_counter() - start

    result = response.choices[0].message.content.strip()
    memory.set_cached(key, result)

    logger.info("[%s] completed in %.2fs", agent_type, elapsed)
    return {
        "agent": agent_type,
        "result": result,
        "time_taken": round(elapsed, 3),
        "from_cache": False,
    }


# ── Public agent functions ─────────────────────────────────────────────────────

async def research_agent(subtask: str, original_task: str) -> dict:
    """Research specialist — facts, comparisons, citations."""
    return await _run_agent("research", subtask, original_task)


async def code_agent(subtask: str, original_task: str) -> dict:
    """Senior engineer — code, architecture, bug identification."""
    return await _run_agent("code", subtask, original_task)


async def analysis_agent(subtask: str, original_task: str) -> dict:
    """Analytical expert — tradeoffs, structured reasoning."""
    return await _run_agent("analysis", subtask, original_task)


async def writer_agent(subtask: str, original_task: str) -> dict:
    """Technical writer — clear, structured, specific prose."""
    return await _run_agent("writer", subtask, original_task)


AGENT_MAP = {
    "research": research_agent,
    "code": code_agent,
    "analysis": analysis_agent,
    "writer": writer_agent,
}
