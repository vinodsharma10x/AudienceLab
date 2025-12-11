/**
 * V3 Migration Helper
 * Utilities to help migrate from V2 (conversationId) to V3 (campaignId)
 */

export interface V3NavigationState {
  // V3 uses campaignId instead of conversationId
  campaignId: string;
  
  // Product and marketing data
  productInfo?: any;
  marketingAnalysis?: any;
  
  // User selections
  selectedAngles?: any[];
  selectedHooks?: any[];
  selectedScripts?: any[];
  
  // Voice/Actor selections
  selectedVoice?: any;
  selectedActor?: any;
  
  // Navigation flags
  isFromURL?: boolean;
  isFromAudio?: boolean;
  isFromVideo?: boolean;
  isCreatingAdditional?: boolean;
  
  // Resume support
  resumeFromStep?: number;
  
  // Video support
  videoNumber?: number;
  existingVideos?: any[];
  
  // Legacy support (will be removed)
  conversationId?: string;
}

/**
 * Get campaign ID from state (handles both old and new format)
 */
export function getCampaignId(state: any): string | undefined {
  return state?.campaignId || state?.conversationId;
}

/**
 * Migrate V2 state to V3 state
 */
export function migrateToV3State(v2State: any): V3NavigationState {
  if (!v2State) {
    return {} as V3NavigationState;
  }
  
  return {
    ...v2State,
    campaignId: v2State.campaignId || v2State.conversationId,
    // Remove conversationId after migration
    conversationId: undefined
  };
}

/**
 * Create a new campaign request payload
 */
export function createCampaignPayload(productUrl?: string, campaignName?: string) {
  return {
    product_url: productUrl,
    campaign_name: campaignName || `Campaign ${new Date().toLocaleString()}`
  };
}

/**
 * Format API response to handle both V2 and V3 formats
 */
export function normalizeApiResponse(response: any): any {
  // Handle campaign_id vs conversation_id
  if (response.conversation_id && !response.campaign_id) {
    response.campaign_id = response.conversation_id;
  }
  
  return response;
}

/**
 * Check if we're creating an additional video for an existing campaign
 */
export function isCreatingAdditionalVideo(state: V3NavigationState): boolean {
  return state?.isCreatingAdditional === true || (state?.videoNumber && state.videoNumber > 1) || false;
}

/**
 * Get the next video number for a campaign
 */
export function getNextVideoNumber(existingVideos?: any[]): number {
  if (!existingVideos || existingVideos.length === 0) {
    return 1;
  }
  
  const maxNumber = Math.max(...existingVideos.map(v => v.video_number || 0));
  return maxNumber + 1;
}