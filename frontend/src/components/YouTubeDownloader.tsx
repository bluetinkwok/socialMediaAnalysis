import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Paper, 
  Grid, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  CircularProgress,
  LinearProgress,
  Chip,
  Card,
  CardMedia,
  CardContent,
  Alert,
  Snackbar,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import { Download, YouTube, Info, Clear } from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
import { apiClient } from '../utils/apiClient';
import { useWebSocket } from '../hooks/useWebSocket';

interface VideoFormat {
  format_id: string;
  ext: string;
  resolution: string;
  filesize?: number;
  filesize_approx?: number;
  fps?: number;
  vcodec?: string;
  acodec?: string;
  format_note?: string;
}

interface VideoInfo {
  video_id: string;
  title: string;
  description: string;
  channel: string;
  channel_id: string;
  duration: number;
  upload_date: string;
  view_count: number;
  like_count: number;
  thumbnail_url: string;
  available_formats: VideoFormat[];
  subtitles_available: string[];
}

interface DownloadProgress {
  task_id: string;
  status: string;
  current_step: string;
  progress_percentage: number;
  message: string;
  current_item: number;
  total_items: number;
  error?: string;
}

const YouTubeDownloader: React.FC = () => {
  const theme = useTheme();
  const [url, setUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [infoLoading, setInfoLoading] = useState(false);
  const [quality, setQuality] = useState('medium');
  const [formatId, setFormatId] = useState<string | null>(null);
  const [includeSubtitles, setIncludeSubtitles] = useState(true);
  const [includeThumbnail, setIncludeThumbnail] = useState(true);
  const [downloadJobId, setDownloadJobId] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<DownloadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // WebSocket connection for real-time progress updates
  const { lastMessage } = useWebSocket(
    downloadJobId ? `ws://localhost:8000/ws/download/${downloadJobId}` : null
  );
  
  // Process WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type === 'progress_update') {
          setDownloadProgress(data.data);
          
          // Check for completion
          if (data.data.status === 'completed') {
            setSuccessMessage('Download completed successfully!');
            setDownloadJobId(null);
          }
          
          // Check for failure
          if (data.data.status === 'failed') {
            setError(`Download failed: ${data.data.error || 'Unknown error'}`);
            setDownloadJobId(null);
          }
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    }
  }, [lastMessage]);
  
  // Reset state when URL changes
  useEffect(() => {
    setVideoInfo(null);
    setFormatId(null);
    setDownloadJobId(null);
    setDownloadProgress(null);
  }, [url]);
  
  // Format file size for display
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };
  
  // Format duration for display
  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  // Handle URL validation
  const validateUrl = async () => {
    if (!url) {
      setError('Please enter a YouTube URL');
      return false;
    }
    
    try {
      const response = await apiClient.get(`/youtube/validate?url=${encodeURIComponent(url)}`);
      
      if (!response.data.data.is_valid) {
        setError('Invalid YouTube URL');
        return false;
      }
      
      return true;
    } catch (err) {
      setError('Error validating URL');
      console.error('Error validating URL:', err);
      return false;
    }
  };
  
  // Fetch video information
  const fetchVideoInfo = async () => {
    if (!await validateUrl()) return;
    
    setInfoLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/youtube/info', { url });
      
      if (response.data.success) {
        setVideoInfo(response.data.data);
      } else {
        setError(response.data.error || 'Failed to fetch video information');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error fetching video information');
      console.error('Error fetching video info:', err);
    } finally {
      setInfoLoading(false);
    }
  };
  
  // Start download process
  const startDownload = async () => {
    if (!await validateUrl()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/youtube/download', {
        url,
        quality,
        format_id: formatId,
        include_subtitles: includeSubtitles,
        include_thumbnail: includeThumbnail
      });
      
      if (response.data.success) {
        setDownloadJobId(response.data.data.job_id);
        setSuccessMessage('Download started!');
      } else {
        setError(response.data.error || 'Failed to start download');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error starting download');
      console.error('Error starting download:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Clear current state
  const handleClear = () => {
    setUrl('');
    setVideoInfo(null);
    setFormatId(null);
    setDownloadJobId(null);
    setDownloadProgress(null);
    setError(null);
  };
  
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        <YouTube sx={{ mr: 1, verticalAlign: 'middle' }} />
        YouTube Downloader
      </Typography>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <TextField
              fullWidth
              label="YouTube URL"
              variant="outlined"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              disabled={loading || !!downloadJobId}
            />
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                color="primary"
                startIcon={<Info />}
                onClick={fetchVideoInfo}
                disabled={!url || infoLoading || loading || !!downloadJobId}
                sx={{ flex: 1 }}
              >
                {infoLoading ? <CircularProgress size={24} /> : 'Get Info'}
              </Button>
              
              <Button
                variant="contained"
                color="secondary"
                startIcon={<Clear />}
                onClick={handleClear}
                sx={{ flex: 1 }}
              >
                Clear
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>
      
      {videoInfo && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardMedia
                  component="img"
                  image={videoInfo.thumbnail_url}
                  alt={videoInfo.title}
                  sx={{ height: 180, objectFit: 'cover' }}
                />
                <CardContent>
                  <Typography variant="h6" noWrap title={videoInfo.title}>
                    {videoInfo.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {videoInfo.channel}
                  </Typography>
                  <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between' }}>
                    <Chip 
                      size="small" 
                      label={`${formatDuration(videoInfo.duration)}`} 
                      variant="outlined" 
                    />
                    <Chip 
                      size="small" 
                      label={`${videoInfo.view_count.toLocaleString()} views`} 
                      variant="outlined" 
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={8}>
              <Typography variant="h6" gutterBottom>Download Options</Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth variant="outlined">
                    <InputLabel>Quality</InputLabel>
                    <Select
                      value={quality}
                      onChange={(e) => {
                        setQuality(e.target.value);
                        setFormatId(null); // Reset format ID when quality changes
                      }}
                      label="Quality"
                      disabled={loading || !!downloadJobId}
                    >
                      <MenuItem value="low">Low (240p-360p)</MenuItem>
                      <MenuItem value="medium">Medium (480p)</MenuItem>
                      <MenuItem value="high">High (720p)</MenuItem>
                      <MenuItem value="best">Best Available</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth variant="outlined">
                    <InputLabel>Specific Format</InputLabel>
                    <Select
                      value={formatId || ''}
                      onChange={(e) => setFormatId(e.target.value)}
                      label="Specific Format"
                      disabled={loading || !!downloadJobId}
                    >
                      <MenuItem value="">
                        <em>Auto (Based on Quality)</em>
                      </MenuItem>
                      {videoInfo.available_formats?.map((format) => (
                        <MenuItem key={format.format_id} value={format.format_id}>
                          {`${format.resolution} - ${format.ext} (${formatFileSize(format.filesize || format.filesize_approx)})`}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={includeSubtitles}
                        onChange={(e) => setIncludeSubtitles(e.target.checked)}
                        disabled={loading || !!downloadJobId}
                      />
                    }
                    label="Download subtitles if available"
                  />
                  
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={includeThumbnail}
                        onChange={(e) => setIncludeThumbnail(e.target.checked)}
                        disabled={loading || !!downloadJobId}
                      />
                    }
                    label="Download thumbnail"
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <Button
                    variant="contained"
                    color="primary"
                    fullWidth
                    startIcon={<Download />}
                    onClick={startDownload}
                    disabled={loading || !!downloadJobId}
                  >
                    {loading ? <CircularProgress size={24} /> : 'Download Video'}
                  </Button>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </Paper>
      )}
      
      {/* Download Progress */}
      {downloadProgress && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>Download Progress</Typography>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              {downloadProgress.message}
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={downloadProgress.progress_percentage} 
              sx={{ mt: 1, mb: 1 }}
            />
            <Typography variant="body2" align="right">
              {`${Math.round(downloadProgress.progress_percentage)}%`}
            </Typography>
          </Box>
          
          <Grid container spacing={1}>
            <Grid item>
              <Chip 
                label={`Step: ${downloadProgress.current_step.replace(/_/g, ' ')}`} 
                variant="outlined" 
                size="small"
              />
            </Grid>
            <Grid item>
              <Chip 
                label={`Status: ${downloadProgress.status}`} 
                variant="outlined"
                size="small"
                color={
                  downloadProgress.status === 'completed' ? 'success' : 
                  downloadProgress.status === 'failed' ? 'error' : 
                  'default'
                }
              />
            </Grid>
            {downloadProgress.current_item > 0 && (
              <Grid item>
                <Chip 
                  label={`Item ${downloadProgress.current_item}/${downloadProgress.total_items}`} 
                  variant="outlined"
                  size="small"
                />
              </Grid>
            )}
          </Grid>
        </Paper>
      )}
      
      {/* Error Snackbar */}
      <Snackbar 
        open={!!error} 
        autoHideDuration={6000} 
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
      
      {/* Success Snackbar */}
      <Snackbar 
        open={!!successMessage} 
        autoHideDuration={6000} 
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default YouTubeDownloader; 