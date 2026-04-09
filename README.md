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

### Creating an Agent

1. Navigate to **Agents**
2. Click **Create Agent**
3. Fill in:
   - **Name** – descriptive name, e.g. `"Research Agent"`
   - **Provider** – OpenAI or Anthropic
   - **Model** – e.g. `gpt-4o`, `claude-3-opus-20240229`
   - **System Prompt** – the agent's instructions
4. Click **Create**

### Creating a Workflow

1. Navigate to **Workflows**
2. Click **Create Workflow**
3. Fill in name and description, select agents to include
4. Click **Create**

### Creating Tasks

1. Navigate to **Tasks**
2. Click **Create Task**
3. Select the workflow and agent, provide title and JSON input data
4. Click **Create**

### Executing a Workflow

1. Navigate to **Workflows** → find your workflow → **Run**
2. Provide input data as JSON, e.g. `{"topic": "AI trends"}`
3. Click **Execute**
4. Monitor progress in the **Events** tab

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

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## License

MIT License – see LICENSE file for details.
