/**
 * Main App component for Social Media Analysis Platform
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider } from './contexts/AppContext';
import Dashboard from './pages/Dashboard';
import Downloads from './pages/Downloads';
import Content from './pages/Content';
import Analytics from './pages/Analytics';
import SuccessPatterns from './pages/SuccessPatterns';
import Layout from './components/Layout';
import './App.css';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/downloads" element={<Downloads />} />
              <Route path="/content" element={<Content />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/success-patterns" element={<SuccessPatterns />} />
              {/* Add more routes as needed */}
            </Routes>
          </Layout>
        </Router>
      </AppProvider>
    </QueryClientProvider>
  );
}

export default App;
