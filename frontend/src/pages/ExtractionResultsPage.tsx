/**
 * Extraction results page for viewing extracted data from documents.
 * Includes functionality to correct extracted values and submit feedback.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Card,
  CardContent,
  TextField,
  Tooltip,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  ArrowBack,
  CheckCircle,
  Warning,
  Edit,
  Save,
  Cancel,
  History,
  School,
} from '@mui/icons-material';
import { apiService } from '@/services/api';

interface ExtractionData {
  extraction_result_id: number;
  template_id: number;
  template_name: string;
  template_version_id: number;
  extracted_data: {
    [key: string]: {
      value: string;
      confidence: number;
      status: string;
      field_label?: string;
      field_type?: string;
      extraction_method?: string;
    };
  };
  created_at: string;
}

interface RawExtractionResult {
  id?: number;
  extraction_result_id?: number;
  template_id?: number;
  template_name?: string;
  template_version_id?: number;
  extracted_data?: Record<string, any> | null;
  result_json?: Record<string, any> | null;
  confidence_json?: Record<string, number> | null;
  created_at?: string;
}

interface Correction {
  id: number;
  extraction_result_id?: number | null;
  field_name: string;
  field_label?: string;
  original_value?: string;
  corrected_value: string;
  is_processed: boolean;
  created_at: string;
}

interface EditedField {
  fieldName: string;
  originalValue: string;
  newValue: string;
  fieldLabel?: string;
  fieldType?: string;
  confidence?: number;
  extractionMethod?: string;
}

const ExtractionResultsPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [extractions, setExtractions] = useState<ExtractionData[]>([]);
  const [document, setDocument] = useState<any>(null);
  const [corrections, setCorrections] = useState<Correction[]>([]);

  // Edit mode state
  const [editMode, setEditMode] = useState(false);
  const [editedFields, setEditedFields] = useState<{ [key: string]: EditedField }>({});
  const [submitting, setSubmitting] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  // History dialog
  const [historyOpen, setHistoryOpen] = useState(false);

  // Learn info banner — dismissible via localStorage
  const [showLearnBanner, setShowLearnBanner] = useState(() => {
    try {
      return localStorage.getItem('hide_learn_banner') !== '1';
    } catch {
      return true;
    }
  });

  useEffect(() => {
    loadData();
  }, [documentId]);

  const dismissLearnBanner = () => {
    setShowLearnBanner(false);
    try {
      localStorage.setItem('hide_learn_banner', '1');
    } catch {
      /* ignore */
    }
  };

  const latestCorrectionValueMap = useMemo(() => {
    const map: { [key: string]: string } = {};
    // Corrections are already ordered newest-first from API.
    for (const correction of corrections) {
      const key = `${correction.extraction_result_id}_${correction.field_name}`;
      if (!(key in map)) {
        map[key] = correction.corrected_value ?? '';
      }
    }
    return map;
  }, [corrections]);

  const normalizeExtractions = (results: RawExtractionResult[]): ExtractionData[] => {
    return (results || []).map((result) => {
      const rawValues = (result.extracted_data ?? result.result_json ?? {}) as Record<string, any>;
      const rawConfidence = (result.confidence_json ?? {}) as Record<string, number>;

      const extracted_data: ExtractionData['extracted_data'] = Object.fromEntries(
        Object.entries(rawValues || {}).map(([fieldName, valueOrMeta]) => {
          if (valueOrMeta && typeof valueOrMeta === 'object' && !Array.isArray(valueOrMeta)) {
            return [
              fieldName,
              {
                value: valueOrMeta.value ?? '',
                confidence: Number(valueOrMeta.confidence ?? rawConfidence[fieldName] ?? 0),
                status: valueOrMeta.status ?? 'extracted',
                field_label: valueOrMeta.field_label,
                field_type: valueOrMeta.field_type,
                extraction_method: valueOrMeta.extraction_method,
              },
            ];
          }

          return [
            fieldName,
            {
              value: valueOrMeta ?? '',
              confidence: Number(rawConfidence[fieldName] ?? 0),
              status: 'extracted',
              field_label: fieldName,
              field_type: 'text',
              extraction_method: 'unknown',
            },
          ];
        })
      );

      return {
        extraction_result_id: result.extraction_result_id ?? result.id ?? 0,
        template_id: result.template_id ?? 0,
        template_name: result.template_name ?? `Template #${result.template_id ?? 'Unknown'}`,
        template_version_id: result.template_version_id ?? 0,
        extracted_data,
        created_at: result.created_at ?? new Date().toISOString(),
      };
    });
  };

  const loadData = async () => {
    try {
      setLoading(true);

      // Load document info
      const docs = await apiService.listDocuments();
      const doc = docs.find((d: any) => d.id === Number(documentId));
      setDocument(doc);

      // Load extraction results
      const results = await apiService.getDocumentExtractions(Number(documentId));
      setExtractions(normalizeExtractions(results));

      // Load correction history
      try {
        const correctionHistory = await apiService.getDocumentCorrections(Number(documentId));
        setCorrections(correctionHistory);
      } catch {
        // Corrections endpoint might not exist yet
        setCorrections([]);
      }
    } catch (err: any) {
      console.error('Failed to load extraction results:', err);
      setError(err.response?.data?.detail || 'Failed to load extraction results');
    } finally {
      setLoading(false);
    }
  };

  const handleEditToggle = () => {
    if (editMode) {
      // Cancel edit mode - clear edited fields
      setEditedFields({});
    }
    setEditMode(!editMode);
  };

  const handleFieldChange = (
    extractionId: number,
    fieldName: string,
    newValue: string,
    originalValue: string,
    fieldData: any
  ) => {
    const key = `${extractionId}_${fieldName}`;
    if (newValue !== originalValue) {
      setEditedFields((prev) => ({
        ...prev,
        [key]: {
          fieldName,
          originalValue,
          newValue,
          fieldLabel: fieldData.field_label,
          fieldType: fieldData.field_type,
          confidence: fieldData.confidence,
          extractionMethod: fieldData.extraction_method,
        },
      }));
    } else {
      // Remove from edited fields if value matches original
      setEditedFields((prev) => {
        const updated = { ...prev };
        delete updated[key];
        return updated;
      });
    }
  };

  const handleSubmitCorrections = async (extraction: ExtractionData) => {
    const correctionsList = Object.entries(editedFields)
      .filter(([key]) => key.startsWith(`${extraction.extraction_result_id}_`))
      .map(([, field]) => ({
        document_id: Number(documentId),
        field_name: field.fieldName,
        field_label: field.fieldLabel,
        field_type: field.fieldType,
        original_value: field.originalValue,
        original_confidence: field.confidence,
        extraction_method: field.extractionMethod,
        corrected_value: field.newValue,
      }));

    if (correctionsList.length === 0) {
      setSnackbar({ open: true, message: 'No changes to submit', severity: 'error' });
      return;
    }

    try {
      setSubmitting(true);

      await apiService.submitBulkCorrections({
        document_id: Number(documentId),
        extraction_result_id: extraction.extraction_result_id,
        corrections: correctionsList,
      });

      setSnackbar({
        open: true,
        message: `Successfully submitted ${correctionsList.length} correction(s)`,
        severity: 'success',
      });

      // Clear edited fields for this extraction
      setEditedFields((prev) => {
        const updated = { ...prev };
        Object.keys(updated)
          .filter((key) => key.startsWith(`${extraction.extraction_result_id}_`))
          .forEach((key) => delete updated[key]);
        return updated;
      });

      // Reload corrections history
      const correctionHistory = await apiService.getDocumentCorrections(Number(documentId));
      setCorrections(correctionHistory);

      setEditMode(false);
    } catch (err: any) {
      console.error('Failed to submit corrections:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to submit corrections',
        severity: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleTriggerLearning = async () => {
    try {
      setSubmitting(true);
      const result = await apiService.triggerLearningProcess();

      const trainedCount = result.training_models_count || 0;
      const trainingResults = result.training_results || [];
      const actuallyTrained = trainingResults.filter(
        (r: any) => r.status === 'trained'
      ).length;

      let message = `Learning complete: ${result.processed_count} corrections processed`;
      if (result.abbreviations_learned > 0) {
        message += `, ${result.abbreviations_learned} new patterns learned`;
      }
      if (actuallyTrained > 0) {
        const avgAcc =
          trainingResults
            .filter((r: any) => r.status === 'trained' && r.accuracy)
            .reduce((sum: number, r: any) => sum + r.accuracy, 0) / actuallyTrained || 0;
        message += `. 🧠 ${actuallyTrained} ML model${
          actuallyTrained > 1 ? 's' : ''
        } trained (avg accuracy: ${Math.round(avgAcc * 100)}%)`;
      } else if (trainedCount === 0) {
        message += '. No models trained yet — need more corrections per field.';
      }

      setSnackbar({
        open: true,
        message,
        severity: 'success',
      });

      // Reload corrections history to reflect the updated is_processed flags
      try {
        const correctionHistory = await apiService.getDocumentCorrections(Number(documentId));
        setCorrections(correctionHistory);
      } catch {
        /* ignore */
      }
    } catch (err: any) {
      console.error('Failed to trigger learning:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to trigger learning process',
        severity: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const getBaseFieldValue = (extractionId: number, fieldName: string, originalValue: string) => {
    const key = `${extractionId}_${fieldName}`;
    return latestCorrectionValueMap[key] ?? originalValue;
  };

  const getEditedValue = (extractionId: number, fieldName: string, originalValue: string) => {
    const key = `${extractionId}_${fieldName}`;
    const baseValue = getBaseFieldValue(extractionId, fieldName, originalValue);
    return editedFields[key]?.newValue ?? baseValue;
  };

  const hasChanges = (extractionId: number) => {
    return Object.keys(editedFields).some((key) => key.startsWith(`${extractionId}_`));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button onClick={() => navigate('/documents')} startIcon={<ArrowBack />}>
          Back to Documents
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Button onClick={() => navigate('/documents')} startIcon={<ArrowBack />} sx={{ mr: 2 }}>
            Back
          </Button>
          <Box>
            <Typography variant="h4" gutterBottom>
              Extraction Results
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {document?.filename}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="View correction history">
            <Button
              variant="outlined"
              startIcon={<History />}
              onClick={() => setHistoryOpen(true)}
              disabled={corrections.length === 0}
            >
              History ({corrections.length})
            </Button>
          </Tooltip>
          <Tooltip title="Process corrections to improve extraction">
            <Button
              variant="outlined"
              startIcon={<School />}
              onClick={handleTriggerLearning}
              disabled={submitting || corrections.filter((c) => !c.is_processed).length === 0}
            >
              Learn
            </Button>
          </Tooltip>
          <Button
            variant={editMode ? 'outlined' : 'contained'}
            startIcon={editMode ? <Cancel /> : <Edit />}
            onClick={handleEditToggle}
            color={editMode ? 'error' : 'primary'}
          >
            {editMode ? 'Cancel' : 'Edit Values'}
          </Button>
        </Box>
      </Box>

      {showLearnBanner && (
        <Alert
          severity="info"
          onClose={dismissLearnBanner}
          sx={{ mb: 3 }}
          icon={<School />}
        >
          <strong>How training works:</strong> Edit wrong values and click{' '}
          <strong>Save Corrections</strong>. After submitting enough corrections (5+ per field),
          click <strong>Learn</strong> to train an ML model. Trained models automatically
          improve confidence scores on future extractions.
        </Alert>
      )}

      {extractions.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No Extractions Yet
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            This document hasn't been processed with any template yet.
          </Typography>
          <Button variant="contained" onClick={() => navigate('/documents')}>
            Go to Documents
          </Button>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {extractions.map((extraction) => (
            <Card key={extraction.extraction_result_id}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box>
                    <Typography variant="h6">{extraction.template_name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Extracted: {new Date(extraction.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    {editMode && hasChanges(extraction.extraction_result_id) && (
                      <Button
                        variant="contained"
                        color="success"
                        size="small"
                        startIcon={<Save />}
                        onClick={() => handleSubmitCorrections(extraction)}
                        disabled={submitting}
                      >
                        Save Corrections
                      </Button>
                    )}
                    <Chip label="Extracted" color="success" size="small" />
                  </Box>
                </Box>

                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Field</strong></TableCell>
                        <TableCell><strong>Value</strong></TableCell>
                        <TableCell align="center"><strong>Confidence</strong></TableCell>
                        <TableCell align="center"><strong>Method</strong></TableCell>
                        {editMode && <TableCell align="center"><strong>Status</strong></TableCell>}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(extraction.extracted_data || {}).map(([fieldName, fieldData]) => {
                        const key = `${extraction.extraction_result_id}_${fieldName}`;
                        const isEdited = !!editedFields[key];
                        const baseValue = getBaseFieldValue(
                          extraction.extraction_result_id,
                          fieldName,
                          fieldData.value || ''
                        );
                        const displayValue = getEditedValue(
                          extraction.extraction_result_id,
                          fieldName,
                          fieldData.value || ''
                        );

                        return (
                          <TableRow
                            key={fieldName}
                            sx={{
                              backgroundColor: isEdited ? 'rgba(76, 175, 80, 0.1)' : 'inherit',
                            }}
                          >
                            <TableCell>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {fieldData.field_label || fieldName}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {fieldName}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              {editMode ? (
                                <TextField
                                  size="small"
                                  fullWidth
                                  value={displayValue}
                                  onChange={(e) =>
                                    handleFieldChange(
                                      extraction.extraction_result_id,
                                      fieldName,
                                      e.target.value,
                                      baseValue,
                                      fieldData
                                    )
                                  }
                                  variant="outlined"
                                  sx={{
                                    '& .MuiOutlinedInput-root': {
                                      backgroundColor: isEdited ? 'rgba(76, 175, 80, 0.05)' : 'inherit',
                                    },
                                  }}
                                />
                              ) : (
                                <Typography variant="body2">
                                  {displayValue || <em style={{ color: '#999' }}>No value extracted</em>}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell align="center">
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                                {fieldData.confidence >= 0.7 ? (
                                  <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
                                ) : (
                                  <Warning sx={{ fontSize: 16, color: 'warning.main' }} />
                                )}
                                <Typography variant="body2">
                                  {Math.round(fieldData.confidence * 100)}%
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell align="center">
                              <Chip
                                label={fieldData.extraction_method || 'unknown'}
                                size="small"
                                variant="outlined"
                                color={
                                  fieldData.extraction_method === 'bbox'
                                    ? 'success'
                                    : fieldData.extraction_method === 'label_search'
                                    ? 'primary'
                                    : 'default'
                                }
                              />
                            </TableCell>
                            {editMode && (
                              <TableCell align="center">
                                {isEdited ? (
                                  <Chip label="Modified" size="small" color="success" />
                                ) : (
                                  <Chip label="Unchanged" size="small" variant="outlined" />
                                )}
                              </TableCell>
                            )}
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Correction History Dialog */}
      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Correction History</DialogTitle>
        <DialogContent>
          {corrections.length === 0 ? (
            <Typography color="text.secondary">No corrections have been made yet.</Typography>
          ) : (
            <List>
              {corrections.map((correction, index) => (
                <React.Fragment key={correction.id}>
                  <ListItem>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle2">
                            {correction.field_label || correction.field_name}
                          </Typography>
                          {correction.is_processed ? (
                            <Chip label="Learned" size="small" color="success" />
                          ) : (
                            <Chip label="Awaiting Learn" size="small" color="warning" />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Original:</strong> {correction.original_value || '(empty)'}
                          </Typography>
                          <Typography variant="body2" color="success.main">
                            <strong>Corrected:</strong> {correction.corrected_value}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(correction.created_at).toLocaleString()}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < corrections.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ExtractionResultsPage;
