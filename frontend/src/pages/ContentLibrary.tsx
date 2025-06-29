/**
 * Content Library page component
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, ChevronLeft, ChevronRight, ExternalLink, Trash2, Download } from 'lucide-react';
import apiService from '../services/api';
import type { Content, Platform, ContentType, FilterOptions, PaginatedResponse } from '../types';

// Platform color mapping
const PLATFORM_COLORS: Record<Platform, string> = {
  youtube: 'bg-red-100 text-red-800',
  instagram: 'bg-purple-100 text-purple-800',
  threads: 'bg-gray-100 text-gray-800',
  rednote: 'bg-orange-100 text-orange-800'
};

// Content type icon mapping
const CONTENT_TYPE_ICONS: Record<ContentType, React.ReactNode> = {
  video: <span className="text-red-500">📹</span>,
  image: <span className="text-blue-500">🖼️</span>,
  text: <span className="text-green-500">📝</span>,
  mixed: <span className="text-purple-500">📦</span>
};

const ContentLibrary: React.FC = () => {
  // State for content data
  const [content, setContent] = useState<Content[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [totalItems, setTotalItems] = useState<number>(0);
  
  // State for pagination
  const [page, setPage] = useState<number>(1);
  const [limit, setLimit] = useState<number>(12);
  
  // State for search and filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState<string>('');
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [filters, setFilters] = useState<FilterOptions>({
    platform: [],
    type: [],
    dateRange: undefined
  });
  
  // State for view mode
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  
  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 500);
    
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // Fetch content when page, limit, search query, or filters change
  useEffect(() => {
    fetchContent();
  }, [page, limit, debouncedSearchQuery, filters]);
  
  // Function to fetch content from API
  const fetchContent = useCallback(async () => {
    try {
      setLoading(true);
      
      let data: PaginatedResponse<Content>;
      
      if (debouncedSearchQuery) {
        // Use search endpoint if there's a query
        const searchResults = await apiService.searchContent(debouncedSearchQuery, filters);
        data = {
          items: searchResults,
          total: searchResults.length,
          page: 1,
          limit: searchResults.length,
          hasNext: false,
          hasPrev: false
        };
      } else {
        // Otherwise use regular content endpoint with filters
        data = await apiService.getContent(page, limit, filters);
      }
      
      setContent(data.items);
      setTotalItems(data.total);
      setError(null);
    } catch (err) {
      console.error('Error fetching content:', err);
      setError('Failed to load content. Please try again later.');
      setContent([]);
    } finally {
      setLoading(false);
    }
  }, [page, limit, debouncedSearchQuery, filters]);
  
  // Function to handle platform filter change
  const handlePlatformFilterChange = (platform: Platform) => {
    setFilters(prev => {
      const platforms = prev.platform || [];
      
      if (platforms.includes(platform)) {
        // Remove platform if already selected
        return {
          ...prev,
          platform: platforms.filter(p => p !== platform)
        };
      } else {
        // Add platform if not selected
        return {
          ...prev,
          platform: [...platforms, platform]
        };
      }
    });
    
    // Reset to first page when changing filters
    setPage(1);
  };
  
  // Function to handle content type filter change
  const handleTypeFilterChange = (type: ContentType) => {
    setFilters(prev => {
      const types = prev.type || [];
      
      if (types.includes(type)) {
        // Remove type if already selected
        return {
          ...prev,
          type: types.filter(t => t !== type)
        };
      } else {
        // Add type if not selected
        return {
          ...prev,
          type: [...types, type]
        };
      }
    });
    
    // Reset to first page when changing filters
    setPage(1);
  };
  
  // Function to clear all filters
  const clearFilters = () => {
    setFilters({
      platform: [],
      type: [],
      dateRange: undefined
    });
    setSearchQuery('');
    setDebouncedSearchQuery('');
    setPage(1);
  };
  
  // Function to handle content deletion
  const handleDeleteContent = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this content?')) {
      return;
    }
    
    try {
      await apiService.deleteContent(id);
      // Refresh content list
      fetchContent();
    } catch (err) {
      console.error('Error deleting content:', err);
      alert('Failed to delete content. Please try again.');
    }
  };
  
  // Function to format date
  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString();
  };
  
  // Calculate pagination info
  const totalPages = Math.ceil(totalItems / limit);
  const startItem = (page - 1) * limit + 1;
  const endItem = Math.min(page * limit, totalItems);
  
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Content Library</h1>
        <p className="text-gray-600">Browse and manage your downloaded content</p>
      </div>
      
      {/* Search and filters */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-4 border-b border-gray-200">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Search bar */}
            <div className="relative flex-grow max-w-lg">
              <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <Search className="w-5 h-5 text-gray-400" />
              </div>
              <input
                type="text"
                className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg block w-full pl-10 p-2.5 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Search by title, description, or hashtags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            {/* View mode and filter toggles */}
            <div className="flex items-center space-x-4">
              {/* View mode toggle */}
              <div className="flex items-center space-x-2">
                <button 
                  className={`p-2 rounded ${viewMode === 'grid' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}
                  onClick={() => setViewMode('grid')}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                </button>
                <button 
                  className={`p-2 rounded ${viewMode === 'list' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}
                  onClick={() => setViewMode('list')}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
              </div>
              
              {/* Filter toggle */}
              <button 
                className={`flex items-center space-x-1 px-3 py-2 rounded ${showFilters ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="h-5 w-5" />
                <span>Filters</span>
                {(filters.platform?.length || filters.type?.length) ? (
                  <span className="inline-flex items-center justify-center w-5 h-5 ml-1 text-xs font-semibold text-white bg-blue-500 rounded-full">
                    {(filters.platform?.length || 0) + (filters.type?.length || 0)}
                  </span>
                ) : null}
              </button>
            </div>
          </div>
          
          {/* Filter options */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Platform filters */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Platform</h4>
                  <div className="flex flex-wrap gap-2">
                    {(['youtube', 'instagram', 'threads', 'rednote'] as Platform[]).map((platform) => (
                      <button
                        key={platform}
                        className={`px-3 py-1 rounded-full text-sm ${
                          filters.platform?.includes(platform)
                            ? PLATFORM_COLORS[platform]
                            : 'bg-gray-100 text-gray-800'
                        }`}
                        onClick={() => handlePlatformFilterChange(platform)}
                      >
                        {platform.charAt(0).toUpperCase() + platform.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Content type filters */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Content Type</h4>
                  <div className="flex flex-wrap gap-2">
                    {(['video', 'image', 'text', 'mixed'] as ContentType[]).map((type) => (
                      <button
                        key={type}
                        className={`px-3 py-1 rounded-full text-sm ${
                          filters.type?.includes(type)
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                        onClick={() => handleTypeFilterChange(type)}
                      >
                        {CONTENT_TYPE_ICONS[type]} {type.charAt(0).toUpperCase() + type.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              
              {/* Clear filters button */}
              {(filters.platform?.length || filters.type?.length || searchQuery) && (
                <div className="mt-4 flex justify-end">
                  <button
                    className="text-sm text-blue-600 hover:text-blue-800"
                    onClick={clearFilters}
                  >
                    Clear all filters
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Content display */}
        <div className="p-6">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
              <span className="block sm:inline">{error}</span>
            </div>
          ) : content.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 text-5xl mb-4">📚</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No content found</h3>
              <p className="text-gray-500 mb-6">
                {searchQuery || filters.platform?.length || filters.type?.length
                  ? 'Try adjusting your search or filters'
                  : 'Download some content to get started'}
              </p>
              <Link
                to="/download-center"
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                <Download className="h-5 w-5 mr-2" />
                Download Content
              </Link>
            </div>
          ) : (
            <>
              {/* Grid view */}
              {viewMode === 'grid' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {content.map((item) => (
                    <div key={item.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                      {/* Thumbnail */}
                      <Link to={`/content/${item.id}`} className="block">
                        <div className="relative h-40 bg-gray-100">
                          {item.thumbnail ? (
                            <img
                              src={item.thumbnail}
                              alt={item.title}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400">
                              {CONTENT_TYPE_ICONS[item.type]}
                            </div>
                          )}
                          <div className="absolute top-2 right-2">
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${PLATFORM_COLORS[item.platform]}`}>
                              {item.platform}
                            </span>
                          </div>
                        </div>
                      </Link>
                      
                      {/* Content info */}
                      <div className="p-4">
                        <Link to={`/content/${item.id}`} className="block hover:text-blue-600">
                          <h3 className="text-sm font-medium text-gray-900 truncate mb-1">
                            {item.title || 'Untitled'}
                          </h3>
                        </Link>
                        <p className="text-xs text-gray-500 mb-2">
                          {item.author} • {formatDate(item.createdAt)}
                        </p>
                        
                        {/* Hashtags */}
                        {item.hashtags?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-3">
                            {item.hashtags.slice(0, 3).map((tag) => (
                              <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                                #{tag}
                              </span>
                            ))}
                            {item.hashtags.length > 3 && (
                              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                                +{item.hashtags.length - 3}
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Engagement metrics */}
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <div className="flex space-x-2">
                            {item.engagement.views !== undefined && (
                              <span>{item.engagement.views.toLocaleString()} views</span>
                            )}
                            {item.engagement.likes !== undefined && (
                              <span>{item.engagement.likes.toLocaleString()} likes</span>
                            )}
                          </div>
                          
                          {/* Actions */}
                          <div className="flex space-x-2">
                            <button
                              onClick={() => window.open(item.url, '_blank')}
                              className="text-gray-400 hover:text-blue-500"
                              title="Open original"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteContent(item.id)}
                              className="text-gray-400 hover:text-red-500"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* List view */}
              {viewMode === 'list' && (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Content
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Platform
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Type
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Author
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Engagement
                        </th>
                        <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {content.map((item) => (
                        <tr key={item.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <Link to={`/content/${item.id}`} className="flex-shrink-0 h-10 w-10 bg-gray-100 rounded">
                                {item.thumbnail ? (
                                  <img
                                    src={item.thumbnail}
                                    alt={item.title}
                                    className="h-10 w-10 rounded object-cover"
                                  />
                                ) : (
                                  <div className="h-10 w-10 rounded flex items-center justify-center">
                                    {CONTENT_TYPE_ICONS[item.type]}
                                  </div>
                                )}
                              </Link>
                              <div className="ml-4">
                                <Link to={`/content/${item.id}`} className="block">
                                  <div className="text-sm font-medium text-gray-900 truncate max-w-xs hover:text-blue-600">
                                    {item.title || 'Untitled'}
                                  </div>
                                </Link>
                                <div className="text-xs text-gray-500 truncate max-w-xs">
                                  {item.hashtags?.slice(0, 3).map(tag => `#${tag}`).join(' ')}
                                  {item.hashtags?.length > 3 ? ` +${item.hashtags.length - 3}` : ''}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${PLATFORM_COLORS[item.platform]}`}>
                              {item.platform}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">
                              {CONTENT_TYPE_ICONS[item.type]} {item.type}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {item.author}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(item.createdAt)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {item.engagement.views !== undefined && (
                              <span className="mr-2">{item.engagement.views.toLocaleString()} views</span>
                            )}
                            {item.engagement.likes !== undefined && (
                              <span>{item.engagement.likes.toLocaleString()} likes</span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => window.open(item.url, '_blank')}
                              className="text-blue-600 hover:text-blue-900 mr-3"
                              title="Open original"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteContent(item.id)}
                              className="text-red-600 hover:text-red-900"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3 sm:px-6 mt-6">
                  <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm text-gray-700">
                        Showing <span className="font-medium">{startItem}</span> to <span className="font-medium">{endItem}</span> of{' '}
                        <span className="font-medium">{totalItems}</span> results
                      </p>
                    </div>
                    <div>
                      <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                        <button
                          onClick={() => setPage(Math.max(1, page - 1))}
                          disabled={page === 1}
                          className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium ${
                            page === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'
                          }`}
                        >
                          <span className="sr-only">Previous</span>
                          <ChevronLeft className="h-5 w-5" />
                        </button>
                        
                        {/* Page numbers */}
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum;
                          
                          // Logic to show pages around current page
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (page <= 3) {
                            pageNum = i + 1;
                          } else if (page >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = page - 2 + i;
                          }
                          
                          return (
                            <button
                              key={pageNum}
                              onClick={() => setPage(pageNum)}
                              className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                                page === pageNum
                                  ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                                  : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                              }`}
                            >
                              {pageNum}
                            </button>
                          );
                        })}
                        
                        <button
                          onClick={() => setPage(Math.min(totalPages, page + 1))}
                          disabled={page === totalPages}
                          className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium ${
                            page === totalPages ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'
                          }`}
                        >
                          <span className="sr-only">Next</span>
                          <ChevronRight className="h-5 w-5" />
                        </button>
                      </nav>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ContentLibrary; 