# LangGraph-GUI - AI Quick Reference

> A visual node-based workflow builder for LLM-powered applications using LangGraph.

## Project Overview

**Purpose**: GUI for creating and executing LLM workflows visually
**Version**: 2.2.1
**License**: MIT
**Architecture**: Monorepo with git submodules (frontend, backend, examples)

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  Frontend (SvelteKit + @xyflow/svelte)        Port 3000         │
│  - Visual node editor for workflow design                       │
│  - Stores graph as nodes/edges in Svelte stores                 │
│  - Exports/imports graph.json                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP API
┌─────────────────────────▼───────────────────────────────────────┐
│  Backend (FastAPI + LangGraph)                Port 5000         │
│  - Executes workflows via LangGraph StateGraph                  │
│  - Multi-user workspaces: /app/src/workspace/{username}/        │
│  - Streams execution output via SSE                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  Ollama (Local LLM)                           Port 13666        │
│  - NVIDIA CUDA 12.2 base                                        │
│  - Alternative: OpenAI GPT API                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
LangGraph-GUI/
├── backend/                 # Git submodule: FastAPI + LangGraph
│   └── src/
│       ├── main.py          # FastAPI server entry point
│       ├── WorkFlow.py      # LangGraph workflow execution (990+ lines)
│       ├── llm.py           # LLM provider abstraction (OpenAI/Ollama)
│       ├── run_graph.py     # CLI workflow runner
│       ├── NodeData.py      # Node data model
│       ├── process_handler.py  # Background process management
│       └── FileTransmit.py  # File upload/download API
│
├── frontend/                # Git submodule: SvelteKit + Svelte 5
│   └── src/routes/
│       ├── graph/           # Main workflow editor
│       │   ├── +page.svelte # Graph editor page
│       │   ├── flow/        # Graph visualization
│       │   │   ├── graphs.store.svelte.ts  # Reactive state store
│       │   │   ├── node-schema.ts          # Node type definitions
│       │   │   └── node-texture.svelte     # Node rendering
│       │   └── menu/        # UI panels
│       │       ├── sidebar.svelte
│       │       ├── ConfigWindow.svelte
│       │       └── RunWindow.svelte
│       ├── app/             # Chapter/content views
│       └── doc/             # Documentation viewer
│
├── k8s/                     # Kubernetes manifests
│   ├── namespace/           # langgraph-gui namespace
│   ├── *-deployment.yaml    # backend, frontend, ollama
│   ├── *-service.yaml       # ClusterIP services
│   ├── *-ingress.yaml       # TLS ingress rules
│   ├── NV-GPU/              # NVIDIA GPU RuntimeClass
│   └── mime/                # MIME type configmap
│
├── ollama/                  # Ollama container (CUDA 12.2)
├── nginx/                   # Reverse proxy config (auth, rate limit)
├── electron/                # Desktop app wrapper
├── examples/                # Git submodule: example workflows
├── docker-compose.yml       # Local development orchestration
└── .gitmodules              # Submodule definitions
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend Framework | SvelteKit 2.16 + Svelte 5 |
| Graph Visualization | @xyflow/svelte 1.0.2 |
| Styling | Tailwind CSS 4 |
| Build Tool | Vite 6.2 |
| Backend Framework | FastAPI (Python 3.12) |
| Workflow Engine | LangGraph + LangChain |
| LLM Providers | Ollama (local), OpenAI GPT |
| Container Runtime | Docker, Kubernetes |
| GPU Support | NVIDIA CUDA 12.2 |

## Key Files Reference

### Backend

| File | Purpose |
|------|---------|
| `backend/src/main.py:1` | FastAPI app with CORS, routes, SSE streaming |
| `backend/src/WorkFlow.py:1` | LangGraph StateGraph builder, node execution logic |
| `backend/src/llm.py:22` | `get_llm()` - LLM provider factory (GPT/Ollama) |
| `backend/src/llm.py:73` | `create_llm_chain()` - Prompt template execution |
| `backend/src/run_graph.py` | CLI entry: `python run_graph.py --llm <model> --key <key>` |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/routes/graph/+page.svelte` | Main graph editor page |
| `frontend/src/routes/graph/flow/node-schema.ts:3` | `NodeType` enum: START, STEP, TOOL, CONDITION, INFO, SUBGRAPH |
| `frontend/src/routes/graph/flow/graphs.store.svelte.ts` | Reactive stores: `currentNodes`, `currentEdges` |
| `frontend/src/routes/graph/menu/RunWindow.svelte` | Workflow execution UI |

## Node Types

```typescript
enum NodeType {
  START     // Entry point, initializes state
  STEP      // LLM prompt execution, returns JSON
  TOOL      // Calls registered Python function
  CONDITION // Boolean branch (true_next / false_next)
  INFO      // Display-only information node
  SUBGRAPH  // Nested workflow execution
}

