import asyncio
import hashlib
import json
import time
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TASK = (
    "Analyze the architecture of a React + FastAPI + PostgreSQL web app, "
    "identify potential security vulnerabilities, suggest performance "
    "improvements, and write a deployment checklist for AWS."
)

AGENT_SYSTEM_PROMPTS = {
    "research": (
        "You are a research agent. Gather factual information and key points "
        "on the given topic. Be thorough and cite concrete details."
    ),
    "code": (
        "You are a code agent. Provide code examples, technical implementation "
        "details, or schema comparisons relevant to the topic."
    ),
    "analysis": (
        "You are an analysis agent. Compare, contrast, and evaluate the "
        "tradeoffs in the given topic. Be analytical and objective."
    ),
    "writer": (
        "You are a writer agent. Synthesize the provided information into a "
        "clear, well-structured, actionable output for a technical audience. "
        "Be specific — do not produce generic boilerplate."
    ),
}

# ── Redis setup (optional — degrades gracefully if unavailable) ───────────────

try:
    import redis
    _redis_client = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=1)
    _redis_client.ping()
    REDIS_AVAILABLE = True
    print("[CACHE] Redis connected at localhost:6379")
except Exception as e:
    REDIS_AVAILABLE = False
    _redis_client = None
    print(f"[CACHE] Redis not available ({e}) — running without cache")

CACHE_TTL = 3600  # 1 hour


def _cache_key(subtask_text: str) -> str:
    """Deterministic cache key from subtask text."""
    return "agentforge:" + hashlib.sha256(subtask_text.encode()).hexdigest()


def cache_get(subtask_text: str) -> str | None:
    if not REDIS_AVAILABLE:
        return None
    try:
        value = _redis_client.get(_cache_key(subtask_text))
        return value.decode() if value else None
    except Exception:
        return None


def cache_set(subtask_text: str, result: str) -> None:
    if not REDIS_AVAILABLE:
        return
    try:
        _redis_client.setex(_cache_key(subtask_text), CACHE_TTL, result)
    except Exception:
        pass


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def decompose_task(task: str) -> list[dict]:
    """Ask the LLM to break the task into subtasks with assigned agent types."""
    print(f"\n[ORCHESTRATOR] Decomposing task:\n  {task}\n")

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a task decomposition engine. Given a complex task, break it into 3-5 subtasks. "
                    "Assign each subtask an agent type from: research, code, analysis, writer. "
                    "Return ONLY a JSON array with objects having keys: 'id' (int), 'agent_type' (str), 'subtask' (str). "
                    "No explanation, no markdown fences — raw JSON only."
                ),
            },
            {"role": "user", "content": task},
        ],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if the model ignores the instruction
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    subtasks = json.loads(raw.strip())

    print(f"[ORCHESTRATOR] Decomposed into {len(subtasks)} subtasks:")
    for s in subtasks:
        print(f"  [{s['agent_type'].upper()}] #{s['id']}: {s['subtask']}")
    print()
    return subtasks


async def run_agent(subtask: dict, original_task: str) -> dict:
    """
    Run a single agent on its subtask.

    FIX applied here: every agent receives the original_task as context so that
    writer/analysis agents aren't flying blind on their slice of the problem.
    """
    agent_type = subtask["agent_type"]
    task_text  = subtask["subtask"]
    task_id    = subtask["id"]

    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_type, "You are a helpful assistant.")

    # ── Cache check ────────────────────────────────────────────────────────────
    cached = cache_get(task_text)
    if cached:
        print(f"[{agent_type.upper()} AGENT #{task_id}] CACHE HIT (instant)")
        print(f"  Task: {task_text[:120]}")
        print(f"  Result (truncated): {cached[:300]}{'...' if len(cached) > 300 else ''}\n")
        return {
            "id":         task_id,
            "agent_type": agent_type,
            "subtask":    task_text,
            "result":     cached,
            "elapsed":    0.0,
            "from_cache": True,
        }

    # ── Live LLM call ──────────────────────────────────────────────────────────
    # FIX: inject original_task so agents aren't isolated from the broader context
    user_message = (
        f"Overall task context: {original_task}\n\n"
        f"Your specific subtask: {task_text}"
    )

    start = time.perf_counter()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.5,
    )
    elapsed = time.perf_counter() - start

    result_text = response.choices[0].message.content.strip()

    # ── Cache store ────────────────────────────────────────────────────────────
    cache_set(task_text, result_text)

    print(f"[{agent_type.upper()} AGENT #{task_id}] Done in {elapsed:.2f}s (fresh LLM)")
    print(f"  Task: {task_text[:120]}")
    print(f"  Result (truncated): {result_text[:300]}{'...' if len(result_text) > 300 else ''}\n")

    return {
        "id":         task_id,
        "agent_type": agent_type,
        "subtask":    task_text,
        "result":     result_text,
        "elapsed":    elapsed,
        "from_cache": False,
    }


