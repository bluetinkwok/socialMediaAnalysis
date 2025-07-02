/**
 * API service for communicating with the FastAPI backend
 */

import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';
import type { 
  ApiResponse, 
  Content, 
  DownloadRequest, 
  DownloadJob, 
  AnalyticsData,
  PaginatedResponse,
  FilterOptions,
  DownloadJobStatus
} from '../types';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('authToken');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.get('/api/v1/ping');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Content management
  async getContent(
    page: number = 1, 
    limit: number = 20, 
    filters?: FilterOptions
  ): Promise<PaginatedResponse<Content>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });

      if (filters) {
        if (filters.platform?.length) {
          params.append('platforms', filters.platform.join(','));
        }
        if (filters.type?.length) {
          params.append('types', filters.type.join(','));
        }
        if (filters.dateRange) {
          params.append('start_date', filters.dateRange.start.toISOString());
          params.append('end_date', filters.dateRange.end.toISOString());
        }
      }

      const response = await this.client.get(`/api/v1/content?${params}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getContentById(id: string): Promise<Content> {
    try {
      const response = await this.client.get(`/api/v1/content/${id}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async deleteContent(id: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.delete(`/api/v1/content/${id}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Download management
  async submitDownloadRequest(request: DownloadRequest): Promise<DownloadJob> {
    try {
      const response = await this.client.post('/api/v1/downloads', request);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getDownloadJobs(): Promise<DownloadJob[]> {
    try {
      const response = await this.client.get('/api/v1/downloads');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getDownloadJob(id: string): Promise<DownloadJob> {
    try {
      const response = await this.client.get(`/api/v1/downloads/${id}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async cancelDownloadJob(id: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.post(`/api/v1/downloads/${id}/cancel`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getDownloadJobStatus(id: string): Promise<any> {
    try {
      const response = await this.client.get(`/api/v1/downloads/${id}/status`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async retryDownloadJob(id: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.client.post(`/api/v1/downloads/${id}/retry`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Analytics
  async getAnalytics(): Promise<AnalyticsData> {
    try {
      const response = await this.client.get('/api/v1/analytics');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getAnalyticsByPlatform(platform: string): Promise<AnalyticsData> {
    try {
      const response = await this.client.get(`/api/v1/analytics/platform/${platform}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getContentAnalytics(contentId: string): Promise<any> {
    try {
      const response = await this.client.get(`/api/v1/analytics/${contentId}?detailed=true`);
      return response.data.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // File operations
  async downloadFile(contentId: string, fileId: string): Promise<Blob> {
    try {
      const response = await this.client.get(
        `/api/v1/content/${contentId}/files/${fileId}/download`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Search
  async searchContent(query: string, filters?: FilterOptions): Promise<Content[]> {
    try {
      const params = new URLSearchParams({ q: query });
      
      if (filters) {
        if (filters.platform?.length) {
          params.append('platforms', filters.platform.join(','));
        }
        if (filters.type?.length) {
          params.append('types', filters.type.join(','));
        }
      }

      const response = await this.client.get(`/api/v1/search?${params}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Analytics metrics
  async getAnalyticsMetrics(days = 30, platform?: string, contentType?: string) {
    try {
      const response = await this.client.get('/api/v1/analytics/metrics', {
        params: {
          days,
          ...(platform && { platform }),
          ...(contentType && { content_type: contentType })
        }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getTimeSeriesData(days = 30, platform?: string, contentType?: string) {
    try {
      const response = await this.client.get('/api/v1/analytics/time-series', {
        params: {
          days,
          ...(platform && { platform }),
          ...(contentType && { content_type: contentType })
        }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getPlatformDistribution() {
    try {
      const response = await this.client.get('/api/v1/analytics/platform-distribution');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getContentTypeDistribution() {
    try {
      const response = await this.client.get('/api/v1/analytics/content-type-distribution');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Success Patterns
  async getSuccessPatterns(page = 1, limit = 10, filters = {}) {
    try {
      const response = await this.client.get('/api/v1/success-patterns', {
        params: { page, limit, ...filters },
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Recommendations
  async getRecommendations(limit = 5, platform?: string, contentType?: string) {
    try {
      const response = await this.client.get('/api/v1/recommendations', {
        params: {
          limit,
          ...(platform && { platform }),
          ...(contentType && { content_type: contentType })
        }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getRecommendationsByType(type: string, limit = 5) {
    try {
      const response = await this.client.get(`/api/v1/recommendations/type/${type}`, {
        params: { limit }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getRecommendationTypes() {
    try {
      const response = await this.client.get('/api/v1/recommendations/types');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async getPostRecommendations(postId: string) {
    try {
      const response = await this.client.get(`/api/v1/recommendations/post/${postId}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Error handling
  private handleError(error: any): Error {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.message || error.response.data?.error || 'Server error';
      return new Error(`API Error: ${message} (${error.response.status})`);
    } else if (error.request) {
      // Request was made but no response received
      return new Error('Network error: Unable to connect to server');
    } else {
      // Something else happened
      return new Error(`Request error: ${error.message}`);
    }
  }
}

// Create and export a singleton instance
export const apiService = new ApiService();
export default apiService; 