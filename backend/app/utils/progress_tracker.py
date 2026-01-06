"""Progress tracking for report generation"""
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

# In-memory progress store (in production, use Redis or database)
_progress_store: Dict[str, Dict] = {}

class ReportProgressTracker:
    """Track progress of report generation tasks"""
    
    TASKS = [
        {"id": "parsing", "name": "Parsing Files", "description": "Reading and parsing data files"},
        {"id": "analysis", "name": "Data Analysis", "description": "Analyzing performance metrics"},
        {"id": "html_generation", "name": "HTML Report", "description": "Generating HTML report"},
        {"id": "pdf_generation", "name": "PDF Report", "description": "Generating PDF report"},
        {"id": "ppt_generation", "name": "PPT Report", "description": "Generating PowerPoint report"},
    ]
    
    @staticmethod
    def initialize(run_id: str) -> Dict:
        """Initialize progress tracking for a run"""
        progress = {
            "run_id": run_id,
            "status": "in_progress",
            "started_at": datetime.utcnow().isoformat(),
            "current_task": None,
            "tasks": {
                task["id"]: {
                    "name": task["name"],
                    "description": task["description"],
                    "status": "pending",  # pending, in_progress, completed, failed
                    "started_at": None,
                    "completed_at": None,
                    "progress_percent": 0
                }
                for task in ReportProgressTracker.TASKS
            },
            "overall_progress": 0,
            "message": "Initializing report generation...",
            "last_updated": datetime.utcnow().isoformat()
        }
        _progress_store[run_id] = progress
        return progress
    
    @staticmethod
    def update_task(run_id: str, task_id: str, status: str, progress_percent: int = 0, message: str = None):
        """Update a specific task's status"""
        if run_id not in _progress_store:
            ReportProgressTracker.initialize(run_id)
        
        progress = _progress_store[run_id]
        
        if task_id in progress["tasks"]:
            task = progress["tasks"][task_id]
            task["status"] = status
            task["progress_percent"] = progress_percent
            
            if status == "in_progress" and not task["started_at"]:
                task["started_at"] = datetime.utcnow().isoformat()
            
            if status in ["completed", "failed"]:
                task["completed_at"] = datetime.utcnow().isoformat()
        
        progress["current_task"] = task_id
        progress["last_updated"] = datetime.utcnow().isoformat()
        
        if message:
            progress["message"] = message
        
        # Calculate overall progress
        completed_tasks = sum(1 for t in progress["tasks"].values() if t["status"] == "completed")
        total_tasks = len(progress["tasks"])
        progress["overall_progress"] = int((completed_tasks / total_tasks) * 100)
        
        return progress
    
    @staticmethod
    def get_progress(run_id: str) -> Optional[Dict]:
        """Get current progress for a run"""
        return _progress_store.get(run_id)
    
    @staticmethod
    def complete(run_id: str, message: str = "Report generation completed successfully"):
        """Mark report generation as completed - only if all tasks are completed"""
        if run_id not in _progress_store:
            return None
            
        progress = _progress_store[run_id]
        
        # Validate that all tasks are completed
        all_tasks = progress["tasks"]
        completed_count = sum(1 for t in all_tasks.values() if t["status"] == "completed")
        failed_count = sum(1 for t in all_tasks.values() if t["status"] == "failed")
        total_tasks = len(all_tasks)
        
        # Check if all tasks are completed (or at least all critical ones)
        critical_tasks = ["parsing", "analysis", "html_generation"]
        critical_completed = all(all_tasks.get(task_id, {}).get("status") == "completed" for task_id in critical_tasks if task_id in all_tasks)
        
        if not critical_completed:
            # Not all critical tasks completed - don't mark as completed
            incomplete_tasks = [task_id for task_id, task in all_tasks.items() if task["status"] not in ["completed", "failed"]]
            progress["status"] = "in_progress"
            progress["message"] = f"Waiting for tasks to complete: {', '.join(incomplete_tasks)}"
            progress["last_updated"] = datetime.utcnow().isoformat()
            return progress
        
        # All critical tasks completed - mark as completed
        progress["status"] = "completed"
        progress["overall_progress"] = 100
        progress["message"] = message
        progress["completed_at"] = datetime.utcnow().isoformat()
        progress["last_updated"] = datetime.utcnow().isoformat()
        
        # Log completion summary
        print(f"✓ Report generation completed for {run_id}")
        print(f"  Completed tasks: {completed_count}/{total_tasks}")
        print(f"  Failed tasks: {failed_count}/{total_tasks}")
        
        return progress
    
    @staticmethod
    def fail(run_id: str, error_message: str):
        """Mark report generation as failed"""
        if run_id in _progress_store:
            progress = _progress_store[run_id]
            progress["status"] = "failed"
            progress["message"] = f"Error: {error_message}"
            progress["completed_at"] = datetime.utcnow().isoformat()
            progress["last_updated"] = datetime.utcnow().isoformat()
            return progress
        return None
    
    @staticmethod
    def cleanup_old_progress(max_age_minutes: int = 60):
        """Remove old progress entries"""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        to_remove = []
        
        for run_id, progress in _progress_store.items():
            last_updated = datetime.fromisoformat(progress["last_updated"])
            if last_updated < cutoff:
                to_remove.append(run_id)
        
        for run_id in to_remove:
            del _progress_store[run_id]
    
    @staticmethod
    def is_stuck(run_id: str, timeout_minutes: int = 5) -> bool:
        """Check if report generation appears to be stuck"""
        if run_id not in _progress_store:
            return False
        
        progress = _progress_store[run_id]
        last_updated = datetime.fromisoformat(progress["last_updated"])
        age = datetime.utcnow() - last_updated
        
        # If no update in last 5 minutes and status is in_progress, it's stuck
        return age > timedelta(minutes=timeout_minutes) and progress["status"] == "in_progress"
    
    @staticmethod
    def clear_progress(run_id: str):
        """Clear progress tracking for a specific run_id"""
        if run_id in _progress_store:
            del _progress_store[run_id]
            print(f"✓ Cleared progress tracking for {run_id}")
            return True
        return False