async def synthesize(original_task: str, agent_results: list[dict]) -> str:
    """Synthesize all agent results into a final cohesive answer."""
    print("[SYNTHESIZER] Combining all agent results into final answer...\n")

    combined = "\n\n".join(
        f"--- {r['agent_type'].upper()} AGENT (subtask: {r['subtask']}) ---\n{r['result']}"
        for r in sorted(agent_results, key=lambda x: x["id"])
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a synthesis agent. Receive outputs from multiple specialist agents "
                    "and combine them into a single, cohesive, well-structured final answer. "
                    "Do not just concatenate — integrate insights and present clearly."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original task: {original_task}\n\n"
                    f"Agent outputs:\n{combined}\n\n"
                    "Write the final synthesized answer."
                ),
            },
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()


async def run_pipeline(task: str, run_label: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {run_label}")
    print(f"{'═' * 70}")

    total_start = time.perf_counter()

    # Step 1: Decompose
    subtasks = await decompose_task(task)

    # Step 2: Run agents in parallel
    print("[ORCHESTRATOR] Running all agents in parallel...\n")
    parallel_start = time.perf_counter()
    agent_results = list(
        await asyncio.gather(*[run_agent(s, task) for s in subtasks])
    )
    parallel_elapsed = time.perf_counter() - parallel_start

    # FIX: real sequential estimate from actual per-agent times
    fresh_times  = [r["elapsed"] for r in agent_results if not r["from_cache"]]
    cached_count = sum(1 for r in agent_results if r["from_cache"])
    sequential_estimate = sum(r["elapsed"] for r in agent_results)

    print(f"[TIMING] Parallel wall time : {parallel_elapsed:.2f}s ({len(agent_results)} agents)")
    if cached_count:
        print(f"[TIMING] Cache hits         : {cached_count}/{len(agent_results)} agents (instant)")
    if fresh_times:
        print(f"[TIMING] Sequential estimate: ~{sequential_estimate:.1f}s  "
              f"(sum of {len(fresh_times)} fresh agent times)")
        speedup = sequential_estimate / parallel_elapsed if parallel_elapsed > 0 else 1
        print(f"[TIMING] Parallelism speedup: {speedup:.1f}x")

    # Step 3: Synthesize
    final_answer = await synthesize(task, agent_results)

    total_elapsed = time.perf_counter() - total_start

    print("=" * 70)
    print("FINAL SYNTHESIZED ANSWER")
    print("=" * 70)
    print(final_answer)
    print("=" * 70)
    print(f"\n[TIMING] Total wall time: {total_elapsed:.2f}s\n")

    return total_elapsed


async def main():
    # ── Run 1: cold (all fresh LLM calls) ─────────────────────────────────────
    t1 = await run_pipeline(TASK, "RUN 1 — Cold (no cache)")

    if REDIS_AVAILABLE:
        print("\n[INFO] Waiting 1s then running same task again to hit cache...\n")
        await asyncio.sleep(1)

        # ── Run 2: warm (all from Redis cache) ────────────────────────────────
        t2 = await run_pipeline(TASK, "RUN 2 — Warm (Redis cache)")

        print(f"\n{'═' * 70}")
        print(f"  CACHE COMPARISON")
        print(f"{'═' * 70}")
        print(f"  Run 1 (cold) : {t1:.2f}s")
        print(f"  Run 2 (warm) : {t2:.2f}s")
        print(f"  Speedup      : {t1 / t2:.1f}x faster with cache")
        print(f"{'═' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
