from pydantic import BaseModel
from typing import Optional, Dict, Any


# =====================================================
# CHAT REQUEST
# =====================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


# =====================================================
# CHAT RESPONSE
# =====================================================

class ChatResponse(BaseModel):
    session_id: str
    bot_reply: str
    intent: Optional[str] = None
    permission_check: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None