/**
 * Entity management page for admin users.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Typography,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Alert,
  Chip,
  IconButton,
  Tooltip,
  alpha,
  Skeleton,
  Snackbar,
  Divider,
  InputAdornment,
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import {
  Add,
  Business,
  Close,
  Person,
  Email,
  Phone,
  Lock,
  Block,
  Receipt,
  Visibility,
  PersonAdd,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';

interface Entity {
  id: number;
  name: string;
  contact_email: string;
  contact_name: string;
  contact_phone?: string;
  subscription_tier: string;
  status: string;
  documents_used: number;
  monthly_document_limit: number;
  per_document_rate: number;
  revenue: number;
  created_at: string;
}

interface EntityDetail extends Entity {
  api_keys_count: number;
  total_documents: number;
  total_revenue: number;
}

const EntitiesPage: React.FC = () => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [openCreateDialog, setOpenCreateDialog] = useState(false);
  const [openDetailDialog, setOpenDetailDialog] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<EntityDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [newEntity, setNewEntity] = useState({
    name: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    subscription_tier: 'free',
    per_document_rate: 0,
    monthly_document_limit: 100,
  });
  const [newPortalUser, setNewPortalUser] = useState({
    name: '',
    email: '',
    password: '',
  });
  const [suspendConfirm, setSuspendConfirm] = useState(false);
  const [invoiceDates, setInvoiceDates] = useState({
    start: '',
    end: '',
  });

  useEffect(() => {
    loadEntities();
  }, []);

  const loadEntities = async () => {
    try {
      const data = await apiService.listEntities();
      setEntities(data || []);
    } catch (err) {
      console.error('Failed to load entities:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEntity = async () => {
    setError('');
    try {
      await apiService.createEntity(newEntity);
      setOpenCreateDialog(false);
      setNewEntity({
        name: '',
        contact_name: '',
        contact_email: '',
        contact_phone: '',
        subscription_tier: 'free',
        per_document_rate: 0,
        monthly_document_limit: 100,
      });
      setSnackbar({ open: true, message: 'Entity created successfully', severity: 'success' });
      loadEntities();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create entity');
    }
  };

  const handleRowClick = async (params: any) => {
    setDetailLoading(true);
    setOpenDetailDialog(true);
    try {
      const data = await apiService.getEntity(params.id);
      setSelectedEntity(data);
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to load entity details', severity: 'error' });
      setOpenDetailDialog(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSuspendEntity = async () => {
    if (!selectedEntity) return;
    try {
      await apiService.suspendEntity(selectedEntity.id);
      setSuspendConfirm(false);
      setOpenDetailDialog(false);
      setSnackbar({ open: true, message: 'Entity suspended successfully', severity: 'success' });
      loadEntities();
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to suspend entity', severity: 'error' });
    }
  };

  const handleCreatePortalUser = async () => {
    if (!selectedEntity) return;
    try {
      await apiService.createEntityUser(selectedEntity.id, newPortalUser);
      setNewPortalUser({ name: '', email: '', password: '' });
      setSnackbar({ open: true, message: 'Portal user created successfully', severity: 'success' });
      // Refresh entity detail
      const data = await apiService.getEntity(selectedEntity.id);
      setSelectedEntity(data);
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to create portal user', severity: 'error' });
    }
  };

  const handleGenerateInvoice = async () => {
    if (!selectedEntity || !invoiceDates.start || !invoiceDates.end) return;
    try {
      await apiService.generateInvoice(selectedEntity.id, invoiceDates.start, invoiceDates.end);
      setInvoiceDates({ start: '', end: '' });
      setSnackbar({ open: true, message: 'Invoice generated successfully', severity: 'success' });
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to generate invoice', severity: 'error' });
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'enterprise':
        return colors.secondary.main;
      case 'pro':
        return colors.primary.main;
      case 'starter':
        return colors.warning.main;
      default:
        return colors.info.main;
    }
  };

  const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'success';
      case 'suspended':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      minWidth: 180,
    },
    {
      field: 'contact_email',
      headerName: 'Contact Email',
      flex: 1,
      minWidth: 200,
    },
    {
      field: 'subscription_tier',
      headerName: 'Tier',
      width: 130,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          size="small"
          sx={{
            bgcolor: alpha(getTierColor(params.value), 0.15),
            color: getTierColor(params.value),
            fontWeight: 500,
            textTransform: 'capitalize',
          }}
        />
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value}
          size="small"
          color={getStatusColor(params.value)}
          sx={{ textTransform: 'capitalize' }}
        />
      ),
    },
    {
      field: 'documents_used',
      headerName: 'Docs Used/Limit',
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {params.row.documents_used} / {params.row.monthly_document_limit}
        </Typography>
      ),
    },
    {
      field: 'revenue',
      headerName: 'Revenue',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {'\u20B9'}{Number(params.value || 0).toLocaleString('en-IN')}
        </Typography>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 100,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Tooltip title="View Details">
          <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleRowClick(params.row); }}>
            <Visibility />
          </IconButton>
        </Tooltip>
      ),
    },
  ];

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Entity Management
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            Manage entities, subscriptions, and billing
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={() => setOpenCreateDialog(true)} sx={{ px: 3 }}>
          Add Entity
        </Button>
      </Box>

      {/* Entities DataGrid */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          {loading ? (
            <Box sx={{ p: 3 }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height={60} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : entities.length === 0 ? (
            <Box sx={{ p: 6, textAlign: 'center' }}>
              <Box
                sx={{
                  width: 80,
                  height: 80,
                  borderRadius: 3,
                  bgcolor: alpha(colors.primary.main, 0.1),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mx: 'auto',
                  mb: 3,
                }}
              >
                <Business sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
              <Typography variant="h6" sx={{ mb: 1 }}>
                No Entities Yet
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
                Add entities to manage client organizations
              </Typography>
              <Button variant="contained" startIcon={<Add />} onClick={() => setOpenCreateDialog(true)}>
                Add First Entity
              </Button>
            </Box>
          ) : (
            <DataGrid
              rows={entities}
              columns={columns}
              onRowClick={handleRowClick}
              autoHeight
              pageSizeOptions={[10, 25, 50]}
              initialState={{
                pagination: { paginationModel: { pageSize: 10 } },
              }}
              disableRowSelectionOnClick
              sx={{
                border: 'none',
                '& .MuiDataGrid-row': {
                  cursor: 'pointer',
                },
                '& .MuiDataGrid-cell:focus': {
                  outline: 'none',
                },
              }}
            />
          )}
        </CardContent>
      </Card>

      {/* Create Entity Dialog */}
      <Dialog open={openCreateDialog} onClose={() => setOpenCreateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Add New Entity</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
            Create a new client entity with subscription settings.
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          <TextField
            fullWidth
            label="Entity Name"
            value={newEntity.name}
            onChange={(e) => setNewEntity({ ...newEntity, name: e.target.value })}
            margin="normal"
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Business sx={{ color: 'text.secondary' }} />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            fullWidth
            label="Contact Name"
            value={newEntity.contact_name}
            onChange={(e) => setNewEntity({ ...newEntity, contact_name: e.target.value })}
            margin="normal"
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Person sx={{ color: 'text.secondary' }} />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            fullWidth
            label="Contact Email"
            type="email"
            value={newEntity.contact_email}
            onChange={(e) => setNewEntity({ ...newEntity, contact_email: e.target.value })}
            margin="normal"
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Email sx={{ color: 'text.secondary' }} />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            fullWidth
            label="Contact Phone"
            value={newEntity.contact_phone}
            onChange={(e) => setNewEntity({ ...newEntity, contact_phone: e.target.value })}
            margin="normal"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Phone sx={{ color: 'text.secondary' }} />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            fullWidth
            select
            label="Subscription Tier"
            value={newEntity.subscription_tier}
            onChange={(e) => setNewEntity({ ...newEntity, subscription_tier: e.target.value })}
            margin="normal"
            required
          >
            <MenuItem value="free">Free</MenuItem>
            <MenuItem value="starter">Starter</MenuItem>
            <MenuItem value="pro">Pro</MenuItem>
            <MenuItem value="enterprise">Enterprise</MenuItem>
          </TextField>
          <TextField
            fullWidth
            label="Per Document Rate"
            type="number"
            value={newEntity.per_document_rate}
            onChange={(e) => setNewEntity({ ...newEntity, per_document_rate: Number(e.target.value) })}
            margin="normal"
            InputProps={{
              startAdornment: <InputAdornment position="start">{'\u20B9'}</InputAdornment>,
            }}
          />
          <TextField
            fullWidth
            label="Monthly Document Limit"
            type="number"
            value={newEntity.monthly_document_limit}
            onChange={(e) => setNewEntity({ ...newEntity, monthly_document_limit: Number(e.target.value) })}
            margin="normal"
          />
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setOpenCreateDialog(false)}>Cancel</Button>
          <Button
            onClick={handleCreateEntity}
            variant="contained"
            disabled={!newEntity.name || !newEntity.contact_name || !newEntity.contact_email}
          >
            Create Entity
          </Button>
        </DialogActions>
      </Dialog>

      {/* Entity Detail Dialog */}
      <Dialog open={openDetailDialog} onClose={() => { setOpenDetailDialog(false); setSelectedEntity(null); }} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 600 }}>
          Entity Details
          <IconButton size="small" onClick={() => { setOpenDetailDialog(false); setSelectedEntity(null); }}>
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {detailLoading ? (
            <Box sx={{ p: 3 }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height={40} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : selectedEntity ? (
            <Box>
              {/* Entity Info */}
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                {selectedEntity.name}
              </Typography>
              <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap', mb: 3 }}>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Contact</Typography>
                  <Typography variant="body2">{selectedEntity.contact_name}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Email</Typography>
                  <Typography variant="body2">{selectedEntity.contact_email}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Phone</Typography>
                  <Typography variant="body2">{selectedEntity.contact_phone || 'N/A'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Tier</Typography>
                  <Box>
                    <Chip
                      label={selectedEntity.subscription_tier}
                      size="small"
                      sx={{
                        bgcolor: alpha(getTierColor(selectedEntity.subscription_tier), 0.15),
                        color: getTierColor(selectedEntity.subscription_tier),
                        fontWeight: 500,
                        textTransform: 'capitalize',
                      }}
                    />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Status</Typography>
                  <Box>
                    <Chip
                      label={selectedEntity.status}
                      size="small"
                      color={getStatusColor(selectedEntity.status)}
                      sx={{ textTransform: 'capitalize' }}
                    />
                  </Box>
                </Box>
              </Box>

              {/* Usage Stats */}
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>Usage Stats</Typography>
              <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap', mb: 3 }}>
                <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(colors.primary.main, 0.08), minWidth: 140 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>{selectedEntity.total_documents}</Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Total Documents</Typography>
                </Box>
                <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(colors.success.main, 0.08), minWidth: 140 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>{'\u20B9'}{Number(selectedEntity.total_revenue || 0).toLocaleString('en-IN')}</Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Total Revenue</Typography>
                </Box>
                <Box sx={{ p: 2, borderRadius: 2, bgcolor: alpha(colors.warning.main, 0.08), minWidth: 140 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>{selectedEntity.api_keys_count}</Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>API Keys</Typography>
                </Box>
              </Box>

              {/* Create Portal User */}
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                <PersonAdd sx={{ fontSize: 20, verticalAlign: 'middle', mr: 1 }} />
                Create Portal User
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-end', mb: 3 }}>
                <TextField
                  size="small"
                  label="Name"
                  value={newPortalUser.name}
                  onChange={(e) => setNewPortalUser({ ...newPortalUser, name: e.target.value })}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Person sx={{ fontSize: 18, color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  size="small"
                  label="Email"
                  type="email"
                  value={newPortalUser.email}
                  onChange={(e) => setNewPortalUser({ ...newPortalUser, email: e.target.value })}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Email sx={{ fontSize: 18, color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  size="small"
                  label="Password"
                  type="password"
                  value={newPortalUser.password}
                  onChange={(e) => setNewPortalUser({ ...newPortalUser, password: e.target.value })}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Lock sx={{ fontSize: 18, color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                  }}
                />
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<PersonAdd />}
                  onClick={handleCreatePortalUser}
                  disabled={!newPortalUser.name || !newPortalUser.email || !newPortalUser.password}
                >
                  Create User
                </Button>
              </Box>

              {/* Generate Invoice */}
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                <Receipt sx={{ fontSize: 20, verticalAlign: 'middle', mr: 1 }} />
                Generate Invoice
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-end', mb: 3 }}>
                <TextField
                  size="small"
                  label="Start Date"
                  type="date"
                  value={invoiceDates.start}
                  onChange={(e) => setInvoiceDates({ ...invoiceDates, start: e.target.value })}
                  InputLabelProps={{ shrink: true }}
                />
                <TextField
                  size="small"
                  label="End Date"
                  type="date"
                  value={invoiceDates.end}
                  onChange={(e) => setInvoiceDates({ ...invoiceDates, end: e.target.value })}
                  InputLabelProps={{ shrink: true }}
                />
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Receipt />}
                  onClick={handleGenerateInvoice}
                  disabled={!invoiceDates.start || !invoiceDates.end}
                >
                  Generate Invoice
                </Button>
              </Box>
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions sx={{ p: 2.5, justifyContent: 'space-between' }}>
          <Button
            color="error"
            variant="outlined"
            startIcon={<Block />}
            onClick={() => setSuspendConfirm(true)}
            disabled={selectedEntity?.status === 'suspended'}
          >
            Suspend Entity
          </Button>
          <Button onClick={() => { setOpenDetailDialog(false); setSelectedEntity(null); }}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Suspend Confirmation Dialog */}
      <Dialog open={suspendConfirm} onClose={() => setSuspendConfirm(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Confirm Suspension</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            Are you sure you want to suspend <strong>{selectedEntity?.name}</strong>? This will disable all API access and portal users for this entity.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setSuspendConfirm(false)}>Cancel</Button>
          <Button onClick={handleSuspendEntity} variant="contained" color="error">
            Suspend
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
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

export default EntitiesPage;
