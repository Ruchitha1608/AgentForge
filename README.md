# AgentForge

Multi-agent task orchestration. Breaks complex tasks into parallel subtasks across specialist AI agents — completing them faster than any single agent could.

**Live demo:** [agentforge.vercel.app](https://agentforge.vercel.app)
**API:** [your-ec2-ip/health](http://your-ec2-ip/health)

## Benchmark results

| Metric | Result |
|--------|--------|
| Parallel vs sequential | **3.65x faster** |
| Agents | 4 specialist types (Research, Code, Analysis, Writer) |
| Cache hit response | <0.5s vs ~20s cold |
| Max concurrent agents | 10 |

*Real numbers from `/benchmark` endpoint — not fabricated.*

## Architecture

```
User → Next.js (Vercel)
          ↓ POST /run
     FastAPI Orchestrator (AWS EC2)
          ↓ asyncio.gather()
  ┌──────────┬────────┬──────────┬────────┐
Research   Code   Analysis  Writer
  └──────────┴────────┴──────────┴────────┘
          ↓ Redis cache (EC2, 1hr TTL)
     Synthesized final answer
          ↓
     Back to UI
```

**Sequential time** (same task, one agent at a time): ~57.5s
**Parallel time** (asyncio.gather): ~15.7s
**Speedup: 3.65x**

## Stack

- **Backend:** Python 3.11, FastAPI, OpenAI `gpt-4o-mini`, asyncio
- **Frontend:** Next.js 16, TypeScript, Tailwind CSS
- **Memory:** Redis (1hr TTL per subtask)
- **Deploy:** AWS EC2 t2.micro (backend) + Vercel (frontend)

## Quick start

```bash
git clone https://github.com/yourusername/agentforge
cd agentforge
cp backend/.env.example backend/.env
# Add your OPENAI_API_KEY to backend/.env
docker compose up --build
```

Open http://localhost:3000

## Local dev (no Docker)

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

## AWS deployment

```bash
# 1. Launch EC2 t2.micro Ubuntu 22.04, open ports 22 + 80

# 2. On the instance:
chmod +x setup.sh && ./setup.sh

# 3. Edit backend/.env with your OPENAI_API_KEY, then:
systemctl start agentforge

# 4. Deploy updates from local:
EC2_IP=your.ip.here ./deploy.sh
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/run` | Run a task through the full pipeline |
| `GET` | `/health` | Redis + model status |
| `GET` | `/benchmark` | Cold vs cached timing comparison |

### POST /run example

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Compare PostgreSQL vs MongoDB for a startup"}'
```

Response:
```json
{
  "session_id": "af44ac88",
  "plan": "...",
  "subtask_results": { ... },
  "final_answer": "...",
  "parallel_time": 15.75,
  "sequential_time": 57.52,
  "speedup": 3.65,
  "agents_used": 3
}
```
