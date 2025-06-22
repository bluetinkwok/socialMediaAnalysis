/**
 * Dashboard page component
 */

import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your social media content analysis</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Stats Cards */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Total Content</h3>
          <p className="text-3xl font-bold text-blue-600">0</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Downloads</h3>
          <p className="text-3xl font-bold text-green-600">0</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Platforms</h3>
          <p className="text-3xl font-bold text-purple-600">4</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Analytics</h3>
          <p className="text-3xl font-bold text-orange-600">Ready</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
          <div className="text-gray-500 text-center py-8">
            No recent activity
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button className="w-full text-left p-3 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors">
              <div className="font-medium text-blue-900">Start New Download</div>
              <div className="text-sm text-blue-600">Download content from social media platforms</div>
            </button>
            
            <button className="w-full text-left p-3 bg-green-50 hover:bg-green-100 rounded-md transition-colors">
              <div className="font-medium text-green-900">View Analytics</div>
              <div className="text-sm text-green-600">Analyze content performance and trends</div>
            </button>
            
            <button className="w-full text-left p-3 bg-purple-50 hover:bg-purple-100 rounded-md transition-colors">
              <div className="font-medium text-purple-900">Browse Content</div>
              <div className="text-sm text-purple-600">Explore downloaded content library</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 