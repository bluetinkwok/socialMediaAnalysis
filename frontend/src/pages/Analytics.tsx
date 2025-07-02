/**
 * Analytics page component
 */

import React from 'react';
import AnalyticsInsights from '../components/AnalyticsInsights';

const Analytics: React.FC = () => {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analytics & Insights</h1>
        <p className="text-gray-600">Analyze content performance, patterns, and get actionable recommendations</p>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Performance Analytics</h3>
        </div>
        <div className="p-6">
          <AnalyticsInsights height={800} />
        </div>
      </div>
    </div>
  );
};

export default Analytics; 