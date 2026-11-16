"""
backend/schemas.py - Pydantic Request & Response Validation Schemas
Validates incoming events from the Chrome Extension and outgoing API responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class StartSessionRequest(BaseModel):
    session_id: str
    primary_tab_id: int
    primary_url: str
    primary_domain: str
    primary_category: str
    timestamp: Optional[datetime] = None

class StopSessionRequest(BaseModel):
    session_id: str
    timestamp: Optional[datetime] = None

class TabSwitchEventRequest(BaseModel):
    session_id: str
    timestamp: datetime
    from_tab_id: Optional[int] = None
    to_tab_id: int
    to_url: str
    to_domain: str
    to_category: str
    duration_on_tab: float = 0.0
    is_primary: bool
    is_interruption: bool

class InterruptionEpisodeRequest(BaseModel):
    session_id: str
    episode_id: str
    start_time: datetime
    end_time: datetime
    duration_sec: float
    switch_count: int
    visited_domains: List[str]
    primary_interruption_category: str
    return_latency_sec: float = 0.0

class WindowFocusEventRequest(BaseModel):
    session_id: str
    timestamp: datetime
    has_focus: bool
    details: Optional[str] = None

class IdleEventRequest(BaseModel):
    session_id: str
    timestamp: datetime
    idle_state: str  # 'active', 'idle', 'locked'
    details: Optional[str] = None

class StandardResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

