import json

from config import model

from src.utils.trace_context import (
    ensure_trace,
    trace_node_start,
    trace_node_end,
)

from src.utils.logger import (
    log_exception,
)

from prompts.validator_prompt import VALIDATOR_PROMPT
from langchain_core.prompts import ChatPromptTemplate

# =========================================================
# VALIDATOR NODE
# =========================================================

def validator_node(state):

    state, run_id = ensure_trace(state)

    start_time = trace_node_start(
        run_id=run_id,
        node="validator_node",
        state=state,
    )

    print("\n🟢 VALIDATOR NODE")

    try:
                
        prompt = ChatPromptTemplate.from_messages([
            ("system", VALIDATOR_PROMPT),
            ("human", """
        USER QUERY:
        {user_query}
        
        SUPERVISOR OUTPUT:
        {supervisor_output}
        
        AGENT OUTPUTS:
        {agent_outputs}
        
        """)
        ])

        prompt = prompt.format(
    user_query=state["user_query"],
    supervisor_output=state["supervisor_output"],
    agent_outputs=state["agent_outputs"].keys()
)
        result = model.invoke(
            [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        try:

            parsed = json.loads(
                result.content
            )

        except Exception:

            parsed = {
                "is_valid": False,
                "risk_level": "moderate",
                "reason": "validator_json_parse_error",
                "fix_needed": "Validator failed to parse response.",
            }

        trace_node_end(
            run_id=run_id,
            node="validator_node",
            start_time=start_time,
            output=parsed,
        )

        return {
            **state,

            "run_id": run_id,

            "validation_result": parsed,

            "validation_risk_level": parsed.get(
                "risk_level",
                "unknown"
            ),

            "is_valid": parsed.get(
                "is_valid",
                False
            ),

            "final_response": state.get(
                "final_response"
            ) or state.get(
                "supervisor_output"
            ),
        }

    except Exception as exc:

        log_exception(
            run_id=run_id,
            node="validator_node",
            exc=exc,
        )

        raise exc