interface JsonNodeData {
  uniq_id: string;
  name: string;
  description: string;      // Prompt template or info text
  nexts: string[];          // Next node IDs (for STEP/TOOL)
  type: string;             // NodeType value
  tool: string;             // Tool function name (for TOOL nodes)
  true_next: string | null; // Condition true branch
  false_next: string | null;// Condition false branch
  ext: { pos_x, pos_y, width, height }; // Visual position
}
```

## Backend API

```
POST /run/{username}
  Body: { llm_model: string, api_key: string }
  Response: SSE stream of execution output
  Action: Spawns run_graph.py in workspace/{username}/

GET /status/{username}
  Response: { running: boolean }

POST /chatbot/{username}
  Body: { input_string, llm_model, api_key }
  Response: { result: string }

POST /files/{username}/upload
GET  /files/{username}/download/{filename}
```

## Workflow Execution Flow

```python
# PipelineState (TypedDict)
{
  "history": str,    # Accumulated context (append-only, clipped to 16K chars)
  "task": str,       # Current task description
  "condition": bool  # For CONDITION node branching
}

# Execution: START → STEP/TOOL → CONDITION → next → ... → END
```

1. Frontend saves `graph.json` to backend workspace
2. User clicks Run → POST `/run/{username}` with LLM config
3. Backend spawns `run_graph.py` as subprocess
4. LangGraph builds `StateGraph` from nodes
5. Each node executes based on type:
   - **STEP**: LLM chain with prompt template → JSON output
   - **TOOL**: Call `tool_registry[tool_name](*args)`
   - **CONDITION**: Evaluate and route to `true_next`/`false_next`
6. Output streams via SSE to frontend

## Environment Variables

```bash
# Backend
BACKEND_PORT=5000
OLLAMA_BASE_URL=http://ollama:13666
OPENAI_API_KEY=sk-...  # For GPT models

# Ollama
OLLAMA_HOST=0.0.0.0:13666
```

## Development Commands

```bash
# Docker Compose (local dev)
docker-compose up --build

# Individual services
cd frontend && npm run dev      # Port 3000
cd backend && python src/main.py # Port 5000

# Kubernetes
kubectl apply -f k8s/namespace/
kubectl apply -f k8s/

# Frontend testing
cd frontend
npm run test:unit    # Vitest
npm run test:e2e     # Playwright
npm run lint         # ESLint + Prettier
```

## Git Submodules

```bash
# Clone with submodules
git clone --recursive <repo-url>

# Update submodules
git submodule update --init --recursive

# Submodule repos:
# - backend  → LangGraph-GUI-backend
# - frontend → LangGraph-GUI-Svelte
# - examples → examples.git
```

## Key Concepts

1. **SSOT (Single Source of Truth)**: Nodes are the source; edges derive from `nexts`, `true_next`, `false_next`
2. **History Clipping**: `clip_history()` limits context to 16K chars
3. **Tool Registry**: Python decorator `@tool` registers functions for TOOL nodes
4. **Subgraph Registry**: Nested workflows loaded from JSON files
5. **Multi-user**: Each user has isolated workspace at `/app/src/workspace/{username}/`

## Common Tasks

### Add a new node type
1. Add to `NodeType` enum in `frontend/src/routes/graph/flow/node-schema.ts`
2. Update node rendering in `node-texture.svelte`
3. Add execution logic in `backend/src/WorkFlow.py`

### Add a new LLM provider
1. Update `get_llm()` in `backend/src/llm.py`
2. Add detection pattern (e.g., `if "provider" in llm_model.lower()`)

### Add a new tool
```python
# backend/src/WorkFlow.py
@tool
def my_tool(arg1: str, arg2: int) -> str:
    """Description of what this tool does."""
    return f"Result: {arg1}, {arg2}"
```

### Deploy to Kubernetes
1. Build and push images to registry (127.0.0.1:7000)
2. Update hostPath in `k8s/*-deployment.yaml` to absolute paths
3. Apply manifests: `kubectl apply -f k8s/`

## File Formats

### graph.json
```json
{
  "nodes": [
    {
      "uniq_id": "node_1",
      "name": "Start",
      "description": "",
      "type": "START",
      "nexts": ["node_2"],
      "tool": "",
      "true_next": null,
      "false_next": null,
      "ext": { "pos_x": 100, "pos_y": 100 }
    }
  ]
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Check `allow_origins` in `backend/src/main.py:30` |
| Ollama connection failed | Verify `OLLAMA_BASE_URL` env var, check network |
| GPU not detected | Ensure NVIDIA drivers, check `nvidia-smi` |
| Submodule empty | Run `git submodule update --init --recursive` |
| K8s hostPath issues | Use absolute paths in deployment yamls |
