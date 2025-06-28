import { useState, useEffect } from 'react';
import apiService from '../services/api';

export interface DashboardData {
  analytics: any;
  downloadJobs: any[];
  topPerformers: any[];
  trendingHashtags: any[];
  loading: boolean;
  error: string | null;
}

export const useDashboardData = (): DashboardData => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [downloadJobs, setDownloadJobs] = useState<any[]>([]);
  const [topPerformers, setTopPerformers] = useState<any[]>([]);
  const [trendingHashtags, setTrendingHashtags] = useState<any[]>([]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Fetch analytics overview
        const analyticsOverview = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/analytics/summary/overview`);
        const analyticsData = await analyticsOverview.json();
        
        // Fetch download jobs
        const jobs = await apiService.getDownloadJobs();
        
        // Fetch top performers across platforms
        const topPerformersResponse = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/analytics/top-performers/youtube?limit=5`);
        const topPerformersData = await topPerformersResponse.json();
        
        // Fetch trending hashtags
        const hashtagsResponse = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/analytics/trends/hashtags`);
        const hashtagsData = await hashtagsResponse.json();
        
        // Set state with fetched data
        setAnalytics(analyticsData.data);
        setDownloadJobs(jobs.slice(0, 5)); // Only show latest 5 jobs
        setTopPerformers(topPerformersData.data.posts || []);
        setTrendingHashtags(hashtagsData.data.hashtags || []);
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return {
    analytics,
    downloadJobs,
    topPerformers,
    trendingHashtags,
    loading,
    error
  };
};

export default useDashboardData; 