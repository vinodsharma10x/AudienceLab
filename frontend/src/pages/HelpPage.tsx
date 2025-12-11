import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  Grid,
  TextField,
  InputAdornment,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Alert,
  Paper,
} from '@mui/material';
import {
  ExpandMore,
  Search,
  VideoLibrary,
  Facebook,
  Analytics,
  Settings,
  LiveHelp,
  Email,
  Phone,
  Chat,
  PlayCircleOutline,
  AutoAwesome,
  Campaign,
  TrendingUp,
} from '@mui/icons-material';

const HelpPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFAQ, setExpandedFAQ] = useState<string | false>(false);

  const handleFAQChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedFAQ(isExpanded ? panel : false);
  };

  const faqs = [
    {
      id: 'faq1',
      question: 'How do I create my first video ad?',
      answer: `To create your first video ad:
      1. Click on "Create Video Ad 2.0" in the sidebar
      2. Enter your product URL or paste product information
      3. Follow the workflow through marketing angles, hooks, and scripts
      4. Generate audio with AI voice actors
      5. Create your final video with our video generation tools`,
      category: 'Getting Started',
    },
    {
      id: 'faq2',
      question: 'How do I connect my Facebook account?',
      answer: `To connect your Facebook account:
      1. Go to "FB Connections" in the sidebar
      2. Click "Connect Facebook Account"
      3. Log in to Facebook and authorize the app
      4. Select the ad accounts and pages you want to manage
      5. Your account will be synced automatically`,
      category: 'Facebook Integration',
    },
    {
      id: 'faq3',
      question: 'What AI models are available for content generation?',
      answer: `We use multiple AI models:
      • Claude (Anthropic) - For creative content and marketing copy
      • GPT-4 (OpenAI) - For product analysis and data extraction
      • ElevenLabs - For realistic voice synthesis
      • Hedra - For video generation
      Each model is optimized for specific tasks to give you the best results.`,
      category: 'AI Features',
    },
    {
      id: 'faq4',
      question: 'How can I track my campaign performance?',
      answer: `Track your campaigns through:
      1. FB Analytics - View real-time Facebook ad performance
      2. FB Conversion Report - Detailed conversion tracking
      3. Dashboard - Overview of all your campaigns
      4. Custom reports can be generated for specific date ranges`,
      category: 'Analytics',
    },
    {
      id: 'faq5',
      question: 'What video formats are supported?',
      answer: `Supported formats:
      • Output: MP4 (recommended), WebM, MOV
      • Aspect Ratios: 16:9, 9:16 (vertical), 1:1 (square)
      • Resolution: Up to 1080p
      • Duration: 15 seconds to 2 minutes
      • File Size: Up to 100MB`,
      category: 'Technical',
    },
    {
      id: 'faq6',
      question: 'How do I manage multiple campaigns?',
      answer: `Use the "My Campaigns" section to:
      • View all your campaigns in one place
      • Filter by status (Active, Draft, Completed)
      • Edit or duplicate existing campaigns
      • Archive old campaigns
      • Export campaign data`,
      category: 'Campaign Management',
    },
  ];

  const quickGuides = [
    {
      title: 'Getting Started Guide',
      description: 'Learn the basics of creating your first video ad',
      icon: <PlayCircleOutline />,
      time: '5 min read',
    },
    {
      title: 'Facebook Integration',
      description: 'Connect and manage your Facebook ad accounts',
      icon: <Facebook />,
      time: '3 min read',
    },
    {
      title: 'AI Voice Generation',
      description: 'Create natural-sounding voiceovers with AI',
      icon: <AutoAwesome />,
      time: '4 min read',
    },
    {
      title: 'Analytics Dashboard',
      description: 'Understanding your campaign metrics',
      icon: <Analytics />,
      time: '6 min read',
    },
  ];

  const filteredFAQs = faqs.filter(faq =>
    faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
    faq.answer.toLowerCase().includes(searchQuery.toLowerCase()) ||
    faq.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box sx={{ backgroundColor: '#f5f5f5', minHeight: '100vh', py: 3 }}>
      <Container maxWidth="lg">
        {/* Header */}
        <Box mb={4}>
          <Box display="flex" alignItems="center" gap={2} mb={1}>
            <Typography variant="h4" fontWeight="bold">
              Help Center
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
            Find answers to your questions and learn how to make the most of AudienceLab
          </Typography>
        </Box>

        {/* Search Bar */}
        <Paper sx={{ p: 2, mb: 4 }}>
          <TextField
            fullWidth
            placeholder="Search for help articles, FAQs, or guides..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
        </Paper>

        {/* Quick Guides */}
        <Typography variant="h5" fontWeight="bold" gutterBottom sx={{ mt: 4, mb: 2 }}>
          Quick Start Guides
        </Typography>
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {quickGuides.map((guide, index) => (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={index}>
              <Card sx={{ 
                height: '100%', 
                cursor: 'pointer',
                '&:hover': { 
                  boxShadow: 3,
                  transform: 'translateY(-2px)',
                  transition: 'all 0.3s'
                }
              }}>
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    <Box sx={{ 
                      p: 1, 
                      borderRadius: 1, 
                      backgroundColor: '#e3f2fd',
                      color: '#1976d2',
                      mr: 2
                    }}>
                      {guide.icon}
                    </Box>
                    <Chip label={guide.time} size="small" />
                  </Box>
                  <Typography variant="h6" gutterBottom>
                    {guide.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {guide.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* FAQs */}
        <Typography variant="h5" fontWeight="bold" gutterBottom sx={{ mt: 4, mb: 2 }}>
          Frequently Asked Questions
        </Typography>
        
        {filteredFAQs.length === 0 ? (
          <Alert severity="info">
            No FAQs found matching "{searchQuery}". Try a different search term.
          </Alert>
        ) : (
          <Box sx={{ mb: 4 }}>
            {filteredFAQs.map((faq) => (
              <Accordion
                key={faq.id}
                expanded={expandedFAQ === faq.id}
                onChange={handleFAQChange(faq.id)}
                sx={{ mb: 1 }}
              >
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                    <Typography sx={{ flexGrow: 1 }}>{faq.question}</Typography>
                    <Chip 
                      label={faq.category} 
                      size="small" 
                      sx={{ mr: 2 }}
                      color="primary"
                      variant="outlined"
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography style={{ whiteSpace: 'pre-line' }}>
                    {faq.answer}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        )}

        {/* Video Tutorials */}
        <Typography variant="h5" fontWeight="bold" gutterBottom sx={{ mt: 4, mb: 2 }}>
          Video Tutorials
        </Typography>
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card>
              <Box sx={{ 
                height: 200, 
                backgroundColor: '#e0e0e0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <VideoLibrary sx={{ fontSize: 60, color: '#9e9e9e' }} />
              </Box>
              <CardContent>
                <Typography variant="h6">Complete Workflow Tutorial</Typography>
                <Typography variant="body2" color="text.secondary">
                  15 min • Step-by-step guide
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card>
              <Box sx={{ 
                height: 200, 
                backgroundColor: '#e0e0e0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Campaign sx={{ fontSize: 60, color: '#9e9e9e' }} />
              </Box>
              <CardContent>
                <Typography variant="h6">Campaign Management</Typography>
                <Typography variant="body2" color="text.secondary">
                  10 min • Best practices
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card>
              <Box sx={{ 
                height: 200, 
                backgroundColor: '#e0e0e0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <TrendingUp sx={{ fontSize: 60, color: '#9e9e9e' }} />
              </Box>
              <CardContent>
                <Typography variant="h6">Analytics & Optimization</Typography>
                <Typography variant="body2" color="text.secondary">
                  12 min • Advanced tips
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Contact Support */}
        <Card sx={{ mt: 4 }}>
          <CardContent>
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              Still Need Help?
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              Our support team is here to help you succeed
            </Typography>
            
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 4 }}>
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <Email color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Email Support"
                      secondary="support@audiencelab.io"
                    />
                  </ListItem>
                </List>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <Chat color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Live Chat"
                      secondary="Available Mon-Fri, 9am-5pm EST"
                    />
                  </ListItem>
                </List>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <LiveHelp color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Knowledge Base"
                      secondary="docs.audiencelab.io"
                    />
                  </ListItem>
                </List>
              </Grid>
            </Grid>
            
            <Box mt={3}>
              <Button 
                variant="contained" 
                size="large"
                startIcon={<Email />}
              >
                Contact Support
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* System Status */}
        <Alert 
          severity="success" 
          sx={{ mt: 4 }}
          icon={<Settings />}
        >
          <strong>System Status:</strong> All services are operational
        </Alert>
      </Container>
    </Box>
  );
};

export default HelpPage;