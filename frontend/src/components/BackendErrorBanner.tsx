import React from 'react';
import { Alert, AlertTitle, Button, Box } from '@mui/material';
import { Refresh, Warning } from '@mui/icons-material';

interface BackendErrorBannerProps {
  onRetry?: () => void;
  compact?: boolean;
}

const BackendErrorBanner: React.FC<BackendErrorBannerProps> = ({ 
  onRetry, 
  compact = false 
}) => {
  if (compact) {
    return (
      <Alert 
        severity="error" 
        sx={{ mb: 2 }}
        action={
          onRetry && (
            <Button color="inherit" size="small" onClick={onRetry}>
              Retry
            </Button>
          )
        }
      >
        Backend server is not responding. Please ensure it's running.
      </Alert>
    );
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Alert 
        severity="error"
        icon={<Warning fontSize="large" />}
        action={
          onRetry && (
            <Button 
              color="inherit" 
              size="small" 
              startIcon={<Refresh />}
              onClick={onRetry}
              sx={{ mt: 1 }}
            >
              Try Again
            </Button>
          )
        }
      >
        <AlertTitle>Connection Error</AlertTitle>
        Cannot connect to the backend server. Please ensure the server is running with:
        <Box 
          component="code" 
          sx={{ 
            display: 'block',
            mt: 1,
            p: 1,
            bgcolor: 'grey.900',
            color: 'lime',
            borderRadius: 1,
            fontSize: '0.875rem',
            fontFamily: 'monospace'
          }}
        >
          cd backend && python main.py
        </Box>
      </Alert>
    </Box>
  );
};

export default BackendErrorBanner;