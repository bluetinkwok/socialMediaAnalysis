import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, Grid, Chip, CircularProgress, Alert, 
  Tabs, Tab, Select, MenuItem, FormControl, InputLabel, SelectChangeEvent } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';

interface SuccessPattern {
  name: string;
  description: string;
  confidence: number;
  frequency: number;
  platform?: string;
  content_type?: string;
}

interface PatternsByPlatform {
  [platform: string]: SuccessPattern[];
}

interface PatternsByContentType {
  [contentType: string]: SuccessPattern[];
}

interface SuccessPatternsProps {
  postId?: number;
  showFilters?: boolean;
  height?: string | number;
}

const SuccessPatterns: React.FC<SuccessPatternsProps> = ({ 
  postId, 
  showFilters = true,
  height = 600
}) => {
  const theme = useTheme();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState<number>(0);
  const [patterns, setPatterns] = useState<SuccessPattern[]>([]);
  const [patternsByPlatform, setPatternsByPlatform] = useState<PatternsByPlatform>({});
  const [patternsByContentType, setPatternsByContentType] = useState<PatternsByContentType>({});
  const [platform, setPlatform] = useState<string>('all');
  const [contentType, setContentType] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<number>(30);

  // Fetch data based on the selected tab
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        let url = '';
        let params: any = {};
        
        // If a specific post ID is provided, only get patterns for that post
        if (postId) {
          url = `/api/v1/success-patterns/post/${postId}`;
        } else {
          // Otherwise, use the appropriate endpoint based on the selected tab
          switch (tabValue) {
            case 0: // All patterns
              url = '/api/v1/success-patterns';
              params = { 
                days: timeRange,
                ...(platform !== 'all' && { platform }),
                ...(contentType !== 'all' && { content_type: contentType })
              };
              break;
            case 1: // Top patterns
              url = '/api/v1/success-patterns/top';
              params = { days: timeRange, limit: 10 };
              break;
            case 2: // By platform
              url = '/api/v1/success-patterns/by-platform';
              params = { days: timeRange };
              break;
            case 3: // By content type
              url = '/api/v1/success-patterns/by-content-type';
              params = { days: timeRange };
              break;
            default:
              url = '/api/v1/success-patterns';
              params = { days: timeRange };
          }
        }
        
        const response = await axios.get(url, { params });
        
        if (response.data.success) {
          if (tabValue === 0 || postId) {
            setPatterns(response.data.patterns || []);
          } else if (tabValue === 1) {
            setPatterns(response.data.patterns || []);
          } else if (tabValue === 2) {
            setPatternsByPlatform(response.data.patterns_by_platform || {});
          } else if (tabValue === 3) {
            setPatternsByContentType(response.data.patterns_by_content_type || {});
          }
        } else {
          setError('Failed to load success patterns');
        }
      } catch (err) {
        console.error('Error fetching success patterns:', err);
        setError('Error loading success patterns');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [tabValue, postId, platform, contentType, timeRange]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handlePlatformChange = (event: SelectChangeEvent) => {
    setPlatform(event.target.value);
  };

  const handleContentTypeChange = (event: SelectChangeEvent) => {
    setContentType(event.target.value);
  };

  const handleTimeRangeChange = (event: SelectChangeEvent) => {
    setTimeRange(Number(event.target.value));
  };

  // Render pattern card
  const renderPatternCard = (pattern: SuccessPattern) => (
    <Card 
      key={pattern.name} 
      sx={{ 
        mb: 2, 
        borderLeft: `4px solid ${theme.palette.primary.main}`,
        boxShadow: 2
      }}
    >
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6" component="div">
            {pattern.name}
          </Typography>
          <Chip 
            label={`${(pattern.confidence * 100).toFixed(0)}% confidence`}
            color={pattern.confidence > 0.8 ? "success" : pattern.confidence > 0.6 ? "primary" : "default"}
          />
        </Box>
        
        <Typography variant="body2" color="text.secondary" mb={2}>
          {pattern.description}
        </Typography>
        
        <Box display="flex" flexWrap="wrap" gap={1}>
          {pattern.platform && (
            <Chip size="small" label={`Platform: ${pattern.platform}`} />
          )}
          {pattern.content_type && (
            <Chip size="small" label={`Type: ${pattern.content_type}`} />
          )}
          {pattern.frequency && (
            <Chip size="small" label={`Frequency: ${pattern.frequency}`} />
          )}
        </Box>
      </CardContent>
    </Card>
  );

  // Render chart for patterns by platform/content type
  const renderChart = (data: any) => {
    const chartData = Object.keys(data).map(key => ({
      name: key,
      count: data[key].length
    }));

    return (
      <Box sx={{ width: '100%', height: 400 }}>
        <ResponsiveContainer>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" name="Number of Patterns" fill={theme.palette.primary.main} />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    );
  };

  // Render filters
  const renderFilters = () => {
    if (!showFilters || postId) return null;
    
    return (
      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        {tabValue === 0 && (
          <>
            <FormControl sx={{ minWidth: 150 }}>
              <InputLabel>Platform</InputLabel>
              <Select
                value={platform}
                label="Platform"
                onChange={handlePlatformChange}
                size="small"
              >
                <MenuItem value="all">All Platforms</MenuItem>
                <MenuItem value="youtube">YouTube</MenuItem>
                <MenuItem value="instagram">Instagram</MenuItem>
                <MenuItem value="tiktok">TikTok</MenuItem>
                <MenuItem value="threads">Threads</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl sx={{ minWidth: 150 }}>
              <InputLabel>Content Type</InputLabel>
              <Select
                value={contentType}
                label="Content Type"
                onChange={handleContentTypeChange}
                size="small"
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="video">Video</MenuItem>
                <MenuItem value="image">Image</MenuItem>
                <MenuItem value="text">Text</MenuItem>
                <MenuItem value="carousel">Carousel</MenuItem>
              </Select>
            </FormControl>
          </>
        )}
        
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={timeRange.toString()}
            label="Time Range"
            onChange={handleTimeRangeChange}
            size="small"
          >
            <MenuItem value="7">Last 7 days</MenuItem>
            <MenuItem value="30">Last 30 days</MenuItem>
            <MenuItem value="90">Last 90 days</MenuItem>
            <MenuItem value="365">Last year</MenuItem>
          </Select>
        </FormControl>
      </Box>
    );
  };

  // Render content based on selected tab
  const renderContent = () => {
    if (loading) {
      return (
        <Box display="flex" justifyContent="center" alignItems="center" height={300}>
          <CircularProgress />
        </Box>
      );
    }

    if (error) {
      return <Alert severity="error">{error}</Alert>;
    }

    if (postId) {
      if (patterns.length === 0) {
        return <Alert severity="info">No success patterns detected for this post.</Alert>;
      }
      
      return (
        <Box>
          {patterns.map(pattern => renderPatternCard(pattern))}
        </Box>
      );
    }

    switch (tabValue) {
      case 0: // All patterns
        if (patterns.length === 0) {
          return <Alert severity="info">No success patterns found with the current filters.</Alert>;
        }
        return (
          <Box>
            {patterns.map(pattern => renderPatternCard(pattern))}
          </Box>
        );
        
      case 1: // Top patterns
        if (patterns.length === 0) {
          return <Alert severity="info">No top patterns found.</Alert>;
        }
        return (
          <Box>
            {patterns.map(pattern => renderPatternCard(pattern))}
          </Box>
        );
        
      case 2: // By platform
        if (Object.keys(patternsByPlatform).length === 0) {
          return <Alert severity="info">No platform-specific patterns found.</Alert>;
        }
        return (
          <Box>
            {renderChart(patternsByPlatform)}
            
            {Object.entries(patternsByPlatform).map(([platform, platformPatterns]) => (
              <Box key={platform} mb={4}>
                <Typography variant="h6" gutterBottom>
                  {platform}
                </Typography>
                {platformPatterns.map(pattern => renderPatternCard(pattern))}
              </Box>
            ))}
          </Box>
        );
        
      case 3: // By content type
        if (Object.keys(patternsByContentType).length === 0) {
          return <Alert severity="info">No content type patterns found.</Alert>;
        }
        return (
          <Box>
            {renderChart(patternsByContentType)}
            
            {Object.entries(patternsByContentType).map(([contentType, contentPatterns]) => (
              <Box key={contentType} mb={4}>
                <Typography variant="h6" gutterBottom>
                  {contentType}
                </Typography>
                {contentPatterns.map(pattern => renderPatternCard(pattern))}
              </Box>
            ))}
          </Box>
        );
        
      default:
        return <Alert severity="warning">Invalid tab selection</Alert>;
    }
  };

  return (
    <Card sx={{ height: height, overflow: 'auto' }}>
      <CardContent>
        <Typography variant="h5" component="h2" gutterBottom>
          {postId ? 'Success Patterns for This Post' : 'Success Patterns'}
        </Typography>
        
        {!postId && (
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange} 
            sx={{ mb: 2 }}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="All Patterns" />
            <Tab label="Top Patterns" />
            <Tab label="By Platform" />
            <Tab label="By Content Type" />
          </Tabs>
        )}
        
        {renderFilters()}
        {renderContent()}
      </CardContent>
    </Card>
  );
};

export default SuccessPatterns; 