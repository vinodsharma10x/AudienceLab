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
  Collapse,
  IconButton
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Whatshot as HookIcon,
  CheckCircle as CheckCircleIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getCampaignId } from '../../utils/v3-migration';

interface SelectedAngleV2 {
  angle_id: string;
  angle: number;
  category: string;
  concept: string;
  type: 'positive' | 'negative';
}

// Hook item matching backend HookItem model
interface HookItem {
  hook_id: string;
  hook_text: string;
  hook_category: string;
}

interface HooksByCategoryV2 {
  direct_question: HookItem[];
  shocking_fact: HookItem[];
  demonstration: HookItem[];
  alarm_tension: HookItem[];
  surprise_curiosity: HookItem[];
  list_enumeration: HookItem[];
  personal_story: HookItem[];
}

interface AngleWithHooksV2 {
  angle_id: string;
  angle_number: number;
  angle_category: string;
  angle_concept: string;
  angle_type: 'positive' | 'negative';
  hooks_by_category: HooksByCategoryV2;
}

interface HooksV2Response {
  conversation_id: string;
  hooks_by_angle: AngleWithHooksV2[];
  raw_response: string;
}

interface LocationState {
  selectedAngles?: SelectedAngleV2[];
  campaignId?: string;
  forceGenerate?: boolean;
}

interface SelectedHookV2 {
  angle_id: string;
  angle: number;
  category: string;
  hook_id: string;  // Added hook_id
  hook_text: string;
}

