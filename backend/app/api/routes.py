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

from app.parsers.json_parser import JSONParser
from app.parsers.csv_parser import CSVParser
from app.parsers.jtl_parser import JTLParser
from app.analyzers.web_vitals_analyzer import WebVitalsAnalyzer
from app.analyzers.jmeter_analyzer import JMeterAnalyzer
from app.analyzers.ui_performance_analyzer import UIPerformanceAnalyzer
from app.report_generator.report_builder import ReportBuilder
from app.report_generator.html_report_generator import HTMLReportGenerator
from app.report_generator.pdf_generator import PDFReportGenerator
from app.report_generator.ppt_generator import PPTReportGenerator
from app.database import get_db
from app.database.service import DatabaseService
from app.database.models import UploadedFile, AnalysisResult, GeneratedReport
from app.ai.chatbot_engine import PerformanceChatbot

router = APIRouter()

# Create uploads and reports directories
UPLOAD_DIR = Path("uploads")
REPORTS_DIR = Path("reports")
UPLOAD_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

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
                data = JTLParser.parse(file_path)
            else:
                data = JSONParser.parse(file_path, category)
            metrics_obj = JMeterAnalyzer.analyze(data)
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
        
        uploaded_files.append(db_file.to_dict())
    
    return {"message": "Files uploaded successfully", "run_id": run_id, "files": uploaded_files}

@router.get("/files")
async def list_files(db: Session = Depends(get_db)):
    """List all uploaded files"""
    files = DatabaseService.get_all_uploaded_files(db)
    return {"files": [f.to_dict() for f in files]}

@router.get("/runs")
async def list_runs(db: Session = Depends(get_db)):
    """List all runs (grouped by upload batch)"""
    try:
        import time
        start_time = time.time()
        runs = DatabaseService.get_all_run_ids(db)
        elapsed = time.time() - start_time
        print(f"get_all_run_ids took {elapsed:.2f} seconds, returned {len(runs)} runs")
        return {"runs": runs}
    except Exception as e:
        print(f"Error in list_runs: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading runs: {str(e)}")

@router.get("/runs/{run_id}")
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

