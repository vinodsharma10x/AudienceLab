import {
  ArrowBack,
  Campaign as CampaignIcon,
  ContentCopy,
  ExpandMore,
  Search,
  TrendingDown,
  TrendingUp
} from '@mui/icons-material';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Grid,
  IconButton,
  InputAdornment,
  Link,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography
} from '@mui/material';
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface MarketingAngle {
  angle_id: string;
  angle_number: number;
  angle_category: string;
  angle_concept: string;
  angle_type: 'positive' | 'negative';
}

interface HookItem {
  hook_id: string;
  hook_text: string;
  hook_category: string;
}

interface HooksByCategory {
  direct_question?: HookItem[];
  shocking_fact?: HookItem[];
  demonstration?: HookItem[];
  alarm_tension?: HookItem[];
  surprise_curiosity?: HookItem[];
  list_enumeration?: HookItem[];
  personal_story?: HookItem[];
}

interface AngleWithHooks {
  angle_id: string;
  angle_number: number;
  angle_category: string;
  angle_concept: string;
  angle_type: 'positive' | 'negative';
  hooks_by_category: HooksByCategory;
}

interface Script {
  script_id: string;
  content: string;
  cta?: string;
  hook_id?: string;
}

type TabValue = 'angles' | 'hooks' | 'scripts';

