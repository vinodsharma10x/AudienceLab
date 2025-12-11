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
import { getCampaignId } from '../../utils/v3-migration';

interface Script {
  script_id: string;
  id?: string;  // For backward compatibility
  version: string;
  content: string;
  cta: string;
  target_emotion: string;
}

interface Hook {
  selected_hook: {
    hook_id: string;
    id?: string;  // For backward compatibility
    hook_text: string;
    hook_category: string;
  };
  scripts: Script[];
}

interface Angle {
  selected_angle: {
    id: string;
    angle: number;
    category?: string;
    angle_category?: string;  // Backend might send this instead
    concept?: string;
    angle_concept?: string;  // Backend might send this instead
    type: string;
  };
  hooks: Hook[];
}

interface CampaignScripts {
  angles: Angle[];
}

interface ScriptsResponse {
  conversation_id: string;
  campaign_scripts: CampaignScripts | any[];  // Can be object or array
  processing_time: number;
  // Alternative formats for backward compatibility
  angles?: any[];
  scripts?: any;
}

interface LocationState {
  campaignId?: string;
  selectedHooks?: any[];
  forceGenerate?: boolean;
  isFromVideo?: boolean;
  isFromAudio?: boolean;
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
  const locationState = (location.state as LocationState) || {};
  const { campaignId, selectedHooks, forceGenerate } = locationState;

