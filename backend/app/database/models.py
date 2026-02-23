"""
Database models for persistent storage
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class UploadedFile(Base):
    """Model for uploaded files"""
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(100), unique=True, index=True, nullable=False)
    run_id = Column(String(100), index=True, nullable=False)  # Groups files from same upload
    filename = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # web_vitals, jmeter, ui_performance
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    record_count = Column(Integer, default=0)  # Number of records in the file
    report_status = Column(String(50), default="pending")  # pending, analyzing, generating, generated, error
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(String(100), default="unknown")
    
    # Relationship
    analysis = relationship("AnalysisResult", back_populates="file", uselist=False, cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary, avoiding relationship loading"""
        # Check if analysis exists without triggering lazy load
        has_analysis = False
        has_reports = False
        try:
            # Use getattr to avoid triggering relationship load
            analysis = getattr(self, 'analysis', None)
            if analysis is not None:
                has_analysis = True
                # Check reports without triggering load
                reports = getattr(analysis, 'reports', None)
                if reports is not None:
                    try:
                        has_reports = len(reports) > 0
                    except:
                        has_reports = False
        except:
            pass
        
        return {
            "file_id": self.file_id,
            "run_id": self.run_id,
            "filename": self.filename,
            "category": self.category,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "record_count": self.record_count or 0,
            "report_status": self.report_status,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "uploaded_by": self.uploaded_by,
            "has_analysis": has_analysis,
            "has_reports": has_reports
        }


class AnalysisResult(Base):
    """Model for analysis results"""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(100), ForeignKey("uploaded_files.file_id"), unique=True, nullable=False)
    category = Column(String(50), nullable=False)
    metrics = Column(JSON, nullable=False)  # Store complete metrics as JSON
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)  # Duration in seconds
    
    # Relationship
    file = relationship("UploadedFile", back_populates="analysis")
    reports = relationship("GeneratedReport", back_populates="analysis", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "file_id": self.file_id,
            "category": self.category,
            "metrics": self.metrics,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "analysis_duration": self.analysis_duration,
            "filename": self.file.filename if self.file else None
        }


class GeneratedReport(Base):
    """Model for generated reports"""
    __tablename__ = "generated_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(100), unique=True, index=True, nullable=False)
    file_id = Column(String(100), ForeignKey("uploaded_files.file_id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False)
    report_type = Column(String(20), nullable=False)  # html, pdf, ppt, json
    report_path = Column(String(500))  # Path to saved report file
    report_content = Column(Text)  # For HTML/JSON reports
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String(100), default="unknown")
    file_size = Column(Integer)
    
    # Relationship
    analysis = relationship("AnalysisResult", back_populates="reports")
    
    def to_dict(self):
        return {
            "report_id": self.report_id,
            "file_id": self.file_id,
            "report_type": self.report_type,
            "report_path": self.report_path,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "generated_by": self.generated_by,
            "file_size": self.file_size
        }


class ChatHistory(Base):
    """Model for AI chatbot conversations"""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    user_id = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    context_file_ids = Column(JSON)  # List of file_ids used for context
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "message": self.message,
            "response": self.response,
            "context_file_ids": self.context_file_ids,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ============================================================================
# PERFORMANCE COMPARISON AND BASELINE MODELS
# ============================================================================

class BaselineRun(Base):
    """Model for baseline test runs"""
    __tablename__ = "baseline_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    baseline_id = Column(String(100), unique=True, index=True, nullable=False)
    run_id = Column(String(100), ForeignKey("uploaded_files.run_id"), nullable=False, index=True)
    application = Column(String(200), nullable=False, index=True)
    environment = Column(String(100), nullable=False, index=True)  # dev/staging/prod
    version = Column(String(100), nullable=False)
    baseline_name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), default="unknown")
    is_active = Column(Boolean, default=True)
    
    # Relationships
    metrics = relationship("BaselineMetric", back_populates="baseline", cascade="all, delete-orphan")
    comparisons_as_baseline = relationship("ComparisonResult", 
                                          foreign_keys="ComparisonResult.baseline_id",
                                          back_populates="baseline",
                                          cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "baseline_id": self.baseline_id,
            "run_id": self.run_id,
            "application": self.application,
            "environment": self.environment,
            "version": self.version,
            "baseline_name": self.baseline_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "is_active": self.is_active
        }


