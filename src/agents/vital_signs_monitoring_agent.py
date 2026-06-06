from langchain.agents import create_agent

from config import model
from prompts import VITAL_SIGNS_MONITORING_AGENT_PROMPT
from src.tools.vital_signs_prediction_tool import predict_vital_signs_risk_category
from langchain_community.tools import tool
from src.utils.tool_logger import (
    tool_call_start,
    tool_call_end,
    tool_call_error
)
from src.utils.agent_trace import trace_agent
import time



@tool
def vital_signs_monitoring_agent(vital_context: str, action: str) -> str:
    """
    Use this specialist for vital signs monitoring and physiological risk signals.

    Input:
    - vital_context: Heart rate, respiratory rate, blood pressure, SpO2,
      temperature, derived vital metrics, and patient context if available.
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.

    Use when the request involves:
    - evaluating whether vital signs are normal, high, low, or abnormal
    - detecting unstable vital sign patterns
    - identifying warning signs from vitals
    - assessing physiological stability from vital data

    Do NOT use for:
    - final diagnosis
    - prescribing medications
    - treatment planning
    """

    vital_tool_prompt = """
    TOOL USAGE RULES
    
    - Use `predict_vital_signs_risk_category` only when all required vital sign inputs are available.
    - If any required inputs are missing, do not invoke the tool; perform standard vital-sign interpretation and optionally request missing values.
    - Use the tool output only to support physiological risk assessment.
    - Never expose raw model outputs, predictions, classes, categories, or probabilities.
    """
    print("\nCalling Agent: Vital Signs Monitoring Agent")
    vital_context= f"User Query: {vital_context} \n\n {vital_tool_prompt}"
    result = vital_signs_monitoring_specialist.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": vital_context,
                }
            ]
        }
    )

    final_output = result["messages"][-1].content

    print("\nFinished Agent: Vital Signs Monitoring Agent")

    trace_agent(
        "Vital Signs Monitoring Agent",
        vital_context,
        final_output,
        action=action
    )

    return {
    "agent": "Vital Signs Monitoring Agent",
    "action": action,
    "input": vital_context,
    "output": final_output
}



# -----------------------------------
# AGENT (UNCHANGED STRUCTURE)
# -----------------------------------
vital_signs_monitoring_specialist = create_agent(
    model=model,
    tools=[predict_vital_signs_risk_category],
    system_prompt=VITAL_SIGNS_MONITORING_AGENT_PROMPT,
)