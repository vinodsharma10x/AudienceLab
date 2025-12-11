import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCampaignId } from '../../utils/v3-migration';
import {
  Box,
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  Stack,
  Card,
  CardContent,
  Tooltip,
  Link
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Search as SearchIcon,
  Add as AddIcon,
  PlayArrow as PlayIcon,
  ContentCopy as CopyIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as InProgressIcon,
  Circle as CircleIcon,
  CheckCircleOutline as CompletedIcon,
  HourglassEmpty as PendingIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';

interface Campaign {
  id: string;
  conversation_id?: string; // Legacy support
  campaign_id: string; // V3 primary key
  campaign_name: string;
  current_step: number;
  status: string;
  created_at: string;
  updated_at: string;
  product_data?: {
    product_name?: string;
    target_audience?: string;
  };
}

const stepNames = [
  'Start',
  'URL',
  'Product',
  'Angles',
  'Hooks',
  'Scripts',
  'Voice',
  'Audio',
  'Video'
];

const stepRoutes = [
  '/video-ads-v2/import-from-url',
  '/video-ads-v2/import-from-url',
  '/video-ads-v2/product-info',
  '/video-ads-v2/marketing-angles',
  '/video-ads-v2/hooks',
  '/video-ads-v2/scripts',
  '/video-ads-v2/voice-actor',
  '/video-ads-v2/audio',
  '/video-ads-v2/video'
];

const CampaignsList: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [editingCampaignId, setEditingCampaignId] = useState<string | null>(null);
  const [editingCampaignName, setEditingCampaignName] = useState<string>('');

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    if (!session?.access_token) {
      console.log('❌ No session token available');
      setError('No authentication token available');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/video-ads-v2/campaigns`;
      console.log('🔍 Fetching campaigns from:', url);
      console.log('🔑 Using token:', session.access_token.substring(0, 20) + '...');

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('📡 Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Error:', errorText);
        throw new Error(`Failed to fetch campaigns: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('✅ Campaigns data received:', data);
      setCampaigns(data.campaigns || []);
    } catch (error: any) {
      console.error('❌ Error fetching campaigns:', error);
      setError(error.message || 'Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, campaign: Campaign) => {
    setAnchorEl(event.currentTarget);
    setSelectedCampaign(campaign);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedCampaign(null);
  };

  const handleResume = (campaign: Campaign) => {
    // Navigate to the current step with campaign_id (V3)
    const route = stepRoutes[campaign.current_step] || stepRoutes[0];
    const campaignId = campaign.campaign_id || campaign.conversation_id; // Support both formats
    navigate(route, { 
      state: { 
        campaignId: campaignId, // V3: Use campaignId
        conversationId: campaignId, // Legacy support
        resumeFromStep: campaign.current_step,
        campaignData: campaign
      } 
    });
    handleMenuClose();
  };

  const handleStepClick = (campaign: Campaign, stepIndex: number) => {
    // Navigate to specific step
    const route = stepRoutes[stepIndex];
    const campaignId = campaign.campaign_id || campaign.conversation_id;
    navigate(route, { 
      state: { 
        campaignId: campaignId,
        conversationId: campaignId,
        resumeFromStep: stepIndex,
        campaignData: campaign
      } 
    });
  };

  const getStepStatus = (campaign: Campaign, stepIndex: number) => {
    if (stepIndex < campaign.current_step) return 'completed';
    // If we're at the last step (8) and campaign is completed, mark it as completed
    if (stepIndex === 8 && campaign.current_step === 8 && campaign.status === 'completed') {
      return 'completed';
    }
    if (stepIndex === campaign.current_step) return 'current';
    return 'pending';
  };

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />;
      case 'current':
        return <CircleIcon sx={{ fontSize: 16, color: 'primary.main' }} />;
      default:
        return <CircleIcon sx={{ fontSize: 16, color: 'grey.400' }} />;
    }
  };

  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'current':
        return 'primary';
      default:
        return 'default';
    }
  };

  const getStepBgColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success.light';
      case 'current':
        return 'primary.light';
      default:
        return 'grey.100';
    }
  };

  const handleFork = async (campaign: Campaign, fromStep: number) => {
    if (!session?.access_token) {
      setError('No authentication token available');
      return;
    }

    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/campaign/fork`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            source_campaign_id: campaign.id,
            fork_from_step: fromStep,
            campaign_name: `${campaign.campaign_name} (Copy)`
          })
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fork campaign: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Navigate to the forked campaign at the specified step
      const route = stepRoutes[fromStep] || stepRoutes[0];
      const newCampaignId = data.new_campaign_id || data.new_conversation_id; // Support both formats
      navigate(route, { 
        state: { 
          campaignId: newCampaignId, // V3: Use campaignId
          conversationId: newCampaignId, // Legacy support
          resumeFromStep: fromStep,
          forkedFrom: campaign.id
        } 
      });
    } catch (error: any) {
      console.error('Error forking campaign:', error);
      setError(error.message || 'Failed to fork campaign');
    }
    handleMenuClose();
  };

  const handleNewCampaign = () => {
    navigate('/video-ads-v2/import-from-url');
  };

  const handleEditCampaignName = (campaign: Campaign) => {
    setEditingCampaignId(campaign.id);
    setEditingCampaignName(campaign.campaign_name);
  };

  const handleCancelEdit = () => {
    setEditingCampaignId(null);
    setEditingCampaignName('');
  };

  const handleSaveCampaignName = async (campaign: Campaign) => {
    if (!session?.access_token || !editingCampaignName.trim()) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const campaignId = campaign.campaign_id || campaign.conversation_id || campaign.id;
      
      const response = await fetch(`${apiUrl}/video-ads-v2/campaign/${campaignId}/name`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          campaign_name: editingCampaignName.trim()
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to update campaign name: ${response.statusText}`);
      }

      // Update the campaign in the local state
      setCampaigns(prev => prev.map(c => 
        c.id === campaign.id 
          ? { ...c, campaign_name: editingCampaignName.trim() }
          : c
      ));

      setEditingCampaignId(null);
      setEditingCampaignName('');
    } catch (error: any) {
      console.error('Error updating campaign name:', error);
      setError(error.message || 'Failed to update campaign name');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'in_progress':
        return 'warning';
      case 'draft':
        return 'default';
      default:
        return 'default';
    }
  };

  const getStepProgress = (currentStep: number) => {
    return Math.round((currentStep / 8) * 100);
  };

  const filteredCampaigns = campaigns.filter(campaign =>
    campaign.campaign_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    campaign.product_data?.product_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Video Ad Campaigns
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage your video ad creation campaigns
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search campaigns..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleNewCampaign}
          sx={{ minWidth: 200 }}
        >
          New Campaign
        </Button>
        <IconButton onClick={fetchCampaigns} color="primary" title="Refresh campaigns">
          <RefreshIcon />
        </IconButton>
      </Stack>

      {filteredCampaigns.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h6" gutterBottom>
              No campaigns found
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              {searchTerm ? 'Try adjusting your search' : 'Create your first campaign to get started'}
            </Typography>
            {!searchTerm && (
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleNewCampaign}
              >
                Create First Campaign
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper} sx={{ boxShadow: 2 }}>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: 'grey.50' }}>
                <TableCell sx={{ fontWeight: 'bold' }}>Campaign</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Workflow Steps</TableCell>
                <TableCell align="center" sx={{ fontWeight: 'bold' }}>Progress</TableCell>
                <TableCell align="center" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredCampaigns.map((campaign) => (
                <TableRow key={campaign.id} hover>
                  <TableCell sx={{ width: '25%' }}>
                    <Box>
                      {editingCampaignId === campaign.id ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <TextField
                            size="small"
                            value={editingCampaignName}
                            onChange={(e) => setEditingCampaignName(e.target.value)}
                            onKeyPress={(e) => {
                              if (e.key === 'Enter') {
                                handleSaveCampaignName(campaign);
                              } else if (e.key === 'Escape') {
                                handleCancelEdit();
                              }
                            }}
                            autoFocus
                            sx={{ flexGrow: 1 }}
                          />
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleSaveCampaignName(campaign)}
                            disabled={!editingCampaignName.trim()}
                          >
                            <SaveIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={handleCancelEdit}
                          >
                            <CancelIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {campaign.campaign_name || 'Untitled Campaign'}
                          </Typography>
                          <IconButton
                            size="small"
                            onClick={() => handleEditCampaignName(campaign)}
                            sx={{ opacity: 0.7, '&:hover': { opacity: 1 } }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      )}
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                        {campaign.product_data?.product_name || 'No product'}
                      </Typography>
                      <Typography variant="caption" color="text.disabled">
                        Created: {new Date(campaign.created_at).toLocaleDateString()}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ width: '50%' }}>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, py: 1 }}>
                      {stepNames.slice(1).map((stepName, index) => {
                        const stepIndex = index + 1; // Skip 'Start' step
                        const status = getStepStatus(campaign, stepIndex);
                        const isClickable = stepIndex <= campaign.current_step;
                        
                        return (
                          <Tooltip key={stepIndex} title={isClickable ? `Go to ${stepName}` : `${stepName} (not available yet)`}>
                            <Chip
                              icon={getStepIcon(status)}
                              label={stepName}
                              color={getStepColor(status) as any}
                              variant={status === 'current' ? 'filled' : 'outlined'}
                              size="medium"
                              onClick={isClickable ? () => handleStepClick(campaign, stepIndex) : undefined}
                              sx={{
                                cursor: isClickable ? 'pointer' : 'not-allowed',
                                opacity: status === 'pending' ? 0.5 : 1,
                                bgcolor: status === 'completed' ? 'success.50' : 
                                        status === 'current' ? 'primary.50' : 
                                        'transparent',
                                borderWidth: status === 'current' ? 2 : 1,
                                '&:hover': isClickable ? {
                                  transform: 'translateY(-2px)',
                                  boxShadow: 2,
                                  bgcolor: status === 'completed' ? 'success.100' : 
                                          status === 'current' ? 'primary.100' : 
                                          'grey.50',
                                } : {},
                                transition: 'all 0.2s ease',
                                fontWeight: status === 'current' ? 'bold' : 'medium',
                                minWidth: '80px',
                              }}
                            />
                          </Tooltip>
                        );
                      })}
                    </Box>
                  </TableCell>
                  <TableCell align="center" sx={{ width: '15%' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <Box sx={{ position: 'relative', display: 'inline-flex', mb: 1 }}>
                        <CircularProgress 
                          variant="determinate" 
                          value={getStepProgress(campaign.current_step)}
                          size={50}
                          thickness={4}
                          color={campaign.status === 'completed' ? 'success' : 'primary'}
                        />
                        <Box
                          sx={{
                            top: 0,
                            left: 0,
                            bottom: 0,
                            right: 0,
                            position: 'absolute',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Typography variant="body2" fontWeight="bold">
                            {getStepProgress(campaign.current_step)}%
                          </Typography>
                        </Box>
                      </Box>
                      <Chip
                        label={campaign.status === 'completed' ? 'Completed' : 'In Progress'}
                        size="small"
                        color={campaign.status === 'completed' ? 'success' : 'warning'}
                        sx={{ fontSize: '0.7rem' }}
                      />
                    </Box>
                  </TableCell>
                  <TableCell align="center" sx={{ width: '10%' }}>
                    <Stack direction="row" spacing={1} justifyContent="center">
                      <Tooltip title="Resume from current step">
                        <IconButton
                          color="primary"
                          onClick={() => handleResume(campaign)}
                          sx={{ 
                            bgcolor: 'primary.light',
                            color: 'white',
                            '&:hover': {
                              bgcolor: 'primary.main',
                            }
                          }}
                        >
                          <PlayIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="More options">
                        <IconButton
                          onClick={(e) => handleMenuOpen(e, campaign)}
                        >
                          <MoreVertIcon />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => selectedCampaign && handleResume(selectedCampaign)}>
          <PlayIcon fontSize="small" sx={{ mr: 1 }} />
          Resume Campaign
        </MenuItem>
        <MenuItem onClick={() => selectedCampaign && handleFork(selectedCampaign, selectedCampaign.current_step)}>
          <CopyIcon fontSize="small" sx={{ mr: 1 }} />
          Fork from Current Step
        </MenuItem>
        <MenuItem onClick={() => selectedCampaign && handleFork(selectedCampaign, 2)}>
          <CopyIcon fontSize="small" sx={{ mr: 1 }} />
          Fork from Product Info
        </MenuItem>
        <MenuItem onClick={() => selectedCampaign && handleFork(selectedCampaign, 3)}>
          <CopyIcon fontSize="small" sx={{ mr: 1 }} />
          Fork from Marketing Analysis
        </MenuItem>
      </Menu>
    </Container>
  );
};

export default CampaignsList;