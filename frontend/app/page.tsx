"use client";

/**
 * page.tsx — Main AgentForge UI.
 * State machine: idle → loading → results (or error)
 */

import { useState } from "react";
import { runTask, RunResponse } from "@/lib/api";
import TaskInput from "@/components/TaskInput";
import StatusIndicator from "@/components/StatusIndicator";
import ResultPanel from "@/components/ResultPanel";

type State = "idle" | "loading" | "results" | "error";

export default function Home() {
  const [state, setState] = useState<State>("idle");
  const [result, setResult] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string>("");

  const handleSubmit = async (task: string) => {
    setState("loading");
    setResult(null);
    setError("");
    try {
      const data = await runTask(task);
      setResult(data);
      setState("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  };

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-zinc-100 pb-24">
      <div className="mx-auto max-w-4xl px-4 pt-12 space-y-8">
        {/* Hero */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100">
            AgentForge
          </h1>
          <p className="text-zinc-400 max-w-xl">
            Type a complex task. The orchestrator decomposes it into subtasks
            and runs specialist agents{" "}
            <span className="text-teal-400 font-medium">in parallel</span>.
            Results are synthesized into a final answer.
          </p>
        </div>

        {/* Input — always visible */}
        <TaskInput onSubmit={handleSubmit} loading={state === "loading"} />

        {/* Status while loading */}
        <StatusIndicator active={state === "loading"} />

        {/* Error */}
        {state === "error" && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-400 text-sm">
            <span className="font-semibold">Error: </span>
            {error}
            <br />
            <span className="text-zinc-500 text-xs mt-1 block">
              Make sure the backend is running at{" "}
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
            </span>
          </div>
        )}

        {/* Results */}
        {state === "results" && result && <ResultPanel data={result} />}
      </div>
    </main>
  );
}
