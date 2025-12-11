import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import { HotjarTracker } from './components/HotjarTracker';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import DashboardLayout from './components/DashboardLayout';
import ImportFromURL from './pages/video-ads/ImportFromURL';
import ProductInfo from './pages/video-ads/ProductInfo';
import MarketingAngles from './pages/video-ads/MarketingAngles';
import Hooks from './pages/video-ads/Hooks';
import Scripts from './pages/video-ads/Scripts';
import VoiceActor from './pages/video-ads/VoiceActor';
import Audio from './pages/video-ads/Audio';
import Video from './pages/video-ads/Video';

// Video Ads V2 Components
import ImportFromURLV2 from './pages/video-ads-v2/ImportFromURL';
import ProductInfoV2 from './pages/video-ads-v2/ProductInfo';
import MarketingAnglesV2 from './pages/video-ads-v2/MarketingAngles';
import HooksV2 from './pages/video-ads-v2/HooksV2';
import ScriptsV2 from './pages/video-ads-v2/Scripts';
import VoiceActorV2 from './pages/video-ads-v2/VoiceActor';
import AudioV2 from './pages/video-ads-v2/Audio';
import VideoV2 from './pages/video-ads-v2/Video';
import CampaignsList from './pages/video-ads-v2/CampaignsList';
import VideoUpload from './pages/video-ads-v2/VideoUpload';

// V4 Components
import V4ImportFromURL from './pages/video-ads-v4/ImportFromURL';
import V4ProductInfo from './pages/video-ads-v4/ProductInfo';
import V4MarketingResearch from './pages/video-ads-v4/MarketingResearch';
import V4ContentLibrary from './pages/video-ads-v4/ContentLibrary';
import V4ContentLibraryV2 from './pages/video-ads-v4/ContentLibraryV2';
import V4ContentLibraryV3 from './pages/video-ads-v4/ContentLibraryV3';
import V4CampaignList from './pages/video-ads-v4/CampaignList';

// Settings and Help Pages
import SettingsPage from './pages/SettingsPage';
import HelpPage from './pages/HelpPage';

// Legal Pages
import PrivacyPolicy from './pages/legal/PrivacyPolicy';
import TermsOfService from './pages/legal/TermsOfService';
import DataDeletion from './pages/legal/DataDeletion';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <Router>
          <HotjarTracker />
          <Routes>
            <Route path="/login" element={<AuthPage />} />
            <Route path="/auth" element={<AuthPage />} />

            {/* Routes with DashboardLayout (sidebar) */}
            <Route element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/video-ads/import-from-url" element={<ImportFromURL />} />
              <Route path="/video-ads/product-info" element={<ProductInfo />} />
              <Route path="/video-ads/marketing-angles" element={<MarketingAngles />} />
              <Route path="/video-ads/hooks" element={<Hooks />} />
              <Route path="/video-ads/scripts" element={<Scripts />} />
              <Route path="/video-ads/voice-actor" element={<VoiceActor />} />
              <Route path="/video-ads/audio" element={<Audio />} />
              <Route path="/video-ads/video" element={<Video />} />
              <Route path="/video-ads-v2/campaigns" element={<CampaignsList />} />
              <Route path="/video-ads-v2/import-from-url" element={<ImportFromURLV2 />} />
              <Route path="/video-ads-v2/product-info" element={<ProductInfoV2 />} />
              <Route path="/video-ads-v2/marketing-angles" element={<MarketingAnglesV2 />} />
              <Route path="/video-ads-v2/hooks" element={<HooksV2 />} />
              <Route path="/video-ads-v2/scripts" element={<ScriptsV2 />} />
              <Route path="/video-ads-v2/voice-actor" element={<VoiceActorV2 />} />
              <Route path="/video-ads-v2/audio" element={<AudioV2 />} />
              <Route path="/video-ads-v2/video" element={<VideoV2 />} />
              <Route path="/video-ads-v2/upload" element={<VideoUpload />} />

              {/* V4 Routes */}
              <Route path="/video-ads-v4/campaigns" element={<V4CampaignList />} />
              <Route path="/video-ads-v4/import" element={<V4ImportFromURL />} />
              <Route path="/video-ads-v4/product-info/:campaignId" element={<V4ProductInfo />} />
              <Route path="/video-ads-v4/research/:campaignId" element={<V4MarketingResearch />} />
              <Route path="/video-ads-v4/library/:campaignId" element={<V4ContentLibrary />} />
              <Route path="/video-ads-v4/library-v2/:campaignId" element={<V4ContentLibraryV2 />} />
              <Route path="/video-ads-v4/library-v3/:campaignId" element={<V4ContentLibraryV3 />} />

              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/help" element={<HelpPage />} />
            </Route>
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/terms" element={<TermsOfService />} />
            <Route path="/data-deletion" element={<DataDeletion />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
