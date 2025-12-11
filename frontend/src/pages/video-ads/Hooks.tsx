import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button, 
  Card, 
  CardContent,
  Chip,
  Checkbox,
  FormControlLabel,
  Alert,
  LinearProgress,
  Container,
  Divider,
  Paper,
  Grid
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Whatshot as HookIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface SelectedAngle {
  angle_id: string;
  angle: number;
  category: string;
  concept: string;
  type: 'positive' | 'negative';
}

interface HooksByCategory {
  direct_question: string[];
  shocking_fact: string[];
  demonstration: string[];
  alarm_tension: string[];
  surprise_curiosity: string[];
  list_enumeration: string[];
  personal_story: string[];
}

interface AngleWithHooks {
  angle_id: string;
  angle_number: number;
  angle_category: string;
  angle_concept: string;
  angle_type: 'positive' | 'negative';
  hooks_by_category: HooksByCategory;
}

interface HooksResponse {
  thread_id: string;
  hooks_by_angle: AngleWithHooks[];
  raw_response: string;
}

interface LocationState {
  productInfo?: any;
  selectedAngles?: SelectedAngle[];
  threadId?: string;
  isFromURL?: boolean;
}

interface SelectedHook {
  angle_id: string;
  angle: number;
  category: string;
  hook_text: string;
}

