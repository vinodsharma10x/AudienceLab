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
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Article as ScriptIcon,
  CheckCircle as CheckCircleIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';

interface Script {
  id: string;
  version: string;
  content: string;
  cta: string;
  target_emotion: string;
}

interface Hook {
  selected_hook: {
    id: string;
    hook_text: string;
    hook_type: string;
  };
  scripts: Script[];
}

interface Angle {
  selected_angle: {
    id: string;
    angle: number;
    category: string;
    concept: string;
    type: string;
  };
  hooks: Hook[];
}

interface CampaignScripts {
  angles: Angle[];
}

interface ScriptsResponse {
  thread_id: string;
  campaign_scripts: CampaignScripts;
  raw_response: string;
}

interface LocationState {
  productInfo?: any;
  selectedAngles?: any[];
  selectedHooks?: any[];
  threadId?: string;
  isFromURL?: boolean;
}

interface SelectedScript {
  angle_id: string;
  hook_id: string;
  script: Script;
}

const Scripts: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  const { selectedHooks, threadId, isFromURL, productInfo, selectedAngles } = (location.state as LocationState) || {};

  const [scriptsData, setScriptsData] = useState<Angle[]>([]);
  const [selectedScripts, setSelectedScripts] = useState<SelectedScript[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!selectedHooks || !threadId) {
      setError('Missing required data. Please go back to hooks selection.');
      return;
    }

    generateScripts();
  }, [selectedHooks, threadId]);

  const generateScripts = async () => {
    if (!selectedHooks || !threadId) return;

    setIsLoading(true);
    setError('');

    try {
      // Get valid token (JWT or dev-token fallback)
      const token = getValidToken(session);
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8001';
      const fullUrl = `${apiUrl}/video-ads/create-scripts`;
      
      console.log('🔍 Scripts API Debug:', {
        token: token?.substring(0, 20) + '...',
        tokenLength: token?.length,
        fullUrl,
        hasSession: !!session,
        hooksCount: selectedHooks?.length
      });
      
      let response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          thread_id: threadId,
          hooks_by_angle: selectedHooks
        })
      });

      // If JWT token fails with 401/403, try dev-token
      if (!response.ok && (response.status === 401 || response.status === 403) && token !== 'dev-token') {
        console.warn('⚠️ JWT token failed, retrying with dev-token');
        response = await fetch(fullUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer dev-token'
          },
          body: JSON.stringify({
            thread_id: threadId,
            hooks_by_angle: selectedHooks
          })
        });
      }

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Scripts API Error:', {
          status: response.status,
          statusText: response.statusText,
          errorText
        });
        
        // Handle specific error messages
        if (response.status === 400 && errorText.includes('Thread expired')) {
          setError('Session expired. Please restart from the marketing angles step.');
        } else {
          setError(`Failed to generate scripts. Please try again. (${response.status})`);
        }
        return;
      }

      const data: ScriptsResponse = await response.json();
      console.log('✅ Scripts API Success:', { anglesCount: data.campaign_scripts.angles.length });
      setScriptsData(data.campaign_scripts.angles);
      
    } catch (err: any) {
      console.error('Scripts generation error:', err);
      if (err instanceof Error && (err.message.includes('Thread expired') || err.message.includes('404'))) {
        setError('Session expired. Please restart from the marketing angles step.');
      } else {
        setError('Failed to generate scripts. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleScriptSelection = (angle_id: string, hook_id: string, script: Script, selected: boolean) => {
    if (selected) {
      setSelectedScripts(prev => [...prev, { angle_id, hook_id, script }]);
    } else {
      setSelectedScripts(prev => prev.filter(s => 
        !(s.angle_id === angle_id && s.hook_id === hook_id && s.script.id === script.id)
      ));
    }
  };

  const isScriptSelected = (angle_id: string, hook_id: string, script: Script) => {
    return selectedScripts.some(s => 
      s.angle_id === angle_id && s.hook_id === hook_id && s.script.id === script.id
    );
  };

  const handleNext = () => {
    if (selectedScripts.length === 0) {
      setError('Please select at least one script to continue.');
      return;
    }

    // Format selected scripts for the next step
    const formattedScripts = {
      campaign_scripts: {
        angles: scriptsData.map(angle => ({
          selected_angle: angle.selected_angle,
          hooks: angle.hooks.map(hook => ({
            selected_hook: hook.selected_hook,
            scripts: hook.scripts.filter(script => 
              selectedScripts.some(s => 
                s.angle_id === angle.selected_angle.id && 
                s.hook_id === hook.selected_hook.id && 
                s.script.id === script.id
              )
            )
          })).filter(hook => hook.scripts.length > 0)
        })).filter(angle => angle.hooks.length > 0)
      }
    };

    navigate('/video-ads/voice-actor', { 
      state: { 
        productInfo,
        selectedAngles,
        selectedHooks,
        selectedScripts: formattedScripts,
        threadId,
        isFromURL 
      } 
    });
  };

  // Early return for missing data
  if (error && !selectedHooks) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert 
            severity="error" 
            action={
              <Button 
                color="inherit" 
                size="small" 
                onClick={() => navigate('/video-ads/hooks', { 
                  state: { productInfo, selectedAngles, threadId, isFromURL } 
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

  const getCategoryIcon = (type: string) => {
    return type === 'positive' ? <TrendingUpIcon color="success" /> : <TrendingDownIcon color="error" />;
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 2 }}>
            <ScriptIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            {selectedScripts.length > 0 && (
              <Chip 
                icon={<CheckCircleIcon />} 
                label={`${selectedScripts.length} Scripts Selected`}
                color="success" 
                variant="outlined" 
                size="small"
              />
            )}
          </Box>
          
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            Select Your Scripts
          </Typography>
          
          <Typography variant="h6" color="text.secondary">
            Choose the scripts that best represent your campaign message. You can select multiple script versions from different hooks and angles.
          </Typography>
        </Box>

        {isLoading && (
          <Box sx={{ mb: 3 }}>
            <LinearProgress />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
              Generating scripts with AI... This may take a moment.
            </Typography>
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

        {!isLoading && scriptsData.length > 0 && (
          <Box sx={{ mb: 4 }}>
            {scriptsData.map((angleData, angleIndex) => (
              <Card 
                key={angleData.selected_angle.id}
                elevation={3}
                sx={{ 
                  mb: 3,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: 4,
                  overflow: 'visible'
                }}
              >
                <CardContent sx={{ p: 0 }}>
                  {/* Angle Header */}
                  <Box
                    sx={{
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      p: 3,
                      borderRadius: '16px 16px 0 0'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                      {getCategoryIcon(angleData.selected_angle.type)}
                      <Typography variant="h5" fontWeight="bold">
                        Angle #{angleData.selected_angle.angle}: {angleData.selected_angle.category}
                      </Typography>
                      <Chip 
                        label={angleData.selected_angle.type} 
                        color={angleData.selected_angle.type === 'positive' ? 'success' : 'warning'}
                        size="small"
                        sx={{ fontWeight: 'bold' }}
                      />
                    </Box>
                    <Typography variant="body1" sx={{ opacity: 0.95, fontStyle: 'italic' }}>
                      {angleData.selected_angle.concept}
                    </Typography>
                  </Box>

                  {/* Hooks and Scripts */}
                  <Box sx={{ bgcolor: 'background.paper', borderRadius: '0 0 16px 16px' }}>
                    {angleData.hooks.map((hookData, hookIndex) => (
                      <Box key={hookData.selected_hook.id} sx={{ p: 3, borderBottom: hookIndex < angleData.hooks.length - 1 ? '1px solid' : 'none', borderColor: 'divider' }}>
                        {/* Hook Header */}
                        <Box sx={{ mb: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                            <PsychologyIcon color="primary" />
                            <Typography variant="h6" fontWeight="bold" color="primary">
                              Hook: {hookData.selected_hook.hook_text}
                            </Typography>
                            <Chip 
                              label={hookData.selected_hook.hook_type.replace('_', ' ')} 
                              variant="outlined" 
                              size="small"
                            />
                          </Box>
                        </Box>

                        {/* Scripts Grid */}
                        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
                          {hookData.scripts.map((script) => {
                            const isSelected = isScriptSelected(angleData.selected_angle.id, hookData.selected_hook.id, script);
                            
                            return (
                              <Card 
                                key={script.id}
                                elevation={isSelected ? 4 : 1}
                                sx={{ 
                                  border: isSelected ? '2px solid' : '1px solid',
                                  borderColor: isSelected ? 'primary.main' : 'divider',
                                  transition: 'all 0.3s ease',
                                  height: '100%'
                                }}
                              >
                                  <CardContent>
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <Typography variant="h6" fontWeight="bold" color="primary">
                                          Version {script.version}
                                        </Typography>
                                        <Chip 
                                          label={script.target_emotion} 
                                          size="small" 
                                          variant="outlined"
                                          color="secondary"
                                        />
                                      </Box>
                                      <FormControlLabel
                                        control={
                                          <Checkbox
                                            checked={isSelected}
                                            onChange={(e) => handleScriptSelection(
                                              angleData.selected_angle.id,
                                              hookData.selected_hook.id,
                                              script,
                                              e.target.checked
                                            )}
                                            color="primary"
                                          />
                                        }
                                        label=""
                                        sx={{ m: 0 }}
                                      />
                                    </Box>
                                    
                                    <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.6 }}>
                                      {script.content}
                                    </Typography>
                                    
                                    <Divider sx={{ my: 2 }} />
                                    
                                    <Box>
                                      <Typography variant="subtitle2" color="primary" fontWeight="bold" sx={{ mb: 1 }}>
                                        Call to Action:
                                      </Typography>
                                      <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                                        {script.cta}
                                      </Typography>
                                    </Box>
                                  </CardContent>
                                </Card>
                            );
                          })}
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}

        {/* Navigation */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/video-ads/hooks', { 
              state: { productInfo, selectedAngles, threadId, isFromURL } 
            })}
            size="large"
          >
            Back to Hooks
          </Button>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Selected: {selectedScripts.length} script{selectedScripts.length !== 1 ? 's' : ''}
            </Typography>
          </Box>

          <Button
            variant="contained"
            endIcon={<ArrowForwardIcon />}
            onClick={handleNext}
            disabled={isLoading || selectedScripts.length === 0}
            size="large"
            sx={{
              background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
              '&:hover': {
                background: 'linear-gradient(45deg, #1976D2 30%, #0288D1 90%)',
              }
            }}
          >
            Continue to Voice Actor ({selectedScripts.length} selected)
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default Scripts;
