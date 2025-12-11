import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  TextField,
  Alert,
  Divider
} from '@mui/material';
import { Delete as DeleteIcon } from '@mui/icons-material';

const DataDeletion: React.FC = () => {
  const [email, setEmail] = useState('');
  const [reason, setReason] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In a real implementation, you would send this to your backend
    console.log('Data deletion request:', { email, reason });
    setSubmitted(true);
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Data Deletion Request
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Request deletion of your personal data from AudienceLab
        </Typography>
      </Box>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Your Right to Data Deletion
          </Typography>
          <Typography variant="body1" paragraph>
            You have the right to request that we delete your personal data. This includes:
          </Typography>
          <Box component="ul" sx={{ pl: 3, mb: 3 }}>
            <li>Your account information</li>
            <li>Connected Facebook account data</li>
            <li>Stored analytics and performance data</li>
            <li>Any other personal information we have collected</li>
          </Box>
          
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              <strong>Please note:</strong> Once your data is deleted, it cannot be recovered. 
              You will lose access to all your analytics data and will need to reconnect your 
              Facebook accounts if you decide to use our service again.
            </Typography>
          </Alert>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <DeleteIcon sx={{ mr: 1 }} />
            Submit Deletion Request
          </Typography>
          
          {submitted ? (
            <Alert severity="success">
              <Typography variant="h6" gutterBottom>
                Request Submitted Successfully
              </Typography>
              <Typography variant="body1">
                Your data deletion request has been received. We will process your request within 30 days 
                and send a confirmation email to {email} once completed.
              </Typography>
            </Alert>
          ) : (
            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Email Address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                helperText="Enter the email address associated with your account"
                sx={{ mb: 3 }}
              />
              
              <TextField
                fullWidth
                label="Reason for Deletion (Optional)"
                multiline
                rows={4}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                helperText="Help us improve by letting us know why you're deleting your data"
                sx={{ mb: 3 }}
              />
              
              <Button
                type="submit"
                variant="contained"
                color="error"
                size="large"
                startIcon={<DeleteIcon />}
                disabled={!email}
              >
                Submit Deletion Request
              </Button>
            </Box>
          )}

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Alternative: Manual Data Deletion
          </Typography>
          <Typography variant="body1" paragraph>
            You can also delete your data manually by:
          </Typography>
          <Box component="ol" sx={{ pl: 3 }}>
            <li>Logging into your AudienceLab account</li>
            <li>Going to Settings → Account Settings</li>
            <li>Clicking "Delete Account" at the bottom of the page</li>
            <li>Following the confirmation prompts</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Need Help?
          </Typography>
          <Typography variant="body1" paragraph>
            If you have questions about data deletion or need assistance, contact us at:
          </Typography>
          <Typography variant="body1">
            Email: privacy@audiencelab.io<br />
            Subject: Data Deletion Request
          </Typography>
        </CardContent>
      </Card>
    </Container>
  );
};

export default DataDeletion;
