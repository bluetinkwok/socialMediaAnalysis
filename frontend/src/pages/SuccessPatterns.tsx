import React from 'react';
import { Container, Typography, Paper } from '@mui/material';
import SuccessPatterns from '../components/SuccessPatterns';
import Layout from '../components/Layout';

const SuccessPatternsPage: React.FC = () => {
  return (
    <Layout>
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Success Patterns
          </Typography>
          <Typography variant="body1" paragraph>
            Explore patterns of success in your social media content. These patterns represent 
            combinations of content attributes and performance metrics that correlate with 
            high-performing posts.
          </Typography>
        </Paper>
        
        <SuccessPatterns height={800} />
      </Container>
    </Layout>
  );
};

export default SuccessPatternsPage; 