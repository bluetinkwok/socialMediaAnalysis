import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Grid, 
  Chip, 
  CircularProgress, 
  Alert, 
  Tabs, 
  Tab, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel, 
  SelectChangeEvent,
  Paper,
  Divider,
  Button,
  IconButton,
  Tooltip
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  Legend, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import InfoIcon from '@mui/icons-material/Info';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import SuccessPatterns from './SuccessPatterns';

interface PerformanceMetric {
  name: string;
  value: number;
  change: number;
  platform?: string;
}

interface TimeSeriesData {
  date: string;
  views?: number;
  likes?: number;
  comments?: number;
  shares?: number;
}

interface PlatformDistribution {
  name: string;
  value: number;
}

interface ContentTypeDistribution {
  name: string;
  value: number;
}

interface Recommendation {
  id: string;
  type: string;
  text: string;
  impact_score: number;
  source_pattern: string;
  pattern_confidence: number;
}

interface AnalyticsInsightsProps {
  height?: string | number;
}

const AnalyticsInsights: React.FC<AnalyticsInsightsProps> = ({ height = 800 }) => {
  const theme = useTheme();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState<number>(0);
  const [platform, setPlatform] = useState<string>('all');
  const [contentType, setContentType] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<number>(30);
  
  // Data states
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetric[]>([]);
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesData[]>([]);
  const [platformDistribution, setPlatformDistribution] = useState<PlatformDistribution[]>([]);
  const [contentTypeDistribution, setContentTypeDistribution] = useState<ContentTypeDistribution[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  // Colors for charts
  const COLORS = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.error.main,
    theme.palette.warning.main,
    theme.palette.success.main,
    theme.palette.info.main,
  ];

  // Fetch analytics data
  useEffect(() => {
    const fetchAnalyticsData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch performance metrics
        const metricsResponse = await axios.get('/api/v1/analytics/metrics', {
          params: {
            days: timeRange,
            ...(platform !== 'all' && { platform }),
            ...(contentType !== 'all' && { content_type: contentType })
          }
        });
        
        if (metricsResponse.data.success) {
          setPerformanceMetrics(metricsResponse.data.metrics || []);
        }
        
        // Fetch time series data
        const timeSeriesResponse = await axios.get('/api/v1/analytics/time-series', {
          params: {
            days: timeRange,
            ...(platform !== 'all' && { platform }),
            ...(contentType !== 'all' && { content_type: contentType })
          }
        });
        
        if (timeSeriesResponse.data.success) {
          setTimeSeriesData(timeSeriesResponse.data.data || []);
        }
        
        // Fetch platform distribution
        const platformResponse = await axios.get('/api/v1/analytics/platform-distribution');
        if (platformResponse.data.success) {
          setPlatformDistribution(platformResponse.data.distribution || []);
        }
        
        // Fetch content type distribution
        const contentTypeResponse = await axios.get('/api/v1/analytics/content-type-distribution');
        if (contentTypeResponse.data.success) {
          setContentTypeDistribution(contentTypeResponse.data.distribution || []);
        }
        
        // Fetch recommendations
        const recommendationsResponse = await axios.get('/api/v1/recommendations', {
          params: {
            limit: 5,
            ...(platform !== 'all' && { platform }),
            ...(contentType !== 'all' && { content_type: contentType })
          }
        });
        
        if (recommendationsResponse.data.success) {
          setRecommendations(recommendationsResponse.data.recommendations || []);
        }
        
      } catch (err) {
        console.error('Error fetching analytics data:', err);
        setError('Error loading analytics data');
      } finally {
        setLoading(false);
      }
    };
    
    fetchAnalyticsData();
  }, [platform, contentType, timeRange]);

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

  // Render performance metrics cards
  const renderPerformanceMetrics = () => (
    <Grid container spacing={3}>
      {performanceMetrics.map((metric) => (
        <Grid item xs={12} sm={6} md={3} key={metric.name}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" component="div" gutterBottom>
                {metric.name}
              </Typography>
              <Typography variant="h4" component="div">
                {metric.value.toLocaleString()}
              </Typography>
              <Box display="flex" alignItems="center" mt={1}>
                <Chip 
                  size="small"
                  label={`${metric.change > 0 ? '+' : ''}${metric.change}%`}
                  color={metric.change > 0 ? "success" : metric.change < 0 ? "error" : "default"}
                  icon={metric.change > 0 ? <TrendingUpIcon /> : undefined}
                />
                <Typography variant="body2" color="text.secondary" ml={1}>
                  vs. previous period
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );

  // Render time series chart
  const renderTimeSeriesChart = () => (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Typography variant="h6" component="div" gutterBottom>
          Engagement Over Time
        </Typography>
        <Box sx={{ width: '100%', height: 400 }}>
          <ResponsiveContainer>
            <LineChart data={timeSeriesData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <RechartsTooltip />
              <Legend />
              <Line type="monotone" dataKey="views" stroke={COLORS[0]} name="Views" />
              <Line type="monotone" dataKey="likes" stroke={COLORS[1]} name="Likes" />
              <Line type="monotone" dataKey="comments" stroke={COLORS[2]} name="Comments" />
              <Line type="monotone" dataKey="shares" stroke={COLORS[3]} name="Shares" />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );

  // Render distribution charts
  const renderDistributionCharts = () => (
    <Grid container spacing={3} sx={{ mt: 1 }}>
      <Grid item xs={12} md={6}>
        <Card sx={{ height: '100%' }}>
          <CardContent>
            <Typography variant="h6" component="div" gutterBottom>
              Content by Platform
            </Typography>
            <Box sx={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={platformDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {platformDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card sx={{ height: '100%' }}>
          <CardContent>
            <Typography variant="h6" component="div" gutterBottom>
              Content by Type
            </Typography>
            <Box sx={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={contentTypeDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {contentTypeDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  // Render recommendation cards
  const renderRecommendations = () => (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={2}>
          <LightbulbIcon color="warning" sx={{ mr: 1 }} />
          <Typography variant="h6" component="div">
            Actionable Recommendations
          </Typography>
          <Tooltip title="Recommendations based on identified success patterns">
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        
        {recommendations.length === 0 ? (
          <Alert severity="info">
            No recommendations available. Analyze more content to generate insights.
          </Alert>
        ) : (
          recommendations.map((rec) => (
            <Paper 
              key={rec.id} 
              sx={{ 
                p: 2, 
                mb: 2, 
                borderLeft: `4px solid ${theme.palette.warning.main}`,
                bgcolor: 'background.default' 
              }}
            >
              <Typography variant="body1" gutterBottom>
                {rec.text}
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1} mt={1}>
                <Chip 
                  size="small" 
                  label={`Impact: ${rec.impact_score}/10`}
                  color="primary"
                />
                <Chip 
                  size="small" 
                  label={`Type: ${rec.type.replace(/_/g, ' ')}`}
                />
                <Chip 
                  size="small" 
                  label={`Based on: ${rec.source_pattern.replace(/_/g, ' ')}`}
                />
              </Box>
            </Paper>
          ))
        )}
        
        <Box display="flex" justifyContent="flex-end" mt={2}>
          <Button variant="outlined" color="primary">
            View All Recommendations
          </Button>
        </Box>
      </CardContent>
    </Card>
  );

  // Render filters
  const renderFilters = () => (
    <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
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
          <MenuItem value="threads">Threads</MenuItem>
          <MenuItem value="rednote">RedNote</MenuItem>
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
          <MenuItem value="mixed">Mixed</MenuItem>
        </Select>
      </FormControl>
      
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

  // Main render
  return (
    <Box sx={{ width: '100%', height }}>
      <Tabs value={tabValue} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tab label="Overview" />
        <Tab label="Performance" />
        <Tab label="Success Patterns" />
        <Tab label="Recommendations" />
      </Tabs>
      
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="200px">
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      ) : (
        <>
          {renderFilters()}
          
          {tabValue === 0 && (
            <>
              {renderPerformanceMetrics()}
              {renderTimeSeriesChart()}
              {renderDistributionCharts()}
              {renderRecommendations()}
            </>
          )}
          
          {tabValue === 1 && (
            <>
              {renderPerformanceMetrics()}
              {renderTimeSeriesChart()}
              <Card sx={{ mt: 3 }}>
                <CardContent>
                  <Typography variant="h6" component="div" gutterBottom>
                    Performance by Platform
                  </Typography>
                  <Box sx={{ width: '100%', height: 400 }}>
                    <ResponsiveContainer>
                      <BarChart data={platformDistribution} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <RechartsTooltip />
                        <Legend />
                        <Bar dataKey="value" name="Content Count" fill={theme.palette.primary.main} />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </>
          )}
          
          {tabValue === 2 && (
            <SuccessPatterns showFilters={false} height={600} />
          )}
          
          {tabValue === 3 && (
            <>
              {renderRecommendations()}
              <Card sx={{ mt: 3 }}>
                <CardContent>
                  <Typography variant="h6" component="div" gutterBottom>
                    Recommendation Categories
                  </Typography>
                  <Box sx={{ width: '100%', height: 400 }}>
                    <ResponsiveContainer>
                      <BarChart 
                        data={[
                          { name: 'Content Creation', count: 12 },
                          { name: 'Posting Strategy', count: 8 },
                          { name: 'Visual Elements', count: 15 },
                          { name: 'Text Elements', count: 10 },
                          { name: 'Engagement Strategy', count: 7 }
                        ]} 
                        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <RechartsTooltip />
                        <Legend />
                        <Bar dataKey="count" name="Recommendation Count" fill={theme.palette.warning.main} />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}
    </Box>
  );
};

export default AnalyticsInsights; 