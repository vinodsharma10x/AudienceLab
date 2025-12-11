-- Add batch processing columns to video_ads_v3_campaigns table
-- These columns track Claude Batch API processing for hooks and scripts generation

-- Add batch_id for tracking the Claude Batch API request
ALTER TABLE video_ads_v3_campaigns
ADD COLUMN IF NOT EXISTS hooks_batch_id TEXT;

-- Add scripts_batch_id for tracking the second batch (scripts generation)
ALTER TABLE video_ads_v3_campaigns
ADD COLUMN IF NOT EXISTS scripts_batch_id TEXT;

-- Add batch_status column (pending, processing, completed, failed)
ALTER TABLE video_ads_v3_campaigns
ADD COLUMN IF NOT EXISTS batch_status TEXT DEFAULT 'pending';

-- Add timestamps for batch processing
ALTER TABLE video_ads_v3_campaigns
ADD COLUMN IF NOT EXISTS batch_created_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE video_ads_v3_campaigns
ADD COLUMN IF NOT EXISTS batch_completed_at TIMESTAMP WITH TIME ZONE;

-- Add column for batch error details if any
ALTER TABLE video_ads_v3_campaigns
ADD COLUMN IF NOT EXISTS batch_error TEXT;

-- Add index for faster lookups by batch_id
CREATE INDEX IF NOT EXISTS idx_campaigns_hooks_batch_id
ON video_ads_v3_campaigns(hooks_batch_id)
WHERE hooks_batch_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_campaigns_scripts_batch_id
ON video_ads_v3_campaigns(scripts_batch_id)
WHERE scripts_batch_id IS NOT NULL;

-- Add index for batch_status to quickly find pending/processing batches
CREATE INDEX IF NOT EXISTS idx_campaigns_batch_status
ON video_ads_v3_campaigns(batch_status)
WHERE batch_status IN ('pending', 'processing');