const ContentLibraryV2: React.FC = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { session } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [campaign, setCampaign] = useState<any>(null);
  const [angles, setAngles] = useState<AngleWithHooks[]>([]);
  const [scripts, setScripts] = useState<any[]>([]);

  const [activeTab, setActiveTab] = useState<TabValue>('angles');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'positive' | 'negative'>('all');
  const [selectedAngleId, setSelectedAngleId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (campaignId) {
      fetchCampaignContent();
    }
  }, [campaignId]);

  const fetchCampaignContent = async () => {
    if (!session?.access_token || !campaignId) return;

    try {
      setLoading(true);
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/video-ads-v4/campaign/${campaignId}`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch campaign content');
      }

      const data = await response.json();
      setCampaign(data);

      console.log('Campaign data:', data);
      console.log('Content:', data.content);

      // Parse content
      if (data.content?.hooks) {
        setAngles(Array.isArray(data.content.hooks) ? data.content.hooks : []);
      }
      if (data.content?.scripts) {
        // Scripts might be an object or array, normalize to array
        const scriptsData = data.content.scripts;
        if (Array.isArray(scriptsData)) {
          setScripts(scriptsData);
        } else if (scriptsData && typeof scriptsData === 'object') {
          // If it's an object, wrap it in an array
          setScripts([scriptsData]);
        } else {
          setScripts([]);
        }
      }
    } catch (err) {
      console.error('Error fetching campaign:', err);
      setError(err instanceof Error ? err.message : 'Failed to load campaign');
    } finally {
      setLoading(false);
    }
  };

  // Process hooks data
  const allHooks = useMemo(() => {
    const hooks: Array<{
      hook: HookItem;
      angle: AngleWithHooks;
      category: string;
      script?: any;
    }> = [];

    angles.forEach(angle => {
      const categories = angle.hooks_by_category || {};
      Object.entries(categories).forEach(([category, hooksList]) => {
        (hooksList as HookItem[])?.forEach(hook => {
          // Find script for this hook - check all scripts data
          let foundScript = null;

          // Scripts can be an array of script sets
          scripts.forEach((scriptSet: any) => {
            if (scriptSet.angles) {
              scriptSet.angles.forEach((angleData: any) => {
                if (angleData.angle_id === angle.angle_id && angleData.hooks) {
                  angleData.hooks.forEach((hookData: any) => {
                    if (hookData.selected_hook?.hook_id === hook.hook_id && hookData.scripts?.length > 0) {
                      foundScript = hookData.scripts[0]; // Get first script
                    }
                  });
                }
              });
            }
          });

          hooks.push({ hook, angle, category, script: foundScript });
        });
      });
    });

    return hooks;
  }, [angles, scripts]);

  // Filtered angles
  const filteredAngles = useMemo(() => {
    return angles.filter(angle => {
      if (typeFilter !== 'all' && angle.angle_type !== typeFilter) return false;
      if (searchQuery && !angle.angle_concept.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !angle.angle_category.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [angles, typeFilter, searchQuery]);

  // Filtered hooks
  const filteredHooks = useMemo(() => {
    return allHooks.filter(({ hook, angle, category }) => {
      if (selectedAngleId && angle.angle_id !== selectedAngleId) return false;
      if (searchQuery && !hook.hook_text.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [allHooks, selectedAngleId, searchQuery]);

  // Group filtered hooks by angle
  const groupedHooks = useMemo(() => {
    const grouped: Record<string, typeof filteredHooks> = {};
    filteredHooks.forEach(item => {
      if (!grouped[item.angle.angle_id]) {
        grouped[item.angle.angle_id] = [];
      }
      grouped[item.angle.angle_id].push(item);
    });
    return grouped;
  }, [filteredHooks]);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: TabValue) => {
    setActiveTab(newValue);
    setSearchQuery('');
    setSelectedAngleId(null);
  };

  const getHookCategoryLabel = (category: string) => {
    return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getHookCountForAngle = (angle: AngleWithHooks) => {
    let count = 0;
    Object.values(angle.hooks_by_category || {}).forEach(hooks => {
      count += (hooks as HookItem[])?.length || 0;
    });
    return count;
  };

  if (loading) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress size={60} />
        </Box>
      </Container>
    );
  }

  if (error || !campaign) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error">{error || 'Campaign not found'}</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/video-ads-v4/campaigns')} sx={{ mt: 2 }}>
          Back to Campaigns
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Breadcrumbs sx={{ mb: 2 }}>
          <Link
            component="button"
            variant="body2"
            onClick={() => navigate('/video-ads-v4/campaigns')}
            sx={{ cursor: 'pointer' }}
          >
            Product Research
          </Link>
          <Typography color="text.primary">{campaign.campaign_name}</Typography>
        </Breadcrumbs>

        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CampaignIcon sx={{ fontSize: 40, color: '#1976d2' }} />
              Marketing Research Library
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {campaign.campaign_name}
            </Typography>
          </Box>
          <Box>
            <Button
              startIcon={<ArrowBack />}
              onClick={() => navigate('/video-ads-v4/campaigns')}
              variant="outlined"
            >
              Back
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid xs={12} sm={4} {...({} as any)}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Marketing Angles
              </Typography>
              <Typography variant="h4">{angles.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid xs={12} sm={4} {...({} as any)}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Hooks Generated
              </Typography>
              <Typography variant="h4">{allHooks.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid xs={12} sm={4} {...({} as any)}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Scripts Created
              </Typography>
              <Typography variant="h4">{scripts.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label={`Angles (${filteredAngles.length})`} value="angles" />
          <Tab label={`Hooks (${filteredHooks.length})`} value="hooks" />
          <Tab label={`Scripts (${scripts.length})`} value="scripts" />
        </Tabs>

        {/* Filters */}
        <Box sx={{ p: 2, bgcolor: '#f5f5f5' }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              size="small"
              sx={{ flexGrow: 1, bgcolor: 'white' }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
            {activeTab === 'angles' && (
              <Stack direction="row" spacing={1}>
                <Chip
                  label="All"
                  onClick={() => setTypeFilter('all')}
                  color={typeFilter === 'all' ? 'primary' : 'default'}
                />
                <Chip
                  label="Positive"
                  onClick={() => setTypeFilter('positive')}
                  color={typeFilter === 'positive' ? 'success' : 'default'}
                  icon={<TrendingUp />}
                />
                <Chip
                  label="Negative"
                  onClick={() => setTypeFilter('negative')}
                  color={typeFilter === 'negative' ? 'error' : 'default'}
                  icon={<TrendingDown />}
                />
              </Stack>
            )}
            {activeTab === 'hooks' && selectedAngleId && (
              <Button
                size="small"
                onClick={() => setSelectedAngleId(null)}
                variant="outlined"
              >
                Clear Filter
              </Button>
            )}
          </Stack>
        </Box>
      </Paper>

      {/* Content Area */}
      {activeTab === 'angles' && (
        <Grid container spacing={3}>
          {filteredAngles.map((angle) => (
            <Grid xs={12} md={6} lg={4} key={angle.angle_id} {...({} as any)}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                    <Typography variant="h6" component="div">
                      Angle {angle.angle_number}
                    </Typography>
                    <Chip
                      size="small"
                      label={angle.angle_type}
                      color={angle.angle_type === 'positive' ? 'success' : 'error'}
                      icon={angle.angle_type === 'positive' ? <TrendingUp /> : <TrendingDown />}
                    />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                    {angle.angle_category}
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {angle.angle_concept.length > 200
                      ? `${angle.angle_concept.substring(0, 200)}...`
                      : angle.angle_concept}
                  </Typography>
                  <Typography variant="caption" color="primary">
                    {getHookCountForAngle(angle)} hooks generated
                  </Typography>
                </CardContent>
                <Box sx={{ p: 2, pt: 0 }}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={() => {
                      setSelectedAngleId(angle.angle_id);
                      setActiveTab('hooks');
                    }}
                  >
                    View Hooks
                  </Button>
                </Box>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {activeTab === 'hooks' && (
        <Box>
          {Object.entries(groupedHooks).map(([angleId, hooks]) => {
            const angle = hooks[0]?.angle;
            if (!angle) return null;

            // Group hooks by category
            const byCategory: Record<string, typeof hooks> = {};
            hooks.forEach(item => {
              if (!byCategory[item.category]) {
                byCategory[item.category] = [];
              }
              byCategory[item.category].push(item);
            });

            return (
              <Accordion key={angleId} defaultExpanded={selectedAngleId === angleId}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    <Typography variant="h6">
                      Angle {angle.angle_number}: {angle.angle_category}
                    </Typography>
                    <Chip
                      size="small"
                      label={angle.angle_type}
                      color={angle.angle_type === 'positive' ? 'success' : 'error'}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {hooks.length} hooks
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ pl: 2 }}>
                    {Object.entries(byCategory).map(([category, categoryHooks]) => (
                      <Box key={category} sx={{ mb: 3 }}>
                        <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 'bold' }}>
                          {getHookCategoryLabel(category)} ({categoryHooks.length})
                        </Typography>
                        {categoryHooks.map(({ hook }) => (
                          <Paper key={hook.hook_id} sx={{ p: 2, mb: 1, bgcolor: '#fafafa' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                              <Typography variant="body2" sx={{ flexGrow: 1, pr: 2 }}>
                                {hook.hook_text}
                              </Typography>
                              <Tooltip title={copiedId === hook.hook_id ? "Copied!" : "Copy"}>
                                <IconButton
                                  size="small"
                                  onClick={() => handleCopy(hook.hook_text, hook.hook_id)}
                                >
                                  <ContentCopy fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </Paper>
                        ))}
                      </Box>
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            );
          })}
        </Box>
      )}

      {activeTab === 'scripts' && (
        <Box>
          {scripts.length === 0 ? (
            <Alert severity="info">No scripts generated yet.</Alert>
          ) : (
            scripts.map((scriptData, scriptSetIndex) => (
              <Box key={scriptSetIndex}>
                {scriptData.angles?.map((angleData: any) => {
                  // Find the angle details
                  const angleDetails = angles.find(a => a.angle_id === angleData.angle_id);

                  // Group hooks by category
                  const hooksByCategory: Record<string, any[]> = {};
                  angleData.hooks?.forEach((hookData: any) => {
                    const category = hookData.selected_hook?.hook_category || 'Other';
                    if (!hooksByCategory[category]) {
                      hooksByCategory[category] = [];
                    }
                    hooksByCategory[category].push(hookData);
                  });

                  return (
                    <Accordion key={angleData.angle_id} defaultExpanded={scriptSetIndex === 0}>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Box sx={{ width: '100%' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                  
                            <Typography variant="h6">
                              Angle {angleData.angle_number}: {angleDetails?.angle_category || 'Marketing Angle vinod'}
                            </Typography>
                            {angleDetails && (
                              <Chip
                                size="small"
                                label={angleDetails.angle_type}
                                color={angleDetails.angle_type === 'positive' ? 'success' : 'error'}
                              />
                            )}
                            <Typography variant="caption" color="text.secondary">
                              {angleData.hooks?.length || 0} hooks
                            </Typography>
                          </Box>
                          {angleDetails?.angle_concept && (
                            <Typography variant="body2" color="text.secondary" sx={{ pr: 4, lineHeight: 1.5 }}>
                              {angleDetails.angle_concept}
                            </Typography>
                          )}
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box sx={{ pl: 2 }}>
                          {Object.entries(hooksByCategory).map(([category, categoryHooks]) => (
                            <Box key={category} sx={{ mb: 4 }}>
                              <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold' }}>
                                {getHookCategoryLabel(category)} ({categoryHooks.length})
                              </Typography>

                              {categoryHooks.map((hookData: any, hookIndex: number) => (
                                <Box key={hookData.selected_hook?.hook_id || hookIndex} sx={{ mb: 3, pb: 3, borderBottom: hookIndex < categoryHooks.length - 1 ? '1px solid #e0e0e0' : 'none' }}>
                                  {/* Hook */}
                                  <Typography variant="body2" sx={{ mb: 2, lineHeight: 1.6 }}>
                                    {hookData.selected_hook?.hook_text}
                                  </Typography>

                                  {/* Scripts */}
                                  {hookData.scripts?.map((script: any, scriptIndex: number) => (
                                    <Box key={script.script_id || scriptIndex} sx={{ mt: 2 }}>
                                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2, lineHeight: 1.6, color: 'text.secondary' }}>
                                        {script.content}
                                      </Typography>

                                      {script.cta && (
                                        <Box sx={{ bgcolor: '#e3f2fd', p: 1.5, borderRadius: 1, mt: 2 }}>
                                          <Typography variant="caption" color="primary" sx={{ display: 'block', mb: 0.5, fontWeight: 'bold' }}>
                                            Call to Action:
                                          </Typography>
                                          <Typography variant="body2">
                                            {script.cta}
                                          </Typography>
                                        </Box>
                                      )}
                                    </Box>
                                  ))}
                                </Box>
                              ))}
                            </Box>
                          ))}
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  );
                })}
              </Box>
            ))
          )}
        </Box>
      )}
    </Container>
  );
};

export default ContentLibraryV2;
