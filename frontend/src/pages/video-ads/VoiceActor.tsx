import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';
import {
  Container,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Button,
  Box,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
  Avatar,
  RadioGroup,
  FormControlLabel,
  Radio
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  VolumeUp as VolumeIcon,
  Person as PersonIcon
} from '@mui/icons-material';

interface ElevenLabsVoice {
  voice_id: string;
  name: string;
  description?: string;
  category?: string;
  labels: string[];
  preview_url?: string;
  gender?: string;
  age?: string;
  accent?: string;
  use_case?: string;
}

interface ActorImage {
  filename: string;
  name: string;
  description: string;
  category: string;
}

interface VoiceActorData {
  voices: ElevenLabsVoice[];
  actors: ActorImage[];
  status: string;
}

const VoiceActor: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();

  // State management
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [voiceActorData, setVoiceActorData] = useState<VoiceActorData | null>(null);
  const [selectedVoice, setSelectedVoice] = useState<ElevenLabsVoice | null>(null);
  const [selectedActor, setSelectedActor] = useState<ActorImage | null>(null);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  
  // Pagination state
  const [voicesDisplayCount, setVoicesDisplayCount] = useState(8);
  const [actorsDisplayCount, setActorsDisplayCount] = useState(8);

  // Data from previous page
  const [campaignScripts, setCampaignScripts] = useState<any>(null);
  const [threadId, setThreadId] = useState<string>('');

  useEffect(() => {
    initializePageData();
  }, []);

  const initializePageData = () => {
    try {
      // Get data from navigation state or localStorage
      const state = location.state || JSON.parse(localStorage.getItem('videoAdsState') || '{}');
      
      // Check for test data first
      let testData = null;
      try {
        const testDataStr = localStorage.getItem('videoAdsTestData');
        if (testDataStr) {
          testData = JSON.parse(testDataStr);
          // Clear test data after using it
          localStorage.removeItem('videoAdsTestData');
        }
      } catch (e) {
        console.log('No test data found');
      }
      
      if (testData || state.selectedScripts || state.data) {
        // Handle data from test button, Scripts page navigation, or stored data
        const scripts = testData || state.selectedScripts || state.data?.campaignScripts || state.data;
        const threadIdFromState = state.threadId || state.data?.threadId || '';
        
        setCampaignScripts(scripts);
        setThreadId(threadIdFromState);
        
        // Fetch voice actor data
        fetchVoiceActorData(threadIdFromState, scripts);
      } else {
        // For direct navigation/testing, create mock data
        const mockScripts = {
          campaign_scripts: {
            angles: [
              {
                selected_angle: {
                  id: "1",
                  angle: "Problem-Solution Focus",
                  category: "pain-point",
                  concept: "Highlight customer pain points and offer solution"
                },
                hooks: [
                  {
                    selected_hook: {
                      id: "1", 
                      hook: "Are you tired of complicated solutions?",
                      category: "question"
                    },
                    scripts: [
                      {
                        id: "1",
                        script: "Are you tired of complicated solutions that just don't work? Our simple, effective approach delivers real results in minutes, not hours.",
                        duration: 30,
                        tone: "conversational"
                      }
                    ]
                  }
                ]
              }
            ]
          }
        };
        setCampaignScripts(mockScripts);
        setThreadId('mock-thread-id');
        
        // Fetch voice actor data with mock data
        fetchVoiceActorData('mock-thread-id', mockScripts);
      }
    } catch (error) {
      console.error('Failed to initialize page data:', error);
      setError('Failed to load page data. Please try again.');
      setLoading(false);
    }
  };

  const fetchVoiceActorData = async (threadId: string, scripts?: any) => {
    try {
      setLoading(true);
      setError(null);

      // Use provided scripts or fall back to state
      const scriptsToSend = scripts || campaignScripts;
      
      if (!scriptsToSend) {
        setError('No scripts data available');
        return;
      }

      // Get valid token (JWT or dev-token fallback)
      const token = getValidToken(session);
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8001';
      
      console.log('🔍 VoiceActor API Debug:', {
        token: token?.substring(0, 20) + '...',
        tokenLength: token?.length,
        apiUrl,
        hasSession: !!session,
        scriptsCount: scriptsToSend.length
      });

      let response = await fetch(`${apiUrl}/video-ads/voice-actor`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          thread_id: threadId,
          campaign_scripts: scriptsToSend
        })
      });

      // If JWT token fails with 401/403, try dev-token
      if (!response.ok && (response.status === 401 || response.status === 403) && token !== 'dev-token') {
        console.warn('⚠️ JWT token failed, retrying with dev-token');
        response = await fetch(`${apiUrl}/video-ads/voice-actor`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer dev-token'
          },
          body: JSON.stringify({
            thread_id: threadId,
            campaign_scripts: scriptsToSend
          })
        });
      }

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ VoiceActor API Error:', {
          status: response.status,
          statusText: response.statusText,
          errorText
        });
        throw new Error(`Failed to fetch voice actors: ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ VoiceActor API Success:', { 
        voicesCount: data.eleven_labs_voices?.length || 0,
        actorsCount: data.actor_images?.length || 0
      });
      setVoiceActorData(data);
      
    } catch (error) {
      console.error('Failed to fetch voice actor data:', error);
      setError(error instanceof Error ? error.message : 'Failed to load voice actors');
    } finally {
      setLoading(false);
    }
  };

  const playVoicePreview = (voice: ElevenLabsVoice) => {
    try {
      // Stop current audio if playing
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }

      if (playingVoice === voice.voice_id) {
        // Stop if same voice is clicked
        setPlayingVoice(null);
        setCurrentAudio(null);
        return;
      }

      if (voice.preview_url) {
        const audio = new Audio(voice.preview_url);
        setCurrentAudio(audio);
        setPlayingVoice(voice.voice_id);

        audio.addEventListener('ended', () => {
          setPlayingVoice(null);
          setCurrentAudio(null);
        });

        audio.play().catch(error => {
          console.error('Failed to play audio:', error);
          setPlayingVoice(null);
          setCurrentAudio(null);
        });
      }
    } catch (error) {
      console.error('Error playing voice preview:', error);
    }
  };

  const handleContinue = () => {
    if (!selectedVoice || !selectedActor) {
      setError('Please select both a voice and an actor to continue.');
      return;
    }

    // Prepare data for next page
    const nextPageData = {
      threadId,
      campaignScripts,
      selectedVoice,
      selectedActor
    };

    console.log('🚀 VoiceActor -> Audio navigation');
    console.log('📋 ThreadId:', threadId);
    console.log('🎤 Selected Voice:', selectedVoice);
    console.log('🎭 Selected Actor:', selectedActor);
    console.log('📝 Campaign Scripts structure:', campaignScripts);
    console.log('📦 Complete data package:', nextPageData);

    // Store in localStorage for navigation
    localStorage.setItem('videoAdsState', JSON.stringify({
      step: 'audio',
      data: nextPageData
    }));

    console.log('💾 Data stored in localStorage for navigation');

    // Navigate to audio page
    navigate('/video-ads/audio', { state: { data: nextPageData } });
  };

  const getVoiceCategoryColor = (category: string) => {
    const colors: { [key: string]: string } = {
      'narration': '#1976d2',
      'conversational': '#388e3c',
      'character': '#f57c00',
      'news': '#7b1fa2',
      'general': '#616161'
    };
    return colors[category?.toLowerCase()] || colors.general;
  };

  const getActorCategoryColor = (category: string) => {
    const colors: { [key: string]: string } = {
      'business': '#1565c0',
      'executive': '#2e7d32',
      'technology': '#ed6c02',
      'sales': '#d32f2f',
      'finance': '#7b1fa2'
    };
    return colors[category?.toLowerCase()] || '#616161';
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading voice actors...
        </Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button 
          variant="contained" 
          onClick={() => navigate('/video-ads/scripts')}
        >
          Back to Scripts
        </Button>
      </Container>
    );
  }

  const displayedVoices = voiceActorData?.voices.slice(0, voicesDisplayCount) || [];
  const displayedActors = voiceActorData?.actors.slice(0, actorsDisplayCount) || [];
  const hasMoreVoices = (voiceActorData?.voices.length || 0) > voicesDisplayCount;
  const hasMoreActors = (voiceActorData?.actors.length || 0) > actorsDisplayCount;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Choose Voice & Actor
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Select one voice and one actor for your video ads
        </Typography>
      </Box>

      {/* Voice Selection */}
      <Box sx={{ mb: 6 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <VolumeIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
          <Box>
            <Typography variant="h5" component="h2" gutterBottom>
              Select Voice
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose a voice that matches your brand personality and target audience
            </Typography>
          </Box>
        </Box>
        
        <RadioGroup
          value={selectedVoice?.voice_id || ''}
          onChange={(e) => {
            const voice = voiceActorData?.voices.find(v => v.voice_id === e.target.value);
            setSelectedVoice(voice || null);
          }}
        >
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { 
              xs: '1fr', 
              sm: 'repeat(1, 1fr)', 
              md: 'repeat(2, 1fr)' 
            }, 
            gap: 2 
          }}>
            {displayedVoices.map((voice) => (
              <Card 
                key={voice.voice_id}
                sx={{ 
                  border: selectedVoice?.voice_id === voice.voice_id ? 2 : 1,
                  borderColor: selectedVoice?.voice_id === voice.voice_id ? 'primary.main' : 'divider',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    borderColor: 'primary.light',
                    boxShadow: 2
                  }
                }}
                onClick={() => setSelectedVoice(voice)}
              >
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                      <FormControlLabel
                        value={voice.voice_id}
                        control={<Radio />}
                        label=""
                        sx={{ mr: 2, mt: 0 }}
                      />
                      <VolumeIcon sx={{ mr: 2, color: 'primary.main' }} />
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                          {voice.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {voice.gender}
                        </Typography>
                        {voice.description && (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {voice.description.split('.')[0] + (voice.description.includes('.') ? '.' : '')}
                          </Typography>
                        )}
                        
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                          {voice.accent && (
                            <Chip 
                              label={voice.accent}
                              size="small"
                              variant="outlined"
                              sx={{ 
                                borderColor: 'primary.main',
                                color: 'primary.main',
                                fontWeight: 500
                              }}
                            />
                          )}
                          {voice.age && (
                            <Chip 
                              label={voice.age.replace('_', ' ')}
                              size="small"
                              variant="outlined"
                              sx={{ 
                                borderColor: 'primary.main',
                                color: 'primary.main',
                                fontWeight: 500
                              }}
                            />
                          )}
                        </Box>
                      </Box>
                    </Box>
                    
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={playingVoice === voice.voice_id ? <PauseIcon /> : <PlayIcon />}
                      onClick={(e) => {
                        e.stopPropagation();
                        playVoicePreview(voice);
                      }}
                      sx={{ 
                        minWidth: 90,
                        textTransform: 'none',
                        fontWeight: 500
                      }}
                    >
                      Preview
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </RadioGroup>

        {hasMoreVoices && (
          <Box sx={{ textAlign: 'center', mt: 3 }}>
            <Button
              variant="outlined"
              onClick={() => setVoicesDisplayCount(prev => prev + 8)}
              sx={{ textTransform: 'none', fontWeight: 500 }}
            >
              Load More Voices ({(voiceActorData?.voices.length || 0) - voicesDisplayCount} remaining)
            </Button>
          </Box>
        )}
      </Box>

      {/* Actor Selection */}
      <Box sx={{ mb: 6 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <PersonIcon sx={{ fontSize: 32, mr: 2, color: 'primary.main' }} />
          <Box>
            <Typography variant="h5" component="h2" gutterBottom>
              Select Actor Image
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose a professional actor image that represents your brand
            </Typography>
          </Box>
        </Box>
        
        <RadioGroup
          value={selectedActor?.filename || ''}
          onChange={(e) => {
            const actor = voiceActorData?.actors.find(a => a.filename === e.target.value);
            setSelectedActor(actor || null);
          }}
        >
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { 
              xs: 'repeat(2, 1fr)', 
              sm: 'repeat(3, 1fr)', 
              md: 'repeat(4, 1fr)' 
            }, 
            gap: 2 
          }}>
            {displayedActors.map((actor) => (
              <Card 
                key={actor.filename}
                sx={{ 
                  border: selectedActor?.filename === actor.filename ? 2 : 1,
                  borderColor: selectedActor?.filename === actor.filename ? 'primary.main' : 'divider',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  borderRadius: 2,
                  overflow: 'hidden',
                  height: 220,
                  position: 'relative',
                  '&:hover': {
                    borderColor: 'primary.light',
                    boxShadow: 2
                  }
                }}
                onClick={() => setSelectedActor(actor)}
              >
                {/* Full height image */}
                <CardMedia
                  component="img"
                  height="220"
                  image={`/actors/${actor.filename}`}
                  alt={actor.name}
                  sx={{ 
                    objectFit: 'cover',
                    width: '100%',
                    height: '100%',
                    position: 'absolute',
                    top: 0,
                    left: 0
                  }}
                  onError={(e) => {
                    // Fallback to placeholder if image doesn't load
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent) {
                      parent.innerHTML = `
                        <div style="
                          width: 100%; 
                          height: 220px; 
                          display: flex; 
                          align-items: center; 
                          justify-content: center;
                          background-color: #e0e0e0;
                          position: absolute;
                          top: 0;
                          left: 0;
                        ">
                          <svg width="60" height="60" viewBox="0 0 24 24" fill="#bdbdbd">
                            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                          </svg>
                        </div>
                      `;
                    }
                  }}
                />
                
                {/* Radio button overlay */}
                <Box sx={{ position: 'absolute', top: 8, left: 8, zIndex: 2 }}>
                  <FormControlLabel
                    value={actor.filename}
                    control={
                      <Radio 
                        sx={{ 
                          bgcolor: 'rgba(255, 255, 255, 0.9)',
                          borderRadius: '50%',
                          p: 0.5
                        }} 
                      />
                    }
                    label=""
                  />
                </Box>

                {/* Text overlay at bottom */}
                <Box 
                  sx={{ 
                    position: 'absolute', 
                    bottom: 0, 
                    left: 0, 
                    right: 0, 
                    background: 'linear-gradient(transparent, rgba(0, 0, 0, 0.7))',
                    color: 'white',
                    p: 2,
                    textAlign: 'center',
                    zIndex: 2
                  }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5, fontSize: '0.95rem' }}>
                    {actor.name}
                  </Typography>
                  <Typography variant="body2" sx={{ fontSize: '0.85rem', opacity: 0.9 }}>
                    {actor.description}
                  </Typography>
                </Box>
              </Card>
            ))}
          </Box>
        </RadioGroup>

        {hasMoreActors && (
          <Box sx={{ textAlign: 'center', mt: 3 }}>
            <Button
              variant="outlined"
              onClick={() => setActorsDisplayCount(prev => prev + 8)}
              sx={{ textTransform: 'none', fontWeight: 500 }}
            >
              Load More Actors ({(voiceActorData?.actors.length || 0) - actorsDisplayCount} remaining)
            </Button>
          </Box>
        )}
      </Box>

      {/* Selection Summary */}
      {(selectedVoice || selectedActor) && (
        <Card sx={{ mb: 4, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Your Selection
            </Typography>
            
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 3 }}>
              {selectedVoice && (
                <Box sx={{ display: 'flex', alignItems: 'center', p: 2, bgcolor: '#f8f9fa', borderRadius: 1 }}>
                  <VolumeIcon sx={{ mr: 2, color: 'primary.main', fontSize: 28 }} />
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {selectedVoice.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {selectedVoice.description || `${selectedVoice.gender} ${selectedVoice.category} voice`}
                    </Typography>
                  </Box>
                </Box>
              )}
              
              {selectedActor && (
                <Box sx={{ display: 'flex', alignItems: 'center', p: 2, bgcolor: '#f8f9fa', borderRadius: 1 }}>
                  <PersonIcon sx={{ mr: 2, color: 'primary.main', fontSize: 28 }} />
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {selectedActor.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {selectedActor.description}
                    </Typography>
                  </Box>
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pt: 2 }}>
        <Button
          variant="outlined"
          onClick={() => navigate('/video-ads/scripts')}
          sx={{ 
            textTransform: 'none', 
            fontWeight: 500,
            px: 3,
            py: 1.5
          }}
        >
          Back to Scripts
        </Button>
        
        <Button
          variant="contained"
          size="large"
          onClick={handleContinue}
          disabled={!selectedVoice || !selectedActor}
          sx={{ 
            textTransform: 'none', 
            fontWeight: 600,
            px: 4,
            py: 1.5,
            fontSize: '1.1rem'
          }}
        >
          Continue to Audio Generation
        </Button>
      </Box>
    </Container>
  );
};

export default VoiceActor;
