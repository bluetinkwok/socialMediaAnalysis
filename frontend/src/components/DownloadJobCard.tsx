/**
 * Download Job Card component for displaying job details and progress
 */

import React from 'react';
import ProgressBar from './ProgressBar';
import type { DownloadJob, DownloadJobStatus } from '../types';

interface DownloadJobCardProps {
  job: DownloadJob;
  status?: DownloadJobStatus;
  onCancel?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
  onRefresh?: (jobId: string) => void;
}

const DownloadJobCard: React.FC<DownloadJobCardProps> = ({
  job,
  status,
  onCancel,
  onRetry,
  onRefresh,
}) => {
  // Determine status color and icon
  const getStatusConfig = (jobStatus: string) => {
    switch (jobStatus) {
      case 'completed':
        return {
          color: 'green',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          icon: '✓',
        };
      case 'failed':
        return {
          color: 'red',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          icon: '✗',
        };
      case 'in_progress':
      case 'processing':
        return {
          color: 'blue',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          textColor: 'text-blue-800',
          icon: '⟳',
        };
      case 'pending':
        return {
          color: 'yellow',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          textColor: 'text-yellow-800',
          icon: '⏳',
        };
      default:
        return {
          color: 'gray',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          textColor: 'text-gray-800',
          icon: '?',
        };
    }
  };

  const statusConfig = getStatusConfig(job.status);
  const isActive = job.status === 'in_progress' || job.status === 'processing' || job.status === 'pending';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';

  // Format time duration
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  // Format processing rate
  const formatRate = (rate: number): string => {
    if (rate < 1) return `${(rate * 60).toFixed(1)}/min`;
    return `${rate.toFixed(1)}/s`;
  };

  return (
    <div className={`
      rounded-lg border-2 p-4 transition-all duration-200
      ${statusConfig.bgColor} ${statusConfig.borderColor}
      hover:shadow-md
    `}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{statusConfig.icon}</span>
          <span className={`font-medium ${statusConfig.textColor}`}>
            Job {job.id}
          </span>
          <span className={`
            px-2 py-1 rounded-full text-xs font-medium
            ${statusConfig.bgColor} ${statusConfig.textColor}
          `}>
            {job.status.replace('_', ' ').toUpperCase()}
          </span>
        </div>
        
        {/* Action buttons */}
        <div className="flex space-x-2">
          {isActive && onCancel && (
            <button
              onClick={() => onCancel(job.id)}
              className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
            >
              Cancel
            </button>
          )}
          {isFailed && onRetry && (
            <button
              onClick={() => onRetry(job.id)}
              className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
            >
              Retry
            </button>
          )}
          {onRefresh && (
            <button
              onClick={() => onRefresh(job.id)}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
            >
              Refresh
            </button>
          )}
        </div>
      </div>

      {/* Progress section */}
      {(isActive || isCompleted) && (
        <div className="mb-3">
          <ProgressBar
            progress={status?.progress?.percentage || job.progress || 0}
            color={statusConfig.color as any}
            animated={isActive}
            className="mb-2"
          />
          
          {status && (
            <div className="flex justify-between text-xs text-gray-600">
              <span>
                {status.progress.processed_items || job.processedItems || 0} / {status.progress.total_items || job.totalItems || 0} items
              </span>
              {status.progress.current_step && (
                <span className="capitalize">
                  {status.progress.current_step.replace('_', ' ')}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Timing information */}
      {status?.timing && (
        <div className="grid grid-cols-2 gap-4 text-xs text-gray-600 mb-3">
          <div>
            <span className="font-medium">Elapsed:</span> {formatDuration(status.timing.elapsed_time)}
          </div>
          {status.timing.processing_rate && (
            <div>
              <span className="font-medium">Rate:</span> {formatRate(status.timing.processing_rate)}
            </div>
          )}
          {status.timing.estimated_completion && isActive && (
            <div className="col-span-2">
              <span className="font-medium">ETA:</span> {new Date(status.timing.estimated_completion).toLocaleTimeString()}
            </div>
          )}
        </div>
      )}

      {/* URLs */}
      {status?.urls && status.urls.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-medium text-gray-700 mb-1">URLs:</div>
          <div className="space-y-1">
            {status.urls.slice(0, 3).map((url, index) => (
              <div key={index} className="text-xs text-gray-600 truncate">
                {url}
              </div>
            ))}
            {status.urls.length > 3 && (
              <div className="text-xs text-gray-500">
                +{status.urls.length - 3} more...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Errors */}
      {job.errors && job.errors.length > 0 && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded">
          <div className="text-xs font-medium text-red-700 mb-1">Errors:</div>
          <div className="space-y-1">
            {job.errors.slice(0, 2).map((error, index) => (
              <div key={index} className="text-xs text-red-600">
                {error}
              </div>
            ))}
            {job.errors.length > 2 && (
              <div className="text-xs text-red-500">
                +{job.errors.length - 2} more errors...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Timestamps */}
      <div className="flex justify-between text-xs text-gray-500 mt-3 pt-3 border-t border-gray-200">
        <span>Started: {new Date(job.createdAt).toLocaleString()}</span>
        {job.completedAt && (
          <span>Completed: {new Date(job.completedAt).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
};

export default DownloadJobCard; 