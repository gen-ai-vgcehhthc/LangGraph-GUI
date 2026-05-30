# LangGraph-GUI — CrewAI Extension

This fork extends [LangGraph-GUI](https://github.com/LangGraph-GUI/LangGraph-GUI) with a **CrewAI node type** that lets you design and run multi-agent crews directly inside the visual graph editor.

---

## New Features

### 1. CREWAI Node Type

A new node type `CREWAI` is available alongside the existing `STEP`, `TOOL`, `CONDITION`, `INFO`, and `SUBGRAPH` types.

When you add a node and set its type to **CREWAI**, the node exposes:

| Field | Description |
|---|---|
| **Max Tokens** | Upper token limit per LLM call inside the crew |
| **Max API Calls** | Maximum number of LLM iterations each agent may make |
| **Process** | `sequential` (agents run in order) or `hierarchical` (a manager delegates tasks) |
| **Crew Task** | The overall objective you want the crew to accomplish |

### 2. Crew Designer Tab

Click **Open Crew Designer** on a CREWAI node to open a dedicated subgraph named `__crew__<nodeId>`.

Inside this subgraph you design your crew by adding **AGENT** nodes. Each AGENT node stores its configuration as JSON in its description field:

```json
{
  "role": "Senior Researcher",
  "goal": "Uncover groundbreaking insights about the topic.",
  "backstory": "You are a veteran researcher with a knack for finding hidden patterns.",
  "tools": []
}
```

You can add as many AGENT nodes as needed. They will all be assembled into a single CrewAI `Crew` at runtime.

### 3. Token & API Call Limits

Both limits are enforced per CREWAI node:

- **max_tokens** — passed as `max_tokens` to the underlying `ChatOpenAI` instance used by every agent in the crew.
- **max_api_calls** — passed as `max_iter` to each `crewai.Agent`, capping the number of reasoning iterations.

### 4. Automatic Runtime Environment

The backend detects whether `crewai` is installed before executing a CREWAI node. If it is missing it runs:

```bash
pip install crewai crewai-tools
```

This means you do not need to pre-install CrewAI — it is bootstrapped on first use.

---

## How It Works (Architecture)

```
Frontend (Svelte)
  └─ CREWAI node selected
       ├─ shows Max Tokens / Max API Calls / Process inputs
       ├─ "Open Crew Designer" → switches to __crew__<id> subgraph
       └─ AGENT nodes in that subgraph hold role/goal/backstory JSON

Serialization
  └─ GraphsToJson() serializes all subgraphs (including __crew__ ones)
       into workflow.json and uploads to backend

Backend (FastAPI + LangGraph)
  └─ run_workflow_as_server() skips __crew__ subgraphs as top-level graphs
  └─ build_subgraph() wires CREWAI nodes as LangGraph nodes
  └─ execute_crewai() at runtime:
       1. Ensures crewai is installed
       2. Reads AGENT nodes from the __crew__ subgraph
       3. Builds crewai.Agent objects with role/goal/backstory
       4. Runs crewai.Crew with the configured process and limits
       5. Appends the crew result to the LangGraph pipeline state
```

---

## Quick Start

### Prerequisites

Same as the base project — Docker Compose (or local Python + Node.js).

### Run with Docker Compose

```bash
git clone https://github.com/gen-ai-vgcehhthc/LangGraph-GUI
cd LangGraph-GUI
docker compose up
```

Open `http://localhost` in your browser.

### Design a CrewAI Workflow

1. Open the graph editor.
2. Add a `START` node and a `CREWAI` node, connect them.
3. On the CREWAI node set **Max Tokens**, **Max API Calls**, **Process**, and the **Crew Task** description.
4. Click **Open Crew Designer** — the view switches to the `__crew__<id>` subgraph.
5. Add one or more `AGENT` nodes. In each node's description field paste JSON:
   ```json
   {"role": "...", "goal": "...", "backstory": "..."}
   ```
6. Navigate back to `root` (use the subgraph dropdown).
7. Click **Run**, provide your LLM model name and API key.

The backend will assemble the crew and stream results back in real time.

---

## Collaborative Development

This repository is set up as a multi-contributor project under the `gen-ai-vgcehhthc` GitHub organization.

- **Frontend** lives in `frontend/` (Svelte submodule).
- **Backend** lives in `backend/` (Python/FastAPI submodule).
- Open issues and PRs against this repo for feature requests and bug reports.
- Use feature branches and pull requests — the `main` branch is protected.

---

## CrewAI Node — Field Reference

### CREWAI node (`crew_config` JSON stored in the workflow)

```json
{
  "max_tokens": 4096,
  "max_api_calls": 10,
  "process": "sequential",
  "crew_subgraph": "__crew__<nodeId>"
}
```

### AGENT node description (free-text JSON in the Description / Agent JSON field)

```json
{
  "role": "Role title shown to the LLM",
  "goal": "What this agent is trying to achieve",
  "backstory": "Persona / background context for the agent",
  "tools": []
}
```

---

## License

Same as upstream — MIT.
