import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';
import { getCampaignId } from '../../utils/v3-migration';
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

const VoiceActorV2: React.FC = () => {
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

  // Data from previous page (V2: using conversationId instead of threadId)
  const [campaignScripts, setCampaignScripts] = useState<any>(null);
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
      
      // Check for test data first
      let testData = null;
      try {
        const testDataStr = localStorage.getItem('videoAdsV2TestData');
        if (testDataStr) {
          testData = JSON.parse(testDataStr);
          // Clear test data after using it
          localStorage.removeItem('videoAdsV2TestData');
        }
      } catch (e) {
        console.log('No V2 test data found');
      }
      
      // V3: If coming back from Audio/Video with only campaignId, load scripts from database
      if (state && state.campaignId && state.isFromAudio && !state.selectedScripts && !state.data && !testData) {
        console.log('🔄 V3: Loading data from database for Voice Actor after returning from Audio');
        
        const token = getValidToken(session);
        if (token) {
          try {
            // Load scripts from database
            const scriptsResponse = await fetch(
              `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${state.campaignId}/scripts`,
              {
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                }
              }
            );

            if (scriptsResponse.ok) {
              const scriptsDataFromDB = await scriptsResponse.json();
              console.log('✅ V3: Loaded scripts from database for Voice Actor:', scriptsDataFromDB);
              
              // Extract the actual scripts data - use selected_scripts if available, otherwise scripts_data
              const scriptsData = scriptsDataFromDB.selected_scripts || scriptsDataFromDB.scripts_data || scriptsDataFromDB;
              
              // Set the scripts data
              setCampaignScripts(scriptsData);
              setCampaignId(state.campaignId);
              
              // Also load audio data to get previously selected voice/actor
              let previousVoiceInfo = null;
              try {
                const audioResponse = await fetch(
                  `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${state.campaignId}/audio`,
                  {
                    headers: {
                      'Authorization': `Bearer ${token}`,
                      'Content-Type': 'application/json'
                    }
                  }
                );
                
                if (audioResponse.ok) {
                  const audioData = await audioResponse.json();
                  if (audioData.voice_info) {
                    console.log('✅ V3: Found previous voice/actor selection in database');
                    previousVoiceInfo = audioData.voice_info;
                  }
                }
              } catch (error) {
                console.log('No previous audio/voice selection found');
              }
              
              // Fetch voice actor data with the loaded scripts and previous voice info
              if (state.campaignId) {
                fetchVoiceActorData(state.campaignId, scriptsData, previousVoiceInfo);
              }
              return; // Exit early after loading from database
            }
          } catch (error) {
            console.error('Error loading scripts from database:', error);
          }
        }
      }
      
      if (testData || state.selectedScripts || state.data) {
        // Handle data from test button, Scripts page navigation, or stored data
        const dataToUse = testData || state.selectedScripts || state.data;
        
        console.log('V2 VoiceActor received data:', dataToUse);
        
        setCampaignScripts(dataToUse);
        
        // Extract campaign ID (V3: campaignId for stateless architecture)
        const campaignIdValue = state.campaignId || dataToUse.conversation_id || state.conversationId || '';
        setCampaignId(campaignIdValue);
        
        if (campaignIdValue) {
          // V3: Always try to load previous voice/actor selection from database
          let previousVoiceInfo = null;
          const token = getValidToken(session);
          if (token && campaignIdValue) {
            try {
              const audioResponse = await fetch(
                `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${campaignIdValue}/audio`,
                {
                  headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                  }
                }
              );
              
              if (audioResponse.ok) {
                const audioData = await audioResponse.json();
                if (audioData.voice_info) {
                  console.log('✅ V3: Found previous voice/actor selection in database');
                  previousVoiceInfo = audioData.voice_info;
                }
              }
            } catch (error) {
              console.log('No previous audio/voice selection found');
            }
          }
          
          fetchVoiceActorData(campaignIdValue, dataToUse, previousVoiceInfo);
        } else {
          setError('No campaign ID found. Please start from the beginning.');
          setLoading(false);
        }
      } else {
        setError('No campaign scripts data found. Please go back to the scripts page.');
        setLoading(false);
      }
    } catch (error) {
      console.error('Error initializing V2 VoiceActor page:', error);
      setError('Failed to load page data. Please try again.');
      setLoading(false);
    }
  };

  const fetchVoiceActorData = async (convId: string, scriptsData: any, previousVoiceInfo?: any) => {
    try {
      setLoading(true);
      
      const token = getValidToken(session);
      if (!token) {
        throw new Error('Authentication required');
      }

      // V2: Call V2 voice-actor endpoint
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/video-ads-v2/voice-actor`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          campaign_id: convId, // V3: campaign_id for stateless architecture
          campaign_scripts: scriptsData
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('V2 Voice Actor data received:', data);
      
      setVoiceActorData(data);
      setError(null);
      
      // Check if we have voice_info to restore selections (from previousVoiceInfo parameter or state)
      const state = location.state;
      const voiceInfoToRestore = previousVoiceInfo || state?.data?.voice_info;
      
      if (voiceInfoToRestore) {
        const voiceInfo = voiceInfoToRestore;
        
        // Restore selected voice
        if (voiceInfo.selected_voice && data.voices) {
          const matchingVoice = data.voices.find(
            (v: ElevenLabsVoice) => v.voice_id === voiceInfo.selected_voice.voice_id
          );
          if (matchingVoice) {
            setSelectedVoice(matchingVoice);
            console.log('✅ Restored selected voice:', matchingVoice.name);
          }
        }
        
        // Restore selected actor  
        if (voiceInfo.selected_actor && data.actors) {
          const matchingActor = data.actors.find(
            (a: ActorImage) => a.filename === voiceInfo.selected_actor.filename
          );
          if (matchingActor) {
            setSelectedActor(matchingActor);
            console.log('✅ Restored selected actor:', matchingActor.name);
          }
        }
      }
    } catch (error: any) {
      console.error('Error fetching V2 voice actor data:', error);
      setError(error.message || 'Failed to load voice and actor data');
    } finally {
      setLoading(false);
    }
  };

  const playVoicePreview = async (voice: ElevenLabsVoice) => {
    try {
      // Stop any currently playing audio
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }

      if (playingVoice === voice.voice_id) {
        setPlayingVoice(null);
        setCurrentAudio(null);
        return;
      }

      if (!voice.preview_url) {
        console.log('No preview URL available for this voice');
        return;
      }

      setPlayingVoice(voice.voice_id);
      
      const audio = new Audio(voice.preview_url);
      setCurrentAudio(audio);
      
      audio.onended = () => {
        setPlayingVoice(null);
        setCurrentAudio(null);
      };
      
      audio.onerror = () => {
        console.error('Error playing voice preview');
        setPlayingVoice(null);
        setCurrentAudio(null);
      };
      
      await audio.play();
    } catch (error) {
      console.error('Error playing voice preview:', error);
      setPlayingVoice(null);
      setCurrentAudio(null);
    }
  };

  const handleVoiceSelect = (voice: ElevenLabsVoice) => {
    setSelectedVoice(voice);
  };

  const handleActorSelect = (actor: ActorImage) => {
    setSelectedActor(actor);
  };

  // Save voice/actor selection to database
  const saveVoiceActorSelection = async () => {
    if (!selectedVoice || !selectedActor || !campaignId) return false;
    
    try {
      const token = getValidToken(session);
      if (!token) return false;
      
      const voiceInfo = {
        selected_voice: selectedVoice,
        selected_actor: selectedActor
      };
      
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/video-ads-v2/campaign/${campaignId}/voice-actor/selected`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ voice_info: voiceInfo })
      });
      
      if (response.ok) {
        console.log('✅ Voice/actor selection saved to database');
        return true;
      } else {
        console.warn('Failed to save voice/actor selection to database');
        return false;
      }
    } catch (error) {
      console.error('Error saving voice/actor selection:', error);
      return false;
    }
  };

  const handleContinue = async () => {
    if (!selectedVoice || !selectedActor) {
      setError('Please select both a voice and an actor to continue.');
      return;
    }

    // Save selections to database before navigating
    await saveVoiceActorSelection();

    // Prepare data for audio generation page (V2)
    const voiceActorSelection = {
      selected_voice: selectedVoice,
      selected_actor: selectedActor
    };

    const dataForAudio = {
      conversation_id: campaignId, // V2: conversation_id instead of thread_id
      voice_actor_selection: voiceActorSelection,
      campaign_scripts: campaignScripts
    };

    // Store in localStorage for persistence (V2: different storage key)
    localStorage.setItem('videoAdsV2State', JSON.stringify(dataForAudio));

    // Navigate to V2 audio page - pass all navigation state
    const state = location.state || {};
    
    // DEBUGGER: Check what VoiceActor is passing to Audio
    debugger; // 🔴 BREAKPOINT 5: Check state from VoiceActor to Audio
    console.log('🔴 DEBUG POINT 5 - VoiceActor navigating to Audio with:', {
      currentLocationState: state,
      dataForAudio,
      campaignId,
      willPassProductInfo: state.productInfo,
      willPassSelectedAngles: state.selectedAngles,
      willPassSelectedHooks: state.selectedHooks
    });
    
    navigate('/video-ads-v2/audio', { state: { 
        data: dataForAudio, 
        campaignId: campaignId, // V3
        conversationId: campaignId, // Legacy support
        // Pass through all navigation state for back navigation
        productInfo: state.productInfo,
        selectedAngles: state.selectedAngles,
        selectedHooks: state.selectedHooks,
        isFromURL: state.isFromURL,
        // Preserve the isFromVideo flag if we're in the Video → Audio → VoiceActor → Audio flow
        isFromVideo: state.isFromVideo || state.isFromAudio
      } });
  };

  const goBack = () => {
    const state = location.state || {};
    // V3: Pass campaignId and preserve navigation flags
    navigate('/video-ads-v2/scripts', { state: {
        campaignId: campaignId, // V3 stateless - Scripts will load from DB
        isFromVideo: state.isFromVideo, // Preserve navigation flags
        isFromAudio: state.isFromAudio
      } });
  };

  const loadMoreVoices = () => {
    setVoicesDisplayCount(prev => prev + 8);
  };

  const loadMoreActors = () => {
    setActorsDisplayCount(prev => prev + 8);
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button variant="outlined" onClick={goBack}>
          Go Back to Scripts
        </Button>
      </Container>
    );
  }

  if (!voiceActorData) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="warning">
          No voice and actor data available.
        </Alert>
        <Button variant="outlined" onClick={goBack} sx={{ mt: 2 }}>
          Go Back to Scripts
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, pb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Choose Voice & Actor
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Select a voice for your scripts and an actor for your videos
        </Typography>
      </Box>

      {/* Progress indicator */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="body2" color="text.secondary">
          Campaign: {campaignId}
        </Typography>
      </Box>

      {/* Voice Selection */}
      <Box sx={{ mb: 6 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
          Select Voice ({voiceActorData.voices.length} available)
        </Typography>
        
        <RadioGroup
          value={selectedVoice?.voice_id || ''}
          onChange={(e) => {
            const voice = voiceActorData.voices.find(v => v.voice_id === e.target.value);
            if (voice) handleVoiceSelect(voice);
          }}
        >
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { 
              xs: '1fr',  // 1 column on mobile
              sm: 'repeat(2, 1fr)',  // 2 columns on tablet
              md: 'repeat(3, 1fr)',  // 3 columns on desktop
              lg: 'repeat(4, 1fr)'   // 4 columns on large screens
            }, 
            gap: 2 
          }}>
            {voiceActorData.voices.slice(0, voicesDisplayCount).map((voice) => (
              <Card 
                key={voice.voice_id} 
                sx={{ 
                  border: selectedVoice?.voice_id === voice.voice_id ? 2 : 1,
                  borderColor: selectedVoice?.voice_id === voice.voice_id ? 'primary.main' : 'divider',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': { 
                    borderColor: 'primary.main',
                    transform: 'translateY(-2px)',
                    boxShadow: 2
                  }
                }}
                onClick={() => handleVoiceSelect(voice)}
              >
                <CardContent sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <FormControlLabel
                      value={voice.voice_id}
                      control={<Radio size="small" />}
                      label=""
                      sx={{ mr: 0.5, ml: -0.5 }}
                    />
                    <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 500 }}>
                      {voice.name}
                    </Typography>
                    <IconButton 
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        playVoicePreview(voice);
                      }}
                      disabled={!voice.preview_url}
                    >
                      {playingVoice === voice.voice_id ? <PauseIcon /> : <PlayIcon />}
                    </IconButton>
                  </Box>
                  
                  {voice.description && (
                    <Typography 
                      variant="caption" 
                      color="text.secondary" 
                      sx={{ 
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        mb: 0.5,
                        minHeight: '2.4em'
                      }}
                    >
                      {voice.description}
                    </Typography>
                  )}
                  
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 0.5 }}>
                    {voice.gender && (
                      <Chip label={voice.gender} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                    )}
                    {voice.age && (
                      <Chip label={voice.age} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                    )}
                    {voice.accent && (
                      <Chip label={voice.accent} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                    )}
                  </Box>
                  
                  {voice.labels.length > 0 && (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {voice.labels.slice(0, 2).map((label, index) => (
                        <Chip key={index} label={label} size="small" sx={{ height: 20, fontSize: '0.7rem' }} />
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Box>
        </RadioGroup>

        {voiceActorData.voices.length > voicesDisplayCount && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Button variant="outlined" onClick={loadMoreVoices}>
              Load More Voices ({voiceActorData.voices.length - voicesDisplayCount} remaining)
            </Button>
          </Box>
        )}
      </Box>

      {/* Actor Selection */}
      <Box sx={{ mb: 6 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
          Select Actor ({voiceActorData.actors.length} available)
        </Typography>
        
        <RadioGroup
          value={selectedActor?.filename || ''}
          onChange={(e) => {
            const actor = voiceActorData.actors.find(a => a.filename === e.target.value);
            if (actor) handleActorSelect(actor);
          }}
        >
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { 
              xs: 'repeat(2, 1fr)',  // 2 columns on mobile
              sm: 'repeat(3, 1fr)',  // 3 columns on tablet
              md: 'repeat(4, 1fr)',  // 4 columns on desktop
              lg: 'repeat(5, 1fr)',  // 5 columns on large screens
              xl: 'repeat(6, 1fr)'   // 6 columns on extra large screens
            }, 
            gap: 2 
          }}>
            {voiceActorData.actors.slice(0, actorsDisplayCount).map((actor) => (
              <Card 
                key={actor.filename}
                sx={{ 
                  border: selectedActor?.filename === actor.filename ? 2 : 1,
                  borderColor: selectedActor?.filename === actor.filename ? 'primary.main' : 'divider',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': { 
                    borderColor: 'primary.main',
                    transform: 'translateY(-2px)',
                    boxShadow: 2
                  }
                }}
                onClick={() => handleActorSelect(actor)}
              >
                <CardMedia
                  component="img"
                  height="120"
                  image={`/images/actors/${actor.filename}`}
                  alt={actor.name}
                  sx={{ objectFit: 'cover' }}
                />
                <CardContent sx={{ p: 1.5 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                    <FormControlLabel
                      value={actor.filename}
                      control={<Radio size="small" />}
                      label=""
                      sx={{ mr: 0.5, ml: -0.5 }}
                    />
                    <Typography variant="subtitle2" sx={{ flexGrow: 1, fontWeight: 500 }}>
                      {actor.name}
                    </Typography>
                  </Box>
                  
                  <Typography 
                    variant="caption" 
                    color="text.secondary" 
                    sx={{ 
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      mb: 0.5,
                      minHeight: '2.4em'
                    }}
                  >
                    {actor.description}
                  </Typography>
                  
                  <Chip label={actor.category} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                </CardContent>
              </Card>
            ))}
          </Box>
        </RadioGroup>

        {voiceActorData.actors.length > actorsDisplayCount && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Button variant="outlined" onClick={loadMoreActors}>
              Load More Actors ({voiceActorData.actors.length - actorsDisplayCount} remaining)
            </Button>
          </Box>
        )}
      </Box>

      {/* Selection Summary & Continue */}
      <Box sx={{ 
        position: 'sticky', 
        bottom: 0, 
        bgcolor: 'background.paper', 
        borderTop: 1, 
        borderColor: 'divider',
        p: 3,
        mt: 4
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', maxWidth: 'xl', mx: 'auto' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {selectedVoice && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <VolumeIcon color="primary" />
                <Typography variant="body2">
                  Voice: <strong>{selectedVoice.name}</strong>
                </Typography>
              </Box>
            )}
            {selectedActor && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <PersonIcon color="primary" />
                <Typography variant="body2">
                  Actor: <strong>{selectedActor.name}</strong>
                </Typography>
              </Box>
            )}
          </Box>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={goBack}>
              Back to Scripts
            </Button>
            <Button 
              variant="contained" 
              onClick={handleContinue}
              disabled={!selectedVoice || !selectedActor}
            >
              Continue to Audio Generation
            </Button>
          </Box>
        </Box>
      </Box>
    </Container>
  );
};

export default VoiceActorV2;
