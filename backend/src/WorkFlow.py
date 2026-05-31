# WorkFlow.py

import os
import re
import json
import time
from typing import Dict, List, TypedDict, Any, Annotated, Callable, Literal, Optional, Union
import operator
import inspect

from langgraph.graph import StateGraph, END, START

from NodeData import NodeData
from llm import get_llm, get_node_llm, clip_history, create_llm_chain
from util import logger

# Tool registry to hold information about tools
tool_registry: Dict[str, Callable] = {}
tool_info_registry: Dict[str, str] = {}
# Maps function name → TOOL node uniq_id so execute_tool can highlight the node
tool_node_id_registry: Dict[str, str] = {}

# Subgraph registry to hold all the subgraph
subgraph_registry: Dict[str, Any] = {}

# Decorator to register tools
def tool(func: Callable) -> Callable:
    signature = inspect.signature(func)
    docstring = func.__doc__ or ""
    tool_info = f"{func.__name__}{signature} - {docstring}"
    tool_registry[func.__name__] = func
    tool_info_registry[func.__name__] = tool_info
    return func

def parse_nodes_from_json(graph_data: Dict[str, Any]) -> Dict[str, NodeData]:
    """
    Parses node data from a subgraph's JSON structure.

    Args:
        graph_data: A dictionary representing a subgraph.
    Returns:
        A dictionary of NodeData objects keyed by their unique IDs.
    """
    node_map = {}
    for node_data in graph_data.get("nodes", []):
        node = NodeData.from_dict(node_data)
        node_map[node.uniq_id] = node
    return node_map

def find_nodes_by_type(node_map: Dict[str, NodeData], node_type: str) -> List[NodeData]:
    return [node for node in node_map.values() if node.type == node_type]


def escape_braces(text: str) -> str:
    """Escape { and } in user-provided text so PromptTemplate doesn't treat
    them as template variables (e.g. {"switch": true} in a description)."""
    return text.replace("{", "{{").replace("}", "}}")


class PipelineState(TypedDict):
    history: Annotated[str, operator.add]
    task: Annotated[str, operator.add]
    condition: Annotated[bool, lambda x, y: y]

def execute_step(name:str, state: PipelineState, prompt_template: str, llm) -> PipelineState:
    logger(f"{name} is working...")
    state["history"] = clip_history(state["history"])

    generation = create_llm_chain(prompt_template, llm, state["history"])
    data = json.loads(_extract_json(generation))
    
    state["history"] += "\n" + json.dumps(data)
    state["history"] = clip_history(state["history"])

    logger(state["history"])
    return state

def _extract_json(text: str) -> str:
    """Strip markdown code fences and stray control chars from an LLM response,
    then return the first complete JSON object or array found."""
    # Remove NUL and other non-printable chars but KEEP whitespace (\t \n \r)
    t = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text).strip()
    # Strip opening ```json / ``` fence
    t = re.sub(r'^```[a-zA-Z]*\s*', '', t)
    # Strip closing ``` fence
    t = re.sub(r'\s*```\s*$', '', t)
    t = t.strip()
    # Bracket-depth scan: extract first complete JSON object or array
    for start, end in [('{', '}'), ('[', ']')]:
        idx = t.find(start)
        if idx == -1:
            continue
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(t[idx:], idx):
            if esc:
                esc = False; continue
            if ch == '\\' and in_str:
                esc = True; continue
            if ch == '"':
                in_str = not in_str; continue
            if in_str:
                continue
            if ch == start:
                depth += 1
            elif ch == end:
                depth -= 1
                if depth == 0:
                    return t[idx:i + 1]
    return t  # fallback: return cleaned text as-is


