from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UIPerformanceData(BaseModel):
    """UI Performance timing data model"""
    timestamp: Optional[datetime] = None
    url: Optional[str] = None
    # Navigation Timing API
    navigation_start: Optional[float] = None
    unload_event_start: Optional[float] = None
    unload_event_end: Optional[float] = None
    redirect_start: Optional[float] = None
    redirect_end: Optional[float] = None
    fetch_start: Optional[float] = None
    domain_lookup_start: Optional[float] = None
    domain_lookup_end: Optional[float] = None
    connect_start: Optional[float] = None
    connect_end: Optional[float] = None
    secure_connection_start: Optional[float] = None
    request_start: Optional[float] = None
    response_start: Optional[float] = None
    response_end: Optional[float] = None
    dom_loading: Optional[float] = None
    dom_interactive: Optional[float] = None
    dom_content_loaded_event_start: Optional[float] = None
    dom_content_loaded_event_end: Optional[float] = None
    dom_complete: Optional[float] = None
    load_event_start: Optional[float] = None
    load_event_end: Optional[float] = None
    # Calculated metrics
    dns_lookup_time: Optional[float] = None
    connection_time: Optional[float] = None
    ssl_time: Optional[float] = None
    time_to_first_byte: Optional[float] = None
    content_download_time: Optional[float] = None
    dom_processing_time: Optional[float] = None
    page_load_time: Optional[float] = None
    full_page_load_time: Optional[float] = None

class UIPerformanceMetrics(BaseModel):
    """Aggregated UI Performance metrics"""
    total_samples: int
    dns_lookup_time: dict
    connection_time: dict
    ssl_time: dict
    time_to_first_byte: dict
    content_download_time: dict
    dom_processing_time: dict
    page_load_time: dict
    full_page_load_time: dict
    summary: dict












