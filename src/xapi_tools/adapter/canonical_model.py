from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class CanonicalActor(BaseModel):
    id: str = Field(..., description="Normalized unique ID of the actor (e.g., user account name or email)")
    name: Optional[str] = Field(None, description="Display name of the actor")

class CanonicalTarget(BaseModel):
    id: str = Field(..., description="Target Activity ID")
    type: Optional[str] = Field(None, description="Standardized target type (e.g., media, assessment, course)")
    name: Optional[str] = Field(None, description="Name of the activity")

class CanonicalResult(BaseModel):
    score_scaled: Optional[float] = Field(None, description="Normalized score between 0.0 and 1.0")
    is_success: Optional[bool] = Field(None, description="Indicates if the action was successful")
    is_completion: Optional[bool] = Field(None, description="Indicates if the activity was completed")
    duration_seconds: Optional[float] = Field(None, description="Time spent in seconds")

    @field_validator("score_scaled")
    @classmethod
    def validate_score_scaled(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("score_scaled must be between 0.0 and 1.0")
        return v

class CanonicalStatement(BaseModel):
    client_id: str = Field(..., description="Identifier for the provider/company")
    actor: CanonicalActor
    verb_category: str = Field(..., description="Unified verb classification (e.g., started, completed, played, paused, answered)")
    original_verb_id: str = Field(..., description="The raw original xAPI Verb URI")
    target: CanonicalTarget
    result: CanonicalResult = Field(default_factory=CanonicalResult)
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Normalized custom metadata (device, browser, etc.)")
    timestamp: datetime = Field(..., description="Timestamp of the event")
