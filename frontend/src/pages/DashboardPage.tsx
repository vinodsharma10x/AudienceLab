import React, { useEffect, useState, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  CircularProgress,
  Stack,
  Paper,
  LinearProgress,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemButton,
  Divider,
  IconButton,
  CardActions,
  Grid,
} from '@mui/material';
import ServerError from '../components/ServerError';
import {
  VideoLibrary,
  TrendingUp,
  Facebook,
  Analytics,
  CheckCircle,
  RadioButtonUnchecked,
  PlayCircleOutline,
  Campaign,
  Speed,
  AttachMoney,
  MovieCreation,
  AutoAwesome,
  ConnectWithoutContact,
  School,
  ArrowForward,
  Add,
  BarChart,
  People,
  Visibility,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

interface DashboardStats {
  total_projects: number;
  active_sessions: number;
  last_login: string;
  account_status: string;
}

interface DashboardData {
  user: {
    id: string;
    email: string;
    created_at: string;
  };
  stats: DashboardStats;
  message: string;
}

const DashboardPage: React.FC = () => {
  const { user, session, signOut } = useAuth();
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [serverError, setServerError] = useState(false);
  const [fbConnected, setFbConnected] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    if (!session?.access_token) {
      setLoading(false);
      return;
    }

    setServerError(false);
    setError(null);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/dashboard`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
        setServerError(false);
      } else {
        setError('Failed to load dashboard data');
      }
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setServerError(true);
      setError('Unable to connect to server');
    } finally {
      setLoading(false);
    }
  }, [session?.access_token]);

  const checkFacebookConnection = useCallback(async () => {
    if (!session?.access_token) return;

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/facebook/accounts`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setFbConnected(data.accounts && data.accounts.length > 0);
      }
    } catch (err) {
      console.error('Failed to check Facebook connection:', err);
    }
  }, [session?.access_token]);

  useEffect(() => {
    fetchDashboardData();
    checkFacebookConnection();
  }, [fetchDashboardData, checkFacebookConnection]);

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (serverError) {
    return (
      <ServerError 
        onRetry={fetchDashboardData}
        message="Cannot connect to the backend server"
      />
    );
  }

  // Determine user state
  const isNewUser = !dashboardData?.stats || 
    (dashboardData.stats.total_projects === 0 && !fbConnected);
  
  // Get greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  // Onboarding steps for new users
  const onboardingSteps = [
    { 
      id: 1, 
      text: 'Create your first video ad', 
      completed: (dashboardData?.stats?.total_projects ?? 0) > 0, 
      path: '/video-ads/import-from-url',
      icon: <MovieCreation />
    },
    { 
      id: 2, 
      text: 'Connect your Facebook account', 
      completed: fbConnected, 
      path: '/dashboard/facebook',
      icon: <Facebook />
    },
    { 
      id: 3, 
      text: 'Set up your first campaign', 
      completed: false, 
      path: '/facebook/analytics',
      icon: <Campaign />
    },
    { 
      id: 4, 
      text: 'Review analytics dashboard', 
      completed: false, 
      path: '/facebook/analytics',
      icon: <Analytics />
    },
  ];
  
  const completedSteps = onboardingSteps.filter(step => step.completed).length;
  const progressPercentage = (completedSteps / onboardingSteps.length) * 100;

  // Sample data for active users
  const recentProjects = [
    { id: 1, name: 'Summer Sale Campaign', status: 'Active', date: '2 hours ago', icon: <Campaign />, color: '#4caf50' },
    { id: 2, name: 'Product Launch Video', status: 'Draft', date: '1 day ago', icon: <VideoLibrary />, color: '#ff9800' },
    { id: 3, name: 'Brand Awareness Ad', status: 'Completed', date: '3 days ago', icon: <TrendingUp />, color: '#2196f3' },
  ];

  // Stats cards for active users
  const statsCards = [
    { title: 'Total Impressions', value: '124.5K', change: '+12.5%', icon: <Visibility />, color: '#2196f3' },
    { title: 'Engagement Rate', value: '3.8%', change: '+0.5%', icon: <People />, color: '#4caf50' },
    { title: 'Ad Spend', value: '€2,450', change: '-8.2%', icon: <AttachMoney />, color: '#ff9800' },
    { title: 'Conversions', value: '342', change: '+18.3%', icon: <TrendingUp />, color: '#9c27b0' },
  ];

  return (
    <Box sx={{ backgroundColor: '#f5f5f5', minHeight: '100vh', p: 3 }}>
      <Container maxWidth="xl">
        {/* Header Section */}
        <Box mb={4}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h4" fontWeight="bold">
              {getGreeting()}, {user?.email?.split('@')[0] || 'there'}!
            </Typography>
            <Chip 
              label="Sample Content" 
              size="small" 
              color="info" 
              variant="outlined"
              sx={{ height: 24 }}
            />
          </Box>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
            {isNewUser 
              ? "Let's get you started with creating amazing video ads"
              : "Here's your campaign performance overview"}
          </Typography>
        </Box>

        {isNewUser ? (
          // New User Experience
          <>
            {/* Onboarding Progress */}
            <Card sx={{ mb: 4, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <CardContent>
                <Typography variant="h6" color="white" gutterBottom>
                  Getting Started Progress
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ width: '100%', mr: 2 }}>
                    <LinearProgress 
                      variant="determinate" 
                      value={progressPercentage} 
                      sx={{ 
                        height: 10, 
                        borderRadius: 5,
                        backgroundColor: 'rgba(255,255,255,0.3)',
                        '& .MuiLinearProgress-bar': {
                          backgroundColor: 'white',
                        }
                      }}
                    />
                  </Box>
                  <Typography variant="body2" color="white" sx={{ minWidth: 50 }}>
                    {completedSteps}/{onboardingSteps.length}
                  </Typography>
                </Box>
                <Typography variant="body2" color="rgba(255,255,255,0.9)">
                  Complete these steps to unlock the full potential of AudienceLab
                </Typography>
              </CardContent>
            </Card>

            {/* Onboarding Checklist */}
            <Grid container spacing={3} mb={4}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <School sx={{ mr: 1 }} />
                      Quick Start Guide
                    </Typography>
                    <List>
                      {onboardingSteps.map((step) => (
                        <ListItem key={step.id} disablePadding>
                          <ListItemButton onClick={() => handleNavigation(step.path)}>
                            <ListItemAvatar>
                              <Avatar sx={{ 
                                bgcolor: step.completed ? '#4caf50' : '#e0e0e0',
                                width: 36,
                                height: 36,
                              }}>
                                {step.completed ? <CheckCircle /> : step.icon}
                              </Avatar>
                            </ListItemAvatar>
                            <ListItemText 
                              primary={step.text}
                              secondary={step.completed ? 'Completed' : 'Click to start'}
                              sx={{
                                '& .MuiListItemText-primary': {
                                  textDecoration: step.completed ? 'line-through' : 'none',
                                  color: step.completed ? 'text.secondary' : 'text.primary',
                                }
                              }}
                            />
                            <ArrowForward color="action" />
                          </ListItemButton>
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                </Card>
              </Grid>

              <Grid size={{ xs: 12, md: 6 }}>
                <Card 
                  sx={{ 
                    height: '100%',
                    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                    color: 'white',
                    cursor: 'pointer',
                    transition: 'transform 0.3s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                    }
                  }}
                  onClick={() => handleNavigation('/video-ads-v2/import-from-url')}
                >
                  <CardContent sx={{ 
                    height: '100%', 
                    display: 'flex', 
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    textAlign: 'center',
                  }}>
                    <AutoAwesome sx={{ fontSize: 60, mb: 2 }} />
                    <Typography variant="h5" fontWeight="bold" gutterBottom>
                      Try Video Ad 2.0
                    </Typography>
                    <Typography variant="body1" sx={{ mb: 3, opacity: 0.95 }}>
                      Experience our AI-powered video creation with enhanced content understanding
                    </Typography>
                    <Button 
                      variant="contained" 
                      size="large"
                      sx={{ 
                        bgcolor: 'white', 
                        color: '#f5576c',
                        '&:hover': {
                          bgcolor: 'rgba(255,255,255,0.9)',
                        }
                      }}
                    >
                      Start Creating
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Quick Action Cards */}
            <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
              Quick Actions
            </Typography>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 3,
                    }
                  }}
                  onClick={() => handleNavigation('/video-ads/import-from-url')}
                >
                  <CardContent sx={{ textAlign: 'center', py: 3 }}>
                    <Avatar sx={{ width: 56, height: 56, bgcolor: '#2196f3', mx: 'auto', mb: 2 }}>
                      <VideoLibrary />
                    </Avatar>
                    <Typography variant="h6" gutterBottom>
                      Create Video Ad
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Import content and create engaging ads
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 3,
                    }
                  }}
                  onClick={() => handleNavigation('/dashboard/facebook')}
                >
                  <CardContent sx={{ textAlign: 'center', py: 3 }}>
                    <Avatar sx={{ width: 56, height: 56, bgcolor: '#1877f2', mx: 'auto', mb: 2 }}>
                      <Facebook />
                    </Avatar>
                    <Typography variant="h6" gutterBottom>
                      Connect Facebook
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Link your ad accounts for analytics
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 3,
                    }
                  }}
                >
                  <CardContent sx={{ textAlign: 'center', py: 3 }}>
                    <Avatar sx={{ width: 56, height: 56, bgcolor: '#4caf50', mx: 'auto', mb: 2 }}>
                      <PlayCircleOutline />
                    </Avatar>
                    <Typography variant="h6" gutterBottom>
                      Watch Tutorial
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Learn how to create effective ads
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 3,
                    }
                  }}
                >
                  <CardContent sx={{ textAlign: 'center', py: 3 }}>
                    <Avatar sx={{ width: 56, height: 56, bgcolor: '#ff9800', mx: 'auto', mb: 2 }}>
                      <School />
                    </Avatar>
                    <Typography variant="h6" gutterBottom>
                      Browse Templates
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Start with professional templates
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </>
        ) : (
          // Active User Experience
          <>
            {/* Stats Overview */}
            <Grid container spacing={3} mb={4}>
              {statsCards.map((stat, index) => (
                <Grid size={{ xs: 12, sm: 6, md: 3 }} key={index}>
                  <Card sx={{ 
                    background: `linear-gradient(135deg, ${stat.color}22 0%, ${stat.color}11 100%)`,
                    borderLeft: `4px solid ${stat.color}`,
                  }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {stat.title}
                          </Typography>
                          <Typography variant="h4" fontWeight="bold">
                            {stat.value}
                          </Typography>
                          <Chip 
                            label={stat.change}
                            size="small"
                            sx={{ 
                              mt: 1,
                              bgcolor: stat.change.startsWith('+') ? '#4caf5022' : '#f4433622',
                              color: stat.change.startsWith('+') ? '#4caf50' : '#f44336',
                              fontWeight: 'bold',
                            }}
                          />
                        </Box>
                        <Avatar sx={{ bgcolor: stat.color, width: 48, height: 48 }}>
                          {stat.icon}
                        </Avatar>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            <Grid container spacing={3}>
              {/* Recent Projects */}
              <Grid size={{ xs: 12, md: 8 }}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6">
                        Recent Projects
                      </Typography>
                      <Button 
                        startIcon={<Add />}
                        variant="outlined"
                        size="small"
                        onClick={() => handleNavigation('/video-ads/import-from-url')}
                      >
                        New Project
                      </Button>
                    </Box>
                    <List>
                      {recentProjects.map((project, index) => (
                        <React.Fragment key={project.id}>
                          <ListItem
                            secondaryAction={
                              <Chip 
                                label={project.status}
                                size="small"
                                sx={{ 
                                  bgcolor: `${project.color}22`,
                                  color: project.color,
                                  fontWeight: 'bold',
                                }}
                              />
                            }
                          >
                            <ListItemAvatar>
                              <Avatar sx={{ bgcolor: project.color }}>
                                {project.icon}
                              </Avatar>
                            </ListItemAvatar>
                            <ListItemText 
                              primary={project.name}
                              secondary={project.date}
                            />
                          </ListItem>
                          {index < recentProjects.length - 1 && <Divider variant="inset" component="li" />}
                        </React.Fragment>
                      ))}
                    </List>
                  </CardContent>
                  <CardActions>
                    <Button size="small" fullWidth>
                      View All Campaigns
                    </Button>
                  </CardActions>
                </Card>
              </Grid>

              {/* Quick Actions */}
              <Grid size={{ xs: 12, md: 4 }}>
                <Stack spacing={2}>
                  <Card 
                    sx={{ 
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      cursor: 'pointer',
                      transition: 'transform 0.3s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                      }
                    }}
                    onClick={() => handleNavigation('/facebook/analytics')}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box>
                          <Typography variant="h6" fontWeight="bold">
                            View Analytics
                          </Typography>
                          <Typography variant="body2" sx={{ opacity: 0.9, mt: 1 }}>
                            Check your campaign performance
                          </Typography>
                        </Box>
                        <BarChart sx={{ fontSize: 40, opacity: 0.8 }} />
                      </Box>
                    </CardContent>
                  </Card>

                  <Card 
                    sx={{ 
                      background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                      color: 'white',
                      cursor: 'pointer',
                      transition: 'transform 0.3s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                      }
                    }}
                    onClick={() => handleNavigation('/video-ads-v2/import-from-url')}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box>
                          <Typography variant="h6" fontWeight="bold">
                            Create with AI
                          </Typography>
                          <Typography variant="body2" sx={{ opacity: 0.9, mt: 1 }}>
                            Try our enhanced Video Ad 2.0
                          </Typography>
                        </Box>
                        <AutoAwesome sx={{ fontSize: 40, opacity: 0.8 }} />
                      </Box>
                    </CardContent>
                  </Card>

                  <Card 
                    sx={{ 
                      background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                      color: 'white',
                      cursor: 'pointer',
                      transition: 'transform 0.3s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                      }
                    }}
                    onClick={() => handleNavigation('/facebook/conversion-report')}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box>
                          <Typography variant="h6" fontWeight="bold">
                            Conversion Report
                          </Typography>
                          <Typography variant="body2" sx={{ opacity: 0.9, mt: 1 }}>
                            View detailed conversion metrics
                          </Typography>
                        </Box>
                        <Speed sx={{ fontSize: 40, opacity: 0.8 }} />
                      </Box>
                    </CardContent>
                  </Card>
                </Stack>
              </Grid>
            </Grid>
          </>
        )}
      </Container>
    </Box>
  );
};

export default DashboardPage;