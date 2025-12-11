import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface Campaign {
  campaign_id: string;
  campaign_name: string;
  status: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

const CampaignList: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { session } = useAuth();

  const fetchCampaigns = async () => {
    try {
      const token = session?.access_token;
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${process.env.REACT_APP_API_URL}/video-ads-v4/campaigns`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch campaigns');
      }

      const data = await response.json();
      // Backend returns campaigns array directly, not wrapped
      setCampaigns(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      console.error('Error fetching campaigns:', err);
      setError(err instanceof Error ? err.message : 'Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const getStatusChip = (status: string) => {
    const statusConfig: Record<string, { color: 'default' | 'warning' | 'info' | 'success' | 'error', label: string }> = {
      'draft': { color: 'default', label: 'Draft' },
      'pending': { color: 'warning', label: 'Starting...' },
      'processing': { color: 'info', label: 'Processing...' },
      'analyzing_avatar': { color: 'info', label: 'Analyzing Target Audience' },
      'analyzing_journey': { color: 'info', label: 'Mapping Customer Journey' },
      'analyzing_objections': { color: 'info', label: 'Analyzing Objections' },
      'generating_angles': { color: 'info', label: 'Generating Marketing Angles' },
      'generating_hooks': { color: 'info', label: 'Generating Hooks' },
      'generating_scripts': { color: 'info', label: 'Generating Scripts' },
      'completed': { color: 'success', label: 'Complete' },
      'complete': { color: 'success', label: 'Complete' },
      'failed': { color: 'error', label: 'Failed' },
    };

    const config = statusConfig[status] || { color: 'default' as const, label: status };
    return <Chip label={config.label} color={config.color} size="small" />;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const handleView = (campaignId: string) => {
    navigate(`/video-ads-v4/library-v3/${campaignId}`);
  };

  const handleCreateNew = () => {
    navigate('/video-ads-v4/import');
  };

  if (loading && campaigns.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Product Research</Typography>
        <Button variant="contained" color="primary" onClick={handleCreateNew}>
          New Research
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Product Name</strong></TableCell>
              <TableCell><strong>Status</strong></TableCell>
              <TableCell><strong>Created</strong></TableCell>
              <TableCell><strong>Last Updated</strong></TableCell>
              <TableCell align="right"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {campaigns.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    No research yet. Click "New Research" to get started!
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              campaigns.map((campaign) => (
                <TableRow key={campaign.campaign_id} hover>
                  <TableCell>{campaign.campaign_name}</TableCell>
                  <TableCell>{getStatusChip(campaign.status)}</TableCell>
                  <TableCell>{formatDate(campaign.created_at)}</TableCell>
                  <TableCell>{formatDate(campaign.updated_at)}</TableCell>
                  <TableCell align="right">
                    {(campaign.status === 'complete' || campaign.status === 'completed') && (
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => handleView(campaign.campaign_id)}
                      >
                        View
                      </Button>
                    )}
                    {campaign.status === 'failed' && campaign.error_message && (
                      <Typography variant="caption" color="error" sx={{ display: 'block', mb: 1 }}>
                        Error: {campaign.error_message.substring(0, 50)}...
                      </Typography>
                    )}
                    {(campaign.status === 'pending' || campaign.status === 'processing' ||
                      campaign.status === 'analyzing_avatar' || campaign.status === 'analyzing_journey' ||
                      campaign.status === 'analyzing_objections' || campaign.status === 'generating_angles' ||
                      campaign.status === 'generating_hooks' || campaign.status === 'generating_scripts') && (
                      <CircularProgress size={20} />
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default CampaignList;
