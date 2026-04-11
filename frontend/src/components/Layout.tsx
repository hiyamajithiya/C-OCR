/**
 * Main layout component with enhanced dark theme sidebar and header.
 */

import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  IconButton,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Avatar,
  Divider,
  Tooltip,
  Badge,
  Chip,
  alpha,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard,
  Description,
  ViewModule,
  Key,
  People,
  History,
  Logout,
  Notifications,
  ChevronLeft,
  DocumentScanner,
  Settings,
  ExpandMore,
  Business,
  BarChart,
} from '@mui/icons-material';
import { useAuth } from '@/contexts/AuthContext';
import { colors } from '@/theme/theme';

const drawerWidth = 260;
const collapsedDrawerWidth = 72;

interface NavItem {
  text: string;
  icon: React.ReactElement;
  path: string;
  roles?: string[];
  badge?: number;
}

const navItems: NavItem[] = [
  { text: 'Dashboard', icon: <Dashboard />, path: '/' },
  { text: 'Documents', icon: <Description />, path: '/documents' },
  { text: 'Templates', icon: <ViewModule />, path: '/templates' },
  { text: 'Entities', icon: <Business />, path: '/entities', roles: ['admin'] },
  { text: 'Analytics', icon: <BarChart />, path: '/analytics', roles: ['admin'] },
  { text: 'API Keys', icon: <Key />, path: '/api-keys', roles: ['admin'] },
  { text: 'Users', icon: <People />, path: '/users', roles: ['admin'] },
  { text: 'Audit Logs', icon: <History />, path: '/audit-logs', roles: ['admin'] },
];

