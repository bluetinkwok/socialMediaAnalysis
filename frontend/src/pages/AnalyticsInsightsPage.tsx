import React from 'react';
import { Container, Typography, Paper } from '@mui/material';
import AnalyticsInsights from '../components/AnalyticsInsights';

const AnalyticsInsightsPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Analytics & Insights
        </Typography>
        <Typography variant="body1" paragraph>
          Explore your content performance analytics, identify success patterns, and get actionable 
          recommendations to improve your social media strategy. This dashboard provides a comprehensive 
          view of your content performance across all platforms.
        </Typography>
      </Paper>
      
      <AnalyticsInsights height={800} />
    </Container>
  );
};

export default AnalyticsInsightsPage;
