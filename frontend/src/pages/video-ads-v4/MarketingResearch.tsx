import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  LinearProgress,
  Stack,
  Breadcrumbs,
  Link,
  Card,
  CardContent,
  Chip,
  ListItemIcon,
  CircularProgress,
} from '@mui/material';
import {
  Check as CheckIcon,
  Pending as PendingIcon,
  PlayArrow as PlayIcon,
  ArrowForward as ArrowForwardIcon,
  Campaign as CampaignIcon,
  Psychology as PsychologyIcon,
  Description as DescriptionIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface GenerationStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  count?: number;
  total?: number;
}

const MarketingResearch: React.FC = () => {
  const navigate = useNavigate();
  const { campaignId } = useParams();
  const { session } = useAuth();

  const [steps, setSteps] = useState<GenerationStep[]>([
    {
      id: 'angles',
      name: 'Marketing Angles',
      description: 'Generate 14 marketing angles (7 positive, 7 negative)',
      status: 'pending',
      total: 14,
    },
    {
      id: 'hooks',
      name: 'Viral Hooks',
      description: 'Generate 294 hooks (21 per angle)',
      status: 'pending',
      total: 294,
    },
    {
      id: 'scripts',
      name: 'Video Scripts',
      description: 'Generate 588 scripts (2 per hook)',
      status: 'pending',
      total: 588,
    },
  ]);

  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [totalProgress, setTotalProgress] = useState(0);

  const updateStepStatus = (stepId: string, status: GenerationStep['status'], count?: number) => {
    setSteps(prev =>
      prev.map(step =>
        step.id === stepId ? { ...step, status, count: count || step.count } : step
      )
    );
  };

  const generateAngles = async () => {
    updateStepStatus('angles', 'in_progress');

    try {
      const token = session?.access_token;
      if (!token) throw new Error('No authentication token');

      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v4/create-marketing-research`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          campaign_id: campaignId,
          force_new_conversation: false,
        }),
      });

      // Handle 202 Accepted (async processing)
      if (response.status === 202) {
        const data = await response.json();
        // Show success message and redirect
        setTimeout(() => {
          navigate('/video-ads-v4/campaigns');
        }, 3000);
        return { async: true, message: data.message };
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate angles');
      }

      const data = await response.json();
      const totalAngles = (data.positive_angles?.length || 0) + (data.negative_angles?.length || 0);
      updateStepStatus('angles', 'completed', totalAngles);
      return data;
    } catch (err) {
      updateStepStatus('angles', 'error');
      throw err;
    }
  };

  const generateHooks = async () => {
    updateStepStatus('hooks', 'in_progress');

    try {
      const token = session?.access_token;
      if (!token) throw new Error('No authentication token');

      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v4/batch-generate-hooks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ campaign_id: campaignId }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate hooks');
      }

      const data = await response.json();
      updateStepStatus('hooks', 'completed', data.total_hooks_generated);
      return data;
    } catch (err) {
      updateStepStatus('hooks', 'error');
      throw err;
    }
  };

  const generateScripts = async () => {
    updateStepStatus('scripts', 'in_progress');

    try {
      const token = session?.access_token;
      if (!token) throw new Error('No authentication token');

      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v4/batch-generate-scripts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ campaign_id: campaignId }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate scripts');
      }

      const data = await response.json();
      updateStepStatus('scripts', 'completed', data.total_scripts_generated);
      return data;
    } catch (err) {
      updateStepStatus('scripts', 'error');
      throw err;
    }
  };

  const startGeneration = async () => {
    setGenerating(true);
    setError(null);
    setSuccess(false);
    setTotalProgress(0);

    try {
      // Phase 1: Generate Angles
      console.log('Generating angles...');
      const anglesResult = await generateAngles();

      // Check if async processing (202 response)
      if (anglesResult && (anglesResult as any).async) {
        setSuccess(true);
        setTotalProgress(100);
        updateStepStatus('angles', 'completed');
        // Don't run hooks and scripts - they're handled in background
        return;
      }

      setTotalProgress(33);

      // Phase 2: Generate Hooks
      console.log('Generating hooks...');
      await generateHooks();
      setTotalProgress(66);

      // Phase 3: Generate Scripts
      console.log('Generating scripts...');
      await generateScripts();
      setTotalProgress(100);

      setSuccess(true);
    } catch (err: any) {
      console.error('Generation error:', err);
      setError(err.message || 'Failed to generate content');
    } finally {
      setGenerating(false);
    }
  };

  const getStepIcon = (status: GenerationStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'in_progress':
        return <CircularProgress size={20} />;
      case 'error':
        return <CloseIcon color="error" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  const navigateToLibrary = () => {
    navigate(`/video-ads-v4/library/${campaignId}`);
  };

  // Auto-start generation on component mount
  useEffect(() => {
    if (!generating && steps[0].status === 'pending') {
      startGeneration();
    }
  }, []);

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Breadcrumbs sx={{ mb: 3 }}>
          <Link color="inherit" href="#" onClick={() => navigate('/video-ads-v4/import')} sx={{ cursor: 'pointer' }}>
            Import URL
          </Link>
          <Link color="inherit" href="#" onClick={() => navigate(`/video-ads-v4/product-info/${campaignId}`)} sx={{ cursor: 'pointer' }}>
            Product Info
          </Link>
          <Typography color="text.primary">Marketing Research</Typography>
        </Breadcrumbs>

        <Typography variant="h4" gutterBottom sx={{ mb: 1 }}>
          V4 Workflow - Step 3: Generate Marketing Content
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Generating comprehensive marketing content for your campaign
        </Typography>

        {/* Overall Progress */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Overall Progress
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Box sx={{ width: '100%', mr: 1 }}>
              <LinearProgress variant="determinate" value={totalProgress} sx={{ height: 10, borderRadius: 5 }} />
            </Box>
            <Box sx={{ minWidth: 35 }}>
              <Typography variant="body2" color="text.secondary">
                {`${Math.round(totalProgress)}%`}
              </Typography>
            </Box>
          </Box>
        </Paper>

        {/* Generation Steps */}
        <Stack spacing={2}>
          {steps.map((step) => (
            <Card key={step.id} sx={{ opacity: step.status === 'pending' ? 0.7 : 1 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <ListItemIcon>
                      {step.id === 'angles' && <CampaignIcon />}
                      {step.id === 'hooks' && <PsychologyIcon />}
                      {step.id === 'scripts' && <DescriptionIcon />}
                    </ListItemIcon>
                    <Box>
                      <Typography variant="h6">
                        {step.name}
                        {step.count && (
                          <Chip
                            label={`${step.count} / ${step.total}`}
                            size="small"
                            sx={{ ml: 2 }}
                            color={step.status === 'completed' ? 'success' : 'default'}
                          />
                        )}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {step.description}
                      </Typography>
                    </Box>
                  </Box>
                  <Box>{getStepIcon(step.status)}</Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mt: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mt: 3 }}>
            Campaign is being built! Check status in Campaign List. You'll be redirected in 3 seconds...
          </Alert>
        )}

        {/* Actions */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4, gap: 2 }}>
          {!generating && !success && (
            <Button
              variant="contained"
              size="large"
              startIcon={<PlayIcon />}
              onClick={startGeneration}
            >
              Retry Generation
            </Button>
          )}

          {success && (
            <Button
              variant="contained"
              size="large"
              endIcon={<ArrowForwardIcon />}
              onClick={() => navigate('/video-ads-v4/campaigns')}
            >
              View Campaign List
            </Button>
          )}
        </Box>

        {/* Info Box */}
        <Box sx={{ mt: 4, p: 3, bgcolor: 'background.paper', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom color="primary">
            What's being generated?
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • <strong>Marketing Angles:</strong> Strategic approaches to present your product<br />
            • <strong>Viral Hooks:</strong> Attention-grabbing openings for your ads (2-3 seconds)<br />
            • <strong>Video Scripts:</strong> Complete scripts ready for video production<br />
            <br />
            This process typically takes 3-5 minutes. All content is saved automatically.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default MarketingResearch;