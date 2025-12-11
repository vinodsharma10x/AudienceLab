-- Add error_message column to video_ads_v3_campaigns table
-- This supports async campaign processing where we need to track errors

ALTER TABLE video_ads_v3_campaigns
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Add comment for documentation
COMMENT ON COLUMN video_ads_v3_campaigns.error_message IS 'Error message if campaign processing failed';
