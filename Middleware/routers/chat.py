from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_service import chat_with_llm, get_available_models  # type: ignore[import-not-found]
import traceback

router = APIRouter()

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    context: Optional[str] = None
    model_preference: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        # Prepend system context if provided
        messages = req.messages.copy()
        
        system_msg = {
            "role": "system",
            "content": "You are a spacecraft telemetry AI assistant. You help engineers understand anomaly detection data, charts, and system status. Provide concise, highly professional responses."
        }
        
        if req.context:
            system_msg["content"] += f"\n\nCurrent Context:\n{req.context}"
            
        messages.insert(0, system_msg)
        
        reply = chat_with_llm(messages, req.model_preference)
        
        return ChatResponse(response=reply)
    except Exception as e:
        print(f"ERROR in chat endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/models")
async def get_models():
    try:
        models = get_available_models()
        return {"models": models}
    except Exception as e:
        print(f"ERROR fetching models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
