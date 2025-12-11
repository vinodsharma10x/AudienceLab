import React from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Paper,
  Alert,
  Stack
} from '@mui/material';
import {
  CloudOff,
  Refresh,
  Construction,
  WifiOff
} from '@mui/icons-material';

interface ServerErrorProps {
  onRetry?: () => void;
  message?: string;
  showDetails?: boolean;
}

const ServerError: React.FC<ServerErrorProps> = ({ 
  onRetry, 
  message = "Unable to connect to server",
  showDetails = true 
}) => {
  return (
    <Container maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Paper 
        elevation={3} 
        sx={{ 
          p: 6, 
          textAlign: 'center',
          background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)'
        }}
      >
        <Box sx={{ mb: 3 }}>
          <CloudOff 
            sx={{ 
              fontSize: 80, 
              color: 'text.secondary',
              opacity: 0.5,
              mb: 2
            }} 
          />
        </Box>

        <Typography 
          variant="h4" 
          gutterBottom 
          sx={{ fontWeight: 600, color: 'text.primary' }}
        >
          Server Connection Error
        </Typography>

        <Typography 
          variant="h6" 
          color="text.secondary" 
          sx={{ mb: 3 }}
        >
          {message}
        </Typography>

        {showDetails && (
          <Alert 
            severity="info" 
            sx={{ 
              mb: 3, 
              maxWidth: 500, 
              mx: 'auto',
              textAlign: 'left' 
            }}
          >
            <Typography variant="body2" gutterBottom>
              <strong>This could be because:</strong>
            </Typography>
            <Stack spacing={1} sx={{ mt: 1 }}>
              <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <WifiOff fontSize="small" /> The backend server is not running
              </Typography>
              <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Construction fontSize="small" /> The server is being updated or maintained
              </Typography>
              <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CloudOff fontSize="small" /> Network connectivity issues
              </Typography>
            </Stack>
          </Alert>
        )}

        <Stack direction="row" spacing={2} justifyContent="center" sx={{ mt: 4 }}>
          {onRetry && (
            <Button
              variant="contained"
              startIcon={<Refresh />}
              onClick={onRetry}
              size="large"
              sx={{
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                '&:hover': {
                  background: 'linear-gradient(45deg, #1976D2 30%, #0288D1 90%)',
                }
              }}
            >
              Try Again
            </Button>
          )}
          
          <Button
            variant="outlined"
            onClick={() => window.location.href = '/'}
            size="large"
          >
            Go to Home
          </Button>
        </Stack>

        <Box sx={{ mt: 4, pt: 3, borderTop: '1px solid', borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary">
            If this problem persists, please ensure the backend server is running with:
          </Typography>
          <Paper 
            sx={{ 
              mt: 1, 
              p: 1, 
              bgcolor: 'grey.900',
              display: 'inline-block'
            }}
          >
            <Typography 
              variant="body2" 
              sx={{ 
                fontFamily: 'monospace',
                color: 'lime'
              }}
            >
              cd backend && python main.py
            </Typography>
          </Paper>
        </Box>
      </Paper>
    </Container>
  );
};

export default ServerError;