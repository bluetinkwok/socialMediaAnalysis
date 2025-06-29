import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import ContentLibrary from '../pages/ContentLibrary';
import apiService from '../services/api';

// Mock the API service
jest.mock('../services/api', () => ({
  getContent: jest.fn(),
  searchContent: jest.fn(),
  deleteContent: jest.fn(),
}));

// Mock window.confirm
global.confirm = jest.fn();

describe('ContentLibrary Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock implementation for getContent
    (apiService.getContent as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 12,
      hasNext: false,
      hasPrev: false
    });
  });

  test('renders content library title', () => {
    render(
      <BrowserRouter>
        <ContentLibrary />
      </BrowserRouter>
    );
    
    expect(screen.getByText('Content Library')).toBeInTheDocument();
    expect(screen.getByText('Browse and manage your downloaded content')).toBeInTheDocument();
  });

  test('shows loading state initially', () => {
    render(
      <BrowserRouter>
        <ContentLibrary />
      </BrowserRouter>
    );
    
    // Check for loading spinner (it's a div with animate-spin class)
    const loadingSpinner = document.querySelector('.animate-spin');
    expect(loadingSpinner).toBeInTheDocument();
  });

  test('displays empty state when no content is available', async () => {
    render(
      <BrowserRouter>
        <ContentLibrary />
      </BrowserRouter>
    );
    
    // Wait for the loading to finish
    await waitFor(() => {
      expect(screen.getByText('No content found')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Download some content to get started')).toBeInTheDocument();
    expect(screen.getByText('Download Content')).toBeInTheDocument();
  });

  test('displays content in grid view', async () => {
    // Mock content data
    const mockContent = [
      {
        id: '1',
        title: 'Test Video',
        description: 'Test description',
        platform: 'youtube',
        type: 'video',
        author: 'Test Author',
        url: 'https://example.com/video',
        createdAt: new Date('2023-01-01'),
        updatedAt: new Date('2023-01-02'),
        hashtags: ['test', 'video'],
        mentions: [],
        engagement: { views: 1000, likes: 100 },
        mediaFiles: [],
        downloadedAt: new Date('2023-01-03'),
        isAnalyzed: true,
        authorId: '123',
        authorAvatar: 'https://example.com/avatar.jpg',
      }
    ];
    
    (apiService.getContent as jest.Mock).mockResolvedValue({
      items: mockContent,
      total: 1,
      page: 1,
      limit: 12,
      hasNext: false,
      hasPrev: false
    });
    
    render(
      <BrowserRouter>
        <ContentLibrary />
      </BrowserRouter>
    );
    
    // Wait for content to load
    await waitFor(() => {
      expect(screen.getByText('Test Video')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Test Author')).toBeInTheDocument();
    expect(screen.getByText('youtube')).toBeInTheDocument();
    expect(screen.getByText('1,000 views')).toBeInTheDocument();
  });

  test('switches between grid and list views', async () => {
    // Mock content data
    const mockContent = [
      {
        id: '1',
        title: 'Test Video',
        description: 'Test description',
        platform: 'youtube',
        type: 'video',
        author: 'Test Author',
        url: 'https://example.com/video',
        createdAt: new Date('2023-01-01'),
        updatedAt: new Date('2023-01-02'),
        hashtags: ['test', 'video'],
        mentions: [],
        engagement: { views: 1000, likes: 100 },
        mediaFiles: [],
        downloadedAt: new Date('2023-01-03'),
        isAnalyzed: true,
        authorId: '123',
        authorAvatar: 'https://example.com/avatar.jpg',
      }
    ];
    
    (apiService.getContent as jest.Mock).mockResolvedValue({
      items: mockContent,
      total: 1,
      page: 1,
      limit: 12,
      hasNext: false,
      hasPrev: false
    });
    
    render(
      <BrowserRouter>
        <ContentLibrary />
      </BrowserRouter>
    );
    
    // Wait for content to load in grid view
    await waitFor(() => {
      expect(screen.getByText('Test Video')).toBeInTheDocument();
    });
    
    // Find and click the list view button
    const listViewButton = document.querySelectorAll('button')[1]; // Second button in the view mode toggle
    userEvent.click(listViewButton);
    
    // Check if table headers are visible (list view)
    await waitFor(() => {
      expect(screen.getByText('Platform')).toBeInTheDocument();
      expect(screen.getByText('Author')).toBeInTheDocument();
      expect(screen.getByText('Date')).toBeInTheDocument();
      expect(screen.getByText('Engagement')).toBeInTheDocument();
    });
  });

  test('filters content by platform', async () => {
    // Mock content data
    const mockContent = [
      {
        id: '1',
        title: 'Test Video',
        platform: 'youtube',
        type: 'video',
        author: 'Test Author',
        url: 'https://example.com/video',
        createdAt: new Date('2023-01-01'),
        updatedAt: new Date('2023-01-02'),
        hashtags: [],
        mentions: [],
        engagement: {},
        mediaFiles: [],
        downloadedAt: new Date('2023-01-03'),
        isAnalyzed: true
      }
    ];
    
    (apiService.getContent as jest.Mock).mockResolvedValue({
      items: mockContent,
      total: 1,
      page: 1,
      limit: 12,
      hasNext: false,
      hasPrev: false
    });
    
    render(
      <BrowserRouter>
        <ContentLibrary />
      </BrowserRouter>
    );
    
    // Wait for content to load
    await waitFor(() => {
      expect(screen.getByText('Test Video')).toBeInTheDocument();
    });
    
    // Click the filter button
    const filterButton = screen.getByText('Filters');
    userEvent.click(filterButton);
    
    // Click on a platform filter (YouTube)
    const youtubeFilter = screen.getByText('Youtube');
    userEvent.click(youtubeFilter);
    
    // Verify that getContent was called with the correct filter
    await waitFor(() => {
      expect(apiService.getContent).toHaveBeenCalledWith(
        1, 
        12, 
        expect.objectContaining({ 
          platform: ['youtube'] 
        })
      );
    });
  });
}); 