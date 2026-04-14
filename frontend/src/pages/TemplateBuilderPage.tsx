/**
 * Template Builder page for visually marking fields on documents.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Paper,
  Typography,
  TextField,
  MenuItem,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Alert,
  CircularProgress,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ArrowBack,
  ArrowForward,
  ZoomIn,
  ZoomOut,
  Delete,
  Save,
  Edit,
  Fullscreen,
  FullscreenExit,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { apiService } from '@/services/api';

interface DocumentOption {
  id: number;
  filename: string;
  page_count: number;
  status: string;
}

interface FieldRegion {
  id: string;
  name: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'currency';
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  required: boolean;
  regex?: string;
}

interface DrawingState {
  isDrawing: boolean;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

const TemplateBuilderPage: React.FC = () => {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();

  // Document state
  const [documents, setDocuments] = useState<DocumentOption[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Image state
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });

  // Canvas and drawing state
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fullscreenCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const loadedImageRef = useRef<HTMLImageElement | null>(null);
  const [drawing, setDrawing] = useState<DrawingState>({
    isDrawing: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
  });

  // Fields state
  const [fields, setFields] = useState<FieldRegion[]>([]);
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null);
  const [fieldDialogOpen, setFieldDialogOpen] = useState(false);
  const [editingField, setEditingField] = useState<FieldRegion | null>(null);

  // Fullscreen state
  const [fullscreenOpen, setFullscreenOpen] = useState(false);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
    if (templateId) {
      loadTemplateData();
    }
  }, []);

  const loadTemplateData = async () => {
    try {
      // Load the latest template version
      const versions = await apiService.getTemplateVersions(Number(templateId));
      if (versions && versions.length > 0) {
        const latestVersion = versions[0]; // Assuming versions are sorted by date desc
        if (latestVersion.fields_json && latestVersion.fields_json.fields) {
          setFields(latestVersion.fields_json.fields);
          console.log('Loaded template fields:', latestVersion.fields_json.fields);
        }
        if (latestVersion.signature_json && latestVersion.signature_json.sample_document_id) {
          setSelectedDocId(latestVersion.signature_json.sample_document_id);
        }
      }
    } catch (err) {
      console.error('Failed to load template data:', err);
    }
  };

  // Load page image when document or page changes
  useEffect(() => {
    if (selectedDocId) {
      loadPageImage(selectedDocId, currentPage);
    }
  }, [selectedDocId, currentPage]);

  // Keep pagination in sync when a document is preselected (e.g. from template signature)
  useEffect(() => {
    if (!selectedDocId) {
      setTotalPages(1);
      setCurrentPage(1);
      return;
    }

    const selectedDoc = documents.find((d) => d.id === selectedDocId);
    const pages = Math.max(1, Number(selectedDoc?.page_count || 1));
    setTotalPages(pages);
    setCurrentPage((prev) => Math.min(prev, pages));
  }, [selectedDocId, documents]);

  // Redraw canvas when fields, zoom, or image changes
  useEffect(() => {
    drawCanvas();
  }, [fields, zoom, imageUrl, selectedFieldId, drawing, imageDimensions, fullscreenOpen]);

  // Force redraw when fullscreen opens (after canvas is mounted)
  useEffect(() => {
    if (fullscreenOpen) {
      // Small delay to ensure canvas is mounted
      const timer = setTimeout(() => {
        drawCanvas();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [fullscreenOpen]);

  const loadDocuments = async () => {
    try {
      const docs = await apiService.listDocuments();
      // Filter to only extracted documents
      const extractedDocs = docs.filter((d: any) => d.status === 'extracted');
      setDocuments(extractedDocs);
    } catch (err) {
      console.error('Failed to load documents:', err);
      setError('Failed to load documents');
    }
  };

  const loadPageImage = async (docId: number, page: number) => {
    console.log('loadPageImage called with docId:', docId, 'page:', page);
    setImageLoading(true);
    try {
      // Revoke previous URL to prevent memory leaks
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }

      console.log('Fetching image from API...');
      const blob = await apiService.getDocumentPageImage(docId, page, 150);
      console.log('Image blob received, size:', blob.size);

      const url = URL.createObjectURL(blob);
      console.log('Created object URL:', url);
      setImageUrl(url);

      // Get image dimensions and cache the image
      const img = new Image();
      img.onload = () => {
        console.log('Image loaded, dimensions:', img.width, 'x', img.height);
        setImageDimensions({ width: img.width, height: img.height });
        loadedImageRef.current = img; // Cache the loaded image
      };
      img.onerror = (e) => {
        console.error('Image failed to load:', e);
      };
      img.src = url;
    } catch (err) {
      console.error('Failed to load page image:', err);
      setError('Failed to load page image');
    } finally {
      setImageLoading(false);
    }
  };

  const handleDocumentChange = (docId: number) => {
    console.log('handleDocumentChange called with docId:', docId, 'currentPage:', currentPage);

    // Clear previous image
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
      setImageUrl(null);
    }

    // Clear fields when changing document
    setFields([]);

    const doc = documents.find((d) => d.id === docId);
    if (doc) {
      setTotalPages(doc.page_count || 1);
    }

    setSelectedDocId(docId);

    // If already on page 1, manually trigger load since state won't change
    if (currentPage === 1) {
      console.log('Already on page 1, manually loading image');
      loadPageImage(docId, 1);
    } else {
      console.log('Setting current page to 1');
      setCurrentPage(1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handleZoomIn = () => {
    setZoom(Math.min(zoom + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoom(Math.max(zoom - 0.25, 0.5));
  };

  // Canvas drawing functions
  const getCanvasCoordinates = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = e.currentTarget;  // Use the canvas that triggered the event
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom;
    const y = (e.clientY - rect.top) / zoom;
    return { x, y };
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = getCanvasCoordinates(e);

    // Check if clicking on existing field
    const clickedField = fields.find(
      (f) =>
        f.page === currentPage &&
        x >= f.x &&
        x <= f.x + f.width &&
        y >= f.y &&
        y <= f.y + f.height
    );

    if (clickedField) {
      setSelectedFieldId(clickedField.id);
      return;
    }

    // Start drawing new field
    setDrawing({
      isDrawing: true,
      startX: x,
      startY: y,
      currentX: x,
      currentY: y,
    });
    setSelectedFieldId(null);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!drawing.isDrawing) return;

    const { x, y } = getCanvasCoordinates(e);
    setDrawing({
      ...drawing,
      currentX: x,
      currentY: y,
    });
  };

  const handleMouseUp = () => {
    if (!drawing.isDrawing) return;

    const width = Math.abs(drawing.currentX - drawing.startX);
    const height = Math.abs(drawing.currentY - drawing.startY);

    // Only create/map field if it has meaningful size
    if (width > 10 && height > 10) {
      const x = Math.min(drawing.startX, drawing.currentX);
      const y = Math.min(drawing.startY, drawing.currentY);

      // If a predefined unmapped field is selected, map the rectangle to it directly
      const selectedField = selectedFieldId
        ? fields.find((f) => f.id === selectedFieldId)
        : null;

      if (selectedField && selectedField.width === 0 && selectedField.height === 0) {
        // Map the region to the selected unmapped field
        const updated = fields.map((f) =>
          f.id === selectedField.id
            ? { ...f, x, y, width, height, page: currentPage }
            : f
        );
        setFields(updated);
      } else {
        // Create a new ad-hoc field (legacy behavior)
        const newField: FieldRegion = {
          id: `field_${Date.now()}`,
          name: '',
          label: '',
          type: 'text',
          page: currentPage,
          x,
          y,
          width,
          height,
          required: false,
        };

        setEditingField(newField);
        setFieldDialogOpen(true);
      }
    }

    setDrawing({
      isDrawing: false,
      startX: 0,
      startY: 0,
      currentX: 0,
      currentY: 0,
    });
  };

  const drawCanvas = () => {
    // Draw on both canvases (normal and fullscreen)
    const canvases = [canvasRef.current, fullscreenCanvasRef.current].filter(Boolean);

    if (canvases.length === 0 || !imageUrl || !loadedImageRef.current) return;

    const img = loadedImageRef.current;

    canvases.forEach((canvas) => {
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Set canvas size
      canvas.width = imageDimensions.width * zoom;
      canvas.height = imageDimensions.height * zoom;

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw image synchronously (already loaded)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Draw existing fields for current page (skip unmapped ones with zero size)
      fields
        .filter((f) => f.page === currentPage && f.width > 0 && f.height > 0)
        .forEach((field) => {
          const isSelected = field.id === selectedFieldId;
          ctx.strokeStyle = isSelected ? '#1976d2' : '#4caf50';
          ctx.lineWidth = isSelected ? 3 : 2;
          ctx.fillStyle = isSelected ? 'rgba(25, 118, 210, 0.1)' : 'rgba(76, 175, 80, 0.1)';

          const x = field.x * zoom;
          const y = field.y * zoom;
          const w = field.width * zoom;
          const h = field.height * zoom;

          ctx.fillRect(x, y, w, h);
          ctx.strokeRect(x, y, w, h);

          // Draw field label
          if (field.label) {
            ctx.fillStyle = isSelected ? '#1976d2' : '#4caf50';
            ctx.font = `${12 * zoom}px Arial`;
            ctx.fillText(field.label, x + 2, y - 4);
          }
        });

      // Draw current drawing rectangle
      if (drawing.isDrawing) {
        ctx.strokeStyle = '#ff9800';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);

        const x = Math.min(drawing.startX, drawing.currentX) * zoom;
        const y = Math.min(drawing.startY, drawing.currentY) * zoom;
        const w = Math.abs(drawing.currentX - drawing.startX) * zoom;
        const h = Math.abs(drawing.currentY - drawing.startY) * zoom;

        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
      }
    });
  };

  const handleSaveField = () => {
    if (!editingField || !editingField.name) return;

    const existingIndex = fields.findIndex((f) => f.id === editingField.id);
    if (existingIndex >= 0) {
      // Update existing field
      const newFields = [...fields];
      newFields[existingIndex] = editingField;
      setFields(newFields);
    } else {
      // Add new field
      setFields([...fields, editingField]);
    }

    setFieldDialogOpen(false);
    setEditingField(null);
    setSelectedFieldId(editingField.id);
  };

  const handleEditField = (field: FieldRegion) => {
    setEditingField({ ...field });
    setFieldDialogOpen(true);
  };

  const handleDeleteField = (fieldId: string) => {
    setFields(fields.filter((f) => f.id !== fieldId));
    if (selectedFieldId === fieldId) {
      setSelectedFieldId(null);
    }
  };

  const handleSaveTemplate = async () => {
    if (fields.length === 0) {
      setError('Please add at least one field');
      return;
    }

    const unmapped = fields.filter((f) => f.width === 0 || f.height === 0);
    if (unmapped.length > 0) {
      setError(
        `Please map all fields before saving. Unmapped: ${unmapped.map((f) => f.name).join(', ')}`
      );
      return;
    }

    setLoading(true);
    try {
      // Save template version with fields
      // Include draw-time image dimensions + DPI so the backend can scale
      // field coordinates to match OCR coordinates (OCR runs at 300 DPI).
      await apiService.createTemplateVersion(Number(templateId), {
        signature_json: {
          sample_document_id: selectedDocId,
          draw_image_width: imageDimensions.width,
          draw_image_height: imageDimensions.height,
          draw_dpi: 150,
        },
        fields_json: { fields },
        rules_json: {},
      });

      navigate('/templates');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save template');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h5">Template Builder</Typography>
          <Typography variant="body2" color="text.secondary">
            Draw rectangles around fields you want to extract
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" onClick={() => navigate('/templates')}>
            Cancel
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSaveTemplate}
            disabled={loading || fields.length === 0}
          >
            Save Template
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2} sx={{ flex: 1, minHeight: 0 }}>
        {/* Left Panel - Document Viewer */}
        <Grid item xs={12} md={9}>
          <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Controls */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <TextField
                select
                size="small"
                label="Select Document"
                value={selectedDocId || ''}
                onChange={(e) => handleDocumentChange(Number(e.target.value))}
                sx={{ minWidth: 250 }}
              >
                {documents.map((doc) => (
                  <MenuItem key={doc.id} value={doc.id}>
                    {doc.filename} ({doc.page_count} pages)
                  </MenuItem>
                ))}
              </TextField>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <IconButton onClick={handlePrevPage} disabled={currentPage <= 1}>
                  <ArrowBack />
                </IconButton>
                <Typography>
                  Page {currentPage} / {totalPages}
                </Typography>
                <IconButton onClick={handleNextPage} disabled={currentPage >= totalPages}>
                  <ArrowForward />
                </IconButton>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <IconButton onClick={handleZoomOut} disabled={zoom <= 0.5}>
                  <ZoomOut />
                </IconButton>
                <Typography>{Math.round(zoom * 100)}%</Typography>
                <IconButton onClick={handleZoomIn} disabled={zoom >= 3}>
                  <ZoomIn />
                </IconButton>
              </Box>

              <IconButton
                onClick={() => setFullscreenOpen(true)}
                disabled={!imageUrl}
                title="Open in fullscreen"
                color="primary"
              >
                <Fullscreen />
              </IconButton>
            </Box>

            {/* Canvas Container */}
            <Box
              ref={containerRef}
              sx={{
                flex: 1,
                overflow: 'auto',
                backgroundColor: '#f5f5f5',
                display: 'flex',
                justifyContent: 'flex-start',
                alignItems: 'flex-start',
                p: 2,
                minHeight: 0,
              }}
            >
              {imageLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', height: '100%' }}>
                  <CircularProgress />
                </Box>
              ) : imageUrl ? (
                <Box sx={{ display: 'inline-block' }}>
                  <canvas
                    ref={canvasRef}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                    style={{ cursor: 'crosshair', border: '1px solid #ccc', display: 'block' }}
                  />
                </Box>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', height: '100%' }}>
                  <Typography color="text.secondary">
                    Select a document to start building the template
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* Right Panel - Fields List */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom>
              Fields ({fields.length})
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
              {fields.some((f) => f.width === 0) ? (
                <>
                  <strong>Step 1:</strong> Click a field below<br />
                  <strong>Step 2:</strong> Draw a rectangle around that field on the document
                </>
              ) : (
                'All fields mapped. Click "Save Template" to finish.'
              )}
            </Typography>
            <Divider sx={{ mb: 2 }} />

            {fields.length === 0 ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                No fields defined. Go back to Templates and create a template with fields first, or draw rectangles here to add them manually.
              </Alert>
            ) : (
              <List sx={{ flex: 1, overflow: 'auto' }}>
                {fields.map((field) => {
                  const isMapped = field.width > 0 && field.height > 0;
                  const isSelected = field.id === selectedFieldId;
                  return (
                    <ListItem
                      key={field.id}
                      button
                      selected={isSelected}
                      onClick={() => {
                        setSelectedFieldId(field.id);
                        if (isMapped && field.page !== currentPage) {
                          setCurrentPage(field.page);
                        }
                      }}
                      sx={{
                        border: 1,
                        borderColor: isSelected ? 'primary.main' : isMapped ? 'success.main' : 'warning.main',
                        borderRadius: 1,
                        mb: 1,
                        borderWidth: isSelected ? 2 : 1,
                      }}
                    >
                      <ListItemText
                        primary={field.label || field.name}
                        secondaryTypographyProps={{ component: 'div' }}
                        secondary={
                          <Box component="span" sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
                            <Chip label={field.type} size="small" />
                            {isMapped ? (
                              <Chip
                                label={`✓ Mapped (p${field.page})`}
                                size="small"
                                color="success"
                                variant="outlined"
                              />
                            ) : (
                              <Chip
                                label="⚠ Not Mapped"
                                size="small"
                                color="warning"
                                variant="outlined"
                              />
                            )}
                          </Box>
                        }
                      />
                      <ListItemSecondaryAction>
                        <IconButton size="small" onClick={() => handleEditField(field)}>
                          <Edit fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => handleDeleteField(field.id)}>
                          <Delete fontSize="small" />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  );
                })}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Field Edit Dialog */}
      <Dialog open={fieldDialogOpen} onClose={() => setFieldDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingField?.name ? 'Edit Field' : 'New Field'}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Field Name (identifier)"
            value={editingField?.name || ''}
            onChange={(e) =>
              setEditingField(editingField ? { ...editingField, name: e.target.value } : null)
            }
            margin="normal"
            required
            placeholder="e.g., invoice_number"
            helperText="Used in extraction results (no spaces)"
          />
          <TextField
            fullWidth
            label="Display Label"
            value={editingField?.label || ''}
            onChange={(e) =>
              setEditingField(editingField ? { ...editingField, label: e.target.value } : null)
            }
            margin="normal"
            placeholder="e.g., Invoice Number"
          />
          <TextField
            fullWidth
            select
            label="Field Type"
            value={editingField?.type || 'text'}
            onChange={(e) =>
              setEditingField(
                editingField
                  ? { ...editingField, type: e.target.value as FieldRegion['type'] }
                  : null
              )
            }
            margin="normal"
          >
            <MenuItem value="text">Text</MenuItem>
            <MenuItem value="number">Number</MenuItem>
            <MenuItem value="date">Date</MenuItem>
            <MenuItem value="currency">Currency</MenuItem>
          </TextField>
          <TextField
            fullWidth
            label="Regex Pattern (optional)"
            value={editingField?.regex || ''}
            onChange={(e) =>
              setEditingField(editingField ? { ...editingField, regex: e.target.value } : null)
            }
            margin="normal"
            placeholder="e.g., INV-\d+"
            helperText="Validation pattern for extracted value"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFieldDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveField}
            variant="contained"
            disabled={!editingField?.name}
          >
            Save Field
          </Button>
        </DialogActions>
      </Dialog>

      {/* Fullscreen Viewer Dialog */}
      <Dialog
        open={fullscreenOpen}
        onClose={() => setFullscreenOpen(false)}
        fullScreen
        PaperProps={{
          sx: { backgroundColor: '#f5f5f5' }
        }}
      >
        <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
          {/* Fullscreen Controls Header */}
          <Box sx={{
            p: 2,
            backgroundColor: 'white',
            borderBottom: '1px solid #e0e0e0',
            display: 'flex',
            gap: 2,
            alignItems: 'center',
            flexWrap: 'wrap'
          }}>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Document Viewer - {documents.find(d => d.id === selectedDocId)?.filename}
            </Typography>

            <TextField
              select
              size="small"
              label="Select Document"
              value={selectedDocId || ''}
              onChange={(e) => handleDocumentChange(Number(e.target.value))}
              sx={{ minWidth: 250 }}
            >
              {documents.map((doc) => (
                <MenuItem key={doc.id} value={doc.id}>
                  {doc.filename} ({doc.page_count} pages)
                </MenuItem>
              ))}
            </TextField>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton onClick={handlePrevPage} disabled={currentPage <= 1}>
                <ArrowBack />
              </IconButton>
              <Typography>
                Page {currentPage} / {totalPages}
              </Typography>
              <IconButton onClick={handleNextPage} disabled={currentPage >= totalPages}>
                <ArrowForward />
              </IconButton>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton onClick={handleZoomOut} disabled={zoom <= 0.5}>
                <ZoomOut />
              </IconButton>
              <Typography>{Math.round(zoom * 100)}%</Typography>
              <IconButton onClick={handleZoomIn} disabled={zoom >= 3}>
                <ZoomIn />
              </IconButton>
            </Box>

            <IconButton
              onClick={() => setFullscreenOpen(false)}
              title="Exit fullscreen"
              color="primary"
            >
              <FullscreenExit />
            </IconButton>
          </Box>

          {/* Fullscreen Canvas Container */}
          <Box
            sx={{
              flex: 1,
              overflow: 'auto',
              display: 'flex',
              justifyContent: 'flex-start',
              alignItems: 'flex-start',
              p: 2,
              minHeight: 0,
            }}
          >
            {imageLoading ? (
              <CircularProgress />
            ) : imageUrl ? (
              <Box sx={{ display: 'inline-block' }}>
                <canvas
                  ref={fullscreenCanvasRef}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  style={{ cursor: 'crosshair', border: '1px solid #ccc', display: 'block', backgroundColor: 'white' }}
                />
              </Box>
            ) : (
              <Typography color="text.secondary">
                Select a document to start building the template
              </Typography>
            )}
          </Box>

          {/* Fullscreen Footer with Instructions */}
          <Box sx={{
            p: 2,
            backgroundColor: 'white',
            borderTop: '1px solid #e0e0e0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <Typography variant="body2" color="text.secondary">
              Draw rectangles around fields you want to extract. Click on existing fields to select them.
            </Typography>
            <Typography variant="body2" color="primary" sx={{ fontWeight: 'bold' }}>
              Fields: {fields.length}
            </Typography>
          </Box>
        </Box>
      </Dialog>
    </Box>
  );
};

export default TemplateBuilderPage;
