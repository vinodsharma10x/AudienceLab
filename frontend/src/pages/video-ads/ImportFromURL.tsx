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
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

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
}

const ImportFromURL: React.FC = () => {
  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const { user, session } = useAuth();
  const navigate = useNavigate();

  const isAuthenticated = !!user;

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

      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads/parse-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
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

    // Basic URL validation
    try {
      new URL(url);
    } catch {
      setError('Please enter a valid URL (e.g., https://example.com)');
      return;
    }

    setError('');
    setIsAnalyzing(true);
    setProgress(0);

    // Progress animation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 85) {
          clearInterval(progressInterval);
          return 85;
        }
        return prev + Math.random() * 10 + 2;
      });
    }, 500);

    // Timeout
    const timeoutId = setTimeout(() => {
      setError('URL analysis is taking too long. Please try a different URL or use manual upload.');
      setIsAnalyzing(false);
      setProgress(0);
      clearInterval(progressInterval);
    }, 35000);

    try {
      console.log('Calling URL parsing API for:', url);
      const extractedData = await parseURL(url);
      console.log('Extracted data:', extractedData);
      
      clearTimeout(timeoutId);
      clearInterval(progressInterval);
      setProgress(100);
      
      // Navigate to product info page with extracted information
      setTimeout(() => {
        navigate('/video-ads/product-info', { 
          state: { 
            extractedData: {
              product_name: extractedData.product_name || '',
              product_information: extractedData.product_information || extractedData.additional_info || '',
              target_audience: extractedData.target_audience || '',
              price: extractedData.price || '',
              problem_solved: extractedData.problem_solved || '',
              differentiation: extractedData.unique_selling_points?.join(', ') || '',
              additional_information: extractedData.key_benefits?.join(', ') || '',
              original_url: url
            },
            isFromURL: true 
          } 
        });
      }, 500);

    } catch (err: any) {
      console.error('URL parsing error:', err);
      
      clearTimeout(timeoutId);
      clearInterval(progressInterval);
      
      let errorMessage = 'Failed to analyze the URL. Please try again or use manual upload.';
      
      if (err.message?.includes('timeout')) {
        errorMessage = 'URL analysis timed out. The webpage might be too slow to load. Please try a different URL or use manual upload.';
      } else if (err.message?.includes('401')) {
        errorMessage = 'Please log in to use the URL analysis feature.';
      } else if (err.message?.includes('400')) {
        errorMessage = 'Invalid URL or failed to fetch the webpage.';
      }
      
      setError(errorMessage);
      setIsAnalyzing(false);
      setProgress(0);
    }
  };

  const handleUploadManually = () => {
    navigate('/video-ads/product-info', { 
      state: { 
        isFromURL: false 
      } 
    });
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Box textAlign="center" mb={4}>
          <AnalyticsIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            Share your product link to generate video ads
          </Typography>
          <Typography variant="h6" color="text.secondary" paragraph>
            Enter your product or landing page URL and we'll automatically extract all the information needed to create compelling video ads.
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
              
              <TextField
                fullWidth
                variant="outlined"
                placeholder="https://yourproduct.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isAnalyzing}
                sx={{ mb: 2 }}
                helperText="Enter the full URL including https://"
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
                disabled={isAnalyzing || !url.trim() || !isAuthenticated}
                startIcon={<AnalyticsIcon />}
                fullWidth
                sx={{ py: 1.5, fontSize: '1.1rem' }}
              >
                {!isAuthenticated ? 'Login Required for URL Analysis' : 
                 isAnalyzing ? 'Analyzing...' : 'Analyze URL'}
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

export default ImportFromURL;
