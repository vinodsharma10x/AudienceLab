import React, { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Container,
  Tab,
  Tabs,
  Alert,
  InputAdornment,
  IconButton,
  Divider,
  Card,
  CardContent,
  useTheme,
  alpha,
  CircularProgress,
} from '@mui/material';
import {
  Email,
  Lock,
  Visibility,
  VisibilityOff,
  Google,
  CheckCircle,
  ArrowBack,
  Person,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function CustomTabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

// Image Carousel Component (reused from LoginPage)
const ImageCarousel: React.FC = () => {
  const [currentIndex, setCurrentIndex] = useState(0);

  const carouselData = [
    {
      image: 'https://images.unsplash.com/photo-1551434678-e076c223a692?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80',
      tagline: 'Create Stunning Video Ads',
      subtitle: 'Transform your marketing with AI-powered video content that converts'
    },
    {
      image: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2015&q=80',
      tagline: 'AI-Powered Marketing',
      subtitle: 'Leverage cutting-edge AI to create compelling advertisements in minutes'
    },
    {
      image: 'https://images.unsplash.com/photo-1553484771-371a605b060b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80',
      tagline: 'Scale Your Business',
      subtitle: 'Reach more customers with personalized video content at scale'
    }
  ];

  React.useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prevIndex) => (prevIndex + 1) % carouselData.length);
    }, 5000);

    return () => clearInterval(timer);
  }, [carouselData.length]);

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {carouselData.map((item, index) => (
        <Box
          key={index}
          sx={{
            position: 'absolute',
            inset: 0,
            opacity: index === currentIndex ? 1 : 0,
            transition: 'opacity 1s ease-in-out',
          }}
        >
          <Box
            component="img"
            src={item.image}
            alt={item.tagline}
            sx={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
          <Box
            sx={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(to top, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.2) 50%, transparent 100%)',
            }}
          />
          
          {/* Content Overlay */}
          <Box
            sx={{
              position: 'absolute',
              bottom: 64,
              left: 48,
              right: 48,
              color: 'white',
            }}
          >
            <Typography variant="h3" component="h2" sx={{ mb: 2, fontWeight: 'bold' }}>
              {item.tagline}
            </Typography>
            <Typography variant="h6" sx={{ opacity: 0.9, maxWidth: '400px' }}>
              {item.subtitle}
            </Typography>
          </Box>
        </Box>
      ))}
      
      {/* Dots Indicator */}
      <Box
        sx={{
          position: 'absolute',
          bottom: 32,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 1,
        }}
      >
        {carouselData.map((_, index) => (
          <Box
            key={index}
            component="button"
            onClick={() => setCurrentIndex(index)}
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              border: 'none',
              bgcolor: index === currentIndex ? 'white' : 'rgba(255,255,255,0.4)',
              cursor: 'pointer',
              transition: 'all 0.3s',
            }}
          />
        ))}
      </Box>
    </Box>
  );
};

// Magic Link Signup Form Component
const MagicLinkSignUpForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState('');
  const { signInWithMagicLink } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await signInWithMagicLink(email);
      if (error) {
        setError(error.message || 'Failed to send magic link');
      } else {
        setIsSuccess(true);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send magic link');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Box
          sx={{
            mx: 'auto',
            width: 64,
            height: 64,
            bgcolor: 'success.light',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 3,
          }}
        >
          <CheckCircle sx={{ fontSize: 32, color: 'success.main' }} />
        </Box>
        <Typography variant="h6" gutterBottom>
          Check your email
        </Typography>
        <Typography color="text.secondary" paragraph>
          We've sent a magic link to <strong>{email}</strong>
        </Typography>
        <Typography color="text.secondary" paragraph>
          Click the link to create your account and sign in.
        </Typography>
        <Button
          variant="text"
          startIcon={<ArrowBack />}
          onClick={() => {
            setIsSuccess(false);
            setEmail('');
          }}
        >
          Use a different email
        </Button>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <TextField
        fullWidth
        type="email"
        label="Email address"
        placeholder="Enter your email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        disabled={isLoading}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Email color="action" />
            </InputAdornment>
          ),
        }}
        sx={{ mb: 2 }}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Button 
        type="submit" 
        fullWidth 
        variant="contained"
        disabled={isLoading || !email}
        sx={{ py: 1.5 }}
      >
        {isLoading ? <CircularProgress size={24} /> : 'Send Magic Link'}
      </Button>
    </Box>
  );
};

