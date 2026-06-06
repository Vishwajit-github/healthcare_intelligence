from langchain.agents import create_agent

from config import model
from prompts import RISK_ASSESSMENT_AGENT_PROMPT
from langchain_community.tools import tool
from src.utils.agent_trace import trace_agent

@tool
def risk_assessment_agent(clinical_context: str, action: str) -> str:
    """
    Use this specialist for healthcare severity and urgency assessment.

    Input:
    - clinical_context: Symptoms, vital signs, lab values, or general patient
      condition description.
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.

    Use when the request involves:
    - risk level or severity assessment
    - urgency of medical attention
    - abnormal vital signs such as HR, BP, SpO2, or temperature
    - deciding whether symptoms are low, moderate, high, or critical risk

    Do NOT use for:
    - final diagnosis
    - prescribing medications
    - treatment planning
    """
    print("\nCalling Agent: Risk Assessment Agent")
  
    result = risk_assessment_specialist.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": clinical_context,
                }
            ]
        }
    )

    final_output = result["messages"][-1].content

    print("\nFinished Agent: Risk Assessment Agent")

    trace_agent(
        "Risk Assessment Agent",
        clinical_context,
        final_output,
        action=action
    )

    return {
    "agent": "Risk Assessment Agent",
    "action": action,
    "input": clinical_context,
    "output": final_output
}


risk_assessment_specialist = create_agent(
    model=model,
    tools=[],
    system_prompt=RISK_ASSESSMENT_AGENT_PROMPT,
)