  const [scriptsData, setScriptsData] = useState<Angle[]>([]);
  const [selectedScripts, setSelectedScripts] = useState<SelectedScript[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [loadingFromDB, setLoadingFromDB] = useState(false);
  
  const [originalSelectedScripts, setOriginalSelectedScripts] = useState<SelectedScript[]>([]);
  const [hasChanges, setHasChanges] = useState<boolean>(false);

  // Track changes in selected scripts
  useEffect(() => {
    if (originalSelectedScripts.length > 0 || selectedScripts.length > 0) {
      const changed = originalSelectedScripts.length !== selectedScripts.length ||
        !selectedScripts.every(script => 
          originalSelectedScripts.some(orig => 
            orig.angle_id === script.angle_id && 
            orig.hook_id === script.hook_id &&
            orig.script.script_id === script.script.script_id
          )
        );
      setHasChanges(changed);
    }
  }, [selectedScripts, originalSelectedScripts]);

  useEffect(() => {
    console.log('🔍 Scripts decision logic:', { 
      campaignId,
      hasSelectedHooks: !!selectedHooks,
      forceGenerate
    });
    
    // Decide whether to load from DB or generate new scripts
    if (selectedHooks && (forceGenerate || !campaignId)) {
      // Generate new scripts if:
      // 1. Selected hooks provided and forceGenerate is true, OR
      // 2. Selected hooks provided but no campaignId yet (new campaign)
      console.log('🔄 Generating new scripts');
      generateScripts();
    } else if (campaignId) {
      // Load from database if we have campaignId
      console.log('📚 Loading scripts from database');
      loadScriptsFromDatabase();
    } else {
      console.log('❌ Missing required data');
      setError('Missing required data. Please go back to hooks selection.');
    }
  }, [selectedHooks, campaignId, forceGenerate]);

  const loadScriptsFromDatabase = async () => {
    setLoadingFromDB(true);
    setError('');
    
    
    try {
      const token = getValidToken(session);
      const apiUrl = process.env.REACT_APP_API_URL || '';
      
      
      // Load scripts from database
      
      const response = await fetch(`${apiUrl}/video-ads-v2/campaign/${campaignId}/scripts`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('📚 Scripts loaded from DB:', data);
        
        // Handle different response formats from database
        let angles: any[] = [];
        if (data.scripts_data && data.scripts_data.angles) {
          angles = data.scripts_data.angles;
        } else if (data.scripts_data && Array.isArray(data.scripts_data)) {
          angles = data.scripts_data;
        } else if (data.scripts && data.scripts.angles) {
          angles = data.scripts.angles;
        } else if (data.scripts && Array.isArray(data.scripts)) {
          angles = data.scripts;
        }
        
        if (angles.length > 0) {
          setScriptsData(angles);
          console.log('📚 Scripts data set:', angles.length, 'angles');
          
          // Load selected scripts if any
          if (data.selected_scripts && data.selected_scripts.length > 0) {
            console.log('📚 Loading selected scripts from DB:', data.selected_scripts);
            console.log('📚 First angle structure:', angles[0]?.selected_angle);
            console.log('📚 First hook structure:', angles[0]?.hooks[0]?.selected_hook);
            console.log('📚 First script structure:', angles[0]?.hooks[0]?.scripts[0]);
            
            const loaded: SelectedScript[] = [];
            
            // For each selected script from DB, find the matching script in the scripts data
            data.selected_scripts.forEach((savedScript: any, index: number) => {
              // The saved script has: angle_id, hook_id, script_id, body
              // We need to find the full script object in the scripts data
              
              if (index === 0) {
                console.log('🔍 Looking for saved script:', {
                  angle_id: savedScript.angle_id,
                  hook_id: savedScript.hook_id,
                  script_id: savedScript.script_id
                });
              }
              
              let found = false;
              for (const angle of angles) {
                // Check if this is the right angle
                const angleMatch = angle.selected_angle && 
                    (angle.selected_angle.id === savedScript.angle_id || 
                     angle.selected_angle.angle_id === savedScript.angle_id);
                
                if (angleMatch) {
                  for (const hook of angle.hooks || []) {
                    // Check if this is the right hook  
                    const hookMatch = hook.selected_hook && 
                        (hook.selected_hook.hook_id === savedScript.hook_id || 
                         hook.selected_hook.id === savedScript.hook_id);
                    
                    if (hookMatch) {
                      for (const script of hook.scripts || []) {
                        // Log first script to see structure
                        if (index === 0 && !found) {
                          console.log('🔍 Checking script:', {
                            script_script_id: script.script_id,
                            script_id: script.id,
                            saved_script_id: savedScript.script_id,
                            matches_script_id: script.script_id === savedScript.script_id,
                            matches_id: script.id === savedScript.script_id
                          });
                        }
                        
                        // Match by script ID - handle all possible ID fields
                        // The scripts have 'id' field, not 'script_id'
                        if (script.script_id === savedScript.script_id || 
                            script.id === savedScript.script_id) {
                          loaded.push({
                            angle_id: savedScript.angle_id,
                            hook_id: savedScript.hook_id,
                            script: {
                              script_id: savedScript.script_id,
                              content: script.content || savedScript.body || '',
                              tone: script.tone || script.target_emotion || '',
                              call_to_action: script.call_to_action || script.cta || ''
                            } as any
                          });
                          found = true;
                          break;
                        }
                      }
                    }
                  }
                }
              }
              
              if (!found) {
                console.log('❌ Could not find script in data for:', savedScript);
              }
            });
            
            // Set the loaded scripts
            setSelectedScripts(loaded);
            setOriginalSelectedScripts(loaded);
            console.log('📚 Restored selected scripts:', loaded.length);
            
            // Log for debugging
            if (loaded.length > 0) {
              console.log('📚 First selected script:', {
                angle_id: loaded[0].angle_id,
                hook_id: loaded[0].hook_id,
                script_id: loaded[0].script.script_id
              });
            }
          }
        } else {
          console.log('📚 No scripts found in database response');
        }
      }
    } catch (error) {
      console.error('Error loading scripts from database:', error);
      setError('Failed to load scripts. Please try generating them again.');
    } finally {
      setLoadingFromDB(false);
    }
  };

  const generateScripts = async () => {
    if (!selectedHooks || !campaignId) return;

    setIsLoading(true);
    setError('');

    try {
      // Get valid token (JWT or dev-token fallback)
      const token = getValidToken(session);
      const apiUrl = process.env.REACT_APP_API_URL || '';
      const fullUrl = `${apiUrl}/video-ads-v2/create-scripts`;
      
      console.log('🔍 V2 Scripts API Debug:', {
        token: token?.substring(0, 20) + '...',
        tokenLength: token?.length,
        fullUrl,
        hasSession: !!session,
        hooksCount: selectedHooks?.length,
        campaignId
      });
      
      let response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          campaign_id: campaignId,      // Primary field for V3
          conversation_id: campaignId,  // Keep for backward compatibility
          hooks_by_angle: selectedHooks          // Using YAML format name
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
            campaign_id: campaignId,      // Primary field for V3
            conversation_id: campaignId,  // Keep for backward compatibility
            hooks_by_angle: selectedHooks          // Using YAML format name
          })
        });
      }

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ V2 Scripts API Error:', {
          status: response.status,
          statusText: response.statusText,
          errorText
        });
        
        // Handle specific error messages
        if (response.status === 400 && errorText.includes('conversation')) {
          setError('Session expired. Please restart from the marketing angles step.');
        } else {
          setError(`Failed to generate scripts. Please try again. (${response.status})`);
        }
        return;
      }

      const data: ScriptsResponse = await response.json();
      console.log('✅ V2 Scripts API Response:', data);
      
      // Handle both response formats - with or without campaign_scripts wrapper
      let angles = [];
      if (data.campaign_scripts && typeof data.campaign_scripts === 'object' && 'angles' in data.campaign_scripts) {
        // Standard format: { campaign_scripts: { angles: [...] } }
        angles = (data.campaign_scripts as CampaignScripts).angles;
      } else if (data.campaign_scripts && Array.isArray(data.campaign_scripts)) {
        // Alternative format: { campaign_scripts: [...] }
        angles = data.campaign_scripts;
      } else if (data.angles) {
        // Direct format: { angles: [...] }
        angles = data.angles;
      } else if (data.scripts && data.scripts.angles) {
        // Scripts wrapper format: { scripts: { angles: [...] } }
        angles = data.scripts.angles;
      }
      
      console.log('📊 Scripts parsed:', { 
        anglesCount: angles.length,
        processingTime: data.processing_time 
      });
      
      // Log script structure for debugging
      if (angles.length > 0) {
        const firstAngle = angles[0];
        console.log('📝 First angle structure:', firstAngle);
        if (firstAngle.hooks && firstAngle.hooks.length > 0) {
          const firstHook = firstAngle.hooks[0];
          if (firstHook.scripts && firstHook.scripts.length > 0) {
            console.log('📝 Script structure sample:', firstHook.scripts[0]);
            console.log('📝 Script ID format:', {
              angleId: firstAngle.selected_angle?.id,
              hookId: firstHook.selected_hook?.id,
              scriptId: firstHook.scripts[0]?.id
            });
          }
        }
      }
      
      setScriptsData(angles);
      
    } catch (err: any) {
      console.error('V2 Scripts generation error:', err);
      if (err instanceof Error && (err.message.includes('conversation') || err.message.includes('404'))) {
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
      // Only allow one script to be selected at a time
      setSelectedScripts([{ angle_id, hook_id, script }]);
    } else {
      // Deselect if it's the currently selected script
      setSelectedScripts(prev => prev.filter(s => 
        !(s.angle_id === angle_id && s.hook_id === hook_id && s.script.script_id === script.script_id)
      ));
    }
  };

  const isScriptSelected = (angle_id: string, hook_id: string, script: Script) => {
    return selectedScripts.some(s => 
      s.angle_id === angle_id && s.hook_id === hook_id && s.script.script_id === script.script_id
    );
  };

  const handleNext = async () => {
    if (selectedScripts.length === 0) {
      setError('Please select one script to continue.');
      return;
    }

    // Save selected scripts to database
    try {
      const token = getValidToken(session);
      const apiUrl = process.env.REACT_APP_API_URL || '';
      
      // Format selected scripts for database
      const scriptsForDB = selectedScripts.map(s => ({
        angle_id: s.angle_id,
        hook_id: s.hook_id,
        script_id: s.script.script_id,
        body: s.script.content
      }));
      
      console.log('💾 Saving selected scripts to DB:', {
        campaignId,
        count: scriptsForDB.length,
        firstScript: scriptsForDB[0]
      });
      
      const response = await fetch(`${apiUrl}/video-ads-v2/campaign/${campaignId}/scripts/selected`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          selected_scripts: scriptsForDB
        })
      });
      
      if (!response.ok) {
        console.error('Failed to save selected scripts');
      } else {
        console.log('✅ Selected scripts saved successfully');
      }
    } catch (error) {
      console.error('Error saving selected scripts:', error);
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
                s.hook_id === hook.selected_hook.hook_id && 
                s.script.script_id === script.script_id
              )
            )
          })).filter(hook => hook.scripts.length > 0)
        })).filter(angle => angle.hooks.length > 0)
      }
    };

    // Preserve navigation flags from location state
    const state = location.state || {};
    navigate('/video-ads-v2/voice-actor', { state: { 
        campaignId,
        selectedScripts: formattedScripts,
        isFromVideo: state.isFromVideo, // Preserve if coming from video flow
        isFromAudio: state.isFromAudio  // Preserve if coming from audio flow
      } });
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
                onClick={() => navigate('/video-ads-v2/hooks', { state: { 
                    campaignId,
                    isFromVideo: locationState.isFromVideo,
                    isFromAudio: locationState.isFromAudio
                  } })}
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
        <>
          {/* Header */}
          <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 2 }}>
            <ScriptIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            {selectedScripts.length > 0 && (
              <Chip 
                icon={<CheckCircleIcon />} 
                label={`${selectedScripts.length} Script Selected`}
                color="success" 
                variant="outlined" 
                size="small"
              />
            )}
          </Box>
          
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            Select Your Script (V2)
          </Typography>
          
          <Typography variant="h6" color="text.secondary">
            Choose one script that best represents your campaign message. These scripts are generated using Claude AI with your complete business context.
          </Typography>
          
          <Typography variant="body2" color="info.main" sx={{ mt: 1 }}>
            ℹ️ You can select only one script to proceed to the next step.
          </Typography>
        </Box>

        {(isLoading || loadingFromDB) && (
          <Box sx={{ mb: 3 }}>
            <LinearProgress />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
              {isLoading ? 'Generating scripts with Claude AI... This may take a moment.' : 'Loading scripts from database...'}
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
                  onClick={() => navigate('/video-ads-v2/marketing-angles', { state: { campaignId } })}
                >
                  Go Back
                </Button>
              ) : null
            }
          >
            {error}
          </Alert>
        )}

        {/* Debug: Show current state */}
        {console.log('🎨 Render state:', { 
          isLoading, 
          loadingFromDB, 
          scriptsDataLength: scriptsData.length,
          shouldRender: !isLoading && !loadingFromDB && scriptsData.length > 0 
        })}
        
        {!isLoading && !loadingFromDB && scriptsData.length > 0 && (
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
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                      {getCategoryIcon(angleData.selected_angle.type)}
                      <Typography variant="h5" fontWeight="bold">
                        Angle #{angleData.selected_angle.angle || angleIndex + 1}: {angleData.selected_angle.concept || angleData.selected_angle.angle_concept || ''}
                      </Typography>
                      <Chip 
                        label={angleData.selected_angle.type} 
                        color={angleData.selected_angle.type === 'positive' ? 'success' : 'warning'}
                        size="small"
                        sx={{ fontWeight: 'bold' }}
                      />
                    </Box>
                    <Typography variant="body2" sx={{ opacity: 0.9 }}>
                      Category: {angleData.selected_angle.category || angleData.selected_angle.angle_category || ''}
                    </Typography>
                  </Box>

                  {/* Hooks and Scripts */}
                  <Box sx={{ bgcolor: 'background.paper', borderRadius: '0 0 16px 16px' }}>
                    {angleData.hooks.map((hookData, hookIndex) => (
                      <Box key={hookData.selected_hook.hook_id} sx={{ p: 3, borderBottom: hookIndex < angleData.hooks.length - 1 ? '1px solid' : 'none', borderColor: 'divider' }}>
                        {/* Hook Header */}
                        <Box sx={{ mb: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                            <PsychologyIcon color="primary" />
                            <Typography variant="h6" fontWeight="bold" color="primary">
                              Hook: {hookData.selected_hook.hook_text}
                            </Typography>
                            <Chip 
                              label={hookData.selected_hook.hook_category.replace('_', ' ')} 
                              variant="outlined" 
                              size="small"
                            />
                          </Box>
                        </Box>

                        {/* Scripts Grid */}
                        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
                          {hookData.scripts.map((script, scriptIndex) => {
                            const isSelected = isScriptSelected(angleData.selected_angle.id, hookData.selected_hook.hook_id || hookData.selected_hook.id || '', script);
                            
                            // Log the first script check in detail
                            if (angleIndex === 0 && hookIndex === 0 && scriptIndex === 0 && selectedScripts.length > 0) {
                              console.log('🎯 First script checkbox check:', {
                                angleId: angleData.selected_angle.id,
                                hookId: hookData.selected_hook.hook_id,
                                scriptId: script.script_id || script.id,
                                isSelected: isSelected,
                                selectedScripts: selectedScripts
                              });
                            }
                            
                            return (
                              <Card 
                                key={script.script_id}
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
                                              hookData.selected_hook.hook_id || hookData.selected_hook.id || '',
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
            onClick={() => navigate('/video-ads-v2/hooks', { state: { 
                campaignId,
                isFromVideo: locationState.isFromVideo,
                isFromAudio: locationState.isFromAudio
              } })}
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
        </>
      </Box>
    </Container>
  );
};

export default Scripts;
