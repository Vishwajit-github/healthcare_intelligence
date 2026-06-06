from langchain.agents import create_agent
from config import model
from prompts import SYMPTOM_ASSISTANCE_AGENT_PROMPT
from langchain_community.tools import tool
from src.utils.trace_context import CURRENT_TRACE
from src.utils.agent_trace import trace_agent

@tool
def symptom_assistance_agent(symptoms: str, action: str) -> str:
    """
    Use this specialist for symptom support and triage-style guidance.

    Input:
    - symptoms: User's symptom description, including severity, duration, and
      any concerns they mention.
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.

    Use when the request involves:
    - symptom explanation or reassurance
    - safe self-care guidance
    - red flag or watch-out symptom checks
    - anxiety around physical symptoms

    Do NOT use for:
    - final diagnosis
    - prescribing prescription medication
    - replacing emergency care
    """
    print("\nCalling Agent: Symptom Assistance Agent")

    result = symptom_assistance_specialist.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": symptoms,
                }
            ]
        }
    )

    final_output = result["messages"][-1].content

    print("\nFinished Agent: Symptom Assistance Agent")

    
    trace_agent(
    "Symptom Assistance Agent",
    symptoms,
    final_output,
    action=action
)


    return {
    "agent": "Symptom Assistance Agent",
    "action": action,
    "input": symptoms,
    "output": final_output
}



symptom_assistance_specialist= create_agent(
    model=model,
    tools=[],
    system_prompt=SYMPTOM_ASSISTANCE_AGENT_PROMPT,
)
