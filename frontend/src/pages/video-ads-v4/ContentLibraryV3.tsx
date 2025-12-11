import React, { useState, useEffect, useMemo } from 'react';
import {
  Container,
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  TextField,
  InputAdornment,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  Alert,
  CircularProgress,
  Breadcrumbs,
  Link,
  Stack,
} from '@mui/material';
import {
  Search,
  ExpandMore,
  ArrowBack,
  TrendingUp,
  TrendingDown,
  Campaign as CampaignIcon
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface AngleData {
  angle_id: string;
  angle_number: number;
  angle_category?: string;
  angle_concept?: string;
  angle_type?: 'positive' | 'negative';
  hooks?: HookData[];
}

interface HookData {
  selected_hook?: {
    hook_id: string;
    hook_text: string;
    hook_category: string;
  };
  scripts?: ScriptData[];
}

interface ScriptData {
  script_id?: string;
  content: string;
  cta?: string;
}

const ContentLibraryV3: React.FC = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { session } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [campaign, setCampaign] = useState<any>(null);
  const [anglesData, setAnglesData] = useState<any[]>([]);
  const [scriptsData, setScriptsData] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'positive' | 'negative'>('all');

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
      console.log('Hooks (angles with details):', data.content?.hooks);
      console.log('Scripts:', data.content?.scripts);

      // Load angle details from hooks (contains angle info + hook details)
      if (data.content?.hooks) {
        const angles = Array.isArray(data.content.hooks) ? data.content.hooks : [];
        setAnglesData(angles);
        console.log('Loaded angles data:', angles);
      }

      // Load scripts data (contains scripts organized by angle/hook)
      if (data.content?.scripts) {
        const scripts = data.content.scripts;
        if (Array.isArray(scripts)) {
          setScriptsData(scripts);
        } else if (scripts && typeof scripts === 'object') {
          setScriptsData([scripts]);
        } else {
          setScriptsData([]);
        }
        console.log('Loaded scripts data:', scripts);
      }
    } catch (err) {
      console.error('Error fetching campaign:', err);
      setError(err instanceof Error ? err.message : 'Failed to load campaign');
    } finally {
      setLoading(false);
    }
  };

  // Use scriptsData as base structure, enrich with details from anglesData
  const allAngles = useMemo(() => {
    console.log('Computing allAngles - scriptsData:', scriptsData, 'anglesData:', anglesData);

    // Create lookup maps from anglesData for quick access
    const angleDetailsMap: Record<string, any> = {};
    const hookDetailsMap: Record<string, any> = {};

    anglesData.forEach((angleData: any) => {
      const angleId = angleData.angle_id;

      // Store angle details
      angleDetailsMap[angleId] = {
        angle_category: angleData.angle_category,
        angle_concept: angleData.angle_concept,
        angle_type: angleData.angle_type
      };

      // Flatten hooks_by_category into hookDetailsMap
      if (angleData.hooks_by_category) {
        Object.values(angleData.hooks_by_category).forEach((categoryHooks: any) => {
          if (Array.isArray(categoryHooks)) {
            categoryHooks.forEach((hook: any) => {
              if (hook.hook_id) {
                hookDetailsMap[hook.hook_id] = {
                  hook_text: hook.hook_text,
                  hook_category: hook.hook_category
                };
              }
            });
          }
        });
      }
    });

    console.log('Built angleDetailsMap:', angleDetailsMap);
    console.log('Built hookDetailsMap:', hookDetailsMap);

    // Enrich scriptsData with details from maps
    const enrichedAngles: AngleData[] = [];

    scriptsData.forEach((scriptSet: any) => {
      if (scriptSet.angles && Array.isArray(scriptSet.angles)) {
        scriptSet.angles.forEach((scriptAngle: any) => {
          const angleId = scriptAngle.angle_id;
          const angleDetails = angleDetailsMap[angleId] || {};

          // Enrich hooks with hook details
          const enrichedHooks: HookData[] = (scriptAngle.hooks || []).map((hookData: any) => {
            const hookId = hookData.selected_hook?.hook_id;
            const hookDetails = hookDetailsMap[hookId] || {};

            return {
              selected_hook: {
                hook_id: hookId,
                hook_text: hookDetails.hook_text || hookId,
                hook_category: hookDetails.hook_category || 'other'
              },
              scripts: hookData.scripts || []
            };
          });

          enrichedAngles.push({
            angle_id: angleId,
            angle_number: scriptAngle.angle_number,
            angle_category: angleDetails.angle_category || 'Marketing Angle',
            angle_concept: angleDetails.angle_concept || '',
            angle_type: angleDetails.angle_type || 'positive',
            hooks: enrichedHooks
          });
        });
      }
    });

    // Sort angles by angle_number numerically
    enrichedAngles.sort((a, b) => a.angle_number - b.angle_number);

    console.log('Enriched angles (sorted):', enrichedAngles);
    return enrichedAngles;
  }, [anglesData, scriptsData]);

  // Calculate stats
  const stats = useMemo(() => {
    let totalHooks = 0;
    let totalScripts = 0;

    allAngles.forEach(angle => {
      const hooksCount = angle.hooks?.length || 0;
      totalHooks += hooksCount;

      angle.hooks?.forEach(hookData => {
        totalScripts += hookData.scripts?.length || 0;
      });
    });

    return {
      angles: allAngles.length,
      hooks: totalHooks,
      scripts: totalScripts
    };
  }, [allAngles]);

  // Filtered angles
  const filteredAngles = useMemo(() => {
    return allAngles.filter(angle => {
      // Type filter
      if (typeFilter !== 'all' && angle.angle_type !== typeFilter) return false;

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesCategory = angle.angle_category?.toLowerCase().includes(query);
        const matchesConcept = angle.angle_concept?.toLowerCase().includes(query);
        const matchesHook = angle.hooks?.some(h =>
          h.selected_hook?.hook_text.toLowerCase().includes(query)
        );
        const matchesScript = angle.hooks?.some(h =>
          h.scripts?.some(s => s.content.toLowerCase().includes(query))
        );

        return matchesCategory || matchesConcept || matchesHook || matchesScript;
      }

      return true;
    });
  }, [allAngles, typeFilter, searchQuery]);

  const getHookCategoryLabel = (category: string) => {
    return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
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

  if (allAngles.length === 0) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="info">
          No content generated yet. Please wait for the campaign processing to complete.
        </Alert>
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
              BACK
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
              <Typography variant="h4">{stats.angles}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid xs={12} sm={4} {...({} as any)}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Hooks Generated
              </Typography>
              <Typography variant="h4">{stats.hooks}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid xs={12} sm={4} {...({} as any)}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Scripts Created
              </Typography>
              <Typography variant="h4">{stats.scripts}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <TextField
            placeholder="Search angles, hooks, or scripts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="small"
            sx={{ flexGrow: 1, minWidth: 300 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
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
        </Stack>
      </Paper>

      {/* Content */}
      <Box>
        {filteredAngles.length === 0 ? (
          <Alert severity="info">No content matches your search criteria.</Alert>
        ) : (
          filteredAngles.map((angle, angleIndex) => {
            // Group hooks by category
            const hooksByCategory: Record<string, HookData[]> = {};
            angle.hooks?.forEach((hookData) => {
              const category = hookData.selected_hook?.hook_category || 'Other';
              if (!hooksByCategory[category]) {
                hooksByCategory[category] = [];
              }
              hooksByCategory[category].push(hookData);
            });

            return (
              <Accordion key={angle.angle_id || angleIndex} defaultExpanded={angleIndex === 0}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ width: '100%' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                      <Typography variant="h6">
                        Angle {angle.angle_number}: {angle.angle_category || 'Marketing Angle'}
                      </Typography>
                      {angle.angle_type && (
                        <Chip
                          size="small"
                          label={angle.angle_type}
                          color={angle.angle_type === 'positive' ? 'success' : 'error'}
                        />
                      )}
                      <Typography variant="caption" color="text.secondary">
                        {angle.hooks?.length || 0} hooks
                      </Typography>
                    </Box>
                    {angle.angle_concept && (
                      <Typography variant="body2" color="text.secondary" sx={{ pr: 4, lineHeight: 1.5 }}>
                        {angle.angle_concept}
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

                        {categoryHooks.map((hookData, hookIndex) => (
                          <Box
                            key={hookData.selected_hook?.hook_id || hookIndex}
                            sx={{
                              mb: 3,
                              pb: 3,
                              borderBottom: hookIndex < categoryHooks.length - 1 ? '1px solid #e0e0e0' : 'none'
                            }}
                          >
                            {/* Hook */}
                            <Typography variant="body2" sx={{ mb: 2, lineHeight: 1.6, fontWeight: 500 }}>
                              {hookData.selected_hook?.hook_text}
                            </Typography>

                            {/* Scripts */}
                            {hookData.scripts?.map((script, scriptIndex) => (
                              <Box key={script.script_id || scriptIndex} sx={{ mt: 2 }}>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    whiteSpace: 'pre-wrap',
                                    mb: 2,
                                    lineHeight: 1.6,
                                    color: 'text.secondary'
                                  }}
                                >
                                  {script.content}
                                </Typography>

                                {script.cta && (
                                  <Box sx={{ bgcolor: '#e3f2fd', p: 1.5, borderRadius: 1, mt: 2 }}>
                                    <Typography
                                      variant="caption"
                                      color="primary"
                                      sx={{ display: 'block', mb: 0.5, fontWeight: 'bold' }}
                                    >
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
          })
        )}
      </Box>
    </Container>
  );
};

export default ContentLibraryV3;
