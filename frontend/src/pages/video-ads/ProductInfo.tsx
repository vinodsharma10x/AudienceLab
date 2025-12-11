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
  StepLabel
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
  Add as AddIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

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
  isFromURL?: boolean;
  isFromMarketingAngles?: boolean;
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
  const { extractedData, isFromURL, isFromMarketingAngles } = (location.state as LocationState) || {};

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
  const [errors, setErrors] = useState<FormErrors>({});

  useEffect(() => {
    if (extractedData) {
      // If coming from marketing angles, populate immediately without loading state
      if (isFromMarketingAngles) {
        setFormData({
          product_name: extractedData.product_name || '',
          product_information: extractedData.product_information || '',
          target_audience: extractedData.target_audience || '',
          price: extractedData.price || '',
          problem_solved: extractedData.problem_solved || '',
          differentiation: extractedData.differentiation || '',
          additional_information: extractedData.additional_information || ''
        });
      } else {
        // If coming from URL extraction, show loading state
        setIsLoading(true);
        setTimeout(() => {
          setFormData({
            product_name: extractedData.product_name || '',
            product_information: extractedData.product_information || '',
            target_audience: extractedData.target_audience || '',
            price: extractedData.price || '',
            problem_solved: extractedData.problem_solved || '',
            differentiation: extractedData.differentiation || '',
            additional_information: extractedData.additional_information || ''
          });
          setIsLoading(false);
        }, 1000);
      }
    }
  }, [extractedData, isFromMarketingAngles]);

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
    navigate('/video-ads/import-from-url');
  };

  const handleNext = () => {
    if (validateForm()) {
      // Navigate to video ads workflow with the product data
      console.log('Form data to be sent:', formData);
      
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
      
      navigate('/video-ads/marketing-angles', { 
        state: { 
          productInfo: productInfo,
          isFromURL: isFromURL 
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
    if (isLoading && isFromURL && !isFromMarketingAngles) {
      return (
        <Box key={field} sx={{ mb: 3 }}>
          <Box display="flex" alignItems="center" gap={1} mb={1}>
            <Box sx={{ color: 'primary.main' }}>
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
                bgcolor: 'rgba(0,0,0,0.04)',
                '&::after': {
                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent)'
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
              <Typography variant="caption">Extracting {label.toLowerCase()}...</Typography>
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
              color: 'primary.main',
              p: 1,
              borderRadius: '50%',
              background: 'rgba(25, 118, 210, 0.1)',
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
                  border: 'none'
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
              <StepLabel>Import URL</StepLabel>
            </Step>
            <Step>
              <StepLabel>Product Info</StepLabel>
            </Step>
            <Step>
              <StepLabel>Marketing Angles</StepLabel>
            </Step>
            <Step>
              <StepLabel>Generate Video</StepLabel>
            </Step>
          </Stepper>
        </Box>

        <Box mb={4}>
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            {isFromMarketingAngles && (
              <Chip 
                icon={<ArrowBackIcon />} 
                label="Returned from Marketing Angles" 
                color="info" 
                variant="outlined" 
                size="small"
              />
            )}
            {isFromURL && !isFromMarketingAngles && (
              <Chip 
                icon={<LinkIcon />} 
                label="Extracted from URL" 
                color="primary" 
                variant="outlined" 
                size="small"
              />
            )}
            {!isFromURL && !isFromMarketingAngles && (
              <Chip 
                icon={<EditIcon />} 
                label="Manual Entry" 
                color="secondary" 
                variant="outlined" 
                size="small"
              />
            )}
          </Box>
          
          <Typography variant="h3" component="h1" gutterBottom color="primary" fontWeight="bold">
            {isFromURL ? 'Review Extracted Information' : 'Enter Product Information'}
          </Typography>
          
          <Typography variant="h6" color="text.secondary">
            {isFromURL 
              ? 'Review and edit the extracted information below. Fields marked with * are required.'
              : 'Please provide detailed information about your product. Fields marked with * are required.'
            }
          </Typography>
        </Box>

        {isFromURL && extractedData && !isFromMarketingAngles && isLoading && (
          <Box sx={{ mb: 3 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              Extracting and organizing product information from URL...
            </Alert>
            <LinearProgress 
              sx={{ 
                height: 8, 
                borderRadius: 4,
                '& .MuiLinearProgress-bar': {
                  background: 'linear-gradient(90deg, #667eea, #764ba2)'
                }
              }} 
            />
          </Box>
        )}

        {isFromURL && extractedData && !isFromMarketingAngles && !isLoading && (
          <Alert severity="success" sx={{ mb: 3 }} icon={<CheckCircleIcon />}>
            Successfully extracted product information from: {extractedData.original_url}
          </Alert>
        )}

        {isFromMarketingAngles && (
          <Alert severity="info" sx={{ mb: 3 }} icon={<ArrowBackIcon />}>
            Your previously entered information has been restored. Make any changes needed and continue again.
          </Alert>
        )}

        <Card 
          elevation={4}
          sx={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
              backgroundColor: 'rgba(25, 118, 210, 0.08)',
              color: 'primary.main',
              '&:hover': {
                backgroundColor: 'rgba(25, 118, 210, 0.12)',
                border: 'none'
              }
            }}
          >
            Back
          </Button>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
              Step 2 of 6
            </Typography>
            <Button
              variant="contained"
              size="large"
              endIcon={<ArrowForwardIcon />}
              onClick={handleNext}
              disabled={isLoading}
              sx={{ 
                px: 4, 
                py: 1.5, 
                fontSize: '1.1rem',
                borderRadius: 3,
                background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                boxShadow: '0 3px 15px rgba(102, 126, 234, 0.4)',
                '&:hover': {
                  background: 'linear-gradient(45deg, #5a6fd8 30%, #6a4190 90%)',
                  boxShadow: '0 6px 20px rgba(102, 126, 234, 0.6)',
                }
              }}
            >
              {isLoading ? 'Loading...' : 'Continue to Marketing Angles'}
            </Button>
          </Box>
        </Box>

        <Box textAlign="center" mt={3}>
          <Typography variant="caption" color="text.secondary">
            This information will be used to generate personalized video ad content for your product.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default ProductInfo;
