
from langchain.agents import create_agent
from langchain_community.tools import tool
import time
from config import model
from src.agents.clinical_document_analysis_agent import clinical_documents_ehr_agent
from src.agents.diagnostic_reasoning_agent import diagnostic_syndrome_reasoning_agent
from src.agents.drug_recommendation_agent import drug_recommendation_agent
from src.agents.lab_interpretation_agent import lab_interpretation_agent
from src.agents.medical_imaging_agent import medical_imaging_agent
from src.agents.risk_assessment_agent import risk_assessment_agent
from src.agents.symptom_assistance_agent import symptom_assistance_agent
from src.agents.vital_signs_monitoring_agent import vital_signs_monitoring_agent
from prompts import SUPERVISOR_AGENT_PROMPT
from src.utils.trace_context import CURRENT_TRACE
from src.utils.agent_trace import trace_agent


supervisor_agent = create_agent(
    model=model,
    tools=[
        clinical_documents_ehr_agent,
        risk_assessment_agent,
        diagnostic_syndrome_reasoning_agent,
        drug_recommendation_agent,
        lab_interpretation_agent,
        symptom_assistance_agent,
        medical_imaging_agent,
    ],
    system_prompt=SUPERVISOR_AGENT_PROMPT,
)
