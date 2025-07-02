import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { AnalyticsData } from '../types';

interface UseDashboardDataOptions {
  refreshInterval?: number;
}

export function useDashboardData(options: UseDashboardDataOptions = {}) {
  const { refreshInterval = 0 } = options;
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const analyticsData = await apiService.getAnalytics();
        setData(analyticsData);
        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load analytics data');
      } finally {
        setLoading(false);
      }
    };

    // Fetch data immediately
    fetchData();

    // Set up interval if specified
    let intervalId: number | undefined;
    if (refreshInterval > 0) {
      intervalId = window.setInterval(fetchData, refreshInterval);
    }

    // Clean up interval on unmount
    return () => {
      if (intervalId) {
        window.clearInterval(intervalId);
      }
    };
  }, [refreshInterval]);

  return { data, loading, error };
}

export default useDashboardData; 