const HooksV2: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  const locationState = (location.state as LocationState) || {};
  const { selectedAngles, campaignId, forceGenerate } = locationState;
  
  // Debug logging
  console.log('🔍 HooksV2 Component Mounted:', {
    locationState,
    selectedAngles: selectedAngles?.length || 0,
    campaignId,
    forceGenerate,
    isComingBackFromScripts: !selectedAngles && campaignId
  });

  const [hooksData, setHooksData] = useState<AngleWithHooksV2[]>([]);
  const [selectedHooks, setSelectedHooks] = useState<SelectedHookV2[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [loadingFromDB, setLoadingFromDB] = useState(false);
  const [originalSelectedHooks, setOriginalSelectedHooks] = useState<SelectedHookV2[]>([]);
  const [hasChanges, setHasChanges] = useState<boolean | undefined>(undefined);
  const [expandedAngles, setExpandedAngles] = useState<Set<string>>(new Set());

  useEffect(() => {
    console.log('🎯 HooksV2 useEffect decision:', {
      campaignId,
      hasSelectedAngles: !!selectedAngles,
      forceGenerate
    });
    
    // Decide whether to load from DB or generate new hooks
    if (selectedAngles && (forceGenerate || !campaignId)) {
      // Generate new hooks if:
      // 1. Selected angles provided and forceGenerate is true, OR
      // 2. Selected angles provided but no campaignId yet (new campaign)
      console.log('🔄 Generating new hooks');
      generateHooks();
    } else if (campaignId) {
      // Load from database if we have campaignId
      console.log('📚 Loading hooks from database');
      loadHooksFromDatabase();
    } else {
      console.log('❌ Missing required data');
      setError('Missing required data. Please go back to marketing angles.');
    }
  }, [selectedAngles, campaignId, forceGenerate]);

  // Initialize expanded angles when hooks data loads
  useEffect(() => {
    if (hooksData.length > 0 && expandedAngles.size === 0) {
      // Sort angles by angle_number and expand only the first one
      const sortedAngles = [...hooksData].sort((a, b) => a.angle_number - b.angle_number);
      if (sortedAngles.length > 0) {
        // Expand only the first angle
        setExpandedAngles(new Set([sortedAngles[0].angle_id]));
      }
    }
  }, [hooksData]);

  // Track changes in selected hooks
  useEffect(() => {
    if (originalSelectedHooks.length > 0 || selectedHooks.length > 0) {
      const changed = originalSelectedHooks.length !== selectedHooks.length ||
        !selectedHooks.every(hook => 
          originalSelectedHooks.some(orig => 
            orig.angle_id === hook.angle_id && 
            orig.hook_text === hook.hook_text
          )
        );
      setHasChanges(changed);
    }
  }, [selectedHooks, originalSelectedHooks]);

  const loadHooksFromDatabase = async () => {
    console.log('📖 loadHooksFromDatabase called with campaignId:', campaignId);
    setLoadingFromDB(true);
    setError('');
    
    if (!campaignId) {
      console.error('No campaign ID available for loading hooks');
      setError('No campaign ID available');
      setLoadingFromDB(false);
      return;
    }
    
    console.log('📖 Loading hooks from DB for campaign:', campaignId);
    
    try {
      // Smart token selection
      let token = session?.access_token || 'dev-token';
      
      // Check if JWT token is expired
      if (session?.access_token) {
        try {
          const payload = JSON.parse(atob(session.access_token.split('.')[1]));
          const now = Math.floor(Date.now() / 1000);
          if (payload.exp && payload.exp < now) {
            token = 'dev-token';
          }
        } catch (e) {
          token = 'dev-token';
        }
      }
      
      const apiUrl = process.env.REACT_APP_API_URL || '';
      const fullUrl = `${apiUrl}/video-ads-v2/campaign/${campaignId}/hooks`;
      console.log('📖 Fetching hooks from URL:', fullUrl);
      console.log('📖 Using token:', token.substring(0, 20) + '...');
      
      const response = await fetch(fullUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('📖 DB Response:', response.status, response.ok);
      
      if (response.ok) {
        const data = await response.json();
        console.log('📖 DB Data received:', data);
        console.log('📖 DB Data keys:', Object.keys(data));
        
        // Handle both V2 and V3 response formats
        const hooksArray = data.hooks_data?.hooks_by_angle || data.hooks_by_angle;
        console.log('📖 Hooks array extracted:', hooksArray);
        
        if (hooksArray && hooksArray.length > 0) {
          console.log('📖 Setting hooks data:', hooksArray.length, 'angles');
          
          // Log the structure of hooks data for debugging
          if (hooksArray.length > 0) {
            const firstAngle = hooksArray[0];
            const firstCategory = Object.keys(firstAngle.hooks_by_category)[0];
            const firstHook = firstAngle.hooks_by_category[firstCategory]?.[0];
            console.log('📖 Hooks data structure:', {
              firstAngle_id: firstAngle.angle_id,
              firstCategory,
              firstHook,
              allCategories: Object.keys(firstAngle.hooks_by_category)
            });
          }
          
          setHooksData(hooksArray);
          
          // Load selected hooks if any
          if (data.selected_hooks && data.selected_hooks.length > 0) {
            const loaded: SelectedHookV2[] = [];
            console.log('📖 Raw selected_hooks from DB:', data.selected_hooks);
            
            data.selected_hooks.forEach((savedHook: any, index: number) => {
              if (index === 0) {
                console.log('📖 First raw hook from DB:', JSON.stringify(savedHook, null, 2));
              }
              
              // Check if this is the complex format from Scripts page (has hooks_by_category)
              if (savedHook.hooks_by_category) {
                // This is the format saved by Scripts page - extract selected hooks from it
                const angleId = savedHook.angle_id;
                const angleNumber = savedHook.angle_number || savedHook.angle || 0;
                
                // Iterate through all categories and hooks
                for (const [category, hooks] of Object.entries(savedHook.hooks_by_category)) {
                  if (Array.isArray(hooks) && hooks.length > 0) {
                    // For the Scripts format, we assume all hooks in the structure were selected
                    for (const hook of hooks as any[]) {
                      loaded.push({
                        angle_id: angleId,
                        angle: angleNumber,
                        category: category,
                        hook_id: hook.hook_id,
                        hook_text: hook.hook_text
                      });
                    }
                  }
                }
              }
              // Simple format - hook was selected directly in Hooks page
              else if (savedHook.hook_id && savedHook.hook_text) {
                loaded.push({
                  angle_id: savedHook.angle_id || '',
                  angle: savedHook.angle || 0,
                  category: savedHook.category || savedHook.hook_type || '',
                  hook_id: savedHook.hook_id,
                  hook_text: savedHook.hook_text
                });
              }
              // Partial data - try to find the hook in the hooks data
              else if (savedHook.angle_id && hooksArray) {
                // Find the angle
                const angleData = hooksArray.find((a: any) => a.angle_id === savedHook.angle_id);
                if (angleData) {
                  // Search through all categories for a matching hook
                  for (const [category, hooks] of Object.entries(angleData.hooks_by_category)) {
                    if (Array.isArray(hooks)) {
                      for (const hook of hooks as any[]) {
                        // Match by hook_id if available, or by text
                        if ((savedHook.hook_id && hook.hook_id === savedHook.hook_id) ||
                            (savedHook.hook_text && hook.hook_text === savedHook.hook_text)) {
                          loaded.push({
                            angle_id: savedHook.angle_id,
                            angle: angleData.angle_number || savedHook.angle || 0,
                            category: category,
                            hook_id: hook.hook_id,
                            hook_text: hook.hook_text
                          });
                          break;
                        }
                      }
                    }
                  }
                }
              }
            });
            
            console.log('📖 Reconstructed selected hooks:', loaded);
            
            // Use setTimeout to ensure hooks data is rendered first
            setTimeout(() => {
              setSelectedHooks(loaded);
              setOriginalSelectedHooks(loaded);
              console.log('📖 Selected hooks state set');
            }, 100);
          } else {
            console.log('📖 No selected hooks in DB response');
          }
        } else {
          // No hooks found, might need to generate
          console.log('📖 No hooks found in database');
          if (selectedAngles && selectedAngles.length > 0) {
            console.log('📖 Generating new hooks with selected angles');
            generateHooks();
          } else {
            setError('No hooks found. Please go back to marketing angles to generate hooks.');
          }
        }
      } else {
        console.log('📖 Failed to load from DB, status:', response.status);
        // Don't try to generate if we don't have selectedAngles
        if (selectedAngles && selectedAngles.length > 0) {
          generateHooks();
        } else {
          setError('Unable to load hooks. Please go back to marketing angles and select angles.');
        }
      }
    } catch (error) {
      console.error('Error loading hooks from database:', error);
      setError('Failed to load hooks. Please try generating them again.');
    } finally {
      setLoadingFromDB(false);
    }
  };

  const generateHooks = async () => {
    if (!selectedAngles || !campaignId) return;

    setIsLoading(true);
    setError('');

    try {
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
      
      console.log('🔐 V2 Token being used:', token.substring(0, 20) + '...'); // Debug logging
      const apiUrl = process.env.REACT_APP_API_URL || '';
      const fullUrl = `${apiUrl}/video-ads-v2/create-hooks`;
      console.log('🌐 V2 API URL:', fullUrl); // Debug logging
      
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          conversation_id: campaignId,  // Backend expects conversation_id
          selected_angles: selectedAngles
        })
      });

      console.log('📡 V2 Response status:', response.status); // Debug logging
      console.log('📡 V2 Response ok:', response.ok); // Debug logging

      if (!response.ok) {
        const errorText = await response.text();
        console.log('❌ V2 Error response:', errorText); // Debug logging
        
        // Handle specific error messages
        if (response.status === 400 && errorText.includes('Conversation expired')) {
          setError('Session expired. Please restart from the marketing angles step.');
        } else {
          setError(`Failed to generate hooks. Please try again. (${response.status})`);
        }
        return;
      }

      const data: HooksV2Response = await response.json();
      console.log('📡 V2 Hooks generated:', data.hooks_by_angle?.length || 0, 'angles');
      setHooksData(data.hooks_by_angle);
      
      // Don't auto-select any hooks - let user choose
      // If you want to keep auto-selection, uncomment the code below
      /*
      const autoSelected: SelectedHookV2[] = [];
      data.hooks_by_angle.forEach((angleData: AngleWithHooksV2) => {
        if (angleData.hooks_by_category) {
          Object.entries(angleData.hooks_by_category).forEach(([category, hooks]) => {
            if (Array.isArray(hooks) && hooks.length > 0) {
              autoSelected.push({
                angle_id: angleData.angle_id,
                angle: angleData.angle_number,
                category: category,
                hook_text: hooks[0]
              });
            }
          });
        }
      });
      
      console.log('📡 Auto-selected hooks:', autoSelected.length);
      setSelectedHooks(autoSelected);
      setOriginalSelectedHooks(autoSelected);
      */
      
      // Start with no hooks selected
      setSelectedHooks([]);
      setOriginalSelectedHooks([]);
      console.log('📡 Starting with no hooks selected - user will choose');
      
    } catch (err: any) {
      console.error('V2 Hooks generation error:', err);
      if (err instanceof Error && (err.message.includes('Conversation expired') || err.message.includes('404'))) {
        setError('Session expired. Please restart from the marketing angles step.');
      } else {
        setError('Failed to generate hooks. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleHookSelection = (angle_id: string, angle: number, category: string, hook_id: string, hook_text: string, isSelected: boolean) => {
    if (isSelected) {
      // Save complete hook data for proper restoration
      const hookData = {
        angle_id,
        angle,
        category,
        hook_id,
        hook_text
      };
      console.log('➕ Adding hook to selection:', hookData);
      setSelectedHooks(prev => [...prev, hookData]);
    } else {
      console.log('➖ Removing hook from selection:', { angle_id, hook_id });
      setSelectedHooks(prev => prev.filter(h => 
        !(h.angle_id === angle_id && h.hook_id === hook_id)  // Use hook_id for comparison
      ));
    }
  };

  const isHookSelected = (angle_id: string, hook_id: string): boolean => {
    const isSelected = selectedHooks.some(h => 
      h.angle_id === angle_id && h.hook_id === hook_id
    );
    // Debug logging for first hook
    if (hooksData.length > 0 && hooksData[0].hooks_by_category.direct_question?.length > 0 && 
        hooksData[0].hooks_by_category.direct_question[0].hook_id === hook_id) {
      console.log('🔍 Hook selection check:', {
        angle_id,
        hook_id,
        isSelected,
        selectedHooks: selectedHooks.map(h => ({ angle_id: h.angle_id, hook_id: h.hook_id }))
      });
    }
    return isSelected;
  };

  const handleBack = () => {
    navigate('/video-ads-v2/marketing-angles', { state: { 
        campaignId
      } });
  };

  const handleNext = async () => {
    if (selectedHooks.length === 0) {
      setError('Please select at least one hook to continue.');
      return;
    }

    // Save selected hooks to database
    if (campaignId) {
      try {
        // Smart token selection
        let token = session?.access_token || 'dev-token';
        
        // Check if JWT token is expired
        if (session?.access_token) {
          try {
            const payload = JSON.parse(atob(session.access_token.split('.')[1]));
            const now = Math.floor(Date.now() / 1000);
            if (payload.exp && payload.exp < now) {
              token = 'dev-token';
            }
          } catch (e) {
            token = 'dev-token';
          }
        }
        
        const apiUrl = process.env.REACT_APP_API_URL || '';
        console.log('💾 Saving selected hooks to DB:', selectedHooks);
        const response = await fetch(`${apiUrl}/video-ads-v2/campaign/${campaignId}/selected-hooks`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            selected_hooks: selectedHooks
          })
        });
        
        if (!response.ok) {
          console.error('Failed to save selected hooks:', response.status);
        } else {
          console.log('✅ Selected hooks saved successfully');
        }
      } catch (error) {
        console.error('Error saving selected hooks:', error);
      }
    }

    // Transform selected hooks into the format expected by the scripts YAML
    // Format according to scripts_generation.yaml input_sample
    const formattedHooksData = hooksData.map(angleData => {
      // Get all selected hooks for this angle
      const angleSelectedHooks = selectedHooks.filter(h => h.angle_id === angleData.angle_id);
      
      if (angleSelectedHooks.length === 0) return null;

      // Group hooks by category with full hook objects (including hook_id)
      const hooksByCategory: { [key: string]: Array<{hook_id: string, hook_text: string, hook_category: string}> } = {};
      angleSelectedHooks.forEach(hook => {
        if (!hooksByCategory[hook.category]) {
          hooksByCategory[hook.category] = [];
        }
        hooksByCategory[hook.category].push({
          hook_id: hook.hook_id,
          hook_text: hook.hook_text,
          hook_category: hook.category
        });
      });

      return {
        angle_id: angleData.angle_id,  // Changed from 'id' to 'angle_id'
        angle_number: angleData.angle_number,
        angle_category: angleData.angle_category,  // Changed from 'category'
        angle_concept: angleData.angle_concept,    // Changed from 'concept'
        angle_type: angleData.angle_type,          // Changed from 'type'
        hooks_by_category: hooksByCategory
      };
    }).filter(Boolean); // Remove null values

    navigate('/video-ads-v2/scripts', { state: { 
        campaignId,
        selectedHooks: hasChanges ? formattedHooksData : undefined,
        forceGenerate: hasChanges
      } });
  };

  const toggleAngleExpansion = (angleId: string) => {
    setExpandedAngles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(angleId)) {
        newSet.delete(angleId);
      } else {
        newSet.add(angleId);
      }
      return newSet;
    });
  };

  const getAngleIcon = (type: string) => {
    if (type === 'positive') {
      return <TrendingUpIcon sx={{ fontSize: 28, color: 'white' }} />;
    }
    return <TrendingDownIcon sx={{ fontSize: 28, color: 'white' }} />;
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'direct_question': return '❓';
      case 'shocking_fact': return '⚡';
      case 'demonstration': return '🎯';
      case 'alarm_tension': return '🚨';
      case 'surprise_curiosity': return '🎭';
      case 'list_enumeration': return '📝';
      case 'personal_story': return '💭';
      default: return '🎯';
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

  // Define category sort order for consistent display
  const categoryOrder = [
    'direct_question',
    'shocking_fact',
    'demonstration',
    'alarm_tension',
    'surprise_curiosity',
    'list_enumeration',
    'personal_story'
  ];

  // Check if we have required data - moved after all the functions
  const shouldShowError = !campaignId && !selectedAngles;
  
  console.log('🔍 HooksV2 Render Check:', {
    shouldShowError,
    hasSelectedAngles: !!selectedAngles,
    hasCampaignId: !!campaignId,
    isLoading,
    loadingFromDB,
    hooksDataLength: hooksData.length,
    error
  });
  
  if (shouldShowError) {
    console.error('🚫 HooksV2: Missing required data', { 
      hasSelectedAngles: !!selectedAngles, 
      campaignId
    });
    
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            Missing required data. Please restart from the marketing angles step.
            {/* Debug info */}
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Debug: selectedAngles={selectedAngles ? 'present' : 'missing'}, 
              campaignId={campaignId || 'missing'}
            </Typography>
          </Alert>
          <Button
            variant="contained"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/video-ads-v2/marketing-angles')}
          >
            Back to Marketing Angles
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <HookIcon sx={{ fontSize: 32, color: 'primary.main', mr: 1 }} />
            <Typography variant="h4" component="h1" fontWeight="bold">
              Viral Hooks Generation V2
            </Typography>
          </Box>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Claude AI has generated viral hooks for your selected marketing angles. 
            Choose the hooks that best capture attention and engage your audience.
          </Typography>
          
          {/* Progress indicator */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip label="Product Info" variant="filled" size="small" />
            <Chip label="Marketing Analysis" variant="filled" size="small" />
            <Chip label="Marketing Angles" variant="filled" size="small" />
            <Chip 
              label="Hooks Generation" 
              variant="filled" 
              size="small"
              color="primary"
              icon={<CheckCircleIcon />}
            />
            <Chip label="Scripts" variant="outlined" size="small" />
          </Box>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Loading State */}
        {(isLoading || loadingFromDB) && (
          <Box sx={{ mb: 3 }}>
            <LinearProgress />
            <Typography variant="body2" sx={{ mt: 1, textAlign: 'center' }}>
              {isLoading ? 'Claude AI is generating viral hooks for your selected angles...' : 'Loading hooks from your campaign...'}
            </Typography>
          </Box>
        )}

        {/* No Hooks Message */}
        {!isLoading && !loadingFromDB && hooksData.length === 0 && !error && (
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              No hooks available
            </Typography>
            <Typography variant="body2">
              Please go back to Marketing Angles to select angles and generate hooks.
            </Typography>
          </Alert>
        )}

        {/* Hooks Display */}
        {!isLoading && !loadingFromDB && hooksData.length > 0 && (
          <Box sx={{ mb: 4 }}>
            {/* Selection Summary */}
            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Selected Hooks: {selectedHooks.length}
              </Typography>
              <Typography variant="body2">
                Choose hooks that best represent your brand voice and resonate with your target audience.
              </Typography>
            </Alert>

            {/* Hooks by Angle - Sorted by angle number */}
            {[...hooksData].sort((a, b) => a.angle_number - b.angle_number).map((angleData, angleIndex) => {
              const isExpanded = expandedAngles.has(angleData.angle_id);
              const angleSelectedCount = selectedHooks.filter(h => h.angle_id === angleData.angle_id).length;
              
              // Debug log first angle data
              if (angleIndex === 0 && selectedHooks.length > 0) {
                console.log('🎯 First angle rendering:', {
                  angle_id: angleData.angle_id,
                  angle_number: angleData.angle_number,
                  selectedHooksForThisAngle: selectedHooks.filter(h => h.angle_id === angleData.angle_id),
                  allSelectedHooks: selectedHooks
                });
              }
              return (
              <Card 
                key={angleData.angle_id} 
                elevation={3}
                sx={{ 
                  mb: 3,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: 4,
                  overflow: 'visible'
                }}
              >
                {/* Angle Header - Prominent Style */}
                <Box
                  sx={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    p: 3,
                    borderRadius: isExpanded ? '16px 16px 0 0' : '16px',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #5569d8 0%, #6a4196 100%)',
                    }
                  }}
                  onClick={() => toggleAngleExpansion(angleData.angle_id)}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      {getAngleIcon(angleData.angle_type)}
                      <Box>
                        <Typography variant="h5" fontWeight="bold">
                          Angle #{angleData.angle_number}: {angleData.angle_concept}
                        </Typography>
                        <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
                          Category: {angleData.angle_category}
                        </Typography>
                      </Box>
                      <Chip 
                        label={angleData.angle_type} 
                        color={angleData.angle_type === 'positive' ? 'success' : 'warning'}
                        size="small"
                        sx={{ fontWeight: 'bold' }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {angleSelectedCount > 0 && (
                        <Chip 
                          label={`${angleSelectedCount} selected`}
                          size="small"
                          sx={{ 
                            bgcolor: 'rgba(255,255,255,0.2)', 
                            color: 'white',
                            fontWeight: 'bold'
                          }}
                        />
                      )}
                      <IconButton 
                        size="large" 
                        sx={{ color: 'white' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleAngleExpansion(angleData.angle_id);
                        }}
                      >
                        {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </Box>
                  </Box>
                </Box>

                {/* Collapsible Content */}
                <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                  <Box sx={{ bgcolor: 'background.paper', borderRadius: '0 0 16px 16px', p: 3 }}>

                  {/* Hooks by Category - sorted for consistent display */}
                  {Object.entries(angleData.hooks_by_category)
                    .sort(([a], [b]) => {
                      const aIndex = categoryOrder.indexOf(a);
                      const bIndex = categoryOrder.indexOf(b);
                      // If both are in the order list, sort by their position
                      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
                      // If only one is in the list, it comes first
                      if (aIndex !== -1) return -1;
                      if (bIndex !== -1) return 1;
                      // Otherwise sort alphabetically
                      return a.localeCompare(b);
                    })
                    .map(([category, hooks]) => {
                    if (!hooks || hooks.length === 0) return null;
                    
                    return (
                      <Box key={category} sx={{ mb: 3 }}>
                        <Paper elevation={1} sx={{ p: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                            <Typography variant="h6" sx={{ mr: 1 }}>
                              {getCategoryIcon(category)}
                            </Typography>
                            <Box>
                              <Typography variant="subtitle1" fontWeight="bold">
                                {getCategoryLabel(category)}
                              </Typography>
                            </Box>
                          </Box>
                          
                          {hooks
                            .sort((a: HookItem, b: HookItem) => (a.hook_id || '').localeCompare(b.hook_id || '')) // Sort hooks by ID for consistency
                            .map((hook: HookItem, hookIndex: number) => (
                            <FormControlLabel
                              key={hook.hook_id || hookIndex}
                              control={
                                <Checkbox
                                  checked={isHookSelected(angleData.angle_id, hook.hook_id)}
                                  onChange={(e) => handleHookSelection(
                                    angleData.angle_id,
                                    angleData.angle_number,
                                    category,
                                    hook.hook_id,
                                    hook.hook_text,
                                    e.target.checked
                                  )}
                                  color="primary"
                                />
                              }
                              label={
                                <Typography variant="body2" sx={{ lineHeight: 1.5 }}>
                                  {hook.hook_text}
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
                    );
                  })}
                  </Box>
                </Collapse>
              </Card>
            );
            })}
          </Box>
        )}

        {/* Navigation */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
            disabled={isLoading}
          >
            Back to Angles
          </Button>
          
          <Button
            variant="contained"
            endIcon={<ArrowForwardIcon />}
            onClick={handleNext}
            disabled={isLoading || selectedHooks.length === 0}
          >
            Continue to Scripts ({selectedHooks.length} hooks selected)
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default HooksV2;
