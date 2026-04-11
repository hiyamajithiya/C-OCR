/**
 * Analytics dashboard page for admin users.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  alpha,
  Skeleton,
} from '@mui/material';
import {
  Description,
  Business,
  AttachMoney,
  Api,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';
import StatsCard from '@/components/StatsCard';

interface OverviewStats {
  total_documents: number;
  total_entities: number;
  active_entities: number;
  total_revenue: number;
  api_calls_this_month: number;
  api_calls_last_month: number;
}

interface UsageTrend {
  date: string;
  document_count: number;
  api_calls: number;
  revenue: number;
}

interface TopEntity {
  entity_id: number;
  entity_name: string;
  document_count: number;
  revenue: number;
}

interface EndpointStat {
  endpoint: string;
  count: number;
  avg_response_time_ms: number;
}

interface ErrorSummary {
  date: string;
  error_count: number;
  client_errors: number;
  server_errors: number;
}

const AnalyticsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<OverviewStats>({
    total_documents: 0,
    total_entities: 0,
    active_entities: 0,
    total_revenue: 0,
    api_calls_this_month: 0,
    api_calls_last_month: 0,
  });
  const [usageTrends, setUsageTrends] = useState<UsageTrend[]>([]);
  const [topEntities, setTopEntities] = useState<TopEntity[]>([]);
  const [endpoints, setEndpoints] = useState<EndpointStat[]>([]);
  const [errors, setErrors] = useState<ErrorSummary[]>([]);

  useEffect(() => {
    loadAnalyticsData();
  }, []);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      const [overviewData, usageData, entitiesData, endpointsData, errorsData] = await Promise.all([
        apiService.getAnalyticsOverview(),
        apiService.getAnalyticsUsage('daily', 30),
        apiService.getAnalyticsTopEntities(10),
        apiService.getAnalyticsEndpoints(),
        apiService.getAnalyticsErrors(),
      ]);
      setOverview(overviewData || { total_documents: 0, total_entities: 0, active_entities: 0, total_revenue: 0, api_calls_this_month: 0, api_calls_last_month: 0 });
      setUsageTrends(usageData || []);
      setTopEntities(entitiesData || []);
      setEndpoints(endpointsData || []);
      setErrors(errorsData || []);
    } catch (error) {
      console.error('Failed to load analytics data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return '\u20B9' + Number(value || 0).toLocaleString('en-IN');
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Analytics
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.secondary' }}>
          Platform metrics and usage insights
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Total Documents"
            value={loading ? '...' : overview.total_documents}
            icon={<Description sx={{ fontSize: 24 }} />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Active Entities"
            value={loading ? '...' : overview.active_entities}
            icon={<Business sx={{ fontSize: 24 }} />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Monthly Revenue"
            value={loading ? '...' : formatCurrency(overview.total_revenue)}
            icon={<AttachMoney sx={{ fontSize: 24 }} />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="API Calls This Month"
            value={loading ? '...' : (overview.api_calls_this_month ?? 0).toLocaleString()}
            icon={<Api sx={{ fontSize: 24 }} />}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* Usage Trends */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 0 }}>
          <Box sx={{ p: 2.5, borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}` }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Usage Trends (Last 30 Days)
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              Daily document processing and API usage
            </Typography>
          </Box>
          {loading ? (
            <Box sx={{ p: 3 }}>
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} height={40} sx={{ mb: 1 }} />
              ))}
            </Box>
          ) : usageTrends.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: 'text.disabled' }}>No usage data available</Typography>
            </Box>
          ) : (
            <TableContainer sx={{ maxHeight: 400 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell align="right">Documents</TableCell>
                    <TableCell align="right">API Calls</TableCell>
                    <TableCell align="right">Revenue</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {usageTrends.map((row, index) => (
                    <TableRow key={index} hover>
                      <TableCell>
                        <Typography variant="body2">
                          {new Date(row.date).toLocaleDateString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{row.document_count ?? 0}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{(row.api_calls ?? 0).toLocaleString()}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {formatCurrency(row.revenue)}
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

      <Grid container spacing={3}>
        {/* Top Entities */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2.5, borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}` }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Top Entities
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Highest usage entities by volume
                </Typography>
              </Box>
              {loading ? (
                <Box sx={{ p: 3 }}>
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} height={40} sx={{ mb: 1 }} />
                  ))}
                </Box>
              ) : topEntities.length === 0 ? (
                <Box sx={{ p: 4, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.disabled' }}>No entity data available</Typography>
                </Box>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Entity Name</TableCell>
                        <TableCell align="right">Documents</TableCell>
                        <TableCell align="right">Revenue</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {topEntities.map((entity, index) => (
                        <TableRow key={index} hover>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {entity.entity_name}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">{(entity.document_count ?? 0).toLocaleString()}</Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {formatCurrency(entity.revenue)}
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
        </Grid>

        {/* Most-Used Endpoints */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2.5, borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}` }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Most-Used Endpoints
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  API endpoint usage and performance
                </Typography>
              </Box>
              {loading ? (
                <Box sx={{ p: 3 }}>
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} height={40} sx={{ mb: 1 }} />
                  ))}
                </Box>
              ) : endpoints.length === 0 ? (
                <Box sx={{ p: 4, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.disabled' }}>No endpoint data available</Typography>
                </Box>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Endpoint</TableCell>
                        <TableCell align="right">Requests</TableCell>
                        <TableCell align="right">Avg Response</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {endpoints.map((ep, index) => (
                        <TableRow key={index} hover>
                          <TableCell>
                            <Chip
                              label={ep.endpoint}
                              size="small"
                              variant="outlined"
                              sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">{(ep.count ?? 0).toLocaleString()}</Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">{ep.avg_response_time_ms ?? 0}ms</Typography>
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

        {/* Error Summary */}
        <Grid item xs={12}>
          <Card>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2.5, borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}` }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Error Summary
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Recent error trends and occurrences
                </Typography>
              </Box>
              {loading ? (
                <Box sx={{ p: 3 }}>
                  {[1, 2].map((i) => (
                    <Skeleton key={i} height={40} sx={{ mb: 1 }} />
                  ))}
                </Box>
              ) : errors.length === 0 ? (
                <Box sx={{ p: 4, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: colors.success.main }}>No errors recorded</Typography>
                </Box>
              ) : (
                <Box sx={{ p: 2.5, display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
                  {errors.map((err, index) => (
                    <Chip
                      key={index}
                      label={`${err.date}: ${err.error_count ?? 0} errors (${err.client_errors ?? 0} client, ${err.server_errors ?? 0} server)`}
                      color="error"
                      variant="outlined"
                      size="small"
                      sx={{ fontWeight: 500 }}
                    />
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AnalyticsPage;
