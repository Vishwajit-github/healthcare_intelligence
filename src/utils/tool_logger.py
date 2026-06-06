import time
import json
from src.utils.logger import log_event


# -----------------------------------
# SAFE SERIALIZER
# -----------------------------------
def safe(obj):
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


# -----------------------------------
# TOOL START
# -----------------------------------
def tool_call_start(run_id, tool_name, input_data):

    log_event(
        run_id,
        event="tool_call_start",
        node="tool",
        data={
            "tool": tool_name,
            "input": safe(input_data)
        }
    )


# -----------------------------------
# TOOL END
# -----------------------------------
def tool_call_end(run_id, tool_name, output, start_time=None):

    latency = round(time.time() - start_time, 4) if start_time else None

    log_event(
        run_id,
        event="tool_call_end",
        node="tool",
        data={
            "tool": tool_name,
            "output": safe(output),
            "latency_sec": latency
        }
    )


# -----------------------------------
# TOOL ERROR
# -----------------------------------
def tool_call_error(run_id, tool_name, error):

    log_event(
        run_id,
        event="tool_call_error",
        node="tool",
        data={
            "tool": tool_name,
            "error": str(error)
        }
    )


# -----------------------------------
# WRAPPER (RECOMMENDED)
# -----------------------------------
def wrap_tool(run_id, tool_name, tool_fn):

    def wrapped(*args, **kwargs):

        start = time.time()

        tool_call_start(
            run_id,
            tool_name,
            {
                "args": safe(args),
                "kwargs": safe(kwargs)
            }
        )

        try:
            result = tool_fn(*args, **kwargs)

            tool_call_end(
                run_id,
                tool_name,
                result,
                start
            )

            return result

        except Exception as e:

            tool_call_error(run_id, tool_name, e)
            raise

    return wrapped