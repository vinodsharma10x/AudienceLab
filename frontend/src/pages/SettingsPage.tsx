import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  Button,
  Divider,
  TextField,
  Alert,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
} from '@mui/material';
import {
  Notifications,
  Security,
  Palette,
  Language,
  Storage,
  Speed,
  Edit,
  Save,
  Cancel,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [saved, setSaved] = useState(false);
  const [editingEmail, setEditingEmail] = useState(false);
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [autoSave, setAutoSave] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [videoQuality, setVideoQuality] = useState('high');
  const [email, setEmail] = useState(user?.email || '');

  const handleSave = () => {
    // In a real app, this would save to backend
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <Box sx={{ backgroundColor: '#f5f5f5', minHeight: '100vh', py: 3 }}>
      <Container maxWidth="lg">
        {/* Header */}
        <Box mb={4}>
          <Box display="flex" alignItems="center" gap={2} mb={1}>
            <Typography variant="h4" fontWeight="bold">
              Settings
            </Typography>
            <Chip 
              label="Sample Content" 
              size="small" 
              color="info" 
              variant="outlined"
              sx={{ height: 24 }}
            />
          </Box>
          <Typography variant="body1" color="text.secondary">
            Manage your account settings and preferences
          </Typography>
        </Box>

        {saved && (
          <Alert severity="success" sx={{ mb: 3 }}>
            Settings saved successfully!
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Account Settings */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Security sx={{ mr: 1, color: '#1976d2' }} />
                  <Typography variant="h6">Account Settings</Typography>
                </Box>
                <Divider sx={{ mb: 3 }} />
                
                <List>
                  <ListItem>
                    <ListItemText 
                      primary="Email Address"
                      secondary={email}
                    />
                    <ListItemSecondaryAction>
                      {editingEmail ? (
                        <>
                          <IconButton onClick={() => setEditingEmail(false)} size="small">
                            <Save />
                          </IconButton>
                          <IconButton onClick={() => {
                            setEmail(user?.email || '');
                            setEditingEmail(false);
                          }} size="small">
                            <Cancel />
                          </IconButton>
                        </>
                      ) : (
                        <IconButton onClick={() => setEditingEmail(true)} size="small">
                          <Edit />
                        </IconButton>
                      )}
                    </ListItemSecondaryAction>
                  </ListItem>
                  
                  {editingEmail && (
                    <ListItem>
                      <TextField
                        fullWidth
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        size="small"
                        type="email"
                      />
                    </ListItem>
                  )}
                  
                  <ListItem>
                    <ListItemText 
                      primary="Account Type"
                      secondary="Pro Plan"
                    />
                    <Chip label="Active" color="success" size="small" />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemText 
                      primary="Member Since"
                      secondary="January 2024"
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* Notification Settings */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Notifications sx={{ mr: 1, color: '#1976d2' }} />
                  <Typography variant="h6">Notifications</Typography>
                </Box>
                <Divider sx={{ mb: 3 }} />
                
                <FormControlLabel
                  control={
                    <Switch 
                      checked={emailNotifications}
                      onChange={(e) => setEmailNotifications(e.target.checked)}
                    />
                  }
                  label="Email Notifications"
                />
                <Typography variant="caption" display="block" sx={{ ml: 6, mb: 2 }} color="text.secondary">
                  Receive updates about your campaigns via email
                </Typography>
                
                <FormControlLabel
                  control={<Switch defaultChecked />}
                  label="Campaign Completion Alerts"
                />
                <Typography variant="caption" display="block" sx={{ ml: 6, mb: 2 }} color="text.secondary">
                  Get notified when your video ads are ready
                </Typography>
                
                <FormControlLabel
                  control={<Switch defaultChecked />}
                  label="Performance Reports"
                />
                <Typography variant="caption" display="block" sx={{ ml: 6 }} color="text.secondary">
                  Weekly analytics summary
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Preferences */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Palette sx={{ mr: 1, color: '#1976d2' }} />
                  <Typography variant="h6">Preferences</Typography>
                </Box>
                <Divider sx={{ mb: 3 }} />
                
                <FormControlLabel
                  control={
                    <Switch 
                      checked={darkMode}
                      onChange={(e) => setDarkMode(e.target.checked)}
                    />
                  }
                  label="Dark Mode"
                />
                <Typography variant="caption" display="block" sx={{ ml: 6, mb: 2 }} color="text.secondary">
                  Switch to dark theme (coming soon)
                </Typography>
                
                <FormControlLabel
                  control={
                    <Switch 
                      checked={autoSave}
                      onChange={(e) => setAutoSave(e.target.checked)}
                    />
                  }
                  label="Auto-save"
                />
                <Typography variant="caption" display="block" sx={{ ml: 6, mb: 2 }} color="text.secondary">
                  Automatically save your work as you go
                </Typography>
                
                <Box mt={3}>
                  <Typography variant="subtitle2" gutterBottom>
                    <Language sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                    Language
                  </Typography>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    defaultValue="en"
                    SelectProps={{ native: true }}
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                  </TextField>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Performance Settings */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Speed sx={{ mr: 1, color: '#1976d2' }} />
                  <Typography variant="h6">Performance</Typography>
                </Box>
                <Divider sx={{ mb: 3 }} />
                
                <Typography variant="subtitle2" gutterBottom>
                  Video Generation Quality
                </Typography>
                <TextField
                  select
                  fullWidth
                  size="small"
                  value={videoQuality}
                  onChange={(e) => setVideoQuality(e.target.value)}
                  SelectProps={{ native: true }}
                  sx={{ mb: 2 }}
                >
                  <option value="low">Low (Faster)</option>
                  <option value="medium">Medium (Balanced)</option>
                  <option value="high">High (Best Quality)</option>
                </TextField>
                
                <Typography variant="subtitle2" gutterBottom sx={{ mt: 3 }}>
                  <Storage sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                  Storage Usage
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Box sx={{ 
                    width: '100%', 
                    height: 8, 
                    backgroundColor: '#e0e0e0', 
                    borderRadius: 4,
                    overflow: 'hidden'
                  }}>
                    <Box sx={{ 
                      width: '35%', 
                      height: '100%', 
                      backgroundColor: '#1976d2',
                    }} />
                  </Box>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  3.5 GB of 10 GB used
                </Typography>
                
                <Button 
                  variant="outlined" 
                  size="small" 
                  sx={{ mt: 2 }}
                >
                  Clear Cache
                </Button>
              </CardContent>
            </Card>
          </Grid>

          {/* API Keys */}
          <Grid size={12}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Security sx={{ mr: 1, color: '#1976d2' }} />
                  <Typography variant="h6">API Configuration</Typography>
                  <Chip label="Advanced" size="small" sx={{ ml: 2 }} />
                </Box>
                <Divider sx={{ mb: 3 }} />
                
                <Alert severity="warning" sx={{ mb: 2 }}>
                  API keys are managed by your system administrator. Contact support to update these settings.
                </Alert>
                
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="subtitle2" gutterBottom>OpenAI API</Typography>
                    <TextField
                      fullWidth
                      size="small"
                      value="sk-...xxxx"
                      disabled
                      InputProps={{ readOnly: true }}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="subtitle2" gutterBottom>Anthropic API</Typography>
                    <TextField
                      fullWidth
                      size="small"
                      value="sk-ant-...xxxx"
                      disabled
                      InputProps={{ readOnly: true }}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Save Button */}
        <Box mt={4} display="flex" justifyContent="flex-end">
          <Button 
            variant="contained" 
            size="large"
            onClick={handleSave}
            sx={{ px: 4 }}
          >
            Save Changes
          </Button>
        </Box>
      </Container>
    </Box>
  );
};

export default SettingsPage;