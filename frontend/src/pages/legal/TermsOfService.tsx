import React from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Divider
} from '@mui/material';

const TermsOfService: React.FC = () => {
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Terms of Service
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Last updated: {new Date().toLocaleDateString()}
        </Typography>
      </Box>

      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            1. Acceptance of Terms
          </Typography>
          <Typography variant="body1" paragraph>
            By accessing and using AudienceLab ("Service"), you accept and agree to be bound by the terms and provision of this agreement.
          </Typography>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            2. Description of Service
          </Typography>
          <Typography variant="body1" paragraph>
            AudienceLab is a marketing research and content generation platform that provides:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>Facebook ad account integration and management</li>
            <li>Performance analytics and reporting</li>
            <li>Automated data synchronization</li>
            <li>Campaign insights and metrics</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            3. User Accounts
          </Typography>
          <Typography variant="body1" paragraph>
            To use our Service, you must:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>Create an account with accurate information</li>
            <li>Maintain the security of your login credentials</li>
            <li>Have valid Facebook ad accounts to connect</li>
            <li>Comply with Facebook's terms of service</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            4. Acceptable Use
          </Typography>
          <Typography variant="body1" paragraph>
            You agree not to:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>Use the Service for any unlawful purposes</li>
            <li>Attempt to gain unauthorized access to our systems</li>
            <li>Interfere with or disrupt the Service</li>
            <li>Violate any applicable laws or regulations</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            5. Facebook Integration
          </Typography>
          <Typography variant="body1" paragraph>
            By connecting your Facebook account, you acknowledge that:
          </Typography>
          <Box component="ul" sx={{ pl: 3 }}>
            <li>You have the right to authorize access to your Facebook data</li>
            <li>You comply with Facebook's Platform Policy</li>
            <li>We will access only the data necessary for our services</li>
            <li>You can disconnect your account at any time</li>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            6. Data and Privacy
          </Typography>
          <Typography variant="body1" paragraph>
            Your privacy is important to us. Please review our Privacy Policy, which also governs your use of the Service, to understand our practices.
          </Typography>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            7. Service Availability
          </Typography>
          <Typography variant="body1" paragraph>
            We strive to maintain service availability but do not guarantee uninterrupted access. We may modify, suspend, or discontinue the Service at any time.
          </Typography>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            8. Limitation of Liability
          </Typography>
          <Typography variant="body1" paragraph>
            To the maximum extent permitted by law, AudienceLab shall not be liable for any indirect, incidental, special, consequential, or punitive damages.
          </Typography>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            9. Termination
          </Typography>
          <Typography variant="body1" paragraph>
            We may terminate or suspend your account and access to the Service immediately, without prior notice, for conduct that we believe violates these Terms.
          </Typography>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" gutterBottom>
            10. Contact Information
          </Typography>
          <Typography variant="body1" paragraph>
            If you have questions about these Terms, please contact us at:
          </Typography>
          <Typography variant="body1">
            Email: support@audiencelab.io<br />
            Address: [Your Company Address]
          </Typography>
        </CardContent>
      </Card>
    </Container>
  );
};

export default TermsOfService;
