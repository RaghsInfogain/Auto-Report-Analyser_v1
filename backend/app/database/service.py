"""Database service layer for CRUD operations"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import re

from .models import UploadedFile, AnalysisResult, GeneratedReport, ChatHistory


class DatabaseService:
    """Service class for database operations"""
    
    @staticmethod
    def generate_next_run_id(db: Session) -> str:
        """Generate the next sequential Run ID (Run-1, Run-2, etc.)"""
        # Get all existing run_ids
        existing_runs = db.query(UploadedFile.run_id).distinct().all()
        
        if not existing_runs:
            return "Run-1"
        
        # Extract numbers from existing Run IDs
        max_number = 0
        for (run_id,) in existing_runs:
            # Match pattern "Run-X" where X is a number
            match = re.match(r'^Run-(\d+)$', run_id)
            if match:
                number = int(match.group(1))
                max_number = max(max_number, number)
        
        # Return next sequential number
        return f"Run-{max_number + 1}"
    
    @staticmethod
    def create_uploaded_file(
        db: Session,
        filename: str,
        category: str,
        file_path: str,
        file_size: int,
        uploaded_by: str = "unknown",
        run_id: str = None
    ) -> UploadedFile:
        """Create a new uploaded file record"""
        file_id = str(uuid.uuid4())
        # Generate run_id if not provided
        if not run_id:
            run_id = DatabaseService.generate_next_run_id(db)
        
        db_file = UploadedFile(
            file_id=file_id,
            run_id=run_id,
            filename=filename,
            category=category,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=uploaded_by
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file
    
    @staticmethod
    def get_uploaded_file(db: Session, file_id: str) -> Optional[UploadedFile]:
        """Get uploaded file by ID"""
        return db.query(UploadedFile).filter(UploadedFile.file_id == file_id).first()
    
    @staticmethod
    def get_files_by_run_id(db: Session, run_id: str) -> List[UploadedFile]:
        """Get all files with a specific run_id"""
        return db.query(UploadedFile).filter(UploadedFile.run_id == run_id).all()
    
    @staticmethod
    def get_all_uploaded_files(db: Session) -> List[UploadedFile]:
        """Get all uploaded files"""
        return db.query(UploadedFile).order_by(UploadedFile.uploaded_at.desc()).all()
    
    @staticmethod
    def get_all_run_ids(db: Session) -> List[dict]:
        """Get all unique run_ids with their file counts and info - optimized to avoid N+1 queries"""
        from sqlalchemy import func, case
        
        # Single query to get all runs with aggregated data
        runs = db.query(
            UploadedFile.run_id,
            func.count(UploadedFile.file_id).label('file_count'),
            func.sum(UploadedFile.file_size).label('total_size'),
            func.sum(UploadedFile.record_count).label('total_records'),
            func.min(UploadedFile.uploaded_at).label('uploaded_at')
        ).group_by(UploadedFile.run_id).order_by(func.min(UploadedFile.uploaded_at).desc()).all()
        
        if not runs:
            return []
        
        # Get all run_ids
        run_ids = [run.run_id for run in runs]
        
        # Single query to get all files for all runs at once
        all_files = db.query(UploadedFile).filter(UploadedFile.run_id.in_(run_ids)).all()
        
        # Group files by run_id in memory (much faster than N queries)
        files_by_run = {}
        for file in all_files:
            if file.run_id not in files_by_run:
                files_by_run[file.run_id] = []
            files_by_run[file.run_id].append(file)
        
        result = []
        for run in runs:
            run_id = run.run_id
            files = files_by_run.get(run_id, [])
            
            # Determine overall status efficiently
            statuses = [f.report_status for f in files]
            if not statuses:
                overall_status = 'pending'
            elif all(s == 'generated' for s in statuses):
                overall_status = 'generated'
            elif any(s == 'error' for s in statuses):
                overall_status = 'error'
            elif any(s == 'generating' for s in statuses):
                overall_status = 'generating'
            elif any(s == 'analyzing' for s in statuses):
                overall_status = 'analyzing'
            else:
                overall_status = 'pending'
            
            # Get categories efficiently
            categories = list(set(f.category for f in files))
            
            # Only include basic file info to avoid loading relationships
            files_data = []
            for f in files:
                files_data.append({
                    "file_id": f.file_id,
                    "run_id": f.run_id,
                    "filename": f.filename,
                    "category": f.category,
                    "file_size": f.file_size,
                    "record_count": f.record_count or 0,
                    "report_status": f.report_status,
                    "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
                    "uploaded_by": f.uploaded_by,
                    "has_analysis": False,  # Don't query relationships
                    "has_reports": False    # Don't query relationships
                })
            
            result.append({
                'run_id': run_id,
                'file_count': run.file_count,
                'total_size': run.total_size or 0,
                'total_records': run.total_records or 0,
                'uploaded_at': run.uploaded_at.isoformat() if run.uploaded_at else None,
                'report_status': overall_status,
                'categories': categories,
                'files': files_data
            })
        
        return result
    
    @staticmethod
    def delete_uploaded_file(db: Session, file_id: str) -> bool:
        """Delete uploaded file and all related data"""
        db_file = DatabaseService.get_uploaded_file(db, file_id)
        if db_file:
            db.delete(db_file)
            db.commit()
            return True
        return False
    
    @staticmethod
    def delete_run(db: Session, run_id: str) -> bool:
        """Delete all files in a run and related data"""
        files = DatabaseService.get_files_by_run_id(db, run_id)
        if files:
            for f in files:
                db.delete(f)
            db.commit()
            return True
        return False
    
    @staticmethod
    def create_analysis_result(
        db: Session,
        file_id: str,
        category: str,
        metrics: Dict[str, Any],
        analysis_duration: Optional[float] = None
    ) -> AnalysisResult:
        """Create a new analysis result"""
        # Check if analysis already exists
        existing = db.query(AnalysisResult).filter(AnalysisResult.file_id == file_id).first()
        if existing:
            # Update existing analysis
            existing.metrics = metrics
            existing.analyzed_at = datetime.utcnow()
            existing.analysis_duration = analysis_duration
            db.commit()
            db.refresh(existing)
            return existing
        
        # Create new analysis
        db_analysis = AnalysisResult(
            file_id=file_id,
            category=category,
            metrics=metrics,
            analysis_duration=analysis_duration
        )
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)
        return db_analysis
    
    @staticmethod
    def get_analysis_result(db: Session, file_id: str) -> Optional[AnalysisResult]:
        """Get analysis result by file ID"""
        return db.query(AnalysisResult).filter(AnalysisResult.file_id == file_id).first()
    
    @staticmethod
    def get_all_analysis_results(db: Session) -> List[AnalysisResult]:
        """Get all analysis results"""
        return db.query(AnalysisResult).order_by(AnalysisResult.analyzed_at.desc()).all()
    
    @staticmethod
    def create_generated_report(
        db: Session,
        file_id: str,
        report_type: str,
        report_content: Optional[str] = None,
        report_path: Optional[str] = None,
        generated_by: str = "unknown",
        file_size: Optional[int] = None
    ) -> GeneratedReport:
        """Create a new generated report record"""
        # Get analysis ID
        analysis = DatabaseService.get_analysis_result(db, file_id)
        if not analysis:
            raise ValueError(f"No analysis found for file_id: {file_id}")
        
        report_id = str(uuid.uuid4())
        db_report = GeneratedReport(
            report_id=report_id,
            file_id=file_id,
            analysis_id=analysis.id,
            report_type=report_type,
            report_path=report_path,
            report_content=report_content,
            generated_by=generated_by,
            file_size=file_size
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report
    
    @staticmethod
    def get_reports_by_file(db: Session, file_id: str) -> List[GeneratedReport]:
        """Get all reports for a file"""
        return db.query(GeneratedReport).filter(GeneratedReport.file_id == file_id).all()
    
    @staticmethod
    def get_report_by_id(db: Session, report_id: str) -> Optional[GeneratedReport]:
        """Get report by ID"""
        return db.query(GeneratedReport).filter(GeneratedReport.report_id == report_id).first()
    
    @staticmethod
    def delete_report(db: Session, report_id: str) -> bool:
        """Delete a report"""
        db_report = DatabaseService.get_report_by_id(db, report_id)
        if db_report:
            db.delete(db_report)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_all_reports(db: Session) -> List[GeneratedReport]:
        """Get all generated reports"""
        return db.query(GeneratedReport).order_by(GeneratedReport.generated_at.desc()).all()
    
    @staticmethod
    def save_chat_message(
        db: Session,
        session_id: str,
        user_id: str,
        message: str,
        response: str,
        context_file_ids: Optional[List[str]] = None
    ) -> ChatHistory:
        """Save a chat message and response"""
        db_chat = ChatHistory(
            session_id=session_id,
            user_id=user_id,
            message=message,
            response=response,
            context_file_ids=context_file_ids or []
        )
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)
        return db_chat
    
    @staticmethod
    def get_chat_history(db: Session, session_id: str) -> List[ChatHistory]:
        """Get chat history for a session"""
        return db.query(ChatHistory).filter(
            ChatHistory.session_id == session_id
        ).order_by(ChatHistory.timestamp.asc()).all()
    
    @staticmethod
    def get_user_chat_sessions(db: Session, user_id: str) -> List[str]:
        """Get all chat sessions for a user"""
        sessions = db.query(ChatHistory.session_id).filter(
            ChatHistory.user_id == user_id
        ).distinct().all()
        return [s[0] for s in sessions]




