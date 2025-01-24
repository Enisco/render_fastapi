from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class User(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    language: Optional[str] = None
    role: Optional[str] = None
    teams: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    banned: Optional[bool] = None
    online: Optional[bool] = None
    blocked_user_ids: Optional[List[str]] = None
    shadow_banned: Optional[bool] = None
    devices: Optional[List[str]] = None
    invisible: Optional[bool] = None


class Participant(BaseModel):
    user: Optional[User] = None
    user_session_id: Optional[str] = None
    role: Optional[str] = None
    joined_at: Optional[datetime] = None


class CallSessionParticipantModel(BaseModel):
    type: Optional[str] = None
    created_at: Optional[datetime] = None
    call_cid: Optional[str] = None
    session_id: Optional[str] = None
    participant: Optional[Participant] = None


def participant_json_to_model(data: dict) -> CallSessionParticipantModel:
    return CallSessionParticipantModel(**data)
