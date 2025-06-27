/**
 * Progress Monitoring Dashboard
 * Main component for monitoring download jobs with real-time updates
 */

import React, { useState, useEffect } from 'react';
import DownloadJobCard from './DownloadJobCard';
import ProgressStats from './ProgressStats';
import type { DownloadJob, DownloadJobStatus } from '../types';

interface ProgressDashboardProps {
  className?: string;
}

const ProgressDashboard: React.FC<ProgressDashboardProps> = ({ className = '' }) => {
  const [jobs, setJobs] = useState<DownloadJob[]>([]);
  const [jobStatuses, setJobStatuses] = useState<Record<string, DownloadJobStatus>>({});
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'failed'>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  // Fetch jobs from API
  const fetchJobs = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/downloads/');
      if (!response.ok) throw new Error('Failed to fetch jobs');
      
      const data = await response.json();
      setJobs(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch jobs');
    } finally {
      setLoading(false);
    }
  };

  // Fetch detailed status for a specific job
  const fetchJobStatus = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/downloads/${jobId}/status`);
      if (!response.ok) throw new Error('Failed to fetch job status');
      
      const status = await response.json();
      setJobStatuses(prev => ({
        ...prev,
        [jobId]: status
      }));
    } catch (err) {
      console.warn(`Failed to fetch status for job ${jobId}:`, err);
    }
  };

  // WebSocket connection for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress`;
    
    const websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
      setWs(websocket);
    };
    
    websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        switch (message.type) {
          case 'progress_update':
            // Update job progress in real-time
            setJobs(prevJobs => 
              prevJobs.map(job => 
                job.id === message.job_id 
                  ? { 
                      ...job, 
                      status: message.status,
                      progress: message.progress_percentage,
                      processedItems: message.processed_items,
                      totalItems: message.total_items
                    }
                  : job
              )
            );
            
            // Update detailed status
            setJobStatuses(prev => ({
              ...prev,
              [message.job_id]: {
                ...prev[message.job_id],
                progress: {
                  percentage: message.progress_percentage,
                  current_step: message.current_step,
                  processed_items: message.processed_items,
                  total_items: message.total_items,
                  message: message.message
                }
              }
            }));
            break;
            
          case 'progress_complete':
          case 'progress_error':
            // Refresh job data when complete or error
            fetchJobs();
            break;
        }
      } catch (err) {
        console.warn('Failed to parse WebSocket message:', err);
      }
    };
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
      setWs(null);
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };
    
    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, []);

  // Subscribe to job updates via WebSocket
  const subscribeToJob = (jobId: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'subscribe_job',
        job_id: jobId
      }));
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchJobs();
  }, []);

  // Subscribe to active jobs for real-time updates
  useEffect(() => {
    const activeJobs = jobs.filter(job => 
      job.status === 'in_progress' || job.status === 'processing' || job.status === 'pending'
    );
    
    activeJobs.forEach(job => {
      subscribeToJob(job.id);
      // Also fetch detailed status for active jobs
      fetchJobStatus(job.id);
    });
  }, [jobs, ws]);

  // Job action handlers
  const handleCancelJob = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/downloads/${jobId}/cancel`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to cancel job');
      
      // Refresh jobs after cancellation
      await fetchJobs();
    } catch (err) {
      console.error('Failed to cancel job:', err);
      setError(err instanceof Error ? err.message : 'Failed to cancel job');
    }
  };

  const handleRetryJob = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/downloads/${jobId}/retry`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to retry job');
      
      // Refresh jobs after retry
      await fetchJobs();
    } catch (err) {
      console.error('Failed to retry job:', err);
      setError(err instanceof Error ? err.message : 'Failed to retry job');
    }
  };

  const handleRefreshJob = (jobId: string) => {
    fetchJobStatus(jobId);
  };

  // Filter jobs based on selected filter
  const filteredJobs = jobs.filter(job => {
    switch (filter) {
      case 'active':
        return job.status === 'in_progress' || job.status === 'processing' || job.status === 'pending';
      case 'completed':
        return job.status === 'completed';
      case 'failed':
        return job.status === 'failed';
      default:
        return true;
    }
  });

  // Calculate stats
  const stats = {
    total: jobs.length,
    active: jobs.filter(j => j.status === 'in_progress' || j.status === 'processing' || j.status === 'pending').length,
    completed: jobs.filter(j => j.status === 'completed').length,
    failed: jobs.filter(j => j.status === 'failed').length,
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Download Progress</h2>
        
        <div className="flex items-center space-x-4">
          {/* WebSocket status indicator */}
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {wsConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
          
          {/* Refresh button */}
          <button
            onClick={fetchJobs}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800 font-medium">Error</div>
          <div className="text-red-600 text-sm">{error}</div>
        </div>
      )}

      {/* Stats */}
      <ProgressStats stats={stats} />

      {/* Filter tabs */}
      <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
        {[
          { key: 'all', label: 'All', count: stats.total },
          { key: 'active', label: 'Active', count: stats.active },
          { key: 'completed', label: 'Completed', count: stats.completed },
          { key: 'failed', label: 'Failed', count: stats.failed },
        ].map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setFilter(key as any)}
            className={`
              flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors
              ${filter === key 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
              }
            `}
          >
            {label} ({count})
          </button>
        ))}
      </div>

      {/* Jobs list */}
      <div className="space-y-4">
        {loading && jobs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            Loading jobs...
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No jobs found for the selected filter.
          </div>
        ) : (
          filteredJobs.map(job => (
            <DownloadJobCard
              key={job.id}
              job={job}
              status={jobStatuses[job.id]}
              onCancel={handleCancelJob}
              onRetry={handleRetryJob}
              onRefresh={handleRefreshJob}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default ProgressDashboard; 