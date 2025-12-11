import React, { useState, useEffect } from 'react';
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
  Grid,
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
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import SignUpPage from './SignUpPage';

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
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

// Image carousel data
const carouselData = [
  {
    image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=800&h=600&fit=crop",
    tagline: "Transform Your Business",
    subtitle: "Create compelling video ads that convert viewers into customers with our AI-powered platform"
  },
  {
    image: "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=800&h=600&fit=crop",
    tagline: "Accelerate Growth", 
    subtitle: "Boost your marketing ROI with video campaigns that drive real results for your business"
  },
  {
    image: "https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=800&h=600&fit=crop",
    tagline: "Scale Your Success",
    subtitle: "Join thousands of businesses using AudienceLab to create resonant marketing content"
  }
];

// Image Carousel Component
const ImageCarousel: React.FC = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const theme = useTheme();

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prevIndex) => 
        prevIndex === carouselData.length - 1 ? 0 : prevIndex + 1
      );
    }, 4000);

    return () => clearInterval(interval);
  }, []);

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

// Magic Link Form Component
const MagicLinkForm: React.FC = () => {
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
          Click the link to sign in to your account.
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

// Email/Password Form Component  
const EmailPasswordForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { signIn } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await signIn(email, password);
      if (error) {
        setError(error.message || 'Failed to sign in');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to sign in');
    } finally {
      setIsLoading(false);
    }
  };

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
        placeholder="Enter your password"
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

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Button 
        type="submit" 
        fullWidth 
        variant="contained"
        disabled={isLoading || !email || !password}
        sx={{ py: 1.5, mb: 2 }}
      >
        {isLoading ? <CircularProgress size={24} /> : 'Sign In'}
      </Button>
      
      <Box sx={{ textAlign: 'center' }}>
        <Button
          variant="text"
          size="small"
          onClick={() => {
            alert('Forgot password functionality coming soon!');
          }}
        >
          Forgot your password?
        </Button>
      </Box>
    </Box>
  );
};

const LoginPage: React.FC = () => {
  const { user } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);

  // Redirect if already logged in
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSwitchToSignUp = () => {
    setIsSignUp(true);
  };

  const handleSwitchToSignIn = () => {
    setIsSignUp(false);
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {isSignUp ? (
        <SignUpPage onSwitchToSignIn={handleSwitchToSignIn} />
      ) : (
        <SignInPage onSwitchToSignUp={handleSwitchToSignUp} />
      )}
    </Box>
  );
};

// Sign In Page Component
const SignInPage: React.FC<{ onSwitchToSignUp: () => void }> = ({ onSwitchToSignUp }) => {
  const { signInWithGoogle } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const theme = useTheme();

  const handleGoogleSignIn = async () => {
    try {
      const { error } = await signInWithGoogle();
      if (error) {
        console.error('Google sign-in error:', error);
        alert('Google sign-in failed. Please try again.');
      }
    } catch (error) {
      console.error('Google sign-in error:', error);
      alert('Google sign-in failed. Please try again.');
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
      
      {/* Right Panel - Sign In Options */}
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
                Welcome back!
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Sign in to your account to continue
              </Typography>
            </Box>

            {/* Google Sign-in Button */}
            <Button
              variant="outlined"
              fullWidth
              size="large"
              onClick={handleGoogleSignIn}
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

            {/* Sign-in Options Card */}
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
                    Sign in with Magic Link
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    We'll send you a secure link to sign in without a password
                  </Typography>
                  <MagicLinkForm />
                </CustomTabPanel>
                
                <CustomTabPanel value={tabValue} index={1}>
                  <Typography variant="h6" gutterBottom>
                    Sign In
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Enter your credentials to access your account
                  </Typography>
                  <EmailPasswordForm />
                </CustomTabPanel>
              </CardContent>
            </Card>

            {/* Development Mode Button - only show in development */}
            {process.env.NODE_ENV === 'development' && (
              <Box sx={{ textAlign: 'center', mt: 2 }}>
                <Button
                  variant="text"
                  size="small"
                  onClick={async () => {
                    try {
                      const response = await fetch('http://localhost:8001/auth/dev-login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                      });
                      if (response.ok) {
                        window.location.reload();
                      }
                    } catch (error) {
                      console.error('Dev login failed:', error);
                    }
                  }}
                  sx={{ 
                    textTransform: 'none',
                    fontSize: '0.8rem',
                    color: 'text.secondary',
                    '&:hover': {
                      color: 'primary.main',
                    }
                  }}
                >
                  🚀 Development Mode Login
                </Button>
              </Box>
            )}

            {/* Footer */}
            <Box sx={{ textAlign: 'center', mt: 4 }}>
              <Typography variant="body2" color="text.secondary">
                Don't have an account?{' '}
                <Button
                  variant="text"
                  onClick={onSwitchToSignUp}
                  sx={{ 
                    textTransform: 'none',
                    fontWeight: 600,
                    p: 0,
                    minWidth: 'auto',
                  }}
                >
                  Create account here
                </Button>
              </Typography>
            </Box>
          </Box>
        </Container>
      </Box>
    </Box>
  );
};

export default LoginPage;
