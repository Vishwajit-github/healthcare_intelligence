
from langchain.agents import create_agent
from langchain_community.tools import tool

from config import model

from src.tools.medical_imaging_tool import (
    medical_imaging_analysis_tool_,
)
from src.utils.agent_trace import trace_agent
from src.utils.trace_context import CURRENT_TRACE


# =========================================================
# SYSTEM PROMPT
# =========================================================

MEDICAL_IMAGING_AGENT_PROMPT = """
You are a Medical Imaging Analysis Agent
in a healthcare decision support system.

Your role:
- analyze uploaded medical images
- extract visible medical information
- provide safe non-diagnostic observations
- summarize visible findings carefully

You can analyze:
- prescriptions
- medicine names
- x-rays
- CT scans
- MRI scans
- ultrasound
- PET scans
- radiology images
- dermatology images
- pathology images
- lab report screenshots
- clinical photographs

Responsibilities:
- describe visible findings
- identify possible abnormalities
- extract medicine names if visible
- mention uncertainty when text is unclear
- highlight urgent findings if present
- recommend clinician review when appropriate

You MUST:
- stay grounded in visible image content
- use cautious medical language
- acknowledge uncertainty
- avoid hallucinating unreadable text

You do NOT:
- provide final diagnosis
- prescribe treatment
- replace clinician/radiologist review

Input:
- image_path
- user_query

Output:
- concise
- structured
- clinically safe
"""


# =========================================================
# TOOL
# =========================================================

@tool
def analyze_medical_image(
    image_path: str,
    user_query: str = "",
) -> str:
    """
    Analyze medical images using OpenAI Vision.

    Supports:
    - Local uploaded image paths
    - Image URLs
    - Prescription photos
    - X-rays
    - CT scans
    - MRI scans
    - Ultrasound
    - Dermatology images
    - Lab report screenshots

    Inputs:
    - image_path: Local file path or image URL
    - user_query: User question about image
    """

    return medical_imaging_analysis_tool_(
        image_path=image_path,
        user_query=user_query,
    )



@tool
def medical_imaging_agent(
    image_context: str,
    action: str,
) -> str:
    """
    Use this specialist for medical image analysis and imaging-based
    clinical interpretation.

    Input:
    - image_context: Medical image path/URL and the user's imaging question.
    - action: Short 2-4 word high-level operation label only; no sentences,
      explanations, or punctuation-heavy text.

    Use when the request involves:
    - X-ray analysis
    - CT scan interpretation
    - MRI interpretation
    - Ultrasound analysis
    - PET scan review
    - radiology imaging findings
    - visible abnormalities or imaging patterns
    - imaging-related urgency or red flags

    Use for:
    - chest X-rays
    - brain imaging
    - abdominal scans
    - musculoskeletal imaging
    - lung imaging
    - general radiology studies

    Do NOT use for:
    - final diagnosis
    - prescribing medications
    - treatment planning
    - non-medical images
    """

    print("\nCalling Agent: Medical Imaging Specialist")

    print(f"INPUT TO MEDICAL IMAGING SPECIALIST:\n{image_context}")

  
    result = medical_imaging_specialist.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": image_context,
                }
            ]
        }
    )

    final_output = result["messages"][-1].content

    print("\nFinished Agent: Medical Imaging Specialist")

    # =====================================================
    # 🔥 FIX: TRACE REGISTRATION (CRITICAL MISSING PIECE)
    # =====================================================
    if "agents" not in CURRENT_TRACE:
        CURRENT_TRACE["agents"] = []

    trace_agent(
        "Medical Imaging Agent",
        image_context,
        final_output,
        evidence={
            "type": "vision_model",
            "grounded": True
        },
        action=action
    )

    return {
        "agent": "Medical Imaging Agent",
        "action": action,
        "input": image_context,
        "output": final_output
    }



# =========================================================
# AGENT
# =========================================================

medical_imaging_specialist = create_agent(

    model=model,

    tools=[
        analyze_medical_image,
    ],

    system_prompt=MEDICAL_IMAGING_AGENT_PROMPT,
)

