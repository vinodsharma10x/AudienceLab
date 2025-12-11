-- Migration: Add Facebook posting fields and statuses
-- Date: 2025-01-XX
-- Description: Adds new status values and columns for tracking Facebook ad posting

-- 1. Add new status values to the CHECK constraint
ALTER TABLE facebook_campaign_scripts
DROP CONSTRAINT IF EXISTS facebook_campaign_scripts_status_check;

ALTER TABLE facebook_campaign_scripts
ADD CONSTRAINT facebook_campaign_scripts_status_check CHECK (status IN (
    'draft',                    -- Saved as draft (videos generated, ready to publish)
    'pending',                  -- Queued for video generation
    'creating_campaign',        -- Creating FB campaign structure
    'generating_videos',        -- Generating video assets
    'uploading_videos',         -- Uploading to Facebook
    'creating_ads',             -- Creating ad sets and ads
    'posting_to_facebook',      -- Posting generated videos to Facebook
    'posting_failed',           -- Facebook posting failed
    'completed',                -- All done, campaign live/scheduled
    'partially_completed',      -- Some videos generated, some failed
    'failed',                   -- Creation failed
    'paused'                    -- Campaign paused
));

-- 2. Add new columns for Facebook posting tracking
ALTER TABLE facebook_campaign_scripts
ADD COLUMN IF NOT EXISTS facebook_adset_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS facebook_ad_ids JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS facebook_post_error TEXT;

-- 3. Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_facebook_campaign_scripts_facebook_adset_id
ON facebook_campaign_scripts(facebook_adset_id);

-- 4. Add comments
COMMENT ON COLUMN facebook_campaign_scripts.facebook_adset_id IS
'Facebook Ad Set ID created for this campaign';

COMMENT ON COLUMN facebook_campaign_scripts.facebook_ad_ids IS
'Array of Facebook Ad IDs created for this campaign (one per video)';

COMMENT ON COLUMN facebook_campaign_scripts.facebook_post_error IS
'Error message if Facebook posting failed';
