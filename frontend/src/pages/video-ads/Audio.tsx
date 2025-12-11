import React, { useState, useEffect, useRef } from 'react';
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
  LinearProgress,
  Avatar,
  Divider
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  VolumeUp as VolumeIcon,
  AudioFile as AudioIcon,
  CheckCircle as CheckCircleIcon,
  Person as PersonIcon,
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';

interface GeneratedAudio {
  audio_id: string;
  type: 'combined' | 'hook' | 'script'; // Updated to include 'combined'
  content: string;
  audio_url: string;
  duration?: number;
  file_size?: number;
  voice_settings?: any;
}

interface ScriptWithAudio {
  script_id: string;
  hook: string;
  body: string;
  call_to_action?: string;
  selected: boolean;
  // New combined audio field
  combined_audio?: GeneratedAudio;
  // Keep old fields for backwards compatibility
  hook_audio?: GeneratedAudio;
  script_audio?: GeneratedAudio;
}

interface AudioGenerationResponse {
  thread_id: string;
  selected_angle: any;
  voice_info: {
    voice: any;
    actor: any;
  };
  scripts_with_audio: ScriptWithAudio[];
  total_audios_generated: number;
  status: string;
}

const Audio: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  
  // State management
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioData, setAudioData] = useState<AudioGenerationResponse | null>(null);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
  const [audioElements, setAudioElements] = useState<{ [key: string]: HTMLAudioElement }>({});
  
  // Data from previous page
  const [voiceActorData, setVoiceActorData] = useState<any>(null);

  useEffect(() => {
    initializePageData();
  }, []);

  const initializePageData = () => {
    try {
      // Get data from navigation state or localStorage
      const state = location.state || JSON.parse(localStorage.getItem('videoAdsState') || '{}');
      
      if (state.data) {
        setVoiceActorData(state.data);
        generateAudio(state.data);
      } else {
        setError('Missing required data. Please go back to voice & actor selection.');
      }
    } catch (e) {
      setError('Failed to load page data. Please try again.');
    }
  };

  const generateAudio = async (data: any) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('supabase.auth.token') || 'dev-token';
      
      // Transform the nested campaign scripts structure to match backend expectations
      const transformedScripts = transformCampaignScriptsForBackend(data.campaignScripts);
      
      console.log('🔍 Debug campaignScripts input:', data.campaignScripts);
      console.log('🔍 Debug transformedScripts output:', transformedScripts);
      
      if (!transformedScripts.scripts || transformedScripts.scripts.length === 0) {
        console.error('❌ No scripts after transformation!');
        throw new Error('No scripts provided');
      }
      
      const requestPayload = {
        thread_id: data.threadId,
        voice_actor_selection: {
          selected_voice: data.selectedVoice,
          selected_actor: data.selectedActor
        },
        campaign_scripts: transformedScripts
      };

      console.log('Generating audio with payload:', requestPayload);
      console.log('Transformed scripts:', transformedScripts);

      const response = await fetch('http://localhost:8001/video-ads/audio', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestPayload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const responseText = await response.text();
      const result: AudioGenerationResponse = JSON.parse(responseText);
      
      setAudioData(result);
      localStorage.setItem('audioData', responseText);
      console.log('🔍 audioData.scripts_with_audio length:', result.scripts_with_audio?.length);
      
      // Force a re-render by adding a small delay
      setTimeout(() => {
        console.log('🔍 audioData state after timeout:', audioData);
      }, 100);
      
      // Store result for navigation
      localStorage.setItem('videoAdsState', JSON.stringify({
        step: 'audio',
        data: { ...data, audioResult: result }
      }));

      console.log('Audio generation completed:', result);

    } catch (err: any) {
      console.error('Audio generation error:', err);
      setError(err.message || 'Failed to generate audio. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePlayAudio = (audioUrl: string, audioId: string) => {
    // Stop any currently playing audio
    if (currentlyPlaying && audioElements[currentlyPlaying]) {
      audioElements[currentlyPlaying].pause();
      audioElements[currentlyPlaying].currentTime = 0;
    }

    if (currentlyPlaying === audioId) {
      // If same audio, just stop
      setCurrentlyPlaying(null);
      return;
    }

    // Create or get audio element
    let audio = audioElements[audioId];
    if (!audio) {
      audio = new (window as any).Audio(audioUrl) as HTMLAudioElement;
      audio.onended = () => setCurrentlyPlaying(null);
      setAudioElements(prev => ({ ...prev, [audioId]: audio }));
    }

    // Play new audio
    audio.play();
    setCurrentlyPlaying(audioId);
  };

  const handleRetryGeneration = () => {
    if (voiceActorData) {
      generateAudio(voiceActorData);
    }
  };

  const handleManualTest = () => {
    const testData = {
      threadId: 'test-thread-123',
      campaignScripts: {
        campaign_scripts: {
          angles: [{
            selected_angle: {
              id: 'angle_1',
              angle: 1,
              category: 'UVT',
              concept: 'Test concept',
              type: 'positive'
            },
            hooks: [{
              selected_hook: {
                id: 'hook_1_1',
                hook_text: 'Ready for real income without leaving your job?',
                hook_type: 'direct_question'
              },
              scripts: [{
                id: 'script_1_1_1',
                version: 'A',
                content: 'Ready for real income without leaving your job? Test content here for audio generation.',
                cta: 'Test CTA',
                target_emotion: 'Hope'
              }]
            }]
          }]
        }
      },
      selectedVoice: {
        voice_id: '21m00Tcm4TlvDq8ikWAM',
        name: 'Rachel',
        category: 'premade'
      },
      selectedActor: {
        id: 'actor_2',
        name: 'Professional Business Woman',
        category: 'business'
      }
    };
    
    setVoiceActorData(testData);
    generateAudio(testData);
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const transformCampaignScriptsForBackend = (campaignScripts: any) => {
    console.log('Transforming campaign scripts:', campaignScripts);
    
    // Handle the nested structure from Scripts page
    let anglesData = [];
    
    if (campaignScripts?.campaign_scripts?.angles) {
      anglesData = campaignScripts.campaign_scripts.angles;
    } else if (campaignScripts?.angles) {
      anglesData = campaignScripts.angles;
    } else {
      console.error('Invalid campaign scripts structure:', campaignScripts);
      return { selected_angle: {}, scripts: [] };
    }
    
    // Extract scripts from the nested structure and flatten them
    const flattenedScripts: any[] = [];
    let selectedAngle = {};
    
    anglesData.forEach((angle: any) => {
      // Use the first angle as the selected angle
      if (Object.keys(selectedAngle).length === 0 && angle.selected_angle) {
        selectedAngle = angle.selected_angle;
      }
      
      angle.hooks?.forEach((hook: any) => {
        hook.scripts?.forEach((script: any) => {
          const transformedScript = {
            script_id: script.id || script.script_id || `script_${Date.now()}_${Math.random()}`,
            hook: hook.selected_hook?.hook_text || hook.hook_text || '',
            body: script.content || script.body || '',
            selected: true // All scripts passed to this page are considered selected
          };
          flattenedScripts.push(transformedScript);
        });
      });
    });
    
    const transformed = {
      selected_angle: selectedAngle,
      scripts: flattenedScripts
    };
    
    console.log('Transformed structure:', transformed);
    return transformed;
  };

  // Early return for missing data
  if (error && !voiceActorData) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert 
            severity="error" 
            action={
              <Button 
                color="inherit" 
                size="small" 
                onClick={() => navigate('/video-ads/voice-actor')}
              >
                Go Back
              </Button>
            }
          >
            {error}
          </Alert>
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
            
            {audioData && (
              <Chip 
                icon={<CheckCircleIcon />} 
                label={`${audioData.total_audios_generated} Audios Generated`}
                color="success" 
                variant="outlined" 
              />
            )}
          </Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Generated Audio
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Listen to your generated audio content for each hook and script
          </Typography>
        </Box>

        {/* Voice & Actor Info */}
        {audioData && (
          <Card sx={{ mb: 4, background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Voice & Actor Selection
              </Typography>
              <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <VolumeIcon color="primary" />
                  <Box>
                    <Typography variant="subtitle1">
                      {audioData.voice_info.voice.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {audioData.voice_info.voice.description}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <PersonIcon color="primary" />
                  <Box>
                    <Typography variant="subtitle1">
                      {audioData.voice_info.actor.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {audioData.voice_info.actor.description}
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {loading && (
          <Card sx={{ mb: 4 }}>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <CircularProgress sx={{ mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Generating Audio...
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Please wait while we create audio for your scripts and hooks
              </Typography>
              <LinearProgress sx={{ mt: 2, width: '100%' }} />
            </CardContent>
          </Card>
        )}

        {/* Error State */}
        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 4 }}
            action={
              <Button 
                color="inherit" 
                size="small" 
                startIcon={<RefreshIcon />}
                onClick={handleRetryGeneration}
              >
                Retry
              </Button>
            }
          >
            {error}
          </Alert>
        )}

        

        {/* Generated Audio Content */}
        {audioData && audioData.scripts_with_audio && Array.isArray(audioData.scripts_with_audio) && audioData.scripts_with_audio.length > 0 && (
          <Box sx={{ mb: 4 }}>
            <Box sx={{ 
              display: 'grid', 
              gridTemplateColumns: { 
                xs: 'repeat(2, 1fr)', 
                sm: 'repeat(3, 1fr)', 
                md: 'repeat(4, 1fr)' 
              }, 
              gap: 2 
            }}>
              {audioData.scripts_with_audio.map((scriptData, index) => {
                // Use combined audio if available, otherwise fallback to separate audios
                const audioToShow = scriptData.combined_audio || scriptData.hook_audio || scriptData.script_audio;
                const contentToShow = scriptData.combined_audio 
                  ? `${scriptData.hook}. ${scriptData.body}` 
                  : (scriptData.hook_audio ? scriptData.hook : scriptData.body);
                
                if (!audioToShow) {
                  return null;
                }
                
                return (
                  <Card 
                    key={`audio-${scriptData.script_id}`}
                    sx={{ 
                      cursor: 'pointer',
                      transition: 'all 0.2s ease-in-out',
                      borderRadius: 2,
                      
                      display: 'flex',
                      flexDirection: 'column',
                      '&:hover': {
                        boxShadow: 3,
                        transform: 'translateY(-2px)'
                      }
                    }}
                  >
                    <CardContent sx={{ p: 2, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                      {/* Audio Type Header */}
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <AudioIcon sx={{ mr: 1, color: 'primary.main', fontSize: 20 }} />
                        <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 600 }}>
                          {scriptData.combined_audio ? `Script ${index + 1}` : 
                           `${scriptData.hook_audio ? 'Hook' : 'Script'} ${index + 1}`}
                        </Typography>
                      </Box>
                      
                      {/* Play Button and Info */}
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                        <IconButton
                          color="primary"
                          onClick={() => handlePlayAudio(
                            `http://localhost:8001${audioToShow.audio_url}`,
                            audioToShow.audio_id
                          )}
                          sx={{ 
                            bgcolor: currentlyPlaying === audioToShow.audio_id ? 'primary.light' : 'transparent',
                            '&:hover': { bgcolor: 'primary.light' }
                          }}
                        >
                          {currentlyPlaying === audioToShow.audio_id ? 
                            <PauseIcon /> : <PlayIcon />
                          }
                        </IconButton>
                        <Typography variant="caption" color="text.secondary">
                          {formatFileSize(audioToShow.file_size)}
                        </Typography>
                      </Box>

                      {/* Script Breakdown */}
                      <Box sx={{ 
                        bgcolor: 'grey.50', 
                        borderRadius: 1, 
                        p: 1.5, 
                        border: '1px solid',
                        borderColor: 'grey.200'
                      }}>
                        <Box sx={{ mb: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'primary.main' }}>
                            Hook:
                          </Typography>
                          <Typography variant="body2" sx={{ fontSize: '0.8rem', mt: 0.5 }}>
                            {scriptData.hook}
                          </Typography>
                        </Box>
                        <Box sx={{ mb: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'secondary.main' }}>
                            Script:
                          </Typography>
                          <Typography variant="body2" sx={{ fontSize: '0.8rem', mt: 0.5 }}>
                            {scriptData.body}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.main' }}>
                            Call to Action:
                          </Typography>
                          <Typography variant="body2" sx={{ fontSize: '0.8rem', mt: 0.5 }}>
                            {scriptData.call_to_action || 'Not specified'}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                );
              }).filter(Boolean)}
            </Box>
          </Box>
        )}

        {/* Navigation */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/video-ads/voice-actor')}
          >
            Back to Voice & Actor
          </Button>
          
          {audioData && (
            <Button
              variant="contained"
              size="large"
              onClick={() => {
                // Navigate to video generation page
                console.log('🚀 Audio -> Video navigation');
                console.log('📋 voiceActorData structure:', JSON.stringify(voiceActorData, null, 2));
                console.log('📋 audioData structure:', JSON.stringify(audioData, null, 2));
                const dataToPass = { 
                  ...voiceActorData, 
                  audioResult: audioData 
                };
                console.log('📦 Complete data package for video:', JSON.stringify(dataToPass, null, 2));
                
                navigate('/video-ads/video', { 
                  state: { 
                    data: dataToPass
                  } 
                });
              }}
            >
              Continue to Video Generation
            </Button>
          )}
        </Box>
      </Box>
    </Container>
  );
};

export default Audio;
