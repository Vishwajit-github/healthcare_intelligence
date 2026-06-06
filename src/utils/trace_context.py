import time
import uuid
from src.utils.logger import log_event

CURRENT_TRACE = {}


def create_run_id():
    return str(uuid.uuid4())


def ensure_trace(state: dict):

    state = state or {}

    if not state.get("run_id"):
        state["run_id"] = create_run_id()

    if "evidence" not in state:
        state["evidence"] = []

    return state, state["run_id"]


def trace_node_start(run_id: str, node: str, state: dict):

    start_time = time.time()

    log_event(
        run_id,
        event=f"{node}_start",
        node=node,
        data={
            "user_query": state.get("user_query"),
            "iteration": state.get("iteration", 0),
            "evidence_count": len(state.get("evidence", [])),
        }
    )

    return start_time


def trace_node_end(run_id: str, node: str, start_time: float, output=None):

    log_event(
        run_id=run_id,
        node=node,
        event="node_end",
        data={
            "latency_sec": round(time.time() - start_time, 4),
            "output": output,
            # "used_agents": CURRENT_TRACE.get("agents", []),
        }
    )


# =========================================================
# 🔥 SINGLE SOURCE OF TRUTH FOR AGENT TRACE
# =========================================================
def trace_agent(agent_name: str, input_data=None, output_data=None, evidence=None):

    if "agents" not in CURRENT_TRACE:
        CURRENT_TRACE["agents"] = []

    CURRENT_TRACE["agents"].append({
        "agent": agent_name,
        "input": input_data,
        "output": output_data,
        "evidence": evidence or {},
        "timestamp": time.time(),
    })


def reset_trace(run_id: str):

    CURRENT_TRACE.clear()

    CURRENT_TRACE["run_id"] = run_id
    CURRENT_TRACE["agents"] = []
    CURRENT_TRACE["started_at"] = time.time()