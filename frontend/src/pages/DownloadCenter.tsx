/**
 * Download Center page component
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import apiService from '../services/api';
import type { DownloadJob, DownloadRequest, Platform } from '../types';

const DownloadCenter: React.FC = () => {
  // State for single URL input
  const [url, setUrl] = useState<string>('');
  const [platform, setPlatform] = useState<Platform | ''>('');
  const [includeFiles, setIncludeFiles] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  // State for batch upload
  const [batchFile, setBatchFile] = useState<File | null>(null);
  const [batchPlatform, setBatchPlatform] = useState<Platform | ''>('');
  const [isBatchSubmitting, setIsBatchSubmitting] = useState<boolean>(false);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchSuccess, setBatchSuccess] = useState<string | null>(null);

  // State for download jobs
  const [activeJobs, setActiveJobs] = useState<DownloadJob[]>([]);
  const [recentJobs, setRecentJobs] = useState<DownloadJob[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // File input reference
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch download jobs on component mount
  useEffect(() => {
    fetchDownloadJobs();
    
    // Set up polling for active jobs
    const intervalId = setInterval(fetchDownloadJobs, 5000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  // Function to fetch download jobs
  const fetchDownloadJobs = async () => {
    try {
      setIsLoading(true);
      
      // Fetch all jobs
      const jobs = await apiService.getDownloadJobs();
      
      // Split into active and recent jobs
      const active = jobs.filter(job => 
        job.status === 'pending' || 
        job.status === 'processing' || 
        job.status === 'in_progress'
      );
      
      const recent = jobs.filter(job => 
        job.status === 'completed' || 
        job.status === 'failed'
      ).slice(0, 10); // Only show 10 most recent completed/failed jobs
      
      setActiveJobs(active);
      setRecentJobs(recent);
      setLoadError(null);
    } catch (error) {
      console.error('Error fetching download jobs:', error);
      setLoadError('Failed to load download jobs. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  // Function to handle single URL submission
  const handleSingleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate input
    if (!url.trim()) {
      setSubmitError('Please enter a URL');
      return;
    }
    
    try {
      setIsSubmitting(true);
      setSubmitError(null);
      setSubmitSuccess(null);
      
      // Prepare request
      const request: DownloadRequest = {
        urls: [url.trim()],
        platform: platform as Platform || 'youtube', // Default to YouTube if not specified
        options: {
          includeComments: includeFiles
        }
      };
      
      // Submit request
      const job = await apiService.submitDownloadRequest(request);
      
      // Clear form and show success message
      setUrl('');
      setPlatform('');
      setSubmitSuccess(`Download job submitted successfully! Job ID: ${job.id}`);
      
      // Refresh job list
      fetchDownloadJobs();
    } catch (error) {
      console.error('Error submitting download request:', error);
      setSubmitError('Failed to submit download request. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Function to handle batch file upload
  const handleBatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate input
    if (!batchFile) {
      setBatchError('Please select a file');
      return;
    }
    
    try {
      setIsBatchSubmitting(true);
      setBatchError(null);
      setBatchSuccess(null);
      
      // Read file content
      const fileContent = await readFileContent(batchFile);
      
      // Parse URLs from file (assuming one URL per line)
      const urls = fileContent
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
      
      if (urls.length === 0) {
        setBatchError('No valid URLs found in the file');
        setIsBatchSubmitting(false);
        return;
      }
      
      // Prepare request
      const request: DownloadRequest = {
        urls: urls,
        platform: batchPlatform as Platform || 'youtube', // Default to YouTube if not specified
        options: {
          includeComments: includeFiles
        }
      };
      
      // Submit request
      const job = await apiService.submitDownloadRequest(request);
      
      // Clear form and show success message
      setBatchFile(null);
      setBatchPlatform('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setBatchSuccess(`Batch download job submitted successfully! Job ID: ${job.id} with ${urls.length} URLs`);
      
      // Refresh job list
      fetchDownloadJobs();
    } catch (error) {
      console.error('Error submitting batch download request:', error);
      setBatchError('Failed to submit batch download request. Please try again.');
    } finally {
      setIsBatchSubmitting(false);
    }
  };

  // Function to read file content
  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          resolve(event.target.result as string);
        } else {
          reject(new Error('Failed to read file'));
        }
      };
      reader.onerror = () => reject(new Error('File read error'));
      reader.readAsText(file);
    });
  };

  // Function to handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setBatchFile(e.target.files[0]);
    }
  };

  // Function to get status badge color
  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'in_progress':
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  // Function to format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Download Center</h1>
        <p className="text-gray-600">Download content from social media platforms</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Single URL Download */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Single URL Download</h3>
          </div>
          <div className="p-6">
            <form onSubmit={handleSingleSubmit}>
              <div className="mb-4">
                <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
                  URL
                </label>
                <input
                  type="text"
                  id="url"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              <div className="mb-4">
                <label htmlFor="platform" className="block text-sm font-medium text-gray-700 mb-1">
                  Platform (Optional - Auto-detected if not specified)
                </label>
                <select
                  id="platform"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value as Platform | '')}
                  disabled={isSubmitting}
                >
                  <option value="">Auto-detect</option>
                  <option value="youtube">YouTube</option>
                  <option value="instagram">Instagram</option>
                  <option value="threads">Threads</option>
                  <option value="rednote">RedNote</option>
                </select>
              </div>

              <div className="mb-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="includeFiles"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    checked={includeFiles}
                    onChange={(e) => setIncludeFiles(e.target.checked)}
                    disabled={isSubmitting}
                  />
                  <label htmlFor="includeFiles" className="ml-2 block text-sm text-gray-700">
                    Download media files (videos, images)
                  </label>
                </div>
              </div>

              {submitError && (
                <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md">
                  {submitError}
                </div>
              )}

              {submitSuccess && (
                <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-md">
                  {submitSuccess}
                </div>
              )}

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Download'}
              </button>
            </form>
          </div>
        </div>

        {/* Batch URL Download */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Batch URL Download</h3>
          </div>
          <div className="p-6">
            <form onSubmit={handleBatchSubmit}>
              <div className="mb-4">
                <label htmlFor="batchFile" className="block text-sm font-medium text-gray-700 mb-1">
                  Upload File (CSV or TXT with one URL per line)
                </label>
                <input
                  type="file"
                  id="batchFile"
                  ref={fileInputRef}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  accept=".csv,.txt"
                  onChange={handleFileChange}
                  disabled={isBatchSubmitting}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Max file size: 1MB. Format: One URL per line.
                </p>
              </div>

              <div className="mb-4">
                <label htmlFor="batchPlatform" className="block text-sm font-medium text-gray-700 mb-1">
                  Platform (Optional - Auto-detected if not specified)
                </label>
                <select
                  id="batchPlatform"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={batchPlatform}
                  onChange={(e) => setBatchPlatform(e.target.value as Platform | '')}
                  disabled={isBatchSubmitting}
                >
                  <option value="">Auto-detect</option>
                  <option value="youtube">YouTube</option>
                  <option value="instagram">Instagram</option>
                  <option value="threads">Threads</option>
                  <option value="rednote">RedNote</option>
                </select>
              </div>

              {batchError && (
                <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md">
                  {batchError}
                </div>
              )}

              {batchSuccess && (
                <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-md">
                  {batchSuccess}
                </div>
              )}

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                disabled={isBatchSubmitting || !batchFile}
              >
                {isBatchSubmitting ? 'Submitting...' : 'Upload & Download'}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Active Download Jobs */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Active Download Jobs</h3>
        </div>
        <div className="p-6">
          {isLoading ? (
            <div className="text-center py-4">
              <div className="spinner h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <p className="text-gray-500">Loading jobs...</p>
            </div>
          ) : loadError ? (
            <div className="p-3 bg-red-50 text-red-700 rounded-md">
              {loadError}
            </div>
          ) : activeJobs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No active download jobs
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Job ID
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Progress
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {activeJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link to={`/downloads/${job.id}`} className="text-blue-600 hover:text-blue-900">
                          {job.id.substring(0, 8)}...
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeColor(job.status)}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="w-full bg-gray-200 rounded-full h-2.5">
                          <div 
                            className="h-2.5 rounded-full bg-blue-600"
                            style={{ width: `${job.progress}%` }}
                          ></div>
                        </div>
                        <span className="text-xs text-gray-500 mt-1">{job.progress}%</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(job.createdAt.toString())}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          className="text-red-600 hover:text-red-900 text-sm font-medium"
                          onClick={async () => {
                            try {
                              await apiService.cancelDownloadJob(job.id);
                              fetchDownloadJobs();
                            } catch (error) {
                              console.error('Error cancelling job:', error);
                            }
                          }}
                        >
                          Cancel
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Recent Download Jobs */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Download Jobs</h3>
        </div>
        <div className="p-6">
          {isLoading ? (
            <div className="text-center py-4">
              <div className="spinner h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <p className="text-gray-500">Loading jobs...</p>
            </div>
          ) : loadError ? (
            <div className="p-3 bg-red-50 text-red-700 rounded-md">
              {loadError}
            </div>
          ) : recentJobs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No recent download jobs
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Job ID
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Items
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Completed
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recentJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link to={`/downloads/${job.id}`} className="text-blue-600 hover:text-blue-900">
                          {job.id.substring(0, 8)}...
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeColor(job.status)}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {job.processedItems} / {job.totalItems}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(job.createdAt.toString())}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {job.completedAt ? formatDate(job.completedAt.toString()) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-4 text-right">
                <Link to="/downloads" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                  View all downloads →
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DownloadCenter; 