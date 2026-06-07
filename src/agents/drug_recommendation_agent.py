from langchain.agents import create_agent
from config import model

from prompts import DRUG_RECOMMENDATION_AGENT_PROMPT
from src.tools.medicine_vector_search_tool import medicine_retrieval_tool
from langchain.agents import create_agent
from langchain_community.tools import tool
from src.utils.trace_context import CURRENT_TRACE
from src.utils.agent_trace import trace_agent


@tool
def drug_recommendation_agent(clinical_context: str, action: str) -> str:
    """
    Use this specialist for informational, data-driven medicine guidance based on
    clinical reasoning.
    
    Input:
    - clinical_context: Symptoms, possible conditions, syndrome categories,
      diagnosis output from other agents, or relevant clinical context.
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.

    Available Tools:
    - medicine_vector_search_tool
        Retrieves medicine records from the curated medicine knowledge base.
        Returns medicine names, compositions, uses, side effects, safety
        information, and other product metadata.
        
    Use when the request involves:
    - possible medicines for symptoms or health conditions
    - general drug classes and representative medications
    - medicine mechanisms, uses, and typical clinical roles
    - side effects and safety considerations
    - informational medication options based on clinical reasoning
    
    You MAY optionally use web search to:
    - verify drug safety information
    - confirm side effects or contraindications
    - enrich or validate clinical knowledge when uncertain
    
    However, web search is optional and must NOT block or delay response.
    
    Do NOT use for:
    - prescribing medications
    - dosage instructions
    - guaranteeing effectiveness
    - replacing clinician or pharmacist advice
    - making definitive patient-specific treatment decisions
"""
    
    print("\nCalling Agent: Drug Recommendation Agent")
    print(f"INPUT TO DRUG RECOMMENDATION AGENT:\n{clinical_context}")

   
    result = drug_recommendation_specialist.invoke(
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

    print("\nFinished Agent: Drug Recommendation Agent")


    CURRENT_TRACE["agents"].append({
    "agent": "Drug Recommendation Agent",
    "action":action,
    "input": clinical_context,
    "output": final_output,
})

    

    return {
    "agent": "Drug Recommendation Agent",
    "action": action,
    "input": clinical_context,
    "output": final_output
}



# -----------------------------------
# DRUG RECOMMENDATION AGENT
# -----------------------------------
drug_recommendation_specialist = create_agent(
    model=model,
    tools=[medicine_retrieval_tool],
    system_prompt=DRUG_RECOMMENDATION_AGENT_PROMPT
)