def execute_tool(name: str, state: PipelineState, prompt_template: str, llm) -> PipelineState:

    logger(f"{name} is working...")

    state["history"] = clip_history(state["history"])

    generation = create_llm_chain(prompt_template, llm, state["history"])

    sanitized_generation = _extract_json(generation)

    logger(sanitized_generation)

    data = json.loads(sanitized_generation)
    
    choice = data
    tool_name = choice["function"]
    args = choice["args"]
    
    if tool_name not in tool_registry:
        raise ValueError(f"Tool {tool_name} not found in registry.")

    # Highlight the TOOL node while its function is executing
    tool_node_id = tool_node_id_registry.get(tool_name)
    if tool_node_id:
        logger(f"__NODE_START__{tool_node_id}__")

    result = tool_registry[tool_name](*args)

    if tool_node_id:
        logger(f"__NODE_END__{tool_node_id}__")

    # Flatten args to a string
    flattened_args = ', '.join(map(str, args))

    logger(f"\nExecuted Tool: {tool_name}({flattened_args})  Result is: {result}")


    state["history"] += f"\nExecuted {tool_name}({flattened_args})  Result is: {result}"
    state["history"] = clip_history(state["history"])

    return state

def condition_switch(name:str, state: PipelineState, prompt_template: str, llm) -> PipelineState:
    logger(f"{name} is working...")

    state["history"] = clip_history(state["history"])

    generation = create_llm_chain(prompt_template, llm, state["history"])
    data = json.loads(generation)
    
    condition = data["switch"]
    state["condition"] = condition
    
    state["history"] += f"\nCondition is {condition}"
    state["history"] = clip_history(state["history"])

    return state

def info_add(name: str, state: PipelineState, information: str, llm) -> PipelineState:
    logger(f"{name} is adding information...")

    # Append the provided information to the history
    state["history"] += "\n" + information
    state["history"] = clip_history(state["history"])

    return state


def execute_input(name: str, state: PipelineState, prompt: str) -> PipelineState:
    """Pause execution and wait for a user text response (file-based IPC)."""
    import time

    request_payload = json.dumps({"nodeId": name, "prompt": prompt})
    logger(f"__INPUT_REQUEST__{request_payload}__")

    input_file = "pending_input.txt"   # relative to CWD = workspace/{username}/
    # Remove any stale file from a previous run
    if os.path.exists(input_file):
        os.remove(input_file)

    deadline = time.time() + 300      # 5-minute timeout
    while time.time() < deadline:
        if os.path.exists(input_file):
            with open(input_file, "r", encoding="utf-8") as f:
                user_text = f.read().strip()
            os.remove(input_file)
            state["history"] += f"\n[User Input ({name})]: {user_text}"
            state["history"] = clip_history(state["history"])
            logger(f"__INPUT_DONE__{name}__")
            return state
        time.sleep(0.2)

    logger(f"__INPUT_TIMEOUT__{name}__")
    state["history"] += f"\n[{name}]: Input timed out."
    return state


def with_markers(node_id: str, func: Callable) -> Callable:
    """Wrap a node function so the frontend can highlight it while running."""
    def wrapped(state):
        logger(f"__NODE_START__{node_id}__")
        result = func(state)
        logger(f"__NODE_END__{node_id}__")
        return result
    return wrapped


