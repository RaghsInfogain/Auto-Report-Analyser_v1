"""
API Routes for Performance Comparison and Release Intelligence
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.comparison.services.baseline_service import BaselineService
from app.comparison.services.comparison_service import ComparisonService

router = APIRouter(prefix="/comparison", tags=["Performance Comparison"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BaselineCreate(BaseModel):
    """Request model for creating a baseline"""
    run_id: str
    application: str
    environment: str
    version: str
    baseline_name: str
    description: Optional[str] = None
    created_by: Optional[str] = "unknown"


class BaselineUpdate(BaseModel):
    """Request model for updating a baseline"""
    baseline_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ComparisonCreate(BaseModel):
    """Request model for creating a comparison"""
    baseline_id: str
    current_run_id: str
    comparison_type: str = 'full'  # 'full', 'jmeter', or 'lighthouse'


# ============================================================================
# BASELINE MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/baseline/set")
async def create_baseline(
    baseline_data: BaselineCreate,
    db: Session = Depends(get_db)
):
    """
    Mark a run as baseline
    
    **Request Body:**
    - run_id: Run identifier to mark as baseline
    - application: Application name
    - environment: Environment (dev/staging/prod)
    - version: Release version
    - baseline_name: User-friendly baseline name
    - description: Optional description
    - created_by: User identifier
    
    **Returns:**
    Baseline object with baseline_id
    """
    
    try:
        baseline = BaselineService.create_baseline(
            db=db,
            run_id=baseline_data.run_id,
            application=baseline_data.application,
            environment=baseline_data.environment,
            version=baseline_data.version,
            baseline_name=baseline_data.baseline_name,
            description=baseline_data.description,
            created_by=baseline_data.created_by
        )
        
        return {
            "success": True,
            "message": "Baseline created successfully",
            "baseline": baseline.to_dict()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating baseline: {str(e)}")


@router.get("/baseline/list")
async def list_baselines(
    application: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all baselines with optional filters
    
    **Query Parameters:**
    - application: Filter by application name
    - environment: Filter by environment
    - is_active: Filter by active status
    
    **Returns:**
    List of baseline objects
    """
    
    try:
        baselines = BaselineService.list_baselines(
            db=db,
            application=application,
            environment=environment,
            is_active=is_active
        )
        
        return {
            "success": True,
            "count": len(baselines),
            "baselines": [b.to_dict() for b in baselines]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing baselines: {str(e)}")


@router.get("/baseline/{baseline_id}")
async def get_baseline(
    baseline_id: str,
    db: Session = Depends(get_db)
):
    """
    Get baseline details by ID
    
    **Path Parameters:**
    - baseline_id: Baseline identifier
    
    **Returns:**
    Baseline object with details
    """
    
    baseline = BaselineService.get_baseline(db, baseline_id)
    
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    
    return {
        "success": True,
        "baseline": baseline.to_dict()
    }


@router.patch("/baseline/{baseline_id}")
async def update_baseline(
    baseline_id: str,
    update_data: BaselineUpdate,
    db: Session = Depends(get_db)
):
    """
    Update baseline properties
    
    **Path Parameters:**
    - baseline_id: Baseline identifier
    
    **Request Body:**
    - baseline_name: Optional new name
    - description: Optional new description
    - is_active: Optional active status
    
    **Returns:**
    Updated baseline object
    """
    
    baseline = BaselineService.update_baseline(
        db=db,
        baseline_id=baseline_id,
        baseline_name=update_data.baseline_name,
        description=update_data.description,
        is_active=update_data.is_active
    )
    
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    
    return {
        "success": True,
        "message": "Baseline updated successfully",
        "baseline": baseline.to_dict()
    }


@router.delete("/baseline/{baseline_id}")
async def delete_baseline(
    baseline_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a baseline
    
    **Path Parameters:**
    - baseline_id: Baseline identifier
    
    **Returns:**
    Success message
    """
    
    success = BaselineService.delete_baseline(db, baseline_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Baseline not found")
    
    return {
        "success": True,
        "message": "Baseline deleted successfully"
    }


@router.patch("/baseline/{baseline_id}/deactivate")
async def deactivate_baseline(
    baseline_id: str,
    db: Session = Depends(get_db)
):
    """
    Deactivate a baseline (soft delete)
    
    **Path Parameters:**
    - baseline_id: Baseline identifier
    
    **Returns:**
    Success message
    """
    
    success = BaselineService.deactivate_baseline(db, baseline_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Baseline not found")
    
    return {
        "success": True,
        "message": "Baseline deactivated successfully"
    }


# ============================================================================
# COMPARISON ENDPOINTS
# ============================================================================

@router.post("/compare")
async def create_comparison(
    comparison_data: ComparisonCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new performance comparison
    
    **Request Body:**
    - baseline_id: Baseline run identifier
    - current_run_id: Current run identifier
    - comparison_type: 'full' (default), 'jmeter', or 'lighthouse'
    
    **Returns:**
    Comparison object with comparison_id (processing in background)
    
    **Note:** Comparison runs asynchronously. Poll /compare/status/{comparison_id}
    to check progress.
    """
    
    try:
        comparison = await ComparisonService.create_comparison(
            db=db,
            baseline_id=comparison_data.baseline_id,
            current_run_id=comparison_data.current_run_id,
            comparison_type=comparison_data.comparison_type
        )
        
        return {
            "success": True,
            "message": "Comparison started successfully",
            "comparison_id": comparison.comparison_id,
            "status": comparison.status
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting comparison: {str(e)}")


@router.get("/compare/status/{comparison_id}")
async def get_comparison_status(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """
    Get comparison processing status
    
    **Path Parameters:**
    - comparison_id: Comparison identifier
    
    **Returns:**
    Status object with processing state
    """
    
    comparison = ComparisonService.get_comparison(db, comparison_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    return {
        "success": True,
        "comparison_id": comparison.comparison_id,
        "status": comparison.status,
        "overall_score": comparison.overall_score,
        "verdict": comparison.verdict,
        "created_at": comparison.created_at.isoformat() if comparison.created_at else None,
        "completed_at": comparison.completed_at.isoformat() if comparison.completed_at else None,
        "error_message": comparison.error_message
    }


@router.get("/compare/result/{comparison_id}")
async def get_comparison_result(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """
    Get full comparison results
    
    **Path Parameters:**
    - comparison_id: Comparison identifier
    
    **Returns:**
    Complete comparison data including regressions, improvements, and scores
    """
    
    comparison = ComparisonService.get_comparison(db, comparison_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    if comparison.status != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Comparison not yet completed. Status: {comparison.status}"
        )
    
    return {
        "success": True,
        "comparison": comparison.to_dict(),
        "baseline_id": comparison.baseline_id,
        "current_run_id": comparison.current_run_id
    }


@router.get("/compare/history")
async def list_comparisons(
    baseline_id: Optional[str] = Query(None),
    current_run_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    List comparison history with optional filters
    
    **Query Parameters:**
    - baseline_id: Filter by baseline
    - current_run_id: Filter by current run
    - limit: Maximum number of results (default: 50, max: 200)
    
    **Returns:**
    List of comparison objects
    """
    
    try:
        comparisons = ComparisonService.list_comparisons(
            db=db,
            baseline_id=baseline_id,
            current_run_id=current_run_id,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(comparisons),
            "comparisons": [c.to_dict() for c in comparisons]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing comparisons: {str(e)}")


# ============================================================================
# RELEASE INTELLIGENCE ENDPOINTS
# ============================================================================

@router.get("/release/score/{comparison_id}")
async def get_release_score(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """
    Get release health score and verdict
    
    **Path Parameters:**
    - comparison_id: Comparison identifier
    
    **Returns:**
    Release scores and verdict details
    """
    
    comparison = ComparisonService.get_comparison(db, comparison_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    if comparison.status != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Comparison not yet completed. Status: {comparison.status}"
        )
    
    comparison_data = comparison.comparison_data or {}
    release_score_data = comparison_data.get('release_score', {})
    
    return {
        "success": True,
        "comparison_id": comparison_id,
        "overall_score": comparison.overall_score,
        "backend_score": comparison.backend_score,
        "frontend_score": comparison.frontend_score,
        "reliability_score": comparison.reliability_score,
        "verdict": comparison.verdict,
        "verdict_details": release_score_data.get('verdict_details', {}),
        "classification": release_score_data.get('classification', 'unknown')
    }


@router.get("/release/verdict/{comparison_id}")
async def get_release_verdict(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """
    Get release recommendation and decision
    
    **Path Parameters:**
    - comparison_id: Comparison identifier
    
    **Returns:**
    Release verdict with detailed recommendation
    """
    
    comparison = ComparisonService.get_comparison(db, comparison_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    if comparison.status != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Comparison not yet completed. Status: {comparison.status}"
        )
    
    comparison_data = comparison.comparison_data or {}
    release_score_data = comparison_data.get('release_score', {})
    verdict_details = release_score_data.get('verdict_details', {})
    
    return {
        "success": True,
        "comparison_id": comparison_id,
        "verdict": comparison.verdict,
        "verdict_text": verdict_details.get('verdict_text', 'Unknown'),
        "recommendation": verdict_details.get('recommendation', ''),
        "overall_score": comparison.overall_score,
        "blocking_reasons": verdict_details.get('blocking_reasons', []),
        "risk_factors": verdict_details.get('risk_factors', []),
        "confidence": verdict_details.get('confidence', 'medium')
    }


@router.get("/release/regressions/{comparison_id}")
async def get_regressions(
    comparison_id: str,
    severity: Optional[str] = Query(None, regex="^(critical|major|minor|stable|improvement)$"),
    category: Optional[str] = Query(None, regex="^(jmeter|lighthouse|web_vitals)$"),
    db: Session = Depends(get_db)
):
    """
    Get regression details for a comparison
    
    **Path Parameters:**
    - comparison_id: Comparison identifier
    
    **Query Parameters:**
    - severity: Filter by severity (critical/major/minor/stable/improvement)
    - category: Filter by category (jmeter/lighthouse/web_vitals)
    
    **Returns:**
    List of regression/improvement details
    """
    
    try:
        regressions = ComparisonService.get_regressions(
            db=db,
            comparison_id=comparison_id,
            severity=severity,
            category=category
        )
        
        return {
            "success": True,
            "comparison_id": comparison_id,
            "count": len(regressions),
            "regressions": [r.to_dict() for r in regressions]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving regressions: {str(e)}")


# ============================================================================
# REPORT GENERATION ENDPOINTS
# ============================================================================

@router.get("/report/summary/{comparison_id}")
async def get_comparison_summary(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """
    Get executive summary of comparison
    
    **Path Parameters:**
    - comparison_id: Comparison identifier
    
    **Returns:**
    Natural language executive summary
    """
    
    comparison = ComparisonService.get_comparison(db, comparison_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    if comparison.status != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Comparison not yet completed. Status: {comparison.status}"
        )
    
    return {
        "success": True,
        "comparison_id": comparison_id,
        "summary": comparison.summary_text or "No summary available",
        "overall_score": comparison.overall_score,
        "verdict": comparison.verdict,
        "regression_count": comparison.regression_count,
        "improvement_count": comparison.improvement_count
    }


@router.get("/health")
async def comparison_health_check():
    """Health check for comparison service"""
    return {
        "status": "healthy",
        "service": "Performance Comparison Engine",
        "version": "1.0.0"
    }
