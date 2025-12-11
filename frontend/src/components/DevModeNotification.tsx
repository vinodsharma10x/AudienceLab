import React, { useState, useEffect } from 'react';
import { Alert, Snackbar, Box, Button } from '@mui/material';
import { Info } from '@mui/icons-material';

interface DevModeNotificationProps {
  show?: boolean;
}

const DevModeNotification: React.FC<DevModeNotificationProps> = ({ show = true }) => {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    // Only check dev mode in development environment
    if (process.env.NODE_ENV === 'production') {
      return; // Don't show dev mode notification in production
    }

    // Check if we're in development mode (Supabase not connected)
    const checkDevMode = async () => {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/health`);
        if (response.ok) {
          const data = await response.json();
          if (!data.supabase_connected && show) {
            setOpen(true);
          }
        }
      } catch (error) {
        console.log('Backend not available');
      }
    };

    checkDevMode();
  }, [show]);

  const handleClose = () => {
    setOpen(false);
  };

  const handleDevLogin = async () => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/auth/dev-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        window.location.reload(); // Reload to trigger auth state change
      }
    } catch (error) {
      console.error('Dev login failed:', error);
    }
  };

  return (
    <Snackbar
      open={open}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      sx={{ mt: 2 }}
    >
      <Alert 
        severity="info" 
        onClose={handleClose}
        icon={<Info />}
        sx={{ 
          minWidth: '400px',
          '& .MuiAlert-action': {
            alignItems: 'flex-start',
            pt: 0
          }
        }}
        action={
          <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
            <Button 
              size="small" 
              variant="outlined" 
              onClick={handleDevLogin}
              sx={{ fontSize: '0.75rem' }}
            >
              Quick Login
            </Button>
          </Box>
        }
      >
        <Box>
          <strong>Development Mode</strong>
          <br />
          Supabase authentication is not configured. Using development mode for testing.
        </Box>
      </Alert>
    </Snackbar>
  );
};

export default DevModeNotification;
