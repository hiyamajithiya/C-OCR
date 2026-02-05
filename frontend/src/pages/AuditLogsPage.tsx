/**
 * Audit Logs page with enhanced dark theme UI.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  alpha,
  Skeleton,
} from '@mui/material';
import {
  History,
  Refresh,
  Visibility,
  Person,
  Key,
  Description,
  ViewModule,
  Login,
  Add,
  Edit,
  Delete,
  Close,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';

interface AuditLog {
  id: number;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  actor_user_id: number | null;
  actor_api_key_id: number | null;
  ip: string | null;
  created_at: string;
  metadata_json: any;
}

const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [filterAction, setFilterAction] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    loadLogs();
  }, [page, rowsPerPage, filterAction]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await apiService.listAuditLogs({
        action: filterAction || undefined,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      });
      setLogs(data);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const getActionConfig = (action: string) => {
    const configs: Record<string, { color: string; icon: React.ReactNode }> = {
      user_login: { color: colors.success.main, icon: <Login sx={{ fontSize: 16 }} /> },
      document_upload: { color: colors.primary.main, icon: <Add sx={{ fontSize: 16 }} /> },
      document_download: { color: colors.secondary.main, icon: <Description sx={{ fontSize: 16 }} /> },
      document_delete: { color: colors.error.main, icon: <Delete sx={{ fontSize: 16 }} /> },
      template_create: { color: colors.primary.main, icon: <ViewModule sx={{ fontSize: 16 }} /> },
      template_update: { color: colors.warning.main, icon: <Edit sx={{ fontSize: 16 }} /> },
      template_apply: { color: colors.success.main, icon: <ViewModule sx={{ fontSize: 16 }} /> },
      api_key_create: { color: colors.warning.main, icon: <Key sx={{ fontSize: 16 }} /> },
      api_key_revoke: { color: colors.error.main, icon: <Key sx={{ fontSize: 16 }} /> },
      user_create: { color: colors.primary.main, icon: <Person sx={{ fontSize: 16 }} /> },
      user_update: { color: colors.warning.main, icon: <Person sx={{ fontSize: 16 }} /> },
      correction_submit: { color: colors.info.main, icon: <Edit sx={{ fontSize: 16 }} /> },
    };
    return configs[action] || { color: colors.text.secondary, icon: <History sx={{ fontSize: 16 }} /> };
  };

  const formatAction = (action: string) => {
    return action
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const handleViewDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setDetailsOpen(true);
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Audit Logs
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.secondary' }}>
          Complete activity history and system logs
        </Typography>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ py: 2, display: 'flex', gap: 2, alignItems: 'center', justifyContent: 'space-between' }}>
          <TextField
            select
            label="Filter by Action"
            value={filterAction}
            onChange={(e) => {
              setFilterAction(e.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 200 }}
            size="small"
          >
            <MenuItem value="">All Actions</MenuItem>
            <MenuItem value="user_login">User Login</MenuItem>
            <MenuItem value="document_upload">Document Upload</MenuItem>
            <MenuItem value="document_download">Document Download</MenuItem>
            <MenuItem value="document_delete">Document Delete</MenuItem>
            <MenuItem value="template_create">Template Create</MenuItem>
            <MenuItem value="template_update">Template Update</MenuItem>
            <MenuItem value="template_apply">Template Apply</MenuItem>
            <MenuItem value="api_key_create">API Key Create</MenuItem>
            <MenuItem value="api_key_revoke">API Key Revoke</MenuItem>
            <MenuItem value="user_create">User Create</MenuItem>
            <MenuItem value="correction_submit">Correction Submit</MenuItem>
          </TextField>
          <Tooltip title="Refresh">
            <IconButton onClick={loadLogs}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          {loading ? (
            <Box sx={{ p: 3 }}>
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} height={50} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : logs.length === 0 ? (
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
                <History sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
              <Typography variant="h6" sx={{ mb: 1 }}>
                No Audit Logs
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Activity logs will appear here as users interact with the system.
              </Typography>
            </Box>
          ) : (
            <>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Action</TableCell>
                      <TableCell>Entity</TableCell>
                      <TableCell>Actor</TableCell>
                      <TableCell>IP Address</TableCell>
                      <TableCell align="right">Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {logs.map((log) => {
                      const actionConfig = getActionConfig(log.action);
                      return (
                        <TableRow key={log.id} hover>
                          <TableCell>
                            <Typography variant="body2">
                              {new Date(log.created_at).toLocaleString()}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              icon={actionConfig.icon}
                              label={formatAction(log.action)}
                              size="small"
                              sx={{
                                bgcolor: alpha(actionConfig.color, 0.15),
                                color: actionConfig.color,
                                fontWeight: 500,
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                              {log.entity_type ? (
                                <>
                                  {log.entity_type}
                                  {log.entity_id && <span> #{log.entity_id}</span>}
                                </>
                              ) : (
                                '-'
                              )}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {log.actor_user_id ? (
                                <>
                                  <Person sx={{ fontSize: 16, color: 'text.secondary' }} />
                                  <Typography variant="body2">User #{log.actor_user_id}</Typography>
                                </>
                              ) : log.actor_api_key_id ? (
                                <>
                                  <Key sx={{ fontSize: 16, color: 'text.secondary' }} />
                                  <Typography variant="body2">API Key #{log.actor_api_key_id}</Typography>
                                </>
                              ) : (
                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                  -
                                </Typography>
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>
                              {log.ip || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            {log.metadata_json && (
                              <Tooltip title="View Details">
                                <IconButton size="small" onClick={() => handleViewDetails(log)}>
                                  <Visibility />
                                </IconButton>
                              </Tooltip>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={-1}
                page={page}
                onPageChange={(_, newPage) => setPage(newPage)}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={(e) => {
                  setRowsPerPage(parseInt(e.target.value, 10));
                  setPage(0);
                }}
                rowsPerPageOptions={[10, 25, 50, 100]}
                sx={{ borderTop: `1px solid ${alpha(colors.text.primary, 0.08)}` }}
              />
            </>
          )}
        </CardContent>
      </Card>

      {/* Details Dialog */}
      <Dialog open={detailsOpen} onClose={() => setDetailsOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Log Details</Typography>
          <IconButton onClick={() => setDetailsOpen(false)}>
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedLog && (
            <Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Action
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {formatAction(selectedLog.action)}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  Timestamp
                </Typography>
                <Typography variant="body1">
                  {new Date(selectedLog.created_at).toLocaleString()}
                </Typography>
              </Box>
              {selectedLog.metadata_json && (
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Metadata
                  </Typography>
                  <Box
                    sx={{
                      mt: 1,
                      p: 2,
                      borderRadius: 2,
                      bgcolor: alpha(colors.background.default, 0.5),
                      border: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                      overflow: 'auto',
                      maxHeight: 300,
                    }}
                  >
                    <pre style={{ margin: 0, fontSize: '0.8rem', fontFamily: 'monospace' }}>
                      {JSON.stringify(selectedLog.metadata_json, null, 2)}
                    </pre>
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AuditLogsPage;
