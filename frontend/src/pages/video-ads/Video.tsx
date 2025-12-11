import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Box,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
  Grid,
  Avatar,
  Divider,
  LinearProgress
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Download as DownloadIcon,
  VideoFile as VideoIcon,
  CheckCircle as CheckCircleIcon,
  Person as PersonIcon,
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  MovieCreation as MovieIcon
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';

interface GeneratedVideo {
  video_id: string;
  script_id: string;
  video_type: string;
  hook_text: string;
  script_text: string;
  combined_text?: string; // New field for combined content
  call_to_action?: string; // Add call to action field
  video_url: string;
  local_path?: string;
  hedra_job_id?: string;
  duration?: number;
  file_size?: number;
  aspect_ratio: string;
  quality: string;
  status: string;
  error?: string;
  created_at?: string;
}

interface VideoGenerationResponse {
  thread_id: string;
  actor_info: {
    image: string;
    path: string;
  };
  generated_videos: GeneratedVideo[];
  total_videos_generated: number;
  processing_time?: number;
  status: string;
}

const Video: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  
  // State management
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoData, setVideoData] = useState<VideoGenerationResponse | null>(null);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
  const [videoElements, setVideoElements] = useState<{ [key: string]: HTMLVideoElement }>({});
  
  // Data from previous page
  const [audioData, setAudioData] = useState<any>(null);

  useEffect(() => {
    initializePageData();
  }, []);

  const initializePageData = () => {
    try {
      // Get data from navigation state or localStorage
      const state = location.state || JSON.parse(localStorage.getItem('videoAdsState') || '{}');
      
      if (state.data) {
        setAudioData(state.data);
        generateVideo(state.data);
      } else {
        setError('Missing required data. Please go back to audio generation.');
      }
    } catch (e) {
      setError('Failed to load page data. Please try again.');
    }
  };

  const transformAudioDataForVideoBackend = (audioData: any) => {
    // Extract the audio result from the data
    const audioResult = audioData.audioResult || audioData;
    
    // Get actor image from the original audio data
    // The selectedActor has 'filename' field, not 'image'
    // Check multiple possible locations for the actor data
    let actorImage = 'actor-01.jpg'; // default fallback
    
    if (audioData.selectedActor?.filename) {
      actorImage = audioData.selectedActor.filename;
    } else if (audioData.voice_info?.actor?.filename) {
      actorImage = audioData.voice_info.actor.filename;
    } else if (audioData.voice_info?.actor?.image) {
      actorImage = audioData.voice_info.actor.image;
    }
    
    const transformed = {
      thread_id: audioData.threadId || audioResult.thread_id,
      audio_data: audioResult,
      actor_image: actorImage,
      video_settings: {
        aspect_ratio: "9:16",
        quality: "low",
        max_duration: 60
      }
    };
    
    return transformed;
  };

  const generateVideo = async (data: any) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('supabase.auth.token') || 'dev-token';
      
      // Transform the data for video backend
      const transformedData = transformAudioDataForVideoBackend(data);
      
      if (!transformedData.audio_data || !transformedData.audio_data.scripts_with_audio) {
        throw new Error('No audio data provided for video generation');
      }
      
      const response = await fetch('http://localhost:8001/video-ads/video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(transformedData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result: VideoGenerationResponse = await response.json();
      setVideoData(result);
      
      // Store result for navigation
      localStorage.setItem('videoAdsState', JSON.stringify({
        step: 'video',
        data: { ...data, videoResult: result }
      }));

    } catch (err: any) {
      setError(err.message || 'Failed to generate videos. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePlayVideo = (videoUrl: string, videoId: string) => {
    // Stop any currently playing video
    if (currentlyPlaying && videoElements[currentlyPlaying]) {
      videoElements[currentlyPlaying].pause();
    }

    // Create video element if it doesn't exist
    if (!videoElements[videoId]) {
      const video = document.createElement('video');
      video.src = videoUrl;
      video.controls = false;
      video.style.width = '100%';
      video.style.height = 'auto';
      video.style.borderRadius = '8px';
      
      setVideoElements(prev => ({
        ...prev,
        [videoId]: video
      }));
    }

    const video = videoElements[videoId];
    if (video) {
      if (currentlyPlaying === videoId) {
        // Toggle pause/play
        if (video.paused) {
          video.play();
        } else {
          video.pause();
          setCurrentlyPlaying(null);
        }
      } else {
        // Play new video
        video.play();
        setCurrentlyPlaying(videoId);
      }
    }
  };

  const handleDownloadVideo = async (videoUrl: string, filename: string) => {
    try {
      const response = await fetch(videoUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown size';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return 'Unknown';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  // Loading state
  if (loading) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <CircularProgress size={60} sx={{ mb: 3 }} />
          <Typography variant="h5" gutterBottom>
            Generating Videos with Hedra AI
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            This may take a few minutes. We're creating personalized talking head videos for each of your scripts.
          </Typography>
          <LinearProgress sx={{ width: '100%', maxWidth: 400, mx: 'auto' }} />
        </Box>
      </Container>
    );
  }

  // Error state
  if (error && !videoData) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<ArrowBackIcon />}
              onClick={() => navigate('/video-ads/audio')}
            >
              Back to Audio
            </Button>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={() => window.location.reload()}
            >
              Retry
            </Button>
          </Box>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 2 }}>
            <MovieIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            {videoData && (
              <Chip 
                icon={<CheckCircleIcon />} 
                label={`${videoData.total_videos_generated} Videos Generated`}
                color="success" 
                variant="outlined" 
              />
            )}
          </Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Generated Videos
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Your personalized talking head videos are ready with complete script narration
          </Typography>
        </Box>

        {/* Actor & Processing Info */}
        {videoData && (
          <Card sx={{ mb: 4, background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Video Generation Summary
              </Typography>
              <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <PersonIcon color="primary" />
                  <Box>
                    <Typography variant="subtitle1">
                      Actor: {videoData.actor_info.image}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Aspect Ratio: 9:16 (TikTok/Mobile)
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <VideoIcon color="primary" />
                  <Box>
                    <Typography variant="subtitle1">
                      {videoData.total_videos_generated} Videos Generated
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Processing Time: {videoData.processing_time?.toFixed(1)}s
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Generated Videos Grid */}
        {videoData && videoData.generated_videos.length > 0 && (
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: 3 }}>
            {videoData.generated_videos.map((video, videoIndex) => {
              const isCombined = video.video_type === 'combined';
              const cardKey = `${video.script_id}-${video.video_type}`;
              
              // Determine what content to show in preview
              const previewContent = isCombined 
                ? video.combined_text || `${video.hook_text}. ${video.script_text}`
                : (video.video_type === 'hook' ? video.hook_text : video.script_text);
              
              return (
                <Card key={cardKey} sx={{ 
                  height: '100%', 
                  display: 'flex', 
                  flexDirection: 'column',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    boxShadow: 3,
                    transform: 'translateY(-2px)'
                  }
                }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    {/* Video Type Header */}
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <VideoIcon sx={{ 
                        mr: 1, 
                        color: 'primary.main', 
                        fontSize: 20 
                      }} />
                      <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 600 }}>
                        {isCombined ? `Script ${videoIndex + 1}` : 
                         `${video.video_type === 'hook' ? 'Hook' : 'Script'} ${videoIndex + 1}`}
                      </Typography>
                    </Box>
                    
                    {/* Video Preview */}
                    <Box sx={{ 
                      width: '100%', 
                      aspectRatio: '9/16', 
                      backgroundColor: '#f5f5f5', 
                      borderRadius: 1, 
                      mb: 2,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      position: 'relative',
                      overflow: 'hidden'
                    }}>
                      {video.status === 'completed' && video.video_url ? (
                        <video
                          src={`http://localhost:8001${video.video_url}`}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          controls
                          poster=""
                        />
                      ) : video.status === 'failed' ? (
                        <Box sx={{ textAlign: 'center', p: 2 }}>
                          <Typography color="error">Generation Failed</Typography>
                          {video.error && (
                            <Typography variant="caption" color="text.secondary">
                              {video.error}
                            </Typography>
                          )}
                        </Box>
                      ) : (
                        <Box sx={{ textAlign: 'center', p: 2 }}>
                          <CircularProgress size={40} />
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            Processing...
                          </Typography>
                        </Box>
                      )}
                    </Box>

                    {/* Script Breakdown */}
                    <Box sx={{ 
                      bgcolor: 'grey.50', 
                      borderRadius: 1, 
                      p: 1.5, 
                      mb: 2,
                      border: '1px solid',
                      borderColor: 'grey.200'
                    }}>
                      <Box sx={{ mb: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'primary.main' }}>
                          Hook:
                        </Typography>
                        <Typography variant="body2" sx={{ fontSize: '0.8rem', mt: 0.5 }}>
                          {video.hook_text}
                        </Typography>
                      </Box>
                      <Box sx={{ mb: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'secondary.main' }}>
                          Script:
                        </Typography>
                        <Typography variant="body2" sx={{ fontSize: '0.8rem', mt: 0.5 }}>
                          {video.script_text}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.main' }}>
                          Call to Action:
                        </Typography>
                        <Typography variant="body2" sx={{ fontSize: '0.8rem', mt: 0.5 }}>
                          {video.call_to_action || 'Not specified'}
                        </Typography>
                      </Box>
                    </Box>

                    {/* Video Metadata */}
                    <Divider sx={{ my: 2 }} />
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      <Chip 
                        label={video.aspect_ratio} 
                        size="small" 
                        variant="outlined" 
                      />
                      <Chip 
                        label={`Quality: ${video.quality}`} 
                        size="small" 
                        variant="outlined" 
                      />
                      {video.duration && (
                        <Chip 
                          label={formatDuration(video.duration)} 
                          size="small" 
                          variant="outlined" 
                        />
                      )}
                    </Box>
                  </CardContent>

                  {/* Action Buttons */}
                  <Box sx={{ p: 2, pt: 0 }}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {video.status === 'completed' && video.video_url && (
                        <Button
                          variant="outlined"
                          startIcon={<DownloadIcon />}
                          onClick={() => handleDownloadVideo(
                            `http://localhost:8001${video.video_url}`,
                            `video_${video.script_id}_${video.video_type}.mp4`
                          )}
                          size="small"
                          fullWidth
                        >
                          Download
                        </Button>
                      )}
                    </Box>
                  </Box>
                </Card>
              );
            })}
          </Box>
        )}

        {/* Navigation */}
        <Box sx={{ mt: 4, display: 'flex', justifyContent: 'space-between' }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/video-ads/audio')}
          >
            Back to Audio
          </Button>
          
          {videoData && videoData.total_videos_generated > 0 && (
            <Button
              variant="contained"
              onClick={() => {
                // Navigate to final step or dashboard
                navigate('/dashboard');
              }}
            >
              Complete Campaign
            </Button>
          )}
        </Box>
      </Box>
    </Container>
  );
};

export default Video;
