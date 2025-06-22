/**
 * Downloads page component
 */

import React from 'react';

const Downloads: React.FC = () => {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Downloads</h1>
        <p className="text-gray-600">Manage your content download jobs</p>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Download Jobs</h3>
        </div>
        <div className="p-6">
          <div className="text-gray-500 text-center py-8">
            No download jobs yet. Start by adding some URLs to download.
          </div>
        </div>
      </div>
    </div>
  );
};

export default Downloads; 