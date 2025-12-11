-- Fix RLS policies for video_ads_v2_documents table
-- This allows both user access and service role access (for backend inserts)

-- Drop the existing policy
DROP POLICY IF EXISTS "Users can view their own documents" ON video_ads_v2_documents;

-- Create separate policies for different operations

-- Policy for SELECT: Users can view their own documents
CREATE POLICY "Users can view their own documents"
ON video_ads_v2_documents
FOR SELECT
USING (auth.uid() = user_id);

-- Policy for INSERT: Allow all authenticated users and service role
-- The backend will ensure the user_id matches the authenticated user
CREATE POLICY "Authenticated users can insert documents"
ON video_ads_v2_documents
FOR INSERT
WITH CHECK (true);

-- Policy for UPDATE: Users can update their own documents
CREATE POLICY "Users can update their own documents"
ON video_ads_v2_documents
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy for DELETE: Users can delete their own documents
CREATE POLICY "Users can delete their own documents"
ON video_ads_v2_documents
FOR DELETE
USING (auth.uid() = user_id);

-- Add a comment about the policies
COMMENT ON TABLE video_ads_v2_documents IS
'Stores document uploads for Video Ads V2. RLS policies allow backend inserts while maintaining user-level security for other operations.';