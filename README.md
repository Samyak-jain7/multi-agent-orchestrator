# Multi-Agent Orchestrator

A platform to visually configure and run multiple AI agents to complete complex tasks. Built with FastAPI, LangGraph, Next.js, and React.

## Features

- **Agent Management**: Create and configure AI agents with custom system prompts, model providers (OpenAI, Anthropic), and tools
- **Workflow Orchestration**: Design workflows that coordinate multiple agents to work together
- **Task Execution**: Execute tasks with dependency management and priority queueing
- **Real-time Streaming**: Monitor execution progress with live event streaming
- **Dashboard Analytics**: Track success rates, task counts, and system health

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
│   Dashboard │ Agents │ Workflows │ Tasks │ Event Stream        │
└──────────────────────────┬────────────────────────────────────┘
                           │ HTTP/SSE
┌──────────────────────────▼────────────────────────────────────┐
│                     Backend (FastAPI)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐ │
│  │  REST API   │  │ Task Queue  │  │   LangGraph Executor  │ │
│  │  /api/v1/*  │  │  (Async)    │  │   (Agent Execution)    │ │
│  └─────────────┘  └─────────────┘  └────────────────────────┘ │
└──────────────────────────┬────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   SQLite Database       │
              │   (orchestrator.db)      │
              └─────────────────────────┘
```

### Backend Stack
- **FastAPI**: High-performance async web framework
- **LangGraph**: Graph-based agent orchestration
- **SQLAlchemy + aiosqlite**: Async database ORM
- **Pydantic**: Data validation and serialization

### Frontend Stack
- **Next.js 14**: React framework with App Router
- **TanStack Query**: Async state management and caching
- **Zustand**: Lightweight state management
- **Tailwind CSS**: Utility-first styling

## Getting Started

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (for OpenAI models)
- Anthropic API key (for Claude models)

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/Samyak-jain7/multi-agent-orchestrator.git
cd multi-agent-orchestrator
```

2. Create a `.env` file in the backend directory:
```bash
cp backend/.env.example backend/.env
```

3. Edit `backend/.env` and add your API keys:
```env
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

4. Start the services:
```bash
docker-compose up --build
```

5. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Manual Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Reference

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
| DELETE | `/api/v1/workflows/{id}` | Delete workflow |
| POST | `/api/v1/workflows/{id}/execute` | Execute workflow |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tasks` | List all tasks |
| POST | `/api/v1/tasks` | Create a new task |
| GET | `/api/v1/tasks/{id}` | Get task by ID |
| PUT | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Delete task |
| POST | `/api/v1/tasks/{id}/retry` | Retry failed task |

### Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/execution/stats` | Get dashboard statistics |
| GET | `/api/v1/execution/task/{id}/status` | Get task execution status |
| GET | `/api/v1/execution/task/{id}/events` | Get task events |
| GET | `/api/v1/execution/stream/{id}` | SSE stream for task |
| GET | `/api/v1/execution/stream/workflow/{id}` | SSE stream for workflow |

## Usage Guide

### Creating an Agent

1. Navigate to the **Agents** tab
2. Click **Create Agent**
3. Fill in the details:
   - **Name**: A descriptive name (e.g., "Research Agent")
   - **Description**: What the agent does
   - **Provider**: OpenAI or Anthropic
   - **Model**: e.g., gpt-4o, claude-3-opus
   - **System Prompt**: The agent's instructions
4. Click **Create**

### Creating a Workflow

1. Navigate to the **Workflows** tab
2. Click **Create Workflow**
3. Fill in the details:
   - **Name**: A descriptive name (e.g., "Market Research")
   - **Description**: What the workflow accomplishes
   - **Agents**: Select agents to include
4. Click **Create**

### Creating Tasks

1. Navigate to the **Tasks** tab
2. Click **Create Task**
3. Fill in the details:
   - **Workflow**: Select which workflow this task belongs to
   - **Agent**: Select which agent executes this task
   - **Title**: Task name
   - **Input Data**: JSON input for the task
   - **Priority**: Higher = runs first
4. Click **Create**

### Executing a Workflow

1. Navigate to the **Workflows** tab
2. Find your workflow and click **Run**
3. Provide input data as JSON (e.g., `{"topic": "AI trends"}`)
4. Click **Execute**
5. Monitor progress in the **Events** tab

## Configuration

### Environment Variables

#### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database URL | `sqlite+aiosqlite:///./orchestrator.db` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `MAX_CONCURRENT_TASKS` | Max parallel tasks | `10` |
| `TASK_TIMEOUT_SECONDS` | Task timeout | `300` |

#### Frontend (`frontend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000/api/v1` |

## Docker Deployment

### Production Build

```bash
docker-compose -f docker-compose.yml up --build -d
```

### Scale Services

```bash
# Scale backend instances
docker-compose up -d --scale backend=3

# Scale frontend instances
docker-compose up -d --scale frontend=2
```

### View Logs

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Project Structure

```
multi-agent-orchestrator/
├── backend/
│   ├── agents/
│   │   ├── executor.py      # LangGraph agent executor
│   │   ├── queue.py         # Async task queue
│   │   └── __init__.py
│   ├── api/
│   │   ├── agents.py        # Agent CRUD endpoints
│   │   ├── workflows.py     # Workflow endpoints
│   │   ├── tasks.py         # Task endpoints
│   │   ├── execution.py     # Execution/streaming endpoints
│   │   └── __init__.py
│   ├── core/
│   │   ├── database.py      # Database configuration
│   │   └── __init__.py
│   ├── models/
│   │   ├── execution.py    # SQLAlchemy models
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── __init__.py      # Pydantic schemas
│   ├── main.py              # FastAPI application
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ui/           # UI primitives
│   │   │   ├── Dashboard.tsx
│   │   │   ├── AgentList.tsx
│   │   │   ├── WorkflowList.tsx
│   │   │   ├── TaskList.tsx
│   │   │   ├── EventStream.tsx
│   │   │   └── QueryProvider.tsx
│   │   ├── lib/
│   │   │   ├── api.ts        # API client
│   │   │   ├── store.ts      # Zustand store
│   │   │   └── utils.ts
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues and feature requests, please open a GitHub issue.
