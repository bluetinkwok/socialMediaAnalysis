/**
 * Progress Statistics component for displaying job statistics
 */

import React from 'react';

interface ProgressStatsProps {
  stats: {
    total: number;
    active: number;
    completed: number;
    failed: number;
  };
  className?: string;
}

const ProgressStats: React.FC<ProgressStatsProps> = ({ stats, className = '' }) => {
  // Calculate completion rate
  const completionRate = stats.total > 0 ? (stats.completed / stats.total) * 100 : 0;
  const failureRate = stats.total > 0 ? (stats.failed / stats.total) * 100 : 0;

  const statCards = [
    {
      label: 'Total Jobs',
      value: stats.total,
      color: 'blue',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-700',
      borderColor: 'border-blue-200',
    },
    {
      label: 'Active',
      value: stats.active,
      color: 'yellow',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-700',
      borderColor: 'border-yellow-200',
    },
    {
      label: 'Completed',
      value: stats.completed,
      color: 'green',
      bgColor: 'bg-green-50',
      textColor: 'text-green-700',
      borderColor: 'border-green-200',
      subtitle: `${completionRate.toFixed(1)}% success rate`,
    },
    {
      label: 'Failed',
      value: stats.failed,
      color: 'red',
      bgColor: 'bg-red-50',
      textColor: 'text-red-700',
      borderColor: 'border-red-200',
      subtitle: `${failureRate.toFixed(1)}% failure rate`,
    },
  ];

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      {statCards.map((stat, index) => (
        <div
          key={index}
          className={`
            p-4 rounded-lg border-2 transition-all duration-200
            ${stat.bgColor} ${stat.borderColor}
            hover:shadow-md
          `}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.textColor}`}>
                {stat.value}
              </p>
              {stat.subtitle && (
                <p className="text-xs text-gray-500 mt-1">{stat.subtitle}</p>
              )}
            </div>
            
            {/* Icon based on stat type */}
            <div className={`text-2xl ${stat.textColor}`}>
              {stat.label === 'Total Jobs' && '📊'}
              {stat.label === 'Active' && '⚡'}
              {stat.label === 'Completed' && '✅'}
              {stat.label === 'Failed' && '❌'}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ProgressStats; 