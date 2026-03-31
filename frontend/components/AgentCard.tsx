"use client";

/**
 * AgentCard.tsx — Displays a single agent's result with type badge,
 * timing, cache indicator, and result text.
 */

import { AgentResult } from "@/lib/api";

const AGENT_COLORS: Record<string, string> = {
  research: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  code:     "bg-green-500/15 text-green-400 border-green-500/30",
  analysis: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  writer:   "bg-amber-500/15 text-amber-400 border-amber-500/30",
};

interface Props {
  id: string;
  data: AgentResult;
}

export default function AgentCard({ id, data }: Props) {
  const colorClass =
    AGENT_COLORS[data.agent] ?? "bg-zinc-500/15 text-zinc-400 border-zinc-500/30";

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-3 flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`rounded-md border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${colorClass}`}
        >
          {data.agent}
        </span>

        <span className="text-xs text-zinc-500">#{id}</span>

        <div className="ml-auto flex items-center gap-2">
          {data.from_cache ? (
            <span className="rounded-md bg-green-500/15 border border-green-500/30 text-green-400 text-xs px-2 py-0.5 font-medium">
              Cached
            </span>
          ) : (
            <span className="text-xs text-zinc-500">
              {data.time_taken.toFixed(2)}s
            </span>
          )}
        </div>
      </div>

      {/* Result body */}
      <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap overflow-auto max-h-72 scrollbar-thin">
        {data.result}
      </div>
    </div>
  );
}
