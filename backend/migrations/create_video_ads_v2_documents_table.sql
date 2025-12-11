-- Create table for storing document uploads for Video Ads V2
-- This table stores metadata for documents uploaded to enhance product analysis

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create documents table
CREATE TABLE IF NOT EXISTS video_ads_v2_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES video_ads_v2_campaigns(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- pdf, png, jpg, jpeg, docx, pptx, etc.
    file_size INTEGER NOT NULL, -- size in bytes
    mime_type VARCHAR(100),
    s3_url TEXT NOT NULL,
    s3_key VARCHAR(500) NOT NULL, -- S3 object key for deletion
    file_metadata JSONB DEFAULT '{}', -- store additional metadata like page count, dimensions for images
    upload_status VARCHAR(50) DEFAULT 'completed' CHECK (upload_status IN ('pending', 'uploading', 'completed', 'failed')),
    processing_status VARCHAR(50) DEFAULT 'ready' CHECK (processing_status IN ('ready', 'processing', 'processed', 'failed')),
    processing_error TEXT, -- store error message if processing fails
    extracted_content TEXT, -- optional: cache extracted text for non-PDF/image files
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX idx_video_ads_v2_documents_campaign_id ON video_ads_v2_documents(campaign_id);
CREATE INDEX idx_video_ads_v2_documents_user_id ON video_ads_v2_documents(user_id);
CREATE INDEX idx_video_ads_v2_documents_upload_status ON video_ads_v2_documents(upload_status);
CREATE INDEX idx_video_ads_v2_documents_created_at ON video_ads_v2_documents(created_at DESC);

-- Enable RLS (Row Level Security)
ALTER TABLE video_ads_v2_documents ENABLE ROW LEVEL SECURITY;

-- Create policy for user access (users can only access their own documents)
CREATE POLICY "Users can view their own documents" ON video_ads_v2_documents
    FOR ALL USING (auth.uid() = user_id);

-- Create trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_video_ads_v2_documents_updated_at
    BEFORE UPDATE ON video_ads_v2_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment to table
COMMENT ON TABLE video_ads_v2_documents IS 'Stores document uploads (PDFs, images, etc.) for Video Ads V2 product analysis enhancement';
COMMENT ON COLUMN video_ads_v2_documents.file_metadata IS 'JSON metadata like {"pages": 10, "width": 1920, "height": 1080}';
COMMENT ON COLUMN video_ads_v2_documents.s3_key IS 'S3 object key for file management and deletion';