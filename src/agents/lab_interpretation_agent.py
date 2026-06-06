from langchain.agents import create_agent
from config import model

from prompts import LAB_INTERPRETATION_AGENT_PROMPT

from src.tools.health_markers_prediction_tool import predict_health_markers_condition
from src.tools.laboratory_multiclass_prediction_tool import predict_laboratory_disease_class
from langchain.agents import create_agent
from langchain_community.tools import tool
from src.utils.trace_context import CURRENT_TRACE
from src.utils.agent_trace import trace_agent

@tool
def lab_interpretation_agent(lab_context: str, action: str) -> str:
    """
    Use this specialist for clinical lab result interpretation.

    Input:
    - lab_context: Lab test values, reference ranges, patient context, disease
      label if available, or free-text blood work summary.
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.

    Use when the request involves:
    - interpreting blood test values
    - identifying high, low, or out-of-range lab values
    - liver, kidney, glucose, lipid, infection, anemia, or metabolic patterns
    - explaining lab abnormalities in cautious clinical terms
    - running lab or health-marker ML prediction support as part of lab interpretation

    Do NOT use for:
    - final diagnosis
    - prescribing medications
    - treatment planning

    IMPORTANT TOOL USAGE RULE:
    When all required lab parameters (gender, age, hemoglobin, RBC, WBC, AST, ALT, spirometry,
    creatinine, glucose, lipase, troponin, and optionally cholesterol/cholestrol) are present in the input,
    you MUST invoke predict_laboratory_disease_classt tool to enhance reasoning.
    If only partial values are provided, proceed with standard clinical reasoning without tool execution.
    """
    print("\nCalling Agent: Lab Interpretation Agent")
    
    tool_prompt = """
TOOL USAGE RULES

- Use `predict_laboratory_disease_class` only when all required laboratory inputs are available.
- Use `predict_health_markers_condition` only when all required health-marker inputs are available.
- If required inputs are missing, do not use the tool; perform standard interpretation and optionally request missing values.
- If inputs for both tools are complete, use both tools and combine the interpretation.
- Never expose raw model outputs, predictions, classes, or probabilities.
"""
    prompt=f"User Query {lab_context} \n{tool_prompt}"

    result = lab_interpretation_specialist.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        }
    )

    final_output = result["messages"][-1].content

    print("\nFinished Agent: Lab Interpretation Agent")
    
    trace_agent(
        "Lab Interpretation Agent",
        lab_context,
        final_output,
        action=action
    )

    return {
    "agent": "Lab Interpretation Agent",
    "action": action,
    "input": lab_context,
    "output": final_output
}


lab_interpretation_specialist = create_agent(
    model=model,
    tools=[
        predict_laboratory_disease_class,
        predict_health_markers_condition,
    ],
    system_prompt=LAB_INTERPRETATION_AGENT_PROMPT,
)
