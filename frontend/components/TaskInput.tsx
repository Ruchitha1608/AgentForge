"use client";

/**
 * TaskInput.tsx — Large textarea + submit button + example chips.
 */

import { useState } from "react";

const EXAMPLES = [
  "Compare PostgreSQL vs MongoDB for a startup in 2025",
  "Analyze this Python Flask app for security vulnerabilities",
  "Research the best AI stack for building a SaaS product",
];

interface Props {
  onSubmit: (task: string) => void;
  loading: boolean;
}

export default function TaskInput({ onSubmit, loading }: Props) {
  const [task, setTask] = useState("");

  const handleSubmit = () => {
    if (!task.trim() || loading) return;
    onSubmit(task.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  return (
    <div className="w-full space-y-4">
      <textarea
        value={task}
        onChange={(e) => setTask(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter a complex task..."
        rows={4}
        disabled={loading}
        className="w-full rounded-xl border border-zinc-700 bg-zinc-900 px-5 py-4 text-zinc-100
                   placeholder-zinc-500 text-base resize-none focus:outline-none
                   focus:ring-2 focus:ring-teal-500 focus:border-transparent
                   disabled:opacity-50 disabled:cursor-not-allowed transition"
      />

      <button
        onClick={handleSubmit}
        disabled={loading || !task.trim()}
        className="w-full rounded-xl bg-teal-500 hover:bg-teal-400 disabled:bg-zinc-700
                   disabled:cursor-not-allowed text-black font-semibold py-3 text-base
                   transition-colors duration-200"
      >
        {loading ? "Running agents…" : "Run AgentForge"}
      </button>

      {/* Example chips */}
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setTask(ex)}
            disabled={loading}
            className="rounded-lg border border-zinc-700 bg-zinc-800 hover:bg-zinc-700
                       text-zinc-400 hover:text-zinc-200 text-xs px-3 py-1.5
                       transition-colors duration-150 disabled:opacity-40
                       disabled:cursor-not-allowed text-left"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
