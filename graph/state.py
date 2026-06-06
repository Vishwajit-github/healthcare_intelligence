from typing import TypedDict, List, Dict, Any, Optional


class HealthcareState(TypedDict):

    # =====================================================
    # USER INPUT
    # =====================================================
    user_query: str

    # =====================================================
    # ACTIVE MESSAGE STATE
    # =====================================================
    messages: List[Dict[str, Any]]

    # =====================================================
    # TRACE / SESSION
    # =====================================================
    run_id: Optional[str]

    # =====================================================
    # IMAGE INPUTS
    # =====================================================
    uploaded_image_path: Optional[str]
    uploaded_image_base64: Optional[str]
    uploaded_image_mime_type: Optional[str]

    # =====================================================
    # SUPERVISOR OUTPUT
    # =====================================================
    supervisor_output: Optional[str]

    # =====================================================
    # VALIDATION
    # =====================================================
    validation_result: Optional[Dict[str, Any]]
    validation_risk_level: Optional[str]
    is_valid: bool

    # =====================================================
    # ITERATION
    # =====================================================
    iteration: int

    # =====================================================
    # FINAL RESPONSE
    # =====================================================
    final_response: Optional[str]

    # =====================================================
    # AGENT TRACKING
    # =====================================================
    used_agents: Optional[List[str]]

    # =====================================================
    # AGENT OUTPUTS
    # =====================================================
    agent_outputs: Optional[Dict[str, Any]]

    # =====================================================
    # CHAT HISTORY
    # =====================================================
    chat_history: Optional[List[Dict[str, Any]]]