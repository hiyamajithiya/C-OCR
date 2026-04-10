/**
 * Entity self-service dashboard page.
 * Comprehensive single-page dashboard with overview, API keys, documents, billing, and webhooks.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Checkbox,
  Alert,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Snackbar,
  alpha,
  Skeleton,
} from '@mui/material';
import {
  Add,
  ContentCopy,
  Delete,
  ExpandMore,
  Refresh,
  Send,
  Description,
  Key,
  Receipt,
  Settings,
} from '@mui/icons-material';
import { usePortalAuth } from '@/contexts/PortalAuthContext';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';

// ─── Types ───────────────────────────────────────────────────────────────────

interface DashboardOverview {
  entity_name: string;
  subscription_tier: string;
  documents_used: number;
  monthly_limit: number;
  current_month_charges: number;
}

interface APIKeyItem {
  id: number;
  name: string;
  key_prefix: string;
  rate_limit: number;
  status: string;
  created_at: string;
}

interface DocumentItem {
  id: number;
  filename: string;
  status: string;
  created_at: string;
}

interface InvoiceItem {
  id: number;
  invoice_number: string;
  period: string;
  documents: number;
  amount: number;
  status: string;
  date: string;
}

interface BillingData {
  invoices: InvoiceItem[];
  current_month_charges: number;
}

interface WebhookEvent {
  id: number;
  event_type: string;
  status: string;
  attempts: number;
  created_at: string;
}

interface WebhookData {
  configured: boolean;
  url?: string;
  events: WebhookEvent[];
}

interface CreateKeyFormData {
  name: string;
  scopes: string[];
  rate_limit: number;
  daily_quota: number;
}

// ─── Available scopes ────────────────────────────────────────────────────────

const AVAILABLE_SCOPES = [
  'documents:read',
  'documents:write',
  'templates:read',
  'templates:write',
  'extractions:read',
  'extractions:write',
];

// ─── Component ───────────────────────────────────────────────────────────────

const PortalDashboardPage: React.FC = () => {
  const { portalUser } = usePortalAuth();

  // Data states
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [apiKeys, setApiKeys] = useState<APIKeyItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [billing, setBilling] = useState<BillingData | null>(null);
  const [webhooks, setWebhooks] = useState<WebhookData | null>(null);

  // Loading states
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingBilling, setLoadingBilling] = useState(true);
  const [loadingWebhooks, setLoadingWebhooks] = useState(true);

  // Create API Key dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState<CreateKeyFormData>({
    name: '',
    scopes: [],
    rate_limit: 100,
    daily_quota: 1000,
  });
  const [creatingKey, setCreatingKey] = useState(false);
  const [newRawKey, setNewRawKey] = useState<string | null>(null);

  // Webhook test
  const [testingWebhook, setTestingWebhook] = useState(false);

  // Snackbar
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });

  // ─── Data Loading ────────────────────────────────────────────────────────

  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);
    try {
      const data = await apiService.getPortalDashboard();
      setOverview(data);
    } catch (error) {
      console.error('Failed to load overview:', error);
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  const loadApiKeys = useCallback(async () => {
    setLoadingKeys(true);
    try {
      const data = await apiService.getPortalAPIKeys();
      setApiKeys(data || []);
    } catch (error) {
      console.error('Failed to load API keys:', error);
    } finally {
      setLoadingKeys(false);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const data = await apiService.getPortalDocuments();
      setDocuments(data || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  const loadBilling = useCallback(async () => {
    setLoadingBilling(true);
    try {
      const data = await apiService.getPortalBilling();
      setBilling(data);
    } catch (error) {
      console.error('Failed to load billing:', error);
    } finally {
      setLoadingBilling(false);
    }
  }, []);

  const loadWebhooks = useCallback(async () => {
    setLoadingWebhooks(true);
    try {
      const data = await apiService.getPortalWebhooks();
      setWebhooks(data);
    } catch (error) {
      console.error('Failed to load webhooks:', error);
    } finally {
      setLoadingWebhooks(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
    loadApiKeys();
    loadDocuments();
    loadBilling();
    loadWebhooks();
  }, [loadOverview, loadApiKeys, loadDocuments, loadBilling, loadWebhooks]);

  // ─── Handlers ────────────────────────────────────────────────────────────

  const handleCreateKey = async () => {
    if (!createForm.name.trim()) return;

    setCreatingKey(true);
    try {
      const result = await apiService.createPortalAPIKey({
        name: createForm.name,
        scopes: createForm.scopes,
        rate_limit: createForm.rate_limit,
        daily_quota: createForm.daily_quota,
      });
      setNewRawKey(result.raw_key || result.key);
      setSnackbar({ open: true, message: 'API key created successfully', severity: 'success' });
      loadApiKeys();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to create API key';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeKey = async (id: number) => {
    try {
      await apiService.revokePortalAPIKey(id);
      setSnackbar({ open: true, message: 'API key revoked', severity: 'success' });
      loadApiKeys();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to revoke API key';
      setSnackbar({ open: true, message, severity: 'error' });
    }
  };

  const handleTestWebhook = async () => {
    setTestingWebhook(true);
    try {
      await apiService.testPortalWebhook();
      setSnackbar({ open: true, message: 'Webhook test sent successfully', severity: 'success' });
      loadWebhooks();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Webhook test failed';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setTestingWebhook(false);
    }
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setSnackbar({ open: true, message: 'Copied to clipboard', severity: 'info' });
  };

  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false);
    setCreateForm({ name: '', scopes: [], rate_limit: 100, daily_quota: 1000 });
    setNewRawKey(null);
  };

  const handleScopeToggle = (scope: string) => {
    setCreateForm((prev) => ({
      ...prev,
      scopes: prev.scopes.includes(scope)
        ? prev.scopes.filter((s) => s !== scope)
        : [...prev.scopes, scope],
    }));
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' | 'info' => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'paid':
      case 'extracted':
      case 'delivered':
      case 'success':
        return 'success';
      case 'processing':
      case 'pending':
        return 'warning';
      case 'revoked':
      case 'error':
      case 'failed':
      case 'overdue':
        return 'error';
      default:
        return 'default';
    }
  };

  const usagePercent = overview
    ? Math.min((overview.documents_used / overview.monthly_limit) * 100, 100)
    : 0;

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <Box>
      {/* ─── Section 1: Overview Cards ─── */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Entity Name + Tier */}
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              {loadingOverview ? (
                <>
                  <Skeleton width="60%" height={24} />
                  <Skeleton width="40%" height={32} sx={{ mt: 1 }} />
                </>
              ) : (
                <>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>
                    Entity
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
                    {overview?.entity_name || portalUser?.entity_name || '-'}
                  </Typography>
                  <Chip
                    label={overview?.subscription_tier || 'Free'}
                    color="primary"
                    size="small"
                  />
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Documents Usage */}
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              {loadingOverview ? (
                <>
                  <Skeleton width="60%" height={24} />
                  <Skeleton width="80%" height={32} sx={{ mt: 1 }} />
                  <Skeleton width="100%" height={8} sx={{ mt: 2 }} />
                </>
              ) : (
                <>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>
                    Documents Used
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
                    {overview?.documents_used?.toLocaleString() || 0}
                    <Typography
                      component="span"
                      variant="body2"
                      sx={{ color: 'text.secondary', ml: 0.5 }}
                    >
                      / {overview?.monthly_limit?.toLocaleString() || 0}
                    </Typography>
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={usagePercent}
                    color={usagePercent > 90 ? 'error' : usagePercent > 70 ? 'warning' : 'primary'}
                    sx={{ mt: 1.5, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, display: 'block' }}>
                    {usagePercent.toFixed(1)}% of monthly limit
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Current Month Charges */}
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              {loadingOverview ? (
                <>
                  <Skeleton width="60%" height={24} />
                  <Skeleton width="50%" height={32} sx={{ mt: 1 }} />
                </>
              ) : (
                <>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>
                    Current Month Charges
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {formatCurrency(overview?.current_month_charges || 0)}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* ─── Section 2: API Keys ─── */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 0 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              p: 2.5,
              borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Key sx={{ color: 'primary.main' }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                API Keys
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Refresh">
                <IconButton size="small" onClick={loadApiKeys}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              <Button
                variant="contained"
                size="small"
                startIcon={<Add />}
                onClick={() => setCreateDialogOpen(true)}
              >
                Create API Key
              </Button>
            </Box>
          </Box>

          {loadingKeys ? (
            <Box sx={{ p: 2 }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height={50} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : apiKeys.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Key sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                No API keys yet. Create one to get started.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Key Prefix</TableCell>
                    <TableCell>Rate Limit</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {apiKeys.map((key) => (
                    <TableRow key={key.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {key.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {key.key_prefix}...
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                          {key.rate_limit}/min
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={key.status}
                          size="small"
                          color={getStatusColor(key.status)}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                          {formatDate(key.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {key.status === 'active' && (
                          <Tooltip title="Revoke Key">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleRevokeKey(key.id)}
                            >
                              <Delete />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* ─── Section 3: Recent Documents ─── */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 0 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              p: 2.5,
              borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Description sx={{ color: 'primary.main' }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Recent Documents
              </Typography>
            </Box>
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={loadDocuments}>
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>

          {loadingDocs ? (
            <Box sx={{ p: 2 }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height={50} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : documents.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Description sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                No documents processed yet.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Filename</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created At</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          #{doc.id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {doc.filename.length > 40
                            ? `${doc.filename.slice(0, 40)}...`
                            : doc.filename}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={doc.status}
                          size="small"
                          color={getStatusColor(doc.status)}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                          {formatDate(doc.created_at)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* ─── Section 4: Billing ─── */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 0 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              p: 2.5,
              borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Receipt sx={{ color: 'primary.main' }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Billing
              </Typography>
            </Box>
            {billing && (
              <Chip
                label={`Current month: ${formatCurrency(billing.current_month_charges)}`}
                color="info"
                size="small"
              />
            )}
          </Box>

          {loadingBilling ? (
            <Box sx={{ p: 2 }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height={50} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : !billing || billing.invoices.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Receipt sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                No invoices yet.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Invoice #</TableCell>
                    <TableCell>Period</TableCell>
                    <TableCell>Documents</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Date</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {billing.invoices.map((invoice) => (
                    <TableRow key={invoice.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {invoice.invoice_number}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                          {invoice.period}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {invoice.documents.toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {formatCurrency(invoice.amount)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={invoice.status}
                          size="small"
                          color={getStatusColor(invoice.status)}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                          {formatDate(invoice.date)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* ─── Section 5: Webhooks (Expandable) ─── */}
      <Accordion
        defaultExpanded={false}
        sx={{
          bgcolor: 'background.paper',
          '&:before': { display: 'none' },
          borderRadius: '16px !important',
          border: `1px solid ${alpha(colors.primary.main, 0.1)}`,
          mb: 4,
        }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Settings sx={{ color: 'primary.main' }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Webhooks
            </Typography>
            {webhooks?.configured && (
              <Chip label="Configured" color="success" size="small" sx={{ ml: 1 }} />
            )}
          </Box>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0 }}>
          {loadingWebhooks ? (
            <Box sx={{ p: 2 }}>
              {[1, 2].map((i) => (
                <Skeleton key={i} height={50} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : (
            <Box>
              {/* Webhook status */}
              <Box
                sx={{
                  px: 2.5,
                  pb: 2,
                  borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Box>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    Status: {webhooks?.configured ? 'Active' : 'Not configured'}
                  </Typography>
                  {webhooks?.url && (
                    <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                      {webhooks.url}
                    </Typography>
                  )}
                </Box>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Send />}
                  onClick={handleTestWebhook}
                  disabled={testingWebhook || !webhooks?.configured}
                >
                  {testingWebhook ? 'Sending...' : 'Test Webhook'}
                </Button>
              </Box>

              {/* Recent webhook events */}
              {!webhooks?.events || webhooks.events.length === 0 ? (
                <Box sx={{ p: 4, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    No webhook events yet.
                  </Typography>
                </Box>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Event Type</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Attempts</TableCell>
                        <TableCell>Created At</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {webhooks.events.map((event) => (
                        <TableRow key={event.id} hover>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 500 }}>
                              {event.event_type}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={event.status}
                              size="small"
                              color={getStatusColor(event.status)}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{event.attempts}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                              {formatDate(event.created_at)}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}
        </AccordionDetails>
      </Accordion>

      {/* ─── Create API Key Dialog ─── */}
      <Dialog
        open={createDialogOpen}
        onClose={handleCloseCreateDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 600 }}>
          {newRawKey ? 'API Key Created' : 'Create API Key'}
        </DialogTitle>
        <DialogContent>
          {newRawKey ? (
            <Box sx={{ mt: 1 }}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Copy this key now. You will not be able to see it again.
              </Alert>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  p: 2,
                  bgcolor: alpha(colors.background.default, 0.5),
                  borderRadius: 2,
                  border: `1px solid ${alpha(colors.text.primary, 0.15)}`,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    fontFamily: 'monospace',
                    flex: 1,
                    wordBreak: 'break-all',
                  }}
                >
                  {newRawKey}
                </Typography>
                <Tooltip title="Copy to clipboard">
                  <IconButton size="small" onClick={() => handleCopyKey(newRawKey)}>
                    <ContentCopy fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          ) : (
            <Box sx={{ mt: 1 }}>
              <TextField
                fullWidth
                label="Key Name"
                value={createForm.name}
                onChange={(e) => setCreateForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Production API Key"
                sx={{ mb: 3 }}
              />

              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                Scopes
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0, mb: 3 }}>
                {AVAILABLE_SCOPES.map((scope) => (
                  <FormControlLabel
                    key={scope}
                    control={
                      <Checkbox
                        checked={createForm.scopes.includes(scope)}
                        onChange={() => handleScopeToggle(scope)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {scope}
                      </Typography>
                    }
                    sx={{ width: '48%' }}
                  />
                ))}
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Rate Limit (req/min)"
                    type="number"
                    value={createForm.rate_limit}
                    onChange={(e) =>
                      setCreateForm((prev) => ({
                        ...prev,
                        rate_limit: parseInt(e.target.value, 10) || 0,
                      }))
                    }
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Daily Quota"
                    type="number"
                    value={createForm.daily_quota}
                    onChange={(e) =>
                      setCreateForm((prev) => ({
                        ...prev,
                        daily_quota: parseInt(e.target.value, 10) || 0,
                      }))
                    }
                  />
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          {newRawKey ? (
            <Button variant="contained" onClick={handleCloseCreateDialog}>
              Done
            </Button>
          ) : (
            <>
              <Button onClick={handleCloseCreateDialog}>Cancel</Button>
              <Button
                variant="contained"
                onClick={handleCreateKey}
                disabled={creatingKey || !createForm.name.trim()}
              >
                {creatingKey ? <CircularProgress size={20} /> : 'Create'}
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>

      {/* ─── Snackbar ─── */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default PortalDashboardPage;
