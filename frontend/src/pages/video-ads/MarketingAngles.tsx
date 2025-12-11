import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Card, 
  CardContent,
  Grid,
  Chip,
  Checkbox,
  FormControlLabel,
  Alert,
  LinearProgress,
  Container,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  Psychology as PsychologyIcon,
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  CheckCircle as CheckCircleIcon
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
  angle: number;
  category: string;
  concept: string;
  type: "positive" | "negative";
}

interface MarketingAnglesResponse {
  thread_id: string;
  positive_angles: MarketingAngle[];
  negative_angles: MarketingAngle[];
  raw_response: string;
}

interface LocationState {
  productInfo?: ProductInfo;
  isFromURL?: boolean;
}

const MarketingAngles: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, session } = useAuth();
  const { productInfo, isFromURL } = (location.state as LocationState) || {};

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [marketingAngles, setMarketingAngles] = useState<MarketingAnglesResponse | null>(null);
  const [selectedAngles, setSelectedAngles] = useState<MarketingAngle[]>([]);
  const [threadId, setThreadId] = useState<string>('');

  useEffect(() => {
    if (!productInfo) {
      navigate('/video-ads/product-info');
      return;
    }
    
    // Automatically generate marketing angles when component mounts
    generateMarketingAngles();
  }, [productInfo]);

  const generateMarketingAngles = async () => {
    if (!productInfo) return;

    setIsLoading(true);
    setError('');

    try {
      // Get valid token (JWT or dev-token fallback)
      const token = getValidToken(session);
      const apiUrl = `${process.env.REACT_APP_API_URL}/video-ads/create-marketing-angles`;
      
      console.log('🔍 MarketingAngles API Debug:', {
        token: token?.substring(0, 20) + '...',
        tokenLength: token?.length,
        apiUrl,
        hasSession: !!session,
        sessionKeys: session ? Object.keys(session) : null
      });

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          product_info: productInfo
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ MarketingAngles API Error:', {
          status: response.status,
          statusText: response.statusText,
          errorText
        });
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ MarketingAngles API Success:', { threadId: data.thread_id });
      setMarketingAngles(data);
      setThreadId(data.thread_id);
      
    } catch (err: any) {
      console.error('Marketing angles generation error:', err);
      setError(`Failed to generate marketing angles: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAngleSelection = (angle: MarketingAngle, isSelected: boolean) => {
    if (isSelected) {
      setSelectedAngles(prev => [...prev, angle]);
    } else {
      setSelectedAngles(prev => prev.filter(a => a.angle !== angle.angle));
    }
  };

  const handleBack = () => {
    navigate('/video-ads/product-info', { 
      state: { 
        extractedData: productInfo, // Pass the product info back as extractedData
        isFromURL: isFromURL,
        isFromMarketingAngles: true // Flag to indicate this is coming back from marketing angles
      } 
    });
  };

  const handleNext = () => {
    if (selectedAngles.length === 0) {
      setError('Please select at least one marketing angle to continue.');
      return;
    }

    // Format selected angles with angle_id for hooks endpoint
    const formattedAngles = selectedAngles.map(angle => ({
      angle_id: `angle_${angle.angle}`,
      angle: angle.angle,
      category: angle.category,
      concept: angle.concept,
      type: angle.type
    }));

    navigate('/video-ads/hooks', { 
      state: { 
        productInfo,
        selectedAngles: formattedAngles,
        threadId,
        isFromURL 
      } 
    });
  };

  const renderAngleCard = (angle: MarketingAngle) => {
    const isSelected = selectedAngles.some(a => a.angle === angle.angle);
    
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
                  label={`Angle ${angle.angle}`}
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

  if (!productInfo) {
    return (
      <Container maxWidth="md">
        <Box textAlign="center" py={8}>
          <Typography variant="h5" color="text.secondary">
            No product information found. Please start from the beginning.
          </Typography>
          <Button 
            variant="contained" 
            onClick={() => navigate('/video-ads/import-from-url')}
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
            <Chip 
              icon={<PsychologyIcon />} 
              label={`Product: ${productInfo.product_name}`}
              color="primary" 
              variant="outlined" 
              size="small"
            />
            {threadId && (
              <Chip 
                label={`Thread: ${threadId.slice(0, 8)}...`}
                color="secondary" 
                variant="outlined" 
                size="small"
              />
            )}
          </Box>
          
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            Select Marketing Angles
          </Typography>
          
          <Typography variant="h6" color="text.secondary">
            Choose the marketing angles that best resonate with your target audience. 
            You can select multiple angles to create diverse video content.
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {isLoading && (
          <Card elevation={3} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 4 }}>
              <Box textAlign="center">
                <PsychologyIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Generating Marketing Angles...
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  Our AI is analyzing your product and creating compelling marketing angles. This may take up to 3 minutes.
                </Typography>
                <LinearProgress sx={{ mb: 2 }} />
                <Typography variant="caption" color="text.secondary">
                  Running 4 specialized AI assistants in sequence...
                </Typography>
              </Box>
            </CardContent>
          </Card>
        )}

        {marketingAngles && !isLoading && (
          <>
            <Alert severity="success" sx={{ mb: 3 }} icon={<CheckCircleIcon />}>
              Successfully generated {marketingAngles.positive_angles.length + marketingAngles.negative_angles.length} marketing angles! 
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
            sx={{ px: 4, py: 1.5, fontSize: '1.1rem' }}
          >
            Continue to Hooks ({selectedAngles.length} selected)
          </Button>
        </Box>

        <Box textAlign="center" mt={3}>
          <Typography variant="caption" color="text.secondary">
            Marketing angles help determine the emotional approach and messaging strategy for your video ads.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default MarketingAngles;
