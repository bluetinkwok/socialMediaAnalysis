"""
Computer Vision API endpoints for image and video analysis
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import uuid
import tempfile
import shutil
from datetime import datetime

from db.database import get_db
from db.models import User
from services.cv_analyzer import CVService
from api.v1.auth import get_current_active_user

router = APIRouter(prefix="/cv", tags=["computer-vision"])

# Initialize CV service
cv_service = CVService()

@router.post("/analyze-image")
async def analyze_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyze an uploaded image using computer vision techniques.
    
    Returns detailed analysis including object detection, scene recognition,
    face detection, and color analysis.
    """
    # Create a temporary file to store the uploaded image
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # Write the uploaded file to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        # Analyze the image
        results = cv_service.analyze_image(temp_file.name)
        
        # Clean up the temporary file in the background
        background_tasks.add_task(os.unlink, temp_file.name)
        
        return results
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error analyzing image: {str(e)}")

@router.post("/analyze-video")
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    extract_frames: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyze an uploaded video using computer vision techniques.
    
    Returns detailed analysis including keyframe extraction, scene recognition,
    face detection, and color analysis.
    """
    # Create a temporary file to store the uploaded video
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # Write the uploaded file to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        # Analyze the video
        results = cv_service.analyze_video(temp_file.name, extract_frames=extract_frames)
        
        # Clean up the temporary file in the background
        background_tasks.add_task(os.unlink, temp_file.name)
        
        return results
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error analyzing video: {str(e)}")

@router.post("/detect-objects")
async def detect_objects(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Detect objects in an uploaded image.
    
    Returns a list of detected objects with class, confidence, and bounding box.
    """
    # Create a temporary file to store the uploaded image
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # Write the uploaded file to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        # Detect objects in the image
        results = cv_service.detect_objects(temp_file.name)
        
        # Clean up the temporary file in the background
        background_tasks.add_task(os.unlink, temp_file.name)
        
        return {"objects": results}
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error detecting objects: {str(e)}")

@router.post("/detect-faces")
async def detect_faces(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Detect faces in an uploaded image.
    
    Returns a list of detected faces with bounding boxes and confidence scores.
    """
    # Create a temporary file to store the uploaded image
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # Write the uploaded file to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        # Detect faces in the image
        results = cv_service.detect_faces(temp_file.name)
        
        # Clean up the temporary file in the background
        background_tasks.add_task(os.unlink, temp_file.name)
        
        return {"faces": results}
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error detecting faces: {str(e)}")

@router.post("/analyze-colors")
async def analyze_colors(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyze the color distribution of an uploaded image.
    
    Returns color statistics including mean color, dominant colors, and brightness.
    """
    # Create a temporary file to store the uploaded image
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # Write the uploaded file to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        # Analyze colors in the image
        results = cv_service.analyze_colors(temp_file.name)
        
        # Clean up the temporary file in the background
        background_tasks.add_task(os.unlink, temp_file.name)
        
        return results
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error analyzing colors: {str(e)}")

@router.post("/extract-keyframes")
async def extract_keyframes(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_frames: int = Form(10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Extract key frames from an uploaded video.
    
    Returns a list of keyframes with timestamps and analysis results.
    """
    # Create a temporary file to store the uploaded video
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # Write the uploaded file to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        # Extract keyframes from the video
        results = cv_service.extract_keyframes(temp_file.name, max_frames=max_frames)
        
        # Clean up the temporary file in the background
        background_tasks.add_task(os.unlink, temp_file.name)
        
        # Remove file paths from results for security
        for frame in results:
            if 'path' in frame:
                del frame['path']
        
        return {"keyframes": results}
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error extracting keyframes: {str(e)}")

@router.post("/content-moderation")
async def content_moderation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Perform content moderation on an uploaded image.
    
    Returns moderation results including potential issues and confidence scores.
    """
    # Create a temporary file to store the uploaded image
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        # Write the uploaded file to the temporary file
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        # Perform content moderation
        results = cv_service.detect_content_moderation_issues(temp_file.name)
        
        # Clean up the temporary file in the background
        background_tasks.add_task(os.unlink, temp_file.name)
        
        return results
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file.name)
        raise HTTPException(status_code=500, detail=f"Error in content moderation: {str(e)}")

@router.post("/batch-analyze")
async def batch_analyze(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyze multiple uploaded files (images and videos) in a batch.
    
    Returns analysis results for each file.
    """
    results = []
    temp_files = []
    
    try:
        for file in files:
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_files.append(temp_file.name)
            
            # Write the uploaded file to the temporary file
            shutil.copyfileobj(file.file, temp_file)
            temp_file.close()
            
            # Determine file type
            content_type = file.content_type or ""
            is_video = content_type.startswith("video/")
            
            # Analyze the file
            if is_video:
                analysis = cv_service.analyze_video(temp_file.name, extract_frames=True)
            else:
                analysis = cv_service.analyze_image(temp_file.name)
                
            results.append({
                "filename": file.filename,
                "content_type": content_type,
                "analysis": analysis
            })
        
        # Clean up temporary files in the background
        for temp_file in temp_files:
            background_tasks.add_task(os.unlink, temp_file)
            
        return {"results": results}
    except Exception as e:
        # Clean up temporary files in case of error
        for temp_file in temp_files:
            background_tasks.add_task(os.unlink, temp_file)
            
        raise HTTPException(status_code=500, detail=f"Error in batch analysis: {str(e)}") 