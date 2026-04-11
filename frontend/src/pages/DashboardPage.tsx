/**
 * Dashboard page with analytics overview and recent activity.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Typography,
  Button,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  alpha,
  Skeleton,
} from '@mui/material';
import {
  Description,
  ViewModule,
  CloudUpload,
  CheckCircle,
  Speed,
  ArrowForward,
  Visibility,
  AccessTime,
  Add,
  Refresh,
  Article,
  Assignment,
  Person,
  Schedule,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';
import StatsCard from '@/components/StatsCard';

interface Document {
  id: number;
  filename: string;
  status: string;
  created_at: string;
  page_count?: number;
}

interface ActivityItem {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  created_at: string;
  metadata_json?: any;
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [docsResponse, templatesResponse] = await Promise.all([
        apiService.listDocuments(),
        apiService.listTemplates(),
      ]);
      setDocuments(docsResponse || []);
      setTemplates(templatesResponse || []);

      // Try to load audit logs for activity
      try {
        const logsResponse = await apiService.listAuditLogs({ limit: 10 });
        setActivities(logsResponse?.items || []);
      } catch {
        setActivities([]);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'extracted':
        return 'success';
      case 'processing':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getActionIcon = (action: string) => {
    if (action.includes('document') || action.includes('upload')) {
      return <Article sx={{ fontSize: 18 }} />;
    }
    if (action.includes('template')) {
      return <Assignment sx={{ fontSize: 18 }} />;
    }
    if (action.includes('user') || action.includes('login')) {
      return <Person sx={{ fontSize: 18 }} />;
    }
    return <Schedule sx={{ fontSize: 18 }} />;
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const stats = {
    documents: documents.length,
    templates: templates.length,
    processed: documents.filter((d) => d.status === 'extracted').length,
    processing: documents.filter((d) => d.status === 'processing').length,
  };

  const recentDocuments = documents.slice(0, 5);

  return (
    <Box>
      {/* Welcome Header */}
      <Box
        sx={{
          mb: 4,
          p: 3,
          borderRadius: 3,
          background: `linear-gradient(135deg, ${alpha(colors.primary.main, 0.1)} 0%, ${alpha(colors.secondary.main, 0.05)} 100%)`,
          border: `1px solid ${alpha(colors.primary.main, 0.1)}`,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
              Welcome back, {user?.name?.split(' ')[0]}!
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary' }}>
              Here's what's happening with your documents today.
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button
              variant="contained"
              startIcon={<CloudUpload />}
              onClick={() => navigate('/documents')}
              sx={{ px: 3 }}
            >
              Upload Document
            </Button>
            <Button
              variant="outlined"
              startIcon={<Add />}
              onClick={() => navigate('/templates')}
            >
              New Template
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Total Documents"
            value={loading ? '...' : stats.documents}
            icon={<Description sx={{ fontSize: 24 }} />}
            color="primary"
            trend={{ value: 12, isPositive: true }}
            onClick={() => navigate('/documents')}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Active Templates"
            value={loading ? '...' : stats.templates}
            icon={<ViewModule sx={{ fontSize: 24 }} />}
            color="secondary"
            onClick={() => navigate('/templates')}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Processed / In Progress"
            value={loading ? '...' : `${stats.processed} / ${stats.processing}`}
            icon={<CheckCircle sx={{ fontSize: 24 }} />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Accuracy Rate"
            value="94%"
            icon={<Speed sx={{ fontSize: 24 }} />}
            color="warning"
            trend={{ value: 3, isPositive: true }}
          />
        </Grid>
      </Grid>

      {/* Main Content Grid */}
      <Grid container spacing={3}>
        {/* Recent Documents */}
        <Grid item xs={12} lg={8} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%', height: '100%' }}>
            <CardContent sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  p: 2.5,
                  borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                }}
              >
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Recent Documents
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    Latest uploaded documents
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Tooltip title="Refresh">
                    <IconButton size="small" onClick={loadDashboardData}>
                      <Refresh />
                    </IconButton>
                  </Tooltip>
                  <Button
                    size="small"
                    endIcon={<ArrowForward />}
                    onClick={() => navigate('/documents')}
                  >
                    View All
                  </Button>
                </Box>
              </Box>

              {loading ? (
                <Box sx={{ p: 2, flex: 1 }}>
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} height={60} sx={{ mb: 1 }} />
                  ))}
                </Box>
              ) : recentDocuments.length === 0 ? (
                <Box sx={{ p: 6, textAlign: 'center', flex: 1 }}>
                  <Description sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                  <Typography variant="h6" sx={{ color: 'text.secondary', mb: 1 }}>
                    No documents yet
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.disabled', mb: 3 }}>
                    Upload your first document to get started
                  </Typography>
                  <Button variant="contained" startIcon={<CloudUpload />} onClick={() => navigate('/documents')}>
                    Upload Document
                  </Button>
                </Box>
              ) : (
                <TableContainer sx={{ flex: 1 }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Document</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Pages</TableCell>
                        <TableCell>Date</TableCell>
                        <TableCell align="right">Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {recentDocuments.map((doc) => (
                        <TableRow key={doc.id} hover>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                              <Box
                                sx={{
                                  width: 36,
                                  height: 36,
                                  borderRadius: 1.5,
                                  bgcolor: alpha(colors.primary.main, 0.1),
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                }}
                              >
                                <Description sx={{ fontSize: 18, color: 'primary.main' }} />
                              </Box>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {doc.filename.length > 30 ? `${doc.filename.slice(0, 30)}...` : doc.filename}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={doc.status}
                              size="small"
                              color={getStatusColor(doc.status) as any}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                              {doc.page_count || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                              {formatTimeAgo(doc.created_at)}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Tooltip title="View Details">
                              <IconButton
                                size="small"
                                onClick={() => navigate(`/documents/${doc.id}/extractions`)}
                              >
                                <Visibility />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Activity Timeline */}
        <Grid item xs={12} lg={4} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%', height: '100%' }}>
            <CardContent sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  p: 2.5,
                  borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                }}
              >
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Recent Activity
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    Your latest actions
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
                {loading ? (
                  <Box>
                    {[1, 2, 3, 4].map((i) => (
                      <Skeleton key={i} height={50} sx={{ mb: 1 }} />
                    ))}
                  </Box>
                ) : activities.length === 0 ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <AccessTime sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
                    <Typography variant="body2" sx={{ color: 'text.disabled' }}>
                      No recent activity
                    </Typography>
                  </Box>
                ) : (
                  <Box>
                    {activities.map((activity, index) => (
                      <Box
                        key={activity.id}
                        sx={{
                          display: 'flex',
                          gap: 2,
                          py: 1.5,
                          borderBottom: index < activities.length - 1 ? `1px solid ${alpha(colors.text.primary, 0.06)}` : 'none',
                        }}
                      >
                        <Box
                          sx={{
                            width: 32,
                            height: 32,
                            borderRadius: 1,
                            bgcolor: alpha(colors.primary.main, 0.1),
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'primary.main',
                            flexShrink: 0,
                          }}
                        >
                          {getActionIcon(activity.action)}
                        </Box>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 500,
                              textTransform: 'capitalize',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {activity.action.replace(/_/g, ' ')}
                          </Typography>
                          <Typography variant="caption" sx={{ color: 'text.disabled' }}>
                            {formatTimeAgo(activity.created_at)}
                          </Typography>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Start Guide */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
                Quick Start Guide
              </Typography>
              <Grid container spacing={3}>
                {[
                  {
                    step: 1,
                    title: 'Upload Documents',
                    description: 'Upload PDF or image files for OCR processing',
                    icon: <CloudUpload />,
                    action: () => navigate('/documents'),
                  },
                  {
                    step: 2,
                    title: 'Create Templates',
                    description: 'Define extraction fields for your document types',
                    icon: <ViewModule />,
                    action: () => navigate('/templates'),
                  },
                  {
                    step: 3,
                    title: 'Apply & Extract',
                    description: 'Match templates to documents and extract data',
                    icon: <Assignment />,
                    action: () => navigate('/documents'),
                  },
                  {
                    step: 4,
                    title: 'Review Results',
                    description: 'Verify extractions and correct if needed',
                    icon: <CheckCircle />,
                    action: () => navigate('/documents'),
                  },
                ].map((item) => (
                  <Grid item xs={12} sm={6} md={3} key={item.step}>
                    <Box
                      onClick={item.action}
                      sx={{
                        p: 2.5,
                        borderRadius: 2,
                        border: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        '&:hover': {
                          borderColor: alpha(colors.primary.main, 0.3),
                          bgcolor: alpha(colors.primary.main, 0.04),
                        },
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1.5 }}>
                        <Box
                          sx={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            bgcolor: alpha(colors.primary.main, 0.1),
                            color: 'primary.main',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 700,
                            fontSize: '0.875rem',
                          }}
                        >
                          {item.step}
                        </Box>
                        <Box sx={{ color: 'primary.main' }}>{item.icon}</Box>
                      </Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                        {item.title}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {item.description}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