class BaselineMetric(Base):
    """Cached metrics from baseline runs for fast comparison"""
    __tablename__ = "baseline_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    baseline_id = Column(String(100), ForeignKey("baseline_runs.baseline_id"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # jmeter/lighthouse/web_vitals
    metric_key = Column(String(255), nullable=False, index=True)
    metric_value = Column(Float)
    metric_json = Column(JSON)
    transaction_name = Column(String(500), index=True)  # For API/page-specific metrics
    
    # Relationship
    baseline = relationship("BaselineRun", back_populates="metrics")
    
    def to_dict(self):
        return {
            "id": self.id,
            "baseline_id": self.baseline_id,
            "category": self.category,
            "metric_key": self.metric_key,
            "metric_value": self.metric_value,
            "metric_json": self.metric_json,
            "transaction_name": self.transaction_name
        }


class ComparisonResult(Base):
    """Stores comparison results between baseline and current runs"""
    __tablename__ = "comparison_results"
    
    id = Column(Integer, primary_key=True, index=True)
    comparison_id = Column(String(100), unique=True, index=True, nullable=False)
    baseline_id = Column(String(100), ForeignKey("baseline_runs.baseline_id"), nullable=False, index=True)
    current_run_id = Column(String(100), nullable=False, index=True)
    comparison_type = Column(String(50), nullable=False)  # jmeter/lighthouse/full
    
    # Overall metrics
    overall_score = Column(Float)  # Release health score (0-100)
    backend_score = Column(Float)  # JMeter score
    frontend_score = Column(Float)  # Lighthouse score
    reliability_score = Column(Float)  # Error rate score
    
    verdict = Column(String(50))  # approved/risky/blocked
    regression_count = Column(Integer, default=0)
    improvement_count = Column(Integer, default=0)
    stable_count = Column(Integer, default=0)
    
    # Detailed comparison data
    comparison_data = Column(JSON)  # Full comparison details
    summary_text = Column(Text)  # Natural language summary
    
    # Processing status
    status = Column(String(50), default="processing")  # processing/completed/failed
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    baseline = relationship("BaselineRun", 
                          foreign_keys=[baseline_id],
                          back_populates="comparisons_as_baseline")
    regressions = relationship("RegressionDetail", back_populates="comparison", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "comparison_id": self.comparison_id,
            "baseline_id": self.baseline_id,
            "current_run_id": self.current_run_id,
            "comparison_type": self.comparison_type,
            "overall_score": self.overall_score,
            "backend_score": self.backend_score,
            "frontend_score": self.frontend_score,
            "reliability_score": self.reliability_score,
            "verdict": self.verdict,
            "regression_count": self.regression_count,
            "improvement_count": self.improvement_count,
            "stable_count": self.stable_count,
            "comparison_data": self.comparison_data,
            "summary_text": self.summary_text,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class RegressionDetail(Base):
    """Individual regression/improvement records"""
    __tablename__ = "regression_details"
    
    id = Column(Integer, primary_key=True, index=True)
    comparison_id = Column(String(100), ForeignKey("comparison_results.comparison_id"), nullable=False, index=True)
    
    metric_name = Column(String(255), nullable=False)
    transaction_name = Column(String(500))  # API endpoint or page name
    category = Column(String(50), nullable=False, index=True)  # jmeter/lighthouse/web_vitals
    
    baseline_value = Column(Float)
    current_value = Column(Float)
    change_percent = Column(Float)
    change_absolute = Column(Float)
    
    severity = Column(String(50), nullable=False, index=True)  # stable/minor/major/critical
    change_type = Column(String(50))  # regression/improvement/stable
    
    # Additional context
    details = Column(JSON)
    
    # Relationship
    comparison = relationship("ComparisonResult", back_populates="regressions")
    
    def to_dict(self):
        return {
            "id": self.id,
            "comparison_id": self.comparison_id,
            "metric_name": self.metric_name,
            "transaction_name": self.transaction_name,
            "category": self.category,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percent": self.change_percent,
            "change_absolute": self.change_absolute,
            "severity": self.severity,
            "change_type": self.change_type,
            "details": self.details
        }



