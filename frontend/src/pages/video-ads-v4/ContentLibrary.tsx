import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Stack,
  Breadcrumbs,
  Link,
  Card,
  CardContent,
  Chip,
  IconButton,
  Grid,
  Divider,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Badge,
  Fade,
  Slide,
  alpha,
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  CheckCircle as CheckCircleIcon,
  Download as DownloadIcon,
  ArrowBack as BackIcon,
  TrendingUp as PositiveIcon,
  TrendingDown as NegativeIcon,
  AutoAwesome as HookIcon,
  Description as ScriptIcon,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface MarketingAngle {
  angle_number: number;
  angle_name: string;
  angle_description: string;
  angle_type: 'positive' | 'negative';
  concept?: string;
  category?: string;
}

interface Hook {
  hook_id: string;
  hook_text: string;
  hook_category: string;
}

interface Script {
  script_id: string;
  script_text: string;
  word_count?: number;
}

const ContentLibrary: React.FC = () => {
  const navigate = useNavigate();
  const { campaignId } = useParams();
  const { session } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Data states
  const [angles, setAngles] = useState<MarketingAngle[]>([]);
  const [hooksData, setHooksData] = useState<any[]>([]);
  const [scriptsData, setScriptsData] = useState<any>(null);

  // Batch processing states
  const [batchStatus, setBatchStatus] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);

  // Selection states
  const [selectedAngle, setSelectedAngle] = useState<number | null>(null);
  const [selectedHook, setSelectedHook] = useState<Hook | null>(null);
  const [currentHooks, setCurrentHooks] = useState<Hook[]>([]);
  const [currentScripts, setCurrentScripts] = useState<Script[]>([]);

  useEffect(() => {
    fetchContent();
  }, [campaignId]);

  useEffect(() => {
    // When angle is selected, load its hooks
    if (selectedAngle !== null) {
      loadHooksForAngle(selectedAngle);
    } else {
      setCurrentHooks([]);
      setSelectedHook(null);
      setCurrentScripts([]);
    }
  }, [selectedAngle]);

  useEffect(() => {
    // When hook is selected, load its scripts
    if (selectedHook) {
      loadScriptsForHook(selectedHook);
    } else {
      setCurrentScripts([]);
    }
  }, [selectedHook]);

  const fetchContent = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = session?.access_token;
      if (!token) throw new Error('No authentication token');

      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/video-ads-v4/campaign/${campaignId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch campaign content');
      }

      const campaign = await response.json();
      const content = campaign.content || {};

      // Check campaign status for batch processing
      if (campaign.status === 'batch_processing') {
        setBatchStatus('processing');
        // Start polling for batch completion
        if (!isPolling) {
          setIsPolling(true);
          pollBatchStatus();
        }
      } else {
        setBatchStatus(null);
        setIsPolling(false);
      }

      // Parse angles
      const parsedAngles: MarketingAngle[] = [];
      if (content.angles) {
        content.angles.positive_angles?.forEach((angle: any) => {
          parsedAngles.push({
            angle_number: angle.angle_number || angle.angle,
            angle_name: angle.angle_name || angle.concept || '',
            angle_description: angle.angle_description || angle.category || '',
            angle_type: 'positive',
            concept: angle.concept,
            category: angle.category
          });
        });

        content.angles.negative_angles?.forEach((angle: any) => {
          parsedAngles.push({
            angle_number: angle.angle_number || angle.angle,
            angle_name: angle.angle_name || angle.concept || '',
            angle_description: angle.angle_description || angle.category || '',
            angle_type: 'negative',
            concept: angle.concept,
            category: angle.category
          });
        });
      }

      setAngles(parsedAngles);
      setHooksData(content.hooks || []);
      setScriptsData(content.scripts || {});
    } catch (err: any) {
      console.error('Error fetching content:', err);
      setError(err.message || 'Failed to load content');
    } finally {
      setLoading(false);
    }
  };

  const checkBatchStatus = async () => {
    try {
      const token = session?.access_token;
      if (!token) return;

      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/video-ads-v4/batch-status/${campaignId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setBatchProgress(data);

        // If batch is complete, fetch updated content
        if (data.batch_status === 'completed') {
          setIsPolling(false);
          setBatchStatus('completed');
          await fetchContent();
        } else if (data.batch_status === 'failed') {
          setIsPolling(false);
          setBatchStatus('failed');
          setError(data.batch_error || 'Batch processing failed');
        }

        return data;
      }
    } catch (err) {
      console.error('Error checking batch status:', err);
    }
  };

  const pollBatchStatus = async () => {
    // Initial check
    const status = await checkBatchStatus();

    // Continue polling if still processing
    if (status?.batch_status === 'processing') {
      // Check and process batch results
      try {
        const token = session?.access_token;
        if (token) {
          await fetch(
            `${process.env.REACT_APP_API_URL}/video-ads-v4/check-and-process-batch/${campaignId}`,
            {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
              },
            }
          );
        }
      } catch (err) {
        console.error('Error processing batch:', err);
      }

      // Poll every 30 seconds
      setTimeout(() => {
        if (isPolling) {
          pollBatchStatus();
        }
      }, 30000);
    }
  };

  const loadHooksForAngle = (angleNumber: number) => {
    console.log('Loading hooks for angle:', angleNumber);
    console.log('Available hooksData:', hooksData);

    const angleHookData = hooksData.find(h => h.angle_number === angleNumber);
    console.log('Found angleHookData:', angleHookData);

    if (angleHookData) {
      const hooks: Hook[] = [];
      if (angleHookData.hooks_by_category) {
        Object.entries(angleHookData.hooks_by_category).forEach(([category, categoryHooks]: [string, any]) => {
          if (Array.isArray(categoryHooks)) {
            categoryHooks.forEach(hook => {
              hooks.push({
                hook_id: hook.hook_id,
                hook_text: hook.hook_text,
                hook_category: hook.hook_category || category
              });
            });
          }
        });
      } else if (angleHookData.hooks) {
        hooks.push(...angleHookData.hooks);
      }
      console.log('Loaded hooks:', hooks);
      setCurrentHooks(hooks);
    } else {
      console.log('No hooks found for angle', angleNumber);
      setCurrentHooks([]);
    }
    setSelectedHook(null);
    setCurrentScripts([]);
  };

  const loadScriptsForHook = (hook: Hook) => {
    const scripts: Script[] = [];

    // Find scripts in the scripts data
    if (scriptsData?.angles) {
      for (const angle of scriptsData.angles) {
        if (angle.hooks) {
          for (const hookData of angle.hooks) {
            if (hookData.hook_id === hook.hook_id && hookData.scripts) {
              hookData.scripts.forEach((script: any) => {
                scripts.push({
                  script_id: script.script_id || `script_${scripts.length + 1}`,
                  script_text: script.script_text || script,
                  word_count: script.word_count
                });
              });
              break;
            }
          }
        }
      }
    }

    setCurrentScripts(scripts);
  };

  const handleCopyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleExportAll = () => {
    const exportData = {
      campaign_id: campaignId,
      angles,
      hooks: hooksData,
      scripts: scriptsData,
      timestamp: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `campaign_${campaignId}_content.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <Container maxWidth="xl">
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl">
        <Box sx={{ py: 4 }}>
          <Alert severity="error">{error}</Alert>
          <Button sx={{ mt: 2 }} onClick={() => navigate(`/video-ads-v4/research/${campaignId}`)}>
            Go Back to Research
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Breadcrumbs sx={{ mb: 3 }}>
          <Link color="inherit" href="#" onClick={() => navigate('/video-ads-v4/import')} sx={{ cursor: 'pointer' }}>
            Import URL
          </Link>
          <Link color="inherit" href="#" onClick={() => navigate(`/video-ads-v4/product-info/${campaignId}`)} sx={{ cursor: 'pointer' }}>
            Product Info
          </Link>
          <Link color="inherit" href="#" onClick={() => navigate(`/video-ads-v4/research/${campaignId}`)} sx={{ cursor: 'pointer' }}>
            Marketing Research
          </Link>
          <Typography color="text.primary">Content Library</Typography>
        </Breadcrumbs>

        {/* Batch Processing Status */}
        {batchStatus === 'processing' && (
          <Fade in={true}>
            <Alert severity="info" sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <CircularProgress size={20} />
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    Generating Hooks and Scripts
                  </Typography>
                  <Typography variant="body2">
                    {batchProgress?.hooks_batch?.request_counts ? (
                      <>
                        Hooks: {batchProgress.hooks_batch.request_counts.succeeded} of{' '}
                        {batchProgress.hooks_batch.request_counts.succeeded +
                          batchProgress.hooks_batch.request_counts.processing} completed
                        {batchProgress.scripts_batch && ' | '}
                        {batchProgress.scripts_batch?.request_counts && (
                          <>
                            Scripts: {batchProgress.scripts_batch.request_counts.succeeded} of{' '}
                            {batchProgress.scripts_batch.request_counts.succeeded +
                              batchProgress.scripts_batch.request_counts.processing} completed
                          </>
                        )}
                      </>
                    ) : (
                      'Processing batch requests... This may take up to 1 hour.'
                    )}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Using Claude's Batch API for 50% cost savings. Auto-refreshing every 30 seconds.
                  </Typography>
                </Box>
              </Box>
            </Alert>
          </Fade>
        )}

        {batchStatus === 'completed' && (
          <Fade in={true}>
            <Alert severity="success" sx={{ mb: 3 }} onClose={() => setBatchStatus(null)}>
              <Typography variant="subtitle1">Batch processing completed successfully!</Typography>
              <Typography variant="body2">
                All hooks and scripts have been generated and are ready to use.
              </Typography>
            </Alert>
          </Fade>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              Content Library
            </Typography>
            <Stack direction="row" spacing={2}>
              <Chip label={`${angles.length} Angles`} color="primary" />
              <Chip label={`${hooksData.reduce((acc, h) => {
                const count = h.hooks_by_category
                  ? Object.values(h.hooks_by_category).reduce((sum: number, cat: any) =>
                      sum + (Array.isArray(cat) ? cat.length : 0), 0)
                  : (h.hooks?.length || 0);
                return acc + count;
              }, 0)} Hooks`} color="secondary" />
              <Chip label={`${scriptsData?.angles?.reduce((acc: number, angle: any) =>
                acc + angle.hooks?.reduce((hAcc: number, h: any) => hAcc + (h.scripts?.length || 0), 0), 0
              ) || 0} Scripts`} color="success" />
            </Stack>
          </Box>
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            onClick={handleExportAll}
          >
            Export All
          </Button>
        </Box>

        {/* Main Content Grid */}
        <Grid container spacing={2}>
          {/* Angles Column */}
          <Grid item xs={12} md={4} {...({} as any)}>
            <Paper sx={{ height: '75vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="h6">Marketing Angles</Typography>
              </Box>
              <List sx={{ overflow: 'auto', flex: 1 }}>
                {angles.map((angle) => (
                  <ListItem key={angle.angle_number} disablePadding>
                    <ListItemButton
                      selected={selectedAngle === angle.angle_number}
                      onClick={() => {
                        console.log('Angle clicked:', angle.angle_number);
                        setSelectedAngle(
                          selectedAngle === angle.angle_number ? null : angle.angle_number
                        );
                      }}
                      sx={{
                        '&.Mui-selected': {
                          backgroundColor: (theme) => alpha(theme.palette.primary.main, 0.08),
                          '&:hover': {
                            backgroundColor: (theme) => alpha(theme.palette.primary.main, 0.12),
                          }
                        }
                      }}
                    >
                      <Box sx={{ width: '100%', py: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          {angle.angle_type === 'positive' ? (
                            <PositiveIcon color="success" sx={{ mr: 1 }} />
                          ) : (
                            <NegativeIcon color="warning" sx={{ mr: 1 }} />
                          )}
                          <Typography variant="subtitle2" sx={{ flex: 1 }}>
                            Angle {angle.angle_number}
                          </Typography>
                          <Chip
                            label={angle.angle_type}
                            size="small"
                            color={angle.angle_type === 'positive' ? 'success' : 'warning'}
                          />
                        </Box>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          {angle.angle_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {angle.angle_description}
                        </Typography>
                      </Box>
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>

          {/* Hooks Column */}
          <Grid item xs={12} md={4} {...({} as any)}>
            <Slide direction="left" in={selectedAngle !== null} mountOnEnter unmountOnExit>
              <Paper sx={{ height: '75vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="h6">
                    Hooks
                    {selectedAngle && (
                      <Chip label={`${currentHooks.length} hooks`} size="small" sx={{ ml: 1 }} />
                    )}
                  </Typography>
                </Box>
                <List sx={{ overflow: 'auto', flex: 1 }}>
                  {currentHooks.map((hook) => (
                    <ListItem key={hook.hook_id} disablePadding>
                      <ListItemButton
                        selected={selectedHook?.hook_id === hook.hook_id}
                        onClick={() => setSelectedHook(
                          selectedHook?.hook_id === hook.hook_id ? null : hook
                        )}
                        sx={{
                          '&.Mui-selected': {
                            backgroundColor: (theme) => alpha(theme.palette.secondary.main, 0.08),
                            '&:hover': {
                              backgroundColor: (theme) => alpha(theme.palette.secondary.main, 0.12),
                            }
                          }
                        }}
                      >
                        <Box sx={{ width: '100%', py: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                            <HookIcon color="secondary" sx={{ mr: 1, mt: 0.5 }} />
                            <Typography variant="body2" sx={{ flex: 1 }}>
                              {hook.hook_text}
                            </Typography>
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCopyToClipboard(hook.hook_text, hook.hook_id);
                              }}
                            >
                              {copiedId === hook.hook_id ? (
                                <CheckCircleIcon color="success" fontSize="small" />
                              ) : (
                                <CopyIcon fontSize="small" />
                              )}
                            </IconButton>
                          </Box>
                          <Chip
                            label={hook.hook_category}
                            size="small"
                            variant="outlined"
                            sx={{ ml: 4 }}
                          />
                        </Box>
                      </ListItemButton>
                    </ListItem>
                  ))}
                  {selectedAngle !== null && currentHooks.length === 0 && (
                    <Box sx={{ p: 3, textAlign: 'center' }}>
                      <Typography color="text.secondary">
                        No hooks available for this angle
                      </Typography>
                    </Box>
                  )}
                </List>
              </Paper>
            </Slide>
          </Grid>

          {/* Scripts Column */}
          <Grid item xs={12} md={4} {...({} as any)}>
            <Slide direction="left" in={selectedHook !== null} mountOnEnter unmountOnExit>
              <Paper sx={{ height: '75vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="h6">
                    Scripts
                    {selectedHook && (
                      <Chip label={`${currentScripts.length} scripts`} size="small" sx={{ ml: 1 }} />
                    )}
                  </Typography>
                </Box>
                <Box sx={{ overflow: 'auto', flex: 1, p: 2 }}>
                  <Stack spacing={2}>
                    {currentScripts.map((script, index) => (
                      <Card key={script.script_id || index} variant="outlined">
                        <CardContent>
                          <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                            <ScriptIcon color="success" sx={{ mr: 1 }} />
                            <Typography variant="subtitle2" sx={{ flex: 1 }}>
                              Script {index + 1}
                              {script.word_count && (
                                <Chip
                                  label={`${script.word_count} words`}
                                  size="small"
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </Typography>
                            <IconButton
                              size="small"
                              onClick={() => handleCopyToClipboard(script.script_text, script.script_id)}
                            >
                              {copiedId === script.script_id ? (
                                <CheckCircleIcon color="success" fontSize="small" />
                              ) : (
                                <CopyIcon fontSize="small" />
                              )}
                            </IconButton>
                          </Box>
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                            {script.script_text}
                          </Typography>
                        </CardContent>
                      </Card>
                    ))}
                    {selectedHook && currentScripts.length === 0 && (
                      <Box sx={{ p: 3, textAlign: 'center' }}>
                        <Typography color="text.secondary">
                          No scripts available for this hook
                        </Typography>
                      </Box>
                    )}
                  </Stack>
                </Box>
              </Paper>
            </Slide>
          </Grid>
        </Grid>

        {/* Instructions */}
        {!selectedAngle && (
          <Box sx={{ mt: 4, p: 3, bgcolor: 'background.paper', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom color="primary">
              How to explore your content
            </Typography>
            <Typography variant="body2" color="text.secondary">
              1. Select a marketing angle from the left column<br />
              2. Choose a hook from the middle column<br />
              3. View and copy scripts from the right column<br />
              Click any text to copy it to your clipboard!
            </Typography>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default ContentLibrary;