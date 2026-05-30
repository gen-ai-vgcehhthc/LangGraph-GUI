# WorkFlow.py

import os
import re
import json
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


class PipelineState(TypedDict):
    history: Annotated[str, operator.add]
    task: Annotated[str, operator.add]
    condition: Annotated[bool, lambda x, y: y]

def execute_step(name:str, state: PipelineState, prompt_template: str, llm) -> PipelineState:
    logger(f"{name} is working...")
    state["history"] = clip_history(state["history"])

    generation = create_llm_chain(prompt_template, llm, state["history"])
    data = json.loads(generation)
    
    state["history"] += "\n" + json.dumps(data)
    state["history"] = clip_history(state["history"])

    logger(state["history"])
    return state

def execute_tool(name: str, state: PipelineState, prompt_template: str, llm) -> PipelineState:

    logger(f"{name} is working...")

    state["history"] = clip_history(state["history"])
    
    generation = create_llm_chain(prompt_template, llm, state["history"])

    # Sanitize the generation output by removing invalid control characters
    sanitized_generation = re.sub(r'[\x00-\x1F\x7F]', '', generation)

    logger(sanitized_generation)

    data = json.loads(sanitized_generation)
    
    choice = data
    tool_name = choice["function"]
    args = choice["args"]
    
    if tool_name not in tool_registry:
        raise ValueError(f"Tool {tool_name} not found in registry.")
    
    result = tool_registry[tool_name](*args)

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


def with_markers(node_id: str, func: Callable) -> Callable:
    """Wrap a node function so the frontend can highlight it while running."""
    def wrapped(state):
        logger(f"__NODE_START__{node_id}__")
        result = func(state)
        logger(f"__NODE_END__{node_id}__")
        return result
    return wrapped


def ensure_crewai():
    """Install crewai at runtime if not already present."""
    try:
        import crewai  # noqa: F401
    except ImportError:
        logger("crewai not found — installing...")
        import subprocess
        subprocess.check_call(["pip", "install", "crewai", "crewai-tools"], stdout=subprocess.DEVNULL)
        logger("crewai installed.")


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
    logger(f"{name} (CrewAI) is working...")
    ensure_crewai()

    from crewai import Agent, Task, Crew, Process  # type: ignore

    max_tokens: int = crew_config.get("max_tokens", 4096)
    max_api_calls: int = crew_config.get("max_api_calls", 10)
    process_type: str = crew_config.get("process", "sequential")
    crew_subgraph: str = crew_config.get("crew_subgraph", f"__crew__{node_id}")

    # Resolve agent nodes from the linked crew subgraph
    crew_graph = next(
        (g for g in graphs_data if g.get("name") == crew_subgraph), None
    )
    agent_node_dicts = (
        [n for n in crew_graph.get("nodes", []) if n.get("type") == "AGENT"]
        if crew_graph
        else []
    )

    # Build LLM for agents (OpenAI-compatible)
    try:
        from langchain_openai import ChatOpenAI  # type: ignore

        agent_llm = ChatOpenAI(
            model=llm_model,
            api_key=api_key,
            max_tokens=max_tokens,
        )
    except Exception:
        agent_llm = None

    agents = []
    for a in agent_node_dicts:
        try:
            cfg = json.loads(a.get("description", "{}"))
        except json.JSONDecodeError:
            cfg = {}
        agent = Agent(
            role=cfg.get("role", a.get("name", "Agent")),
            goal=cfg.get("goal", "Complete the assigned task."),
            backstory=cfg.get("backstory", "An AI agent."),
            llm=agent_llm,
            max_iter=max_api_calls,
            verbose=True,
        )
        agents.append(agent)

    if not agents:
        logger(f"{name}: no AGENT nodes found in '{crew_subgraph}', skipping crew.")
        state["history"] += f"\n[CrewAI {name}]: No agents configured."
        return state

    full_task = task_description + "\n\nContext:\n" + clip_history(state["history"])
    tasks = [
        Task(
            description=full_task,
            expected_output="A comprehensive result addressing the task.",
            agent=agents[0],
        )
    ]

    process = Process.sequential if process_type == "sequential" else Process.hierarchical
    crew = Crew(agents=agents, tasks=tasks, process=process, verbose=True)
    result = crew.kickoff()

    result_str = str(result)
    state["history"] += f"\n[CrewAI {name}]: {result_str}"
    state["history"] = clip_history(state["history"])
    logger(f"CrewAI {name} result: {result_str[:300]}")
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
        if current_node.tool:
            tool_info = tool_info_registry[current_node.tool]
            prompt_template = f"""
            history: {{history}}
            {current_node.description}
            Available tool: {tool_info}
            Based on Available tool, arguments in the json format:
            "function": "<func_name>", "args": [<arg1>, <arg2>, ...]

            next stage directly parse then run <func_name>(<arg1>,<arg2>, ...) make sure syntax is right json and align function siganture
            """
            subgraph.add_node(
                current_node.uniq_id,
                with_markers(current_node.uniq_id,
                    lambda state, template=prompt_template, node_llm=node_llm, name=current_node.name: execute_tool(name, state, template, node_llm))
            )
        else:
            prompt_template = f"""
            history: {{history}}
            {current_node.description}
            you reply in the json format
            """
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

    # Edges — from start_node
    next_node_ids = start_node.nexts
    next_nodes = [node_map[next_id] for next_id in next_node_ids]

    for next_node in next_nodes:
        logger(f"Next node ID: {next_node.uniq_id}, Type: {next_node.type}")
        subgraph.add_edge(START, next_node.uniq_id)

    # Edges — from all executable nodes
    for node in step_nodes + info_nodes + subgraph_nodes + crewai_nodes:
        next_nodes = [node_map[next_id] for next_id in node.nexts]
        for next_node in next_nodes:
            logger(f"{node.name} {node.uniq_id}'s next node: {next_node.name} {next_node.uniq_id}, Type: {next_node.type}")
            subgraph.add_edge(node.uniq_id, next_node.uniq_id)

    # Find all condition nodes
    condition_nodes = find_nodes_by_type(node_map, "CONDITION")
    for condition in condition_nodes:
        node_llm = get_node_llm(condition.llm_config, llm, llm_model, api_key)
        condition_template = f"""{condition.description}
        history: {{history}}, decide the condition result in the json format:
        "switch": True/False
        """
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
    response = subgraph.invoke(
        PipelineState(
            history="",
            task="",
            condition=False
        )
    )
    return  {"input": None}


def run_workflow_as_server(llm, llm_model: str = "", api_key: str = ""):
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
            tool_code = f"{tool_node.description}"
            exec(tool_code, globals())

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
    for state in main_graph.stream(
        {
            "input": None,
        }
    ):
        logger(state)