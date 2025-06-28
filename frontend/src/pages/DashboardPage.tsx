/**
 * Dashboard page component
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import type { Platform } from '../types';
import useDashboardData from '../hooks/useDashboardData';

// Chart colors
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];
const PLATFORM_COLORS: Record<Platform, string> = {
  youtube: '#FF0000',
  instagram: '#E1306C',
  threads: '#000000',
  rednote: '#FF5733'
};

const DashboardPage: React.FC = () => {
  const { analytics, downloadJobs, topPerformers, trendingHashtags, loading, error } = useDashboardData();

  // Prepare data for platform distribution chart
  const preparePlatformData = () => {
    if (!analytics?.by_platform) return [];
    
    return Object.entries(analytics.by_platform).map(([platform, count]) => ({
      name: platform,
      value: count,
      color: PLATFORM_COLORS[platform as Platform] || '#999'
    }));
  };

  // Prepare data for content type chart
  const prepareContentTypeData = () => {
    if (!analytics?.by_type) return [];
    
    return Object.entries(analytics.by_type).map(([type, count]) => ({
      name: type,
      value: count
    }));
  };

  // Format large numbers
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="spinner h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-lg">
        <h3 className="font-bold mb-2">Error</h3>
        <p>{error}</p>
        <button 
          className="mt-3 bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your social media content analysis</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Total Content</h3>
          <p className="text-3xl font-bold text-blue-600">
            {analytics?.total_content ? formatNumber(analytics.total_content) : '0'}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Downloads</h3>
          <p className="text-3xl font-bold text-green-600">
            {downloadJobs?.length || '0'}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Avg. Engagement</h3>
          <p className="text-3xl font-bold text-purple-600">
            {analytics?.engagement_stats?.average_engagement ? 
              formatNumber(analytics.engagement_stats.average_engagement) : '0'}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Analyzed</h3>
          <p className="text-3xl font-bold text-orange-600">
            {analytics?.analyzed_count ? formatNumber(analytics.analyzed_count) : '0'}
          </p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Platform Distribution Chart */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Content by Platform</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={preparePlatformData()}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  nameKey="name"
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                >
                  {preparePlatformData().map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        {/* Content Type Distribution Chart */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Content by Type</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={prepareContentTypeData()}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#8884d8" name="Count" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Performers */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Top Performers</h3>
          {topPerformers.length > 0 ? (
            <div className="overflow-hidden">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Score
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {topPerformers.map((post) => (
                    <tr key={post.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                          {post.title || 'Untitled'}
                        </div>
                        <div className="text-sm text-gray-500">{post.platform}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {post.performance_score ? post.performance_score.toFixed(1) : 'N/A'}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-4 text-right">
                <Link to="/analytics" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                  View all →
                </Link>
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">
              No top performers data available
            </div>
          )}
        </div>

        {/* Trending Hashtags */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Trending Hashtags</h3>
          {trendingHashtags.length > 0 ? (
            <div className="overflow-hidden">
              <div className="flex flex-wrap gap-2 mb-4">
                {trendingHashtags.slice(0, 10).map((tag, index) => (
                  <div 
                    key={tag.tag} 
                    className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm"
                    style={{ fontSize: `${Math.max(0.8, Math.min(1.4, 0.8 + (tag.count / 10)))}rem` }}
                  >
                    #{tag.tag} <span className="text-blue-500">({tag.count})</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 text-right">
                <Link to="/analytics" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                  View all →
                </Link>
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">
              No trending hashtags data available
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="mt-6 bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Downloads</h3>
        {downloadJobs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progress
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {downloadJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link to={`/downloads/${job.id}`} className="text-blue-600 hover:text-blue-900">
                        {job.id.substring(0, 8)}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                        ${job.status === 'completed' ? 'bg-green-100 text-green-800' : 
                          job.status === 'failed' ? 'bg-red-100 text-red-800' : 
                          'bg-yellow-100 text-yellow-800'}`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className={`h-2.5 rounded-full ${job.status === 'completed' ? 'bg-green-600' : 
                            job.status === 'failed' ? 'bg-red-600' : 'bg-blue-600'}`}
                          style={{ width: `${job.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-500 mt-1">{job.progress}%</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(job.createdAt).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 text-right">
              <Link to="/downloads" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                View all downloads →
              </Link>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 text-center py-8">
            No recent download jobs
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="mt-6 bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/downloads" className="block p-4 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors">
            <div className="font-medium text-blue-900">Start New Download</div>
            <div className="text-sm text-blue-600">Download content from social media platforms</div>
          </Link>
          
          <Link to="/analytics" className="block p-4 bg-green-50 hover:bg-green-100 rounded-md transition-colors">
            <div className="font-medium text-green-900">View Analytics</div>
            <div className="text-sm text-green-600">Analyze content performance and trends</div>
          </Link>
          
          <Link to="/content" className="block p-4 bg-purple-50 hover:bg-purple-100 rounded-md transition-colors">
            <div className="font-medium text-purple-900">Browse Content</div>
            <div className="text-sm text-purple-600">Explore downloaded content library</div>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage; 