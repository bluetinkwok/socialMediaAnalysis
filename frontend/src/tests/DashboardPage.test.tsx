import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import DashboardPage from '../pages/DashboardPage';
import * as dashboardHook from '../hooks/useDashboardData';

// Mock the custom hook
jest.mock('../hooks/useDashboardData');

describe('DashboardPage Component', () => {
  const mockUseDashboardData = dashboardHook.useDashboardData as jest.Mock;

  beforeEach(() => {
    // Reset mock before each test
    jest.clearAllMocks();
  });

  test('renders loading state correctly', () => {
    mockUseDashboardData.mockReturnValue({
      loading: true,
      error: null,
      analytics: null,
      downloadJobs: [],
      topPerformers: [],
      trendingHashtags: []
    });

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Loading dashboard data...')).toBeInTheDocument();
  });

  test('renders error state correctly', () => {
    const errorMessage = 'Failed to load dashboard data';
    mockUseDashboardData.mockReturnValue({
      loading: false,
      error: errorMessage,
      analytics: null,
      downloadJobs: [],
      topPerformers: [],
      trendingHashtags: []
    });

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  test('renders dashboard content when data is loaded', () => {
    mockUseDashboardData.mockReturnValue({
      loading: false,
      error: null,
      analytics: {
        total_content: 120,
        by_platform: {
          youtube: 50,
          instagram: 40,
          threads: 20,
          rednote: 10
        },
        by_type: {
          video: 60,
          image: 40,
          text: 20
        },
        engagement_stats: {
          average_engagement: 1250
        },
        analyzed_count: 100
      },
      downloadJobs: [
        {
          id: 'job123',
          status: 'completed',
          progress: 100,
          createdAt: new Date().toISOString()
        }
      ],
      topPerformers: [
        {
          id: 'post1',
          title: 'Top Performing Post',
          platform: 'youtube',
          performance_score: 95.5
        }
      ],
      trendingHashtags: [
        {
          tag: 'trending',
          count: 15
        }
      ]
    });

    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    // Check for main heading
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    
    // Check for stats
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    
    // Check for top performers
    expect(screen.getByText('Top Performers')).toBeInTheDocument();
    expect(screen.getByText('Top Performing Post')).toBeInTheDocument();
    
    // Check for hashtags
    expect(screen.getByText('Trending Hashtags')).toBeInTheDocument();
    expect(screen.getByText('#trending')).toBeInTheDocument();
    
    // Check for download jobs
    expect(screen.getByText('Recent Downloads')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
  });
}); 