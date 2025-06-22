/**
 * Content page component
 */

import React from 'react';

const Content: React.FC = () => {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Content</h1>
        <p className="text-gray-600">Browse and manage your downloaded content</p>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Content Library</h3>
        </div>
        <div className="p-6">
          <div className="text-gray-500 text-center py-8">
            No content available. Download some content to get started.
          </div>
        </div>
      </div>
    </div>
  );
};

export default Content; 