import time

from langchain_core.messages import AIMessage

from src.agents.supervisor_agent import supervisor_agent

from src.utils.trace_context import (
    ensure_trace,
    trace_node_start,
    trace_node_end,
    CURRENT_TRACE,
)

from src.utils.logger import (
    log_exception,
    log_event,
    append_chat_history,
    get_chat_history,
)


def supervisor_node(state):

    # =====================================================
    # TRACE SETUP
    # =====================================================

    state, run_id = ensure_trace(state)

    CURRENT_TRACE.clear()
    CURRENT_TRACE["run_id"] = run_id
    CURRENT_TRACE["agents"] = []
    CURRENT_TRACE["started_at"] = time.time()

    start_time = trace_node_start(
        run_id=run_id,
        node="supervisor_node",
        state=state,
    )

    print("\n🔵 SUPERVISOR NODE")

    try:

        # =====================================================
        # FETCH LAST CHAT HISTORY
        # =====================================================

        history_messages = get_chat_history(
            run_id=run_id,
            limit=3,
        )

        # =====================================================
        # CURRENT USER MESSAGE
        # =====================================================

        current_messages = state["messages"]

        # =====================================================
        # MERGE HISTORY + CURRENT
        # =====================================================

        merged_messages = history_messages + current_messages

        validation_result = state.get("validation_result")

        if state.get("is_valid") is False and validation_result:
            merged_messages.append(
                {
                    "role": "user",
                    "content": f"""
Previous response failed validation.

Original user query:
{state.get("user_query", "")}

Validator reason:
{validation_result.get("reason", "")}

Fix needed:
{validation_result.get("fix_needed", "")}

Previous supervisor output:
{state.get("supervisor_output", "")}
""",
                }
            )

        # =====================================================
        # INVOKE SUPERVISOR
        # =====================================================

        result = supervisor_agent.invoke({
            "messages": merged_messages,
            "run_id": run_id,
        })

        # =====================================================
        # FINAL SUPERVISOR RESPONSE
        # =====================================================

        final_message = None

        for msg in reversed(result.get("messages", [])):
            if (
                isinstance(msg, AIMessage)
                and isinstance(msg.content, str)
                and msg.content.strip()
            ):
                final_message = msg.content
                break

        if not final_message:
            final_message = "No response generated."

        # =====================================================
        # AGENT TRACE COLLECTION (CLEAN ONLY)
        # =====================================================

        raw_agents = CURRENT_TRACE.get("agents", [])

        agent_outputs = {}

        for item in raw_agents:
            agent_name = item.get("agent")

            if not agent_name:
                continue

            agent_output = {}

            if "action" in item:
                agent_output["action"] = item.get("action")

            agent_output["input"] = item.get("input")
            agent_output["output"] = item.get("output")

            agent_outputs[agent_name] = agent_output

            log_event(
                run_id=run_id,
                agent=agent_name,
                event="agent_output",
                data=agent_output,
            )

        # =====================================================
        # GET LATEST USER MESSAGE
        # =====================================================

        latest_user_message = ""

        for msg in reversed(current_messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                latest_user_message = msg.get("content", "")
                break

        # =====================================================
        # SAVE CHAT HISTORY
        # =====================================================

        append_chat_history(
            run_id=run_id,
            user_message=latest_user_message,
            ai_message=final_message,
        )

        # =====================================================
        # TRACE OUTPUT
        # =====================================================

        output = {
            "supervisor_output": final_message,
            "iteration": state.get("iteration", 0) + 1,
        }

        trace_node_end(
            run_id=run_id,
            node="supervisor_node",
            start_time=start_time,
            output=output,
        )

        # =====================================================
        # RETURN UPDATED STATE
        # =====================================================

        return {
            **state,
            "run_id": run_id,
            "supervisor_output": final_message,
            "final_response": final_message,
            "agent_outputs": agent_outputs,
            "chat_history": history_messages,
            "messages": current_messages + [
                {
                    "role": "assistant",
                    "content": final_message,
                }
            ],
            "iteration": state.get("iteration", 0) + 1,
        }

    except Exception as exc:

        log_exception(
            run_id=run_id,
            node="supervisor_node",
            exc=exc,
        )

        raise exc