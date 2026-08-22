from fastapi import APIRouter, Depends, HTTPException, status
from app.models.chat import ChatRequest, ChatResponse
from app.services.agent import generate_agent_response
from app.core.security import get_api_key

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(get_api_key)])
async def chat_endpoint(request: ChatRequest):
    try:
        response_text = await generate_agent_response(request)
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
