"""
WebSocket API endpoints for real-time progress updates
Provides WebSocket connections for clients to receive live progress updates
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import HTMLResponse

from ...services.websocket_manager import websocket_manager
from ...dependencies import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/progress")
async def websocket_progress_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Authentication token (optional)"),
    client_id: Optional[str] = Query(None, description="Client identifier"),
    user_agent: Optional[str] = Query(None, description="Client user agent")
):
    """
    WebSocket endpoint for receiving real-time progress updates.
    
    Clients can connect to this endpoint to receive:
    - Progress updates for specific download jobs
    - Error notifications
    - Completion notifications
    - Connection status messages
    
    Message types from server:
    - connection_established: Welcome message with connection ID
    - progress_update: Progress update for a subscribed job
    - progress_error: Error notification for a subscribed job
    - progress_complete: Completion notification for a subscribed job
    - job_subscription: Confirmation of job subscription
    - job_unsubscription: Confirmation of job unsubscription
    - pong: Response to ping message
    
    Message types from client:
    - subscribe_job: Subscribe to job progress (requires job_id)
    - unsubscribe_job: Unsubscribe from job progress (requires job_id)
    - ping: Ping server for connection health check
    """
    
    # Prepare client info
    client_info = {
        "client_id": client_id,
        "user_agent": user_agent,
        "has_token": token is not None
    }
    
    connection_id = None
    
    try:
        # Establish WebSocket connection
        connection_id = await websocket_manager.connect(websocket, client_info)
        
        logger.info(f"WebSocket client connected: {connection_id} (client_id: {client_id})")
        
        # Handle incoming messages
        while True:
            message = await websocket.receive_text()
            await websocket_manager.handle_message(connection_id, message)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error for connection {connection_id}: {e}")
    
    finally:
        if connection_id:
            websocket_manager.disconnect(connection_id)


@router.get("/stats")
async def get_websocket_stats(
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get WebSocket connection statistics.
    
    Returns information about active connections and job subscriptions.
    """
    stats = websocket_manager.get_connection_stats()
    
    # Add additional statistics
    stats.update({
        "endpoint": "/ws/progress",
        "supported_message_types": [
            "subscribe_job",
            "unsubscribe_job", 
            "ping"
        ],
        "server_message_types": [
            "connection_established",
            "progress_update",
            "progress_error",
            "progress_complete",
            "job_subscription",
            "job_unsubscription",
            "pong"
        ]
    })
    
    return stats


@router.get("/test", response_class=HTMLResponse)
async def websocket_test_page():
    """
    Simple HTML test page for WebSocket connections.
    Useful for development and testing WebSocket functionality.
    """
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Progress Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .message { background-color: #f8f9fa; border: 1px solid #dee2e6; }
            .controls { margin: 20px 0; }
            .controls input, .controls button { margin: 5px; padding: 8px; }
            #messages { height: 400px; overflow-y: auto; border: 1px solid #dee2e6; padding: 10px; }
            .message-item { margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee; }
            .timestamp { color: #6c757d; font-size: 0.8em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket Progress Test</h1>
            
            <div id="status" class="status disconnected">
                Disconnected
            </div>
            
            <div class="controls">
                <button id="connect">Connect</button>
                <button id="disconnect" disabled>Disconnect</button>
                <button id="ping">Ping</button>
                <br>
                <input type="text" id="jobId" placeholder="Job ID" />
                <button id="subscribe">Subscribe to Job</button>
                <button id="unsubscribe">Unsubscribe from Job</button>
            </div>
            
            <div>
                <h3>Messages</h3>
                <div id="messages"></div>
                <button id="clear">Clear Messages</button>
            </div>
        </div>

        <script>
            let ws = null;
            let connectionId = null;
            
            const statusDiv = document.getElementById('status');
            const messagesDiv = document.getElementById('messages');
            const connectBtn = document.getElementById('connect');
            const disconnectBtn = document.getElementById('disconnect');
            const pingBtn = document.getElementById('ping');
            const subscribeBtn = document.getElementById('subscribe');
            const unsubscribeBtn = document.getElementById('unsubscribe');
            const jobIdInput = document.getElementById('jobId');
            const clearBtn = document.getElementById('clear');
            
            function addMessage(message) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message-item';
                messageDiv.innerHTML = `
                    <div class="timestamp">${new Date().toLocaleTimeString()}</div>
                    <pre>${JSON.stringify(message, null, 2)}</pre>
                `;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            function updateStatus(connected) {
                if (connected) {
                    statusDiv.textContent = `Connected (ID: ${connectionId})`;
                    statusDiv.className = 'status connected';
                    connectBtn.disabled = true;
                    disconnectBtn.disabled = false;
                } else {
                    statusDiv.textContent = 'Disconnected';
                    statusDiv.className = 'status disconnected';
                    connectBtn.disabled = false;
                    disconnectBtn.disabled = true;
                    connectionId = null;
                }
            }
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress?client_id=test-client`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    addMessage({ type: 'system', message: 'WebSocket connection opened' });
                };
                
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'connection_established') {
                        connectionId = message.connection_id;
                        updateStatus(true);
                    }
                    
                    addMessage(message);
                };
                
                ws.onclose = function() {
                    addMessage({ type: 'system', message: 'WebSocket connection closed' });
                    updateStatus(false);
                };
                
                ws.onerror = function(error) {
                    addMessage({ type: 'system', message: 'WebSocket error', error: error });
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                }
            }
            
            function sendMessage(message) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify(message));
                    addMessage({ type: 'sent', message: message });
                } else {
                    addMessage({ type: 'system', message: 'WebSocket not connected' });
                }
            }
            
            connectBtn.onclick = connect;
            disconnectBtn.onclick = disconnect;
            
            pingBtn.onclick = function() {
                sendMessage({ type: 'ping' });
            };
            
            subscribeBtn.onclick = function() {
                const jobId = jobIdInput.value.trim();
                if (jobId) {
                    sendMessage({ type: 'subscribe_job', job_id: jobId });
                } else {
                    alert('Please enter a Job ID');
                }
            };
            
            unsubscribeBtn.onclick = function() {
                const jobId = jobIdInput.value.trim();
                if (jobId) {
                    sendMessage({ type: 'unsubscribe_job', job_id: jobId });
                } else {
                    alert('Please enter a Job ID');
                }
            };
            
            clearBtn.onclick = function() {
                messagesDiv.innerHTML = '';
            };
            
            // Auto-connect on page load
            window.onload = function() {
                setTimeout(connect, 100);
            };
        </script>
    </body>
    </html>
    """
    
    return html_content 