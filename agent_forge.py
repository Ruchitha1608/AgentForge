import asyncio
import json
import time
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TASK = "Research the pros and cons of PostgreSQL vs MongoDB, then write a comparison summary"

AGENT_SYSTEM_PROMPTS = {
    "research": "You are a research agent. Your job is to gather factual information and key points on the given topic. Be thorough and cite concrete details.",
    "code":     "You are a code agent. Your job is to provide code examples, technical implementation details, or schema comparisons relevant to the topic.",
    "analysis": "You are an analysis agent. Your job is to compare, contrast, and evaluate the tradeoffs in the given topic. Be analytical and objective.",
    "writer":   "You are a writer agent. Your job is to synthesize provided research into a clear, well-structured summary for a technical audience.",
}


async def decompose_task(task: str) -> list[dict]:
    """Ask the LLM to break the task into subtasks with assigned agent types."""
    print(f"\n[ORCHESTRATOR] Decomposing task: {task!r}\n")

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
    subtasks = json.loads(raw)
    print(f"[ORCHESTRATOR] Decomposed into {len(subtasks)} subtasks:")
    for s in subtasks:
        print(f"  [{s['agent_type'].upper()}] #{s['id']}: {s['subtask']}")
    print()
    return subtasks


async def run_agent(subtask: dict) -> dict:
    """Run a single agent on its subtask."""
    agent_type = subtask["agent_type"]
    task_text  = subtask["subtask"]
    task_id    = subtask["id"]

    system_prompt = AGENT_SYSTEM_PROMPTS.get(
        agent_type, "You are a helpful assistant."
    )

    start = time.perf_counter()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": task_text},
        ],
        temperature=0.5,
    )
    elapsed = time.perf_counter() - start

    result_text = response.choices[0].message.content.strip()

    print(f"[{agent_type.upper()} AGENT #{task_id}] Done in {elapsed:.2f}s")
    print(f"  Task : {task_text}")
    print(f"  Result (truncated): {result_text[:300]}{'...' if len(result_text) > 300 else ''}\n")

    return {
        "id":         task_id,
        "agent_type": agent_type,
        "subtask":    task_text,
        "result":     result_text,
    }


async def synthesize(original_task: str, agent_results: list[dict]) -> str:
    """Writer agent synthesizes all results into a final answer."""
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
                    "You are a synthesis agent. You receive outputs from multiple specialist agents "
                    "and combine them into a single, cohesive, well-structured final answer. "
                    "Do not just concatenate — integrate and present clearly."
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


async def main():
    total_start = time.perf_counter()

    # Step 1: Decompose
    subtasks = await decompose_task(TASK)

    # Step 2: Run agents in parallel
    print("[ORCHESTRATOR] Running all agents in parallel...\n")
    parallel_start = time.perf_counter()
    agent_results = await asyncio.gather(*[run_agent(s) for s in subtasks])
    parallel_elapsed = time.perf_counter() - parallel_start

    print(f"[TIMING] All {len(subtasks)} agents finished in {parallel_elapsed:.2f}s (parallel)")
    sequential_estimate = sum(
        # rough: assume each agent took its share of wall time
        # we don't have per-agent times here so estimate from parallel total / overlap
        parallel_elapsed * 1.5  # conservative: sequential would be ~1.5-2x slower
        for _ in subtasks
    ) / len(subtasks) * len(subtasks)  # just parallel_elapsed * 1.5 essentially
    print(f"[TIMING] Estimated sequential time: ~{sequential_estimate:.1f}s\n")

    # Step 3: Synthesize
    final_answer = await synthesize(TASK, list(agent_results))

    total_elapsed = time.perf_counter() - total_start

    print("=" * 70)
    print("FINAL SYNTHESIZED ANSWER")
    print("=" * 70)
    print(final_answer)
    print("=" * 70)
    print(f"\n[TIMING] Total wall time: {total_elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
