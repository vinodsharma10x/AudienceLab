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
import { getCampaignId } from '../../utils/v3-migration';

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

interface VideoGenerationV2Response {
  conversation_id: string; // V2: conversation_id instead of thread_id
  actor_info: {
    image: string;
    path: string;
  };
  generated_videos: GeneratedVideo[];
  videos?: GeneratedVideo[]; // Alternative name for backward compatibility
  total_videos_generated: number;
  processing_time?: number;
  status: string;
  actor_image?: string; // Optional for backward compatibility
  video_settings?: {
    aspect_ratio?: string;
    quality?: string;
  };
}

const VideoV2: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  
  // State management
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoData, setVideoData] = useState<VideoGenerationV2Response | null>(null);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
  const [videoElements, setVideoElements] = useState<{ [key: string]: HTMLVideoElement }>({});
  
  // Data from previous page (V2: different state management)
  const [audioData, setAudioData] = useState<any>(null);
  const [campaignId, setCampaignId] = useState<string>('');

  useEffect(() => {
    initializePageData();
  }, []);

  const initializePageData = async () => {
    try {
      // Get data from navigation state or localStorage (V2: different storage key)
      let state = location.state;
      
      if (!state) {
        try {
          const storedState = localStorage.getItem('videoAdsV2State');
          if (storedState) {
            // Safely parse JSON, handling any Unicode issues
            state = JSON.parse(storedState);
          } else {
            state = {};
          }
        } catch (parseError) {
          console.error('Error parsing stored state:', parseError);
          state = {};
        }
      }
      
      // V3: Check if we only have campaignId (navigating back or resuming)
      if (state.campaignId && !state.data) {
        console.log('🔄 V3: Loading video data from database for campaign:', state.campaignId);
        await loadVideoFromDatabase(state.campaignId);
      } else if (state.data) {
        const campaignIdValue = state.data.campaign_id || state.data.conversation_id || state.conversationId || state.campaignId || '';
        setAudioData(state.data);
        setCampaignId(campaignIdValue);
        
        // Check if video already exists in database before regenerating
        console.log('🔍 Checking for existing video before regenerating...');
        const existingVideo = await checkForExistingVideo(campaignIdValue);
        
        if (existingVideo) {
          console.log('✅ Using existing video from database, not regenerating');
          setVideoData(existingVideo);
          setLoading(false); // Important: stop loading state
        } else {
          console.log('🎬 No existing video found, generating new video');
          generateVideo(state.data);
        }
      } else {
        setError('Missing required data. Please go back to audio generation.');
      }
    } catch (e) {
      console.error('Error initializing page data:', e);
      setError('Failed to load page data. Please try again.');
    }
  };

  const checkForExistingVideo = async (campaignId: string): Promise<any> => {
    try {
      const token = getValidToken(session);
      if (!token) {
        console.log('❌ No token available for checking existing video');
        return null;
      }

      console.log('🔍 Checking for existing video for campaign:', campaignId);

      // V3: Check for existing video data in database
      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${campaignId}/video`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        console.log('❌ Failed to fetch existing video, status:', response.status);
        return null;
      }

      const videoData = await response.json();
      console.log('📦 Video data from database:', videoData);
      
      // Check for different response formats (videos vs generated_videos)
      const videos = videoData.videos || videoData.generated_videos || [];
      
      console.log('📹 Found videos in response:', videos.length);
      
      if (videoData.status === 'not_found' || videos.length === 0) {
        console.log('❌ No videos found or status is not_found');
        return null;
      }
      
      // Check if videos have valid URLs
      const hasValidVideos = videos.some((v: any) => v.video_url && v.status === 'completed');
      
      console.log('✅ Has valid videos with URLs:', hasValidVideos);
      
      if (!hasValidVideos) {
        console.log('❌ No valid videos with completed status and URLs');
        return null;
      }
      
      // Normalize the response to always have 'videos' field
      if (videoData.generated_videos && !videoData.videos) {
        videoData.videos = videoData.generated_videos;
      }
      
      console.log('✅ Returning existing video data to reuse');
      return videoData;
      
    } catch (err: any) {
      console.error('Error checking for existing video:', err);
      return null;
    }
  };

  const loadVideoFromDatabase = async (campaignId: string) => {
    setLoading(true);
    setError(null);
    setCampaignId(campaignId);
    
    try {
      const token = getValidToken(session);
      if (!token) {
        throw new Error('Authentication required');
      }

      // V3: Load video data from database
      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${campaignId}/video`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        if (response.status === 404 || (await response.json()).status === 'not_found') {
          // No video data yet, need to load audio data and generate
          console.log('No video data found, loading audio data...');
          await loadAudioAndGenerateVideo(campaignId);
        } else {
          throw new Error(`Failed to load video data: ${response.statusText}`);
        }
        return;
      }

      const videoData = await response.json();
      
      if (videoData.status === 'not_found') {
        // No video data yet, need to load audio data and generate
        console.log('No video data found, loading audio data...');
        await loadAudioAndGenerateVideo(campaignId);
        return;
      }
      
      // Set the video data
      setVideoData(videoData);
      console.log('✅ V3: Loaded video data from database');
      
    } catch (err: any) {
      console.error('Error loading video data:', err);
      setError(err.message || 'Failed to load video data.');
    } finally {
      setLoading(false);
    }
  };

  const loadAudioAndGenerateVideo = async (campaignId: string) => {
    try {
      const token = getValidToken(session);
      if (!token) {
        throw new Error('Authentication required');
      }

      // Load audio data from database
      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${campaignId}/audio`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error('No audio data found. Please generate audio first.');
      }

      const audioData = await response.json();
      
      if (audioData.status === 'not_found') {
        throw new Error('No audio data found. Please generate audio first.');
      }
      
      // Set audio data and generate video
      setAudioData(audioData);
      await generateVideo(audioData);
      
    } catch (err: any) {
      console.error('Error loading audio data:', err);
      setError(err.message || 'Failed to load audio data.');
      setLoading(false);
    }
  };

  const transformAudioDataForVideoBackend = (audioData: any, fallbackCampaignId?: string) => {
    // Extract the audio result from the data
    const audioResult = audioData.audioResult || audioData;
    
    // Get actor image from the original audio data
    // The selectedActor has 'filename' field, not 'image'
    // Check multiple possible locations for the actor data
    let actorImage = 'actor-01.jpg'; // default fallback
    
    if (audioData.voice_actor_selection?.selected_actor?.filename) {
      actorImage = audioData.voice_actor_selection.selected_actor.filename;
    } else if (audioData.selectedActor?.filename) {
      actorImage = audioData.selectedActor.filename;
    } else if (audioData.voice_info?.actor?.filename) {
      actorImage = audioData.voice_info.actor.filename;
    } else if (audioData.voice_info?.actor?.image) {
      actorImage = audioData.voice_info.actor.image;
    }
    
    const transformed = {
      conversation_id: audioData.conversation_id || audioData.campaign_id || fallbackCampaignId, // V3: Try all possible ID fields
      campaign_id: audioData.campaign_id || audioData.conversation_id || fallbackCampaignId, // V3: Include both for compatibility
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
      const token = getValidToken(session);
      
      // Transform the data for video backend
      const transformedData = transformAudioDataForVideoBackend(data, campaignId);
      
      if (!transformedData.audio_data || !transformedData.audio_data.scripts_with_audio) {
        throw new Error('No audio data provided for video generation');
      }
      
      // Log what we're sending to the backend
      console.log('🎬 ===========================================');
      console.log('🎬 VIDEO GENERATION REQUEST TO BACKEND');
      console.log('🎬 ===========================================');
      console.log('📋 Conversation ID:', transformedData.conversation_id);
      console.log('🎭 Actor Image:', transformedData.actor_image);
      console.log('🎵 Scripts with audio count:', transformedData.audio_data.scripts_with_audio?.length);
      console.log('⚙️ Video Settings:', JSON.stringify(transformedData.video_settings, null, 2));
      
      // Log each script's audio details
      transformedData.audio_data.scripts_with_audio?.forEach((script: any, index: number) => {
        console.log(`\n📝 Script ${index + 1}:`);
        console.log('  - Script ID:', script.script_id);
        console.log('  - Has combined audio:', !!script.combined_audio);
        console.log('  - Combined audio URL:', script.combined_audio?.audio_url);
        console.log('  - Combined audio duration:', script.combined_audio?.duration);
        console.log('  - Hook:', script.hook?.substring(0, 50) + '...');
        console.log('  - Body:', script.body?.substring(0, 50) + '...');
      });
      
      console.log('\n📦 Full payload being sent:', JSON.stringify(transformedData, null, 2));
      console.log('🎬 ===========================================\n');
      
      // V2: Call V2 video endpoint
      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v2/video`, {
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

      const result: VideoGenerationV2Response = await response.json();
      setVideoData(result);
      
      // Store result for navigation (V2: different storage key)
      localStorage.setItem('videoAdsV2State', JSON.stringify({
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
          {campaignId && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Campaign: {campaignId}
            </Typography>
          )}
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
              onClick={() => navigate('/video-ads-v2/audio', {
                state: {
                  campaignId: campaignId, // V3: Only pass campaignId when going back
                  isFromVideo: true
                }
              })}
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
          {campaignId && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Campaign: {campaignId}
            </Typography>
          )}
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
                      Actor: {videoData.actor_info?.image || videoData.actor_image || 'Default Actor'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Aspect Ratio: {videoData.video_settings?.aspect_ratio || '9:16'} (TikTok/Mobile)
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
        {videoData && (videoData.videos || videoData.generated_videos || []).length > 0 && (
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: 3 }}>
            {(videoData.videos || videoData.generated_videos || []).map((video, videoIndex) => {
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
                          src={video.video_url} // V2: Use direct video URL
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
                            video.video_url,
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
            onClick={() => navigate('/video-ads-v2/audio', {
              state: {
                campaignId: campaignId, // V3: Only pass campaignId when going back
                isFromVideo: true
              }
            })}
          >
            Back to Audio
          </Button>
          
          {videoData && videoData.total_videos_generated > 0 && (
            <Button
              variant="contained"
              onClick={() => {
                // Navigate to dashboard
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

export default VideoV2;
