import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getValidToken } from '../../utils/auth';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  Grid,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  VideoLibrary as VideoIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
} from '@mui/icons-material';

interface UploadedVideo {
  upload_id: string;
  file_url: string;
  filename: string;
  file_size: number;
  campaign_id?: string;
  status: 'uploading' | 'completed' | 'error';
  progress?: number;
  error?: string;
}

const VideoUpload: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [uploadedVideos, setUploadedVideos] = useState<UploadedVideo[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const validateFile = (file: File): string | null => {
    const allowedTypes = ['.mp4', '.mov', '.avi', '.webm'];
    const maxSize = 500 * 1024 * 1024; // 500MB
    
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedTypes.includes(extension)) {
      return `Invalid file type. Allowed types: ${allowedTypes.join(', ')}`;
    }
    
    if (file.size > maxSize) {
      return `File too large. Maximum size is 500MB, your file is ${formatFileSize(file.size)}`;
    }
    
    return null;
  };

  const uploadFile = async (file: File, campaignId?: string) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    const tempId = `temp_${Date.now()}`;
    const newVideo: UploadedVideo = {
      upload_id: tempId,
      file_url: '',
      filename: file.name,
      file_size: file.size,
      campaign_id: campaignId,
      status: 'uploading',
      progress: 0,
    };
    
    setUploadedVideos(prev => [...prev, newVideo]);
    setError(null);

    try {
      const token = getValidToken(session);
      const formData = new FormData();
      formData.append('file', file);
      if (campaignId) {
        formData.append('campaign_id', campaignId);
      }

      // Create XMLHttpRequest for progress tracking
      const xhr = new XMLHttpRequest();
      
      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadedVideos(prev => 
            prev.map(v => 
              v.upload_id === tempId 
                ? { ...v, progress } 
                : v
            )
          );
        }
      });

      // Handle completion
      const uploadPromise = new Promise<any>((resolve, reject) => {
        xhr.onload = () => {
          if (xhr.status === 200) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            reject(new Error(xhr.responseText));
          }
        };
        xhr.onerror = () => reject(new Error('Upload failed'));
      });

      // Start upload
      xhr.open('POST', `${process.env.REACT_APP_API_URL}/video-ads-v2/upload-video`);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);

      const result = await uploadPromise;
      
      // Update with real data
      setUploadedVideos(prev => 
        prev.map(v => 
          v.upload_id === tempId 
            ? {
                ...v,
                upload_id: result.upload_id,
                file_url: result.file_url,
                status: 'completed',
                progress: 100,
              }
            : v
        )
      );
      
    } catch (error: any) {
      console.error('Upload error:', error);
      setUploadedVideos(prev => 
        prev.map(v => 
          v.upload_id === tempId 
            ? {
                ...v,
                status: 'error',
                error: error.message || 'Upload failed',
              }
            : v
        )
      );
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      Array.from(files).forEach(file => uploadFile(file));
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
    
    const files = event.dataTransfer.files;
    if (files) {
      Array.from(files).forEach(file => uploadFile(file));
    }
  };

  const removeVideo = (uploadId: string) => {
    setUploadedVideos(prev => prev.filter(v => v.upload_id !== uploadId));
  };

  const playVideo = (videoUrl: string) => {
    window.open(videoUrl, '_blank');
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', py: 3 }}>
      <Typography variant="h4" fontWeight="bold" gutterBottom>
        Upload Videos
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Upload your pre-created video ads to store them in the cloud
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Upload Area */}
      <Card 
        sx={{ 
          mb: 3,
          border: isDragging ? 2 : 1,
          borderColor: isDragging ? 'primary.main' : 'divider',
          borderStyle: 'dashed',
          bgcolor: isDragging ? 'action.hover' : 'background.paper',
          cursor: 'pointer',
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <CardContent sx={{ textAlign: 'center', py: 5 }}>
          <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Drag & Drop Videos Here
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            or click to browse
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Supported formats: MP4, MOV, AVI, WebM (max 500MB)
          </Typography>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".mp4,.mov,.avi,.webm"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
        </CardContent>
      </Card>

      {/* Uploaded Videos List */}
      {uploadedVideos.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Uploaded Videos
            </Typography>
            
            <List>
              {uploadedVideos.map((video) => (
                <ListItem key={video.upload_id}>
                  <ListItemIcon>
                    {video.status === 'uploading' && <VideoIcon color="action" />}
                    {video.status === 'completed' && <CheckIcon color="success" />}
                    {video.status === 'error' && <ErrorIcon color="error" />}
                  </ListItemIcon>
                  
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body1">{video.filename}</Typography>
                        <Chip 
                          label={formatFileSize(video.file_size)} 
                          size="small" 
                          variant="outlined" 
                        />
                        {video.status === 'completed' && (
                          <Chip label="Uploaded" size="small" color="success" />
                        )}
                        {video.status === 'error' && (
                          <Chip label="Failed" size="small" color="error" />
                        )}
                      </Box>
                    }
                    secondary={
                      <>
                        {video.status === 'uploading' && (
                          <Box sx={{ mt: 1 }}>
                            <LinearProgress 
                              variant="determinate" 
                              value={video.progress || 0} 
                            />
                            <Typography variant="caption" color="text.secondary">
                              {video.progress}% uploaded
                            </Typography>
                          </Box>
                        )}
                        {video.status === 'error' && (
                          <Typography variant="caption" color="error">
                            {video.error}
                          </Typography>
                        )}
                        {video.status === 'completed' && video.file_url && (
                          <Typography 
                            variant="caption" 
                            color="primary" 
                            sx={{ cursor: 'pointer' }}
                            onClick={() => playVideo(video.file_url)}
                          >
                            Click to preview
                          </Typography>
                        )}
                      </>
                    }
                  />
                  
                  <Box>
                    {video.status === 'completed' && video.file_url && (
                      <IconButton 
                        size="small" 
                        onClick={() => playVideo(video.file_url)}
                        title="Play video"
                      >
                        <PlayIcon />
                      </IconButton>
                    )}
                    <IconButton 
                      size="small" 
                      onClick={() => removeVideo(video.upload_id)}
                      title="Remove from list"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          onClick={() => fileInputRef.current?.click()}
          startIcon={<UploadIcon />}
        >
          Upload More
        </Button>
        <Button
          variant="outlined"
          onClick={() => navigate('/video-ads-v2/campaigns')}
        >
          View Campaigns
        </Button>
      </Box>
    </Box>
  );
};

export default VideoUpload;