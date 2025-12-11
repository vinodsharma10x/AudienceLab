import React, { useState, useEffect } from 'react';
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
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  Save as SaveIcon,
  ArrowForward as ArrowForwardIcon,
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface ProductData {
  product_name: string;
  product_information: string;
  target_audience: string;
  price: string;
  problem_solved: string;
  differentiation: string;
  additional_information: string;
  product_url?: string;
}

const ProductInfo: React.FC = () => {
  const navigate = useNavigate();
  const { campaignId } = useParams();
  const location = useLocation();
  const { session } = useAuth();

  const [productData, setProductData] = useState<ProductData>({
    product_name: '',
    product_information: '',
    target_audience: '',
    price: 'Not specified',
    problem_solved: '',
    differentiation: '',
    additional_information: '',
    product_url: '',
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    // Load product info from navigation state
    if (location.state?.productInfo) {
      setProductData(location.state.productInfo);
    }
  }, [location]);

  const handleChange = (field: keyof ProductData) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setProductData(prev => ({
      ...prev,
      [field]: event.target.value,
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const token = session?.access_token;
      if (!token) {
        throw new Error('No authentication token');
      }

      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v4/product-info`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          campaign_id: campaignId,
          product_data: productData,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save product info');
      }

      setSuccess('Product information saved successfully');
    } catch (err: any) {
      console.error('Error saving product info:', err);
      setError(err.message || 'Failed to save product info');
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateResearch = async () => {
    // Save product info first
    await handleSave();

    if (!error) {
      // Navigate to marketing research page
      navigate(`/video-ads-v4/research/${campaignId}`);
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Breadcrumbs sx={{ mb: 3 }}>
          <Link
            color="inherit"
            href="#"
            onClick={() => navigate('/video-ads-v4/import')}
            sx={{ cursor: 'pointer' }}
          >
            Import URL
          </Link>
          <Typography color="text.primary">Product Information</Typography>
        </Breadcrumbs>

        <Typography variant="h4" gutterBottom sx={{ mb: 1 }}>
          New Product Research
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Review and edit the extracted product information before starting the research
        </Typography>

        <Paper sx={{ p: 4 }}>
          <Stack spacing={3}>
            <TextField
              fullWidth
              label="Product Name"
              value={productData.product_name}
              onChange={handleChange('product_name')}
              required
            />

            <TextField
              fullWidth
              multiline
              rows={4}
              label="Product Description"
              value={productData.product_information}
              onChange={handleChange('product_information')}
              required
              helperText="Detailed description of what the product does"
            />

            <TextField
              fullWidth
              multiline
              rows={2}
              label="Target Audience"
              value={productData.target_audience}
              onChange={handleChange('target_audience')}
              required
              helperText="Who is this product for?"
            />

            <TextField
              fullWidth
              label="Price"
              value={productData.price}
              onChange={handleChange('price')}
              helperText="Product price (if applicable)"
            />

            <TextField
              fullWidth
              multiline
              rows={3}
              label="Problem Solved"
              value={productData.problem_solved}
              onChange={handleChange('problem_solved')}
              required
              helperText="What problem or pain point does this product solve?"
            />

            <TextField
              fullWidth
              multiline
              rows={3}
              label="Differentiation"
              value={productData.differentiation}
              onChange={handleChange('differentiation')}
              required
              helperText="What makes this product unique compared to competitors?"
            />

            <TextField
              fullWidth
              multiline
              rows={3}
              label="Additional Information"
              value={productData.additional_information}
              onChange={handleChange('additional_information')}
              helperText="Any other relevant details"
            />

            {productData.product_url && (
              <TextField
                fullWidth
                label="Product URL"
                value={productData.product_url}
                disabled
                helperText="Source URL"
              />
            )}

            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" onClose={() => setSuccess(null)}>
                {success}
              </Alert>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mt: 3 }}>
              <Button
                variant="outlined"
                size="large"
                startIcon={<ArrowBackIcon />}
                onClick={() => navigate('/video-ads-v4/import')}
              >
                Back
              </Button>

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save'}
                </Button>

                <Button
                  variant="contained"
                  size="large"
                  endIcon={loading ? <CircularProgress size={20} /> : <ArrowForwardIcon />}
                  onClick={handleGenerateResearch}
                  disabled={loading || saving}
                >
                  {loading ? 'Processing...' : 'Generate Marketing Research'}
                </Button>
              </Box>
            </Box>
          </Stack>
        </Paper>

        <Box sx={{ mt: 4, p: 3, bgcolor: 'background.paper', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom color="primary">
            Next Step: AI Research Generation
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Click "Generate Marketing Research" to start the AI analysis process.<br />
            <br />
            Your comprehensive research will include:<br />
            • Target audience analysis<br />
            • Customer journey mapping<br />
            • Marketing angles and hooks<br />
            • Ad scripts ready to use<br />
            <br />
            <strong>Processing time: 10-20 minutes</strong><br />
            Once complete, your research will be available in the "Existing Research" page.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default ProductInfo;