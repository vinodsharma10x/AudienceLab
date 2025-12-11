import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  TextField, 
  Button, 
  Card, 
  CardContent,
  Grid,
  Alert,
  Chip,
  Skeleton,
  Container,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  CircularProgress
} from '@mui/material';
import { 
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  Edit as EditIcon,
  Link as LinkIcon,
  CheckCircle as CheckCircleIcon,
  BusinessCenter as BusinessCenterIcon,
  Info as InfoIcon,
  Group as GroupIcon,
  AttachMoney as AttachMoneyIcon,
  ReportProblem as ProblemIcon,
  Star as StarIcon,
  Add as AddIcon,
  Psychology as PsychologyIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';
import DocumentUpload from '../../components/DocumentUpload';

interface ExtractedData {
  product_name?: string;
  product_information?: string;
  target_audience?: string;
  price?: string;
  problem_solved?: string;
  differentiation?: string;
  additional_information?: string;
  original_url?: string;
}

interface LocationState {
  extractedData?: ExtractedData;
  campaignId?: string;
  isNewCampaign?: boolean;
  isManualEntry?: boolean;
}

interface FormData {
  product_name: string;
  product_information: string;
  target_audience: string;
  price: string;
  problem_solved: string;
  differentiation: string;
  additional_information: string;
}

interface FormErrors {
  [key: string]: string;
}

interface ProductInfo {
  product_name: string;
  product_information: string;
  target_audience: string;
  price: string;
  problem_solved: string;
  differentiation: string;
  additional_information: string;
}

const ProductInfo: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { session } = useAuth();
  const locationState = (location.state as LocationState) || {};
  const { extractedData, campaignId: stateCampaignId, isNewCampaign, isManualEntry } = locationState;

  // Use existing campaignId or generate a temporary one for document uploads
  const campaignId = stateCampaignId || `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const [formData, setFormData] = useState<FormData>({
    product_name: '',
    product_information: '',
    target_audience: '',
    price: '',
    problem_solved: '',
    differentiation: '',
    additional_information: ''
  });

  const [isLoading, setIsLoading] = useState(false);
  const [loadingFromDB, setLoadingFromDB] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [originalFormData, setOriginalFormData] = useState<FormData | null>(null);
  const [hasChanges, setHasChanges] = useState<boolean | undefined>(undefined);
  const [uploadedDocuments, setUploadedDocuments] = useState<any[]>([]);

  // Load data from database if we have a campaignId and no extracted data
  useEffect(() => {
    const loadProductInfo = async () => {
      if (stateCampaignId && !extractedData && !isNewCampaign) {
        setLoadingFromDB(true);
        try {
          const token = getValidToken(session);
          const response = await fetch(
            `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/${stateCampaignId}/product-info`,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            }
          );

          if (response.ok) {
            const data = await response.json();
            setFormData({
              product_name: data.product_name || '',
              product_information: data.product_information || '',
              target_audience: data.target_audience || '',
              price: data.price || '',
              problem_solved: data.problem_solved || '',
              differentiation: data.differentiation || '',
              additional_information: data.additional_information || ''
            });
            // Store original data for change detection
            setOriginalFormData({
              product_name: data.product_name || '',
              product_information: data.product_information || '',
              target_audience: data.target_audience || '',
              price: data.price || '',
              problem_solved: data.problem_solved || '',
              differentiation: data.differentiation || '',
              additional_information: data.additional_information || ''
            });
          }
        } catch (error) {
          console.error('Error loading product info:', error);
        } finally {
          setLoadingFromDB(false);
        }
      } else if (extractedData) {
        // Original logic for data from URL extraction
        if (!isNewCampaign && stateCampaignId) {
          const data = {
            product_name: extractedData.product_name || '',
            product_information: extractedData.product_information || '',
            target_audience: extractedData.target_audience || '',
            price: extractedData.price || '',
            problem_solved: extractedData.problem_solved || '',
            differentiation: extractedData.differentiation || '',
            additional_information: extractedData.additional_information || ''
          };
          setFormData(data);
          // Set original data for change detection when coming back
          setOriginalFormData(data);
        } else {
          // If coming from URL extraction, show loading state
          setIsLoading(true);
          setTimeout(() => {
            const data = {
              product_name: extractedData.product_name || '',
              product_information: extractedData.product_information || '',
              target_audience: extractedData.target_audience || '',
              price: extractedData.price || '',
              problem_solved: extractedData.problem_solved || '',
              differentiation: extractedData.differentiation || '',
              additional_information: extractedData.additional_information || ''
            };
            setFormData(data);
            // Set original data for initial load too
            setOriginalFormData(data);
            setIsLoading(false);
          }, 1000);
        }
      }
    };

    loadProductInfo();
  }, [extractedData, stateCampaignId, isNewCampaign, session]);

  // Check if form data has changed
  useEffect(() => {
    if (originalFormData) {
      const changed = Object.keys(formData).some(key => 
        formData[key as keyof FormData] !== originalFormData[key as keyof FormData]
      );
      setHasChanges(changed);
    } else {
      // If no original data yet, hasChanges should be undefined
      setHasChanges(undefined);
    }
  }, [formData, originalFormData]);

  const handleInputChange = (field: keyof FormData) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};
    
    if (!formData.product_name.trim()) {
      newErrors.product_name = 'Product name is required';
    }
    
    if (!formData.product_information.trim()) {
      newErrors.product_information = 'Product information is required';
    }
    
    if (!formData.target_audience.trim()) {
      newErrors.target_audience = 'Target audience is required';
    }
    
    if (!formData.problem_solved.trim()) {
      newErrors.problem_solved = 'Problem solved is required';
    }
    
    if (!formData.differentiation.trim()) {
      newErrors.differentiation = 'Differentiation is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleBack = () => {
    navigate('/video-ads-v2/import-from-url', {
      state: { campaignId }
    });
  };

  const handleNext = () => {
    if (validateForm()) {
      // Convert formData to the format expected by the workflow
      const productInfo: ProductInfo = {
        product_name: formData.product_name,
        product_information: formData.product_information,
        target_audience: formData.target_audience,
        price: formData.price,
        problem_solved: formData.problem_solved,
        differentiation: formData.differentiation,
        additional_information: formData.additional_information
      };
      
      // Extract S3 URLs from uploaded documents
      const documentUrls = uploadedDocuments
        .filter(doc => doc.s3_url && doc.upload_status === 'completed')
        .map(doc => doc.s3_url);

      // Only pass productInfo if it's new or changed
      navigate('/video-ads-v2/marketing-angles', {
        state: {
          campaignId,
          productInfo: (isNewCampaign || hasChanges) ? productInfo : undefined,
          forceGenerate: hasChanges,
          documentUrls: documentUrls.length > 0 ? documentUrls : undefined
        }
      });
    }
  };

  const getFieldIcon = (field: keyof FormData) => {
    switch (field) {
      case 'product_name': return <BusinessCenterIcon />;
      case 'product_information': return <InfoIcon />;
      case 'target_audience': return <GroupIcon />;
      case 'price': return <AttachMoneyIcon />;
      case 'problem_solved': return <ProblemIcon />;
      case 'differentiation': return <StarIcon />;
      case 'additional_information': return <AddIcon />;
      default: return <InfoIcon />;
    }
  };

  const renderField = (
    field: keyof FormData, 
    label: string, 
    multiline: boolean = false, 
    required: boolean = true, 
    placeholder: string = ''
  ) => {
    if (isLoading && extractedData) {
      return (
        <Box key={field} sx={{ mb: 3 }}>
          <Box display="flex" alignItems="center" gap={1} mb={1}>
            <Box sx={{ color: 'purple.main' }}>
              {getFieldIcon(field)}
            </Box>
            <Typography variant="subtitle1" fontWeight="600">
              {label} {required && <span style={{ color: '#d32f2f' }}>*</span>}
            </Typography>
          </Box>
          <Box sx={{ position: 'relative' }}>
            <Skeleton 
              variant="rectangular" 
              height={multiline ? 100 : 56} 
              sx={{ 
                borderRadius: 3,
                bgcolor: 'rgba(156,39,176,0.04)',
                '&::after': {
                  background: 'linear-gradient(90deg, transparent, rgba(156,39,176,0.8), transparent)'
                }
              }} 
            />
            <Box
              sx={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                color: 'text.secondary'
              }}
            >
              <PsychologyIcon sx={{ fontSize: 16 }} />
              <Typography variant="caption">AI extracting {label.toLowerCase()}...</Typography>
            </Box>
          </Box>
        </Box>
      );
    }

    return (
      <Box key={field} sx={{ mb: 3 }}>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <Box 
            sx={{ 
              color: 'purple.main',
              p: 1,
              borderRadius: '50%',
              background: 'rgba(156, 39, 176, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {getFieldIcon(field)}
          </Box>
          <Typography variant="subtitle1" fontWeight="600" sx={{ color: 'text.primary' }}>
            {label} {required && <span style={{ color: '#d32f2f' }}>*</span>}
          </Typography>
        </Box>
        <TextField
          fullWidth
          multiline={multiline}
          rows={multiline ? 3 : 1}
          variant="outlined"
          value={formData[field]}
          onChange={handleInputChange(field)}
          error={!!errors[field]}
          helperText={errors[field]}
          placeholder={placeholder}
          sx={{ 
            '& .MuiOutlinedInput-root': {
              borderRadius: 3,
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px)',
              transition: 'all 0.3s ease-in-out',
              '& .MuiOutlinedInput-notchedOutline': {
                border: 'none'
              },
              '&:hover': {
                background: 'rgba(255, 255, 255, 0.9)',
                '& .MuiOutlinedInput-notchedOutline': {
                  border: 'none'
                }
              },
              '&.Mui-focused': {
                background: 'white',
                '& .MuiOutlinedInput-notchedOutline': {
                  border: '2px solid #9c27b0'
                }
              },
              '&.Mui-error': {
                '& .MuiOutlinedInput-notchedOutline': {
                  border: '2px solid #d32f2f'
                }
              }
            },
            '& .MuiInputBase-input': {
              fontSize: '1rem',
              lineHeight: 1.5
            }
          }}
        />
      </Box>
    );
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Progress Stepper */}
        <Box sx={{ mb: 4 }}>
          <Stepper activeStep={1} alternativeLabel>
            <Step>
              <StepLabel>Import URL 2.0</StepLabel>
            </Step>
            <Step>
              <StepLabel>Product Info 2.0</StepLabel>
            </Step>
            <Step>
              <StepLabel>Analysis</StepLabel>
            </Step>
            <Step>
              <StepLabel>Generate Video 2.0</StepLabel>
            </Step>
          </Stepper>
        </Box>

        <Box mb={4}>
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            {!isNewCampaign && stateCampaignId && (
              <Chip 
                icon={<ArrowBackIcon />} 
                label="Returned from Analysis" 
                color="secondary" 
                variant="outlined" 
                size="small"
              />
            )}
            {extractedData && (
              <Chip 
                icon={<LinkIcon />} 
                label="Extracted with AI" 
                sx={{ 
                  color: 'purple.main',
                  borderColor: 'purple.main',
                  '& .MuiChip-icon': { color: 'purple.main' }
                }}
                variant="outlined" 
                size="small"
              />
            )}
            {isManualEntry && (
              <Chip 
                icon={<EditIcon />} 
                label="Manual Entry" 
                color="secondary" 
                variant="outlined" 
                size="small"
              />
            )}
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <PsychologyIcon sx={{ fontSize: 32, color: 'purple.main' }} />
            <Typography variant="h3" component="h1" gutterBottom sx={{ 
              background: 'linear-gradient(45deg, #9c27b0, #1976d2)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              color: 'transparent',
              fontWeight: 'bold'
            }}>
              Product Information 2.0
            </Typography>
          </Box>
          
          <Typography variant="h6" color="text.secondary">
            {extractedData 
              ? 'AI has analyzed your content. Review and enhance the extracted information below for optimal results.'
              : 'Provide detailed product information to generate enhanced marketing content. Fields marked with * are required.'
            }
          </Typography>
        </Box>

        {extractedData && isLoading && (
          <Box sx={{ mb: 3 }}>
            <Alert severity="info" sx={{ mb: 2, border: '1px solid', borderColor: 'purple.200' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <PsychologyIcon sx={{ color: 'purple.main' }} />
                <Typography>AI is analyzing and organizing your product information...</Typography>
              </Box>
            </Alert>
            <LinearProgress 
              sx={{ 
                height: 8, 
                borderRadius: 4,
                '& .MuiLinearProgress-bar': {
                  background: 'linear-gradient(90deg, #9c27b0, #1976d2)'
                }
              }} 
            />
          </Box>
        )}

        {extractedData && !isLoading && isNewCampaign && (
          <Alert severity="success" sx={{ mb: 3, border: '1px solid', borderColor: 'purple.200' }} icon={<CheckCircleIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <PsychologyIcon sx={{ color: 'purple.main' }} />
              <Box>
                <Typography fontWeight="bold">AI Analysis Complete!</Typography>
                <Typography variant="body2">Successfully extracted product information from: {extractedData.original_url}</Typography>
              </Box>
            </Box>
          </Alert>
        )}

        {(!isNewCampaign && stateCampaignId) && (
          <Alert severity="info" sx={{ mb: 3, border: '1px solid', borderColor: 'purple.200' }} icon={<ArrowBackIcon />}>
            Your previously entered information has been restored. Make any changes needed and continue with the enhanced analysis.
          </Alert>
        )}

        <Card 
          elevation={4}
          sx={{ 
            background: 'linear-gradient(135deg, #9c27b0 0%, #1976d2 100%)',
            borderRadius: 4,
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ 
              background: 'white', 
              borderRadius: 3, 
              p: 4,
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
              backdropFilter: 'blur(10px)',
              animation: isLoading ? 'none' : 'fadeIn 0.6s ease-in-out',
              '@keyframes fadeIn': {
                '0%': {
                  opacity: 0,
                  transform: 'translateY(20px)'
                },
                '100%': {
                  opacity: 1,
                  transform: 'translateY(0)'
                }
              }
            }}>
              {renderField('product_name', 'Product Name', false, true, 'e.g., Acme CRM Pro')}
              
              {renderField('product_information', 'Product Information', true, true, 
                'Describe what your product does, its main features, and how it works...')}
              
              {renderField('target_audience', 'Target Audience', true, true, 
                'Who is your ideal customer? (e.g., Small business owners, Marketing professionals...)')}
              
              {renderField('price', 'Price', false, false, 
                'e.g., $99/month, $499 one-time, Free with premium options')}
              
              {renderField('problem_solved', 'Problem Solved', true, true, 
                'What main problem or pain point does your product solve for customers?')}
              
              {renderField('differentiation', 'Differentiation', true, true, 
                'What makes your product unique compared to competitors? What are your key advantages?')}
              
              {renderField('additional_information', 'Additional Information', true, false,
                'Any other relevant details, features, benefits, or selling points...')}

              {/* Document Upload Section */}
              <DocumentUpload
                campaignId={campaignId}
                onDocumentsChange={(docs) => setUploadedDocuments(docs)}
              />
            </Box>
          </CardContent>
        </Card>

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
              backgroundColor: 'rgba(156, 39, 176, 0.08)',
              color: 'purple.main',
              '&:hover': {
                backgroundColor: 'rgba(156, 39, 176, 0.12)',
                border: 'none'
              }
            }}
          >
            Back
          </Button>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
              Step 2 of 6 • Create Video Ad 2.0
            </Typography>
            <Button
              variant="contained"
              size="large"
              endIcon={<PsychologyIcon />}
              onClick={handleNext}
              disabled={isLoading}
              sx={{ 
                px: 4, 
                py: 1.5, 
                fontSize: '1.1rem',
                borderRadius: 3,
                background: 'linear-gradient(45deg, #9c27b0 30%, #1976d2 90%)',
                boxShadow: '0 3px 15px rgba(156, 39, 176, 0.4)',
                '&:hover': {
                  background: 'linear-gradient(45deg, #8e24aa 30%, #1565c0 90%)',
                  boxShadow: '0 6px 20px rgba(156, 39, 176, 0.6)',
                }
              }}
            >
              {isLoading ? 'Loading...' : 'Continue to Analysis'}
            </Button>
          </Box>
        </Box>

        <Box textAlign="center" mt={3}>
          <Typography variant="caption" color="text.secondary">
            This information will be processed by AI to generate enhanced, context-aware video ad content for your product.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default ProductInfo;
