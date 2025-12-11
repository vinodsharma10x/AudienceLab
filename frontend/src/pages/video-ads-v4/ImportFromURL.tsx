import React, { useState } from 'react';
import {
  Container,
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Stack,
} from '@mui/material';
import {
  Link as LinkIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const ImportFromURL: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useAuth();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url) {
      setError('Please enter a URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = session?.access_token;
      if (!token) {
        throw new Error('No authentication token');
      }

      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v4/parse-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to parse URL');
      }

      const data = await response.json();

      // Extract product info from response (fields are at root level)
      const productInfo = {
        product_name: data.product_name,
        product_information: data.product_information,
        target_audience: data.target_audience,
        price: data.price,
        problem_solved: data.problem_solved,
        differentiation: data.differentiation,
        additional_information: data.additional_information,
        product_url: data.original_url
      };

      // Navigate to product info page with campaign ID
      navigate(`/video-ads-v4/product-info/${data.campaign_id}`, {
        state: { productInfo }
      });

    } catch (err: any) {
      console.error('Error parsing URL:', err);
      setError(err.message || 'Failed to parse URL');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ mb: 1 }}>
          New Product Research
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Enter your product URL to automatically extract product information and start the research process
        </Typography>

        <Paper sx={{ p: 4 }}>
          <form onSubmit={handleSubmit}>
            <Stack spacing={3}>
              <TextField
                fullWidth
                label="Product URL"
                placeholder="https://example.com/product"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={loading}
                InputProps={{
                  startAdornment: <LinkIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                }}
                helperText="Enter the URL of your product page"
              />

              {error && (
                <Alert severity="error" onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={loading || !url}
                  endIcon={loading ? <CircularProgress size={20} /> : <ArrowForwardIcon />}
                >
                  {loading ? 'Parsing URL...' : 'Parse URL'}
                </Button>
              </Box>
            </Stack>
          </form>
        </Paper>
      </Box>
    </Container>
  );
};

export default ImportFromURL;