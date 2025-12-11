import React from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Divider
} from '@mui/material';

const PrivacyPolicy: React.FC = () => {
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Privacy Policy
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Last updated: {new Date().toLocaleDateString()}
        </Typography>
      </Box>

      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            1. Information We Collect 
          </Typography>
          <Typography variant="body1" paragraph>
            AudienceLab ("we," "our," or "us") collects information you provide directly to us, such as when you create an account, use our services, or contact us for support.
          </Typography>
          
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Facebook Data
          </Typography>
          <Typography variant="body1" paragraph>
            When you connect your Facebook account, we collect:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>Your Facebook profile information (name, email)</li>
            <li>Ad account data and performance metrics</li>
            <li>Campaign and ad set information</li>
            <li>Analytics and insights data</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            2. How We Use Your Information
          </Typography>
          <Typography variant="body1" paragraph>
            We use the information we collect to:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>Provide, maintain, and improve our services</li>
            <li>Generate analytics and reporting for your Facebook ad campaigns</li>
            <li>Sync and analyze your advertising performance data</li>
            <li>Communicate with you about our services</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            3. Information Sharing and Disclosure
          </Typography>
          <Typography variant="body1" paragraph>
            We do not sell, trade, or otherwise transfer your personal information to third parties without your consent, except as described in this policy. We may share information in the following circumstances:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>With your explicit consent</li>
            <li>To comply with legal obligations</li>
            <li>To protect our rights and safety</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            4. Data Security
          </Typography>
          <Typography variant="body1" paragraph>
            We implement appropriate security measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction. Your Facebook access tokens are encrypted and stored securely.
          </Typography>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            5. Data Retention
          </Typography>
          <Typography variant="body1" paragraph>
            We retain your information only as long as necessary to provide our services and as required by law. You can request deletion of your data at any time.
          </Typography>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            6. Your Rights
          </Typography>
          <Typography variant="body1" paragraph>
            You have the right to:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>Access your personal information</li>
            <li>Correct inaccurate information</li>
            <li>Request deletion of your information</li>
            <li>Disconnect your Facebook account at any time</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            7. Contact Us
          </Typography>
          <Typography variant="body1" paragraph>
            If you have questions about this Privacy Policy, please contact us at:
          </Typography>
          <Typography variant="body1">
            Email: privacy@audiencelab.io<br />
            Address: [Your Company Address]
          </Typography>
        </CardContent>
      </Card>
    </Container>
  );
};

export default PrivacyPolicy;
