from langchain.agents import create_agent

from config import model
from prompts import DIAGNOSTIC_REASONING_AGENT_PROMPT
from langchain.agents import create_agent
from langchain_community.tools import tool
from src.utils.agent_trace import trace_agent


@tool
def diagnostic_syndrome_reasoning_agent(clinical_context: str, action: str) -> str:
    """
    Use this specialist for clinical reasoning, possible conditions,
    syndrome categories, and next diagnostic steps.

    Input:
    - clinical_context: Symptoms, vitals, labs, risk level,
      imaging findings, or patient clinical context.
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.

    Use when the request involves:
    - possible causes or conditions
    - differential diagnosis style reasoning
    - disease or syndrome categories
    - body-system reasoning
    - next diagnostic tests or evaluations
    - consultation recommendations
    - prioritizing evaluation urgency

    Do NOT use for:
    - final diagnosis
    - prescribing medications
    - treatment planning
    """

    print("\nCalling Agent: Diagnostic Reasoning Specialist")
    print(f"INPUT TO DIAGNOSTIC REASONING SPECIALIST:\n{clinical_context}")

 
    result = diagnostic_reasoning_specialist.invoke(
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

    print("\nFinished Agent: Diagnostic Reasoning Specialist")

    trace_agent(
        "Diagnostic Reasoning Agent",
        clinical_context,
        final_output,
        action=action
    )

    return {
    "agent": "Diagnostic Reasoning Agent",
    "action": action,
    "input": clinical_context,
    "output": final_output
}



diagnostic_reasoning_specialist = create_agent(
    model=model,
    tools=[],
    system_prompt=DIAGNOSTIC_REASONING_AGENT_PROMPT,
)
