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
import { getCampaignId } from '../../utils/v3-migration';

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

interface AudioGenerationV2Response {
  conversation_id: string; // V2: conversation_id instead of thread_id
  selected_angle: any;
  voice_info: {
    voice?: any;
    actor?: any;
    selected_voice?: any;
    selected_actor?: any;
  };
  scripts_with_audio: ScriptWithAudio[];
  total_audios_generated: number;
  status: string;
}

const AudioV2: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  
  // State management
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioData, setAudioData] = useState<AudioGenerationV2Response | null>(null);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
  const [audioElements, setAudioElements] = useState<{ [key: string]: HTMLAudioElement }>({});
  
  // Data from previous page (V2: different state management)
  const [voiceActorData, setVoiceActorData] = useState<any>(null);
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
        console.log('🔄 V3: Loading audio data from database for campaign:', state.campaignId);
        await loadAudioFromDatabase(state.campaignId);
      } 
      // Check if we're resuming from campaigns list
      else if (state.resumeFromStep && state.conversationId && !state.data) {
        // Load data from database for resume scenario
        await loadDataForResume(state.conversationId);
      } else if (state.data) {
        setVoiceActorData(state.data);
        const campaignIdValue = state.data.campaign_id || state.data.conversation_id || state.conversationId || state.campaignId || '';
        setCampaignId(campaignIdValue);
        
        // ALWAYS check for existing audio first to avoid regeneration
        console.log('🔍 Checking for existing audio before generating...');
        
        // Try to load existing audio from database first
        if (campaignIdValue) {
          const existingAudio = await checkForExistingAudio(campaignIdValue);
          
          if (existingAudio) {
            console.log('✅ Found existing audio in database, not regenerating');
            setAudioData(existingAudio);
            setLoading(false);
            return; // Exit early, no need to generate
          }
        }
        
        // If no existing audio found, check if we have passed audio data
        if (state.data.audioResult) {
          console.log('✅ Using passed audio data');
          setAudioData(state.data.audioResult);
        } else if (state.data.scripts_with_audio) {
          console.log('✅ Using passed scripts_with_audio');
          // Create a proper AudioGenerationV2Response object
          const audioResponse: AudioGenerationV2Response = {
            conversation_id: state.conversationId || state.data.campaign_id || state.data.conversation_id || '',
            scripts_with_audio: state.data.scripts_with_audio,
            selected_angle: state.data.selected_angle || null,
            voice_info: state.data.voice_info || {},
            total_audios_generated: state.data.scripts_with_audio?.length || 0,
            status: 'success'
          };
          setAudioData(audioResponse);
        } else {
          // Only generate if no existing audio found
          console.log('🎵 No existing audio found, generating for the first time');
          generateAudio(state.data);
        }
      } else {
        setError('Missing required data. Please go back to voice & actor selection.');
      }
    } catch (e) {
      setError('Failed to load page data. Please try again.');
    }
  };

  const checkForExistingAudio = async (campaignId: string): Promise<any> => {
    try {
      const token = getValidToken(session);
      if (!token) {
        console.log('❌ No token available for checking existing audio');
        return null;
      }

      console.log('🔍 Checking for existing audio for campaign:', campaignId);

      // V3: Check for existing audio data in database
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
        console.log('❌ Failed to fetch existing audio, status:', response.status);
        return null;
      }

      const audioData = await response.json();
      console.log('📦 Audio data from database:', audioData);
      
      // Check if audio exists with valid URLs
      if (audioData.status === 'not_found' || !audioData.scripts_with_audio || audioData.scripts_with_audio.length === 0) {
        console.log('❌ No audio found or status is not_found');
        return null;
      }
      
      // Check if audio files have valid URLs
      const hasValidAudio = audioData.scripts_with_audio.some((s: any) => 
        (s.combined_audio_url || s.hook_audio_url || s.script_audio_url)
      );
      
      console.log('✅ Has valid audio with URLs:', hasValidAudio);
      
      if (!hasValidAudio) {
        console.log('❌ No valid audio URLs found');
        return null;
      }
      
      console.log('✅ Returning existing audio data to reuse');
      return audioData;
      
    } catch (err: any) {
      console.error('Error checking for existing audio:', err);
      return null;
    }
  };

  const loadAudioFromDatabase = async (campaignId: string) => {
    setLoading(true);
    setError(null);
    setCampaignId(campaignId);
    
    try {
      const token = getValidToken(session);
      if (!token) {
        throw new Error('Authentication required');
      }

      // V3: Load audio data from database
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
        if (response.status === 404) {
          // No audio data yet, need to generate
          setError('No audio data found. Please return to voice selection.');
        } else {
          throw new Error(`Failed to load audio data: ${response.statusText}`);
        }
        return;
      }

      const audioData = await response.json();
      
      if (audioData.status === 'not_found') {
        setError('No audio data found. Please return to voice selection.');
        return;
      }
      
      // Set the audio data
      setAudioData(audioData);
      
      // Also set voice actor data if available
      if (audioData.voice_info) {
        setVoiceActorData({
          voice_actor_selection: audioData.voice_info,
          campaign_id: campaignId
        });
      }
      
      console.log('✅ V3: Loaded audio data from database');
      
    } catch (err: any) {
      console.error('Error loading audio data:', err);
      setError(err.message || 'Failed to load audio data.');
    } finally {
      setLoading(false);
    }
  };

  const loadDataForResume = async (conversationId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const token = getValidToken(session);
      if (!token) {
        throw new Error('Authentication required');
      }

      // Load campaign scripts and selections from database
      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${campaignId}/resume-audio`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to load campaign data: ${response.statusText}`);
      }

      const resumeData = await response.json();
      
      // Reconstruct the data structure needed for audio generation
      const reconstructedData = {
        conversation_id: conversationId,
        campaign_scripts: resumeData.scripts_data,
        voice_actor_selection: {
          voice: resumeData.voice_data,
          actor: resumeData.actor_data
        }
      };

      setVoiceActorData(reconstructedData);
      setCampaignId(conversationId);
      
      // Generate audio with the loaded data
      generateAudio(reconstructedData);
      
    } catch (err: any) {
      console.error('Error loading resume data:', err);
      setError(err.message || 'Failed to load campaign data for resume.');
      setLoading(false);
    }
  };

  const generateAudio = async (data: any) => {
    setLoading(true);
    setError(null);

    try {
      const token = getValidToken(session);
      
      // Transform the nested campaign scripts structure to match backend expectations
      const transformedScripts = transformCampaignScriptsForBackend(data.campaign_scripts);
      
      console.log('🔍 Debug V2 campaign_scripts input:', data.campaign_scripts);
      console.log('🔍 Debug V2 transformedScripts output:', transformedScripts);
      
      if (!transformedScripts.scripts || transformedScripts.scripts.length === 0) {
        console.error('❌ No scripts after transformation!');
        throw new Error('No scripts provided');
      }
      
      const requestPayload = {
        conversation_id: (data.campaign_id || data.conversation_id), // V2: conversation_id instead of thread_id
        voice_actor_selection: data.voice_actor_selection,
        campaign_scripts: transformedScripts
      };

      console.log('V2 Generating audio with payload:', requestPayload);

      // V2: Call V2 audio endpoint
      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v2/audio`, {
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
      const result: AudioGenerationV2Response = JSON.parse(responseText);
      
      setAudioData(result);
      localStorage.setItem('audioV2Data', responseText); // V2: different localStorage key
      console.log('🔍 V2 audioData.scripts_with_audio length:', result.scripts_with_audio?.length);
      
      // Force a re-render by adding a small delay
      setTimeout(() => {
        console.log('🔍 V2 audioData state after timeout:', audioData);
      }, 100);
      
      // Store result for navigation (V2: different storage key)
      localStorage.setItem('videoAdsV2State', JSON.stringify({
        step: 'audio',
        data: { ...data, audioResult: result }
      }));

      console.log('V2 Audio generation completed:', result);

    } catch (err: any) {
      console.error('V2 Audio generation error:', err);
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

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const transformCampaignScriptsForBackend = (campaignScripts: any) => {
    console.log('V2 Transforming campaign scripts:', campaignScripts);
    
    // Handle the nested structure from Scripts page
    let anglesData = [];
    
    if (campaignScripts?.campaign_scripts?.angles) {
      anglesData = campaignScripts.campaign_scripts.angles;
    } else if (campaignScripts?.angles) {
      anglesData = campaignScripts.angles;
    } else {
      console.error('Invalid V2 campaign scripts structure:', campaignScripts);
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
    
    console.log('V2 Transformed structure:', transformed);
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
                onClick={() => navigate('/video-ads-v2/voice-actor', {
                  state: { 
                    campaignId: campaignId,  // V3: Only pass campaignId when going back
                    isFromAudio: true  // Flag to indicate coming from audio
                  }
                })}
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
                label={`${audioData.total_audios_generated || 0} Audios Generated`}
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
          {campaignId && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Campaign: {campaignId}
            </Typography>
          )}
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
                      {audioData.voice_info?.selected_voice?.name || audioData.voice_info?.voice?.name || 'Voice Name'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {audioData.voice_info?.selected_voice?.description || audioData.voice_info?.voice?.description || 'Voice Description'}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <PersonIcon color="primary" />
                  <Box>
                    <Typography variant="subtitle1">
                      {audioData.voice_info?.selected_actor?.name || audioData.voice_info?.actor?.name || 'Actor Name'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {audioData.voice_info?.selected_actor?.description || audioData.voice_info?.actor?.description || 'Actor Description'}
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
                            `${audioToShow.audio_url}`, // V2: Use direct audio URL
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
            onClick={() => {
              // DEBUGGER: Check what Audio page is passing back to VoiceActor
              debugger; // 🔴 BREAKPOINT 4: Check state from Audio to VoiceActor
              console.log('🔴 DEBUG POINT 4 - Audio navigating to VoiceActor with:', {
                currentLocationState: location.state,
                voiceActorData,
                audioData,
                campaignId
              });
              
              navigate('/video-ads-v2/voice-actor', {
                state: { 
                  campaignId: campaignId,  // V3: Only pass campaignId when going back
                  isFromAudio: true,  // Flag to indicate coming from audio
                  isFromVideo: location.state?.isFromVideo  // Preserve the isFromVideo flag if it exists
                }
              });
            }}
          >
            Back to Voice & Actor
          </Button>
          
          {audioData && (
            <Button
              variant="contained"
              size="large"
              onClick={() => {
                // Navigate to V2 video generation page
                console.log('🚀 V2 Audio -> Video navigation');
                console.log('📋 V2 voiceActorData structure:', JSON.stringify(voiceActorData, null, 2));
                console.log('📋 V2 audioData structure:', JSON.stringify(audioData, null, 2));
                const dataToPass = { 
                  ...voiceActorData, 
                  audioResult: audioData 
                };
                console.log('📦 V2 Complete data package for video:', JSON.stringify(dataToPass, null, 2));
                
                navigate('/video-ads-v2/video', { state: { 
                    data: dataToPass,
                    campaignId: campaignId, // V3
        conversationId: campaignId // Legacy support
                  } });
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

export default AudioV2;
