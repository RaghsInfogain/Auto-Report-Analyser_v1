from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class JMeterData(BaseModel):
    """JMeter test result data model"""
    timestamp: Optional[datetime] = None
    label: Optional[str] = None
    response_code: Optional[str] = None
    response_message: Optional[str] = None
    thread_name: Optional[str] = None
    data_type: Optional[str] = None
    success: Optional[bool] = None
    failure_message: Optional[str] = None
    bytes: Optional[int] = None
    sent_bytes: Optional[int] = None
    grp_threads: Optional[int] = None
    all_threads: Optional[int] = None
    latency: Optional[float] = None  # milliseconds
    sample_time: Optional[float] = None  # milliseconds
    connect_time: Optional[float] = None  # milliseconds

class JMeterMetrics(BaseModel):
    """Aggregated JMeter metrics"""
    total_samples: int
    total_errors: int
    error_rate: float
    throughput: float  # requests per second
    latency: dict  # {mean, median, p95, p99, min, max}
    sample_time: dict
    connect_time: dict
    response_codes: dict
    labels: dict  # metrics per label
    summary: dict












