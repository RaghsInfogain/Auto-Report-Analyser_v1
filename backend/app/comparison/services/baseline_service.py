"""
Baseline Service
Handles CRUD operations for baseline runs
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.database.models import BaselineRun, BaselineMetric, AnalysisResult, UploadedFile
from app.database.service import DatabaseService


class BaselineService:
    """Service for managing baseline test runs"""
    
    @staticmethod
    def create_baseline(
        db: Session,
        run_id: str,
        application: str,
        environment: str,
        version: str,
        baseline_name: str,
        description: str = None,
        created_by: str = "unknown"
    ) -> BaselineRun:
        """
        Mark a run as baseline
        
        Args:
            db: Database session
            run_id: Run ID to mark as baseline
            application: Application name
            environment: Environment (dev/staging/prod)
            version: Release version
            baseline_name: User-friendly baseline name
            description: Optional description
            created_by: User identifier
        
        Returns:
            Created BaselineRun object
        """
        
        # Verify run exists
        files = DatabaseService.get_files_by_run_id(db, run_id)
        if not files:
            raise ValueError(f"Run ID {run_id} not found")
        
        # Create baseline
        baseline_id = str(uuid.uuid4())
        baseline = BaselineRun(
            baseline_id=baseline_id,
            run_id=run_id,
            application=application,
            environment=environment,
            version=version,
            baseline_name=baseline_name,
            description=description,
            created_by=created_by,
            is_active=True
        )
        
        db.add(baseline)
        db.commit()
        db.refresh(baseline)
        
        # Cache baseline metrics
        BaselineService._cache_baseline_metrics(db, baseline_id, run_id)
        
        return baseline
    
    @staticmethod
    def _cache_baseline_metrics(db: Session, baseline_id: str, run_id: str):
        """Cache metrics from analysis results for fast comparison"""
        
        # Get all files for this run
        files = DatabaseService.get_files_by_run_id(db, run_id)
        
        for file in files:
            # Get analysis result
            analysis = DatabaseService.get_analysis_result(db, file.file_id)
            if not analysis or not analysis.metrics:
                continue
            
            category = analysis.category
            metrics = analysis.metrics
            
            # Cache key metrics based on category
            if category == 'jmeter':
                BaselineService._cache_jmeter_metrics(db, baseline_id, metrics)
            elif category == 'lighthouse':
                BaselineService._cache_lighthouse_metrics(db, baseline_id, metrics)
            elif category == 'web_vitals':
                BaselineService._cache_webvitals_metrics(db, baseline_id, metrics)
    
    @staticmethod
    def _cache_jmeter_metrics(db: Session, baseline_id: str, metrics: Dict):
        """Cache JMeter metrics"""
        
        # Cache overall metrics
        overall_metrics = [
            ('avg_response_time', metrics.get('avg_response_time')),
            ('p90_response_time', metrics.get('p90_response_time')),
            ('p95_response_time', metrics.get('p95_response_time')),
            ('p99_response_time', metrics.get('p99_response_time')),
            ('throughput', metrics.get('throughput')),
            ('error_rate', metrics.get('error_rate')),
            ('success_rate', metrics.get('success_rate')),
        ]
        
        for metric_key, metric_value in overall_metrics:
            if metric_value is not None:
                db.add(BaselineMetric(
                    baseline_id=baseline_id,
                    category='jmeter',
                    metric_key=metric_key,
                    metric_value=float(metric_value),
                    metric_json=None,
                    transaction_name=None
                ))
        
        # Cache per-transaction metrics
        by_label = metrics.get('by_label', {})
        for transaction_name, trans_metrics in by_label.items():
            trans_metric_list = [
                ('avg_response_time', trans_metrics.get('avg_response_time')),
                ('p90', trans_metrics.get('p90')),
                ('p95', trans_metrics.get('p95')),
                ('error_rate', trans_metrics.get('error_rate')),
                ('throughput', trans_metrics.get('throughput')),
            ]
            
            for metric_key, metric_value in trans_metric_list:
                if metric_value is not None:
                    db.add(BaselineMetric(
                        baseline_id=baseline_id,
                        category='jmeter',
                        metric_key=metric_key,
                        metric_value=float(metric_value),
                        metric_json=None,
                        transaction_name=transaction_name
                    ))
        
        db.commit()
    
    @staticmethod
    def _cache_lighthouse_metrics(db: Session, baseline_id: str, metrics: Dict):
        """Cache Lighthouse metrics"""
        
        # Extract pages
        pages = metrics.get('pages', {})
        if not pages and 'performance_score' in metrics:
            # Single page
            pages = {'default': metrics}
        
        for page_url, page_metrics in pages.items():
            lighthouse_metrics = [
                ('performance_score', page_metrics.get('performance_score')),
                ('lcp', page_metrics.get('lcp')),
                ('cls', page_metrics.get('cls')),
                ('fcp', page_metrics.get('fcp')),
                ('tbt', page_metrics.get('tbt')),
                ('speed_index', page_metrics.get('speed_index')),
                ('tti', page_metrics.get('tti')),
            ]
            
            for metric_key, metric_value in lighthouse_metrics:
                if metric_value is not None:
                    db.add(BaselineMetric(
                        baseline_id=baseline_id,
                        category='lighthouse',
                        metric_key=metric_key,
                        metric_value=float(metric_value),
                        metric_json=None,
                        transaction_name=page_url
                    ))
        
        db.commit()
    
    @staticmethod
    def _cache_webvitals_metrics(db: Session, baseline_id: str, metrics: Dict):
        """Cache Web Vitals metrics"""
        
        # Similar to lighthouse but for web vitals
        webvitals_metrics = [
            ('lcp', metrics.get('lcp')),
            ('cls', metrics.get('cls')),
            ('fcp', metrics.get('fcp')),
            ('fid', metrics.get('fid')),
            ('ttfb', metrics.get('ttfb')),
        ]
        
        for metric_key, metric_value in webvitals_metrics:
            if metric_value is not None:
                db.add(BaselineMetric(
                    baseline_id=baseline_id,
                    category='web_vitals',
                    metric_key=metric_key,
                    metric_value=float(metric_value),
                    metric_json=None,
                    transaction_name=None
                ))
        
        db.commit()
    
    @staticmethod
    def get_baseline(db: Session, baseline_id: str) -> Optional[BaselineRun]:
        """Get baseline by ID"""
        return db.query(BaselineRun).filter(BaselineRun.baseline_id == baseline_id).first()
    
    @staticmethod
    def list_baselines(
        db: Session,
        application: str = None,
        environment: str = None,
        is_active: bool = None
    ) -> List[BaselineRun]:
        """
        List baselines with optional filters
        
        Args:
            db: Database session
            application: Filter by application
            environment: Filter by environment
            is_active: Filter by active status
        
        Returns:
            List of baselines
        """
        
        query = db.query(BaselineRun)
        
        if application:
            query = query.filter(BaselineRun.application == application)
        
        if environment:
            query = query.filter(BaselineRun.environment == environment)
        
        if is_active is not None:
            query = query.filter(BaselineRun.is_active == is_active)
        
        return query.order_by(BaselineRun.created_at.desc()).all()
    
    @staticmethod
    def update_baseline(
        db: Session,
        baseline_id: str,
        baseline_name: str = None,
        description: str = None,
        is_active: bool = None
    ) -> Optional[BaselineRun]:
        """Update baseline properties"""
        
        baseline = BaselineService.get_baseline(db, baseline_id)
        if not baseline:
            return None
        
        if baseline_name:
            baseline.baseline_name = baseline_name
        
        if description is not None:
            baseline.description = description
        
        if is_active is not None:
            baseline.is_active = is_active
        
        db.commit()
        db.refresh(baseline)
        return baseline
    
    @staticmethod
    def delete_baseline(db: Session, baseline_id: str) -> bool:
        """Delete a baseline"""
        
        baseline = BaselineService.get_baseline(db, baseline_id)
        if not baseline:
            return False
        
        db.delete(baseline)
        db.commit()
        return True
    
    @staticmethod
    def deactivate_baseline(db: Session, baseline_id: str) -> bool:
        """Deactivate a baseline (soft delete)"""
        
        baseline = BaselineService.get_baseline(db, baseline_id)
        if not baseline:
            return False
        
        baseline.is_active = False
        db.commit()
        return True
    
    @staticmethod
    def get_baseline_metrics(
        db: Session,
        baseline_id: str,
        category: str = None
    ) -> List[BaselineMetric]:
        """Get cached baseline metrics"""
        
        query = db.query(BaselineMetric).filter(BaselineMetric.baseline_id == baseline_id)
        
        if category:
            query = query.filter(BaselineMetric.category == category)
        
        return query.all()
