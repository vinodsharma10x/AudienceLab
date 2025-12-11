-- Facebook Ad Creation Tables for Sucana v4
-- This migration adds tables for programmatic Facebook ad creation

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table to map video ads to Facebook ads
CREATE TABLE IF NOT EXISTS facebook_ad_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    video_ad_id UUID NOT NULL,
    facebook_campaign_id VARCHAR(255),
    facebook_adset_id VARCHAR(255),
    facebook_ad_id VARCHAR(255),
    facebook_creative_id VARCHAR(255),
    video_upload_status VARCHAR(50) CHECK (video_upload_status IN ('pending', 'uploading', 'processing', 'ready', 'failed')),
    video_facebook_id VARCHAR(255),
    performance_score FLOAT,
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX idx_facebook_ad_mappings_video_ad_id ON facebook_ad_mappings(video_ad_id);
CREATE INDEX idx_facebook_ad_mappings_user_id ON facebook_ad_mappings(user_id);
CREATE INDEX idx_facebook_ad_mappings_facebook_ids ON facebook_ad_mappings(facebook_campaign_id, facebook_adset_id, facebook_ad_id);

-- Table for campaign templates
CREATE TABLE IF NOT EXISTS facebook_campaign_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    objective VARCHAR(50) NOT NULL,
    targeting_spec JSONB,
    budget_settings JSONB,
    placement_settings JSONB,
    bidding_settings JSONB,
    is_default BOOLEAN DEFAULT false,
    usage_count INT DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_facebook_campaign_templates_user_id ON facebook_campaign_templates(user_id);
CREATE INDEX idx_facebook_campaign_templates_is_default ON facebook_campaign_templates(is_default);

-- Table for creative assets
CREATE TABLE IF NOT EXISTS facebook_creative_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    video_ad_id UUID,
    facebook_video_id VARCHAR(255),
    facebook_image_hash VARCHAR(255),
    asset_type VARCHAR(50) CHECK (asset_type IN ('video', 'image', 'carousel')),
    s3_url TEXT,
    facebook_url TEXT,
    upload_status VARCHAR(50) CHECK (upload_status IN ('pending', 'uploading', 'processing', 'ready', 'failed')),
    processing_error TEXT,
    metadata JSONB,
    file_size_bytes BIGINT,
    duration_seconds INT,
    width INT,
    height INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_facebook_creative_assets_user_id ON facebook_creative_assets(user_id);
CREATE INDEX idx_facebook_creative_assets_video_ad_id ON facebook_creative_assets(video_ad_id);
CREATE INDEX idx_facebook_creative_assets_facebook_video_id ON facebook_creative_assets(facebook_video_id);
CREATE INDEX idx_facebook_creative_assets_upload_status ON facebook_creative_assets(upload_status);

-- Table for tracking ad creation jobs
CREATE TABLE IF NOT EXISTS facebook_ad_creation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    job_type VARCHAR(50) CHECK (job_type IN ('single_ad', 'batch_ads', 'split_test', 'dynamic_creative')),
    status VARCHAR(50) CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'partially_completed')),
    request_data JSONB NOT NULL,
    result_data JSONB,
    error_message TEXT,
    total_ads_to_create INT DEFAULT 1,
    ads_created INT DEFAULT 0,
    ads_failed INT DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_facebook_ad_creation_jobs_user_id ON facebook_ad_creation_jobs(user_id);
CREATE INDEX idx_facebook_ad_creation_jobs_status ON facebook_ad_creation_jobs(status);
CREATE INDEX idx_facebook_ad_creation_jobs_created_at ON facebook_ad_creation_jobs(created_at DESC);

-- Table for audience presets
CREATE TABLE IF NOT EXISTS facebook_audience_presets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    targeting_spec JSONB NOT NULL,
    estimated_reach_min INT,
    estimated_reach_max INT,
    is_custom_audience BOOLEAN DEFAULT false,
    custom_audience_id VARCHAR(255),
    usage_count INT DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_facebook_audience_presets_user_id ON facebook_audience_presets(user_id);
CREATE INDEX idx_facebook_audience_presets_name ON facebook_audience_presets(name);

-- Add RLS (Row Level Security) policies
ALTER TABLE facebook_ad_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE facebook_campaign_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE facebook_creative_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE facebook_ad_creation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE facebook_audience_presets ENABLE ROW LEVEL SECURITY;

-- Create policies for user access
CREATE POLICY "Users can view their own ad mappings" ON facebook_ad_mappings
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own campaign templates" ON facebook_campaign_templates
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own creative assets" ON facebook_creative_assets
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own ad creation jobs" ON facebook_ad_creation_jobs
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own audience presets" ON facebook_audience_presets
    FOR ALL USING (auth.uid() = user_id);

-- Add updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_facebook_ad_mappings_updated_at BEFORE UPDATE ON facebook_ad_mappings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facebook_campaign_templates_updated_at BEFORE UPDATE ON facebook_campaign_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facebook_creative_assets_updated_at BEFORE UPDATE ON facebook_creative_assets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facebook_audience_presets_updated_at BEFORE UPDATE ON facebook_audience_presets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();