const Layout: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasRole } = useAuth();

  const currentDrawerWidth = collapsed ? collapsedDrawerWidth : drawerWidth;

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleCollapseToggle = () => {
    setCollapsed(!collapsed);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNotificationsClick = () => {
    if (hasRole(['admin'])) {
      navigate('/audit-logs');
      return;
    }
    navigate('/');
  };

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return colors.error.main;
      case 'reviewer':
        return colors.warning.main;
      default:
        return colors.primary.main;
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const drawer = (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: `linear-gradient(180deg, ${colors.background.paper} 0%, ${colors.background.default} 100%)`,
      }}
    >
      {/* Logo Section */}
      <Box
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          minHeight: 64,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 2,
              background: `linear-gradient(135deg, ${colors.primary.main} 0%, ${colors.secondary.main} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 4px 12px ${alpha(colors.primary.main, 0.4)}`,
            }}
          >
            <DocumentScanner sx={{ fontSize: 24, color: 'white' }} />
          </Box>
          {!collapsed && (
            <Typography
              variant="h6"
              sx={{
                fontWeight: 700,
                background: `linear-gradient(135deg, ${colors.primary.light} 0%, ${colors.secondary.main} 100%)`,
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              C-OCR
            </Typography>
          )}
        </Box>
        {!collapsed && (
          <IconButton
            size="small"
            onClick={handleCollapseToggle}
            sx={{ color: 'text.secondary', display: { xs: 'none', sm: 'flex' } }}
          >
            <ChevronLeft />
          </IconButton>
        )}
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, px: 1.5, py: 2 }}>
        <List component="nav" sx={{ p: 0 }}>
          {navItems
            .filter((item) => !item.roles || hasRole(item.roles))
            .map((item) => {
              const active = isActive(item.path);
              return (
                <ListItemButton
                  key={item.text}
                  onClick={() => navigate(item.path)}
                  selected={active}
                  sx={{
                    borderRadius: 2,
                    mb: 0.5,
                    px: collapsed ? 2 : 2,
                    minHeight: 48,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: collapsed ? 0 : 40,
                      color: active ? 'primary.main' : 'text.secondary',
                      justifyContent: 'center',
                    }}
                  >
                    {item.badge ? (
                      <Badge badgeContent={item.badge} color="error" max={99}>
                        {item.icon}
                      </Badge>
                    ) : (
                      item.icon
                    )}
                  </ListItemIcon>
                  {!collapsed && (
                    <ListItemText
                      primary={item.text}
                      primaryTypographyProps={{
                        fontSize: '0.9rem',
                        fontWeight: active ? 600 : 400,
                      }}
                    />
                  )}
                  {!collapsed && item.roles?.includes('admin') && (
                    <Chip
                      label="Admin"
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.65rem',
                        bgcolor: alpha(colors.error.main, 0.15),
                        color: colors.error.light,
                      }}
                    />
                  )}
                </ListItemButton>
              );
            })}
        </List>
      </Box>

      {/* User Section */}
      <Box sx={{ p: 2, borderTop: `1px solid ${alpha(colors.text.primary, 0.08)}` }}>
        {collapsed ? (
          <Tooltip title={user?.name || 'User'} placement="right">
            <Avatar
              sx={{
                width: 40,
                height: 40,
                bgcolor: getRoleColor(user?.role || ''),
                cursor: 'pointer',
                mx: 'auto',
              }}
              onClick={handleMenuOpen}
            >
              {user?.name ? getInitials(user.name) : 'U'}
            </Avatar>
          </Tooltip>
        ) : (
          <Box
            onClick={handleMenuOpen}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              p: 1.5,
              borderRadius: 2,
              cursor: 'pointer',
              transition: 'all 0.2s',
              '&:hover': {
                bgcolor: alpha(colors.primary.main, 0.08),
              },
            }}
          >
            <Avatar
              sx={{
                width: 40,
                height: 40,
                bgcolor: getRoleColor(user?.role || ''),
              }}
            >
              {user?.name ? getInitials(user.name) : 'U'}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography
                variant="body2"
                sx={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
              >
                {user?.name || 'User'}
              </Typography>
              <Typography
                variant="caption"
                sx={{ color: 'text.secondary', textTransform: 'capitalize' }}
              >
                {user?.role || 'Role'}
              </Typography>
            </Box>
            <ExpandMore sx={{ color: 'text.secondary' }} />
          </Box>
        )}
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${currentDrawerWidth}px)` },
          ml: { sm: `${currentDrawerWidth}px` },
          transition: 'all 0.3s ease',
        }}
      >
        <Toolbar sx={{ minHeight: { xs: 64, sm: 70 } }}>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          {collapsed && (
            <IconButton
              onClick={handleCollapseToggle}
              sx={{ mr: 2, display: { xs: 'none', sm: 'flex' } }}
            >
              <MenuIcon />
            </IconButton>
          )}
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {navItems.find((item) => isActive(item.path))?.text || 'Dashboard'}
            </Typography>
          </Box>

          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton sx={{ mr: 1 }} onClick={handleNotificationsClick}>
              <Badge badgeContent={0} color="error">
                <Notifications />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* Settings */}
          <Tooltip title="Settings">
            <IconButton sx={{ mr: 1 }} onClick={() => navigate('/settings')}>
              <Settings />
            </IconButton>
          </Tooltip>

          {/* User Avatar Menu */}
          <Tooltip title="Account">
            <IconButton onClick={handleMenuOpen} sx={{ p: 0 }}>
              <Avatar sx={{ width: 36, height: 36, bgcolor: colors.primary.main, fontWeight: 700 }}>
                {user?.name?.charAt(0)?.toUpperCase() || '?'}
              </Avatar>
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* User Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        PaperProps={{
          sx: {
            mt: 1,
            minWidth: 200,
          },
        }}
      >
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            {user?.name}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {user?.email}
          </Typography>
        </Box>
        <Divider sx={{ my: 1 }} />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <Logout fontSize="small" />
          </ListItemIcon>
          <ListItemText>Sign Out</ListItemText>
        </MenuItem>
      </Menu>

      {/* Mobile Drawer */}
      <Box
        component="nav"
        sx={{
          width: { sm: currentDrawerWidth },
          flexShrink: { sm: 0 },
          transition: 'all 0.3s ease',
        }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              border: 'none',
            },
          }}
        >
          {drawer}
        </Drawer>

        {/* Desktop Drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: currentDrawerWidth,
              transition: 'all 0.3s ease',
              border: 'none',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, sm: 3 },
          width: { sm: `calc(100% - ${currentDrawerWidth}px)` },
          mt: { xs: 8, sm: 9 },
          transition: 'all 0.3s ease',
          minHeight: 'calc(100vh - 70px)',
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;
