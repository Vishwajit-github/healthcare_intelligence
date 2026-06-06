from src.utils.logger import log_event


# =========================================================
# ROUTER
# =========================================================

def route_after_validation(state):

    run_id = state.get("run_id")

    is_valid = state.get("is_valid")

    iteration = state.get(
        "iteration",
        0
    )

    log_event(
        run_id=run_id,
        node="router",
        event="routing_decision",
        data={
            "is_valid": is_valid,
            "iteration": iteration,
        }
    )

    # -----------------------------------------------------
    # VALID RESPONSE
    # -----------------------------------------------------

    if is_valid:

        log_event(
            run_id=run_id,
            node="router",
            event="route_end_success",
        )

        return "end"

    # -----------------------------------------------------
    # MAX RETRIES
    # -----------------------------------------------------

    if iteration >= 3:

        log_event(
            run_id=run_id,
            node="router",
            event="route_end_max_iterations",
        )

        return "end"

    # -----------------------------------------------------
    # RETRY SUPERVISOR
    # -----------------------------------------------------

    log_event(
        run_id=run_id,
        node="router",
        event="route_retry_supervisor",
    )

    return "supervisor"