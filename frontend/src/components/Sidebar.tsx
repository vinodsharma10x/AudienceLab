import React, { useEffect } from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Divider,
  Avatar,
  Typography,
  Tooltip,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  ChevronLeft,
  Dashboard,
  Settings,
  Help,
  ExitToApp,
  AutoAwesome,
  Campaign,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ open, onToggle }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { signOut, session } = useAuth();

  const drawerWidth = open ? 240 : 60;

  useEffect(() => {
    // Auto-collapse on mobile
    if (isMobile && open) {
      onToggle();
    }
  }, [isMobile]);

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      onToggle(); // Close drawer on mobile after navigation
    }
  };

  const isActive = (path: string) => location.pathname === path;

  const menuItems = [
    {
      text: 'Dashboard',
      icon: <Dashboard />,
      path: '/dashboard',
    },
    {
      text: 'New Research',
      icon: <AutoAwesome />,
      path: '/video-ads-v4/import',
    },
    {
      text: 'Existing Research',
      icon: <Campaign />,
      path: '/video-ads-v4/campaigns',
    },
  ];

  const bottomMenuItems = [
    {
      text: 'Settings',
      icon: <Settings />,
      path: '/settings',
    },
    {
      text: 'Help',
      icon: <Help />,
      path: '/help',
    },
  ];

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          backgroundColor: '#f8f9fa',
          borderRight: '1px solid #e0e0e0',
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          overflowX: 'hidden',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: open ? 'space-between' : 'center', p: 1, minHeight: 64 }}>
        {open && (
          <Typography variant="h6" sx={{ ml: 1, fontWeight: 'bold', color: '#1976d2' }}>
            AudienceLab
          </Typography>
        )}
        <IconButton onClick={onToggle} size="small">
          {open ? <ChevronLeft /> : <MenuIcon />}
        </IconButton>
      </Box>
      
      <Divider />
      
      <List sx={{ flexGrow: 1, pt: 1 }}>
        {menuItems.map((item, index) => (
          <ListItem key={index} disablePadding sx={{ display: 'block' }}>
            <ListItemButton
              onClick={() => handleNavigation(item.path)}
              sx={{
                minHeight: 48,
                justifyContent: open ? 'initial' : 'center',
                px: 2.5,
                backgroundColor: isActive(item.path) ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
                '&:hover': {
                  backgroundColor: 'rgba(25, 118, 210, 0.12)',
                },
              }}
            >
              <Tooltip title={!open ? item.text : ''} placement="right">
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open ? 3 : 'auto',
                    justifyContent: 'center',
                    color: isActive(item.path) ? '#1976d2' : 'inherit',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
              </Tooltip>
              {open && (
                <ListItemText
                  primary={item.text}
                  sx={{
                    opacity: open ? 1 : 0,
                    '& .MuiTypography-root': {
                      fontWeight: isActive(item.path) ? 600 : 400,
                      color: isActive(item.path) ? '#1976d2' : 'inherit',
                    }
                  }}
                />
              )}
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      
      <Divider />
      
      <List>
        {/* AudienceLab Section */}
        <ListItem sx={{ px: 2, py: 1 }}>
          {open ? (
            <>
              <Avatar sx={{ width: 32, height: 32, mr: 2, bgcolor: '#1976d2' }}>
                A
              </Avatar>
              <ListItemText 
                primary="AudienceLab"
                primaryTypographyProps={{ 
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}
              />
            </>
          ) : (
            <Tooltip title="AudienceLab" placement="right">
              <Avatar sx={{ width: 32, height: 32, bgcolor: '#1976d2', mx: 'auto' }}>
                A
              </Avatar>
            </Tooltip>
          )}
        </ListItem>
        
        <Divider sx={{ my: 1 }} />
        
        {bottomMenuItems.map((item, index) => (
          <ListItem key={index} disablePadding sx={{ display: 'block' }}>
            <ListItemButton
              onClick={() => handleNavigation(item.path)}
              sx={{
                minHeight: 48,
                justifyContent: open ? 'initial' : 'center',
                px: 2.5,
                '&:hover': {
                  backgroundColor: 'rgba(25, 118, 210, 0.12)',
                },
              }}
            >
              <Tooltip title={!open ? item.text : ''} placement="right">
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open ? 3 : 'auto',
                    justifyContent: 'center',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
              </Tooltip>
              {open && <ListItemText primary={item.text} sx={{ opacity: open ? 1 : 0 }} />}
            </ListItemButton>
          </ListItem>
        ))}
        
        <ListItem disablePadding sx={{ display: 'block' }}>
          <ListItemButton
            onClick={signOut}
            sx={{
              minHeight: 48,
              justifyContent: open ? 'initial' : 'center',
              px: 2.5,
              '&:hover': {
                backgroundColor: 'rgba(211, 47, 47, 0.12)',
              },
            }}
          >
            <Tooltip title={!open ? 'Sign Out' : ''} placement="right">
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: open ? 3 : 'auto',
                  justifyContent: 'center',
                  color: '#d32f2f',
                }}
              >
                <ExitToApp />
              </ListItemIcon>
            </Tooltip>
            {open && <ListItemText primary="Sign Out" sx={{ opacity: open ? 1 : 0, color: '#d32f2f' }} />}
          </ListItemButton>
        </ListItem>
      </List>
    </Drawer>
  );
};

export default Sidebar;