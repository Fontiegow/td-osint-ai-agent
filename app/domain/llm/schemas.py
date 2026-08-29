from enum import Enum
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from typing import Optional


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class NormalizedMessage(BaseModel):
    role: MessageRole
    content: str
    
    # We allow optional metadata for things like tool_call_ids in the future
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class LLMStreamEvent(BaseModel):
    content_delta: str
    finish_reason: Optional[str] = None

class GenerationRequest(BaseModel):
    messages: List[NormalizedMessage]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    
    # The magical component for Milestone 2: 
    # Pass a Pydantic class here, and the Gateway will enforce it.
    response_format: Optional[Type[BaseModel]] = None 
    
    # Let the Gateway/Adapter handle the specific model routing based on config,
    # but allow the request to override it if a specific sub-agent needs a smaller/larger model.
    model_override: Optional[str] = None

class GenerationResponse(BaseModel):
    content: str
    finish_reason: str
    usage: TokenUsage
    latency_ms: float
    provider: str
    model: str