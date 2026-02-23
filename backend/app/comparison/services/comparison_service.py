"""
Comparison Service
Orchestrates the performance comparison workflow
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import asyncio

from app.database.models import ComparisonResult, RegressionDetail, AnalysisResult
from app.database.service import DatabaseService
from app.comparison.engines.jmeter_comparison import JMeterComparisonEngine
from app.comparison.engines.lighthouse_comparison import LighthouseComparisonEngine
from app.comparison.engines.correlation_engine import CorrelationEngine
from app.comparison.engines.release_scorer import ReleaseScorer
from .baseline_service import BaselineService


class ComparisonService:
    """
    Orchestrates performance comparison between baseline and current runs
    """
    
    @staticmethod
    async def create_comparison(
        db: Session,
        baseline_id: str,
        current_run_id: str,
        comparison_type: str = 'full'
    ) -> ComparisonResult:
        """
        Create and execute a comparison
        
        Args:
            db: Database session
            baseline_id: Baseline run identifier
            current_run_id: Current run identifier
            comparison_type: 'full', 'jmeter', or 'lighthouse'
        
        Returns:
            ComparisonResult object (processing in background)
        """
        
        # Validate inputs
        baseline = BaselineService.get_baseline(db, baseline_id)
        if not baseline:
            raise ValueError(f"Baseline {baseline_id} not found")
        
        current_files = DatabaseService.get_files_by_run_id(db, current_run_id)
        if not current_files:
            raise ValueError(f"Run {current_run_id} not found")
        
        # Create comparison record
        comparison_id = str(uuid.uuid4())
        comparison = ComparisonResult(
            comparison_id=comparison_id,
            baseline_id=baseline_id,
            current_run_id=current_run_id,
            comparison_type=comparison_type,
            status='processing'
        )
        
        db.add(comparison)
        db.commit()
        db.refresh(comparison)
        
        # Execute comparison asynchronously
        try:
            await ComparisonService._execute_comparison(
                db, comparison_id, baseline, current_run_id, comparison_type
            )
        except Exception as e:
            # Update status to failed
            comparison.status = 'failed'
            comparison.error_message = str(e)
            db.commit()
            raise
        
        return comparison
    
    @staticmethod
    async def _execute_comparison(
        db: Session,
        comparison_id: str,
        baseline: Any,
        current_run_id: str,
        comparison_type: str
    ):
        """Execute the comparison workflow"""
        
        # Get baseline metrics from database
        baseline_run_id = baseline.run_id
        baseline_metrics = ComparisonService._get_run_metrics(db, baseline_run_id)
        
        # Get current run metrics
        current_metrics = ComparisonService._get_run_metrics(db, current_run_id)
        
        # Initialize results containers
        jmeter_results = {}
        lighthouse_results = {}
        correlation_results = {}
        release_score_data = {}
        
        # Run comparisons based on type
        if comparison_type in ['full', 'jmeter']:
            if baseline_metrics.get('jmeter') and current_metrics.get('jmeter'):
                jmeter_engine = JMeterComparisonEngine()
                jmeter_results = jmeter_engine.compare(
                    baseline_metrics['jmeter'],
                    current_metrics['jmeter']
                )
        
        if comparison_type in ['full', 'lighthouse']:
            if baseline_metrics.get('lighthouse') and current_metrics.get('lighthouse'):
                lighthouse_engine = LighthouseComparisonEngine()
                lighthouse_results = lighthouse_engine.compare(
                    baseline_metrics['lighthouse'],
                    current_metrics['lighthouse']
                )
        
        # Run correlation and release scoring for full comparison
        if comparison_type == 'full' and jmeter_results and lighthouse_results:
            correlation_engine = CorrelationEngine()
            correlation_results = correlation_engine.correlate(
                jmeter_results,
                lighthouse_results
            )
            
            release_scorer = ReleaseScorer()
            release_score_data = release_scorer.calculate_release_score(
                jmeter_results,
                lighthouse_results,
                correlation_results
            )
        
        # Store results in database
        await ComparisonService._store_comparison_results(
            db,
            comparison_id,
            jmeter_results,
            lighthouse_results,
            correlation_results,
            release_score_data
        )
    
    @staticmethod
    def _get_run_metrics(db: Session, run_id: str) -> Dict[str, Dict]:
        """
        Get all analysis metrics for a run
        
        Returns:
            {
                'jmeter': {...},
                'lighthouse': {...},
                'web_vitals': {...}
            }
        """
        
        files = DatabaseService.get_files_by_run_id(db, run_id)
        metrics = {}
        
        for file in files:
            analysis = DatabaseService.get_analysis_result(db, file.file_id)
            if analysis and analysis.metrics:
                category = analysis.category
                
                if category == 'jmeter':
                    metrics['jmeter'] = analysis.metrics
                elif category == 'lighthouse':
                    metrics['lighthouse'] = analysis.metrics
                elif category == 'web_vitals':
                    metrics['web_vitals'] = analysis.metrics
        
        return metrics
    
    @staticmethod
    async def _store_comparison_results(
        db: Session,
        comparison_id: str,
        jmeter_results: Dict,
        lighthouse_results: Dict,
        correlation_results: Dict,
        release_score_data: Dict
    ):
        """Store comparison results in database"""
        
        # Get comparison record
        comparison = db.query(ComparisonResult).filter(
            ComparisonResult.comparison_id == comparison_id
        ).first()
        
        if not comparison:
            return
        
        # Extract scores
        scores = release_score_data.get('scores', {})
        verdict_details = release_score_data.get('verdict_details', {})
        
        # Update comparison record
        comparison.overall_score = scores.get('overall_score')
        comparison.backend_score = scores.get('backend_score')
        comparison.frontend_score = scores.get('frontend_score')
        comparison.reliability_score = scores.get('reliability_score')
        comparison.verdict = release_score_data.get('verdict')
        comparison.status = 'completed'
        comparison.completed_at = datetime.utcnow()
        
        # Count regressions and improvements
        jmeter_regressions = jmeter_results.get('regressions', [])
        lighthouse_regressions = lighthouse_results.get('regressions', [])
        jmeter_improvements = jmeter_results.get('improvements', [])
        lighthouse_improvements = lighthouse_results.get('improvements', [])
        
        comparison.regression_count = len(jmeter_regressions) + len(lighthouse_regressions)
        comparison.improvement_count = len(jmeter_improvements) + len(lighthouse_improvements)
        comparison.stable_count = (
            len(jmeter_results.get('stable_metrics', [])) +
            len(lighthouse_results.get('stable_metrics', []))
        )
        
        # Store detailed comparison data
        comparison.comparison_data = {
            'jmeter': jmeter_results,
            'lighthouse': lighthouse_results,
            'correlation': correlation_results,
            'release_score': release_score_data
        }
        
        # Generate summary text
        if 'verdict_details' in release_score_data:
            release_scorer = ReleaseScorer()
            release_scorer.scores = scores
            release_scorer.verdict_details = verdict_details
            comparison.summary_text = release_scorer.generate_executive_summary(
                jmeter_results,
                lighthouse_results,
                correlation_results
            )
        
        db.commit()
        
        # Store individual regression details
        await ComparisonService._store_regression_details(
            db,
            comparison_id,
            jmeter_regressions,
            lighthouse_regressions
        )
    
    @staticmethod
    async def _store_regression_details(
        db: Session,
        comparison_id: str,
        jmeter_regressions: list,
        lighthouse_regressions: list
    ):
        """Store individual regression/improvement records"""
        
        # Store JMeter regressions
        for regression in jmeter_regressions:
            detail = RegressionDetail(
                comparison_id=comparison_id,
                metric_name=regression['metric_name'],
                transaction_name=regression.get('transaction_name'),
                category='jmeter',
                baseline_value=regression['baseline_value'],
                current_value=regression['current_value'],
                change_percent=regression['change_percent'],
                change_absolute=regression['change_absolute'],
                severity=regression['severity'],
                change_type='regression' if regression['is_regression'] else 'improvement',
                details=regression
            )
            db.add(detail)
        
        # Store Lighthouse regressions
        for regression in lighthouse_regressions:
            detail = RegressionDetail(
                comparison_id=comparison_id,
                metric_name=regression['metric_name'],
                transaction_name=regression.get('page_url'),
                category='lighthouse',
                baseline_value=regression['baseline_value'],
                current_value=regression['current_value'],
                change_percent=regression['change_percent'],
                change_absolute=regression['change_absolute'],
                severity=regression['severity'],
                change_type='regression' if regression['is_regression'] else 'improvement',
                details=regression
            )
            db.add(detail)
        
        db.commit()
    
    @staticmethod
    def get_comparison(db: Session, comparison_id: str) -> Optional[ComparisonResult]:
        """Get comparison by ID"""
        return db.query(ComparisonResult).filter(
            ComparisonResult.comparison_id == comparison_id
        ).first()
    
    @staticmethod
    def list_comparisons(
        db: Session,
        baseline_id: str = None,
        current_run_id: str = None,
        limit: int = 50
    ) -> list:
        """List comparisons with optional filters"""
        
        query = db.query(ComparisonResult)
        
        if baseline_id:
            query = query.filter(ComparisonResult.baseline_id == baseline_id)
        
        if current_run_id:
            query = query.filter(ComparisonResult.current_run_id == current_run_id)
        
        return query.order_by(ComparisonResult.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_regressions(
        db: Session,
        comparison_id: str,
        severity: str = None,
        category: str = None
    ) -> list:
        """Get regression details with optional filters"""
        
        query = db.query(RegressionDetail).filter(
            RegressionDetail.comparison_id == comparison_id
        )
        
        if severity:
            query = query.filter(RegressionDetail.severity == severity)
        
        if category:
            query = query.filter(RegressionDetail.category == category)
        
        return query.all()
