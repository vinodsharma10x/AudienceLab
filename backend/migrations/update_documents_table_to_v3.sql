-- Update video_ads_v2_documents table to work with v3 campaigns
-- This migration updates the foreign key to reference v3 campaigns

-- First, drop the existing foreign key constraint
ALTER TABLE video_ads_v2_documents
DROP CONSTRAINT IF EXISTS video_ads_v2_documents_campaign_id_fkey;

-- Add new foreign key constraint to v3 campaigns table
-- Reference the campaign_id field in v3 table (not id)
ALTER TABLE video_ads_v2_documents
ADD CONSTRAINT video_ads_v2_documents_campaign_id_fkey
FOREIGN KEY (campaign_id)
REFERENCES video_ads_v3_campaigns(campaign_id)
ON DELETE CASCADE;

-- Also rename the table to v3 for consistency (optional)
-- ALTER TABLE video_ads_v2_documents RENAME TO video_ads_v3_documents;

-- Add comment about the update
COMMENT ON TABLE video_ads_v2_documents IS
'Stores document uploads for Video Ads. Updated to work with v3_campaigns table using campaign_id field.';