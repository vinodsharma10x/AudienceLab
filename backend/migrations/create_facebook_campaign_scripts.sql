-- Facebook Campaign Scripts Table
-- This migration adds a table to store Facebook campaigns created from video ads research
-- Each campaign contains selected scripts from a research campaign

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table to store Facebook campaigns and their selected scripts
CREATE TABLE IF NOT EXISTS facebook_campaign_scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,

    -- Campaign basic info
    campaign_name VARCHAR(255) NOT NULL,
    research_campaign_id UUID NOT NULL, -- Links to video_ads_v3_campaigns

    -- Campaign settings
    ad_account_id VARCHAR(255) NOT NULL,
    objective VARCHAR(50) NOT NULL DEFAULT 'CONVERSIONS',

    -- Budget & Schedule
    daily_budget_per_adset NUMERIC(10, 2) NOT NULL DEFAULT 10.00,
    start_option VARCHAR(20) NOT NULL DEFAULT 'immediately' CHECK (start_option IN ('immediately', 'draft', 'schedule')),
    scheduled_start_time TIMESTAMP WITH TIME ZONE,

    -- Targeting
    targeting_spec JSONB NOT NULL DEFAULT '{}',
    -- Structure: {
    --   "locations": ["United States"],
    --   "age_min": 25,
    --   "age_max": 55,
    --   "gender": "all",
    --   "interests": ["Interest 1", "Interest 2"],
    --   "job_titles": ["Title 1"],
    --   "placements": "automatic"
    -- }

    -- Creative settings
    creative_settings JSONB NOT NULL DEFAULT '{}',
    -- Structure: {
    --   "voice_actor": "",
    --   "video_avatar": "",
    --   "landing_page_url": "",
    --   "cta_button": "LEARN_MORE"
    -- }

    -- Selected scripts (array of script objects)
    selected_scripts JSONB NOT NULL DEFAULT '[]',
    -- Structure: [{
    --   "script_id": "uuid",
    --   "angle_id": "uuid",
    --   "hook_id": "uuid",
    --   "angle_name": "string",
    --   "angle_type": "positive|negative",
    --   "hook_text": "string",
    --   "script_preview": "string",
    --   "full_script": "string",
    --   "cta": "string"
    -- }]

    -- Campaign status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',                    -- Saved as draft (videos generated, ready to publish)
        'pending',                  -- Queued for video generation
        'creating_campaign',        -- Creating FB campaign structure
        'generating_videos',        -- Generating video assets
        'uploading_videos',         -- Uploading to Facebook
        'creating_ads',             -- Creating ad sets and ads
        'completed',                -- All done, campaign live/scheduled
        'partially_completed',      -- Some videos generated, some failed
        'failed',                   -- Creation failed
        'paused'                    -- Campaign paused
    )),

    -- Facebook IDs (populated after creation)
    facebook_campaign_id VARCHAR(255),
    facebook_campaign_data JSONB, -- Store FB campaign details

    -- Video generation tracking
    video_generation_status JSONB DEFAULT '{}',
    -- Structure: {
    --   "script_id_1": {"status": "pending|processing|completed|failed", "video_url": "...", "error": "..."},
    --   "script_id_2": {...}
    -- }

    -- Error handling
    error_message TEXT,
    error_details JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for faster queries
CREATE INDEX idx_facebook_campaign_scripts_user_id ON facebook_campaign_scripts(user_id);
CREATE INDEX idx_facebook_campaign_scripts_research_campaign_id ON facebook_campaign_scripts(research_campaign_id);
CREATE INDEX idx_facebook_campaign_scripts_status ON facebook_campaign_scripts(status);
CREATE INDEX idx_facebook_campaign_scripts_created_at ON facebook_campaign_scripts(created_at DESC);
CREATE INDEX idx_facebook_campaign_scripts_facebook_campaign_id ON facebook_campaign_scripts(facebook_campaign_id);

-- Foreign key to research campaigns
ALTER TABLE facebook_campaign_scripts
ADD CONSTRAINT facebook_campaign_scripts_research_campaign_fkey
FOREIGN KEY (research_campaign_id)
REFERENCES video_ads_v3_campaigns(campaign_id)
ON DELETE CASCADE;

-- Add RLS (Row Level Security)
ALTER TABLE facebook_campaign_scripts ENABLE ROW LEVEL SECURITY;

-- Create policy for user access
CREATE POLICY "Users can manage their own Facebook campaigns" ON facebook_campaign_scripts
    FOR ALL USING (auth.uid() = user_id);

-- Add updated_at trigger
CREATE TRIGGER update_facebook_campaign_scripts_updated_at
BEFORE UPDATE ON facebook_campaign_scripts
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE facebook_campaign_scripts IS
'Stores Facebook ABO test campaigns created from video ads research. Each campaign contains 1-5 selected scripts with targeting and creative settings.';
