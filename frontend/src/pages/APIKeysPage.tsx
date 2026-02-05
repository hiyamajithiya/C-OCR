/**
 * API Keys management page with usage statistics and template scoping.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  IconButton,
  Alert,
  Grid,
  Tooltip,
  alpha,
  Skeleton,
  LinearProgress,
  FormControlLabel,
  Checkbox,
  Autocomplete,
  Divider,
} from '@mui/material';
import {
  Add,
  Key,
  Delete,
  ContentCopy,
  Speed,
  CheckCircle,
  Warning,
  Close,
  Analytics,
  TrendingUp,
  ViewModule,
  Refresh,
  BarChart,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';

interface APIKeyUsage {
  today: number;
  today_quota_percent: number;
  week: number;
  total: number;
  current_minute: number;
}

interface APIKeyWithStats {
  id: number;
  name: string;
  key_prefix: string;
  is_active: boolean;
  rate_limit: number;
  daily_quota: number;
  restrict_to_templates: boolean;
  allowed_template_count: number | null;
  created_at: string;
  last_used_at: string | null;
  usage: APIKeyUsage;
}

interface APIKeyStats {
  api_key_id: number;
  api_key_name: string;
  period_days: number;
  total_requests: number;
  successful_requests: number;
  client_errors: number;
  server_errors: number;
  success_rate: number;
  today: {
    requests: number;
    quota_limit: number;
    quota_remaining: number;
    quota_percent_used: number;
  };
  rate_limit: {
    limit_per_minute: number;
    current_minute_usage: number;
    remaining: number;
  };
  daily_breakdown: Array<{
    date: string;
    total: number;
    successful: number;
    failed: number;
  }>;
  top_endpoints: Array<{
    endpoint: string;
    count: number;
  }>;
}

interface Template {
  id: number;
  name: string;
}

const APIKeysPage: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<APIKeyWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [statsDialogOpen, setStatsDialogOpen] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState<number | null>(null);
  const [selectedKeyStats, setSelectedKeyStats] = useState<APIKeyStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [newKey, setNewKey] = useState<any>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [newAPIKey, setNewAPIKey] = useState({
    name: '',
    scopes: ['documents:read', 'documents:write'],
    rate_limit: 100,
    daily_quota: 5000,
    restrict_to_templates: false,
    template_ids: [] as number[],
  });

  useEffect(() => {
    loadAPIKeys();
    loadTemplates();
  }, []);

  const loadAPIKeys = async () => {
    try {
      const data = await apiService.listAPIKeysWithStats();
      setApiKeys(data);
    } catch (err) {
      // Fallback to regular list if with-stats fails
      try {
        const data = await apiService.listAPIKeys();
        setApiKeys(data.map((k: any) => ({
          ...k,
          usage: { today: 0, today_quota_percent: 0, week: 0, total: 0, current_minute: 0 }
        })));
      } catch (innerErr) {
        console.error('Failed to load API keys:', innerErr);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await apiService.listTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const handleViewStats = async (keyId: number) => {
    setLoadingStats(true);
    setStatsDialogOpen(true);
    try {
      const stats = await apiService.getAPIKeyStats(keyId, 30);
      setSelectedKeyStats(stats);
    } catch (err) {
      console.error('Failed to load stats:', err);
      setSelectedKeyStats(null);
    } finally {
      setLoadingStats(false);
    }
  };

  const handleCreateAPIKey = async () => {
    setError('');
    try {
      const result = await apiService.createAPIKey(newAPIKey);
      setNewKey(result);
      setShowKeyDialog(true);
      setOpenDialog(false);
      setNewAPIKey({
        name: '',
        scopes: ['documents:read', 'documents:write'],
        rate_limit: 100,
        daily_quota: 5000,
        restrict_to_templates: false,
        template_ids: [],
      });
      loadAPIKeys();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create API key');
    }
  };

  const handleRevokeKey = async () => {
    if (!keyToDelete) return;
    try {
      await apiService.revokeAPIKey(keyToDelete);
      loadAPIKeys();
      setDeleteDialogOpen(false);
      setKeyToDelete(null);
    } catch (err) {
      console.error('Failed to revoke API key:', err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getQuotaColor = (percent: number) => {
    if (percent >= 90) return colors.error.main;
    if (percent >= 70) return colors.warning.main;
    return colors.success.main;
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            API Keys
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            Manage API keys for external integrations with usage tracking
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<Refresh />} onClick={loadAPIKeys}>
            Refresh
          </Button>
          <Button variant="contained" startIcon={<Add />} onClick={() => setOpenDialog(true)} sx={{ px: 3 }}>
            Create API Key
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* API Keys Grid */}
      {loading ? (
        <Grid container spacing={3}>
          {[1, 2].map((i) => (
            <Grid item xs={12} md={6} key={i}>
              <Skeleton variant="rounded" height={220} />
            </Grid>
          ))}
        </Grid>
      ) : apiKeys.length === 0 ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: 3,
              bgcolor: alpha(colors.warning.main, 0.1),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mx: 'auto',
              mb: 3,
            }}
          >
            <Key sx={{ fontSize: 40, color: colors.warning.main }} />
          </Box>
          <Typography variant="h6" sx={{ mb: 1 }}>
            No API Keys
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
            Create an API key to integrate with external applications
          </Typography>
          <Button variant="contained" startIcon={<Add />} onClick={() => setOpenDialog(true)}>
            Create First API Key
          </Button>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {apiKeys.map((key) => (
            <Grid item xs={12} md={6} key={key.id}>
              <Card
                sx={{
                  position: 'relative',
                  '&::before': key.is_active
                    ? {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        height: 4,
                        background: `linear-gradient(90deg, ${colors.success.main} 0%, ${alpha(colors.success.main, 0.5)} 100%)`,
                      }
                    : {},
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  {/* Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Box
                        sx={{
                          width: 48,
                          height: 48,
                          borderRadius: 2,
                          bgcolor: alpha(key.is_active ? colors.success.main : colors.text.secondary, 0.15),
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Key sx={{ fontSize: 24, color: key.is_active ? colors.success.main : 'text.secondary' }} />
                      </Box>
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {key.name}
                        </Typography>
                        <Typography variant="body2" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>
                          {key.key_prefix}...
                        </Typography>
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        icon={key.is_active ? <CheckCircle sx={{ fontSize: 14 }} /> : <Warning sx={{ fontSize: 14 }} />}
                        label={key.is_active ? 'Active' : 'Revoked'}
                        size="small"
                        color={key.is_active ? 'success' : 'default'}
                      />
                      {key.restrict_to_templates && (
                        <Tooltip title={`Restricted to ${key.allowed_template_count} template(s)`}>
                          <Chip
                            icon={<ViewModule sx={{ fontSize: 14 }} />}
                            label="Restricted"
                            size="small"
                            sx={{ bgcolor: alpha(colors.warning.main, 0.15), color: colors.warning.main }}
                          />
                        </Tooltip>
                      )}
                    </Box>
                  </Box>

                  {/* Usage Stats */}
                  <Box sx={{ mb: 2, p: 2, borderRadius: 2, bgcolor: alpha(colors.background.default, 0.5) }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        Today's Usage
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {key.usage.today.toLocaleString()} / {key.daily_quota.toLocaleString()}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(key.usage.today_quota_percent, 100)}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        bgcolor: alpha(colors.text.primary, 0.08),
                        '& .MuiLinearProgress-bar': {
                          borderRadius: 3,
                          bgcolor: getQuotaColor(key.usage.today_quota_percent),
                        },
                      }}
                    />
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {key.usage.today_quota_percent.toFixed(1)}% used
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {(key.daily_quota - key.usage.today).toLocaleString()} remaining
                      </Typography>
                    </Box>
                  </Box>

                  {/* Stats Row */}
                  <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Speed sx={{ fontSize: 18, color: 'text.secondary' }} />
                      <Typography variant="body2">
                        <strong>{key.rate_limit}</strong>/min
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <TrendingUp sx={{ fontSize: 18, color: 'text.secondary' }} />
                      <Typography variant="body2">
                        <strong>{key.usage.week.toLocaleString()}</strong> this week
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Analytics sx={{ fontSize: 18, color: 'text.secondary' }} />
                      <Typography variant="body2">
                        <strong>{key.usage.total.toLocaleString()}</strong> total
                      </Typography>
                    </Box>
                  </Box>

                  {/* Footer */}
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                        Created: {new Date(key.created_at).toLocaleDateString()}
                      </Typography>
                      {key.last_used_at && (
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          Last used: {new Date(key.last_used_at).toLocaleDateString()}
                        </Typography>
                      )}
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Tooltip title="View Statistics">
                        <IconButton
                          size="small"
                          onClick={() => handleViewStats(key.id)}
                          sx={{ color: colors.primary.main }}
                        >
                          <BarChart />
                        </IconButton>
                      </Tooltip>
                      {key.is_active && (
                        <Tooltip title="Revoke Key">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => {
                              setKeyToDelete(key.id);
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <Delete />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create API Key Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Create New API Key</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
            API keys allow external applications to access your data programmatically.
          </Typography>
          <TextField
            fullWidth
            label="Key Name"
            value={newAPIKey.name}
            onChange={(e) => setNewAPIKey({ ...newAPIKey, name: e.target.value })}
            margin="normal"
            required
            placeholder="e.g., Production API Key"
          />
          <TextField
            fullWidth
            label="Rate Limit (requests/minute)"
            type="number"
            value={newAPIKey.rate_limit}
            onChange={(e) => setNewAPIKey({ ...newAPIKey, rate_limit: parseInt(e.target.value) || 60 })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Daily Quota"
            type="number"
            value={newAPIKey.daily_quota}
            onChange={(e) => setNewAPIKey({ ...newAPIKey, daily_quota: parseInt(e.target.value) || 1000 })}
            margin="normal"
          />

          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={newAPIKey.restrict_to_templates}
                  onChange={(e) => setNewAPIKey({ ...newAPIKey, restrict_to_templates: e.target.checked })}
                />
              }
              label="Restrict to specific templates"
            />
          </Box>

          {newAPIKey.restrict_to_templates && (
            <Autocomplete
              multiple
              options={templates}
              getOptionLabel={(option) => option.name}
              value={templates.filter((t) => newAPIKey.template_ids.includes(t.id))}
              onChange={(_, newValue) =>
                setNewAPIKey({ ...newAPIKey, template_ids: newValue.map((t) => t.id) })
              }
              renderInput={(params) => (
                <TextField {...params} label="Allowed Templates" placeholder="Select templates" margin="normal" />
              )}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip label={option.name} size="small" {...getTagProps({ index })} key={option.id} />
                ))
              }
            />
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateAPIKey} variant="contained" disabled={!newAPIKey.name}>
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Revoke API Key</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to revoke this API key? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleRevokeKey}>
            Revoke
          </Button>
        </DialogActions>
      </Dialog>

      {/* Show New Key Dialog */}
      <Dialog open={showKeyDialog} onClose={() => setShowKeyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">API Key Created</Typography>
          <IconButton onClick={() => setShowKeyDialog(false)}>
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 3 }}>
            Save this key now! You won't be able to see it again.
          </Alert>
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              bgcolor: alpha(colors.background.default, 0.5),
              border: `1px solid ${alpha(colors.text.primary, 0.08)}`,
            }}
          >
            <Typography
              variant="body2"
              sx={{ wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '0.8rem', mb: 2 }}
            >
              {newKey?.raw_key}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={copied ? <CheckCircle /> : <ContentCopy />}
              onClick={() => copyToClipboard(newKey?.raw_key || '')}
              color={copied ? 'success' : 'primary'}
            >
              {copied ? 'Copied!' : 'Copy to Clipboard'}
            </Button>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setShowKeyDialog(false)} variant="contained">
            Done
          </Button>
        </DialogActions>
      </Dialog>

      {/* Stats Dialog */}
      <Dialog open={statsDialogOpen} onClose={() => setStatsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <BarChart sx={{ color: colors.primary.main }} />
            <Typography variant="h6">API Key Statistics</Typography>
          </Box>
          <IconButton onClick={() => setStatsDialogOpen(false)}>
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {loadingStats ? (
            <Box sx={{ py: 4 }}>
              <Skeleton variant="rounded" height={100} sx={{ mb: 2 }} />
              <Skeleton variant="rounded" height={200} />
            </Box>
          ) : selectedKeyStats ? (
            <Box>
              {/* Summary Cards */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} md={3}>
                  <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(colors.primary.main, 0.1), textAlign: 'center' }}>
                    <Typography variant="h4" sx={{ color: colors.primary.main, fontWeight: 700 }}>
                      {selectedKeyStats.total_requests.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Total Requests (30d)
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(colors.success.main, 0.1), textAlign: 'center' }}>
                    <Typography variant="h4" sx={{ color: colors.success.main, fontWeight: 700 }}>
                      {selectedKeyStats.success_rate}%
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Success Rate
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(colors.warning.main, 0.1), textAlign: 'center' }}>
                    <Typography variant="h4" sx={{ color: colors.warning.main, fontWeight: 700 }}>
                      {selectedKeyStats.today.requests.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Today's Requests
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(colors.error.main, 0.1), textAlign: 'center' }}>
                    <Typography variant="h4" sx={{ color: colors.error.main, fontWeight: 700 }}>
                      {selectedKeyStats.client_errors + selectedKeyStats.server_errors}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Errors (30d)
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Quota Progress */}
              <Box sx={{ mb: 3, p: 2, borderRadius: 2, bgcolor: alpha(colors.background.default, 0.5) }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>Today's Quota Usage</Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(selectedKeyStats.today.quota_percent_used, 100)}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    bgcolor: alpha(colors.text.primary, 0.08),
                    '& .MuiLinearProgress-bar': {
                      borderRadius: 4,
                      bgcolor: getQuotaColor(selectedKeyStats.today.quota_percent_used),
                    },
                  }}
                />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {selectedKeyStats.today.quota_percent_used.toFixed(1)}% used
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {selectedKeyStats.today.quota_remaining.toLocaleString()} / {selectedKeyStats.today.quota_limit.toLocaleString()} remaining
                  </Typography>
                </Box>
              </Box>

              {/* Top Endpoints */}
              {selectedKeyStats.top_endpoints.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" sx={{ mb: 2 }}>Top Endpoints</Typography>
                  {selectedKeyStats.top_endpoints.slice(0, 5).map((ep, i) => (
                    <Box
                      key={i}
                      sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        py: 1,
                        px: 2,
                        borderRadius: 1,
                        bgcolor: i % 2 === 0 ? alpha(colors.background.default, 0.3) : 'transparent',
                      }}
                    >
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {ep.endpoint}
                      </Typography>
                      <Chip label={ep.count.toLocaleString()} size="small" />
                    </Box>
                  ))}
                </Box>
              )}

              {/* Daily Breakdown */}
              {selectedKeyStats.daily_breakdown.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 2 }}>Daily Usage (Last 7 Days)</Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end', height: 100 }}>
                    {selectedKeyStats.daily_breakdown.slice(-7).map((day, i) => {
                      const maxRequests = Math.max(...selectedKeyStats.daily_breakdown.slice(-7).map(d => d.total));
                      const height = maxRequests > 0 ? (day.total / maxRequests) * 80 : 0;
                      return (
                        <Tooltip key={i} title={`${day.date}: ${day.total} requests`}>
                          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <Box
                              sx={{
                                width: '100%',
                                height: `${height}px`,
                                minHeight: 4,
                                borderRadius: 1,
                                bgcolor: colors.primary.main,
                                transition: 'height 0.3s ease',
                              }}
                            />
                            <Typography variant="caption" sx={{ mt: 1, color: 'text.secondary', fontSize: '0.65rem' }}>
                              {new Date(day.date).toLocaleDateString(undefined, { weekday: 'short' })}
                            </Typography>
                          </Box>
                        </Tooltip>
                      );
                    })}
                  </Box>
                </Box>
              )}
            </Box>
          ) : (
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">No statistics available</Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setStatsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default APIKeysPage;
