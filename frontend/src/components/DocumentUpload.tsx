import React, { useState, useRef } from 'react';
import {
  Box,
  Typography,
  IconButton,
  LinearProgress,
  Alert,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Chip
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as DocumentIcon,
  Image as ImageIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { getValidToken } from '../utils/auth';

interface DocumentUploadProps {
  campaignId: string;
  onDocumentsChange?: (documents: UploadedDocument[]) => void;
  maxFiles?: number;
  maxFileSize?: number; // in MB
  acceptedTypes?: string[];
}

interface UploadedDocument {
  id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  s3_url: string;
  upload_status: 'pending' | 'uploading' | 'completed' | 'failed';
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  campaignId,
  onDocumentsChange,
  maxFiles = 10,
  maxFileSize = 32, // 32MB default (Claude's limit)
  acceptedTypes = ['pdf', 'png', 'jpg', 'jpeg', 'docx', 'pptx', 'doc', 'ppt', 'txt']
}) => {
  const { session } = useAuth();
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = async (files: FileList) => {
    const filesArray = Array.from(files);

    // Validate files
    const validFiles = filesArray.filter(file => {
      const extension = file.name.split('.').pop()?.toLowerCase() || '';
      const sizeInMB = file.size / (1024 * 1024);

      if (!acceptedTypes.includes(extension)) {
        setError(`File type .${extension} is not supported`);
        return false;
      }

      if (sizeInMB > maxFileSize) {
        setError(`File ${file.name} exceeds ${maxFileSize}MB limit`);
        return false;
      }

      return true;
    });

    if (validFiles.length + documents.length > maxFiles) {
      setError(`Maximum ${maxFiles} files allowed`);
      return;
    }

    if (validFiles.length === 0) return;

    // Upload files
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('campaign_id', campaignId);

      validFiles.forEach(file => {
        formData.append('files', file);
      });

      const token = getValidToken(session);

      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/upload-documents`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        }
      );

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        const newDocs = [...documents, ...result.documents];
        setDocuments(newDocs);
        onDocumentsChange?.(newDocs);
        setUploadProgress(100);
        setTimeout(() => setUploadProgress(0), 1000);
      } else {
        setError(result.message || 'Upload failed');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload documents');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    try {
      const token = localStorage.getItem('dev-token') || sessionStorage.getItem('access_token');

      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/video-ads-v2/documents/${documentId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const updatedDocs = documents.filter(doc => doc.id !== documentId);
        setDocuments(updatedDocs);
        onDocumentsChange?.(updatedDocs);
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const getFileIcon = (fileType: string) => {
    if (['png', 'jpg', 'jpeg'].includes(fileType)) {
      return <ImageIcon />;
    }
    return <DocumentIcon />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Supporting Documents (Optional)
      </Typography>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Upload PDFs, images, or documents to provide additional context for AI analysis.
        Supported formats: PDF, PNG, JPG, DOCX, PPTX (max {maxFileSize}MB per file)
      </Typography>

      {/* Upload Area */}
      <Paper
        variant="outlined"
        sx={{
          p: 3,
          borderRadius: 2,
          borderStyle: 'dashed',
          borderColor: dragActive ? 'primary.main' : 'divider',
          backgroundColor: dragActive ? 'action.hover' : 'background.paper',
          cursor: 'pointer',
          transition: 'all 0.3s ease'
        }}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.map(type => `.${type}`).join(',')}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        <Box sx={{ textAlign: 'center' }}>
          <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="body1" gutterBottom>
            Drag & drop files here or click to browse
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Maximum {maxFiles} files, up to {maxFileSize}MB each
          </Typography>
        </Box>
      </Paper>

      {/* Upload Progress */}
      {uploading && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress variant="indeterminate" />
          <Typography variant="caption" sx={{ mt: 1 }}>
            Uploading documents...
          </Typography>
        </Box>
      )}

      {/* Error Message */}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Uploaded Documents List */}
      {documents.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Uploaded Documents ({documents.length})
          </Typography>
          <List>
            {documents.map((doc) => (
              <ListItem
                key={doc.id}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  mb: 1
                }}
              >
                <ListItemIcon>
                  {getFileIcon(doc.file_type)}
                </ListItemIcon>
                <ListItemText
                  primary={doc.file_name}
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={doc.file_type.toUpperCase()}
                        size="small"
                        variant="outlined"
                      />
                      <Typography variant="caption">
                        {formatFileSize(doc.file_size)}
                      </Typography>
                      {doc.upload_status === 'completed' && (
                        <CheckIcon sx={{ fontSize: 16, color: 'success.main' }} />
                      )}
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={() => handleDelete(doc.id)}
                    size="small"
                  >
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Info Message */}
      {documents.length > 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Documents will be analyzed by AI during the avatar analysis phase to provide deeper insights into your target audience and product positioning.
        </Alert>
      )}
    </Box>
  );
};

export default DocumentUpload;