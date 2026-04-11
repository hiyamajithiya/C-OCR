/**
 * Documents page with enhanced dark theme UI.
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  LinearProgress,
  Chip,
  Grid,
  TextField,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Tabs,
  Tab,
  Divider,
  Checkbox,
  InputAdornment,
  IconButton,
  Tooltip,
  alpha,
  Skeleton,
} from '@mui/material';
import {
  CloudUpload,
  Description,
  TextSnippet,
  Delete,
  PlayArrow,
  Visibility,
  Search,
  Refresh,
  InsertDriveFile,
  PictureAsPdf,
  Image,
  Close,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Schedule,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { apiService } from '@/services/api';
import { colors } from '@/theme/theme';

interface UploadedDocument {
  document_id: number;
  status: string;
  message: string;
  filename?: string;
}

interface DocumentDetails {
  id: number;
  filename: string;
  mime_type: string;
  page_count?: number;
  status: string;
  source: string;
  created_at: string;
}

interface OCRResult {
  document_id: number;
  status: string;
  page_count?: number;
  pages: Array<{
    page_number: number;
    text: string;
    confidence: number;
  }>;
  full_text: string;
}

const DocumentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [, setUploadedDocs] = useState<UploadedDocument[]>([]);
  const [allDocuments, setAllDocuments] = useState<any[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [error, setError] = useState('');
  const [docCategory, setDocCategory] = useState('');
  const [customCategory, setCustomCategory] = useState('');
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetails | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [tabIndex, setTabIndex] = useState(0);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [deleting, setDeleting] = useState(false);
  const [applyTemplateOpen, setApplyTemplateOpen] = useState(false);
  const [applyingTemplate, setApplyingTemplate] = useState(false);
  const [documentToApply, setDocumentToApply] = useState<number | null>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<number | null>(null);

  const parseServerDate = (dateString: string) => {
    // Backend sends naive UTC timestamps; append Z so browser parses as UTC.
    if (!dateString) return new Date(0);
    if (dateString.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(dateString)) {
      return new Date(dateString);
    }
    return new Date(`${dateString}Z`);
  };

  const formatUploadDateTime = (dateString: string) => {
    const date = parseServerDate(dateString);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    })}`;
  };

  useEffect(() => {
    loadAllDocuments();
  }, []);

  // Auto-poll while any document is still processing or uploaded (not yet complete)
  useEffect(() => {
    const hasInProgress = allDocuments.some(
      (d) => d.status === 'processing' || d.status === 'uploaded'
    );
    if (!hasInProgress) return;

    const interval = setInterval(() => {
      loadAllDocuments(true);
    }, 3000);
    return () => clearInterval(interval);
  }, [allDocuments]);

  const loadAllDocuments = async (silent: boolean = false) => {
    if (!silent) setLoadingDocs(true);
    try {
      const docs = await apiService.listDocuments();
      setAllDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      if (!silent) setLoadingDocs(false);
    }
  };

  const filteredDocuments = allDocuments.filter((doc) => {
    const matchesSearch = !searchQuery || doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = !statusFilter || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleDeleteDocument = async () => {
    if (!docToDelete) return;
    try {
      await apiService.deleteDocument(docToDelete);
      loadAllDocuments();
      setUploadedDocs((prev) => prev.filter((doc) => doc.document_id !== docToDelete));
      setDeleteDialogOpen(false);
      setDocToDelete(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete document');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedDocIds.length === 0) return;
    setDeleting(true);
    try {
      const result = await apiService.bulkDeleteDocuments(selectedDocIds);
      if (result.errors && result.errors.length > 0) {
        setError(`Deleted ${result.deleted_count} document(s). Errors: ${result.errors.join(', ')}`);
      }
      loadAllDocuments();
      setSelectedDocIds([]);
      setUploadedDocs((prev) => prev.filter((doc) => !selectedDocIds.includes(doc.document_id)));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete documents');
    } finally {
      setDeleting(false);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedDocIds(filteredDocuments.map((doc) => doc.id));
    } else {
      setSelectedDocIds([]);
    }
  };

  const handleSelectDocument = (documentId: number, checked: boolean) => {
    if (checked) {
      setSelectedDocIds((prev) => [...prev, documentId]);
    } else {
      setSelectedDocIds((prev) => prev.filter((id) => id !== documentId));
    }
  };

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setError('');
      setUploading(true);
      try {
        const categoryToUse = docCategory === 'custom' ? customCategory : docCategory;
        const uploadPromises = acceptedFiles.map(async (file) => {
          const result = await apiService.uploadDocument(file, categoryToUse || undefined);
          return { ...result, filename: file.name };
        });
        const results = await Promise.all(uploadPromises);
        setUploadedDocs((prev) => [...results, ...prev]);
        loadAllDocuments();
      } catch (err: any) {
        let errorMessage = 'Upload failed. Please try again.';
        if (err.response?.data?.detail) {
          const detail = err.response.data.detail;
          if (Array.isArray(detail)) {
            errorMessage = detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
          } else if (typeof detail === 'string') {
            errorMessage = detail;
          }
        }
        setError(errorMessage);
      } finally {
        setUploading(false);
      }
    },
    [docCategory, customCategory]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/tiff': ['.tiff', '.tif'],
    },
    disabled: uploading,
  });

  const handleViewDetails = async (documentId: number) => {
    setLoadingDetails(true);
    setDetailsOpen(true);
    setTabIndex(0);
    setOcrResult(null);
    try {
      const [details, ocrData] = await Promise.all([
        apiService.getDocument(documentId),
        apiService.getDocumentResult(documentId),
      ]);
      setSelectedDoc(details);
      setOcrResult(ocrData);
    } catch (err: any) {
      console.error('Failed to fetch document details:', err);
      setError('Failed to load document details');
      setDetailsOpen(false);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedDoc(null);
    setOcrResult(null);
    setTabIndex(0);
  };

  const handleOpenApplyTemplate = async (documentId: number) => {
    setDocumentToApply(documentId);
    setApplyTemplateOpen(true);
    setError('');
    if (templates.length === 0) {
      try {
        const templatesList = await apiService.listTemplates();
        setTemplates(templatesList);
      } catch (err) {
        console.error('Failed to load templates:', err);
        setError('Failed to load templates');
      }
    }
  };

  const handleApplyTemplate = async () => {
    if (!selectedTemplateId || !documentToApply) return;
    setApplyingTemplate(true);
    try {
      await apiService.applyTemplate(selectedTemplateId, documentToApply);
      setApplyTemplateOpen(false);
      setSelectedTemplateId(null);
      setDocumentToApply(null);
      navigate(`/documents/${documentToApply}/extractions`);
    } catch (err: any) {
      console.error('Failed to apply template:', err);
      setError(err.response?.data?.detail || 'Failed to apply template');
    } finally {
      setApplyingTemplate(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'extracted':
        return <CheckCircle sx={{ fontSize: 18, color: colors.success.main }} />;
      case 'processing':
        return <Schedule sx={{ fontSize: 18, color: colors.warning.main }} />;
      case 'error':
        return <ErrorIcon sx={{ fontSize: 18, color: colors.error.main }} />;
      default:
        return <Warning sx={{ fontSize: 18, color: colors.text.secondary }} />;
    }
  };

  const getStatusColor = (status: string) => {
    const statusColors: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'error'> = {
      uploaded: 'default',
      processing: 'warning',
      extracted: 'success',
      needs_training: 'warning',
      error: 'error',
    };
    return statusColors[status] || 'default';
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType?.includes('pdf')) {
      return <PictureAsPdf sx={{ fontSize: 24, color: colors.error.main }} />;
    }
    if (mimeType?.includes('image')) {
      return <Image sx={{ fontSize: 24, color: colors.secondary.main }} />;
    }
    return <InsertDriveFile sx={{ fontSize: 24, color: colors.primary.main }} />;
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Documents
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.secondary' }}>
          Upload, manage, and process your documents
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Upload Area */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Upload Documents
          </Typography>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Document Category (Optional)"
                value={docCategory}
                onChange={(e) => {
                  setDocCategory(e.target.value);
                  if (e.target.value !== 'custom') setCustomCategory('');
                }}
                disabled={uploading}
                size="small"
              >
                <MenuItem value="">None</MenuItem>
                <MenuItem value="invoice">Invoice</MenuItem>
                <MenuItem value="bank_statement">Bank Statement</MenuItem>
                <MenuItem value="gst_return">GST Return</MenuItem>
                <MenuItem value="tds_certificate">TDS Certificate</MenuItem>
                <MenuItem value="audit_schedule">Audit Schedule</MenuItem>
                <MenuItem value="custom">Custom</MenuItem>
              </TextField>
            </Grid>
            {docCategory === 'custom' && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Custom Category"
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  disabled={uploading}
                  size="small"
                  placeholder="e.g., purchase_order"
                />
              </Grid>
            )}
          </Grid>

          <Box
            {...getRootProps()}
            sx={{
              border: `2px dashed ${isDragActive ? colors.primary.main : alpha(colors.text.primary, 0.2)}`,
              borderRadius: 3,
              p: 5,
              textAlign: 'center',
              cursor: uploading ? 'not-allowed' : 'pointer',
              bgcolor: isDragActive ? alpha(colors.primary.main, 0.08) : 'transparent',
              transition: 'all 0.3s ease',
              '&:hover': {
                borderColor: uploading ? alpha(colors.text.primary, 0.2) : colors.primary.main,
                bgcolor: uploading ? 'transparent' : alpha(colors.primary.main, 0.04),
              },
            }}
          >
            <input {...getInputProps()} />
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
                mb: 2,
              }}
            >
              <CloudUpload sx={{ fontSize: 40, color: 'primary.main' }} />
            </Box>
            <Typography variant="h6" sx={{ mb: 1 }}>
              {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
              or click to browse from your computer
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Chip label="PDF" size="small" variant="outlined" />
              <Chip label="JPG" size="small" variant="outlined" />
              <Chip label="PNG" size="small" variant="outlined" />
              <Chip label="TIFF" size="small" variant="outlined" />
            </Box>
            {uploading && <LinearProgress sx={{ mt: 3, borderRadius: 1 }} />}
          </Box>
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          {/* Toolbar */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              p: 2,
              borderBottom: `1px solid ${alpha(colors.text.primary, 0.08)}`,
              flexWrap: 'wrap',
              gap: 2,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {filteredDocuments.length > 0 && (
                <Checkbox
                  checked={selectedDocIds.length === filteredDocuments.length && filteredDocuments.length > 0}
                  indeterminate={selectedDocIds.length > 0 && selectedDocIds.length < filteredDocuments.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              )}
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                All Documents
              </Typography>
              <Chip label={filteredDocuments.length} size="small" sx={{ ml: 1 }} />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                size="small"
                placeholder="Search documents..."
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
                sx={{ width: 220 }}
              />
              <TextField
                select
                size="small"
                label="Status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                sx={{ width: 140 }}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="uploaded">Uploaded</MenuItem>
                <MenuItem value="processing">Processing</MenuItem>
                <MenuItem value="extracted">Extracted</MenuItem>
                <MenuItem value="error">Error</MenuItem>
              </TextField>
              <Tooltip title="Refresh">
                <IconButton onClick={loadAllDocuments}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              {selectedDocIds.length > 0 && (
                <Button
                  variant="contained"
                  color="error"
                  size="small"
                  startIcon={<Delete />}
                  onClick={handleBulkDelete}
                  disabled={deleting}
                >
                  Delete ({selectedDocIds.length})
                </Button>
              )}
            </Box>
          </Box>

          {/* Documents Grid */}
          {loadingDocs ? (
            <Box sx={{ p: 3 }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height={80} sx={{ mb: 2 }} />
              ))}
            </Box>
          ) : filteredDocuments.length === 0 ? (
            <Box sx={{ p: 6, textAlign: 'center' }}>
              <Description sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" sx={{ mb: 1 }}>
                {searchQuery || statusFilter ? 'No documents match your filters' : 'No documents yet'}
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
                {searchQuery || statusFilter
                  ? 'Try adjusting your search or filters'
                  : 'Upload your first document to get started'}
              </Typography>
            </Box>
          ) : (
            <Box sx={{ p: 2 }}>
              {filteredDocuments.map((doc) => (
                <Box
                  key={doc.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    p: 2,
                    mb: 1,
                    borderRadius: 2,
                    border: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                    transition: 'all 0.2s',
                    '&:hover': {
                      borderColor: alpha(colors.primary.main, 0.3),
                      bgcolor: alpha(colors.primary.main, 0.04),
                    },
                  }}
                >
                  <Checkbox
                    checked={selectedDocIds.includes(doc.id)}
                    onChange={(e) => handleSelectDocument(doc.id, e.target.checked)}
                    sx={{ mr: 1 }}
                  />
                  <Box
                    sx={{
                      width: 44,
                      height: 44,
                      borderRadius: 2,
                      bgcolor: alpha(colors.primary.main, 0.1),
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mr: 2,
                    }}
                  >
                    {getFileIcon(doc.mime_type)}
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body1" sx={{ fontWeight: 500, mb: 0.5 }}>
                      {doc.filename}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        ID: {doc.id}
                      </Typography>
                      {doc.page_count && (
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          {doc.page_count} pages
                        </Typography>
                      )}
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {formatUploadDateTime(doc.created_at)}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip
                      icon={getStatusIcon(doc.status)}
                      label={doc.status}
                      size="small"
                      color={getStatusColor(doc.status)}
                    />
                    <Button size="small" variant="outlined" onClick={() => handleViewDetails(doc.id)}>
                      Details
                    </Button>
                    {doc.status === 'extracted' && (
                      <>
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => handleOpenApplyTemplate(doc.id)}
                        >
                          Apply Template
                        </Button>
                        <Tooltip title="View Extractions">
                          <IconButton
                            size="small"
                            onClick={() => navigate(`/documents/${doc.id}/extractions`)}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => {
                          setDocToDelete(doc.id);
                          setDeleteDialogOpen(true);
                        }}
                      >
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Delete Document</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this document? This action cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDeleteDocument}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Document Details Dialog */}
      <Dialog open={detailsOpen} onClose={handleCloseDetails} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Document Details</Typography>
          <IconButton onClick={handleCloseDetails}>
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {loadingDetails ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : selectedDoc ? (
            <Box>
              <Tabs value={tabIndex} onChange={(_, v) => setTabIndex(v)} sx={{ mb: 3 }}>
                <Tab label="Details" icon={<Description />} iconPosition="start" />
                <Tab
                  label="OCR Text"
                  icon={<TextSnippet />}
                  iconPosition="start"
                  disabled={selectedDoc.status !== 'extracted'}
                />
              </Tabs>

              {tabIndex === 0 && (
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Filename
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {selectedDoc.filename}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Status
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Chip label={selectedDoc.status} color={getStatusColor(selectedDoc.status)} size="small" />
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      File Type
                    </Typography>
                    <Typography variant="body1">{selectedDoc.mime_type}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Pages
                    </Typography>
                    <Typography variant="body1">{selectedDoc.page_count || '-'}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Uploaded
                    </Typography>
                    <Typography variant="body1">
                      {formatUploadDateTime(selectedDoc.created_at)}
                    </Typography>
                  </Grid>
                </Grid>
              )}

              {tabIndex === 1 && ocrResult && (
                <Box>
                  {ocrResult.pages?.length > 0 ? (
                    ocrResult.pages.map((page, index) => (
                      <Box key={index} sx={{ mb: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                            Page {page.page_number}
                          </Typography>
                          <Chip
                            label={`${(page.confidence * 100).toFixed(0)}% confidence`}
                            size="small"
                            color={page.confidence > 0.8 ? 'success' : page.confidence > 0.5 ? 'warning' : 'error'}
                          />
                        </Box>
                        <Box
                          sx={{
                            p: 2,
                            borderRadius: 2,
                            bgcolor: alpha(colors.background.default, 0.5),
                            border: `1px solid ${alpha(colors.text.primary, 0.08)}`,
                            maxHeight: 400,
                            overflow: 'auto',
                            fontFamily: 'monospace',
                            fontSize: '0.875rem',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                          }}
                        >
                          {page.text || '[No text extracted]'}
                        </Box>
                        {index < ocrResult.pages.length - 1 && <Divider sx={{ my: 2 }} />}
                      </Box>
                    ))
                  ) : (
                    <Alert severity="info">No OCR text available for this document.</Alert>
                  )}
                </Box>
              )}
            </Box>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Apply Template Dialog */}
      <Dialog open={applyTemplateOpen} onClose={() => setApplyTemplateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Apply Template</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
            Select a template to extract data from this document.
          </Typography>
          <TextField
            select
            fullWidth
            label="Template"
            value={selectedTemplateId || ''}
            onChange={(e) => setSelectedTemplateId(Number(e.target.value))}
          >
            {templates.map((template) => (
              <MenuItem key={template.id} value={template.id}>
                {template.name} {template.doc_category && `(${template.doc_category})`}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyTemplateOpen(false)} disabled={applyingTemplate}>
            Cancel
          </Button>
          <Button
            onClick={handleApplyTemplate}
            variant="contained"
            disabled={!selectedTemplateId || applyingTemplate}
            startIcon={applyingTemplate ? <CircularProgress size={20} /> : <PlayArrow />}
          >
            {applyingTemplate ? 'Applying...' : 'Apply Template'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DocumentsPage;
