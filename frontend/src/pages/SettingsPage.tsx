/**
 * Settings page — user profile, preferences, security.
 */

import React, { useState } from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Divider,
  Switch,
  FormControlLabel,
  Avatar,
  Chip,
  Alert,
  Snackbar,
  InputAdornment,
  IconButton,
  alpha,
} from '@mui/material';
import {
  Person,
  Email,
  Lock,
  Notifications,
  Palette,
  Security,
  Visibility,
  VisibilityOff,
  Save,
  Badge,
} from '@mui/icons-material';
import { useAuth } from '@/contexts/AuthContext';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';

const SettingsPage: React.FC = () => {
  const { user } = useAuth();

  // Profile state
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [savingProfile, setSavingProfile] = useState(false);

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  // Preferences
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [browserNotifications, setBrowserNotifications] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const [compactMode, setCompactMode] = useState(false);

  // Snackbar
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const showMessage = (message: string, severity: 'success' | 'error' = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleSaveProfile = async () => {
    if (!user) return;
    if (!name.trim() || !email.trim()) {
      showMessage('Name and email are required', 'error');
      return;
    }
    setSavingProfile(true);
    try {
      await apiService.updateUser(user.id, { name, email });
      showMessage('Profile updated successfully');
    } catch (error: any) {
      showMessage(error?.response?.data?.detail || 'Failed to update profile', 'error');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async () => {
    if (!user) return;
    if (!newPassword || newPassword.length < 8) {
      showMessage('Password must be at least 8 characters', 'error');
      return;
    }
    if (newPassword !== confirmPassword) {
      showMessage('Passwords do not match', 'error');
      return;
    }
    setSavingPassword(true);
    try {
      await apiService.updateUser(user.id, { password: newPassword });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showMessage('Password changed successfully');
    } catch (error: any) {
      showMessage(error?.response?.data?.detail || 'Failed to change password', 'error');
    } finally {
      setSavingPassword(false);
    }
  };

  const handleSavePreferences = () => {
    // Preferences are client-side for now
    localStorage.setItem(
      'user_preferences',
      JSON.stringify({ emailNotifications, browserNotifications, darkMode, compactMode })
    );
    showMessage('Preferences saved');
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Settings
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.secondary' }}>
          Manage your profile, security, and preferences
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Profile Section */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <Avatar
                sx={{
                  width: 96,
                  height: 96,
                  margin: '0 auto',
                  mb: 2,
                  bgcolor: colors.primary.main,
                  fontSize: '2rem',
                  fontWeight: 700,
                }}
              >
                {user?.name?.charAt(0)?.toUpperCase() || '?'}
              </Avatar>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {user?.name}
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
                {user?.email}
              </Typography>
              <Chip
                icon={<Badge sx={{ fontSize: 16 }} />}
                label={user?.role?.toUpperCase()}
                color={user?.role === 'admin' ? 'primary' : 'default'}
                size="small"
                sx={{ fontWeight: 600 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          {/* Profile Information */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: 1.5,
                    bgcolor: alpha(colors.primary.main, 0.12),
                    color: 'primary.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Person />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Profile Information
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Update your personal details
                  </Typography>
                </Box>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Full Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <Person fontSize="small" />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Email Address"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <Email fontSize="small" />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>
              </Grid>

              <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  startIcon={<Save />}
                  onClick={handleSaveProfile}
                  disabled={savingProfile}
                >
                  {savingProfile ? 'Saving...' : 'Save Changes'}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Security */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: 1.5,
                    bgcolor: alpha(colors.warning.main, 0.12),
                    color: 'warning.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Security />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Change Password
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Keep your account secure
                  </Typography>
                </Box>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Current Password"
                    type={showPassword ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <Lock fontSize="small" />
                        </InputAdornment>
                      ),
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small">
                            {showPassword ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="New Password"
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    helperText="Minimum 8 characters"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Confirm New Password"
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    error={confirmPassword !== '' && newPassword !== confirmPassword}
                    helperText={confirmPassword !== '' && newPassword !== confirmPassword ? 'Passwords do not match' : ''}
                  />
                </Grid>
              </Grid>

              <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  color="warning"
                  startIcon={<Save />}
                  onClick={handleChangePassword}
                  disabled={savingPassword || !newPassword}
                >
                  {savingPassword ? 'Updating...' : 'Update Password'}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Preferences */}
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: 1.5,
                    bgcolor: alpha(colors.success.main, 0.12),
                    color: 'success.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Palette />
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Preferences
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Customize your experience
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ mb: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
                  <Notifications sx={{ fontSize: 16, verticalAlign: 'middle', mr: 0.5 }} />
                  Notifications
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={emailNotifications}
                      onChange={(e) => setEmailNotifications(e.target.checked)}
                    />
                  }
                  label="Email notifications"
                  sx={{ display: 'flex', mb: 0.5 }}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={browserNotifications}
                      onChange={(e) => setBrowserNotifications(e.target.checked)}
                    />
                  }
                  label="Browser notifications"
                  sx={{ display: 'flex' }}
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
                  <Palette sx={{ fontSize: 16, verticalAlign: 'middle', mr: 0.5 }} />
                  Appearance
                </Typography>
                <FormControlLabel
                  control={<Switch checked={darkMode} onChange={(e) => setDarkMode(e.target.checked)} />}
                  label="Dark mode"
                  sx={{ display: 'flex', mb: 0.5 }}
                />
                <FormControlLabel
                  control={<Switch checked={compactMode} onChange={(e) => setCompactMode(e.target.checked)} />}
                  label="Compact layout"
                  sx={{ display: 'flex' }}
                />
              </Box>

              <Alert severity="info" sx={{ mt: 2 }}>
                Some preference changes may require a page reload to take effect.
              </Alert>

              <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                <Button variant="contained" color="success" startIcon={<Save />} onClick={handleSavePreferences}>
                  Save Preferences
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SettingsPage;
