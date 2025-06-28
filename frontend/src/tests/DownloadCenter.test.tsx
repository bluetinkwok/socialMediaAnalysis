import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import DownloadCenter from '../pages/DownloadCenter';
import apiService from '../services/api';

// Mock the API service
jest.mock('../services/api', () => ({
  getDownloadJobs: jest.fn(),
  submitDownloadRequest: jest.fn(),
  cancelDownloadJob: jest.fn()
}));

describe('DownloadCenter Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mock implementations
    (apiService.getDownloadJobs as jest.Mock).mockResolvedValue([]);
    (apiService.submitDownloadRequest as jest.Mock).mockResolvedValue({ id: 'test-job-id' });
    (apiService.cancelDownloadJob as jest.Mock).mockResolvedValue({});
  });

  test('renders download forms and job tables', async () => {
    render(
      <BrowserRouter>
        <DownloadCenter />
      </BrowserRouter>
    );

    // Check for main heading
    expect(screen.getByText('Download Center')).toBeInTheDocument();
    
    // Check for single URL form
    expect(screen.getByText('Single URL Download')).toBeInTheDocument();
    expect(screen.getByLabelText('URL')).toBeInTheDocument();
    
    // Check for batch upload form
    expect(screen.getByText('Batch URL Download')).toBeInTheDocument();
    expect(screen.getByLabelText(/Upload File/)).toBeInTheDocument();
    
    // Check for job tables
    expect(screen.getByText('Active Download Jobs')).toBeInTheDocument();
    expect(screen.getByText('Recent Download Jobs')).toBeInTheDocument();
    
    // Wait for jobs to load
    await waitFor(() => {
      expect(apiService.getDownloadJobs).toHaveBeenCalled();
    });
  });

  test('submits single URL download request', async () => {
    render(
      <BrowserRouter>
        <DownloadCenter />
      </BrowserRouter>
    );

    // Fill out the form
    const urlInput = screen.getByLabelText('URL');
    fireEvent.change(urlInput, { target: { value: 'https://www.youtube.com/watch?v=test123' } });
    
    // Submit the form
    const submitButton = screen.getByText('Download');
    fireEvent.click(submitButton);
    
    // Check if API was called with correct data
    await waitFor(() => {
      expect(apiService.submitDownloadRequest).toHaveBeenCalledWith({
        urls: ['https://www.youtube.com/watch?v=test123'],
        platform: 'youtube',
        options: {
          includeComments: true
        }
      });
    });
    
    // Check for success message
    await waitFor(() => {
      expect(screen.getByText(/Download job submitted successfully/)).toBeInTheDocument();
    });
  });

  test('displays active jobs correctly', async () => {
    // Mock active jobs
    const mockJobs = [
      {
        id: 'job-1',
        status: 'in_progress',
        progress: 45,
        totalItems: 10,
        processedItems: 4,
        errors: [],
        createdAt: new Date().toISOString()
      },
      {
        id: 'job-2',
        status: 'pending',
        progress: 0,
        totalItems: 5,
        processedItems: 0,
        errors: [],
        createdAt: new Date().toISOString()
      }
    ];
    
    (apiService.getDownloadJobs as jest.Mock).mockResolvedValue(mockJobs);
    
    render(
      <BrowserRouter>
        <DownloadCenter />
      </BrowserRouter>
    );
    
    // Wait for jobs to load
    await waitFor(() => {
      expect(screen.getByText('job-1')).toBeInTheDocument();
      expect(screen.getByText('job-2')).toBeInTheDocument();
      expect(screen.getByText('in_progress')).toBeInTheDocument();
      expect(screen.getByText('pending')).toBeInTheDocument();
    });
    
    // Check for cancel buttons
    const cancelButtons = screen.getAllByText('Cancel');
    expect(cancelButtons.length).toBe(2);
    
    // Test cancel functionality
    fireEvent.click(cancelButtons[0]);
    await waitFor(() => {
      expect(apiService.cancelDownloadJob).toHaveBeenCalledWith('job-1');
    });
  });

  test('handles form validation for single URL', async () => {
    render(
      <BrowserRouter>
        <DownloadCenter />
      </BrowserRouter>
    );
    
    // Submit without URL
    const submitButton = screen.getByText('Download');
    fireEvent.click(submitButton);
    
    // Check for validation error
    await waitFor(() => {
      expect(screen.getByText('Please enter a URL')).toBeInTheDocument();
    });
    
    // API should not have been called
    expect(apiService.submitDownloadRequest).not.toHaveBeenCalled();
  });

  test('handles API errors gracefully', async () => {
    // Mock API error
    (apiService.getDownloadJobs as jest.Mock).mockRejectedValue(new Error('Network error'));
    
    render(
      <BrowserRouter>
        <DownloadCenter />
      </BrowserRouter>
    );
    
    // Wait for error message
    await waitFor(() => {
      expect(screen.getByText('Failed to load download jobs. Please try again later.')).toBeInTheDocument();
    });
  });
}); 