def execute_crewai(
    name: str,
    state: PipelineState,
    task_description: str,
    crew_config: dict,
    graphs_data: Dict[str, Any],
    llm_model: str,
    api_key: str,
    node_id: str,
) -> PipelineState:
    """Run a CrewAI crew.  All exceptions are caught and written to history."""
    logger(f"{name} (CrewAI) is working...")
    try:
        # crewai is in requirements.txt — just import it
        from crewai import Agent, Task, Crew  # type: ignore

        # Process enum moved between crewai versions — handle both import paths
        try:
            from crewai import Process  # type: ignore
        except ImportError:
            from crewai.process import Process  # type: ignore  # newer versions

        cfg = crew_config or {}
        max_api_calls: int = cfg.get("max_api_calls", 10)
        process_type: str = cfg.get("process", "sequential")
        crew_subgraph: str = cfg.get("crew_subgraph", f"__crew__{node_id}")

        # Set API key in env so CrewAI's internal LLM factory can find it
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        # Resolve AGENT nodes from the linked crew subgraph
        crew_graph = next(
            (g for g in graphs_data if g.get("name") == crew_subgraph), None
        )
        if not crew_graph:
            raise ValueError(
                f"Crew subgraph '{crew_subgraph}' not found. "
                "Open the Crew Designer on the CREWAI node and add AGENT nodes."
            )

        agent_node_dicts = [
            n for n in crew_graph.get("nodes", []) if n.get("type") == "AGENT"
        ]
        if not agent_node_dicts:
            raise ValueError(
                f"No AGENT nodes found in '{crew_subgraph}'. "
                "Add at least one AGENT node in the Crew Designer."
            )

        # Build agents
        # Pass llm as a model-name string — crewai handles LLM creation internally.
        agents: list = []
        agent_cfgs: list = []
        for a in agent_node_dicts:
            try:
                acfg = json.loads(a.get("description", "{}"))
            except (json.JSONDecodeError, TypeError):
                acfg = {}
            agent_cfgs.append(acfg)
            agents.append(Agent(
                role=acfg.get("role", a.get("name", "Agent")),
                goal=acfg.get("goal", "Complete the assigned task."),
                backstory=acfg.get("backstory", "An AI agent."),
                llm=llm_model,          # string model name works across crewai versions
                max_iter=max_api_calls,
                verbose=True,
            ))

        # Build one Task per Agent.
        # If the agent JSON has a "task" key, use it; otherwise fall back to the
        # CREWAI node's description (with context injected only for the first task).
        context_str = clip_history(state["history"])
        tasks: list = []
        for i, (agent, acfg) in enumerate(zip(agents, agent_cfgs)):
            if "task" in acfg:
                desc = acfg["task"]
            else:
                desc = task_description
            if i == 0 and context_str:
                desc += f"\n\nContext from previous steps:\n{context_str}"
            tasks.append(Task(
                description=desc,
                expected_output="A comprehensive, well-structured result.",
                agent=agent,
            ))

        process = (
            Process.sequential if process_type == "sequential" else Process.hierarchical
        )
        crew = Crew(agents=agents, tasks=tasks, process=process, verbose=True)
        result = crew.kickoff()

        result_str = str(result)
        state["history"] += f"\n[CrewAI {name}]: {result_str}"
        state["history"] = clip_history(state["history"])
        logger(f"CrewAI {name} completed successfully.")

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger(f"CrewAI {name} FAILED — {error_msg}")
        state["history"] += f"\n[CrewAI Error ({name})]: {error_msg}"

    return state


def sg_add(name:str, state: PipelineState, sg_name: str) -> PipelineState:
    logger(f"{name} is working, it is a subgraph node call {sg_name} ...")
    subgraph = subgraph_registry[sg_name]
    response = subgraph.invoke(
        PipelineState(
            history=state["history"],
            task=state["task"],
            condition=state["condition"]
        )
    )
    state["history"] = response["history"]
    state["task"] = response["task"]
    state["condition"] = response["condition"]
    return state


def conditional_edge(state: PipelineState) -> Literal["True", "False"]:
    if state["condition"] in ["True", "true", True]:
        return "True"
    else:
        return "False"

