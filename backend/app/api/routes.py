from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import uuid
from pathlib import Path
import time
import json
from datetime import datetime
import pandas as pd
import asyncio
from functools import wraps

from app.parsers.json_parser import JSONParser
from app.parsers.csv_parser import CSVParser
from app.parsers.jtl_parser import JTLParser
from app.parsers.jtl_parser_v2 import JTLParserV2
from app.analyzers.web_vitals_analyzer import WebVitalsAnalyzer
from app.analyzers.jmeter_analyzer import JMeterAnalyzer
from app.analyzers.jmeter_analyzer_v2 import JMeterAnalyzerV2
from app.analyzers.ui_performance_analyzer import UIPerformanceAnalyzer
from app.report_generator.report_builder import ReportBuilder
from app.report_generator.html_report_generator import HTMLReportGenerator
from app.report_generator.pdf_generator import PDFReportGenerator
from app.report_generator.ppt_generator import PPTReportGenerator
from app.database import get_db
from app.database.service import DatabaseService
from app.database.models import UploadedFile, AnalysisResult, GeneratedReport
from app.ai.chatbot_engine import PerformanceChatbot
from app.utils.progress_tracker import ReportProgressTracker

router = APIRouter()

# Timeout decorator for endpoints
def timeout_handler(timeout_seconds: float):
    """Decorator to add timeout to async endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail=f"Request timed out after {timeout_seconds} seconds"
                )
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator

# Create uploads, merged files, and reports directories
# Use absolute paths to ensure consistency
# routes.py is in backend/app/api/, so parent.parent.parent = backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
MERGED_DIR = BASE_DIR / "merged"
REPORTS_DIR = BASE_DIR / "reports"
UPLOAD_DIR.mkdir(exist_ok=True)
MERGED_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

@router.get("/health")
async def health_check():
    """Health check endpoint - lightweight, no database access"""
    import time
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "Auto Report Analyzer API"
    }

@router.post("/files/{file_id}/generate-complete-report")
async def generate_complete_report(file_id: str, db: Session = Depends(get_db)):
    """
    Complete workflow: Analyze file and generate all reports (HTML, PDF, PPT)
    Returns progress updates and final report URLs
    """
    # Step 1: Validate file exists
    db_file = DatabaseService.get_uploaded_file(db, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Update status: analyzing
        db_file.report_status = "analyzing"
        db.commit()
        
        file_path = db_file.file_path
        category = db_file.category
        
        # Step 2: Perform Analysis
        start_time = time.time()
        
        # Parse file based on category and extension
        if category == "web_vitals":
            if file_path.endswith(".json"):
                data = JSONParser.parse(file_path, category)
            else:
                data = CSVParser.parse(file_path, category)
            metrics_obj = WebVitalsAnalyzer.analyze(data)
            metrics = metrics_obj.dict()
            record_count = len(data) if isinstance(data, list) else 1
        elif category == "jmeter":
            if file_path.endswith(".jtl") or file_path.endswith(".csv"):
                data = JTLParserV2.parse(file_path)
            else:
                data = JSONParser.parse(file_path, category)
            metrics_obj = JMeterAnalyzerV2.analyze(data)
            metrics = metrics_obj.dict()
            record_count = len(data) if isinstance(data, list) else 1
        elif category == "ui_performance":
            if file_path.endswith(".json"):
                data = JSONParser.parse(file_path, category)
            else:
                data = CSVParser.parse(file_path, category)
            metrics_obj = UIPerformanceAnalyzer.analyze(data)
            metrics = metrics_obj.dict()
            record_count = len(data) if isinstance(data, list) else 1
        else:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")
        
        analysis_duration = time.time() - start_time
        
        # Update record count
        db_file.record_count = record_count
        
        # Store or update analysis in database
        existing_analysis = DatabaseService.get_analysis_result(db, file_id)
        if existing_analysis:
            # Update existing analysis
            existing_analysis.metrics = metrics
            existing_analysis.analyzed_at = datetime.utcnow()
            existing_analysis.analysis_duration = analysis_duration
            db.commit()
            db_analysis = existing_analysis
        else:
            # Create new analysis
            db_analysis = DatabaseService.create_analysis_result(
                db=db,
                file_id=file_id,
                category=category,
                metrics=metrics,
                analysis_duration=analysis_duration
            )
        
        # Update status: generating
        db_file.report_status = "generating"
        db.commit()
        
        # Step 3: Generate all report types
        report_urls = {}
        
        # Generate reports based on category
        if category == "jmeter":
            # Generate HTML Report
            html_content = HTMLReportGenerator.generate_jmeter_html_report(metrics)
            pdf_bytes = PDFReportGenerator.generate_jmeter_pdf_report(metrics)
            ppt_bytes = PPTReportGenerator.generate_jmeter_ppt_report(metrics)
        elif category == "web_vitals":
            # Generate Web Vitals reports
            html_content = HTMLReportGenerator.generate_web_vitals_html_report(metrics, db_file.filename)
            pdf_bytes = PDFReportGenerator.generate_web_vitals_pdf_report(metrics, db_file.filename)
            ppt_bytes = PPTReportGenerator.generate_web_vitals_ppt_report(metrics, db_file.filename)
        elif category == "ui_performance":
            # Generate UI Performance reports
            html_content = HTMLReportGenerator.generate_ui_performance_html_report(metrics, db_file.filename)
            pdf_bytes = PDFReportGenerator.generate_ui_performance_pdf_report(metrics, db_file.filename)
            ppt_bytes = PPTReportGenerator.generate_ui_performance_ppt_report(metrics, db_file.filename)
        else:
            raise HTTPException(status_code=400, detail=f"Report generation not supported for category: {category}")
        
        # Save HTML Report
        html_report_id = str(uuid.uuid4())
        html_path = REPORTS_DIR / f"{html_report_id}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        html_report = DatabaseService.create_generated_report(
            db=db,
            file_id=file_id,
            report_type="html",
            report_path=str(html_path),
            report_content=html_content,
            file_size=len(html_content.encode('utf-8')),
            generated_by="raghskmr"
        )
        html_report_id = html_report.report_id
        report_urls["html"] = f"/api/files/{file_id}/reports/html"
        
        # Save PDF Report
        pdf_path = REPORTS_DIR / f"{file_id}_report.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        pdf_report = DatabaseService.create_generated_report(
            db=db,
            file_id=file_id,
            report_type="pdf",
            report_path=str(pdf_path),
            file_size=len(pdf_bytes),
            generated_by="raghskmr"
        )
        pdf_report_id = pdf_report.report_id
        report_urls["pdf"] = f"/api/files/{file_id}/reports/pdf"
        
        # Save PowerPoint Report
        ppt_path = REPORTS_DIR / f"{file_id}_report.pptx"
        with open(ppt_path, "wb") as f:
            f.write(ppt_bytes)
        
        ppt_report = DatabaseService.create_generated_report(
            db=db,
            file_id=file_id,
            report_type="ppt",
            report_path=str(ppt_path),
            file_size=len(ppt_bytes),
            generated_by="raghskmr"
        )
        ppt_report_id = ppt_report.report_id
        report_urls["ppt"] = f"/api/files/{file_id}/reports/ppt"
        
        # Update status: generated
        db_file.report_status = "generated"
        db.commit()
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": db_file.filename,
            "record_count": record_count,
            "analysis_duration": analysis_duration,
            "report_urls": report_urls,
            "report_ids": {
                "html": html_report_id,
                "pdf": pdf_report_id,
                "ppt": ppt_report_id
            }
        }
    except Exception as e:
        # Update status: error
        db_file.report_status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@router.get("/files/{file_id}/reports/{report_type}")
async def get_file_report(file_id: str, report_type: str, db: Session = Depends(get_db)):
    """Get a specific report for a file by type (html, pdf, ppt)"""
    db_file = DatabaseService.get_uploaded_file(db, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get all reports for this file
    reports = DatabaseService.get_reports_by_file(db, file_id)
    
    # Find report of requested type
    report = next((r for r in reports if r.report_type == report_type), None)
    if not report:
        raise HTTPException(status_code=404, detail=f"{report_type.upper()} report not found")
    
    if report_type == "html":
        # Return HTML content
        if report.report_content:
            return HTMLResponse(content=report.report_content)
        elif report.report_path and os.path.exists(report.report_path):
            with open(report.report_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            raise HTTPException(status_code=404, detail="HTML report content not found")
    
    elif report_type == "pdf":
        # Return PDF file
        if report.report_path and os.path.exists(report.report_path):
            with open(report.report_path, "rb") as f:
                pdf_bytes = f.read()
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={db_file.filename.replace('.jtl', '').replace('.csv', '').replace('.json', '')}_report.pdf"
                }
            )
        else:
            raise HTTPException(status_code=404, detail="PDF report file not found")
    
    elif report_type == "ppt":
        # Return PowerPoint file
        if report.report_path and os.path.exists(report.report_path):
            with open(report.report_path, "rb") as f:
                ppt_bytes = f.read()
            return Response(
                content=ppt_bytes,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={
                    "Content-Disposition": f"attachment; filename={db_file.filename.replace('.jtl', '').replace('.csv', '').replace('.json', '')}_report.pptx"
                }
            )
        else:
            raise HTTPException(status_code=404, detail="PowerPoint report file not found")
    
    else:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    categories: List[str] = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload files with their categories
    Expected: files and categories arrays (same length)
    All files in single upload share one Run ID
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided. Please select at least one file to upload.")
    
    if not categories or len(categories) == 0:
        raise HTTPException(status_code=400, detail="No categories provided. Please specify a category for each file.")
    
    if len(files) != len(categories):
        raise HTTPException(
            status_code=400, 
            detail=f"Number of files ({len(files)}) must match number of categories ({len(categories)}). Please ensure each file has a corresponding category."
        )
    
    # Generate a single sequential Run ID for this upload batch
    run_id = DatabaseService.generate_next_run_id(db)
    
    uploaded_files = []
    jmeter_files_data = []  # Store JMeter files for merging
    jmeter_filenames = []
    other_files = []  # Store non-JMeter files
    
    # First pass: Save all files and group JMeter files
    for file, category in zip(files, categories):
        if category not in ["web_vitals", "jmeter", "ui_performance"]:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        file_extension = Path(file.filename).suffix.lower()
        
        # Validate file type
        if category == "jmeter":
            if file_extension not in [".jtl", ".csv", ".xml"]:
                raise HTTPException(status_code=400, detail="JMeter files must be .jtl, .csv, or .xml")
        else:
            if file_extension not in [".json", ".csv"]:
                raise HTTPException(status_code=400, detail="Files must be .json or .csv")
        
        # Generate unique file ID and save file
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}{file_extension}"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Store in database with run_id
        db_file = DatabaseService.create_uploaded_file(
            db=db,
            filename=file.filename,
            category=category,
            file_path=str(file_path),
            file_size=len(content),
            uploaded_by="current_user",
            run_id=run_id  # All files in this upload share the same run_id
        )
        
        # Group JMeter files for merging
        if category == "jmeter":
            jmeter_files_data.append({
                "db_file": db_file,
                "file_path": file_path,
                "file_id": file_id
            })
            jmeter_filenames.append(file.filename)
        else:
            other_files.append(db_file)
        
        uploaded_files.append(db_file.to_dict())
    
    # Handle JMeter files: Merge if multiple, keep single as-is
    if len(jmeter_files_data) > 1:
        # USE CASE 2: Multiple files - Merge first, then analyze merged file
        print(f"\n{'='*60}")
        print(f"USE CASE 2: Multiple JMeter files detected")
        print(f"Merging {len(jmeter_files_data)} JMeter files for run {run_id}...")
        print(f"{'='*60}\n")
        
        # Parse all JMeter files
        all_jmeter_data = []
        for jmeter_file_info in jmeter_files_data:
            file_path = jmeter_file_info["file_path"]
            print(f"  Parsing {Path(file_path).name}...")
            try:
                if str(file_path).endswith(".jtl") or str(file_path).endswith(".csv"):
                    data = JTLParserV2.parse(str(file_path))
                else:
                    data = JSONParser.parse(str(file_path), "jmeter")
                all_jmeter_data.append(data)
                print(f"    ✓ Parsed {len(data):,} records")
            except Exception as e:
                print(f"    ✗ Error parsing {Path(file_path).name}: {e}")
                raise HTTPException(status_code=400, detail=f"Error parsing file {Path(file_path).name}: {e}")
        
        # Merge all data
        merged_data = JTLParserV2.merge_data(all_jmeter_data)
        print(f"  ✓ Merged {len(merged_data):,} total records")
        
        # Save merged file as CSV (JTL format)
        MERGED_DIR.mkdir(exist_ok=True)
        merged_file_path = MERGED_DIR / f"{run_id}_merged.jtl"
        
        # Write merged data as CSV (JTL format)
        # Convert list of dicts to DataFrame, handling None values
        try:
            df = pd.DataFrame(merged_data)
            df.to_csv(merged_file_path, index=False)
            merged_file_size = merged_file_path.stat().st_size
            print(f"  ✓ Saved merged file: {merged_file_path} ({merged_file_size:,} bytes)")
        except Exception as e:
            print(f"  ✗ Error saving merged file: {e}")
            raise HTTPException(status_code=500, detail=f"Error saving merged file: {e}")
        
        # Update all JMeter file records to point to merged file
        merged_filename = f"MERGED_{run_id}_{'+'.join(jmeter_filenames[:3])}{'...' if len(jmeter_filenames) > 3 else ''}"
        for jmeter_file_info in jmeter_files_data:
            db_file = jmeter_file_info["db_file"]
            db_file.file_path = str(merged_file_path)
            db_file.filename = merged_filename
            db_file.file_size = merged_file_path.stat().st_size
            db_file.record_count = len(merged_data)
        
        db.commit()
        print(f"✓ Merged file created and linked to {len(jmeter_files_data)} file records")
        print(f"  All files now point to: {merged_file_path}")
        
    elif len(jmeter_files_data) == 1:
        # USE CASE 1: Single file - Keep original file, just get record count
        print(f"\n{'='*60}")
        print(f"USE CASE 1: Single JMeter file detected")
        print(f"Processing single file for run {run_id}...")
        print(f"{'='*60}\n")
        
        single_file_info = jmeter_files_data[0]
        file_path = single_file_info["file_path"]
        db_file = single_file_info["db_file"]
        
        print(f"  File: {db_file.filename}")
        print(f"  Path: {file_path}")
        print(f"  File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Uploaded file not found: {file_path}")
        
        # Parse to get record count (file_path stays as original uploaded file)
        try:
            if str(file_path).endswith(".jtl") or str(file_path).endswith(".csv"):
                data = JTLParserV2.parse(str(file_path))
            else:
                data = JSONParser.parse(str(file_path), "jmeter")
            db_file.record_count = len(data)
            db.commit()
            print(f"  ✓ Parsed {len(data):,} records")
            print(f"  ✓ File path preserved: {file_path}")
            print(f"  ✓ Single file ready for analysis")
        except Exception as e:
            print(f"  ✗ Error parsing file: {e}")
            raise HTTPException(status_code=400, detail=f"Error parsing file: {e}")
    
    return {"message": "Files uploaded successfully", "run_id": run_id, "files": uploaded_files}

@router.get("/files")
@timeout_handler(30.0)  # 30 second timeout
async def list_files(db: Session = Depends(get_db)):
    """List all uploaded files"""
    try:
        files = DatabaseService.get_all_uploaded_files(db)
        return {"files": [f.to_dict() for f in files]}
    except Exception as e:
        print(f"Error in list_files: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading files: {str(e)}")

@router.get("/runs")
@timeout_handler(30.0)  # 30 second timeout
async def list_runs(db: Session = Depends(get_db)):
    """List all runs (grouped by upload batch)"""
    try:
        import time
        start_time = time.time()
        runs = DatabaseService.get_all_run_ids(db)
        elapsed = time.time() - start_time
        print(f"get_all_run_ids took {elapsed:.2f} seconds, returned {len(runs)} runs")
        return {"runs": runs}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in list_runs: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading runs: {str(e)}")

@router.get("/runs/{run_id}")
@timeout_handler(30.0)  # 30 second timeout
async def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get details of a specific run"""
    files = DatabaseService.get_files_by_run_id(db, run_id)
    if not files:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Calculate totals
    total_size = sum(f.file_size for f in files)
    total_records = sum(f.record_count for f in files)
    categories = list(set(f.category for f in files))
    
    # Determine overall status
    statuses = [f.report_status for f in files]
    if all(s == 'generated' for s in statuses):
        overall_status = 'generated'
    elif any(s == 'error' for s in statuses):
        overall_status = 'error'
    elif any(s == 'generating' for s in statuses):
        overall_status = 'generating'
    elif any(s == 'analyzing' for s in statuses):
        overall_status = 'analyzing'
    else:
        overall_status = 'pending'
    
    return {
        "run_id": run_id,
        "file_count": len(files),
        "total_size": total_size,
        "total_records": total_records,
        "categories": categories,
        "report_status": overall_status,
        "uploaded_at": files[0].uploaded_at.isoformat() if files else None,
        "files": [f.to_dict() for f in files]
    }

