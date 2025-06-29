/**
 * Content Detail View component
 * Displays detailed information about a specific content item
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  ExternalLink, 
  Download, 
  Clock, 
  Calendar, 
  User, 
  Hash, 
  AtSign,
  BarChart2, 
  Eye, 
  ThumbsUp, 
  MessageSquare, 
  Share2,
  Save,
  AlertTriangle
} from 'lucide-react';
import apiService from '../services/api';
import type { Content, MediaFile, Platform } from '../types';

// Platform color mapping
const PLATFORM_COLORS: Record<Platform, string> = {
  youtube: 'bg-red-100 text-red-800',
  instagram: 'bg-purple-100 text-purple-800',
  threads: 'bg-gray-100 text-gray-800',
  rednote: 'bg-orange-100 text-orange-800'
};

// Platform display names
const PLATFORM_NAMES: Record<Platform, string> = {
  youtube: 'YouTube',
  instagram: 'Instagram',
  threads: 'Threads',
  rednote: 'RedNote'
};

const ContentView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [content, setContent] = useState<Content | null>(null);
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'analytics' | 'media'>('overview');

  // Fetch content details
  useEffect(() => {
    const fetchContentDetails = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        const contentData = await apiService.getContentById(id);
        setContent(contentData);
        
        // Also fetch analytics if content is analyzed
        if (contentData.isAnalyzed) {
          try {
            const analyticsData = await apiService.getContentAnalytics(id);
            setAnalytics(analyticsData);
          } catch (err) {
            console.error('Error fetching analytics:', err);
            // Don't set error here, just log it as analytics is optional
          }
        }
        
        setError(null);
      } catch (err) {
        console.error('Error fetching content details:', err);
        setError('Failed to load content details. The item may have been deleted or is unavailable.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchContentDetails();
  }, [id]);

  // Format date
  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Handle go back
  const handleGoBack = () => {
    navigate('/content');
  };

  // Render loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Render error state
  if (error || !content) {
    return (
      <div className="p-6 bg-white rounded-lg shadow-md">
        <div className="flex items-center mb-4">
          <button 
            onClick={handleGoBack}
            className="flex items-center text-blue-600 hover:text-blue-800"
          >
            <ArrowLeft className="h-5 w-5 mr-1" />
            Back to Content Library
          </button>
        </div>
        <div className="text-center py-12">
          <AlertTriangle className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Content Not Found</h2>
          <p className="text-gray-600 mb-6">{error || 'The requested content could not be found.'}</p>
          <button 
            onClick={handleGoBack}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Return to Content Library
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      {/* Header with back button */}
      <div className="flex items-center mb-4">
        <button 
          onClick={handleGoBack}
          className="flex items-center text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="h-5 w-5 mr-1" />
          Back to Content Library
        </button>
      </div>

      {/* Content header with title and platform */}
      <div className="mb-6">
        <div className="flex items-center mb-2">
          <span className={`px-2 py-1 rounded-full text-xs font-medium mr-2 ${PLATFORM_COLORS[content.platform]}`}>
            {PLATFORM_NAMES[content.platform]}
          </span>
          <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded-full text-xs font-medium">
            {content.type.charAt(0).toUpperCase() + content.type.slice(1)}
          </span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{content.title}</h1>
        
        {/* Author and date info */}
        <div className="flex items-center text-gray-600 mb-4">
          <User className="h-4 w-4 mr-1" />
          <span className="mr-4">{content.author}</span>
          <Calendar className="h-4 w-4 mr-1" />
          <span className="mr-4">{formatDate(content.createdAt)}</span>
          <Clock className="h-4 w-4 mr-1" />
          <span>Downloaded {formatDate(content.downloadedAt)}</span>
        </div>
        
        {/* External link */}
        <a 
          href={content.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center text-blue-600 hover:text-blue-800"
        >
          <ExternalLink className="h-4 w-4 mr-1" />
          View Original
        </a>
      </div>

      {/* Tab navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex -mb-px">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2 px-4 border-b-2 font-medium text-sm ${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`py-2 px-4 border-b-2 font-medium text-sm ${
              activeTab === 'analytics'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            disabled={!content.isAnalyzed}
          >
            Analytics
          </button>
          <button
            onClick={() => setActiveTab('media')}
            className={`py-2 px-4 border-b-2 font-medium text-sm ${
              activeTab === 'media'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
            disabled={!content.mediaFiles || content.mediaFiles.length === 0}
          >
            Media Files
          </button>
        </nav>
      </div>

      {/* Tab content */}
      <div className="mb-6">
        {/* Overview tab */}
        {activeTab === 'overview' && (
          <div>
            {/* Description */}
            {content.description && (
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-2">Description</h2>
                <p className="text-gray-700 whitespace-pre-line">{content.description}</p>
              </div>
            )}
            
            {/* Engagement metrics */}
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-2">Engagement</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {content.engagement.views !== undefined && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-center mb-1">
                      <Eye className="h-4 w-4 text-gray-500 mr-1" />
                      <span className="text-sm text-gray-500">Views</span>
                    </div>
                    <div className="text-xl font-semibold">
                      {content.engagement.views.toLocaleString()}
                    </div>
                  </div>
                )}
                
                {content.engagement.likes !== undefined && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-center mb-1">
                      <ThumbsUp className="h-4 w-4 text-gray-500 mr-1" />
                      <span className="text-sm text-gray-500">Likes</span>
                    </div>
                    <div className="text-xl font-semibold">
                      {content.engagement.likes.toLocaleString()}
                    </div>
                  </div>
                )}
                
                {content.engagement.comments !== undefined && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-center mb-1">
                      <MessageSquare className="h-4 w-4 text-gray-500 mr-1" />
                      <span className="text-sm text-gray-500">Comments</span>
                    </div>
                    <div className="text-xl font-semibold">
                      {content.engagement.comments.toLocaleString()}
                    </div>
                  </div>
                )}
                
                {content.engagement.shares !== undefined && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-center mb-1">
                      <Share2 className="h-4 w-4 text-gray-500 mr-1" />
                      <span className="text-sm text-gray-500">Shares</span>
                    </div>
                    <div className="text-xl font-semibold">
                      {content.engagement.shares.toLocaleString()}
                    </div>
                  </div>
                )}
                
                {content.engagement.saves !== undefined && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-center mb-1">
                      <Save className="h-4 w-4 text-gray-500 mr-1" />
                      <span className="text-sm text-gray-500">Saves</span>
                    </div>
                    <div className="text-xl font-semibold">
                      {content.engagement.saves.toLocaleString()}
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* Tags and mentions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Hashtags */}
              {content.hashtags && content.hashtags.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-800 mb-2">Hashtags</h2>
                  <div className="flex flex-wrap gap-2">
                    {content.hashtags.map((tag, index) => (
                      <span 
                        key={index} 
                        className="bg-blue-50 text-blue-700 px-2 py-1 rounded-full text-sm flex items-center"
                      >
                        <Hash className="h-3 w-3 mr-1" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Mentions */}
              {content.mentions && content.mentions.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-800 mb-2">Mentions</h2>
                  <div className="flex flex-wrap gap-2">
                    {content.mentions.map((mention, index) => (
                      <span 
                        key={index} 
                        className="bg-green-50 text-green-700 px-2 py-1 rounded-full text-sm flex items-center"
                      >
                        <AtSign className="h-3 w-3 mr-1" />
                        {mention}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Analytics tab */}
        {activeTab === 'analytics' && (
          <div>
            {content.isAnalyzed && analytics ? (
              <>
                {/* Performance scores */}
                <div className="mb-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-2">Performance Scores</h2>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {analytics.advanced_metrics && (
                      <>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-500 mb-1">Virality Score</div>
                          <div className="text-xl font-semibold">
                            {analytics.advanced_metrics.virality_score.toFixed(1)}
                          </div>
                        </div>
                        
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-500 mb-1">Trend Score</div>
                          <div className="text-xl font-semibold">
                            {analytics.advanced_metrics.trend_score.toFixed(1)}
                          </div>
                        </div>
                        
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-500 mb-1">Content Quality</div>
                          <div className="text-xl font-semibold">
                            {analytics.advanced_metrics.content_quality_score.toFixed(1)}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
                
                {/* Success patterns */}
                {analytics.metadata && analytics.metadata.success_patterns && (
                  <div className="mb-6">
                    <h2 className="text-lg font-semibold text-gray-800 mb-2">Identified Success Patterns</h2>
                    <ul className="list-disc pl-5 space-y-1">
                      {analytics.metadata.success_patterns.map((pattern: string, index: number) => (
                        <li key={index} className="text-gray-700">{pattern}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {/* Ranking information */}
                {analytics.ranking && (
                  <div className="mb-6">
                    <h2 className="text-lg font-semibold text-gray-800 mb-2">Content Ranking</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-500 mb-1">Platform Rank</div>
                        <div className="text-xl font-semibold">
                          #{analytics.ranking.platform_rank}
                        </div>
                      </div>
                      
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-500 mb-1">Category Rank</div>
                        <div className="text-xl font-semibold">
                          #{analytics.ranking.category_rank}
                        </div>
                      </div>
                      
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-500 mb-1">Overall Rank</div>
                        <div className="text-xl font-semibold">
                          #{analytics.ranking.overall_rank}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12">
                <BarChart2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-1">Analytics Not Available</h3>
                <p className="text-gray-500">
                  This content has not been analyzed yet or analytics data is unavailable.
                </p>
              </div>
            )}
          </div>
        )}
        
        {/* Media Files tab */}
        {activeTab === 'media' && (
          <div>
            {content.mediaFiles && content.mediaFiles.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {content.mediaFiles.map((file: MediaFile) => (
                  <div key={file.id} className="border rounded-lg overflow-hidden">
                    {file.mimetype.startsWith('image/') ? (
                      <div className="aspect-video bg-gray-100 flex items-center justify-center">
                        <img 
                          src={`/api/v1/media/${file.filepath}`} 
                          alt={file.filename}
                          className="max-h-full max-w-full object-contain"
                        />
                      </div>
                    ) : file.mimetype.startsWith('video/') ? (
                      <div className="aspect-video bg-black">
                        <video 
                          src={`/api/v1/media/${file.filepath}`}
                          controls
                          className="w-full h-full"
                        ></video>
                      </div>
                    ) : (
                      <div className="aspect-video bg-gray-100 flex items-center justify-center">
                        <div className="text-gray-500">
                          {file.mimetype.split('/')[0]} file
                        </div>
                      </div>
                    )}
                    
                    <div className="p-3">
                      <div className="text-sm font-medium text-gray-900 truncate mb-1">
                        {file.filename}
                      </div>
                      <div className="text-xs text-gray-500 mb-2">
                        {(file.filesize / 1024 / 1024).toFixed(2)} MB • {file.mimetype}
                      </div>
                      <a 
                        href={`/api/v1/media/${file.filepath}?download=true`}
                        download={file.filename}
                        className="flex items-center text-blue-600 hover:text-blue-800 text-sm"
                      >
                        <Download className="h-4 w-4 mr-1" />
                        Download
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Download className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-1">No Media Files</h3>
                <p className="text-gray-500">
                  This content doesn't have any associated media files.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentView; 