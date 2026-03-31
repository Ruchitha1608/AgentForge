"use client";

/**
 * StatusIndicator.tsx — Animated pipeline stage progress shown while the
 * API call runs in the background. Each stage lights up every 1.5s.
 */

import { useEffect, useState } from "react";

const STAGES = [
  "Decomposing task...",
  "Dispatching agents...",
  "Running in parallel...",
  "Synthesizing results...",
];

interface Props {
  active: boolean;
}

export default function StatusIndicator({ active }: Props) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!active) {
      setStep(0);
      return;
    }
    const interval = setInterval(() => {
      setStep((s) => Math.min(s + 1, STAGES.length - 1));
    }, 1500);
    return () => clearInterval(interval);
  }, [active]);

  if (!active) return null;

  return (
    <div className="w-full rounded-xl border border-zinc-700 bg-zinc-900 p-5 space-y-3">
      <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-4">
        Pipeline
      </p>
      {STAGES.map((label, i) => {
        const done = i < step;
        const current = i === step;
        return (
          <div key={label} className="flex items-center gap-3">
            <div
              className={`h-2 w-2 rounded-full flex-shrink-0 transition-colors duration-500 ${
                done
                  ? "bg-teal-400"
                  : current
                  ? "bg-teal-500 animate-pulse"
                  : "bg-zinc-700"
              }`}
            />
            <span
              className={`text-sm transition-colors duration-500 ${
                done
                  ? "text-teal-400"
                  : current
                  ? "text-zinc-100"
                  : "text-zinc-600"
              }`}
            >
              {label}
            </span>
            {current && (
              <svg
                className="ml-auto h-4 w-4 animate-spin text-teal-400 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
            )}
          </div>
        );
      })}
    </div>
  );
}