@router.delete("/runs/{run_id}")
async def delete_run(run_id: str, db: Session = Depends(get_db)):
    """Delete a run and all its files"""
    files = DatabaseService.get_files_by_run_id(db, run_id)
    if not files:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Delete physical files
    for f in files:
        try:
            if os.path.exists(f.file_path):
                os.remove(f.file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
    
    # Delete from database
    DatabaseService.delete_run(db, run_id)
    
    return {"message": f"Run {run_id} deleted successfully"}

@router.get("/runs/{run_id}/progress")
async def get_report_progress(run_id: str):
    """Get progress of report generation for a run"""
    progress = ReportProgressTracker.get_progress(run_id)
    
    if not progress:
        # Check if run exists and has stuck status
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            files = DatabaseService.get_files_by_run_id(db, run_id)
            if files and any(f.report_status in ["analyzing", "generating"] for f in files):
                # Check if it's stuck
                if ReportProgressTracker.is_stuck(run_id):
                    # Reset stuck status
                    for f in files:
                        if f.report_status in ["analyzing", "generating"]:
                            f.report_status = "pending"
                    db.commit()
                    return {
                        "run_id": run_id,
                        "status": "stuck",
                        "message": "Report generation appears to be stuck. Status has been reset. Please try again.",
                        "can_retry": True
                    }
                else:
                    return {
                        "run_id": run_id,
                        "status": "unknown",
                        "message": "No progress tracking found. Report generation may not have started."
                    }
            else:
                return {
                    "run_id": run_id,
                    "status": "not_found",
                    "message": "Run not found or no active report generation"
                }
        finally:
            db.close()
    
    return progress

@router.post("/runs/{run_id}/generate-report")
@timeout_handler(180.0)  # 3 minutes timeout for report generation
async def generate_run_report(run_id: str, db: Session = Depends(get_db), regenerate: bool = Query(False, description="Regenerate reports from existing analysis")):
    """
    Generate consolidated report for a run (all files in the run)
    Analyzes all files and creates a single combined report
    If regenerate=True, regenerates reports from existing analysis
    
    Timeout: 3 minutes maximum
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
    
    try:
        files = DatabaseService.get_files_by_run_id(db, run_id)
    except Exception as e:
        print(f"Error getting files for run {run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if not files:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Set maximum timeout (3 minutes)
    MAX_TIMEOUT = 180  # 3 minutes in seconds
    
    # Check if already in progress
    existing_progress = ReportProgressTracker.get_progress(run_id)
    if existing_progress and existing_progress["status"] == "in_progress":
        # ALWAYS check for stuck status in database first - reset if found
        stuck_in_db = any(f.report_status in ["analyzing", "generating"] for f in files)
        if stuck_in_db:
            print(f"⚠️  Run {run_id} has stuck status in database, resetting to pending...")
            for f in files:
                if f.report_status in ["analyzing", "generating"]:
                    f.report_status = "pending"
            db.commit()
            ReportProgressTracker.clear_progress(run_id)  # Clear old progress
        
        # Check if stuck in progress tracker
        if ReportProgressTracker.is_stuck(run_id, timeout_minutes=5):
            # Reset stuck status
            print(f"⚠️  Run {run_id} appears stuck in progress tracker, resetting...")
            for f in files:
                if f.report_status in ["analyzing", "generating"]:
                    f.report_status = "pending"
            db.commit()
            ReportProgressTracker.clear_progress(run_id)  # Clear old progress
            ReportProgressTracker.initialize(run_id)  # Re-initialize
        elif existing_progress and existing_progress.get("status") == "in_progress":
            # Already in progress, return current progress (don't start new generation)
            print(f"ℹ️  Run {run_id} already in progress, returning current progress")
            return existing_progress
    
    # Initialize progress tracking for new generation
    ReportProgressTracker.initialize(run_id)
    print(f"✓ Initialized progress tracking for {run_id}")
    
    def run_analysis_with_timeout():
        """Run analysis in a separate thread with timeout"""
        try:
            print(f"\n{'='*60}")
            print(f"Starting report generation thread for {run_id}")
            print(f"{'='*60}\n")
            
            # Update status for all files
            for f in files:
                f.report_status = "analyzing" if not regenerate else "generating"
            db.commit()
            
            result = perform_analysis_and_report_generation(files, db, run_id, regenerate, start_time=time.time())
            
            print(f"\n{'='*60}")
            print(f"Report generation thread completed for {run_id}")
            if isinstance(result, dict):
                print(f"Result success: {result.get('success', False)}")
                print(f"Result keys: {list(result.keys())}")
            else:
                print(f"Result type: {type(result)}")
            print(f"{'='*60}\n")
            
            # Ensure result is a dict with success flag
            if not isinstance(result, dict):
                result = {"success": True, "run_id": run_id, "message": "Report generation completed"}
            elif "success" not in result:
                result["success"] = True
            
            return result
        except Exception as e:
            # Update status to error
            error_msg = str(e)
            print(f"\n{'='*60}")
            print(f"✗ ERROR in report generation thread for {run_id}")
            print(f"Error: {error_msg}")
            print(f"{'='*60}\n")
            import traceback
            traceback.print_exc()
            ReportProgressTracker.fail(run_id, error_msg)
            try:
                for f in files:
                    f.report_status = "error"
                db.commit()
            except Exception as db_error:
                print(f"✗ Error updating database status: {str(db_error)}")
            # Wrap in a dict so it can be returned and checked
            return {
                "success": False,
                "error": error_msg,
                "run_id": run_id
            }
    
    try:
        # Use ThreadPoolExecutor to run with timeout
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = loop.run_in_executor(executor, run_analysis_with_timeout)
            try:
                result = await asyncio.wait_for(future, timeout=MAX_TIMEOUT)
                
                # Check if result indicates failure
                if isinstance(result, dict) and result.get("success") is False:
                    error_msg = result.get("error", "Unknown error occurred during report generation")
                    ReportProgressTracker.fail(run_id, error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                return result
            except asyncio.TimeoutError:
                # Update status to error
                for f in files:
                    f.report_status = "error"
                db.commit()
                raise HTTPException(status_code=504, detail=f"Report generation timed out after {MAX_TIMEOUT} seconds. The dataset may be too large. Please try with smaller files or contact support.")
    except HTTPException:
        raise
    except Exception as e:
        # Update status to error for all files
        print(f"✗ Error in report generation for {run_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            for f in files:
                f.report_status = "error"
            db.commit()
        except Exception as db_error:
            print(f"✗ Error updating status: {str(db_error)}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

def perform_analysis_and_report_generation(files, db, run_id, regenerate, start_time):
    """Perform the actual analysis and report generation with optimizations"""
    try:
        print(f"\n{'='*60}")
        print(f"Starting report generation for {run_id}")
        print(f"Files: {len(files)}, Regenerate: {regenerate}")
        print(f"File details:")
        for f in files:
            print(f"  - {f.filename} (ID: {f.file_id}, Status: {f.report_status}, Category: {f.category})")
        print(f"{'='*60}\n")
        
        # Task 1: Parsing Files
        ReportProgressTracker.update_task(run_id, "parsing", "in_progress", 0, "Starting analysis and report generation...")
        
        # Group files by category
        files_by_category = {}
        for db_file in files:
            category = db_file.category
            if category not in files_by_category:
                files_by_category[category] = []
            files_by_category[category].append(db_file)
        
        # Analyze files - for JMeter, merge all files first then analyze once
        all_metrics = []
        total_records = 0
        # Note: start_time is passed as parameter, don't overwrite it
        
        for category, category_files in files_by_category.items():
            if category == "jmeter":
                # Check if files already point to a merged file (from upload-time merge)
                first_file_path = category_files[0].file_path
                # Only consider it merged if there are multiple files AND the path/filename indicates merged
                # Single files should NEVER be considered merged, even if path contains "merged"
                is_merged_file = len(category_files) > 1 and ("merged" in first_file_path.lower() or "merged" in category_files[0].filename.lower())
                merged_data = None  # Initialize for scope
                all_jmeter_data = []  # Initialize for scope
                
                # Handle both merged files and single files
                if is_merged_file and len(category_files) > 1:
                    # Files already merged at upload time - use the merged file directly
                    print(f"\n{'='*60}")
                    print(f"Using pre-merged file from Merged folder:")
                    print(f"  Path: {first_file_path}")
                    print(f"  File exists: {os.path.exists(first_file_path)}")
                    print(f"{'='*60}\n")
                    
                    merged_file_path = first_file_path
                    
                    if not os.path.exists(merged_file_path):
                        # Try to find the merged file in MERGED_DIR
                        merged_filename = f"{run_id}_merged.jtl"
                        alternative_path = MERGED_DIR / merged_filename
                        if os.path.exists(alternative_path):
                            print(f"  Found merged file at alternative location: {alternative_path}")
                            merged_file_path = str(alternative_path)
                            # Update file paths in database
                            for db_file in category_files:
                                db_file.file_path = merged_file_path
                            db.commit()
                        else:
                            raise HTTPException(status_code=404, detail=f"Merged file not found at {merged_file_path} or {alternative_path}")
                    
                    # Parse the merged file with progress tracking
                    ReportProgressTracker.update_task(run_id, "parsing", "in_progress", 30, f"Parsing merged file...")
                    file_size_mb = os.path.getsize(merged_file_path) / (1024 * 1024)
                    print(f"Parsing merged file: {Path(merged_file_path).name} ({file_size_mb:.1f} MB)...")
                    parse_start = time.time()
                    
                    if merged_file_path.endswith(".jtl") or merged_file_path.endswith(".csv"):
                        merged_data = JTLParserV2.parse(merged_file_path)
                    else:
                        merged_data = JSONParser.parse(merged_file_path, category)
                    
                    parse_duration = time.time() - parse_start
                    print(f"  ✓ Parsed {len(merged_data):,} records in {parse_duration:.1f}s ({len(merged_data)/parse_duration:,.0f} records/sec)")
                    ReportProgressTracker.update_task(run_id, "parsing", "completed", 100, f"Parsed {len(merged_data):,} records")
                    
                    # Analyze merged data with progress tracking
                    ReportProgressTracker.update_task(run_id, "analysis", "in_progress", 0, f"Analyzing {len(merged_data):,} records...")
                    print(f"Starting analysis of merged data ({len(merged_data):,} records)...")
                    analysis_start = time.time()
                    try:
                        metrics_obj = JMeterAnalyzerV2.analyze(merged_data)
                        metrics = metrics_obj.dict()
                        analysis_duration = time.time() - analysis_start
                        print(f"✓ Analysis complete in {analysis_duration:.1f}s. Total samples: {metrics.get('total_samples', 0):,}")
                        ReportProgressTracker.update_task(run_id, "analysis", "completed", 100, f"Analysis completed: {metrics.get('total_samples', 0):,} samples")
                    except Exception as e:
                        print(f"✗ Analysis failed: {str(e)}")
                        ReportProgressTracker.update_task(run_id, "analysis", "failed", 0, f"Analysis failed: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
                    
                    # Create file info from original filenames
                    file_info_list = []
                    for db_file in category_files:
                        # Extract original filename from the merged filename
                        original_filename = db_file.filename.replace("MERGED_", "").split("_", 1)[-1] if "MERGED_" in db_file.filename else db_file.filename
                        file_info_list.append({
                            "filename": original_filename,
                            "samples": db_file.record_count or 0,
                            "errors": 0,  # Will be calculated from merged data
                            "throughput": 0  # Will be calculated from merged data
                        })
                    
                    # Calculate errors and throughput from merged data
                    errors = sum(1 for d in merged_data if d.get("success") is False or 
                                 (d.get("response_code") and str(d.get("response_code")).startswith(("4", "5"))))
                    timestamps = [d.get("timestamp") for d in merged_data if d.get("timestamp")]
                    duration = (max(timestamps) - min(timestamps)) / 1000 if timestamps and len(timestamps) > 1 else 1
                    throughput = len(merged_data) / duration if duration > 0 else 0
                    
                    # Update file info with calculated values
                    for file_info in file_info_list:
                        file_info["errors"] = int(errors * (file_info["samples"] / len(merged_data))) if merged_data else 0
                        file_info["throughput"] = throughput * (file_info["samples"] / len(merged_data)) if merged_data else 0
                    
                    jmeter_filenames = [f["filename"] for f in file_info_list]
                
                elif len(category_files) == 1:
                    # USE CASE 1: Single file - process directly from original upload location
                    single_file = category_files[0]
                    single_file_path = single_file.file_path
                    print(f"\n{'='*60}")
                    print(f"USE CASE 1: Processing single JMeter file")
                    print(f"  File: {single_file.filename}")
                    print(f"  Path: {single_file_path}")
                    print(f"  File exists: {os.path.exists(single_file_path)}")
                    print(f"  Record count: {single_file.record_count or 'Not set'}")
                    print(f"{'='*60}\n")
                    
                    # Resolve file path - try multiple locations
                    if not os.path.exists(single_file_path):
                        print(f"  ⚠️  File not found at original path, searching...")
                        file_id = single_file.file_id
                        file_ext = Path(single_file.filename).suffix if single_file.filename else ".jtl"
                        
                        # Try multiple possible locations
                        alternative_paths = [
                            UPLOAD_DIR / f"{file_id}{file_ext}",
                            UPLOAD_DIR / f"{file_id}.jtl",
                            UPLOAD_DIR / f"{file_id}.csv",
                        ]
                        
                        # Also search by file_id pattern
                        if UPLOAD_DIR.exists():
                            matching_files = list(UPLOAD_DIR.glob(f"{file_id}*"))
                            if matching_files:
                                alternative_paths.extend([Path(f) for f in matching_files])
                        
                        resolved = False
                        for alt_path in alternative_paths:
                            if os.path.exists(alt_path):
                                print(f"  ✅ File found at: {alt_path}")
                                single_file_path = str(alt_path)
                                single_file.file_path = single_file_path
                                db.commit()
                                resolved = True
                                break
                        
                        if not resolved:
                            error_msg = f"File not found. Searched:\n  - {single_file_path}"
                            for alt in alternative_paths[:3]:
                                error_msg += f"\n  - {alt}"
                            raise HTTPException(status_code=404, detail=error_msg)
                    
                    # Parse the single file with progress tracking
                    ReportProgressTracker.update_task(run_id, "parsing", "in_progress", 30, f"Parsing file: {single_file.filename}...")
                    file_size_mb = os.path.getsize(single_file_path) / (1024 * 1024)
                    print(f"Parsing file: {Path(single_file_path).name} ({file_size_mb:.1f} MB)...")
                    parse_start = time.time()
                    
                    if single_file_path.endswith(".jtl") or single_file_path.endswith(".csv"):
                        merged_data = JTLParserV2.parse(single_file_path)
                    else:
                        merged_data = JSONParser.parse(single_file_path, category)
                    
                    parse_duration = time.time() - parse_start
                    print(f"  ✓ Parsed {len(merged_data):,} records in {parse_duration:.1f}s ({len(merged_data)/parse_duration:,.0f} records/sec)")
                    ReportProgressTracker.update_task(run_id, "parsing", "completed", 100, f"Parsed {len(merged_data):,} records")
                    
                    # Analyze single file data with progress tracking
                    ReportProgressTracker.update_task(run_id, "analysis", "in_progress", 0, f"Analyzing {len(merged_data):,} records...")
                    print(f"Starting analysis of data ({len(merged_data):,} records)...")
                    analysis_start = time.time()
                    try:
                        metrics_obj = JMeterAnalyzerV2.analyze(merged_data)
                        metrics = metrics_obj.dict()
                        analysis_duration = time.time() - analysis_start
                        print(f"✓ Analysis complete in {analysis_duration:.1f}s. Total samples: {metrics.get('total_samples', 0):,}")
                        ReportProgressTracker.update_task(run_id, "analysis", "completed", 100, f"Analysis completed: {metrics.get('total_samples', 0):,} samples")
                    except Exception as e:
                        print(f"✗ Analysis failed: {str(e)}")
                        ReportProgressTracker.update_task(run_id, "analysis", "failed", 0, f"Analysis failed: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
                    
                    # Create file info for single file
                    errors = sum(1 for d in merged_data if d.get("success") is False or 
                                 (d.get("response_code") and str(d.get("response_code")).startswith(("4", "5"))))
                    timestamps = [d.get("timestamp") for d in merged_data if d.get("timestamp")]
                    duration = (max(timestamps) - min(timestamps)) / 1000 if timestamps and len(timestamps) > 1 else 1
                    throughput = len(merged_data) / duration if duration > 0 else 0
                    
                    file_info_list = [{
                        "filename": single_file.filename,
                        "samples": len(merged_data),
                        "errors": errors,
                        "throughput": throughput
                    }]
                    
                    jmeter_filenames = [single_file.filename]
                    total_records = len(merged_data)
                    single_file.record_count = len(merged_data)
                    
                    # Add file information to summary
                    summary = metrics.get("summary", {})
                    summary["file_info"] = file_info_list
                    summary["file_count"] = len(category_files)
                    summary["consolidated_from_files"] = jmeter_filenames
                    metrics["summary"] = summary
                    print(f"✓ File information added to summary")
                    
                    # Store analysis for single file
                    print(f"Storing analysis results for single file...")
                    existing_analysis = DatabaseService.get_analysis_result(db, single_file.file_id)
                    if existing_analysis:
                        existing_analysis.metrics = metrics
                        existing_analysis.analyzed_at = datetime.utcnow()
                        existing_analysis.analysis_duration = time.time() - start_time
                    else:
                        DatabaseService.create_analysis_result(
                            db=db,
                            file_id=single_file.file_id,
                            category=category,
                            metrics=metrics,
                            analysis_duration=time.time() - start_time
                        )
                    db.commit()
                    print(f"✓ Analysis results stored successfully")
                    
                    # Add to all_metrics for report generation
                    all_metrics.append({
                        'file_id': single_file.file_id,
                        'filename': single_file.filename,
                        'category': category,
                        'metrics': metrics
                    })
                    print(f"✓ Added single file metrics to all_metrics")
                
                else:
                    # Multiple files not merged yet - merge them now (fallback for old data)
                    print(f"Merging {len(category_files)} JMeter file(s) for analysis...")
                    all_jmeter_data = []
                    jmeter_filenames = []
                    
                    # Parse all files and collect file info during parsing
                    file_info_list = []
                    for db_file in category_files:
                        file_path = db_file.file_path
                        print(f"Parsing {db_file.filename}...")
                        if file_path.endswith(".jtl") or file_path.endswith(".csv"):
                            data = JTLParserV2.parse(file_path)
                        else:
                            data = JSONParser.parse(file_path, category)
                        
                        all_jmeter_data.append(data)
                        jmeter_filenames.append(db_file.filename)
                        print(f"Parsed {len(data):,} records from {db_file.filename}")
                        
                        # Calculate file info during parsing to avoid second pass
                        errors = 0
                        timestamps = []
                        for d in data:
                            if d.get("success") is False or (d.get("response_code") and str(d.get("response_code")).startswith(("4", "5"))):
                                errors += 1
                            ts = d.get("timestamp")
                            if ts is not None:
                                timestamps.append(ts)
                        
                        duration = (max(timestamps) - min(timestamps)) / 1000 if timestamps and len(timestamps) > 1 else 1
                        throughput = len(data) / duration if duration > 0 else 0
                        
                        file_info_list.append({
                            "filename": db_file.filename,
                            "samples": len(data),
                            "errors": errors,
                            "throughput": throughput
                        })
                    
                    if all_jmeter_data:
                        # Merge all JTL data
                        print(f"Starting merge of {len(all_jmeter_data)} file(s)...")
                        merged_data = JTLParserV2.merge_data(all_jmeter_data)
                        print(f"✓ Merge complete: {len(merged_data):,} total records")
                        
                        # Analyze merged data once
                        print(f"Starting analysis of merged data ({len(merged_data):,} records)...")
                        try:
                            metrics_obj = JMeterAnalyzerV2.analyze(merged_data)
                            metrics = metrics_obj.dict()
                            print(f"✓ Analysis complete. Total samples: {metrics.get('total_samples', 0):,}")
                        except Exception as e:
                            print(f"✗ Analysis failed: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
                        
                        # Add file information to summary for fallback merge
                        summary = metrics.get("summary", {})
                        summary["file_info"] = file_info_list
                        summary["file_count"] = len(category_files)
                        summary["consolidated_from_files"] = jmeter_filenames
                        metrics["summary"] = summary
                        print(f"✓ File information added to summary")
                
                # Ensure summary is set (already done in both branches above, but ensure it's consistent)
                if "summary" not in metrics or "file_info" not in metrics.get("summary", {}):
                    summary = metrics.get("summary", {})
                    summary["file_info"] = file_info_list
                    summary["file_count"] = len(category_files)
                    summary["consolidated_from_files"] = jmeter_filenames
                    metrics["summary"] = summary
                
                # Store analysis for each file (same metrics for all files in the run)
                print(f"Storing analysis results for {len(category_files)} file(s)...")
                
                # For merged files, count records only once
                if is_merged_file and merged_data:
                    # All files point to the same merged file - count only once
                    total_records = len(merged_data)
                    # Update all files' record_count to the merged count
                    for db_file in category_files:
                        db_file.record_count = len(merged_data)
                    print(f"  Updated record_count for {len(category_files)} files to {len(merged_data):,} (merged file)")
                else:
                    # For non-merged files, calculate from individual files
                    for idx, db_file in enumerate(category_files, 1):
                        file_idx = jmeter_filenames.index(db_file.filename) if db_file.filename in jmeter_filenames else 0
                        if file_idx < len(all_jmeter_data):
                            db_file.record_count = len(all_jmeter_data[file_idx])
                            total_records += len(all_jmeter_data[file_idx])
                
                for idx, db_file in enumerate(category_files, 1):
                    print(f"  Storing analysis {idx}/{len(category_files)}: {db_file.filename}")
                    
                    existing_analysis = DatabaseService.get_analysis_result(db, db_file.file_id)
                    if existing_analysis:
                        existing_analysis.metrics = metrics
                        existing_analysis.analyzed_at = datetime.utcnow()
                        existing_analysis.analysis_duration = time.time() - start_time
                    else:
                        DatabaseService.create_analysis_result(
                            db=db,
                            file_id=db_file.file_id,
                            category=category,
                            metrics=metrics,
                            analysis_duration=time.time() - start_time
                        )
                
                # Commit once after all files are processed
                db.commit()
                print(f"✓ Analysis results stored successfully")
                
                all_metrics.append({
                    'file_id': category_files[0].file_id,
                    'filename': f"Merged: {', '.join(jmeter_filenames)}",
                    'category': category,
                    'metrics': metrics
                })
            
            else:
                # For other categories, analyze individually
                for db_file in category_files:
                    existing_analysis = DatabaseService.get_analysis_result(db, db_file.file_id)
                    
                    if existing_analysis and not regenerate:
                        print(f"Reusing existing analysis for {db_file.filename}")
                        metrics = existing_analysis.metrics
                        record_count = db_file.record_count or 0
                    else:
                        print(f"Analyzing {db_file.filename}...")
                        file_path = db_file.file_path
                        
                        if category == "web_vitals":
                            if file_path.endswith(".json"):
                                data = JSONParser.parse(file_path, category)
                            else:
                                data = CSVParser.parse(file_path, category)
                            metrics_obj = WebVitalsAnalyzer.analyze(data)
                            metrics = metrics_obj.dict()
                        elif category == "ui_performance":
                            if file_path.endswith(".json"):
                                data = JSONParser.parse(file_path, category)
                            else:
                                data = CSVParser.parse(file_path, category)
                            metrics_obj = UIPerformanceAnalyzer.analyze(data)
                            metrics = metrics_obj.dict()
                        else:
                            continue
                        
                        record_count = len(data) if isinstance(data, list) else 1
                        db_file.record_count = record_count
                        
                        if existing_analysis:
                            existing_analysis.metrics = metrics
                            existing_analysis.analyzed_at = datetime.utcnow()
                            existing_analysis.analysis_duration = time.time() - start_time
                            db.commit()
                        else:
                            DatabaseService.create_analysis_result(
                                db=db,
                                file_id=db_file.file_id,
                                category=category,
                                metrics=metrics,
                                analysis_duration=time.time() - start_time
                            )
                    
                    total_records += record_count
                    
                    all_metrics.append({
                        'file_id': db_file.file_id,
                        'filename': db_file.filename,
                        'category': category,
                        'metrics': metrics
                    })
        
        analysis_duration = time.time() - start_time
        print(f"\n✓ Analysis phase completed in {analysis_duration:.1f}s")
        print(f"Total records processed: {total_records:,}")
        
        # Update status to generating
        if not regenerate:
            for f in files:
                f.report_status = "generating"
            db.commit()
        
        report_gen_start = time.time()
        print(f"\n{'='*60}")
        print(f"Starting report generation for {run_id}...")
        print(f"Analysis completed in {analysis_duration:.1f}s")
        print(f"{'='*60}\n")
        
        # Generate consolidated report (use first file's category for report type)
        # For mixed categories, prioritize jmeter > ui_performance > web_vitals
        if not all_metrics:
            print(f"❌ ERROR: all_metrics is empty! Cannot generate reports.")
            print(f"   Files processed: {len(files)}")
            print(f"   Categories: {[f.category for f in files]}")
            raise HTTPException(status_code=500, detail="No metrics available for report generation. Analysis may have failed.")
        
        categories = [m['category'] for m in all_metrics]
        print(f"Available categories in all_metrics: {categories}")
        print(f"Total metrics in all_metrics: {len(all_metrics)}")
        
        if 'jmeter' in categories:
            primary_category = 'jmeter'
            # For JMeter, we already merged and analyzed, so use the first (and only) metrics
            primary_metrics = next((m['metrics'] for m in all_metrics if m['category'] == 'jmeter'), None)
        elif 'ui_performance' in categories:
            primary_category = 'ui_performance'
            primary_metrics = next((m['metrics'] for m in all_metrics if m['category'] == 'ui_performance'), None)
        else:
            primary_category = 'web_vitals'
            primary_metrics = next((m['metrics'] for m in all_metrics if m['category'] == 'web_vitals'), None)
        
        if not primary_metrics:
            print(f"❌ ERROR: primary_metrics is None!")
            print(f"   all_metrics: {[m.get('category') for m in all_metrics]}")
            raise HTTPException(status_code=400, detail="No valid metrics found for report generation. Please check analysis results.")
        
        print(f"✓ Using primary_category: {primary_category}, metrics keys: {list(primary_metrics.keys())[:5]}...")
        
        # Use the first file for report generation
        primary_file = files[0]
        
        # Delete existing reports if regenerating
        if regenerate:
            existing_reports = DatabaseService.get_reports_by_file(db, primary_file.file_id)
            for report in existing_reports:
                if report.report_path and os.path.exists(report.report_path):
                    try:
                        os.remove(report.report_path)
                    except Exception as e:
                        print(f"Error deleting old report: {e}")
                db.delete(report)
            db.commit()
            print(f"Deleted {len(existing_reports)} old reports")
        
        # Generate reports based on primary category
        ReportProgressTracker.update_task(run_id, "html_generation", "in_progress", 0, "Generating HTML report...")
        print(f"Generating HTML report...")
        print(f"  Primary category: {primary_category}")
        print(f"  Metrics keys: {list(primary_metrics.keys())[:10]}...")
        print(f"  Total samples: {primary_metrics.get('total_samples', 'N/A')}")
        
        html_start_time = time.time()
        try:
            if primary_category == "jmeter":
                print(f"  Calling HTMLReportGenerator.generate_jmeter_html_report()...")
                
                # Progress callback for HTML generation
                def update_html_progress(percent: int, message: str):
                    ReportProgressTracker.update_task(run_id, "html_generation", "in_progress", 10 + int(percent * 0.8), message)
                    print(f"  HTML Progress: {percent}% - {message}")
                
                html_content = HTMLReportGenerator.generate_jmeter_html_report(
                    primary_metrics,
                    progress_callback=update_html_progress
                )
                html_duration = time.time() - html_start_time
                print(f"✓ HTML report generated in {html_duration:.1f}s ({len(html_content):,} characters)")
            elif primary_category == "web_vitals":
                html_content = HTMLReportGenerator.generate_web_vitals_html_report(primary_metrics, primary_file.filename)
            else:
                html_content = HTMLReportGenerator.generate_ui_performance_html_report(primary_metrics, primary_file.filename)
            
            ReportProgressTracker.update_task(run_id, "html_generation", "completed", 100, f"HTML report generated ({len(html_content):,} chars)")
        except Exception as e:
            html_duration = time.time() - html_start_time
            print(f"✗ HTML report generation failed after {html_duration:.1f}s: {str(e)}")
            ReportProgressTracker.update_task(run_id, "html_generation", "failed", 0, f"HTML generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"HTML report generation failed: {str(e)}")
        
        ReportProgressTracker.update_task(run_id, "pdf_generation", "in_progress", 0, "Generating PDF report...")
        print(f"Generating PDF report...")
        try:
            if primary_category == "jmeter":
                pdf_bytes = PDFReportGenerator.generate_jmeter_pdf_report(primary_metrics)
            elif primary_category == "web_vitals":
                pdf_bytes = PDFReportGenerator.generate_web_vitals_pdf_report(primary_metrics, primary_file.filename)
            else:
                pdf_bytes = PDFReportGenerator.generate_ui_performance_pdf_report(primary_metrics, primary_file.filename)
            print(f"✓ PDF report generated ({len(pdf_bytes):,} bytes)")
            ReportProgressTracker.update_task(run_id, "pdf_generation", "completed", 100, f"PDF report generated ({len(pdf_bytes):,} bytes)")
        except Exception as e:
            print(f"✗ PDF report generation failed: {str(e)}")
            ReportProgressTracker.update_task(run_id, "pdf_generation", "failed", 0, f"PDF generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"PDF report generation failed: {str(e)}")
        
        ReportProgressTracker.update_task(run_id, "ppt_generation", "in_progress", 0, "Generating PPT report...")
        print(f"Generating PPT report...")
        try:
            if primary_category == "jmeter":
                ppt_bytes = PPTReportGenerator.generate_jmeter_ppt_report(primary_metrics)
            elif primary_category == "web_vitals":
                ppt_bytes = PPTReportGenerator.generate_web_vitals_ppt_report(primary_metrics, primary_file.filename)
            else:
                ppt_bytes = PPTReportGenerator.generate_ui_performance_ppt_report(primary_metrics, primary_file.filename)
            print(f"✓ PPT report generated ({len(ppt_bytes):,} bytes)")
            ReportProgressTracker.update_task(run_id, "ppt_generation", "completed", 100, f"PPT report generated ({len(ppt_bytes):,} bytes)")
        except Exception as e:
            print(f"✗ PPT report generation failed: {str(e)}")
            ReportProgressTracker.update_task(run_id, "ppt_generation", "failed", 0, f"PPT generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"PPT report generation failed: {str(e)}")
        
        print(f"Saving reports to database...")
        
        # Ensure reports directory exists
        REPORTS_DIR.mkdir(exist_ok=True)
        
        # Save reports (associate with first file in run)
        html_path = REPORTS_DIR / f"{run_id}_report.html"
        print(f"Saving HTML report to: {html_path}")
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            html_size = len(html_content.encode('utf-8'))
            print(f"  ✓ HTML report saved ({html_size:,} bytes)")
            
            DatabaseService.create_generated_report(
                db=db,
                file_id=primary_file.file_id,
                report_type="html",
                report_path=str(html_path),
                report_content=html_content,
                file_size=html_size,
                generated_by="raghskmr"
            )
            db.commit()
            print(f"  ✓ HTML report saved to database")
        except Exception as e:
            print(f"  ✗ Error saving HTML report: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        pdf_path = REPORTS_DIR / f"{run_id}_report.pdf"
        print(f"Saving PDF report to: {pdf_path}")
        try:
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            pdf_size = len(pdf_bytes)
            print(f"  ✓ PDF report saved ({pdf_size:,} bytes)")
            
            DatabaseService.create_generated_report(
                db=db,
                file_id=primary_file.file_id,
                report_type="pdf",
                report_path=str(pdf_path),
                file_size=pdf_size,
                generated_by="raghskmr"
            )
            db.commit()
            print(f"  ✓ PDF report saved to database")
        except Exception as e:
            print(f"  ✗ Error saving PDF report: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        ppt_path = REPORTS_DIR / f"{run_id}_report.pptx"
        print(f"Saving PPT report to: {ppt_path}")
        try:
            with open(ppt_path, "wb") as f:
                f.write(ppt_bytes)
            ppt_size = len(ppt_bytes)
            print(f"  ✓ PPT report saved ({ppt_size:,} bytes)")
            
            DatabaseService.create_generated_report(
                db=db,
                file_id=primary_file.file_id,
                report_type="ppt",
                report_path=str(ppt_path),
                file_size=ppt_size,
                generated_by="raghskmr"
            )
            db.commit()
            print(f"  ✓ PPT report saved to database")
        except Exception as e:
            print(f"  ✗ Error saving PPT report: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        print(f"✓ All reports saved successfully")
        
        # Validate all tasks are completed before marking as done
        progress = ReportProgressTracker.get_progress(run_id)
        if progress:
            all_tasks = progress.get("tasks", {})
            critical_tasks = ["parsing", "analysis", "html_generation"]
            all_critical_completed = all(
                all_tasks.get(task_id, {}).get("status") == "completed" 
                for task_id in critical_tasks 
                if task_id in all_tasks
            )
            
            if not all_critical_completed:
                incomplete = [task_id for task_id in critical_tasks 
                             if all_tasks.get(task_id, {}).get("status") != "completed"]
                print(f"⚠️  Warning: Critical tasks not completed: {incomplete}")
                print(f"   Task statuses: {[(tid, all_tasks.get(tid, {}).get('status')) for tid in critical_tasks]}")
            else:
                print(f"✓ All critical tasks completed successfully")
        
        # Verify reports were actually saved before marking as complete
        saved_reports = DatabaseService.get_reports_by_file(db, primary_file.file_id)
        print(f"\n{'='*60}")
        print(f"Verifying saved reports for {run_id}:")
        print(f"  Reports found in database: {len(saved_reports)}")
        for saved_report in saved_reports:
            exists = os.path.exists(saved_report.report_path) if saved_report.report_path else False
            status_icon = "✓" if exists else "✗"
            print(f"    {status_icon} {saved_report.report_type.upper()}: {saved_report.report_path} (exists: {exists})")
        print(f"{'='*60}\n")
        
        if len(saved_reports) == 0:
            error_msg = "Report generation completed but no reports were saved to database. Please check server logs."
            print(f"\n✗ {error_msg}")
            ReportProgressTracker.fail(run_id, error_msg)
            for f in files:
                f.report_status = "error"
            db.commit()
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Check if all critical reports exist
        critical_reports = ["html"]
        missing_reports = [rt for rt in critical_reports 
                          if not any(r.report_type == rt and os.path.exists(r.report_path) 
                                    for r in saved_reports if r.report_path)]
        if missing_reports:
            error_msg = f"Critical reports missing: {', '.join(missing_reports)}"
            print(f"\n✗ {error_msg}")
            ReportProgressTracker.fail(run_id, error_msg)
            for f in files:
                f.report_status = "error"
            db.commit()
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Mark progress as completed (will validate internally)
        ReportProgressTracker.complete(run_id, "All reports generated successfully!")
        
        # Double-check completion status
        final_progress = ReportProgressTracker.get_progress(run_id)
        if final_progress and final_progress.get("status") != "completed":
            print(f"⚠️  Report generation not marked as completed. Status: {final_progress.get('status')}")
            print(f"   Message: {final_progress.get('message')}")
            # Force completion since reports are saved
            ReportProgressTracker.complete(run_id, "All reports generated and verified successfully!")
        
        # Update status to generated for all files
        for f in files:
            f.report_status = "generated"
        db.commit()
        print(f"✓ File statuses updated to 'generated'")
        
        total_duration = time.time() - start_time
        report_gen_duration = time.time() - report_gen_start
        
        print(f"\n{'='*60}")
        print(f"✓ Report generation completed successfully!")
        print(f"  Analysis: {analysis_duration:.1f}s")
        print(f"  Report Generation: {report_gen_duration:.1f}s")
        print(f"  Total Duration: {total_duration:.1f}s")
        print(f"  Total Records: {total_records:,}")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "run_id": run_id,
            "file_count": len(files),
            "total_records": total_records,
            "analysis_duration": analysis_duration,
            "report_generation_duration": report_gen_duration,
            "total_duration": total_duration,
            "report_urls": {
                "html": f"/api/runs/{run_id}/reports/html",
                "pdf": f"/api/runs/{run_id}/reports/pdf",
                "ppt": f"/api/runs/{run_id}/reports/ppt"
            }
        }
        
    except Exception as e:
        # Update status to error for all files
        ReportProgressTracker.fail(run_id, str(e))
        print(f"✗ Error in report generation for {run_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            for f in files:
                f.report_status = "error"
            db.commit()
        except Exception as db_error:
            print(f"✗ Error updating status: {str(db_error)}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@router.get("/runs/{run_id}/reports/{report_type}")
async def get_run_report(run_id: str, report_type: str, db: Session = Depends(get_db)):
    """Get report for a run"""
    files = DatabaseService.get_files_by_run_id(db, run_id)
    if not files:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get report from first file (reports are stored with first file)
    primary_file = files[0]
    reports = DatabaseService.get_reports_by_file(db, primary_file.file_id)
    
    report = next((r for r in reports if r.report_type == report_type), None)
    if not report:
        raise HTTPException(status_code=404, detail=f"{report_type.upper()} report not found")
    
    if report_type == "html":
        if report.report_content:
            return HTMLResponse(content=report.report_content)
        elif report.report_path and os.path.exists(report.report_path):
            with open(report.report_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    elif report_type == "pdf":
        if report.report_path and os.path.exists(report.report_path):
            with open(report.report_path, "rb") as f:
                return Response(
                    content=f.read(),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={run_id}_report.pdf"}
                )
    elif report_type == "ppt":
        if report.report_path and os.path.exists(report.report_path):
            with open(report.report_path, "rb") as f:
                return Response(
                    content=f.read(),
                    media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    headers={"Content-Disposition": f"attachment; filename={run_id}_report.pptx"}
                )
    
    raise HTTPException(status_code=404, detail="Report content not found")

@router.delete("/files/{file_id}")
async def delete_file(file_id: str, db: Session = Depends(get_db)):
    """Delete an uploaded file and all related data"""
    db_file = DatabaseService.get_uploaded_file(db, file_id)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete physical file
    try:
        if os.path.exists(db_file.file_path):
            os.remove(db_file.file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    # Delete from database (cascades to analysis and reports)
    DatabaseService.delete_uploaded_file(db, file_id)
    
    return {"message": "File deleted successfully"}

@router.post("/analyze")
async def analyze_files(file_ids: List[str], db: Session = Depends(get_db)):
    """
    Analyze selected files
    """
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    
    results = {}
    
    for file_id in file_ids:
        db_file = DatabaseService.get_uploaded_file(db, file_id)
        if not db_file:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")
        
        # Check if analysis already exists
        existing_analysis = DatabaseService.get_analysis_result(db, file_id)
        if existing_analysis:
            results[file_id] = {
                "category": existing_analysis.category,
                "filename": db_file.filename,
                "metrics": existing_analysis.metrics,
                "from_cache": True
            }
            continue
        
        file_path = db_file.file_path
        category = db_file.category
        
        start_time = time.time()
        
        # Parse file based on category and extension
        if category == "web_vitals":
            if file_path.endswith(".json"):
                data = JSONParser.parse(file_path, category)
            else:
                data = CSVParser.parse(file_path, category)
            metrics_obj = WebVitalsAnalyzer.analyze(data)
            metrics = metrics_obj.dict()
        elif category == "jmeter":
            if file_path.endswith(".jtl") or file_path.endswith(".csv"):
                data = JTLParserV2.parse(file_path)
            else:
                data = JSONParser.parse(file_path, category)
            metrics_obj = JMeterAnalyzerV2.analyze(data)
            metrics = metrics_obj.dict()
        elif category == "ui_performance":
            if file_path.endswith(".json"):
                data = JSONParser.parse(file_path, category)
            else:
                data = CSVParser.parse(file_path, category)
            metrics_obj = UIPerformanceAnalyzer.analyze(data)
            metrics = metrics_obj.dict()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")
        
        analysis_duration = time.time() - start_time
        
        # Store analysis in database
        db_analysis = DatabaseService.create_analysis_result(
            db=db,
            file_id=file_id,
            category=category,
            metrics=metrics,
            analysis_duration=analysis_duration
        )
        
        results[file_id] = {
            "category": category,
            "filename": db_file.filename,
            "metrics": metrics,
            "from_cache": False
        }
    
    return {"results": results}

@router.get("/analyzed-files")
async def get_analyzed_files(db: Session = Depends(get_db)):
    """Get all files that have been analyzed"""
    analyses = DatabaseService.get_all_analysis_results(db)
    return {"analyses": [a.to_dict() for a in analyses]}

@router.post("/report/generate")
async def generate_report(request_body: dict, db: Session = Depends(get_db)):
    """
    Generate comprehensive JSON report from analyzed files
    Accepts either file_ids or analysis_data directly
    """
    # Support both old format (list) and new format (dict with analysis_data)
    if isinstance(request_body, list):
        file_ids = request_body
        analysis_data = None
    else:
        file_ids = request_body.get("file_ids", [])
        analysis_data = request_body.get("analysis_data", {})
    
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    
    web_vitals_results = None
    jmeter_results = None
    ui_performance_results = None
    
    # Aggregate results by category
    for file_id in file_ids:
        # Try to get from provided analysis_data first, then from database
        if analysis_data and file_id in analysis_data:
            result = analysis_data[file_id]
        else:
            db_analysis = DatabaseService.get_analysis_result(db, file_id)
            if not db_analysis:
                raise HTTPException(status_code=404, detail=f"Analysis results for {file_id} not found. Please re-analyze the file.")
            result = {
                "category": db_analysis.category,
                "metrics": db_analysis.metrics
            }
        
        category = result.get("category")
        
        if category == "web_vitals":
            if web_vitals_results is None:
                web_vitals_results = result.get("metrics")
        elif category == "jmeter":
            if jmeter_results is None:
                jmeter_results = result.get("metrics")
        elif category == "ui_performance":
            if ui_performance_results is None:
                ui_performance_results = result.get("metrics")
    
    # Generate comprehensive report
    report = ReportBuilder.generate_comprehensive_report(
        web_vitals_results=web_vitals_results,
        jmeter_results=jmeter_results,
        ui_performance_results=ui_performance_results
    )
    
    # Save report to database
    for file_id in file_ids:
        try:
            DatabaseService.create_generated_report(
                db=db,
                file_id=file_id,
                report_type="json",
                report_content=json.dumps(report),
                generated_by="current_user",
                file_size=len(json.dumps(report))
            )
        except Exception as e:
            print(f"Error saving report for {file_id}: {e}")
    
    return report

@router.post("/report/generate-html")
async def generate_html_report(request_body: dict, db: Session = Depends(get_db)):
    """
    Generate HTML report from analyzed files
    Accepts either file_ids or analysis_data directly
    """
    # Support both old format (list) and new format (dict with analysis_data)
    if isinstance(request_body, list):
        file_ids = request_body
        analysis_data = None
    else:
        file_ids = request_body.get("file_ids", [])
        analysis_data = request_body.get("analysis_data", {})
    
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    
    jmeter_results = None
    
    # Get JMeter results (prioritize JMeter for HTML reports)
    for file_id in file_ids:
        # Try to get from provided analysis_data first, then from database
        if analysis_data and file_id in analysis_data:
            result = analysis_data[file_id]
        else:
            db_analysis = DatabaseService.get_analysis_result(db, file_id)
            if not db_analysis:
                raise HTTPException(status_code=404, detail=f"Analysis results for {file_id} not found. Please re-analyze the file.")
            result = {
                "category": db_analysis.category,
                "metrics": db_analysis.metrics
            }
        
        category = result.get("category")
        
        if category == "jmeter":
            jmeter_results = result.get("metrics")
            break
    
    if not jmeter_results:
        raise HTTPException(status_code=400, detail="No JMeter results found. HTML reports are currently only available for JMeter data.")
    
    # Generate HTML report
    html_content = HTMLReportGenerator.generate_jmeter_html_report(jmeter_results)
    
    # Save report to database
    for file_id in file_ids:
        try:
            DatabaseService.create_generated_report(
                db=db,
                file_id=file_id,
                report_type="html",
                report_content=html_content,
                generated_by="current_user",
                file_size=len(html_content)
            )
        except Exception as e:
            print(f"Error saving HTML report for {file_id}: {e}")
    
    return HTMLResponse(content=html_content, status_code=200)

@router.post("/report/generate-pdf")
async def generate_pdf_report(request_body: dict, db: Session = Depends(get_db)):
    """Generate PDF report from analyzed files"""
    file_ids = request_body.get("file_ids", [])
    analysis_data = request_body.get("analysis_data", {})
    
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    
    # Get JMeter results
    jmeter_results = None
    for file_id in file_ids:
        if analysis_data and file_id in analysis_data:
            result = analysis_data[file_id]
        else:
            db_analysis = DatabaseService.get_analysis_result(db, file_id)
            if not db_analysis:
                continue
            result = {"category": db_analysis.category, "metrics": db_analysis.metrics}
        
        if result.get("category") == "jmeter":
            jmeter_results = result.get("metrics")
            break
    
    if not jmeter_results:
        raise HTTPException(status_code=400, detail="No JMeter results found.")
    
    # Generate PDF
    pdf_bytes = PDFReportGenerator.generate_jmeter_pdf_report(jmeter_results)
    
    # Save to database
    for file_id in file_ids:
        try:
            DatabaseService.create_generated_report(
                db=db,
                file_id=file_id,
                report_type="pdf",
                generated_by="current_user",
                file_size=len(pdf_bytes)
            )
        except Exception as e:
            print(f"Error saving PDF report: {e}")
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=performance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        }
    )

@router.post("/report/generate-ppt")
async def generate_ppt_report(request_body: dict, db: Session = Depends(get_db)):
    """Generate PowerPoint report from analyzed files"""
    file_ids = request_body.get("file_ids", [])
    analysis_data = request_body.get("analysis_data", {})
    
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    
    # Get JMeter results
    jmeter_results = None
    for file_id in file_ids:
        if analysis_data and file_id in analysis_data:
            result = analysis_data[file_id]
        else:
            db_analysis = DatabaseService.get_analysis_result(db, file_id)
            if not db_analysis:
                continue
            result = {"category": db_analysis.category, "metrics": db_analysis.metrics}
        
        if result.get("category") == "jmeter":
            jmeter_results = result.get("metrics")
            break
    
    if not jmeter_results:
        raise HTTPException(status_code=400, detail="No JMeter results found.")
    
    # Generate PPT
    ppt_bytes = PPTReportGenerator.generate_jmeter_ppt_report(jmeter_results)
    
    # Save to database
    for file_id in file_ids:
        try:
            DatabaseService.create_generated_report(
                db=db,
                file_id=file_id,
                report_type="ppt",
                generated_by="current_user",
                file_size=len(ppt_bytes)
            )
        except Exception as e:
            print(f"Error saving PPT report: {e}")
    
    return Response(
        content=ppt_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f"attachment; filename=performance_report_{datetime.now().strftime('%Y%m%d')}.pptx"
        }
    )

@router.get("/reports")
async def list_reports(db: Session = Depends(get_db)):
    """Get all generated reports with file information"""
    reports = DatabaseService.get_all_reports(db)
    
    # Enrich with file information
    report_list = []
    for report in reports:
        db_file = DatabaseService.get_uploaded_file(db, report.file_id)
        report_dict = report.to_dict()
        if db_file:
            report_dict["filename"] = db_file.filename
            report_dict["category"] = db_file.category
        report_list.append(report_dict)
    
    return {"reports": report_list}

@router.get("/reports/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    """Get a specific report by ID"""
    report = DatabaseService.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.report_type == "html":
        return HTMLResponse(content=report.report_content)
    else:
        return JSONResponse(content=json.loads(report.report_content) if report.report_content else {})

@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, db: Session = Depends(get_db)):
    """Delete a generated report"""
    success = DatabaseService.delete_report(db, report_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {"message": "Report deleted successfully"}

@router.get("/chat/sample-prompts")
async def get_sample_prompts():
    """Get sample prompts organized by category"""
    return {
        "all_prompts": PerformanceChatbot.get_sample_prompts(),
        "suggested_prompts": PerformanceChatbot.get_random_prompts(8)
    }

@router.post("/chat")
async def chat_with_ai(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Enhanced AI chatbot endpoint for querying performance reports
    Request body: {
        "message": "user question",
        "session_id": "optional session id",
        "file_ids": ["optional list of file ids for context"]
    }
    """
    message = request.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    session_id = request.get("session_id", str(uuid.uuid4()))
    file_ids = request.get("file_ids", [])
    
    # Get context from analyses
    context_data = []
    for file_id in file_ids:
        analysis = DatabaseService.get_analysis_result(db, file_id)
        if analysis:
            context_data.append({
                "file_id": file_id,
                "filename": analysis.file.filename if analysis.file else "Unknown",
                "category": analysis.category,
                "metrics": analysis.metrics
            })
    
    # Generate AI response using enhanced chatbot engine
    response = PerformanceChatbot.generate_response(message, context_data)
    
    # Save to chat history
    try:
        DatabaseService.save_chat_message(
            db=db,
            session_id=session_id,
            user_id="current_user",  # TODO: Get from auth context
            message=message,
            response=response,
            context_file_ids=file_ids
        )
    except Exception as e:
        print(f"Error saving chat history: {e}")
    
    return {
        "session_id": session_id,
        "message": message,
        "response": response,
        "context_files": len(context_data),
        "intent": PerformanceChatbot.analyze_query_intent(message)
    }

@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    """Get chat history for a session"""
    history = DatabaseService.get_chat_history(db, session_id)
    return {"history": [h.to_dict() for h in history]}

# The generate_ai_response function has been replaced by PerformanceChatbot.generate_response
# Remove the old implementation
