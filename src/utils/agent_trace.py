import time
from src.utils.trace_context import CURRENT_TRACE


def trace_agent(agent_name: str, input_data=None, output_data=None, evidence=None, action=None):
    """
    Unified agent trace writer.

    This guarantees:
    - consistent logging for ALL tools
    - supervisor can always reconstruct used_agents + inputs + outputs
    - no missing medical imaging trace issues
    """

    if "agents" not in CURRENT_TRACE:
        CURRENT_TRACE["agents"] = []

    agent_trace = {
        "agent": agent_name,
        "input": input_data,
        "output": output_data,
        "evidence": evidence or {},
        "timestamp": time.time(),
    }

    if action is not None:
        agent_trace["action"] = action

    CURRENT_TRACE["agents"].append(agent_trace)