const Hooks: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  const { selectedAngles, threadId, isFromURL, productInfo } = (location.state as LocationState) || {};

  const [hooksData, setHooksData] = useState<AngleWithHooks[]>([]);
  const [selectedHooks, setSelectedHooks] = useState<SelectedHook[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!selectedAngles || !threadId) {
      setError('Missing required data. Please go back to marketing angles.');
      return;
    }

    generateHooks();
  }, [selectedAngles, threadId]);

  const generateHooks = async () => {
    if (!selectedAngles || !threadId) return;

    setIsLoading(true);
    setError('');

    try {
      // For development, ensure we use dev-token
      // Smart token selection: try JWT first, fall back to dev-token
      let token = session?.access_token || 'dev-token';
      
      // Check if JWT token is expired
      if (session?.access_token) {
        try {
          const payload = JSON.parse(atob(session.access_token.split('.')[1]));
          const now = Math.floor(Date.now() / 1000);
          if (payload.exp && payload.exp < now) {
            console.warn('⚠️ JWT token expired, using dev-token');
            token = 'dev-token';
          }
        } catch (e) {
          console.warn('⚠️ Failed to parse JWT token, using dev-token');
          token = 'dev-token';
        }
      }
      
      // let token = 'dev-token'; // Force dev-token for testing
      // let token = localStorage.getItem('token');
      // if (!token || token === 'null' || token === 'undefined') {
      //   token = 'dev-token';
      //   localStorage.setItem('token', 'dev-token'); // Store for consistency
      // }
      console.log('🔐 Token being used:', token.substring(0, 20) + '...'); // Debug logging
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8001';
      const fullUrl = `${apiUrl}/video-ads/create-hooks`;
      console.log('🌐 API URL:', fullUrl); // Debug logging
      
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          thread_id: threadId,
          selected_angles: selectedAngles
        })
      });

      console.log('📡 Response status:', response.status); // Debug logging
      console.log('📡 Response ok:', response.ok); // Debug logging

      if (!response.ok) {
        const errorText = await response.text();
        console.log('❌ Error response:', errorText); // Debug logging
        
        // Handle specific error messages
        if (response.status === 400 && errorText.includes('Thread expired')) {
          setError('Session expired. Please restart from the marketing angles step.');
        } else {
          setError(`Failed to generate hooks. Please try again. (${response.status})`);
        }
        return;
      }

      const data: HooksResponse = await response.json();
      setHooksData(data.hooks_by_angle);
      
    } catch (err: any) {
      console.error('Hooks generation error:', err);
      if (err instanceof Error && (err.message.includes('Thread expired') || err.message.includes('404'))) {
        setError('Session expired. Please restart from the marketing angles step.');
      } else {
        setError('Failed to generate hooks. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleHookSelection = (angle_id: string, angle: number, category: string, hook_text: string, isSelected: boolean) => {
    if (isSelected) {
      setSelectedHooks(prev => [...prev, { angle_id, angle, category, hook_text }]);
    } else {
      setSelectedHooks(prev => prev.filter(h => 
        !(h.angle_id === angle_id && h.category === category && h.hook_text === hook_text)
      ));
    }
  };

  const isHookSelected = (angle_id: string, category: string, hook_text: string): boolean => {
    return selectedHooks.some(h => 
      h.angle_id === angle_id && h.category === category && h.hook_text === hook_text
    );
  };

  const handleBack = () => {
    navigate('/video-ads/marketing-angles', { 
      state: { 
        productInfo: location.state?.productInfo,
        isFromURL: isFromURL
      } 
    });
  };

  const handleNext = () => {
    if (selectedHooks.length === 0) {
      setError('Please select at least one hook to continue.');
      return;
    }

    // Transform selected hooks into the format expected by the scripts endpoint
    const formattedHooksData = hooksData.map(angleData => {
      // Get all selected hooks for this angle
      const angleSelectedHooks = selectedHooks.filter(h => h.angle_id === angleData.angle_id);
      
      if (angleSelectedHooks.length === 0) return null;

      // Group hooks by category
      const hooksByCategory: { [key: string]: string[] } = {};
      angleSelectedHooks.forEach(hook => {
        if (!hooksByCategory[hook.category]) {
          hooksByCategory[hook.category] = [];
        }
        hooksByCategory[hook.category].push(hook.hook_text);
      });

      return {
        id: angleData.angle_id,
        angle: angleData.angle_number,
        category: angleData.angle_category,
        concept: angleData.angle_concept,
        type: angleData.angle_type,
        hooks_by_category: hooksByCategory
      };
    }).filter(Boolean); // Remove null values

    navigate('/video-ads/scripts', { 
      state: { 
        productInfo: location.state?.productInfo,
        selectedAngles,
        selectedHooks: formattedHooksData,
        threadId,
        isFromURL 
      } 
    });
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'direct_question': return '❓';
      case 'shocking_fact': return '⚡';
      case 'demonstration': return '🎯';
      case 'alarm_tension': return '🚨';
      case 'surprise_curiosity': return '🤔';
      case 'list_enumeration': return '📝';
      case 'personal_story': return '📖';
      default: return '💡';
    }
  };

  const getCategoryLabel = (category: string) => {
    const labels: { [key: string]: string } = {
      'direct_question': 'Direct Question',
      'shocking_fact': 'Shocking Fact',
      'demonstration': 'Demonstration',
      'alarm_tension': 'Alarm & Tension',
      'surprise_curiosity': 'Surprise & Curiosity',
      'list_enumeration': 'List & Enumeration',
      'personal_story': 'Personal Story'
    };
    return labels[category] || category;
  };

  if (error && !selectedAngles) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
          <Button onClick={handleBack} variant="outlined" startIcon={<ArrowBackIcon />}>
            Go Back to Marketing Angles
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box mb={4}>
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            <Chip 
              icon={<HookIcon />} 
              label={`${selectedAngles?.length || 0} Angles Selected`}
              color="primary" 
              variant="outlined" 
              size="small"
            />
            {selectedHooks.length > 0 && (
              <Chip 
                icon={<CheckCircleIcon />} 
                label={`${selectedHooks.length} Hooks Selected`}
                color="success" 
                variant="outlined" 
                size="small"
              />
            )}
          </Box>
          
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            Select Your Hooks
          </Typography>
          
          <Typography variant="h6" color="text.secondary">
            Choose the hooks that resonate most with your target audience. You can select multiple hooks from different categories and angles.
          </Typography>
        </Box>

        {isLoading && (
          <Box sx={{ mb: 3 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Box display="flex" alignItems="center" gap={2}>
                <PsychologyIcon />
                Generating creative hooks for your selected marketing angles...
              </Box>
            </Alert>
            <LinearProgress 
              sx={{ 
                height: 8, 
                borderRadius: 4,
                '& .MuiLinearProgress-bar': {
                  background: 'linear-gradient(90deg, #667eea, #764ba2)'
                }
              }} 
            />
          </Box>
        )}

        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 3 }}
            action={
              error.includes('Session expired') ? (
                <Button 
                  color="inherit" 
                  size="small" 
                  onClick={() => navigate('/video-ads/marketing-angles', { 
                    state: { productInfo, isFromURL } 
                  })}
                >
                  Go Back
                </Button>
              ) : null
            }
          >
            {error}
          </Alert>
        )}

        {!isLoading && hooksData.length > 0 && (
          <Box sx={{ mb: 4 }}>
            {hooksData.map((angleData, angleIndex) => (
              <Card 
                key={angleData.angle_id}
                elevation={3}
                sx={{ 
                  mb: 3,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: 4,
                  overflow: 'hidden'
                }}
              >
                <CardContent sx={{ p: 4 }}>
                  <Box sx={{ 
                    background: 'white', 
                    borderRadius: 3, 
                    p: 3,
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
                  }}>
                    {/* Angle Header */}
                    <Box display="flex" alignItems="center" gap={2} mb={3}>
                      <Chip 
                        icon={angleData.angle_type === 'positive' ? <TrendingUpIcon /> : <TrendingDownIcon />}
                        label={`Angle ${angleData.angle_number}`}
                        color={angleData.angle_type === 'positive' ? 'success' : 'warning'}
                        size="medium"
                      />
                      <Typography variant="h6" fontWeight="bold">
                        {angleData.angle_category}
                      </Typography>
                    </Box>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3, fontStyle: 'italic' }}>
                      "{angleData.angle_concept}"
                    </Typography>

                    <Divider sx={{ mb: 3 }} />

                    {/* Hooks by Category */}
                    <Box>
                      {Object.entries(angleData.hooks_by_category).map(([category, hooks]) => 
                        hooks.length > 0 && (
                          <Box key={category} sx={{ mb: 3 }}>
                            <Paper elevation={1} sx={{ p: 2 }}>
                              <Box display="flex" alignItems="center" gap={1} mb={2}>
                                <Typography variant="h6" fontSize="1.2rem">
                                  {getCategoryIcon(category)}
                                </Typography>
                                <Typography variant="subtitle1" fontWeight="600">
                                  {getCategoryLabel(category)}
                                </Typography>
                              </Box>
                              
                              {hooks.map((hook: string, hookIndex: number) => (
                                <FormControlLabel
                                  key={hookIndex}
                                  control={
                                    <Checkbox
                                      checked={isHookSelected(angleData.angle_id, category, hook)}
                                      onChange={(e) => handleHookSelection(
                                        angleData.angle_id, 
                                        angleData.angle_number, 
                                        category, 
                                        hook, 
                                        e.target.checked
                                      )}
                                      color="primary"
                                    />
                                  }
                                  label={
                                    <Typography variant="body2" sx={{ lineHeight: 1.5 }}>
                                      {hook}
                                    </Typography>
                                  }
                                  sx={{ 
                                    alignItems: 'flex-start',
                                    mb: 1,
                                    ml: 0,
                                    display: 'flex'
                                  }}
                                />
                              ))}
                            </Paper>
                          </Box>
                        )
                      )}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}

        <Box display="flex" justifyContent="space-between" alignItems="center" mt={4} sx={{ gap: 2 }}>
          <Button
            variant="outlined"
            size="large"
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
            sx={{ 
              px: 4, 
              py: 1.5,
              borderRadius: 3,
              border: 'none',
              backgroundColor: 'rgba(25, 118, 210, 0.08)',
              color: 'primary.main',
              '&:hover': {
                backgroundColor: 'rgba(25, 118, 210, 0.12)',
                border: 'none'
              }
            }}
          >
            Back
          </Button>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
              Step 3 of 6
            </Typography>
            <Button
              variant="contained"
              size="large"
              endIcon={<ArrowForwardIcon />}
              onClick={handleNext}
              disabled={isLoading || selectedHooks.length === 0}
              sx={{ 
                px: 4, 
                py: 1.5, 
                fontSize: '1.1rem',
                borderRadius: 3,
                background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                boxShadow: '0 3px 15px rgba(102, 126, 234, 0.4)',
                '&:hover': {
                  background: 'linear-gradient(45deg, #5a6fd8 30%, #6a4190 90%)',
                  boxShadow: '0 6px 20px rgba(102, 126, 234, 0.6)',
                }
              }}
            >
              {isLoading ? 'Generating...' : 'Continue to Scripts'}
            </Button>
          </Box>
        </Box>

        <Box textAlign="center" mt={3}>
          <Typography variant="caption" color="text.secondary">
            These hooks will be used to create compelling scripts for your video ads.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default Hooks;