def build_subgraph(node_map: Dict[str, NodeData], llm, graphs_data: List[Any] = None, llm_model: str = "", api_key: str = "") -> StateGraph:
    # Define the state machine
    subgraph = StateGraph(PipelineState)

    # Start node, only one start point
    start_node = find_nodes_by_type(node_map, "START")[0]
    logger(f"Start root ID: {start_node.uniq_id}")

    # Step nodes
    step_nodes = find_nodes_by_type(node_map, "STEP")
    for current_node in step_nodes:
        node_llm = get_node_llm(current_node.llm_config, llm, llm_model, api_key)
        desc = escape_braces(current_node.description)
        if current_node.tool:
            raw_tool_info = tool_info_registry.get(
                current_node.tool,
                f"{current_node.tool}() - (no description found; check TOOL node)"
            )
            tool_info = escape_braces(raw_tool_info)
            prompt_template = (
                "history: {history}\n"
                + desc + "\n"
                + "Available tool: " + tool_info + "\n"
                + "Based on the Available tool, provide arguments in JSON:\n"
                + '{{"function": "<func_name>", "args": [<arg1>, <arg2>, ...]}}\n'
                + "Make sure syntax is valid JSON and aligns with the function signature."
            )
            subgraph.add_node(
                current_node.uniq_id,
                with_markers(current_node.uniq_id,
                    lambda state, template=prompt_template, node_llm=node_llm, name=current_node.name: execute_tool(name, state, template, node_llm))
            )
        else:
            prompt_template = (
                "history: {history}\n"
                + desc + "\n"
                + "Reply in JSON format."
            )
            subgraph.add_node(
                current_node.uniq_id,
                with_markers(current_node.uniq_id,
                    lambda state, template=prompt_template, node_llm=node_llm, name=current_node.name: execute_step(name, state, template, node_llm))
            )

    # Add INFO nodes
    info_nodes = find_nodes_by_type(node_map, "INFO")
    for info_node in info_nodes:
        subgraph.add_node(
            info_node.uniq_id,
            with_markers(info_node.uniq_id,
                lambda state, template=info_node.description, node_llm=llm, name=info_node.name: info_add(name, state, template, node_llm))
        )

    # Add SUBGRAPH nodes
    subgraph_nodes = find_nodes_by_type(node_map, "SUBGRAPH")
    for sg_node in subgraph_nodes:
        subgraph.add_node(
            sg_node.uniq_id,
            with_markers(sg_node.uniq_id,
                lambda state, name=sg_node.name, sg_name=sg_node.name: sg_add(name, state, sg_name))
        )

    # Add CREWAI nodes
    crewai_nodes = find_nodes_by_type(node_map, "CREWAI")
    for crew_node in crewai_nodes:
        node_llm_cfg = crew_node.llm_config
        subgraph.add_node(
            crew_node.uniq_id,
            with_markers(crew_node.uniq_id,
                lambda state,
                       name=crew_node.name,
                       task_desc=crew_node.description,
                       cfg=crew_node.crew_config or {},
                       gdata=graphs_data or [],
                       model=llm_model,
                       key=api_key,
                       nid=crew_node.uniq_id,
                       nlcfg=node_llm_cfg: execute_crewai(
                           name, state, task_desc, cfg, gdata,
                           nlcfg.get("model", model) if nlcfg and not nlcfg.get("use_default", True) else model,
                           nlcfg.get("api_key", key) if nlcfg and not nlcfg.get("use_default", True) else key,
                           nid
                       ))
        )

    # Add INPUT nodes
    input_nodes = find_nodes_by_type(node_map, "INPUT")
    for inp_node in input_nodes:
        subgraph.add_node(
            inp_node.uniq_id,
            with_markers(inp_node.uniq_id,
                lambda state, name=inp_node.name, prompt=inp_node.description: execute_input(name, state, prompt))
        )

    # Edges — from start_node
    next_node_ids = start_node.nexts
    next_nodes = [node_map[next_id] for next_id in next_node_ids]

    for next_node in next_nodes:
        logger(f"Next node ID: {next_node.uniq_id}, Type: {next_node.type}")
        subgraph.add_edge(START, next_node.uniq_id)

    # Edges — from all executable nodes
    for node in step_nodes + info_nodes + subgraph_nodes + crewai_nodes + input_nodes:
        next_nodes = [node_map[next_id] for next_id in node.nexts]
        for next_node in next_nodes:
            logger(f"{node.name} {node.uniq_id}'s next node: {next_node.name} {next_node.uniq_id}, Type: {next_node.type}")
            subgraph.add_edge(node.uniq_id, next_node.uniq_id)

    # Find all condition nodes
    condition_nodes = find_nodes_by_type(node_map, "CONDITION")
    for condition in condition_nodes:
        node_llm = get_node_llm(condition.llm_config, llm, llm_model, api_key)
        desc = escape_braces(condition.description)
        condition_template = (
            desc + "\n"
            + "history: {history}\n"
            + "Decide the condition result and output ONLY this JSON (true or false):\n"
            + '{{"switch": true}}'
        )
        subgraph.add_node(
            condition.uniq_id,
            with_markers(condition.uniq_id,
                lambda state, template=condition_template, node_llm=node_llm, name=condition.name: condition_switch(name, state, template, node_llm))
        )

        logger(f"{condition.name} {condition.uniq_id}'s condition")
        logger(f"true will go {condition.true_next}")
        logger(f"false will go {condition.false_next}")
        subgraph.add_conditional_edges(
            condition.uniq_id,
            conditional_edge,
            {
                "True": condition.true_next if condition.true_next else END,
                "False": condition.false_next if condition.false_next else END
            }
        )
    return subgraph.compile()


