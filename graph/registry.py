import time
from graph.utils.logger import log_event


# -----------------------------------
# SAFE IMPORT WRAPPER
# -----------------------------------
def safe_import(path, name):
    try:
        module = __import__(path, fromlist=[name])
        return getattr(module, name)
    except Exception as e:
        print(f"[AGENT LOAD ERROR] {name}: {e}")
        return None


# -----------------------------------
# IMPORT AGENTS
# -----------------------------------
lab_interpretation_agent_ = safe_import("agents.lab_interpretation_agent", "lab_interpretation_agent_")
drug_recommendation_agent_ = safe_import("agents.drug_recommendation_agent", "drug_recommendation_agent_")
radiology_imaging_diagnostic_agent_ = safe_import("agents.radiology_imaging_diagnostic_agent", "radiology_imaging_diagnostic_agent_")
clinical_notes_ehr_agent_ = safe_import("agents.clinical_notes_agent", "clinical_notes_ehr_agent_")
pathology_slide_analysis_agent_ = safe_import("agents.pathology_agent", "pathology_slide_analysis_agent_")
vital_signs_monitoring_agent_ = safe_import("agents.vital_signs_monitoring_agent", "vital_signs_monitoring_agent_")
diagnostic_recommender_agent_ = safe_import("agents.diagnostic_recommender_agent", "diagnostic_recommender_agent_")
differential_diagnosis_agent_ = safe_import("agents.differential_diagnosis_agent", "differential_diagnosis_agent_")
disease_syndrome_classification_agent_ = safe_import("agents.disease_classification_agent", "disease_syndrome_classification_agent_")
risk_assessment_agent_ = safe_import("agents.risk_assessment_agent", "risk_assessment_agent_")
symptom_assistance_agent_ = safe_import("agents.symptom_assistance_agent", "symptom_assistance_agent_")


# -----------------------------------
# AGENT WRAPPER (STANDARDIZED TRACE)
# -----------------------------------
def trace_agent_call(run_id, agent_name, agent_fn, input_payload):

    start_time = time.time()

    log_event(run_id, "agent_call_start", {
        "agent": agent_name,
        "input": str(input_payload)
    })

    try:

        if agent_fn is None:
            raise ValueError(f"Agent not found: {agent_name}")

        result = agent_fn.invoke(input_payload)

        output = (
            result.content
            if hasattr(result, "content")
            else str(result)
        )

        latency = round(time.time() - start_time, 4)

        log_event(run_id, "agent_call_end", {
            "agent": agent_name,
            "output": output,
            "latency_sec": latency,
            "status": "success"
        })

        return result

    except Exception as e:

        latency = round(time.time() - start_time, 4)

        log_event(run_id, "agent_call_error", {
            "agent": agent_name,
            "error": str(e),
            "latency_sec": latency,
            "status": "error"
        })

        return None  # IMPORTANT: keep downstream safe


# -----------------------------------
# WRAPPED ACCESSOR (IMPORTANT)
# -----------------------------------
def get_agent(agent_name, run_id=None):

    agent = AGENT_REGISTRY.get(agent_name)

    if agent is None:
        return None

    def wrapped(input_payload):

        return trace_agent_call(
            run_id=run_id,
            agent_name=agent_name,
            agent_fn=agent,
            input_payload=input_payload
        )

    return wrapped


# -----------------------------------
# FINAL REGISTRY
# -----------------------------------
AGENT_REGISTRY = {
    "lab_interpretation_agent": lab_interpretation_agent_,
    "drug_recommendation_agent": drug_recommendation_agent_,
    "radiology_imaging_diagnostic_agent": radiology_imaging_diagnostic_agent_,
    "clinical_notes_ehr_agent": clinical_notes_ehr_agent_,
    "pathology_slide_analysis_agent": pathology_slide_analysis_agent_,
    "vital_signs_monitoring_agent": vital_signs_monitoring_agent_,
    "diagnostic_recommender_agent": diagnostic_recommender_agent_,
    "differential_diagnosis_agent": differential_diagnosis_agent_,
    "disease_syndrome_classification_agent": disease_syndrome_classification_agent_,
    "risk_assessment_agent": risk_assessment_agent_,
    "symptom_assistance_agent": symptom_assistance_agent_,
}