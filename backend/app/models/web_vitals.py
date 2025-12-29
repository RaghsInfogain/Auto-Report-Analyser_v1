from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class WebVitalsData(BaseModel):
    """Web Vitals data model"""
    timestamp: Optional[datetime] = None
    url: Optional[str] = None
    lcp: Optional[float] = None  # Largest Contentful Paint
    fid: Optional[float] = None  # First Input Delay
    cls: Optional[float] = None  # Cumulative Layout Shift
    fcp: Optional[float] = None  # First Contentful Paint
    ttfb: Optional[float] = None  # Time to First Byte
    inp: Optional[float] = None  # Interaction to Next Paint
    custom_metrics: Optional[dict] = None

class WebVitalsMetrics(BaseModel):
    """Aggregated Web Vitals metrics"""
    total_samples: int
    lcp: dict  # {mean, median, p95, p99, min, max}
    fid: dict
    cls: dict
    fcp: dict
    ttfb: dict
    inp: Optional[dict] = None
    summary: dict












