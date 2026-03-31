"use client";

/**
 * ResultPanel.tsx — Shows benchmark timing bars, agent cards grid, and final answer.
 */

import { RunResponse } from "@/lib/api";
import AgentCard from "./AgentCard";

interface Props {
  data: RunResponse;
}

function TimingBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span>{label}</span>
        <span className="font-mono">{value.toFixed(2)}s</span>
      </div>
      <div className="h-3 w-full rounded-full bg-zinc-800 overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function ResultPanel({ data }: Props) {
  const maxTime = data.sequential_time;
  const entries = Object.entries(data.subtask_results).sort(
    ([a], [b]) => Number(a) - Number(b)
  );

  return (
    <div className="w-full space-y-8">
      {/* Benchmark bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">
            Parallel Performance
          </h2>
          <span className="text-2xl font-bold text-teal-400">
            {data.speedup}x faster
          </span>
        </div>
        <TimingBar
          label="Parallel (actual)"
          value={data.parallel_time}
          max={maxTime}
          color="bg-teal-500"
        />
        <TimingBar
          label="Sequential (estimated)"
          value={data.sequential_time}
          max={maxTime}
          color="bg-zinc-600"
        />
        <p className="text-xs text-zinc-500">
          {data.agents_used} specialist agents ran concurrently using asyncio.gather()
        </p>
      </div>

      {/* Agent cards grid */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-widest mb-4">
          Agent Results
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {entries.map(([id, result]) => (
            <AgentCard key={id} id={id} data={result} />
          ))}
        </div>
      </div>

      {/* Final answer */}
      <div className="rounded-xl border border-teal-500/30 bg-teal-500/5 p-6 space-y-3">
        <h2 className="text-sm font-semibold text-teal-400 uppercase tracking-widest">
          Final Answer
        </h2>
        <div className="text-zinc-200 text-sm leading-relaxed whitespace-pre-wrap">
          {data.final_answer}
        </div>
      </div>
    </div>
  );
}
