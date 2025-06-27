/**
 * TypeScript type definitions for Social Media Analysis Platform
 */

// Platform types
export type Platform = 'youtube' | 'instagram' | 'threads' | 'rednote';

export type ContentType = 'video' | 'image' | 'text' | 'mixed';

// Content data structures
export interface BaseContent {
  id: string;
  platform: Platform;
  type: ContentType;
  title: string;
  description?: string;
  url: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface MediaFile {
  id: string;
  filename: string;
  filepath: string;
  filesize: number;
  mimetype: string;
  contentId: string;
}

export interface EngagementMetrics {
  views?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  saves?: number;
  retweets?: number; // For Twitter-like platforms
}

export interface Content extends BaseContent {
  author: string;
  authorId?: string;
  authorAvatar?: string;
  thumbnail?: string;
  duration?: number; // For videos in seconds
  hashtags: string[];
  mentions: string[];
  engagement: EngagementMetrics;
  mediaFiles: MediaFile[];
  downloadedAt: Date;
  isAnalyzed: boolean;
}

// Download request types
export interface DownloadRequest {
  urls: string[];
  platform: Platform;
  options?: DownloadOptions;
}

export interface DownloadOptions {
  includeComments?: boolean;
  maxQuality?: 'low' | 'medium' | 'high';
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export interface DownloadJob {
  id: string;
  status: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  totalItems: number;
  processedItems: number;
  errors: string[];
  createdAt: Date;
  completedAt?: Date;
}

export interface DownloadJobProgress {
  percentage: number;
  processed_items: number;
  total_items: number;
  current_step?: string;
}

export interface DownloadJobTiming {
  started_at: string;
  elapsed_time: number;
  estimated_completion?: string;
  processing_rate?: number;
}

export interface DownloadJobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed';
  progress: DownloadJobProgress;
  timing: DownloadJobTiming;
  errors: any[];
  metadata?: any;
  urls?: string[];
  platform?: Platform;
}

// Analytics types
export interface AnalyticsData {
  totalContent: number;
  byPlatform: Record<Platform, number>;
  byType: Record<ContentType, number>;
  engagementStats: {
    averageViews: number;
    averageLikes: number;
    averageComments: number;
    totalEngagement: number;
  };
  topPerformers: Content[];
  trendingHashtags: Array<{
    tag: string;
    count: number;
    platforms: Platform[];
  }>;
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// UI component types
export interface TableColumn<T> {
  key: keyof T;
  title: string;
  sortable?: boolean;
  render?: (value: any, record: T) => React.ReactNode;
}

export interface FilterOptions {
  platform?: Platform[];
  type?: ContentType[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  engagement?: {
    minViews?: number;
    minLikes?: number;
  };
}

// Theme and UI types
export interface Theme {
  mode: 'light' | 'dark';
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    border: string;
    error: string;
    warning: string;
    success: string;
  };
}

// User and authentication types (for future use)
export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: 'admin' | 'user';
  createdAt: Date;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
} 