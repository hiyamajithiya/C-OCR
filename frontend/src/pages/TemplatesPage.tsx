/**
 * Templates page with enhanced dark theme UI.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Grid,
  Chip,
  Alert,
  InputAdornment,
  IconButton,
  alpha,
  Skeleton,
  MenuItem,
} from '@mui/material';
import {
  Add,
  ViewModule,
  Search,
  Edit,
  PlayArrow,
  Delete,
  WarningAmber,
  Category,
  CalendarToday,
  Close,
} from '@mui/icons-material';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';

interface Template {
  id: number;
  name: string;
  description: string;
  doc_category: string;
  is_active: boolean;
  created_at: string;
}

const TemplatesPage: React.FC = () => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState<Template | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    description: '',
    doc_category: '',
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await apiService.listTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = async () => {
    setError('');
    try {
      await apiService.createTemplate(newTemplate);
      setOpenDialog(false);
      setNewTemplate({ name: '', description: '', doc_category: '' });
      loadTemplates();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create template');
    }
  };

  const handleOpenDeleteDialog = (template: Template) => {
    setError('');
    setTemplateToDelete(template);
    setDeleteDialogOpen(true);
  };

  const handleDeleteTemplate = async () => {
    if (!templateToDelete) return;

    setDeleting(true);
    setError('');
    try {
      await apiService.deleteTemplate(templateToDelete.id);
      setDeleteDialogOpen(false);
      setTemplateToDelete(null);
      await loadTemplates();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete template');
    } finally {
      setDeleting(false);
    }
  };

  const filteredTemplates = templates.filter((template) => {
    const matchesSearch =
      !searchQuery ||
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !categoryFilter || template.doc_category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const uniqueCategories = [...new Set(templates.map((t) => t.doc_category).filter(Boolean))];

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
            Templates
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            Create and manage document extraction templates
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Add />} onClick={() => setOpenDialog(true)} sx={{ px: 3 }}>
          Create Template
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Filters */}
      {templates.length > 0 && (
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <TextField
            size="small"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search sx={{ fontSize: 20, color: 'text.secondary' }} />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchQuery('')}>
                    <Close sx={{ fontSize: 16 }} />
                  </IconButton>
                </InputAdornment>
              ),
            }}
            sx={{ width: 280 }}
          />
          <TextField
            select
            size="small"
            label="Category"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            sx={{ width: 180 }}
          >
            <MenuItem value="">All Categories</MenuItem>
            {uniqueCategories.map((cat) => (
              <MenuItem key={cat} value={cat}>
                {cat}
              </MenuItem>
            ))}
          </TextField>
        </Box>
      )}

      {/* Templates Grid */}
      {loading ? (
        <Grid container spacing={3}>
          {[1, 2, 3].map((i) => (
            <Grid item xs={12} md={6} lg={4} key={i}>
              <Skeleton variant="rounded" height={220} />
            </Grid>
          ))}
        </Grid>
      ) : filteredTemplates.length === 0 ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
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
            <ViewModule sx={{ fontSize: 40, color: 'primary.main' }} />
          </Box>
          <Typography variant="h6" sx={{ mb: 1 }}>
            {searchQuery || categoryFilter ? 'No templates match your filters' : 'No Templates Yet'}
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
            {searchQuery || categoryFilter
              ? 'Try adjusting your search or filters'
              : 'Create your first template to start extracting data from documents'}
          </Typography>
          {!searchQuery && !categoryFilter && (
            <Button variant="contained" startIcon={<Add />} onClick={() => setOpenDialog(true)}>
              Create First Template
            </Button>
          )}
        </Card>
      ) : (
        <Grid container spacing={3}>
          {filteredTemplates.map((template) => (
            <Grid item xs={12} md={6} lg={4} key={template.id}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  cursor: 'pointer',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                  },
                }}
                onClick={() => navigate(`/templates/${template.id}/builder`)}
              >
                <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                  {/* Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: 2,
                        bgcolor: alpha(colors.secondary.main, 0.15),
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <ViewModule sx={{ fontSize: 24, color: colors.secondary.main }} />
                    </Box>
                    <Chip
                      label={template.is_active ? 'Active' : 'Inactive'}
                      size="small"
                      color={template.is_active ? 'success' : 'default'}
                    />
                  </Box>

                  {/* Title & Description */}
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                    {template.name}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: 'text.secondary',
                      mb: 2,
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {template.description || 'No description provided'}
                  </Typography>

                  {/* Meta Info */}
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
                    {template.doc_category && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Category sx={{ fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          {template.doc_category}
                        </Typography>
                      </Box>
                    )}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CalendarToday sx={{ fontSize: 16, color: 'text.secondary' }} />
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {new Date(template.created_at).toLocaleDateString()}
                      </Typography>
                    </Box>
                  </Box>

                  {/* Actions */}
                  <Box sx={{ display: 'flex', gap: 1 }} onClick={(e) => e.stopPropagation()}>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<Edit />}
                      onClick={() => navigate(`/templates/${template.id}/builder`)}
                      sx={{ flex: 1 }}
                    >
                      Edit
                    </Button>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<PlayArrow />}
                      onClick={() => navigate(`/templates/${template.id}/builder`)}
                      sx={{ flex: 1 }}
                    >
                      Train
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<Delete />}
                      onClick={() => handleOpenDeleteDialog(template)}
                      sx={{ flex: 1 }}
                    >
                      Delete
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Template Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>Create New Template</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
            Create a new template to define extraction fields for your documents.
          </Typography>
          <TextField
            fullWidth
            label="Template Name"
            value={newTemplate.name}
            onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
            margin="normal"
            required
            placeholder="e.g., Invoice Template"
          />
          <TextField
            fullWidth
            label="Description"
            value={newTemplate.description}
            onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
            margin="normal"
            multiline
            rows={3}
            placeholder="Describe what this template extracts..."
          />
          <TextField
            fullWidth
            select
            label="Document Category"
            value={newTemplate.doc_category}
            onChange={(e) => setNewTemplate({ ...newTemplate, doc_category: e.target.value })}
            margin="normal"
          >
            <MenuItem value="">None</MenuItem>
            <MenuItem value="invoice">Invoice</MenuItem>
            <MenuItem value="bank_statement">Bank Statement</MenuItem>
            <MenuItem value="gst_return">GST Return</MenuItem>
            <MenuItem value="tds_certificate">TDS Certificate</MenuItem>
            <MenuItem value="audit_schedule">Audit Schedule</MenuItem>
            <MenuItem value="trial_balance">Trial Balance</MenuItem>
          </TextField>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateTemplate} variant="contained" disabled={!newTemplate.name}>
            Create Template
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleting && setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningAmber sx={{ color: colors.warning.main }} />
          Delete Template
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            It will completely delete the template.
          </Alert>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            This action cannot be undone. All template versions linked to
            <Typography component="span" sx={{ fontWeight: 700, mx: 0.5 }}>
              {templateToDelete?.name || 'this template'}
            </Typography>
            will be permanently removed.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeleteTemplate}
            disabled={deleting}
          >
            {deleting ? 'Deleting...' : 'Delete Template'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TemplatesPage;
