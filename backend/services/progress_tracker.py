"""
Progress Tracking System for Download Operations
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProgressStatus(Enum):
    """Progress status enumeration"""
    PENDING = "pending"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressStep(Enum):
    """Download progress steps"""
    INITIALIZING = "initializing"
    VALIDATING_URL = "validating_url"
    FETCHING_CONTENT = "fetching_content"
    PARSING_CONTENT = "parsing_content"
    EXTRACTING_MEDIA = "extracting_media"
    DOWNLOADING_FILES = "downloading_files"
    STORING_DATA = "storing_data"
    FINALIZING = "finalizing"


@dataclass
class ProgressUpdate:
    """Progress update data structure"""
    task_id: str
    status: ProgressStatus
    current_step: ProgressStep
    progress_percentage: float
    message: str
    current_item: int = 0
    total_items: int = 1
    error: Optional[str] = None
    warning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProgressCallback(ABC):
    """Abstract base class for progress callbacks"""
    
    @abstractmethod
    async def on_progress_update(self, update: ProgressUpdate) -> None:
        """Handle progress update"""
        pass
    
    @abstractmethod
    async def on_error(self, task_id: str, error: str, step: ProgressStep) -> None:
        """Handle error"""
        pass
    
    @abstractmethod
    async def on_completion(self, task_id: str, success: bool, final_message: str) -> None:
        """Handle completion"""
        pass


class DatabaseProgressCallback(ProgressCallback):
    """Progress callback that stores updates in the database"""
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    async def on_progress_update(self, update: ProgressUpdate) -> None:
        """Store progress update in database"""
        try:
            from db.models import DownloadJob
            
            # Find or create download job
            job = self.db_session.query(DownloadJob).filter(
                DownloadJob.id == update.task_id
            ).first()
            
            if job:
                job.progress_percentage = update.progress_percentage
                job.processed_items = update.current_item
                job.total_items = update.total_items
                job.updated_at = update.timestamp
                
                # Update status if changed
                if update.status == ProgressStatus.COMPLETED:
                    job.status = "completed"
                    job.completed_at = update.timestamp
                elif update.status == ProgressStatus.FAILED:
                    job.status = "failed"
                elif update.status == ProgressStatus.IN_PROGRESS:
                    job.status = "in_progress"
                    if not job.started_at:
                        job.started_at = update.timestamp
                
                self.db_session.commit()
                logger.debug(f"Updated progress for task {update.task_id}: {update.progress_percentage}%")
                
        except Exception as e:
            logger.error(f"Failed to update progress in database: {e}")
            self.db_session.rollback()
    
    async def on_error(self, task_id: str, error: str, step: ProgressStep) -> None:
        """Store error in database"""
        try:
            from db.models import DownloadJob
            
            job = self.db_session.query(DownloadJob).filter(
                DownloadJob.id == task_id
            ).first()
            
            if job:
                # Add error to errors list
                current_errors = job.errors or []
                current_errors.append({
                    "error": error,
                    "step": step.value,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                job.errors = current_errors
                job.error_count = len(current_errors)
                job.status = "failed"
                job.updated_at = datetime.now(timezone.utc)
                
                self.db_session.commit()
                logger.error(f"Recorded error for task {task_id}: {error}")
                
        except Exception as e:
            logger.error(f"Failed to record error in database: {e}")
            self.db_session.rollback()
    
    async def on_completion(self, task_id: str, success: bool, final_message: str) -> None:
        """Handle completion"""
        try:
            from db.models import DownloadJob
            
            job = self.db_session.query(DownloadJob).filter(
                DownloadJob.id == task_id
            ).first()
            
            if job:
                job.status = "completed" if success else "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.progress_percentage = 100.0 if success else job.progress_percentage
                job.updated_at = datetime.now(timezone.utc)
                
                self.db_session.commit()
                logger.info(f"Task {task_id} completed: {final_message}")
                
        except Exception as e:
            logger.error(f"Failed to record completion in database: {e}")
            self.db_session.rollback()


class LoggingProgressCallback(ProgressCallback):
    """Progress callback that logs updates"""
    
    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level
    
    async def on_progress_update(self, update: ProgressUpdate) -> None:
        """Log progress update"""
        logger.log(
            self.log_level,
            f"Task {update.task_id}: {update.current_step.value} - "
            f"{update.progress_percentage:.1f}% - {update.message}"
        )
    
    async def on_error(self, task_id: str, error: str, step: ProgressStep) -> None:
        """Log error"""
        logger.error(f"Task {task_id} error at {step.value}: {error}")
    
    async def on_completion(self, task_id: str, success: bool, final_message: str) -> None:
        """Log completion"""
        level = logging.INFO if success else logging.ERROR
        logger.log(level, f"Task {task_id} {'completed' if success else 'failed'}: {final_message}")


class ProgressTracker:
    """Main progress tracker class"""
    
    def __init__(self, task_id: str = None):
        self.task_id = task_id or str(uuid4())
        self.callbacks: List[ProgressCallback] = []
        self.current_step = ProgressStep.INITIALIZING
        self.current_item = 0
        self.total_items = 1
        self.progress_percentage = 0.0
        self.status = ProgressStatus.PENDING
        self.start_time = None
        self.step_weights = {
            ProgressStep.INITIALIZING: 5,
            ProgressStep.VALIDATING_URL: 5,
            ProgressStep.FETCHING_CONTENT: 25,
            ProgressStep.PARSING_CONTENT: 15,
            ProgressStep.EXTRACTING_MEDIA: 10,
            ProgressStep.DOWNLOADING_FILES: 25,
            ProgressStep.STORING_DATA: 10,
            ProgressStep.FINALIZING: 5
        }
    
    def add_callback(self, callback: ProgressCallback) -> None:
        """Add a progress callback"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: ProgressCallback) -> None:
        """Remove a progress callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def start(self, total_items: int = 1) -> None:
        """Start progress tracking"""
        self.total_items = total_items
        self.current_item = 0
        self.status = ProgressStatus.STARTING
        self.start_time = time.time()
        
        await self._notify_progress("Starting download operation")
    
    async def update_step(self, step: ProgressStep, message: str = "", 
                         item_progress: float = 0.0) -> None:
        """Update current step and progress"""
        self.current_step = step
        self.status = ProgressStatus.IN_PROGRESS
        
        # Calculate overall progress based on step weights and item progress
        step_progress = self._calculate_step_progress(step, item_progress)
        self.progress_percentage = min(step_progress, 99.0)  # Cap at 99% until completion
        
        await self._notify_progress(message or f"Processing {step.value}")
    
    async def update_item_progress(self, current_item: int, message: str = "") -> None:
        """Update progress for current item in batch"""
        self.current_item = current_item
        
        # Recalculate progress with new item count
        item_progress = (current_item / self.total_items) * 100 if self.total_items > 0 else 0
        step_progress = self._calculate_step_progress(self.current_step, item_progress)
        self.progress_percentage = min(step_progress, 99.0)
        
        await self._notify_progress(message or f"Processing item {current_item}/{self.total_items}")
    
    async def report_error(self, error: str, warning: bool = False) -> None:
        """Report an error or warning"""
        if warning:
            await self._notify_progress(f"Warning: {error}", warning=error)
        else:
            self.status = ProgressStatus.FAILED
            for callback in self.callbacks:
                await callback.on_error(self.task_id, error, self.current_step)
    
    async def complete(self, success: bool = True, message: str = "") -> None:
        """Mark progress as complete"""
        self.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
        self.progress_percentage = 100.0 if success else self.progress_percentage
        
        final_message = message or ("Download completed successfully" if success else "Download failed")
        
        await self._notify_progress(final_message)
        
        for callback in self.callbacks:
            await callback.on_completion(self.task_id, success, final_message)
    
    def _calculate_step_progress(self, step: ProgressStep, item_progress: float) -> float:
        """Calculate overall progress based on current step and item progress"""
        # Get the cumulative weight of completed steps
        completed_weight = sum(
            weight for s, weight in self.step_weights.items() 
            if list(self.step_weights.keys()).index(s) < list(self.step_weights.keys()).index(step)
        )
        
        # Get current step weight and progress within step
        current_step_weight = self.step_weights[step]
        step_progress = (item_progress / 100) * current_step_weight
        
        # Calculate total progress
        total_weight = sum(self.step_weights.values())
        overall_progress = ((completed_weight + step_progress) / total_weight) * 100
        
        return overall_progress
    
    async def _notify_progress(self, message: str, warning: str = None) -> None:
        """Notify all callbacks of progress update"""
        update = ProgressUpdate(
            task_id=self.task_id,
            status=self.status,
            current_step=self.current_step,
            progress_percentage=self.progress_percentage,
            message=message,
            current_item=self.current_item,
            total_items=self.total_items,
            warning=warning
        )
        
        for callback in self.callbacks:
            try:
                await callback.on_progress_update(update)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status as dictionary"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "current_step": self.current_step.value,
            "progress_percentage": self.progress_percentage,
            "current_item": self.current_item,
            "total_items": self.total_items,
            "elapsed_time": elapsed_time
        } 