@router.post("/runs/{run_id}/generate-report")
async def generate_run_report(run_id: str, db: Session = Depends(get_db), regenerate: bool = Query(False, description="Regenerate reports from existing analysis")):
    """
    Generate consolidated report for a run (all files in the run)
    Analyzes all files and creates a single combined report
    If regenerate=True, regenerates reports from existing analysis
    """
    files = DatabaseService.get_files_by_run_id(db, run_id)
    if not files:
        raise HTTPException(status_code=404, detail="Run not found")
    
    try:
        # Update status for all files
        for f in files:
            f.report_status = "analyzing" if not regenerate else "generating"
        db.commit()
        
        # Analyze all files and collect metrics
        all_metrics = []
        total_records = 0
        start_time = time.time()
        
        for db_file in files:
            # Check if analysis already exists
            existing_analysis = DatabaseService.get_analysis_result(db, db_file.file_id)
            
            if existing_analysis and not regenerate:
                # Reuse existing analysis
                print(f"Reusing existing analysis for {db_file.filename}")
                metrics = existing_analysis.metrics
                record_count = db_file.record_count or 0
            else:
                # Perform new analysis
                print(f"Analyzing {db_file.filename}...")
                file_path = db_file.file_path
                category = db_file.category
                
                # Parse and analyze each file
                if category == "web_vitals":
                    if file_path.endswith(".json"):
                        data = JSONParser.parse(file_path, category)
                    else:
                        data = CSVParser.parse(file_path, category)
                    metrics_obj = WebVitalsAnalyzer.analyze(data)
                    metrics = metrics_obj.dict()
                elif category == "jmeter":
                    if file_path.endswith(".jtl") or file_path.endswith(".csv"):
                        data = JTLParser.parse(file_path)
                    else:
                        data = JSONParser.parse(file_path, category)
                    print(f"Parsed {len(data)} records, starting analysis...")
                    metrics_obj = JMeterAnalyzer.analyze(data)
                    metrics = metrics_obj.dict()
                    print(f"Analysis complete for {db_file.filename}")
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
                
                # Store or update analysis
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
                'category': db_file.category,
                'metrics': metrics
            })
        
        analysis_duration = time.time() - start_time
        
        # Update status to generating
        if not regenerate:
            for f in files:
                f.report_status = "generating"
            db.commit()
        
        print(f"Generating reports for {run_id}...")
        
        # Generate consolidated report (use first file's category for report type)
        # For mixed categories, prioritize jmeter > ui_performance > web_vitals
        categories = [m['category'] for m in all_metrics]
        if 'jmeter' in categories:
            primary_category = 'jmeter'
            primary_metrics = next(m['metrics'] for m in all_metrics if m['category'] == 'jmeter')
        elif 'ui_performance' in categories:
            primary_category = 'ui_performance'
            primary_metrics = next(m['metrics'] for m in all_metrics if m['category'] == 'ui_performance')
        else:
            primary_category = 'web_vitals'
            primary_metrics = next(m['metrics'] for m in all_metrics if m['category'] == 'web_vitals')
        
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
        print(f"Generating HTML report...")
        if primary_category == "jmeter":
            html_content = HTMLReportGenerator.generate_jmeter_html_report(primary_metrics)
        elif primary_category == "web_vitals":
            html_content = HTMLReportGenerator.generate_web_vitals_html_report(primary_metrics, primary_file.filename)
        else:
            html_content = HTMLReportGenerator.generate_ui_performance_html_report(primary_metrics, primary_file.filename)
        
        print(f"Generating PDF report...")
        if primary_category == "jmeter":
            pdf_bytes = PDFReportGenerator.generate_jmeter_pdf_report(primary_metrics)
        elif primary_category == "web_vitals":
            pdf_bytes = PDFReportGenerator.generate_web_vitals_pdf_report(primary_metrics, primary_file.filename)
        else:
            pdf_bytes = PDFReportGenerator.generate_ui_performance_pdf_report(primary_metrics, primary_file.filename)
        
        print(f"Generating PPT report...")
        if primary_category == "jmeter":
            ppt_bytes = PPTReportGenerator.generate_jmeter_ppt_report(primary_metrics)
        elif primary_category == "web_vitals":
            ppt_bytes = PPTReportGenerator.generate_web_vitals_ppt_report(primary_metrics, primary_file.filename)
        else:
            ppt_bytes = PPTReportGenerator.generate_ui_performance_ppt_report(primary_metrics, primary_file.filename)
        
        print(f"Saving reports to database...")
        
        # Save reports (associate with first file in run)
        html_path = REPORTS_DIR / f"{run_id}_report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        DatabaseService.create_generated_report(
            db=db,
            file_id=primary_file.file_id,
            report_type="html",
            report_path=str(html_path),
            report_content=html_content,
            file_size=len(html_content.encode('utf-8')),
            generated_by="raghskmr"
        )
        
        pdf_path = REPORTS_DIR / f"{run_id}_report.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        DatabaseService.create_generated_report(
            db=db,
            file_id=primary_file.file_id,
            report_type="pdf",
            report_path=str(pdf_path),
            file_size=len(pdf_bytes),
            generated_by="raghskmr"
        )
        
        ppt_path = REPORTS_DIR / f"{run_id}_report.pptx"
        with open(ppt_path, "wb") as f:
            f.write(ppt_bytes)
        
        DatabaseService.create_generated_report(
            db=db,
            file_id=primary_file.file_id,
            report_type="ppt",
            report_path=str(ppt_path),
            file_size=len(ppt_bytes),
            generated_by="raghskmr"
        )
        
        print(f"Reports saved successfully")
        
        # Update status to generated for all files
        for f in files:
            f.report_status = "generated"
        db.commit()
        
        return {
            "success": True,
            "run_id": run_id,
            "file_count": len(files),
            "total_records": total_records,
            "analysis_duration": analysis_duration,
            "report_urls": {
                "html": f"/api/runs/{run_id}/reports/html",
                "pdf": f"/api/runs/{run_id}/reports/pdf",
                "ppt": f"/api/runs/{run_id}/reports/ppt"
            }
        }
        
    except Exception as e:
        # Update status to error for all files
        for f in files:
            f.report_status = "error"
        db.commit()
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
                data = JTLParser.parse(file_path)
            else:
                data = JSONParser.parse(file_path, category)
            metrics_obj = JMeterAnalyzer.analyze(data)
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
