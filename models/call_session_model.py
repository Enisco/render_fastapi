from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class User(BaseModel):
    id: Optional[str]
    name: Optional[str]
    language: Optional[str]
    role: Optional[str]
    teams: Optional[List[str]]
    created_at: Optional[str]
    updated_at: Optional[str]
    banned: Optional[bool]
    online: Optional[bool]
    last_active: Optional[str]
    blocked_user_ids: Optional[List[str]]
    shadow_banned: Optional[bool]
    devices: Optional[List[str]]
    invisible: Optional[bool]

class AudioSettings(BaseModel):
    access_request_enabled: Optional[bool]
    opus_dtx_enabled: Optional[bool]
    redundant_coding_enabled: Optional[bool]
    mic_default_on: Optional[bool]
    speaker_default_on: Optional[bool]
    default_device: Optional[str]
    noise_cancellation: Optional[Dict[str, Any]]

class BackstageSettings(BaseModel):
    enabled: Optional[bool]

class HLSSettings(BaseModel):
    auto_on: Optional[bool]
    enabled: Optional[bool]
    quality_tracks: Optional[List[str]]
    layout: Optional[Dict[str, Any]]

class RTMPSettings(BaseModel):
    enabled: Optional[bool]
    quality: Optional[str]
    layout: Optional[Dict[str, Any]]

class BroadcastingSettings(BaseModel):
    enabled: Optional[bool]
    hls: Optional[HLSSettings]
    rtmp: Optional[RTMPSettings]

class GeofencingSettings(BaseModel):
    names: Optional[List[str]]

class RecordingSettings(BaseModel):
    audio_only: Optional[bool]
    mode: Optional[str]
    quality: Optional[str]
    layout: Optional[Dict[str, Any]]

class RingSettings(BaseModel):
    incoming_call_timeout_ms: Optional[int]
    auto_cancel_timeout_ms: Optional[int]
    missed_call_timeout_ms: Optional[int]

class ScreensharingSettings(BaseModel):
    enabled: Optional[bool]
    access_request_enabled: Optional[bool]
    target_resolution: Optional[Dict[str, Any]]

class TranscriptionSettings(BaseModel):
    mode: Optional[str]
    closed_caption_mode: Optional[str]
    languages: Optional[List[str]]
    language: Optional[str]

class VideoSettings(BaseModel):
    enabled: Optional[bool]
    access_request_enabled: Optional[bool]
    target_resolution: Optional[Dict[str, Any]]
    camera_default_on: Optional[bool]
    camera_facing: Optional[str]

class LimitsSettings(BaseModel):
    max_participants: Optional[int]
    max_duration_seconds: Optional[int]

class SessionSettings(BaseModel):
    inactivity_timeout_seconds: Optional[int]

class Settings(BaseModel):
    audio: Optional[AudioSettings]
    backstage: Optional[BackstageSettings]
    broadcasting: Optional[BroadcastingSettings]
    geofencing: Optional[GeofencingSettings]
    recording: Optional[RecordingSettings]
    ring: Optional[RingSettings]
    screensharing: Optional[ScreensharingSettings]
    transcription: Optional[TranscriptionSettings]
    video: Optional[VideoSettings]
    thumbnails: Optional[Dict[str, Any]]
    limits: Optional[LimitsSettings]
    session: Optional[SessionSettings]

class CallSession(BaseModel):
    id: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    participants: Optional[List[Any]]
    participants_count_by_role: Optional[Dict[str, int]]
    anonymous_participant_count: Optional[int]
    rejected_by: Optional[str]
    accepted_by: Optional[str]
    missed_by: Optional[str]
    live_started_at: Optional[str]
    live_ended_at: Optional[str]
    timer_ends_at: Optional[str]

class Ingress(BaseModel):
    rtmp: Optional[Dict[str, Any]]

class Call(BaseModel):
    type: Optional[str]
    id: Optional[str]
    cid: Optional[str]
    current_session_id: Optional[str]
    created_by: Optional[User]
    custom: Optional[Any]
    created_at: Optional[str]
    updated_at: Optional[str]
    recording: Optional[bool]
    transcribing: Optional[bool]
    captioning: Optional[bool]
    ended_at: Optional[str]
    starts_at: Optional[str]
    backstage: Optional[bool]
    settings: Optional[Settings]
    blocked_user_ids: Optional[List[str]]
    ingress: Optional[Ingress]
    session: Optional[CallSession]
    egress: Optional[Dict[str, Any]]
    thumbnails: Optional[Any]
    join_ahead_time_seconds: Optional[int]

class CallSessionModel(BaseModel):
    type: Optional[str]
    created_at: Optional[str]
    call_cid: Optional[str]
    session_id: Optional[str]
    call: Optional[Call]

def session_json_to_model(data: dict) -> CallSessionModel:
    return CallSessionModel(**data)
