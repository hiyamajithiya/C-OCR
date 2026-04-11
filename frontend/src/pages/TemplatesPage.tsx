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
  Autocomplete,
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

  interface FieldDef {
    name: string;
    label: string;
    type: 'text' | 'number' | 'date' | 'currency';
  }

  const [newFields, setNewFields] = useState<FieldDef[]>([
    { name: '', label: '', type: 'text' },
  ]);

  const addFieldRow = () => {
    setNewFields([...newFields, { name: '', label: '', type: 'text' }]);
  };

  const removeFieldRow = (index: number) => {
    setNewFields(newFields.filter((_, i) => i !== index));
  };

  const updateFieldRow = (index: number, updates: Partial<FieldDef>) => {
    const updated = [...newFields];
    updated[index] = { ...updated[index], ...updates };
    setNewFields(updated);
  };

  // Built-in document categories
  const BUILT_IN_CATEGORIES = [
    'invoice',
    'bank_statement',
    'gst_return',
    'tds_certificate',
    'audit_schedule',
    'trial_balance',
  ];

  // User-added custom categories (persisted in localStorage)
  const [customCategories, setCustomCategories] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('custom_doc_categories');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const persistCustomCategories = (cats: string[]) => {
    setCustomCategories(cats);
    try {
      localStorage.setItem('custom_doc_categories', JSON.stringify(cats));
    } catch {
      /* ignore */
    }
  };

  // Training status per template — keyed by template id
  interface TrainingFieldStatus {
    field_name: string;
    field_label: string;
    total_corrections: number;
    unprocessed_corrections: number;
    ready_to_train: boolean;
    model_active: boolean;
    model_version: number | null;
    accuracy_score: number | null;
    training_samples: number;
  }
  interface TrainingStatus {
    template_id: number;
    template_name: string;
    min_corrections: number;
    total_fields: number;
    trained_fields: number;
    fields: TrainingFieldStatus[];
  }
  const [trainingStatus, setTrainingStatus] = useState<Record<number, TrainingStatus>>({});
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [statusDialogTemplate, setStatusDialogTemplate] = useState<Template | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await apiService.listTemplates();
      setTemplates(data);
      // Fetch training status for each template in parallel
      if (data.length > 0) {
        const results = await Promise.allSettled(
          data.map((t: Template) => apiService.getTemplateTrainingStatus(t.id))
        );
        const map: Record<number, TrainingStatus> = {};
        results.forEach((r, idx) => {
          if (r.status === 'fulfilled') {
            map[data[idx].id] = r.value;
          }
        });
        setTrainingStatus(map);
      }
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenTrainingStatus = (template: Template) => {
    setStatusDialogTemplate(template);
    setStatusDialogOpen(true);
  };

  const handleCreateTemplate = async () => {
    setError('');
    try {
      const category = newTemplate.doc_category.trim();

      // Filter out empty field rows and validate
      const validFields = newFields
        .filter((f) => f.name.trim())
        .map((f) => ({
          id: `field_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          name: f.name.trim(),
          label: f.label.trim() || f.name.trim(),
          type: f.type,
          page: 1,
          x: 0,
          y: 0,
          width: 0,
          height: 0,
          required: false,
        }));

      if (validFields.length === 0) {
        setError('Please add at least one field to extract');
        return;
      }

      // Create the template
      const created = await apiService.createTemplate({ ...newTemplate, doc_category: category });

      // Create initial version with defined fields (coordinates empty — to be filled in Builder)
      try {
        await apiService.createTemplateVersion(created.id, {
          signature_json: {},
          fields_json: { fields: validFields },
          rules_json: {},
        });
      } catch (versionErr) {
        console.warn('Failed to create initial version, template still created:', versionErr);
      }

      // Persist new category if it's user-added
      if (
        category &&
        !BUILT_IN_CATEGORIES.includes(category) &&
        !customCategories.includes(category)
      ) {
        persistCustomCategories([...customCategories, category]);
      }

      setOpenDialog(false);
      setNewTemplate({ name: '', description: '', doc_category: '' });
      setNewFields([{ name: '', label: '', type: 'text' }]);
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
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      <Chip
                        label={template.is_active ? 'Active' : 'Inactive'}
                        size="small"
                        color={template.is_active ? 'success' : 'default'}
                      />
                      {(() => {
                        const status = trainingStatus[template.id];
                        if (!status) return null;
                        const trained = status.trained_fields;
                        const total = status.total_fields;
                        if (trained > 0) {
                          return (
                            <Chip
                              label={`🧠 ML Trained ${trained}/${total}`}
                              size="small"
                              color="success"
                              variant="outlined"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenTrainingStatus(template);
                              }}
                            />
                          );
                        }
                        return (
                          <Chip
                            label={`Not Trained (0/${total})`}
                            size="small"
                            color="default"
                            variant="outlined"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenTrainingStatus(template);
                            }}
                          />
                        );
                      })()}
                    </Box>
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
          <Autocomplete
            freeSolo
            fullWidth
            options={[
              ...BUILT_IN_CATEGORIES,
              ...customCategories,
              ...templates
                .map((t) => t.doc_category)
                .filter(
                  (c): c is string =>
                    !!c &&
                    !BUILT_IN_CATEGORIES.includes(c) &&
                    !customCategories.includes(c)
                ),
            ]}
            value={newTemplate.doc_category}
            onChange={(_, value) =>
              setNewTemplate({ ...newTemplate, doc_category: value || '' })
            }
            onInputChange={(_, value) =>
              setNewTemplate({ ...newTemplate, doc_category: value || '' })
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label="Document Category"
                margin="normal"
                placeholder="Select or type a new category"
                helperText="Pick from list or type a custom category — it will be remembered"
              />
            )}
          />

          {/* Fields to Extract */}
          <Box sx={{ mt: 3, mb: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Fields to Extract
              </Typography>
              <Button size="small" startIcon={<Add />} onClick={addFieldRow}>
                Add Field
              </Button>
            </Box>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1.5 }}>
              Define what fields you want to extract. You'll map them to document regions in the next step.
            </Typography>

            {newFields.map((field, index) => (
              <Box
                key={index}
                sx={{
                  display: 'flex',
                  gap: 1,
                  mb: 1,
                  alignItems: 'flex-start',
                }}
              >
                <TextField
                  size="small"
                  label="Field Name"
                  placeholder="invoice_number"
                  value={field.name}
                  onChange={(e) =>
                    updateFieldRow(index, { name: e.target.value.replace(/\s+/g, '_').toLowerCase() })
                  }
                  sx={{ flex: 2 }}
                  required
                />
                <TextField
                  size="small"
                  label="Display Label"
                  placeholder="Invoice Number"
                  value={field.label}
                  onChange={(e) => updateFieldRow(index, { label: e.target.value })}
                  sx={{ flex: 2 }}
                />
                <TextField
                  size="small"
                  select
                  label="Type"
                  value={field.type}
                  onChange={(e) => updateFieldRow(index, { type: e.target.value as any })}
                  sx={{ flex: 1, minWidth: 100 }}
                >
                  <MenuItem value="text">Text</MenuItem>
                  <MenuItem value="number">Number</MenuItem>
                  <MenuItem value="date">Date</MenuItem>
                  <MenuItem value="currency">Currency</MenuItem>
                </TextField>
                <IconButton
                  size="small"
                  onClick={() => removeFieldRow(index)}
                  disabled={newFields.length === 1}
                  sx={{ mt: 0.5 }}
                >
                  <Delete sx={{ fontSize: 18 }} />
                </IconButton>
              </Box>
            ))}
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button
            onClick={handleCreateTemplate}
            variant="contained"
            disabled={!newTemplate.name || !newFields.some((f) => f.name.trim())}
          >
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

      {/* Training Status Dialog */}
      <Dialog
        open={statusDialogOpen}
        onClose={() => setStatusDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 600 }}>
          ML Training Status — {statusDialogTemplate?.name}
        </DialogTitle>
        <DialogContent>
          {statusDialogTemplate && trainingStatus[statusDialogTemplate.id] ? (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                Training requires at least{' '}
                <strong>{trainingStatus[statusDialogTemplate.id].min_corrections}</strong>{' '}
                corrections per field. Submit corrections from the Extraction Results page then
                click "Learn" to train ML models that improve extraction confidence.
              </Alert>
              <Box
                component="table"
                sx={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  '& th, & td': {
                    textAlign: 'left',
                    p: 1.25,
                    borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                  },
                  '& th': {
                    fontWeight: 600,
                    fontSize: '0.8rem',
                    color: 'text.secondary',
                    textTransform: 'uppercase',
                  },
                }}
              >
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Corrections</th>
                    <th>Status</th>
                    <th>Version</th>
                    <th>Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {trainingStatus[statusDialogTemplate.id].fields.map((f) => (
                    <tr key={f.field_name}>
                      <td>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {f.field_label || f.field_name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          {f.field_name}
                        </Typography>
                      </td>
                      <td>
                        <Typography variant="body2">
                          {f.total_corrections}
                          {f.unprocessed_corrections > 0 && (
                            <Typography
                              component="span"
                              variant="caption"
                              sx={{ color: 'warning.main', ml: 0.5 }}
                            >
                              ({f.unprocessed_corrections} pending)
                            </Typography>
                          )}
                        </Typography>
                      </td>
                      <td>
                        {f.model_active ? (
                          <Chip label="🧠 Trained" size="small" color="success" />
                        ) : f.ready_to_train ? (
                          <Chip label="Ready to Train" size="small" color="warning" />
                        ) : (
                          <Chip
                            label={`Need ${
                              trainingStatus[statusDialogTemplate.id].min_corrections -
                              f.total_corrections
                            } more`}
                            size="small"
                          />
                        )}
                      </td>
                      <td>
                        <Typography variant="body2">
                          {f.model_version ? `v${f.model_version}` : '—'}
                        </Typography>
                      </td>
                      <td>
                        <Typography variant="body2">
                          {f.accuracy_score !== null
                            ? `${Math.round(f.accuracy_score * 100)}%`
                            : '—'}
                        </Typography>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Box>
            </>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Loading training status...
            </Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setStatusDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TemplatesPage;
