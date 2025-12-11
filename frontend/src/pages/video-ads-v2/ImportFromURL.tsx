import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  TextField, 
  Button, 
  Card, 
  CardContent,
  LinearProgress,
  Alert,
  Divider,
  Container
} from '@mui/material';
import { 
  Link as LinkIcon, 
  Upload as UploadIcon,
  Analytics as AnalyticsIcon 
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';

interface ExtractedData {
  product_name?: string;
  product_information?: string;
  target_audience?: string;
  price?: string;
  problem_solved?: string;
  key_benefits?: string[];
  unique_selling_points?: string[];
  additional_info?: string;
  original_url?: string;
  campaign_id?: string;
}

interface LocationState {
  campaignId?: string;
}

const ImportFromURLV2: React.FC = () => {
  const [url, setUrl] = useState('');
  const [originalUrl, setOriginalUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const { user, session } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = (location.state as LocationState) || {};
  const { campaignId } = locationState;

  const isAuthenticated = !!user;

  // Load original URL from campaign if navigating back
  useEffect(() => {
    const loadCampaignUrl = async () => {
      if (campaignId) {
        try {
          const token = getValidToken(session);
          const apiUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${campaignId}`;
          
          const response = await fetch(apiUrl, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.ok) {
            const data = await response.json();
            console.log('📚 Loaded campaign data:', data);
            
            // Set the URL from the campaign data
            if (data.product_url) {
              setUrl(data.product_url);
              setOriginalUrl(data.product_url);
            }
          }
        } catch (error) {
          console.error('Error loading campaign URL:', error);
        }
      }
    };
    
    loadCampaignUrl();
  }, [campaignId, session]);

  // Debug: Log environment variables
  useEffect(() => {
    console.log('🔧 Environment Debug:');
    console.log('📍 REACT_APP_API_URL:', process.env.REACT_APP_API_URL);
    console.log('🌐 Current window location:', window.location.href);
  }, []);

  const parseURL = async (url: string): Promise<ExtractedData> => {
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

      const apiUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/parse-url`;
      console.log('🔍 Making V2 request to:', apiUrl);
      console.log('🔑 Using token:', token.substring(0, 20) + '...');
      console.log('📡 Request URL:', url);

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ url }),
      });

      console.log('📊 Response status:', response.status);
      console.log('📋 Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Response data:', data);
      return data;
    } catch (error) {
      console.error('URL parsing error:', error);
      throw error;
    }
  };

  const handleAnalyzeURL = async () => {
    if (!url.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    if (!isAuthenticated) {
      setError('Please log in to use the URL analysis feature');
      return;
    }

    // Check if URL has changed from original
    if (campaignId && url === originalUrl) {
      // URL hasn't changed, just navigate to Product Info
      navigate('/video-ads-v2/product-info', { 
        state: { 
          campaignId
        } 
      });
      return;
    }

    // URL has changed or it's a new analysis
    setError('');
    setIsAnalyzing(true);
    setProgress(0);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 500);

      const extractedData = await parseURL(url);
      
      clearInterval(progressInterval);
      setProgress(100);

      // Navigate to product info page with extracted data
      setTimeout(() => {
        navigate('/video-ads-v2/product-info', { 
          state: { 
            campaignId: extractedData.campaign_id,
            extractedData,
            isNewCampaign: true
          } 
        });
      }, 500);

    } catch (error) {
      console.error('Analysis failed:', error);
      setError('Failed to analyze the URL. Please check the URL and try again, or use manual entry instead.');
      setIsAnalyzing(false);
      setProgress(0);
    }
  };

  const handleUploadManually = () => {
    // Clear any existing V2 state to ensure fresh start
    localStorage.removeItem('videoAdsV2State');
    
    navigate('/video-ads-v2/product-info', { 
      state: { 
        isNewCampaign: true,
        isManualEntry: true
      } 
    });
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Box textAlign="center" mb={4}>
          <AnalyticsIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            Create Video Ad 2.0
          </Typography>
          <Typography variant="h6" color="text.secondary" paragraph>
            Experience next-generation video ad creation. Analyze any product URL or enter information manually.
          </Typography>
        </Box>

        <Card elevation={3} sx={{ mb: 3 }}>
          <CardContent sx={{ p: 4 }}>
            <Box mb={3}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LinkIcon color="primary" />
                Product URL Analysis
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={2}>
                Paste your product page, landing page, or website URL below
              </Typography>
              
              {campaignId && url && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Campaign URL loaded:</strong> This URL was used in your previous campaign. 
                    You can analyze it again or continue to Product Info.
                  </Typography>
                </Alert>
              )}
              
              <TextField
                fullWidth
                variant="outlined"
                placeholder="https://yourproduct.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isAnalyzing}
                sx={{ mb: 2 }}
                helperText={campaignId ? "URL from your campaign. You can modify it or continue." : "Enter the full URL including https://"}
              />

              {!isAuthenticated && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    <strong>Authentication Required:</strong> Please log in to use the URL analysis feature. 
                    You can still create video ads manually by clicking "Upload Manually" below.
                  </Typography>
                </Alert>
              )}

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              {isAnalyzing && (
                <Box sx={{ mb: 2 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body2" color="text.secondary">
                      Analyzing your product page...
                    </Typography>
                    <Typography variant="body2" color="primary">
                      {Math.round(progress)}%
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={progress} 
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Extracting product information, target audience, and key features...
                  </Typography>
                </Box>
              )}

              <Button
                variant="contained"
                size="large"
                onClick={handleAnalyzeURL}
                disabled={isAnalyzing || !url.trim()}
                startIcon={<AnalyticsIcon />}
                fullWidth
                sx={{ py: 1.5, fontSize: '1.1rem' }}
              >
                {isAnalyzing ? 'Analyzing URL...' : (campaignId && url === originalUrl ? 'Continue to Product Info' : 'Analyze URL')}
              </Button>
            </Box>

            <Divider sx={{ my: 3 }}>
              <Typography variant="body2" color="text.secondary">
                OR
              </Typography>
            </Divider>

            <Box textAlign="center">
              <Typography variant="h6" gutterBottom color="text.secondary">
                Don't have a product page?
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={2}>
                No problem! You can manually enter your product information instead.
              </Typography>
              
              <Button
                variant="outlined"
                size="large"
                onClick={handleUploadManually}
                startIcon={<UploadIcon />}
                disabled={isAnalyzing}
                sx={{ py: 1.5, px: 4, fontSize: '1.1rem' }}
              >
                Upload Manually
              </Button>
            </Box>
          </CardContent>
        </Card>

        <Box textAlign="center">
          <Typography variant="caption" color="text.secondary">
            Your data is secure and will only be used to generate your marketing content.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default ImportFromURLV2;
