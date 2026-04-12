# Multi-Agent Orchestrator

A platform to visually configure and run multiple AI agents to complete complex tasks. Built with FastAPI, LangGraph, Next.js, and React.

## What It Does

- **Agent Management** — Create agents with custom system prompts, model providers (OpenAI/Anthropic), and tools
- **Workflow Orchestration** — Design workflows that coordinate multiple agents together
- **Task Execution** — Execute tasks with dependency management and priority queueing
- **Real-time Streaming** — Monitor execution progress via SSE event streams
- **Dashboard Analytics** — Track success rates, task counts, and system health

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 14)                    │
│   Dashboard │ Agents │ Workflows │ Tasks │ Event Stream         │
└──────────────────────────┬────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼────────────────────────────────────┐
│                     Backend (FastAPI)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐ │
│  │  REST API   │  │ Task Queue  │  │   LangGraph Executor  │ │
│  │  /api/v1/*  │  │  (AsyncIO)   │  │   (Agent Execution)    │ │
│  └─────────────┘  └─────────────┘  └────────────────────────┘ │
└──────────────────────────┬────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   SQLite Database       │
              │   (orchestrator.db)     │
              └─────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI · LangGraph · SQLAlchemy (async) · Pydantic |
| Frontend | Next.js 14 (App Router) · TanStack Query · Zustand · Tailwind CSS |
| Database | SQLite via aiosqlite (file-based, zero-config) |
| Task Queue | AsyncIO queue with configurable worker pool |

---

## Run / Deploy

### Prerequisites

- Docker & Docker Compose **v2+**
- Python **3.11+** (for local backend development)
- Node.js **20+** (for local frontend development)
- OpenAI and/or Anthropic API keys

### Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/Samyak-jain7/multi-agent-orchestrator.git
cd multi-agent-orchestrator

# 2. Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and add your API keys

# 3. Start all services
docker-compose up --build

# 4. Access the application
#   Frontend:   http://localhost:3000
#   Backend:    http://localhost:8000
#   API Docs:   http://localhost:8000/docs
```

### Manual Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./orchestrator.db` | Async SQLite connection string |
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key (`sk-...`) |
| `ANTHROPIC_API_KEY` | Yes* | — | Anthropic API key (`sk-ant-...`) |
| `HOST` | No | `0.0.0.0` | Server bind host |
| `PORT` | No | `8000` | Server port |
| `FRONTEND_URL` | No | `http://localhost:3000` | CORS-allowed frontend origin |
| `APP_API_KEY` | No | — | If set, all `/api/*` requests require `X-API-Key` header |
| `MAX_CONCURRENT_TASKS` | No | `10` | Maximum parallel tasks in the queue |
| `TASK_TIMEOUT_SECONDS` | No | `300` | Timeout per task in seconds |
| `REDIS_URL` | No | — | Redis URL for distributed deployments (optional) |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ENV` | No | `production` | Set to `development` to enable uvicorn reload |

*\* At least one LLM provider key is required to run agents.*

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000/api/v1` | Backend API base URL |
| `NEXT_TELEMETRY_DISABLED` | No | `1` | Disable Next.js telemetry |

---

## API Reference

### Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness probe – `200` if service is up |
| GET | `/ready` | Readiness probe – `200` if DB and queue are ready |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agents` | List all agents |
| POST | `/api/v1/agents` | Create a new agent |
| GET | `/api/v1/agents/{id}` | Get agent by ID |
| PUT | `/api/v1/agents/{id}` | Update agent |
| DELETE | `/api/v1/agents/{id}` | Delete agent |

### Workflows

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/workflows` | List all workflows |
| POST | `/api/v1/workflows` | Create a new workflow |
| GET | `/api/v1/workflows/{id}` | Get workflow by ID |
| PUT | `/api/v1/workflows/{id}` | Update workflow |
| DELETE | `/api/v1/workflows/{id}` | Delete workflow + cascade delete tasks |
| POST | `/api/v1/workflows/{id}/execute` | Execute workflow (returns `task_id`) |
| GET | `/api/v1/workflows/{id}/tasks` | Get all tasks for a workflow |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tasks` | List tasks (filter by `workflow_id`, `status`) |
| POST | `/api/v1/tasks` | Create a new task |
| GET | `/api/v1/tasks/{id}` | Get task by ID |
| PUT | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Delete task |
| POST | `/api/v1/tasks/{id}/retry` | Retry a failed/cancelled task |

### Execution & Streaming

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/execution/stats` | Dashboard statistics |
| GET | `/api/v1/execution/task/{id}/status` | Get task queue status |
| GET | `/api/v1/execution/task/{id}/events` | Retrieve stored task events |
| GET | `/api/v1/execution/stream/{id}` | SSE stream for task events |
| GET | `/api/v1/execution/stream/workflow/{id}` | SSE stream for workflow events |
| GET | `/api/v1/execution/logs/{workflow_id}` | Get execution logs for a workflow |
| POST | `/api/v1/execution/log` | Create an execution log entry |

---

## Usage Guide

### System Prompt Engineering

The **System Prompt** is the most critical field when creating an agent. It defines:
- Who the agent is and what it does
- How it should behave and respond
- What output format it should produce
- Any constraints or rules it must follow

**Tips for effective prompts:**
- Be specific about the role (e.g., "You are a senior financial analyst specializing in SaaS companies")
- Define output format clearly (e.g., "Always return your analysis as JSON with fields: summary, metrics{}, risks[]")
- Set boundaries (e.g., "Never invent data. If you don't know, say so.")
- Include fallback behavior (e.g., "If the input is unclear, ask clarifying questions")

**Example system prompt:**
```
You are a market research analyst. Your role:
1. Analyze the given topic thoroughly using web search
2. Identify key players, market size, and trends
3. Summarize findings in a structured report

Output format (always follow this exact JSON structure):
{
  "topic": "<the topic analyzed>",
  "key_players": ["<company 1>", "<company 2>"],
  "market_size": "<estimated size with source>",
  "trends": ["<trend 1>", "<trend 2>", "<trend 3>"],
  "risks": ["<risk 1>", "<risk 2>"],
  "summary": "<2-3 paragraph executive summary>"
}

Rules:
- Only use verified information from searches
- Do not guess or fabricate data
- If a section cannot be completed, use null for that field
```

### Creating an Agent

1. Navigate to **Agents**
2. Click **Create Agent**
3. Fill in:
   - **Name** – descriptive name, e.g. `"Research Agent"`
   - **Provider** – select from OpenAI, Anthropic, MiniMax, or Ollama
   - **Model** – dropdown auto-updates based on selected provider (recommended models shown with descriptions)
   - **System Prompt** – the agent's instructions (see System Prompt Engineering above)
4. Click **Create**

### Creating a Workflow

1. Navigate to **Workflows**
2. Click **Create Workflow**
3. Fill in name and description, select agents to include (order matters — agents execute in the order listed)
4. Click **Create**

### Input Data Format

When executing a workflow, **Input Data** is passed as JSON to every agent in the pipeline. Each agent's task-level `input_data` gets merged with the workflow's global input at runtime.

**Example — Market Research Workflow:**
```json
{
  "topic": "AI coding assistants in 2024",
  "depth": "comprehensive",
  "target_audience": "enterprise CTOs"
}
```

**How agents access input:** Each agent receives `input_data` in their execution state. The fields drive what the agent works on.

**Passing agent-specific input:**
```json
{
  "query": "What are the top 5 trends in AI?",
  "search_depth": "shallow",
  "output_format": "bullet_points"
}
```

### Executing a Workflow

1. Navigate to **Workflows** → find your workflow → click **Run**
2. Provide input data as JSON, e.g. `{"topic": "AI trends"}`
3. Click **Execute**
4. Monitor progress in the **Events** tab (real-time SSE stream)

### Where to Find Output

After a workflow completes, output is stored at two levels:

**Task-level output** (each agent's individual result):
- Available via `GET /api/v1/execution/task/{task_id}/status`
- Frontend: **Tasks** tab → click "View Details" → scroll to **Output** section

**Workflow-level output** (aggregated from all tasks):
- Available via `GET /api/v1/workflows/{id}`
- Frontend: **Workflows** tab → "Details" → completed workflows show aggregated `task_results`

**Sample task output (JSON):**
```json
{
  "result": "The market research analysis is complete. Key findings:\n\n**Topic:** AI coding assistants in 2024\n\n**Key Players:** GitHub Copilot, Cursor AI, Replit Agent...\n\n**Market Size:** $4.5B globally (Grand View Research), growing at 28% CAGR...",
  "metadata": {
    "model": "MiniMax-M2.7",
    "tokens_used": 1842,
    "latency_ms": 2340
  }
}
```

### Agent Best Practices

1. **One agent, one job** — Don't overload a single agent with too many responsibilities
2. **Clear output contracts** — Always specify what format the agent should return in the system prompt
3. **Dependency order matters** — When creating a workflow, add agents in execution order (e.g., research → analyze → report)
4. **Input data shapes behavior** — The JSON you pass at workflow execution time drives agent behavior
5. **System prompt examples** — Include 1-2 examples of ideal inputs/outputs in complex prompts

### Model Recommendations

| Provider | Best For | Recommended Model |
|----------|----------|-------------------|
| **OpenAI** | General purpose, complex reasoning | `gpt-4o` or `gpt-4o-mini` |
| **Anthropic** | Long context, complex reasoning | `claude-3-5-sonnet-20241022` or `claude-3-opus-20240229` |
| **MiniMax** | Cost-effective, fast, 204k context | `MiniMax-M2.7` or `MiniMax-M2.7-highspeed` |
| **Ollama** | Local/self-hosted models | `llama3.1`, `mistral`, `codellama` |

OpenAI is set as the default provider for new agents.

### Workflow Execution Flow

1. **Create agents** (e.g., Research Agent, Writer Agent)
2. **Create workflow** → assign agents in order
3. **Execute workflow** → pass global input JSON
4. **Monitor** → Events tab for real-time streaming
5. **Inspect results** → Tasks tab or workflow detail modal

---

## Project Structure

```
multi-agent-orchestrator/
├── backend/
│   ├── agents/
│   │   ├── executor.py      # LangGraph-based agent executor
│   │   └── queue.py         # AsyncIO task queue with pub/sub
│   ├── api/
│   │   ├── agents.py        # Agent CRUD endpoints
│   │   ├── workflows.py     # Workflow CRUD + execute endpoints
│   │   ├── tasks.py         # Task CRUD + retry endpoints
│   │   └── execution.py     # Streaming + stats endpoints
│   ├── core/
│   │   └── database.py      # SQLAlchemy async engine setup
│   ├── models/
│   │   └── execution.py     # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── __init__.py      # Pydantic request/response schemas
│   ├── main.py              # FastAPI app, middleware, routes
│   ├── Dockerfile           # Multi-stage production build
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router
│   │   ├── components/      # React components
│   │   ├── lib/             # API client, store, utilities
│   │   └── types/           # TypeScript type definitions
│   ├── Dockerfile           # Multi-stage Next.js production build
│   ├── package.json
│   └── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml           # Lint, test, Docker build pipeline
├── docker-compose.yml       # Full-stack local dev + production compose
└── README.md
```

---

## Docker Deployment

### Production

```bash
docker-compose -f docker-compose.yml up --build -d
```

### Scale

```bash
# Scale backend instances (requires shared filesystem or Redis)
docker-compose up -d --scale backend=3

# Scale frontend CDN (use a separate CDN in front of the service)
docker-compose up -d --scale frontend=2
```

### Logs

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

---

## Troubleshooting

### "no such column: workflows.output"

The database schema is stale after a recent update. Run this once on your server:

```bash
docker exec orchestrator-backend python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/orchestrator.db')
cur = conn.cursor()
cur.execute('ALTER TABLE workflows ADD COLUMN output TEXT')
conn.commit()
print('Migrated:', [row[1] for row in cur.execute('PRAGMA table_info(workflows)').fetchall()])
conn.close()
"
```

Then restart the backend:
```bash
docker-compose restart backend
```

### Workflow executes but shows no output

- Check the **Tasks** tab — did tasks get created? If the workflow has agents but no tasks appear, the task auto-creation may have failed.
- Check the **Events** tab for real-time errors during execution.
- Verify the API key for your LLM provider is set correctly in `backend/.env`.
- If using MiniMax, ensure `MINIMAX_API_KEY` is set and `MINIMAX_BASE_URL=https://api.minimax.io/v1`.

### Frontend not loading or returning 500 errors

- Ensure the backend is running: `docker-compose logs backend`
- Check the browser console for CORS errors — ensure `FRONTEND_URL` in backend `.env` matches your frontend URL (e.g., `http://localhost:3000` for local dev).
- If the DB has schema mismatches, rebuild: `docker-compose down -v && docker-compose up --build` (WARNING: this deletes all data).

### Buttons not working / forms not submitting

- Check `docker-compose logs backend` for the actual error.
- If seeing middleware errors, check that `APP_API_KEY` is set if enabled, and that you're sending the `X-API-Key` header.
- Verify the database file is writable: `docker exec orchestrator-backend ls -la /app/data/`

### MiniMax API errors (401 / 403)

- Verify your MiniMax API key is correct in `backend/.env`.
- Check `MINIMAX_BASE_URL` is set to `https://api.minimax.io/v1` (not the default OpenAI endpoint).
- Ensure your MiniMax account has credits — keys from platform.minimax.io are pay-as-you-go.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## License

MIT License – see LICENSE file for details.
