"""
orchestrator.py — Task decomposition, parallel dispatch, and synthesis.
Measures real parallel vs sequential timing and returns the speedup ratio.
"""

import asyncio
import json
import logging
import time
import uuid
from openai import AsyncOpenAI
from agents import AGENT_MAP
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

DECOMPOSE_SYSTEM = """You are a task decomposition engine for a multi-agent AI system.
Break the user's task into 3-5 focused subtasks. Assign each to the best agent type.

Agent types and their strengths:
- research: facts, comparisons, background knowledge
- code: implementation, architecture, code review, technical specs
- analysis: tradeoffs, evaluation, structured reasoning
- writer: documentation, summaries, checklists, final prose

Return ONLY a valid JSON array. No markdown fences. No explanation.
Each item must have exactly these keys:
  "id": integer starting at 1
  "agent_type": one of: research, code, analysis, writer
  "prompt": the specific subtask instruction (be precise and self-contained)
  "depends_on": [] (empty list — all run in parallel for now)

Example output:
[
  {"id": 1, "agent_type": "research", "prompt": "Research X", "depends_on": []},
  {"id": 2, "agent_type": "code", "prompt": "Write code for Y", "depends_on": []}
]"""


async def decompose_task(task: str) -> list[dict]:
    """Call OpenAI to break the task into structured subtasks."""
    response = await client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": DECOMPOSE_SYSTEM},
            {"role": "user", "content": task},
        ],
        temperature=0.2,  # Low temp for consistent structure
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if the model ignores the instruction
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    subtasks = json.loads(raw)
    logger.info("Decomposed into %d subtasks", len(subtasks))
    return subtasks


async def run_parallel(subtasks: list[dict], original_task: str) -> dict:
    """
    Run all subtasks in parallel using asyncio.gather().
    Measures both parallel wall time and estimated sequential time.
    Returns results keyed by subtask id.
    """

    async def run_one(subtask: dict) -> tuple[str, dict]:
        agent_fn = AGENT_MAP.get(subtask["agent_type"])
        if agent_fn is None:
            logger.warning("Unknown agent type: %s — falling back to research", subtask["agent_type"])
            agent_fn = AGENT_MAP["research"]

        result = await agent_fn(subtask["prompt"], original_task)
        return str(subtask["id"]), result

    parallel_start = time.perf_counter()
    pairs = await asyncio.gather(*[run_one(s) for s in subtasks])
    parallel_time = time.perf_counter() - parallel_start

    results = {task_id: data for task_id, data in pairs}

    # Sequential time = sum of all individual times (what it would have taken one-by-one)
    sequential_time = sum(r["time_taken"] for r in results.values())
    speedup = round(sequential_time / parallel_time, 2) if parallel_time > 0 else 1.0

    return {
        "results": results,
        "parallel_time": round(parallel_time, 3),
        "sequential_time": round(sequential_time, 3),
        "speedup": speedup,
    }


async def synthesize(task: str, subtask_results: dict) -> str:
    """Combine all agent results into a final cohesive answer."""
    combined = "\n\n".join(
        f"--- {data['agent'].upper()} AGENT ---\n{data['result']}"
        for data in sorted(subtask_results.values(), key=lambda x: x.get("id", 0))
    )

    response = await client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a synthesis agent. Integrate outputs from multiple specialist agents "
                    "into a single cohesive, well-structured final answer. "
                    "Do not concatenate — weave insights together. Use clear headers."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original task: {task}\n\n"
                    f"Agent outputs:\n{combined}\n\n"
                    "Write the final synthesized answer."
                ),
            },
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()


async def run_pipeline(task: str) -> dict:
    """
    Full pipeline: decompose → parallel agents → synthesize.
    Returns everything the API endpoint needs.
    """
    session_id = str(uuid.uuid4())[:8]

    subtasks = await decompose_task(task)
    plan = "\n".join(
        f"  [{s['agent_type'].upper()}] {s['prompt']}" for s in subtasks
    )

    dispatch = await run_parallel(subtasks, task)
    subtask_results = dispatch["results"]

    final_answer = await synthesize(task, subtask_results)

    return {
        "session_id": session_id,
        "plan": plan,
        "subtask_results": subtask_results,
        "final_answer": final_answer,
        "parallel_time": dispatch["parallel_time"],
        "sequential_time": dispatch["sequential_time"],
        "speedup": dispatch["speedup"],
        "agents_used": len(subtasks),
    }
