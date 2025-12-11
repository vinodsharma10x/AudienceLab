-- Temporarily disable RLS for video_ads_v2_documents table
-- This allows backend operations while we implement proper service role authentication

-- Disable RLS on the documents table
ALTER TABLE video_ads_v2_documents DISABLE ROW LEVEL SECURITY;

-- Add a comment explaining why RLS is disabled
COMMENT ON TABLE video_ads_v2_documents IS
'Stores document uploads for Video Ads V2. RLS temporarily disabled to allow backend operations. Security is enforced at the API level through JWT authentication.';

-- Note: To re-enable RLS later with proper policies:
-- ALTER TABLE video_ads_v2_documents ENABLE ROW LEVEL SECURITY;