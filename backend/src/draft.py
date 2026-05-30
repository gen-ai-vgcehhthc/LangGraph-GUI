# draft.py — generate a workflow JSON from a plain-text user prompt

import json
import re
from collections import defaultdict, deque
from typing import Any, Dict, List

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from util import logger

# ---------------------------------------------------------------------------
# System prompt — tells the LLM what to produce
# ---------------------------------------------------------------------------

DRAFT_SYSTEM_PROMPT = """
You are a workflow architect for LangGraph-GUI.
Given a description, output a workflow as a JSON array of graph objects.

== Output format ==

Return ONLY a valid JSON array. No markdown, no explanation, no code fences.

[
  {
    "name": "root",
    "nodes": [ ...node objects... ]
  }
]

== Node object schema ==

{
  "uniq_id": "1",            // unique string integer, start from "1"
  "name": "Short Name",      // concise node label
  "description": "...",      // detailed instructions / context for this node's LLM call
  "type": "STEP",            // one of: START | STEP | TOOL | CONDITION | INFO | CREWAI
  "nexts": ["2"],            // IDs of next nodes (empty array for terminal nodes)
  "true_next": null,         // CONDITION only: node ID when condition is true
  "false_next": null,        // CONDITION only: node ID when condition is false
  "crew_config": null,
  "llm_config": null,
  "tool": "",
  "ext": { "pos_x": 0, "pos_y": 0, "width": 280, "height": 320 }
}

== Node type rules ==

START  – entry point; exactly one per graph; no incoming edges; nexts has exactly one ID.
STEP   – LLM reasoning; description = the prompt/task for the LLM.
TOOL   – terminal node (nexts is []); description = Python function source code.
CONDITION – branching; uses true_next/false_next instead of nexts (leave nexts []).
INFO   – static text appended to history; no LLM call.
CREWAI – multi-agent crew; description = crew's main task.

== Layout ==

Leave ext as { "pos_x": 0, "pos_y": 0, "width": 280, "height": 320 }.
Layout will be computed server-side.

== Example (3-node linear workflow) ==

[{"name":"root","nodes":[
  {"uniq_id":"1","name":"Start","description":"","type":"START","nexts":["2"],"true_next":null,"false_next":null,"crew_config":null,"llm_config":null,"tool":"","ext":{"pos_x":0,"pos_y":0,"width":280,"height":320}},
  {"uniq_id":"2","name":"Researcher","description":"Research the topic and summarise findings as JSON.","type":"STEP","nexts":["3"],"true_next":null,"false_next":null,"crew_config":null,"llm_config":null,"tool":"","ext":{"pos_x":0,"pos_y":0,"width":280,"height":320}},
  {"uniq_id":"3","name":"Writer","description":"Write a report based on the research. Return JSON with key 'report'.","type":"STEP","nexts":[],"true_next":null,"false_next":null,"crew_config":null,"llm_config":null,"tool":"","ext":{"pos_x":0,"pos_y":0,"width":280,"height":320}}
]}]

Now generate a workflow for the following request:

{user_prompt}
"""

# ---------------------------------------------------------------------------
# Auto-layout: BFS level assignment → evenly spaced positions
# ---------------------------------------------------------------------------

NODE_W = 280
NODE_H = 320
X_GAP = 340   # horizontal gap between sibling nodes
Y_GAP = 380   # vertical gap between levels


def auto_layout(nodes: List[Dict]) -> List[Dict]:
    """Assign pos_x / pos_y based on graph topology using BFS level assignment."""
    if not nodes:
        return nodes

    id_to_node = {n["uniq_id"]: n for n in nodes}

    # Build adjacency list (all outgoing edges)
    children: Dict[str, List[str]] = defaultdict(list)
    for n in nodes:
        for nxt in (n.get("nexts") or []):
            children[n["uniq_id"]].append(nxt)
        if n.get("true_next"):
            children[n["uniq_id"]].append(n["true_next"])
        if n.get("false_next"):
            children[n["uniq_id"]].append(n["false_next"])

    # Find start node
    start = next((n for n in nodes if n["type"] == "START"), nodes[0])

    # BFS to assign levels
    level: Dict[str, int] = {}
    queue: deque = deque([start["uniq_id"]])
    level[start["uniq_id"]] = 0
    while queue:
        nid = queue.popleft()
        for child in children.get(nid, []):
            if child not in level:
                level[child] = level[nid] + 1
                queue.append(child)

    # Group nodes by level
    by_level: Dict[int, List[str]] = defaultdict(list)
    for nid, lvl in level.items():
        by_level[lvl].append(nid)
    # Nodes not reached by BFS (isolated) go to last level + 1
    max_lvl = max(by_level.keys(), default=0)
    for n in nodes:
        if n["uniq_id"] not in level:
            max_lvl += 1
            by_level[max_lvl].append(n["uniq_id"])

    # Assign coordinates
    for lvl, ids in by_level.items():
        count = len(ids)
        total_w = count * NODE_W + (count - 1) * (X_GAP - NODE_W)
        start_x = -total_w // 2 + NODE_W // 2
        for i, nid in enumerate(ids):
            n = id_to_node[nid]
            n["ext"] = {
                "pos_x": start_x + i * X_GAP,
                "pos_y": 60 + lvl * Y_GAP,
                "width": NODE_W,
                "height": NODE_H,
            }

    return nodes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_draft(user_prompt: str, llm) -> List[Dict[str, Any]]:
    """Call the LLM to generate a workflow, then auto-layout the nodes."""
    prompt = PromptTemplate.from_template(DRAFT_SYSTEM_PROMPT)
    chain = prompt | llm | StrOutputParser()
    raw = chain.invoke({"user_prompt": user_prompt})
    logger(f"Draft raw output (first 400 chars): {raw[:400]}")

    # Strip any accidental markdown fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\n?```$", "", raw.strip(), flags=re.MULTILINE)

    graphs: List[Dict[str, Any]] = json.loads(raw.strip())

    # Apply auto-layout to every graph
    for g in graphs:
        g["nodes"] = auto_layout(g.get("nodes", []))

    return graphs