// Email/Password Signup Form Component  
const EmailPasswordSignUpForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);
  const { signUp } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !confirmPassword) return;
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await signUp(email, password);
      if (error) {
        setError(error.message || 'Failed to create account');
      } else {
        setIsSuccess(true);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create account');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Box
          sx={{
            mx: 'auto',
            width: 64,
            height: 64,
            bgcolor: 'success.light',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 3,
          }}
        >
          <CheckCircle sx={{ fontSize: 32, color: 'success.main' }} />
        </Box>
        <Typography variant="h6" gutterBottom>
          Account created successfully!
        </Typography>
        <Typography color="text.secondary" paragraph>
          Please check your email to verify your account.
        </Typography>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <TextField
        fullWidth
        type="email"
        label="Email address"
        placeholder="Enter your email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        disabled={isLoading}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Email color="action" />
            </InputAdornment>
          ),
        }}
        sx={{ mb: 2 }}
      />
      
      <TextField
        fullWidth
        type={showPassword ? 'text' : 'password'}
        label="Password"
        placeholder="Create a password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        disabled={isLoading}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Lock color="action" />
            </InputAdornment>
          ),
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label="toggle password visibility"
                onClick={() => setShowPassword(!showPassword)}
                edge="end"
                disabled={isLoading}
              >
                {showPassword ? <VisibilityOff /> : <Visibility />}
              </IconButton>
            </InputAdornment>
          ),
        }}
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        type={showConfirmPassword ? 'text' : 'password'}
        label="Confirm Password"
        placeholder="Confirm your password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        required
        disabled={isLoading}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Lock color="action" />
            </InputAdornment>
          ),
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label="toggle confirm password visibility"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                edge="end"
                disabled={isLoading}
              >
                {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
              </IconButton>
            </InputAdornment>
          ),
        }}
        sx={{ mb: 2 }}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Button 
        type="submit" 
        fullWidth 
        variant="contained"
        disabled={isLoading || !email || !password || !confirmPassword}
        sx={{ py: 1.5, mb: 2 }}
      >
        {isLoading ? <CircularProgress size={24} /> : 'Create Account'}
      </Button>
      
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
        By creating an account, you agree to our Terms of Service and Privacy Policy
      </Typography>
    </Box>
  );
};

interface SignUpPageProps {
  onSwitchToSignIn?: () => void;
}

const SignUpPage: React.FC<SignUpPageProps> = ({ onSwitchToSignIn }) => {
  const { user, signInWithGoogle } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const theme = useTheme();

  // Redirect if already logged in
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleGoogleSignUp = async () => {
    try {
      const { error } = await signInWithGoogle();
      if (error) {
        console.error('Google sign-up error:', error);
        alert('Google sign-up failed. Please try again.');
      }
    } catch (error) {
      console.error('Google sign-up error:', error);
      alert('Google sign-up failed. Please try again.');
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex' }}>
      {/* Left Panel - Visual Storytelling */}
      <Box 
        sx={{ 
          display: { xs: 'none', lg: 'flex' }, 
          width: '50%', 
          position: 'relative' 
        }}
      >
        <ImageCarousel />
      </Box>
      
      {/* Right Panel - Sign Up Options */}
      <Box 
        sx={{ 
          width: { xs: '100%', lg: '50%' }, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          px: 3,
          py: 6,
          bgcolor: 'background.default'
        }}
      >
        <Container maxWidth="sm">
          <Box sx={{ maxWidth: 480, mx: 'auto' }}>
            {/* Header */}
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Typography variant="h3" component="h1" gutterBottom fontWeight="bold">
                Create your account
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Join AudienceLab and start creating resonant content
              </Typography>
            </Box>

            {/* Google Sign-up Button */}
            <Button
              variant="outlined"
              fullWidth
              size="large"
              onClick={handleGoogleSignUp}
              startIcon={<Google />}
              sx={{ 
                py: 1.5, 
                mb: 3,
                borderColor: 'divider',
                '&:hover': {
                  bgcolor: 'action.hover',
                }
              }}
            >
              Continue with Google
            </Button>

            <Box sx={{ position: 'relative', mb: 3 }}>
              <Divider />
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  bgcolor: 'background.default',
                  px: 2,
                }}
              >
                or
              </Typography>
            </Box>

            {/* Sign-up Options Card */}
            <Card elevation={2}>
              <CardContent sx={{ p: 4 }}>
                <Tabs 
                  value={tabValue} 
                  onChange={handleTabChange} 
                  centered
                  sx={{ mb: 2 }}
                >
                  <Tab label="Magic Link" />
                  <Tab label="Email & Password" />
                </Tabs>
                
                <CustomTabPanel value={tabValue} index={0}>
                  <Typography variant="h6" gutterBottom>
                    Sign up with Magic Link
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Enter your email and we'll send you a secure link to create your account
                  </Typography>
                  <MagicLinkSignUpForm />
                </CustomTabPanel>
                
                <CustomTabPanel value={tabValue} index={1}>
                  <Typography variant="h6" gutterBottom>
                    Create Account
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Fill in your details to create your AudienceLab account
                  </Typography>
                  <EmailPasswordSignUpForm />
                </CustomTabPanel>
              </CardContent>
            </Card>

            {/* Footer */}
            <Box sx={{ textAlign: 'center', mt: 4 }}>
              <Typography variant="body2" color="text.secondary">
                Already have an account?{' '}
                <Button
                  variant="text"
                  onClick={onSwitchToSignIn}
                  sx={{ 
                    textTransform: 'none',
                    fontWeight: 600,
                    p: 0,
                    minWidth: 'auto',
                  }}
                >
                  Sign in here
                </Button>
              </Typography>
            </Box>
          </Box>
        </Container>
      </Box>
    </Box>
  );
};

export default SignUpPage;
