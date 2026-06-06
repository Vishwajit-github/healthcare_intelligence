
# graph/builder.py

from langgraph.graph import StateGraph, END
from graph.state import HealthcareState

from graph.nodes.supervisor_node import supervisor_node
from graph.nodes.validator_node import validator_node
from graph.nodes.router import route_after_validation


workflow = StateGraph(HealthcareState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("validator", validator_node)

workflow.set_entry_point("supervisor")

workflow.add_edge("supervisor", "validator")

workflow.add_conditional_edges(
    "validator",
    route_after_validation,
    {
        "supervisor": "supervisor",
        "end": END
    }
)

graph = workflow.compile()   # ✅ IMPORTANT FIX