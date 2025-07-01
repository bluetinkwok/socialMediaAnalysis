/**
 * Download Center page component
 */

import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import apiService from '../services/api';
import type { DownloadJob, DownloadRequest, Platform } from '../types';
import { Tabs, Tab, Box } from '@mui/material';
import YouTubeDownloader from '../components/YouTubeDownloader';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`download-tabpanel-${index}`}
      aria-labelledby={`download-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const DownloadCenter: React.FC = () => {
  // Tab state
  const [tabValue, setTabValue] = useState(0);

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

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

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

      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="download options tabs">
            <Tab label="YouTube Downloader" id="download-tab-0" aria-controls="download-tabpanel-0" />
            <Tab label="General Downloader" id="download-tab-1" aria-controls="download-tabpanel-1" />
            <Tab label="Batch Download" id="download-tab-2" aria-controls="download-tabpanel-2" />
          </Tabs>
        </Box>
        
        <TabPanel value={tabValue} index={0}>
          <YouTubeDownloader />
        </TabPanel>
        
        <TabPanel value={tabValue} index={1}>
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
                    Platform
                  </label>
                  <select
                    id="platform"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={platform}
                    onChange={(e) => setPlatform(e.target.value as Platform | '')}
                    disabled={isSubmitting}
                  >
                    <option value="">Select Platform</option>
                    <option value="youtube">YouTube</option>
                    <option value="twitter">Twitter</option>
                    <option value="instagram">Instagram</option>
                    <option value="tiktok">TikTok</option>
                    <option value="facebook">Facebook</option>
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
                      Include comments and metadata
                    </label>
                  </div>
                </div>

                {submitError && (
                  <div className="mb-4 p-3 bg-red-100 text-red-800 rounded-md">
                    {submitError}
                  </div>
                )}

                {submitSuccess && (
                  <div className="mb-4 p-3 bg-green-100 text-green-800 rounded-md">
                    {submitSuccess}
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Submitting...' : 'Download'}
                </button>
              </form>
            </div>
          </div>
        </TabPanel>
        
        <TabPanel value={tabValue} index={2}>
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Batch URL Download</h3>
            </div>
            <div className="p-6">
              <form onSubmit={handleBatchSubmit}>
                <div className="mb-4">
                  <label htmlFor="batchFile" className="block text-sm font-medium text-gray-700 mb-1">
                    Upload File with URLs (one URL per line)
                  </label>
                  <input
                    type="file"
                    id="batchFile"
                    ref={fileInputRef}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    accept=".txt,.csv"
                    onChange={handleFileChange}
                    disabled={isBatchSubmitting}
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Upload a text file with one URL per line
                  </p>
                </div>

                <div className="mb-4">
                  <label htmlFor="batchPlatform" className="block text-sm font-medium text-gray-700 mb-1">
                    Platform
                  </label>
                  <select
                    id="batchPlatform"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={batchPlatform}
                    onChange={(e) => setBatchPlatform(e.target.value as Platform | '')}
                    disabled={isBatchSubmitting}
                  >
                    <option value="">Select Platform</option>
                    <option value="youtube">YouTube</option>
                    <option value="twitter">Twitter</option>
                    <option value="instagram">Instagram</option>
                    <option value="tiktok">TikTok</option>
                    <option value="facebook">Facebook</option>
                  </select>
                </div>

                {batchError && (
                  <div className="mb-4 p-3 bg-red-100 text-red-800 rounded-md">
                    {batchError}
                  </div>
                )}

                {batchSuccess && (
                  <div className="mb-4 p-3 bg-green-100 text-green-800 rounded-md">
                    {batchSuccess}
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  disabled={isBatchSubmitting}
                >
                  {isBatchSubmitting ? 'Submitting...' : 'Upload and Download'}
                </button>
              </form>
            </div>
          </div>
        </TabPanel>
      </Box>

      {/* Active and Recent Jobs */}
      <div className="mt-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Download Jobs</h2>
        
        {loadError && (
          <div className="mb-4 p-3 bg-red-100 text-red-800 rounded-md">
            {loadError}
          </div>
        )}
        
        {isLoading ? (
          <div className="text-center py-4">Loading...</div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Active Jobs */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Active Jobs</h3>
              </div>
              <div className="p-6">
                {activeJobs.length === 0 ? (
                  <div className="text-center py-4 text-gray-500">No active jobs</div>
                ) : (
                  <ul className="divide-y divide-gray-200">
                    {activeJobs.map((job) => (
                      <li key={job.id} className="py-4">
                        <div className="flex justify-between">
                          <div>
                            <span className="font-medium">Job ID: {job.id}</span>
                            <div className="text-sm text-gray-500">
                              {job.urls && job.urls.length > 0 ? (
                                <span>URL: {job.urls[0]}{job.urls.length > 1 ? ` (+${job.urls.length - 1} more)` : ''}</span>
                              ) : (
                                <span>No URLs</span>
                              )}
                            </div>
                            <div className="text-sm text-gray-500">
                              Created: {formatDate(job.created_at)}
                            </div>
                          </div>
                          <div>
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(job.status)}`}>
                              {job.status}
                            </span>
                            <div className="text-sm text-gray-500 mt-1">
                              Progress: {job.progress_percentage ? `${Math.round(job.progress_percentage)}%` : 'N/A'}
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            
            {/* Recent Jobs */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Recent Jobs</h3>
              </div>
              <div className="p-6">
                {recentJobs.length === 0 ? (
                  <div className="text-center py-4 text-gray-500">No recent jobs</div>
                ) : (
                  <ul className="divide-y divide-gray-200">
                    {recentJobs.map((job) => (
                      <li key={job.id} className="py-4">
                        <div className="flex justify-between">
                          <div>
                            <span className="font-medium">Job ID: {job.id}</span>
                            <div className="text-sm text-gray-500">
                              {job.urls && job.urls.length > 0 ? (
                                <span>URL: {job.urls[0]}{job.urls.length > 1 ? ` (+${job.urls.length - 1} more)` : ''}</span>
                              ) : (
                                <span>No URLs</span>
                              )}
                            </div>
                            <div className="text-sm text-gray-500">
                              Completed: {job.completed_at ? formatDate(job.completed_at) : 'N/A'}
                            </div>
                          </div>
                          <div>
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(job.status)}`}>
                              {job.status}
                            </span>
                            {job.status === 'completed' && (
                              <div className="text-sm text-right mt-1">
                                <Link to={`/content?job=${job.id}`} className="text-blue-600 hover:text-blue-800">
                                  View Content
                                </Link>
                              </div>
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DownloadCenter; 