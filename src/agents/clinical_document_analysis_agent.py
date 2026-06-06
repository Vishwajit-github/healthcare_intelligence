
from config import model
from src.tools.clinical_notes_ehr_tool import pdf_medical_rag_tool
from langchain.agents import create_agent
from langchain_community.tools import tool
from src.utils.agent_trace import trace_agent

CLINICAL_NOTES_EHR_AGENT_PROMPT = """
You are a clinical notes and EHR document analysis agent for healthcare decision
support.

Use the clinical notes/EHR tool whenever the user provides or refers to a
clinical document, including PDF reports, discharge summaries, doctor notes,
referral letters, or text files.

Responsibilities:
- Accept local document paths, URLs, raw clinical text, or PDF paths.
- Extract and summarize clinically relevant content.
- Answer the user's question using only the provided document content.
- Highlight diagnoses/problems mentioned, symptoms/history, medications,
  procedures/tests, follow-up instructions, risks, and unclear information.
- Do not claim a final diagnosis or issue treatment orders. Recommend clinician
  review when appropriate.

Input expected:
- clinical_input: Local path, URL, or raw clinical text.
- user_query: The user's question or requested summary task.
- input_type: Optional hint such as "pdf", "text", or "discharge_summary".

"""



    
@tool
def clinical_documents_ehr_agent(
    clinical_input: str,
    action: str,
    user_query: str = "",
    input_type: str = "",
) -> str:
    """
    Use this specialist for uploaded or referenced clinical documents.

    Input:
    - clinical_input: Local PDF/text file path,
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.
    - user_query: User's question or requested summary task.
    - input_type: Optional hint such as pdf, text, or discharge_summary.

    Use when the request involves:
    - PDF clinical reports, discharge summaries, referral notes, or EHR notes
    - text documents containing clinical content
    - asking questions about an uploaded clinical document

    Do NOT use for:
    - radiology image files such as png/jpg/webp unless the PDF/text contains a
      written radiology report
    - pathology whole slide image files
    """
    print("\nCalling Agent: Clinical Notes/EHR Agent")
    
    prompt = f"""
Clinical input:
{clinical_input}

Input type:
{input_type or "auto-detect"}

User query:
{user_query or "Summarize this clinical document."}
"""

    result = clinical_document_analysis_specialist_.invoke(
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

    print("\nFinished Agent: Clinical Notes/EHR Agent")

    trace_agent(
        "Clinical Notes EHR Agent",
        prompt,
        final_output,
        action=action
    )

    return {
    "agent": "Clinical Documents EHR Agent",
    "action": action,
    "input": prompt,
    "output": final_output
}



# -----------------------------------
# AGENT CREATION (TRACEABLE VERSION)
# -----------------------------------
clinical_document_analysis_specialist_ = create_agent(
    model=model,
    tools=[pdf_medical_rag_tool],
    system_prompt=CLINICAL_NOTES_EHR_AGENT_PROMPT
)