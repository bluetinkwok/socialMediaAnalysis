"""
WebSocket Manager for Real-time Progress Updates
Handles WebSocket connections and broadcasts progress updates to clients
"""

import json
import logging
from typing import Dict, Set, Any, Optional
from uuid import uuid4
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from .progress_tracker import ProgressCallback, ProgressUpdate

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Represents an active WebSocket connection with metadata"""
    
    def __init__(self, websocket: WebSocket, connection_id: str, client_info: Optional[Dict[str, Any]] = None):
        self.websocket = websocket
        self.connection_id = connection_id
        self.client_info = client_info or {}
        self.connected_at = datetime.utcnow()
        self.subscribed_jobs: Set[str] = set()
        self.is_active = True
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to client, returns False if connection is broken"""
        try:
            await self.websocket.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to connection {self.connection_id}: {e}")
            self.is_active = False
            return False
    
    def subscribe_to_job(self, job_id: str):
        """Subscribe to progress updates for a specific job"""
        self.subscribed_jobs.add(job_id)
    
    def unsubscribe_from_job(self, job_id: str):
        """Unsubscribe from progress updates for a specific job"""
        self.subscribed_jobs.discard(job_id)
    
    def is_subscribed_to_job(self, job_id: str) -> bool:
        """Check if connection is subscribed to a specific job"""
        return job_id in self.subscribed_jobs


class WebSocketManager:
    """Manages WebSocket connections and handles message broadcasting"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.job_subscribers: Dict[str, Set[str]] = {}  # job_id -> set of connection_ids
    
    async def connect(self, websocket: WebSocket, client_info: Optional[Dict[str, Any]] = None) -> str:
        """Accept new WebSocket connection and return connection ID"""
        await websocket.accept()
        connection_id = str(uuid4())
        
        connection = WebSocketConnection(websocket, connection_id, client_info)
        self.connections[connection_id] = connection
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Send welcome message
        await connection.send_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to progress updates"
        })
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            
            # Remove from job subscriptions
            for job_id in connection.subscribed_jobs:
                if job_id in self.job_subscribers:
                    self.job_subscribers[job_id].discard(connection_id)
                    if not self.job_subscribers[job_id]:
                        del self.job_subscribers[job_id]
            
            del self.connections[connection_id]
            logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def subscribe_to_job(self, connection_id: str, job_id: str) -> bool:
        """Subscribe a connection to job progress updates"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.subscribe_to_job(job_id)
        
        if job_id not in self.job_subscribers:
            self.job_subscribers[job_id] = set()
        self.job_subscribers[job_id].add(connection_id)
        
        # Send confirmation
        await connection.send_message({
            "type": "job_subscription",
            "job_id": job_id,
            "status": "subscribed",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.debug(f"Connection {connection_id} subscribed to job {job_id}")
        return True
    
    async def unsubscribe_from_job(self, connection_id: str, job_id: str) -> bool:
        """Unsubscribe a connection from job progress updates"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.unsubscribe_from_job(job_id)
        
        if job_id in self.job_subscribers:
            self.job_subscribers[job_id].discard(connection_id)
            if not self.job_subscribers[job_id]:
                del self.job_subscribers[job_id]
        
        # Send confirmation
        await connection.send_message({
            "type": "job_unsubscription",
            "job_id": job_id,
            "status": "unsubscribed",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.debug(f"Connection {connection_id} unsubscribed from job {job_id}")
        return True
    
    async def broadcast_to_job_subscribers(self, job_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections subscribed to a specific job"""
        if job_id not in self.job_subscribers:
            return 0
        
        subscribers = self.job_subscribers[job_id].copy()
        successful_sends = 0
        broken_connections = []
        
        for connection_id in subscribers:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                if await connection.send_message(message):
                    successful_sends += 1
                else:
                    broken_connections.append(connection_id)
        
        # Clean up broken connections
        for connection_id in broken_connections:
            self.disconnect(connection_id)
        
        logger.debug(f"Broadcasted message to {successful_sends}/{len(subscribers)} subscribers for job {job_id}")
        return successful_sends
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all active connections"""
        active_connections = list(self.connections.keys())
        successful_sends = 0
        broken_connections = []
        
        for connection_id in active_connections:
            connection = self.connections[connection_id]
            if await connection.send_message(message):
                successful_sends += 1
            else:
                broken_connections.append(connection_id)
        
        # Clean up broken connections
        for connection_id in broken_connections:
            self.disconnect(connection_id)
        
        logger.debug(f"Broadcasted message to {successful_sends}/{len(active_connections)} connections")
        return successful_sends
    
    async def handle_message(self, connection_id: str, message: str):
        """Handle incoming message from WebSocket client"""
        if connection_id not in self.connections:
            return
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe_job":
                job_id = data.get("job_id")
                if job_id:
                    await self.subscribe_to_job(connection_id, job_id)
            
            elif message_type == "unsubscribe_job":
                job_id = data.get("job_id")
                if job_id:
                    await self.unsubscribe_from_job(connection_id, job_id)
            
            elif message_type == "ping":
                # Respond to ping with pong
                connection = self.connections[connection_id]
                await connection.send_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                logger.warning(f"Unknown message type from {connection_id}: {message_type}")
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from connection {connection_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections"""
        return {
            "total_connections": len(self.connections),
            "active_connections": sum(1 for conn in self.connections.values() if conn.is_active),
            "total_job_subscriptions": len(self.job_subscribers),
            "jobs_with_subscribers": list(self.job_subscribers.keys())
        }


class WebSocketProgressCallback(ProgressCallback):
    """Progress callback that broadcasts updates via WebSocket"""
    
    def __init__(self, websocket_manager: WebSocketManager, job_id: str):
        self.websocket_manager = websocket_manager
        self.job_id = job_id
    
    async def on_progress_update(self, update: ProgressUpdate):
        """Handle progress update by broadcasting to WebSocket subscribers"""
        message = {
            "type": "progress_update",
            "job_id": self.job_id,
            "data": {
                "task_id": update.task_id,
                "status": update.status.value,
                "current_step": update.current_step.value,
                "progress_percentage": update.progress_percentage,
                "message": update.message,
                "current_item": update.current_item,
                "total_items": update.total_items,
                "timestamp": update.timestamp.isoformat()
            }
        }
        
        # Add error information if present
        if update.error:
            message["data"]["error"] = update.error
        
        # Add warning information if present
        if update.warning:
            message["data"]["warning"] = update.warning
        
        # Add metadata if present
        if update.metadata:
            message["data"]["metadata"] = update.metadata
        
        await self.websocket_manager.broadcast_to_job_subscribers(self.job_id, message)
    
    async def on_error(self, task_id: str, error: str, step: str = None):
        """Handle error by broadcasting to WebSocket subscribers"""
        message = {
            "type": "progress_error",
            "job_id": self.job_id,
            "data": {
                "task_id": task_id,
                "error": error,
                "step": step,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.websocket_manager.broadcast_to_job_subscribers(self.job_id, message)
    
    async def on_complete(self, task_id: str, success: bool, message: str = None):
        """Handle completion by broadcasting to WebSocket subscribers"""
        completion_message = {
            "type": "progress_complete",
            "job_id": self.job_id,
            "data": {
                "task_id": task_id,
                "success": success,
                "message": message or ("Download completed successfully" if success else "Download failed"),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.websocket_manager.broadcast_to_job_subscribers(self.job_id, completion_message)


# Global WebSocket manager instance
websocket_manager = WebSocketManager() 