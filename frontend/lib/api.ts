/**
 * api.ts — Typed client for the AgentForge FastAPI backend.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AgentResult {
  agent: string;
  result: string;
  time_taken: number;
  from_cache: boolean;
}

export interface RunResponse {
  session_id: string;
  plan: string;
  subtask_results: Record<string, AgentResult>;
  final_answer: string;
  parallel_time: number;
  sequential_time: number;
  speedup: number;
  agents_used: number;
}

export interface HealthResponse {
  status: string;
  redis: string;
  model: string;
}

export async function runTask(task: string): Promise<RunResponse> {
  const res = await fetch(`${BASE_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json();
}

export async function healthCheck(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}