class MainGraphState(TypedDict):
    input: Union[str, None]

def invoke_root(state: MainGraphState):
    subgraph = subgraph_registry["root"]
    history = ""
    try:
        response = subgraph.invoke(
            PipelineState(history="", task="", condition=False)
        )
        history = response.get("history", "")
    except Exception as exc:
        # Catch pipeline-level errors so __RESULT_START__/__RESULT_END__ are
        # always emitted and the frontend result panel shows what went wrong.
        error_text = f"Pipeline error — {type(exc).__name__}: {exc}"
        logger(error_text)
        history = error_text

    logger("__RESULT_START__")
    logger(history)
    logger("__RESULT_END__")
    return {"input": None}


def run_workflow_as_server(llm, llm_model: str = "", api_key: str = ""):
    # Clear registries so stale entries from a previous run don't linger
    tool_registry.clear()
    tool_info_registry.clear()
    tool_node_id_registry.clear()
    subgraph_registry.clear()

    # Load subgraph data
    with open("workflow.json", 'r') as file:
        graphs_data = json.load(file)

    # Process each subgraph (skip __crew__ designer subgraphs — handled inside CREWAI nodes)
    for graph in graphs_data:
        subgraph_name = graph.get("name")
        if subgraph_name.startswith("__crew__"):
            continue

        node_map = parse_nodes_from_json(graph)

        # Register the tool functions dynamically if has tool node, must before build graph
        for tool_node in find_nodes_by_type(node_map, "TOOL"):
            tool_code = tool_node.description
            try:
                exec(tool_code, globals())
            except Exception as exc:
                logger(f"TOOL node '{tool_node.name}' exec failed: {exc}")
                continue
            # Auto-register every top-level function defined in the TOOL code.
            # Users don't need to use the @tool decorator — any plain def works.
            for fn_name in re.findall(r'^def\s+(\w+)', tool_code, re.MULTILINE):
                fn = globals().get(fn_name)
                if not callable(fn):
                    continue
                if fn_name not in tool_registry:
                    # Register so execute_tool() can find it
                    tool_registry[fn_name] = fn
                    sig = inspect.signature(fn)
                    doc = (fn.__doc__ or "").strip()
                    tool_info_registry[fn_name] = f"{fn_name}{sig} - {doc}"
                # Map to node ID for highlight markers
                tool_node_id_registry[fn_name] = tool_node.uniq_id

        subgraph = build_subgraph(node_map, llm, graphs_data=graphs_data, llm_model=llm_model, api_key=api_key)
        subgraph_registry[subgraph_name] = subgraph

    
    # Main Graph
    main_graph = StateGraph(MainGraphState)
    main_graph.add_node("subgraph", invoke_root)
    main_graph.set_entry_point("subgraph")
    main_graph = main_graph.compile()


    # ==========================
    # Run
    # ==========================
    for state in main_graph.stream({"input": None}):
        logger(state)

    logger("__WORKFLOW_COMPLETE__")