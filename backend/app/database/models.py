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



