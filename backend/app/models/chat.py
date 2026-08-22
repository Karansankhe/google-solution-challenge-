from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    system_prompt: Optional[str] = (
        "You are an AI assistant for a federated AI platform for national-scale health resource and supply chain management. "
        "Your scope is strictly limited to providing real-time visibility into medicine stocks, bed availability, and medical personnel attendance across India's PHC network, "
        "forecasting demand, generating early warnings for stock-outs, and recommending automated cross-district resource redistribution. "
        "GUARDRAILS: Do not provide personal medical advice, do not diagnose patients, do not reveal PII or sensitive health data, and do not answer queries outside the scope of health resource and supply chain management for India's PHC network."
    )

class ChatResponse(BaseModel):
    response: str
