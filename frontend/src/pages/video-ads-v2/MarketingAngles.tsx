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
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  Psychology as PsychologyIcon,
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  CheckCircle as CheckCircleIcon,
  AutoAwesome as AIIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';

interface ProductInfo {
  product_name: string;
  product_information: string;
  target_audience: string;
  price: string;
  problem_solved: string;
  differentiation: string;
  additional_information: string;
}

interface MarketingAngle {
  angle: number;  // Keep for backward compatibility
  angle_id?: string;  // New field: "angle_1", "angle_2", etc.
  angle_number?: number;  // New field: explicit angle number
  category: string;
  concept: string;
  type: "positive" | "negative";
}

interface MarketingAnglesResponse {
  positive_angles: MarketingAngle[];
  negative_angles: MarketingAngle[];
  conversation_id?: string; // Legacy support
  campaign_id?: string; // V3
}

interface LocationState {
  productInfo?: ProductInfo;
  campaignId?: string;
  forceGenerate?: boolean;
  documentUrls?: string[];
}

const MarketingAnglesV2: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { session } = useAuth();
  const locationState = (location.state as LocationState) || {};
  const { productInfo, campaignId, forceGenerate, documentUrls } = locationState;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [marketingAngles, setMarketingAngles] = useState<MarketingAnglesResponse | null>(null);
  const [selectedAngles, setSelectedAngles] = useState<MarketingAngle[]>([]);
  const [currentCampaignId, setCurrentCampaignId] = useState<string>(campaignId || '');
  const [loadingFromDB, setLoadingFromDB] = useState(false);
  const [originalSelectedAngles, setOriginalSelectedAngles] = useState<MarketingAngle[]>([]);
  const [hasAngleChanges, setHasAngleChanges] = useState(false);

  const loadMarketingAnglesFromDB = async () => {
    const idToUse = currentCampaignId || campaignId;
    if (!idToUse) return;
    
    setLoadingFromDB(true);
    setError('');
    
    try {
      const token = getValidToken(session);
      const apiUrl = `${process.env.REACT_APP_API_URL || ''}/video-ads-v2/campaign/${idToUse}/marketing-analysis`;
      
      console.log('📚 Loading marketing angles from DB for campaign:', idToUse);
      
      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Loaded marketing angles from DB:', data);
        
        // Convert DB format to component format
        // V3 stores as "angles", V2 stores as "angles_generation"
        const anglesData = data.angles || data.angles_generation;
        if (anglesData) {
          setMarketingAngles({
            positive_angles: anglesData.positive_angles || [],
            negative_angles: anglesData.negative_angles || [],
            campaign_id: idToUse,
            conversation_id: idToUse // Legacy support
          });
          
          // Load selected angles if any
          if (data.selected_angles && data.selected_angles.length > 0) {
            console.log('✅ Loading selected angles from DB:', data.selected_angles);
            setSelectedAngles(data.selected_angles);
            setOriginalSelectedAngles(data.selected_angles);
          } else {
            console.log('📌 No selected angles found in DB response');
          }
        } else {
          console.warn('⚠️ No angles data found in DB response');
          // If no angles data, generate new
          await generateMarketingAngles();
        }
      } else {
        console.warn('⚠️ Could not load from DB, will regenerate');
        // If loading fails, generate new angles
        await generateMarketingAngles();
      }
    } catch (error) {
      console.error('Error loading marketing angles from DB:', error);
      // Fallback to generating new angles
      await generateMarketingAngles();
    } finally {
      setLoadingFromDB(false);
    }
  };

  const generateMarketingAngles = async () => {
    if (!productInfo) return;

    setIsLoading(true);
    setError('');

    try {
      // Get valid token (JWT or dev-token fallback)
      const token = getValidToken(session);
      const apiUrl = `${process.env.REACT_APP_API_URL || ''}/video-ads-v2/create-marketing-angles`;
      
      console.log('🔍 MarketingAnglesV2 API Debug:', {
        token: token?.substring(0, 20) + '...',
        tokenLength: token?.length,
        apiUrl,
        hasSession: !!session,
        sessionKeys: session ? Object.keys(session) : null
      });

      // Use create-marketing-analysis if documents are provided, otherwise use create-marketing-angles
      const endpoint = documentUrls && documentUrls.length > 0
        ? '/video-ads-v2/create-marketing-analysis'
        : '/video-ads-v2/create-marketing-angles';

      const apiUrlWithDocs = `${process.env.REACT_APP_API_URL || ''}${endpoint}`;

      const requestBody = {
        product_info: {
          product_name: productInfo.product_name,
          product_information: productInfo.product_information,
          target_audience: productInfo.target_audience,
          price: productInfo.price,
            problem_solved: productInfo.problem_solved,
            differentiation: productInfo.differentiation,
            additional_information: productInfo.additional_information
          },
          force_new_conversation: false,
          ...(documentUrls && documentUrls.length > 0 ? { document_urls: documentUrls } : {})
        };

      const response = await fetch(apiUrlWithDocs, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ MarketingAnglesV2 API Error:', {
          status: response.status,
          statusText: response.statusText,
          errorText
        });
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      const newCampaignId = data.campaign_id || data.conversation_id; // Support both formats
      console.log('✅ MarketingAnglesV2 API Success:', { campaignId: newCampaignId });

      // When using create-marketing-analysis endpoint, angles are nested in analysis.angles_generation
      // When using create-marketing-angles endpoint, angles are at the root level
      const anglesData = data.analysis?.angles_generation || data;
      setMarketingAngles(anglesData);
      setCurrentCampaignId(newCampaignId);
      
    } catch (err: any) {
      console.error('Marketing angles generation error:', err);
      setError(`Failed to generate marketing angles: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Decide whether to load from DB or generate new angles
    if (productInfo && (forceGenerate || !campaignId)) {
      // Generate new angles if:
      // 1. Product info provided and forceGenerate is true, OR
      // 2. Product info provided but no campaignId yet (new campaign)
      console.log('🆕 Generating new marketing angles');
      generateMarketingAngles();
    } else if (campaignId || currentCampaignId) {
      // Load from database if we have campaignId
      console.log('📚 Loading marketing angles from database');
      loadMarketingAnglesFromDB();
    } else {
      // No product info and no campaign ID - go back
      console.log('❌ Missing required data, navigating back');
      navigate('/video-ads-v2/product-info');
    }
  }, []);

  // Check if selected angles have changed
  useEffect(() => {
    if (originalSelectedAngles.length > 0 || selectedAngles.length > 0) {
      const changed = originalSelectedAngles.length !== selectedAngles.length ||
        !selectedAngles.every(angle => 
          originalSelectedAngles.some(orig => orig.angle === angle.angle)
        );
      setHasAngleChanges(changed);
    }
  }, [selectedAngles, originalSelectedAngles]);

  const handleAngleSelection = (angle: MarketingAngle, isSelected: boolean) => {
    if (isSelected) {
      // Ensure the angle has all necessary fields when selecting
      const angleWithId = {
        ...angle,
        angle_id: angle.angle_id || `angle_${angle.angle}`,
        angle_number: angle.angle_number || angle.angle
      };
      setSelectedAngles(prev => [...prev, angleWithId]);
    } else {
      // Remove using the same comparison logic as renderAngleCard
      setSelectedAngles(prev => prev.filter(a => {
        // Try comparing by angle_id first
        if (angle.angle_id && a.angle_id) {
          return angle.angle_id !== a.angle_id;
        }
        // Try comparing by angle_number if available
        if (angle.angle_number !== undefined && a.angle_number !== undefined) {
          return !(angle.angle_number === a.angle_number && angle.type === a.type);
        }
        // Fallback to angle number and type comparison
        return !(angle.angle === a.angle && angle.type === a.type);
      }));
    }
  };

  const handleBack = () => {
    navigate('/video-ads-v2/product-info', { 
      state: { 
        campaignId: currentCampaignId || campaignId
      } 
    });
  };

  const handleNext = async () => {
    if (selectedAngles.length === 0) {
      setError('Please select at least one marketing angle to continue.');
      return;
    }

    // Transform selected angles to match SelectedAngleV2 interface
    const transformedAngles = selectedAngles.map((angle) => ({
      angle_id: angle.angle_id || `angle_${angle.angle}`, // Use angle_id if available, otherwise generate
      angle_number: angle.angle_number || angle.angle,
      angle: angle.angle,
      category: angle.category,
      concept: angle.concept,
      type: angle.type
    }));

    // Save selected angles to database
    if (campaignId) {
      try {
        const token = getValidToken(session);
        await fetch(
          `${process.env.REACT_APP_API_URL || ''}/video-ads-v2/campaign/${campaignId}/selected-angles`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              selected_angles: transformedAngles
            })
          }
        );
      } catch (error) {
        console.error('Error saving selected angles:', error);
      }
    }

    // Navigate to V2 hooks page
    navigate('/video-ads-v2/hooks', {
      state: {
        campaignId: currentCampaignId || campaignId,
        selectedAngles: hasAngleChanges ? transformedAngles : undefined,
        forceGenerate: hasAngleChanges
      }
    });
  };

  const renderAngleCard = (angle: MarketingAngle) => {
    // Use multiple comparison methods to ensure proper matching
    const isSelected = selectedAngles.some(a => {
      // Try comparing by angle_id first
      if (angle.angle_id && a.angle_id) {
        return angle.angle_id === a.angle_id;
      }
      // Try comparing by angle_number if available
      if (angle.angle_number !== undefined && a.angle_number !== undefined) {
        return angle.angle_number === a.angle_number && angle.type === a.type;
      }
      // Fallback to angle number and type comparison
      return angle.angle === a.angle && angle.type === a.type;
    });
    
    return (
      <Card 
        key={angle.angle}
        elevation={isSelected ? 4 : 2}
        sx={{ 
          mb: 2, 
          border: isSelected ? '2px solid' : '1px solid',
          borderColor: isSelected ? 'primary.main' : 'divider',
          transition: 'all 0.3s ease'
        }}
      >
        <CardContent>
          <Box display="flex" alignItems="flex-start" gap={2}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={isSelected}
                  onChange={(e) => handleAngleSelection(angle, e.target.checked)}
                  color="primary"
                />
              }
              label=""
              sx={{ margin: 0 }}
            />
            
            <Box flex={1}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Chip 
                  icon={angle.type === 'positive' ? <TrendingUpIcon /> : <TrendingDownIcon />}
                  label={`Angle ${angle.angle_number || angle.angle}`}
                  color={angle.type === 'positive' ? 'success' : 'warning'}
                  size="small"
                />
                <Typography variant="caption" color="text.secondary">
                  {angle.type === 'positive' ? 'Positive' : 'Negative'} Angle
                </Typography>
              </Box>
              
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                {angle.category}
              </Typography>
              
              <Typography variant="body2" color="text.secondary">
                {angle.concept}
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  };

  if (!productInfo && !campaignId) {
    return (
      <Container maxWidth="md">
        <Box textAlign="center" py={8}>
          <Typography variant="h5" color="text.secondary">
            No product information found. Please start from the beginning.
          </Typography>
          <Button 
            variant="contained" 
            onClick={() => navigate('/video-ads-v2/import-from-url')}
            sx={{ mt: 2 }}
          >
            Start Over
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
            {productInfo && (
              <Chip 
                icon={<PsychologyIcon />} 
                label={`Product: ${productInfo.product_name}`}
                color="primary" 
                variant="outlined" 
                size="small"
              />
            )}
            <Chip 
              icon={<AIIcon />} 
              label="Powered by AI" 
              color="secondary" 
              variant="outlined" 
              size="small"
            />
            {campaignId && (
              <Chip 
                label={`Campaign: ${campaignId.slice(0, 8)}...`}
                color="info" 
                variant="outlined" 
                size="small"
              />
            )}
          </Box>
          
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            Select Marketing Angles (2.0)
          </Typography>
          
          <Typography variant="h6" color="text.secondary">
            AI has analyzed your product and generated comprehensive marketing angles. 
            Choose the ones that best resonate with your target audience.
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {(isLoading || loadingFromDB) && (
          <Card elevation={3} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 4 }}>
              <Box textAlign="center">
                <AIIcon sx={{ fontSize: 48, color: 'secondary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  {loadingFromDB ? 'Loading Your Analysis...' : 'AI is Analyzing Your Product...'}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  {loadingFromDB 
                    ? 'Retrieving your previously generated marketing angles from the database.'
                    : 'Our advanced AI is running a comprehensive 4-phase analysis to create the most effective marketing angles for your product.'}
                </Typography>
                <LinearProgress sx={{ mb: 2 }} />
                {!loadingFromDB && (
                  <Typography variant="caption" color="text.secondary">
                    Phase 1: Avatar Analysis → Phase 2: Journey Mapping → Phase 3: Objections Analysis → Phase 4: Angle Generation
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        )}

        {marketingAngles && !isLoading && !loadingFromDB && (
          <>
            <Alert severity="success" sx={{ mb: 3 }} icon={<CheckCircleIcon />}>
              🎉 AI successfully generated {marketingAngles.positive_angles.length + marketingAngles.negative_angles.length} marketing angles with comprehensive analysis! 
              Select at least one to continue.
            </Alert>

            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Selected: {selectedAngles.length} angle{selectedAngles.length !== 1 ? 's' : ''}
              </Typography>
            </Box>

            {marketingAngles.positive_angles.length > 0 && (
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" alignItems="center" gap={2}>
                    <TrendingUpIcon color="success" />
                    <Typography variant="h6">
                      Positive Angles ({marketingAngles.positive_angles.length})
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box>
                    {marketingAngles.positive_angles.map(angle => 
                      renderAngleCard(angle)
                    )}
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}

            {marketingAngles.negative_angles.length > 0 && (
              <Accordion defaultExpanded sx={{ mt: 2 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" alignItems="center" gap={2}>
                    <TrendingDownIcon color="warning" />
                    <Typography variant="h6">
                      Negative Angles ({marketingAngles.negative_angles.length})
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box>
                    {marketingAngles.negative_angles.map(angle => 
                      renderAngleCard(angle)
                    )}
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}
          </>
        )}

        <Box display="flex" justifyContent="space-between" mt={4}>
          <Button
            variant="outlined"
            size="large"
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
            disabled={isLoading}
            sx={{ px: 4, py: 1.5 }}
          >
            Back to Product Info
          </Button>

          <Button
            variant="contained"
            size="large"
            endIcon={<ArrowForwardIcon />}
            onClick={handleNext}
            disabled={isLoading || selectedAngles.length === 0}
            sx={{ 
              px: 4, 
              py: 1.5, 
              fontSize: '1.1rem',
              background: 'linear-gradient(45deg, #FF6B6B 30%, #4ECDC4 90%)',
              '&:hover': {
                background: 'linear-gradient(45deg, #FF5722 30%, #00BCD4 90%)',
              }
            }}
          >
            Continue with Analysis ({selectedAngles.length} selected)
          </Button>
        </Box>

        <Box textAlign="center" mt={3}>
          <Typography variant="caption" color="text.secondary">
            🤖 These angles are powered by AI's advanced reasoning and comprehensive product analysis.
            Each angle comes with detailed customer psychology insights.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default MarketingAnglesV2;
