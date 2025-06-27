/**
 * Custom hook for tracking download job progress
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiService } from '../services/api';
import type { DownloadJobStatus, DownloadJob } from '../types';

interface UseDownloadProgressOptions {
  refreshInterval?: number;
  autoRefresh?: boolean;
}

interface UseDownloadProgressReturn {
  jobs: DownloadJob[];
  jobStatuses: Record<string, DownloadJobStatus>;
  loading: boolean;
  error: string | null;
  refreshJobs: () => Promise<void>;
  getJobStatus: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  retryJob: (jobId: string) => Promise<void>;
}

export const useDownloadProgress = (
  options: UseDownloadProgressOptions = {}
): UseDownloadProgressReturn => {
  const { refreshInterval = 2000, autoRefresh = true } = options;
  
  const [jobs, setJobs] = useState<DownloadJob[]>([]);
  const [jobStatuses, setJobStatuses] = useState<Record<string, DownloadJobStatus>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  // Fetch all download jobs
  const refreshJobs = useCallback(async () => {
    if (!mountedRef.current) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const fetchedJobs = await apiService.getDownloadJobs();
      
      if (mountedRef.current) {
        setJobs(fetchedJobs);
        
        // Fetch detailed status for active jobs
        const activeJobs = fetchedJobs.filter(job => 
          job.status === 'processing' || job.status === 'in_progress' || job.status === 'pending'
        );
        
        await Promise.all(
          activeJobs.map(job => getJobStatus(job.id))
        );
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to fetch jobs');
        console.error('Error fetching download jobs:', err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  // Get detailed status for a specific job
  const getJobStatus = useCallback(async (jobId: string) => {
    if (!mountedRef.current) return;
    
    try {
      const status = await apiService.getDownloadJobStatus(jobId);
      
      if (mountedRef.current) {
        setJobStatuses(prev => ({
          ...prev,
          [jobId]: status
        }));
      }
    } catch (err) {
      console.error(`Error fetching status for job ${jobId}:`, err);
      // Don't set error state for individual job status failures
    }
  }, []);

  // Cancel a download job
  const cancelJob = useCallback(async (jobId: string) => {
    try {
      await apiService.cancelDownloadJob(jobId);
      await refreshJobs(); // Refresh the job list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel job');
      throw err;
    }
  }, [refreshJobs]);

  // Retry a failed download job
  const retryJob = useCallback(async (jobId: string) => {
    try {
      await apiService.retryDownloadJob(jobId);
      await refreshJobs(); // Refresh the job list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry job');
      throw err;
    }
  }, [refreshJobs]);

  // Set up automatic refresh for active jobs
  useEffect(() => {
    if (!autoRefresh) return;

    const hasActiveJobs = jobs.some(job => 
      job.status === 'processing' || job.status === 'in_progress' || job.status === 'pending'
    );

    if (hasActiveJobs) {
      intervalRef.current = setInterval(() => {
        refreshJobs();
      }, refreshInterval);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobs, autoRefresh, refreshInterval, refreshJobs]);

  // Initial load
  useEffect(() => {
    refreshJobs();
    
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [refreshJobs]);

  return {
    jobs,
    jobStatuses,
    loading,
    error,
    refreshJobs,
    getJobStatus,
    cancelJob,
    retryJob,
  };
}; 